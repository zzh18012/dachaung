"""schema 校验小工具：避免 evaluation.metrics 与 app.schema 之间产生 import 循环。"""

from __future__ import annotations

from typing import Any


def document_passes_schema(document: dict[str, Any]) -> bool:
    """用 app.schema.is_valid 校验 document dict。"""
    from app.schema import is_valid  # 延迟 import

    return bool(is_valid(document))


__all__ = ["document_passes_schema"]
