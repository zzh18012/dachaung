"""HTML 解析器：基于 stdlib ``html.parser``，无外部依赖。

支持：
- 标题 ``<h1>..<h6>``
- 段落 ``<p>`` 与 body 直接子文本（loose text）
- 无序/有序列表 ``<ul>`` / ``<ol>`` / ``<li>``
- 预格式化 ``<pre>``（保留文本，附 ``metadata.kind="preformatted"``）
- 引用 ``<blockquote>``（附 ``metadata.kind="blockquote"``）
- 表格 ``<table>/<tr>/<td>/<th>``
- 图片 ``<img src=...>``（独立 element，``resource_path=src``）
- ``<hr>`` 主题分隔符（忽略）
- 字符实体（``convert_charrefs=True`` 自动转换）

跳过：``<head>``、``<title>``、``<script>``、``<style>`` 内的内容。

明确不支持：
- 表格列对齐 / colspan / rowspan（按 cell 顺序填充）
- ``<dl>/<dt>/<dd>`` 定义列表
- 内联框架 / object / video
- CSS / JS 触发的动态内容

嵌套 table 语义（BUG-html-1 修复）：内层 table 作为独立 table element
解析一次（不重复折叠进外层单元格）；外层单元格的直接文本在嵌套点
前/后各保留为一个 paragraph element；每段文本恰好出现一次；记
``html_nested_table`` 警告。元素顺序：前文本段 → 内层表格 → 后文本段
→ 外层表格（外层表格在 ``</table>`` 才产出），来源顺序经 line locator
可追踪。

source_locator 结构：``{"line": N, "section_path": "H1 > H2..."}``，
``section_path`` 跟踪当前 ATX 标题层级（同级或更高级标题弹出栈）。
"""

from __future__ import annotations

from html.parser import HTMLParser as _StdHTMLParser
from pathlib import Path
from typing import Any

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError, make_document_id

_HTML_EXTENSIONS = (".html", ".htm")
_HEADING_LEVELS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_SKIP_TAGS = {"script", "style", "head", "title", "meta", "link", "noscript"}


def _detect_html_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _HTML_EXTENSIONS:
        return "html"
    raise ParserError(
        code="unsupported_type",
        message=f"HTML 解析器只支持 .html/.htm，得到 {suffix or '(无)'}",
        details={"suffix": suffix},
    )


