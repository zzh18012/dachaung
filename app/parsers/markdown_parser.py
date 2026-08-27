"""Markdown 解析器：stdlib 实现的 CommonMark 子集，无外部依赖。

支持：
- ATX 标题（``#``..``######``）
- 段落（空行分隔的连续文本行）
- 无序列表项（``-`` / ``*`` / ``+``）
- 有序列表项（``1.`` / ``1)``）
- 围栏代码块（``` ``` ``` 或 ``~~~``）
- 引用块（``>`` 开头，连续行合并）
- 表格（pipe table：``| a | b |`` + 分隔行 ``| --- | --- |``）
- 独立图片行（``![alt](url)`` 整行）
- 主题分隔符（``---`` / ``***`` / ``___``）忽略

明确不支持（避免歧义与依赖）：
- setext 标题（下划线式 ``===`` / ``---``）
- 嵌套列表 / 松紧切换
- 缩进代码块（4 空格）
- reference-style 链接/图片
- YAML frontmatter / TOML frontmatter
- 原生 HTML 块
- 表格列对齐语法（``:---:``）

source_locator 结构：``{"line": N, "section_path": "H1 > H2 > ..."}``，
其中 ``section_path`` 跟踪当前 ATX 标题层级（同级或更高级的标题会弹出栈）。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError, make_document_id

_MD_EXTENSIONS = (".md", ".markdown")

_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_THEMATIC_RE = re.compile(r"^(?:[-*_])(?:\s*[-*_]){2,}$")
_FENCED_RE = re.compile(r"^(`{3,}|~{3,})\s*([\w+-]*)\s*$")
_UNORDERED_LIST_RE = re.compile(r"^[-*+]\s+(.+)$")
_ORDERED_LIST_RE = re.compile(r"^\d+[.)]\s+(.+)$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.*)$")
_PIPE_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_PIPE_TABLE_SEP_RE = re.compile(
    r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$"
)
_STANDALONE_IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")


def _detect_md_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _MD_EXTENSIONS:
        return "markdown"
    raise ParserError(
        code="unsupported_type",
        message=f"Markdown 解析器只支持 .md/.markdown，得到 {suffix or '(无)'}",
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


def _split_pipe_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _is_pipe_table_start(lines: list[str], i: int) -> bool:
    """lines[i] 是表格首行：当前行 + 下一行满足 pipe + 分隔。"""
    if i + 1 >= len(lines):
        return False
    return bool(
        _PIPE_TABLE_ROW_RE.match(lines[i])
        and _PIPE_TABLE_SEP_RE.match(lines[i + 1])
    )


class MarkdownParser(Parser):
    """Markdown → elements 的最小解析器。"""

    name = "markdown"
    version = "stdlib/0.1.0"

    def parse(self, path: str | Path, source_hash: str) -> Document:
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        source_type = _detect_md_source_type(p)
        document_id = make_document_id(source_hash)

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ParserError(
                code="md_read_failed",
                message=f"读取 Markdown 文件失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        elements, warnings = self._parse_text(text, document_id)
        if not elements:
            warnings.append(
                WarningRecord(
                    code="md_no_content",
                    reason="Markdown 文件未提取到任何 element（可能为空文件或仅含主题分隔符）",
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
            metadata={"markdown": True},
        )

    def _parse_text(
        self, text: str, document_id: str
    ) -> tuple[list[Element], list[WarningRecord]]:
        lines = text.splitlines()
        n = len(lines)
        elements: list[Element] = []
        warnings: list[WarningRecord] = []
        section_path: list[str] = []
        section_levels: list[int] = []

        def make_locator(line_idx_1based: int) -> dict[str, Any]:
            loc: dict[str, Any] = {"line": line_idx_1based}
            if section_path:
                loc["section_path"] = " > ".join(section_path)
            return loc

        def push(
            etype: str,
            content: str | None,
            line_idx: int,
            *,
            resource_path: str | None = None,
            **meta: Any,
        ) -> None:
            elements.append(
                Element(
                    element_id=f"{document_id}::e{len(elements):04d}",
                    type=etype,
                    content=content,
                    resource_path=resource_path,
                    parent_id=None,
                    source_locator=make_locator(line_idx),
                    confidence=0.95,
                    metadata=meta,
                )
            )

        i = 0
        while i < n:
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # ATX 标题
            m = _ATX_HEADING_RE.match(line)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                while section_levels and section_levels[-1] >= level:
                    section_levels.pop()
                    section_path.pop()
                section_levels.append(level)
                section_path.append(title)
                push("heading", title, i + 1, level=level)
                i += 1
                continue

            # 围栏代码块
            m = _FENCED_RE.match(line)
            if m:
                fence = m.group(1)
                lang = m.group(2)
                start_line = i + 1
                code_lines: list[str] = []
                i += 1
                while i < n and not lines[i].strip().startswith(fence[0] * 3):
                    code_lines.append(lines[i])
                    i += 1
                if i < n:
                    i += 1  # 跳过结束围栏
                code = "\n".join(code_lines)
                if code:
                    push("paragraph", code, start_line, kind="code_block", language=lang or "")
                else:
                    warnings.append(
                        WarningRecord(
                            code="md_empty_code_block",
                            reason=f"line {start_line} 处的代码块为空",
                        )
                    )
                continue

            # 主题分隔符
            if _THEMATIC_RE.match(stripped):
                i += 1
                continue

            # 独立图片行
            m = _STANDALONE_IMAGE_RE.match(stripped)
            if m:
                alt = m.group(1)
                url = m.group(2)
                push("image", None, i + 1, resource_path=url, alt=alt)
                i += 1
                continue

            # 列表项
            m = _UNORDERED_LIST_RE.match(line)
            if m:
                push("list_item", m.group(1).strip(), i + 1, ordered=False, marker="unordered")
                i += 1
                continue
            m = _ORDERED_LIST_RE.match(line)
            if m:
                push("list_item", m.group(1).strip(), i + 1, ordered=True, marker="ordered")
                i += 1
                continue

            # 引用块（连续 > 行合并）
            if _BLOCKQUOTE_RE.match(line):
                start_line = i + 1
                quoted: list[str] = []
                while i < n:
                    bm = _BLOCKQUOTE_RE.match(lines[i])
                    if not bm:
                        break
                    quoted.append(bm.group(1))
                    i += 1
                text_ = "\n".join(quoted).strip()
                if text_:
                    push("paragraph", text_, start_line, kind="blockquote")
                continue

            # 表格
            if _is_pipe_table_start(lines, i):
                start_line = i + 1
                end = i
                while end < n and _PIPE_TABLE_ROW_RE.match(lines[end]):
                    end += 1
                table_lines = lines[i:end]
                i = end
                rows = [_split_pipe_row(table_lines[0])] + [
                    _split_pipe_row(row_line) for row_line in table_lines[2:]
                ]
                md = _rows_to_md(rows)
                push(
                    "table",
                    md,
                    start_line,
                    row_count=len(rows),
                    col_count=max(len(r) for r in rows),
                    source="markdown_pipe_table",
                )
                continue

            # 段落：吸收后续连续非特殊行
            start_line = i + 1
            para_lines: list[str] = [line]
            i += 1
            while i < n:
                nxt = lines[i]
                nxt_stripped = nxt.strip()
                if not nxt_stripped:
                    break
                if (
                    _ATX_HEADING_RE.match(nxt)
                    or _FENCED_RE.match(nxt)
                    or _THEMATIC_RE.match(nxt_stripped)
                    or _UNORDERED_LIST_RE.match(nxt)
                    or _ORDERED_LIST_RE.match(nxt)
                    or _BLOCKQUOTE_RE.match(nxt)
                    or _STANDALONE_IMAGE_RE.match(nxt_stripped)
                    or _is_pipe_table_start(lines, i)
                ):
                    break
                para_lines.append(nxt)
                i += 1
            content = "\n".join(para_lines).strip()
            if content:
                push("paragraph", content, start_line)

        return elements, warnings


__all__ = ["MarkdownParser"]
