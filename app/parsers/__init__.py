"""解析器子包。

业务代码只依赖这里的 `Parser` 抽象基类，
具体实现（Kreuzberg / Fallback）通过依赖注入或工厂选择。
"""

from __future__ import annotations

from .base import Parser, ParserError, make_document_id

__all__ = ["Parser", "ParserError", "make_document_id"]
