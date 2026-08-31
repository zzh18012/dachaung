"""解析器抽象接口。

业务代码（pipeline、cli）只 import 这个文件，永远不直接依赖 kreuzberg/pdfplumber/python-docx。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Literal

from app.models import Document, SourceType


class ParserError(Exception):
    """所有解析器失败的统一异常。

    `code` 是机器可读的错误码（如 'file_not_found'、'unsupported_type'），
    `details` 是可选的额外信息，会被 pipeline 透传到输出 JSON 的 errors 数组。
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def make_document_id(source_hash: str) -> str:
    """由源文件 SHA-256 派生稳定的 document_id。

    取前 16 个 hex 字符（64 bit）够区分原型阶段的样本。
    """
    if len(source_hash) != 64:
        raise ValueError(f"source_hash 长度异常: {len(source_hash)}")
    return f"doc-{source_hash[:16]}"


def detect_source_type(path: str | Path) -> SourceType:
    """根据扩展名判定 source_type。

    Pipeline 在调用 parser 之前用这个函数，避免每个 parser 重复实现。
    """
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    raise ParserError(
        code="unsupported_type",
        message=f"不支持的文件扩展名: {suffix or '(无)'}，仅支持 .pdf / .docx",
        details={"suffix": suffix},
    )


class Parser(ABC):
    """所有解析器的抽象接口。

    子类必须设置 `name` 和 `version` 类属性，并实现 `parse`。
    parse 返回的 Document 应当：
    - 包含完整的 elements
    - chunks 留空（由 chunker 在后续步骤填充）
    - warnings 记录降级、缺字段等情况

    批次 18 注册表元数据：
    - `supported_extensions`：声明支持的扩展名（小写含点）；空 tuple =
      不参与扩展名自动发现（只能显式 --parser 指定）
    - `priority`：自动发现时数值越小越优先；平局先注册者胜
    """

    name: str = "abstract"
    version: str = "0.0.0"
    supported_extensions: tuple[str, ...] = ()
    priority: int = 100

    @abstractmethod
    def parse(self, path: str | Path, source_hash: str) -> Document:
        """解析文件，返回带 elements 的 Document（chunks 留空）。

        Args:
            path: 输入文件路径
            source_hash: 调用方预先算好的 SHA-256 hex（64 字符）

        Raises:
            ParserError: 解析失败（文件不存在、格式错误、库异常等）
        """
        raise NotImplementedError


__all__ = ["Parser", "ParserError", "make_document_id", "detect_source_type"]


def _silence_unused() -> None:
    """保留 Literal / SourceType 引用，便于类型检查器看到。"""
    _t: type[SourceType] = type  # noqa: F841
    _u: type[Literal["pdf", "docx"]] = type  # noqa: F841
