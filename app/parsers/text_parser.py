"""纯文本解析器：按空行分段的 minimal parser。

策略：把输入按一行或多多个空行切段，每段（去除首尾空白后）作为一个 paragraph element。

支持的扩展名：``.txt``、``.text``。

source_locator 结构：``{"family": "line_address", "line": N}``，
N 是该段首字符在原文中的 1-indexed 行号（family 见 docs/locator-kvfs-contract.md）。

不做的事（明确放弃）：
- 任何形式的结构识别（无标题、无列表、无表格）
- 字符编码自动检测（强制 utf-8，失败时 errors=replace）
- 行内重排（连续行不会合并；用户怎么写就怎么存）
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.models import Document, Element, WarningRecord
from app.parsers.base import Parser, ParserError, make_document_id

_TEXT_EXTENSIONS = (".txt", ".text")


def _detect_text_source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in _TEXT_EXTENSIONS:
        return "text"
    raise ParserError(
        code="unsupported_type",
        message=f"纯文本解析器只支持 .txt/.text，得到 {suffix or '(无)'}",
        details={"suffix": suffix},
    )


def _split_paragraphs(text: str) -> list[tuple[int, str]]:
    """切分文本为 [(start_line_1based, content), ...]。

    用空行（连续 whitespace-only 行）作为段落分隔。
    """
    if not text:
        return []
    # 归一换行：CRLF / CR → LF
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = norm.split("\n")
    paragraphs: list[tuple[int, str]] = []
    i = 0
    line_no = 1  # 1-indexed 行号，指向 lines[i]
    while i < len(lines):
        # 跳过空白行（仅含 whitespace 的行）
        while i < len(lines) and not lines[i].strip():
            i += 1
            line_no += 1
        if i >= len(lines):
            break
        # 收集连续非空白行
        para_start_line = line_no
        para_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            para_lines.append(lines[i])
            i += 1
            line_no += 1
        content = "\n".join(para_lines).strip()
        if content:
            paragraphs.append((para_start_line, content))
    return paragraphs


class TextParser(Parser):
    """``.txt`` → elements 的最小解析器。"""

    name = "text"
    version = "stdlib/0.1.0"

    def parse(self, path: str | Path, source_hash: str) -> Document:
        p = Path(path)
        if not p.is_file():
            raise ParserError(
                code="file_not_found",
                message=f"输入文件不存在: {p}",
                details={"path": str(p)},
            )
        source_type = _detect_text_source_type(p)
        document_id = make_document_id(source_hash)

        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            raise ParserError(
                code="text_read_failed",
                message=f"读取文本文件失败: {e}",
                details={"exception_type": type(e).__name__},
            ) from e

        elements: list[Element] = []
        warnings: list[WarningRecord] = []
        for start_line, content in _split_paragraphs(text):
            elements.append(
                Element(
                    element_id=f"{document_id}::e{len(elements):04d}",
                    type="paragraph",
                    content=content,
                    parent_id=None,
                    source_locator={"family": "line_address", "line": start_line},
                    confidence=0.95,
                    metadata={},
                )
            )
        if not elements:
            warnings.append(
                WarningRecord(
                    code="text_no_content",
                    reason="文本文件未提取到任何 element（空文件或仅含空白）",
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
            metadata={"text": True},
        )


__all__ = ["TextParser"]
