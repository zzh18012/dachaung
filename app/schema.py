"""JSON Schema 加载与校验。

业务代码（pipeline / cli）只通过这里的函数校验输出，不直接操作 jsonschema 库。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "document.schema.json"


class SchemaValidationError(Exception):
    """Schema 校验失败时抛出。message 给人看，errors 给程序看。"""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def load_schema(path: Path | str = SCHEMA_PATH) -> dict[str, Any]:
    """从磁盘读取 JSON Schema 文件。每次重新读取，方便测试用临时 schema。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Schema 文件不存在: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(document: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    """校验单个 document dict。失败时抛 SchemaValidationError。

    默认使用打包的 document.schema.json；测试可传入临时 schema。
    """
    sch = schema if schema is not None else load_schema()
    validator = Draft202012Validator(sch)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    if not errors:
        return

    flat: list[dict[str, Any]] = []
    for err in errors:
        flat.append(
            {
                "path": list(err.absolute_path),
                "message": err.message,
                "schema_path": list(err.absolute_schema_path),
            }
        )
    head = errors[0]
    raise SchemaValidationError(
        f"Schema 校验失败 ({len(errors)} 处)：{head.message} @ path={list(head.absolute_path)}",
        errors=flat,
    )


def is_valid(document: dict[str, Any], schema: dict[str, Any] | None = None) -> bool:
    """非抛出版：返回 True/False。用于 cli 友好的判断。"""
    try:
        validate(document, schema)
        return True
    except SchemaValidationError:
        return False


def validate_file(path: Path | str, schema: dict[str, Any] | None = None) -> None:
    """校验磁盘上已有的 JSON 文件。供 `cli --validate` 使用。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"待校验文件不存在: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    validate(data, schema)


__all__ = [
    "SCHEMA_PATH",
    "SchemaValidationError",
    "load_schema",
    "validate",
    "is_valid",
    "validate_file",
]


def _silence_unused_import() -> None:
    """JSValidationError 仅用于类型提示可见性，保留 import。"""
    return None
