"""Jupyter Notebook (.ipynb) 解析器：stdlib ``json`` + 复用 MarkdownParser。

支持 nbformat == 4 的 .ipynb 文件（契约 docs/ipynb-contract.md）。每个 cell 转换为 element(s)：

- ``markdown`` cell → 委托给 ``MarkdownParser._parse_text``，可能产生多个 element
  （heading / paragraph / list_item / table 等）
- ``code`` cell → 单个 paragraph，``metadata.kind="code_cell"``，
  ``metadata.language`` 来自 kernelspec.language_info.name
- ``raw`` cell → 单个 paragraph，``metadata.kind="raw_cell"``

source_locator 结构：``{"family": "container_line", "cell_index": N (0-based), "cell_type": "markdown"|"code"|"raw", "line": N (1-based, cell 内偏移)}``。
markdown cell 里的 sub-element 还会带 ``section_path``（仅在该 cell 内的标题栈）；
family 语义见 docs/locator-kvfs-contract.md。

不做的事（明确放弃）：
- ``outputs``（执行输出）→ 丢弃
- ``execution_count`` → 丢弃
- 跨 cell 的 section_path 跟踪（每个 markdown cell 独立）
- nbformat < 4 的老格式
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError, make_document_id
from app.parsers.markdown_parser import MarkdownParser

_IPYNB_EXTENSIONS = (".ipynb",)


def _detect_ipynb_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _IPYNB_EXTENSIONS:
        return "ipynb"
    raise ParserError(
        code="unsupported_type",
        message=f"Jupyter Notebook 解析器只支持 .ipynb，得到 {suffix or '(无)'}",
        details={"suffix": suffix},
    )


def _cell_source_to_text(source: Any) -> str | None:
    """契约 §5（adoption 修正，2026-08-27）：source 归一。

    str 原样返回；list 须全部项为 str 才 ''.join（禁止 str() 把
    数字/对象/null 转成正文）；其余（缺失、非 str/list、列表含非
    字符串项）返回 None 表示非法，由调用方跳过该 cell 并发
    ipynb_bad_cell。
    """
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(s, str) for s in source):
        return "".join(source)
    return None


def _extract_kernel_language(metadata: dict[str, Any]) -> str:
    """从 notebook metadata 推断主语言。

    契约 §6（adoption 修正，2026-08-27）：kernelspec.language →
    language_info.name → 空串；kernelspec.name 是内核标识，不参与
    语言判定。非 dict 的中间节点与非 str 取值视作缺失（不崩溃、
    不做 str() 强转）。
    """
    for holder_key, lang_key in (
        ("kernelspec", "language"),
        ("language_info", "name"),
    ):
        holder = metadata.get(holder_key)
        if not isinstance(holder, dict):
            continue
        value = holder.get(lang_key)
        if isinstance(value, str) and value:
            return value
    return ""


class IpynbParser(Parser):
    """.ipynb → elements 解析器。"""

    name = "ipynb"
    version = "stdlib/0.1.0"

    def parse(self, path: str | Path, source_hash: str) -> Document:
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        source_type = _detect_ipynb_source_type(p)
        document_id = make_document_id(source_hash)

        try:
            with p.open("r", encoding="utf-8") as f:
                nb = json.load(f)
        except json.JSONDecodeError as e:
            raise ParserError(
                code="ipynb_invalid_json",
                message=f".ipynb 不是合法 JSON: {e}",
                details={"exception_type": type(e).__name__},
            ) from e
        except OSError as e:
            raise ParserError(
                code="ipynb_read_failed",
                message=f"读取 .ipynb 文件失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        if not isinstance(nb, dict):
            raise ParserError(
                code="ipynb_bad_structure",
                message=".ipynb 顶层不是对象",
            )
        # 契约 §2（adoption 修正，2026-08-27）：版本字段必须为整数类型
        # （bool 属于 int 但语义是布尔，显式拒绝）；缺失或类型错误归
        # ipynb_bad_structure；类型合法但主版本 != 4 归 ipynb_unsupported_version。
        nbformat_major = nb.get("nbformat")
        if not isinstance(nbformat_major, int) or isinstance(nbformat_major, bool):
            raise ParserError(
                code="ipynb_bad_structure",
                message=f".ipynb 的 nbformat 字段缺失或不是整数: {nbformat_major!r}",
                details={"field": "nbformat", "value": nbformat_major},
            )
        if nbformat_major != 4:
            raise ParserError(
                code="ipynb_unsupported_version",
                message=f"仅支持 nbformat == 4，得到 nbformat={nbformat_major}",
                details={"nbformat": nbformat_major},
            )
        nbformat_minor = nb.get("nbformat_minor")
        if (
            not isinstance(nbformat_minor, int)
            or isinstance(nbformat_minor, bool)
            or nbformat_minor < 0
        ):
            raise ParserError(
                code="ipynb_bad_structure",
                message=f".ipynb 的 nbformat_minor 字段缺失、不是整数或为负: {nbformat_minor!r}",
                details={"field": "nbformat_minor", "value": nbformat_minor},
            )

        cells = nb.get("cells") or []
        if not isinstance(cells, list):
            raise ParserError(
                code="ipynb_bad_structure",
                message=".ipynb 的 cells 字段不是数组",
            )

        nb_metadata = nb.get("metadata")
        if not isinstance(nb_metadata, dict):
            nb_metadata = {}
        language = _extract_kernel_language(nb_metadata)
        md_parser = MarkdownParser()
        raw_elements: list[tuple[str, str | None, str | None, dict[str, Any], dict[str, Any]]] = []
        # (type, content, resource_path, source_locator, metadata)
        warnings: list[WarningRecord] = []

        for idx, cell in enumerate(cells):
            if not isinstance(cell, dict):
                warnings.append(WarningRecord(
                    code="ipynb_bad_cell",
                    reason=f"cell #{idx} 不是对象，已跳过",
                    details={"cell_index": idx},
                ))
                continue
            # 契约 §7（adoption 修正，2026-08-27）：outputs/attachments 只忽略
            # 并诊断，不入 elements/metadata；不因 nbformat_minor 门控。
            outputs = cell.get("outputs")
            if isinstance(outputs, list) and outputs:
                warnings.append(WarningRecord(
                    code="ipynb_outputs_ignored",
                    reason=f"cell #{idx} 的 outputs 已忽略",
                    details={"cell_index": idx, "count": len(outputs)},
                ))
            attachments = cell.get("attachments")
            if isinstance(attachments, dict) and attachments:
                warnings.append(WarningRecord(
                    code="ipynb_attachments_ignored",
                    reason=f"cell #{idx} 的 attachments 已忽略",
                    details={"cell_index": idx, "count": len(attachments)},
                ))
            ct = cell.get("cell_type") or "unknown"
            text = _cell_source_to_text(cell.get("source"))
            if text is None:
                # 契约 §5（adoption 修正，2026-08-27）：source 缺失/非 str/list/
                # 列表含非字符串项 → 跳过该 cell + ipynb_bad_cell（注明字段）。
                warnings.append(WarningRecord(
                    code="ipynb_bad_cell",
                    reason=f"cell #{idx} 的 source 字段非法，已跳过",
                    details={"cell_index": idx, "field": "source"},
                ))
                continue
            if ct == "markdown":
                sub_elements, sub_warnings = md_parser._parse_text(text, document_id)
                for w in sub_warnings:
                    warnings.append(WarningRecord(
                        code=w.code,
                        reason=f"cell #{idx} (markdown): {w.reason}",
                        details={**(w.details or {}), "cell_index": idx},
                    ))
                for el in sub_elements:
                    # 契约 §7（adoption 修正，2026-08-27）：attachment: 图片引用
                    # 无法解析为资源 → 跳过该 image element 并诊断，其余照常。
                    if (
                        el.type == "image"
                        and isinstance(el.resource_path, str)
                        and el.resource_path.startswith("attachment:")
                    ):
                        warnings.append(WarningRecord(
                            code="ipynb_attachment_ref_skipped",
                            reason=f"cell #{idx} 的 attachment: 图片引用未解析，已跳过",
                            details={
                                "cell_index": idx,
                                "ref": el.resource_path,
                                "alt": el.metadata.get("alt", ""),
                            },
                        ))
                        continue
                    loc = dict(el.source_locator)
                    # 在 locator 前置 cell 信息
                    new_loc: dict[str, Any] = {
                        "family": "container_line",
                        "cell_index": idx,
                        "cell_type": "markdown",
                    }
                    if "line" in loc:
                        new_loc["line"] = loc["line"]
                    if "section_path" in loc:
                        new_loc["section_path"] = loc["section_path"]
                    raw_elements.append((el.type, el.content, el.resource_path, new_loc, dict(el.metadata)))
            elif ct == "code":
                if not text.strip():
                    warnings.append(WarningRecord(
                        code="ipynb_empty_code_cell",
                        reason=f"cell #{idx} 是空 code cell",
                        details={"cell_index": idx},
                    ))
                    continue
                # 契约 §5（adoption 修正，2026-08-27）：strip() 仅用于判空，
                # 正文保留原始缩进与换行；locator 含 line=1（契约 §8）。
                raw_elements.append((
                    "paragraph",
                    text,
                    None,
                    {"family": "container_line", "cell_index": idx, "cell_type": "code", "line": 1},
                    {"kind": "code_cell", "language": language},
                ))
            elif ct == "raw":
                if not text.strip():
                    continue
                raw_elements.append((
                    "paragraph",
                    text,
                    None,
                    {"family": "container_line", "cell_index": idx, "cell_type": "raw", "line": 1},
                    {"kind": "raw_cell"},
                ))
            else:
                warnings.append(WarningRecord(
                    code="ipynb_unknown_cell_type",
                    reason=f"cell #{idx} 类型未知: {ct!r}",
                    details={"cell_index": idx, "cell_type": ct},
                ))

        # 重新分配 element_id（连续编号）
        elements: list[Element] = []
        for k, (etype, content, resource_path, locator, meta) in enumerate(raw_elements):
            elements.append(Element(
                element_id=f"{document_id}::e{k:04d}",
                type=etype,
                content=content,
                resource_path=resource_path,
                parent_id=None,
                source_locator=locator,
                confidence=0.95,
                metadata=meta,
            ))

        if not elements:
            warnings.append(WarningRecord(
                code="ipynb_no_content",
                reason=".ipynb 未提取到任何 element（空 notebook 或仅含空 cell）",
            ))

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
            metadata={
                "ipynb": True,
                "nbformat": nbformat_major,
                "nbformat_minor": nbformat_minor,
                "cell_count": len(cells),
                "language": language,
            },
        )


__all__ = ["IpynbParser"]