def _rows_to_md(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    norm = [r + [""] * (width - len(r)) for r in rows]
    header = norm[0]
    body = norm[1:] if len(norm) > 1 else []
    out = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


class _HTMLDocParser(_StdHTMLParser):
    """SAX 风格的 HTML → elements 转换器。"""

    def __init__(self, document_id: str) -> None:
        super().__init__(convert_charrefs=True)
        self.document_id = document_id
        self.elements: list[Element] = []
        self.warnings: list[WarningRecord] = []
        # 当前块上下文
        self._cur_kind: str | None = None
        self._cur_buffer: list[str] = []
        self._cur_start_line: int = 0
        self._cur_level: int = 0
        self._cur_ordered: bool = False
        # 列表栈
        self._list_stack: list[str] = []
        # 嵌套 pre/blockquote 计数（同种可嵌套）
        self._pre_depth = 0
        self._blockquote_depth = 0
        # section 跟踪
        self._section_path: list[str] = []
        self._section_levels: list[int] = []
        # 表格模式
        self._table_depth = 0
        self._table_rows_stack: list[list[list[str]]] = []
        self._table_start_lines: list[int] = []
        self._row_buffers_stack: list[list[str] | None] = []
        self._cell_buffers_stack: list[list[str] | None] = []
        # 当前 cell 是否被嵌套 table 消费过（收尾时文本走段落而非单元格）
        self._cell_nested_stack: list[bool] = []
        # 跳过栈
        self._skip_stack: list[str] = []

    # ---------- locator 与 emit ----------

    def _make_locator_for_current(self) -> dict[str, Any]:
        loc: dict[str, Any] = {"line": self._cur_start_line}
        if self._section_path:
            loc["section_path"] = " > ".join(self._section_path)
        return loc

    def _make_locator_for_inline(self) -> dict[str, Any]:
        loc: dict[str, Any] = {"line": self.getpos()[0]}
        if self._section_path:
            loc["section_path"] = " > ".join(self._section_path)
        return loc

    def _emit_image(self, src: str, alt: str) -> None:
        self._flush_block()
        self.elements.append(
            Element(
                element_id=f"{self.document_id}::e{len(self.elements):04d}",
                type="image",
                content=None,
                resource_path=src,
                parent_id=None,
                source_locator=self._make_locator_for_inline(),
                confidence=0.9,
                metadata={"alt": alt},
            )
        )

    def _emit_cell_text_paragraph(self, text: str) -> None:
        """BUG-html-1：被嵌套 table 消费的单元格直接文本 → paragraph。"""
        self.elements.append(
            Element(
                element_id=f"{self.document_id}::e{len(self.elements):04d}",
                type="paragraph",
                content=text,
                parent_id=None,
                source_locator=self._make_locator_for_inline(),
                confidence=0.9,
                metadata={},
            )
        )

    def _flush_block(self) -> None:
        if self._cur_kind is None:
            return
        text = "".join(self._cur_buffer).strip()
        if not text:
            self._reset_block()
            return
        if self._cur_kind == "heading":
            level = self._cur_level or 1
            while self._section_levels and self._section_levels[-1] >= level:
                self._section_levels.pop()
                self._section_path.pop()
            self._section_levels.append(level)
            self._section_path.append(text)
            self.elements.append(
                Element(
                    element_id=f"{self.document_id}::e{len(self.elements):04d}",
                    type="heading",
                    content=text,
                    parent_id=None,
                    source_locator={"line": self._cur_start_line, "section_path": " > ".join(self._section_path)},
                    confidence=0.95,
                    metadata={"level": level},
                )
            )
        elif self._cur_kind == "list_item":
            self.elements.append(
                Element(
                    element_id=f"{self.document_id}::e{len(self.elements):04d}",
                    type="list_item",
                    content=text,
                    parent_id=None,
                    source_locator=self._make_locator_for_current(),
                    confidence=0.95,
                    metadata={"ordered": self._cur_ordered, "marker": "ordered" if self._cur_ordered else "unordered"},
                )
            )
        else:
            kind_meta = {"pre": "preformatted", "blockquote": "blockquote"}.get(self._cur_kind)
            meta: dict[str, Any] = {"kind": kind_meta} if kind_meta else {}
            self.elements.append(
                Element(
                    element_id=f"{self.document_id}::e{len(self.elements):04d}",
                    type="paragraph",
                    content=text,
                    parent_id=None,
                    source_locator=self._make_locator_for_current(),
                    confidence=0.95,
                    metadata=meta,
                )
            )
        self._reset_block()

    def _reset_block(self) -> None:
        self._cur_kind = None
        self._cur_buffer = []
        self._cur_level = 0
        self._cur_ordered = False

    def _start_block(self, kind: str, level: int = 0, ordered: bool = False) -> None:
        self._flush_block()
        self._cur_kind = kind
        self._cur_buffer = []
        self._cur_start_line = self.getpos()[0]
        self._cur_level = level
        self._cur_ordered = ordered

    # ---------- SAX 回调 ----------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._skip_stack:
            if tag == self._skip_stack[-1]:
                self._skip_stack.append(tag)
            return
        if tag in _SKIP_TAGS:
            self._skip_stack.append(tag)
            return

        # 表格模式
        if tag == "table":
            self._flush_block()
            if self._table_depth >= 1:
                # BUG-html-1 修复：嵌套 table 作为独立元素解析一次；
                # 外层单元格的直接文本保留为段落，不折叠进外层单元格
                if self._cell_buffers_stack[-1] is not None:
                    text = "".join(self._cell_buffers_stack[-1]).strip()
                    if text:
                        self._emit_cell_text_paragraph(text)
                    self._cell_buffers_stack[-1] = None
                    self._cell_nested_stack[-1] = True
                self.warnings.append(
                    WarningRecord(
                        code="html_nested_table",
                        reason="嵌套 table 已作为独立元素解析；外层单元格直接文本保留为段落",
                    )
                )
            self._table_depth += 1
            self._table_rows_stack.append([])
            self._table_start_lines.append(self.getpos()[0])
            self._row_buffers_stack.append(None)
            self._cell_buffers_stack.append(None)
            self._cell_nested_stack.append(False)
            return
        if self._table_depth >= 1:
            self._handle_table_inner_start(tag, attrs)
            return

        # 普通块
        if tag in _HEADING_LEVELS:
            self._start_block("heading", level=_HEADING_LEVELS[tag])
        elif tag == "p":
            if self._cur_kind is None:
                self._start_block("paragraph")
            # 已经在 blockquote/pre 上下文中：忽略 <p>，继续累积
        elif tag == "li":
            ordered = bool(self._list_stack) and self._list_stack[-1] == "ol"
            self._start_block("list_item", ordered=ordered)
        elif tag == "pre":
            self._pre_depth += 1
            if self._pre_depth == 1:
                self._start_block("pre")
        elif tag == "blockquote":
            self._blockquote_depth += 1
            if self._blockquote_depth == 1:
                self._start_block("blockquote")
        elif tag in ("ul", "ol"):
            self._flush_block()
            self._list_stack.append(tag)
        elif tag == "img":
            attrs_d = {k: (v or "") for k, v in attrs}
            src = attrs_d.get("src", "").strip()
            alt = attrs_d.get("alt", "")
            if src:
                self._emit_image(src, alt)
        elif tag == "br":
            if self._cur_kind is not None:
                self._cur_buffer.append(" ")
        elif tag == "hr":
            self._flush_block()
        # 其他 inline / container：忽略

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "img":
            attrs_d = {k: (v or "") for k, v in attrs}
            src = attrs_d.get("src", "").strip()
            alt = attrs_d.get("alt", "")
            if src:
                self._emit_image(src, alt)
        elif tag == "br":
            if self._cur_kind is not None:
                self._cur_buffer.append(" ")
        elif tag == "hr":
            self._flush_block()
        else:
            # 其他自闭合：当作 start tag 处理
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_stack:
            if tag == self._skip_stack[-1]:
                self._skip_stack.pop()
            return

        if self._table_depth >= 1:
            if tag == "table":
                rows = self._table_rows_stack.pop()
                start_line = self._table_start_lines.pop()
                self._row_buffers_stack.pop()
                self._cell_buffers_stack.pop()
                self._cell_nested_stack.pop()
                self._table_depth -= 1
                # BUG-html-1：回到外层时，被嵌套消费过的 cell 重开以接收后文
                if (
                    self._table_depth >= 1
                    and self._cell_nested_stack
                    and self._cell_nested_stack[-1]
                    and self._cell_buffers_stack[-1] is None
                ):
                    self._cell_buffers_stack[-1] = []
                md = _rows_to_md(rows)
                if md:
                    self.elements.append(
                        Element(
                            element_id=f"{self.document_id}::e{len(self.elements):04d}",
                            type="table",
                            content=md,
                            parent_id=None,
                            source_locator={"line": start_line, **({"section_path": " > ".join(self._section_path)} if self._section_path else {})},
                            confidence=0.9,
                            metadata={
                                "row_count": len(rows),
                                "col_count": max((len(r) for r in rows), default=0),
                                "source": "html_table",
                            },
                        )
                    )
                return
            self._handle_table_inner_end(tag)
            return

        if tag in _HEADING_LEVELS and self._cur_kind == "heading":
            self._flush_block()
        elif tag == "p" and self._cur_kind == "paragraph":
            self._flush_block()
        elif tag == "li" and self._cur_kind == "list_item":
            self._flush_block()
        elif tag == "pre":
            if self._pre_depth > 0:
                self._pre_depth -= 1
                if self._pre_depth == 0 and self._cur_kind == "pre":
                    self._flush_block()
        elif tag == "blockquote":
            if self._blockquote_depth > 0:
                self._blockquote_depth -= 1
                if self._blockquote_depth == 0 and self._cur_kind == "blockquote":
                    self._flush_block()
        elif tag in ("ul", "ol"):
            if self._list_stack and self._list_stack[-1] == tag:
                self._list_stack.pop()
            self._flush_block()

    def _finalize_cell(self) -> None:
        """收尾当前 cell：被嵌套消费过的 cell 文本走段落，普通 cell 并入行。"""
        text = "".join(self._cell_buffers_stack[-1]).strip()
        if self._cell_nested_stack[-1]:
            if text:
                self._emit_cell_text_paragraph(text)
            if self._row_buffers_stack[-1] is not None:
                self._row_buffers_stack[-1].append("")
        else:
            if self._row_buffers_stack[-1] is not None:
                self._row_buffers_stack[-1].append(text)
        self._cell_buffers_stack[-1] = None
        self._cell_nested_stack[-1] = False

    def _handle_table_inner_start(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "tr":
            if self._row_buffers_stack[-1] is not None:
                if (
                    self._cell_buffers_stack[-1] is not None
                    and self._cell_nested_stack[-1]
                ):
                    # 嵌套消费过的 cell 在未闭合 <tr> 前收尾（保留文本）
                    self._finalize_cell()
                # 上一个 <tr> 未正常闭合，先收尾
                self._table_rows_stack[-1].append(self._row_buffers_stack[-1])
            self._row_buffers_stack[-1] = []
            self._cell_buffers_stack[-1] = None
            self._cell_nested_stack[-1] = False
        elif tag in ("td", "th"):
            if self._row_buffers_stack[-1] is None:
                self._row_buffers_stack[-1] = []
            if self._cell_buffers_stack[-1] is not None:
                self._finalize_cell()
            self._cell_buffers_stack[-1] = []
            self._cell_nested_stack[-1] = False

    def _handle_table_inner_end(self, tag: str) -> None:
        if tag == "tr":
            if self._cell_buffers_stack[-1] is not None:
                self._finalize_cell()
            if self._row_buffers_stack[-1] is not None:
                self._table_rows_stack[-1].append(self._row_buffers_stack[-1])
                self._row_buffers_stack[-1] = None
        elif tag in ("td", "th"):
            if self._cell_buffers_stack[-1] is not None:
                self._finalize_cell()

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        if self._table_depth >= 1:
            if self._cell_buffers_stack[-1] is not None:
                self._cell_buffers_stack[-1].append(data)
            return
        if self._cur_kind is None:
            if data.strip():
                # loose text → 视为段落
                self._start_block("paragraph")
                self._cur_buffer.append(data)
        else:
            self._cur_buffer.append(data)


class HtmlParser(Parser):
    """HTML → elements 解析器。"""

    name = "html"
    version = "stdlib/0.1.0"

    def parse(self, path: str | Path, source_hash: str) -> Document:
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        source_type = _detect_html_source_type(p)
        document_id = make_document_id(source_hash)

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ParserError(
                code="html_read_failed",
                message=f"读取 HTML 文件失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        handler = _HTMLDocParser(document_id)
        try:
            handler.feed(text)
            handler.close()
        except Exception as e:
            raise ParserError(
                code="html_parse_failed",
                message=f"HTML 解析失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        handler._flush_block()
        elements = handler.elements
        warnings = handler.warnings
        if not elements:
            warnings.append(
                WarningRecord(
                    code="html_no_content",
                    reason="HTML 文件未提取到任何 element（可能为空 body 或仅含 head/script）",
                )
            )

        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type=source_type,
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=elements,
            chunks=[],
            relations=[],
            warnings=warnings,
            errors=[],
            metadata={"html": True},
        )


__all__ = ["HtmlParser"]
