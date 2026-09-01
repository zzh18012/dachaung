"""Markdown Enhanced 参考插件（Stage 8 批次 18，Option B 裁决）。

在 MarkdownParser 基础上增加：
- YAML frontmatter（文件头 ``---`` 分隔块）受限解析：仅接受扁平
  ``key: scalar``（可带一层引号）；嵌套 / 列表 / 空值 → 记
  ``frontmatter_*_skipped`` 警告后跳过该键，**不伪装为完整 YAML**
  （完整 YAML + PyYAML 依赖在 docs/BACKLOG.md）。解析出的键值对
  顶层合并进 ``Document.metadata``。
- GFM 任务列表：``- [ ]`` / ``- [x]`` 前缀识别为 list_item 的
  ``metadata.task_item`` / ``metadata.checked``，content 去除标记。

定位：随项目分发的参考/增强插件（内置注册，list-parsers 可见），
同时是"如何写插件"的活样板——外部插件照本文件 import + @register 接入。

已知语义：frontmatter 剥离后 body 的行号相对原文件偏移
（source_locator.line 以 body 为基准）。
"""

from __future__ import annotations

import re
from pathlib import Path

from app.models import Document, WarningRecord
from app.parser_registry import register
from app.parsers.base import Parser, ParserError, make_document_id
from app.parsers.markdown_parser import MarkdownParser

_MD_EXTENSIONS = (".md", ".markdown")

_TASK_ITEM_RE = re.compile(r"^\[( |x|X)\]\s+(.*)$")
_FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z0-9_\-]+):\s*(.*)$")


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    """返回 (frontmatter 块或 None, body)。

    仅当首行为 ``---`` 且存在闭合 ``---`` 行时视作 frontmatter；
    未闭合不当作 frontmatter（原样交给 markdown 解析）。
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1 :])
    return None, text


def _parse_frontmatter(
    block: str, warnings: list[WarningRecord]
) -> dict[str, str]:
    """受限解析：扁平 key: scalar。不合法行/值记警告跳过，不抛异常。"""
    meta: dict[str, str] = {}
    for line_no, raw in enumerate(block.splitlines(), 1):
        line = raw.rstrip()
        if not line.strip():
            continue
        m = _FRONTMATTER_KEY_RE.match(line)
        if not m:
            warnings.append(
                WarningRecord(
                    code="frontmatter_line_skipped",
                    reason=(
                        f"frontmatter 第 {line_no} 行不是扁平 key: value "
                        "形式（嵌套或列表），已跳过"
                    ),
                    details={"line": line_no, "text": line.strip()[:80]},
                )
            )
            continue
        key, value = m.group(1), m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if not value or value[0] in "[{":
            warnings.append(
                WarningRecord(
                    code="frontmatter_value_skipped",
                    reason=(
                        f"frontmatter 键 {key} 的值是列表/映射/空值"
                        "（受限解析仅支持标量），已跳过"
                    ),
                    details={"line": line_no, "key": key},
                )
            )
            continue
        meta[key] = value
    return meta


@register
class MarkdownEnhancedParser(Parser):
    """frontmatter + 任务列表增强的 Markdown 解析器（参考插件）。"""

    name = "markdown_enhanced"
    version = "stdlib/0.1.0"
    supported_extensions = _MD_EXTENSIONS
    priority = 5  # 裁决：优先于 markdown(20)，.md 自动发现选本插件
    source_types = ("markdown",)
    locator_family = "line_address"

    def __init__(self) -> None:
        self._md = MarkdownParser()

    def parse(self, path: str | Path, source_hash: str) -> Document:
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        suffix = p.suffix.lower()
        if suffix not in _MD_EXTENSIONS:
            raise ParserError(
                code="unsupported_type",
                message=(
                    f"Markdown Enhanced 只支持 .md/.markdown，得到 {suffix or '(无)'}"
                ),
                details={"suffix": suffix},
            )
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

        warnings: list[WarningRecord] = []
        fm_block, body = _split_frontmatter(text)
        frontmatter = (
            _parse_frontmatter(fm_block, warnings) if fm_block is not None else {}
        )

        elements, body_warnings = self._md._parse_text(body, document_id)
        warnings.extend(body_warnings)

        for el in elements:
            if el.type == "list_item" and el.content:
                m = _TASK_ITEM_RE.match(el.content)
                if m:
                    el.content = m.group(2)
                    el.metadata["task_item"] = True
                    el.metadata["checked"] = m.group(1).lower() == "x"

        if not elements:
            warnings.append(
                WarningRecord(
                    code="md_no_content",
                    reason="Markdown 文件未提取到任何 element（可能为空文件或仅含 frontmatter）",
                )
            )

        return Document(
            document_id=document_id,
            source_path=str(p),
            source_type="markdown",
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=elements,
            chunks=[],
            relations=[],
            warnings=warnings,
            errors=[],
            metadata={"markdown": True, **frontmatter},
        )


__all__ = ["MarkdownEnhancedParser"]
