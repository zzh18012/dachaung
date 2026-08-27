"""统一文档模型（dataclass）。

业务代码只依赖这里的类型，永远不直接依赖 Kreuzberg / pdfplumber / python-docx 的返回格式。
所有持久化（写 JSON）和校验（Schema）都基于这里的结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

SCHEMA_VERSION = "0.1.0"

ElementType = Literal[
    "heading", "paragraph", "list_item", "table", "image", "caption", "header", "footer"
]
SourceType = Literal["pdf", "docx", "markdown", "html", "text", "ipynb"]


@dataclass
class Element:
    """文档元素：标题 / 段落 / 表格 / 图片等。

    约束（与 document.schema.json 一致）：
    - `content` 与 `resource_path` 至少有一个非空（文本元素走 content，二进制走 resource_path）。
    - `source_locator` 的结构因 `source_type` 而异（PDF: page/bbox；DOCX: paragraph_index 等）。
      Element 自身不强制结构，由 Document 层级的 `source_type` 决定，schema 在 if/then 中校验。
    """

    element_id: str
    type: ElementType
    source_locator: dict[str, Any]
    parent_id: Optional[str] = None
    content: Optional[str] = None
    resource_path: Optional[str] = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.element_id:
            raise ValueError("element_id 不能为空")
        if not (self.content or self.resource_path):
            raise ValueError(
                f"element {self.element_id} 必须至少有 content 或 resource_path"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Chunk:
    """分块：表示一段可以独立检索的文本。

    `source_element_ids` 至少 1 个，确保可追溯到原始 Element。
    `source_spans`（可选）给出每个被引用 element 在其 content 中的字符区间
    `[start, end)`，用于字符级保留验证。空列表表示该 chunk 不带 span 信息
    （向后兼容旧 chunker 输出）。
    """

    chunk_id: str
    text: str
    source_element_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
    source_spans: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.chunk_id:
            raise ValueError("chunk_id 不能为空")
        if not self.source_element_ids:
            raise ValueError(f"chunk {self.chunk_id} 至少要有一个 source_element_id")
        if not self.text:
            raise ValueError(f"chunk {self.chunk_id} 文本不能为空")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # 空 span 不序列化：保证旧 chunker（不带 span）的输出形状不变
        if not d["source_spans"]:
            del d["source_spans"]
        return d


@dataclass
class Relation:
    """元素之间的关系（父子、顺序、引用等）。本阶段主要用于 heading→children。"""

    type: str
    from_id: str
    to_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WarningRecord:
    """非致命问题：降级、字段缺失、可疑解析等。"""

    code: str
    reason: str
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "reason": self.reason}
        if self.details is not None:
            d["details"] = self.details
        return d


@dataclass
class ErrorRecord:
    """致命错误：单文件失败时输出结构化错误而非崩溃。"""

    code: str
    message: str
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            d["details"] = self.details
        return d


@dataclass
class Document:
    """统一文档模型：贯穿解析、分块、校验、输出全流程。"""

    document_id: str
    source_path: str
    source_type: SourceType
    source_hash: str
    parser_name: str
    parser_version: str
    elements: list[Element] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    warnings: list[WarningRecord] = field(default_factory=list)
    errors: list[ErrorRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "document_id": self.document_id,
            "source_path": self.source_path,
            "source_type": self.source_type,
            "source_hash": self.source_hash,
            "parser_name": self.parser_name,
            "parser_version": self.parser_version,
            "elements": [e.to_dict() for e in self.elements],
            "chunks": [c.to_dict() for c in self.chunks],
            "relations": [r.to_dict() for r in self.relations],
            "warnings": [w.to_dict() for w in self.warnings],
            "errors": [er.to_dict() for er in self.errors],
            "metadata": self.metadata,
        }
