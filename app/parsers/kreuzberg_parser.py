"""Kreuzberg 适配器。

**实测发现（2026-08-03，kreuzberg==4.10.2）**：
- DOCX：返回 content + tables + metadata，**elements 字段始终为空**（即使开 include_document_structure=True）
- PDF（手写最小版）：返回 content，elements/pages/tables 全空
- 因此本适配器只能基于 content 做启发式段落切分，无法提供精确的 bbox/page/paragraph_index
- 这些缺失会以 warnings 形式记录，pipeline 可选择切换到 FallbackParser

业务代码不直接 import kreuzberg，只通过 Parser 接口调用。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError, detect_source_type, make_document_id

try:
    import kreuzberg  # type: ignore[import-not-found]
    from kreuzberg import ExtractionConfig  # type: ignore[import-not-found]
    _KREUZBERG_VERSION: str | None = getattr(kreuzberg, "__version__", "4.10.2")
    _KREUZBERG_AVAILABLE = True
except ImportError as _e:  # pragma: no cover - 装好 kreuzberg 就不会进
    _KREUZBERG_IMPORT_ERROR = str(_e)
    _KREUZBERG_AVAILABLE = False
    _KREUZBERG_VERSION = None


# 启发式：行长度 ≤ 80 且没有句号，当作 heading
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+(\S.*?)\s*$")  # markdown 风格
_SHORT_LINE_MAX = 80


def _classify_line(line: str) -> tuple[str, dict[str, Any]]:
    """启发式判断单行是 heading 还是 paragraph 片段。返回 (element_type, metadata)。"""
    text = line.strip()
    if not text:
        return "paragraph", {}
    m = _HEADING_RE.match(line)
    if m:
        level = len(line) - len(line.lstrip("#"))
        return "heading", {"level": max(1, level), "raw_text": m.group(1)}
    if len(text) <= _SHORT_LINE_MAX and not text.endswith(("。", ".", "!", "?", "！", "？")):
        return "heading", {"level": 0, "raw_text": text, "heuristic": "short_line"}
    return "paragraph", {}


def _split_content_to_elements(
    content: str, source_type: str, document_id: str
) -> tuple[list[Element], list[str]]:
    """把 kreuzberg 返回的整篇 content 按双换行切段。

    返回 (elements, used_paragraph_indices_per_element)。
    `used_paragraph_indices_per_element` 仅用于调试，调用方一般忽略。
    """
    elements: list[Element] = []
    blocks = [b.strip() for b in re.split(r"\n\s*\n", content) if b.strip()]
    para_idx = 0
    for block in blocks:
        first_line = block.splitlines()[0]
        etype, meta = _classify_line(first_line)
        if etype == "heading" and meta.get("raw_text"):
            # heading 用第一行清洗后的文本
            text = meta["raw_text"]
            elements.append(
                Element(
                    element_id=f"{document_id}::e{len(elements):04d}",
                    type="heading",
                    content=text,
                    parent_id=None,
                    source_locator=_make_locator(source_type, para_idx),
                    confidence=0.6,
                    metadata={"level": meta.get("level", 0), "heuristic": meta.get("heuristic")},
                )
            )
            para_idx += 1
            # 如果 heading 后还有正文（多行 block），把剩余作为 paragraph
            rest = "\n".join(block.splitlines()[1:]).strip()
            if rest:
                elements.append(
                    Element(
                        element_id=f"{document_id}::e{len(elements):04d}",
                        type="paragraph",
                        content=rest,
                        parent_id=None,
                        source_locator=_make_locator(source_type, para_idx),
                        confidence=0.5,
                        metadata={"kreuzberg_heuristic": True},
                    )
                )
                para_idx += 1
        else:
            elements.append(
                Element(
                    element_id=f"{document_id}::e{len(elements):04d}",
                    type="paragraph",
                    content=block,
                    parent_id=None,
                    source_locator=_make_locator(source_type, para_idx),
                    confidence=0.5,
                    metadata={"kreuzberg_heuristic": True},
                )
            )
            para_idx += 1
    return elements, []


def _make_locator(source_type: str, paragraph_index: int) -> dict[str, Any]:
    """Kreuzberg 给不出 bbox/page（实测）。给一个最小合法 locator。

    family 按 docs/locator-kvfs-contract.md §2 标注（pdf→page_geometry、
    docx→structural_index）；占位/启发式标记键保留——family 只解释字段
    含义，不构成可回溯承诺（契约 §1 不变量 2 豁免）。
    """
    if source_type == "pdf":
        # PDF locator schema 要求 page（≥1）。kreuzberg 不给 page 信息时退到 page=1
        # 并用 metadata 标记这是占位。
        return {"family": "page_geometry", "page": 1, "_kreuzberg_placeholder": True}
    return {"family": "structural_index", "paragraph_index": paragraph_index, "_kreuzberg_heuristic": True}


class KreuzbergParser(Parser):
    """Kreuzberg 适配器。

    能力边界（实测）：
    - 能拿到全文 content、tables、metadata
    - 给不出 element-level 结构；本适配器用启发式段落切分模拟
    - PDF 的 page/bbox 给不出，DOCX 的 paragraph_index 是启发式编号而非真实
    """

    name = "kreuzberg"
    version = _KREUZBERG_VERSION or "unknown"
    supported_extensions = (".pdf", ".docx")
    priority = 50  # 备选路径：自动发现让位于 fallback(10)

    def __init__(self, *, include_document_structure: bool = True) -> None:
        self._include_document_structure = include_document_structure

    def parse(self, path: str | Path, source_hash: str) -> Document:
        if not _KREUZBERG_AVAILABLE:
            raise ParserError(
                code="kreuzberg_unavailable",
                message=f"kreuzberg 未安装：{_KREUZBERG_IMPORT_ERROR}",
            )
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )

        source_type = detect_source_type(p)
        try:
            cfg = ExtractionConfig(include_document_structure=self._include_document_structure)
            result = kreuzberg.extract_file_sync(str(p), config=cfg)
        except Exception as e:  # kreuzberg 自己抛的异常各种各样，统一收口
            raise ParserError(
                code="kreuzberg_extract_failed",
                message=f"kreuzberg 解析失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        document_id = make_document_id(source_hash)
        warnings: list[WarningRecord] = []
        elements: list[Element] = []

        content = result.content or ""
        if content:
            els, _ = _split_content_to_elements(content, source_type, document_id)
            elements.extend(els)

        # tables（kreuzberg 的强项之一）
        kreuzberg_tables = result.tables or []
        for i, t in enumerate(kreuzberg_tables):
            md = getattr(t, "markdown", None) or ""
            cells = getattr(t, "cells", None) or []
            tbl_locator: dict[str, Any]
            if source_type == "pdf":
                # kreuzberg 给 page_number=0 表示无效
                pn = getattr(t, "page_number", 0) or 1
                tbl_locator = {"family": "page_geometry", "page": pn}
                bb = getattr(t, "bounding_box", None)
                if bb:
                    tbl_locator["bbox"] = list(bb)
            else:
                tbl_locator = {
                    "family": "structural_index",
                    "table_index": i,
                    "_kreuzberg_heuristic": True,
                }
            elements.append(
                Element(
                    element_id=f"{document_id}::e{len(elements):04d}",
                    type="table",
                    content=md,
                    parent_id=None,
                    source_locator=tbl_locator,
                    confidence=0.8 if cells else 0.5,
                    metadata={
                        "cell_count": sum(len(r) for r in cells) if cells else 0,
                        "row_count": len(cells) if cells else 0,
                        "source": "kreuzberg",
                    },
                )
            )

        # 结构性警告（让 pipeline 知道 kreuzberg 不够用）
        kreuzberg_elements = result.elements
        if not kreuzberg_elements:
            warnings.append(
                WarningRecord(
                    code="kreuzberg_no_structured_elements",
                    reason=(
                        f"kreuzberg {self.version} 未返回结构化 elements，"
                        f"已用启发式段落切分填充 {source_type} 内容"
                    ),
                    details={
                        "source_type": source_type,
                        "fallback_strategy": "heuristic_paragraph_split",
                        "element_count_after_heuristic": len(elements),
                    },
                )
            )
        if source_type == "pdf":
            warnings.append(
                WarningRecord(
                    code="kreuzberg_pdf_no_bbox",
                    reason="kreuzberg 实测无法给出每个 element 的 page/bbox，已用 page=1 占位",
                    details={"source_type": "pdf"},
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
            chunks=[],  # 由 chunker 填
            relations=[],
            warnings=warnings,
            errors=[],
            metadata={
                "kreuzberg_mime_type": result.mime_type,
                "kreuzberg_quality_score": result.quality_score,
            },
        )


__all__ = ["KreuzbergParser"]
