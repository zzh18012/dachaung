"""加载并校验本阶段三个新 Schema：manifest / annotation / evaluation-report。

不与 app/schema.py 复用，因为它们的 Schema 路径、错误类型用途都不同
（业务输出 vs 评测元数据），分开更清晰。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


class EvalSchemaError(Exception):
    """Schema 校验失败时抛出。errors 给程序看，message 给人看。"""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.errors = errors or []


def _schema_path(name: str) -> Path:
    p = SCHEMAS_DIR / name
    if not p.is_file():
        raise FileNotFoundError(f"Schema 文件不存在: {p}")
    return p


def load_schema(name: str) -> dict[str, Any]:
    """从 schemas/ 目录加载命名 Schema（如 'manifest.schema.json'）。"""
    with _schema_path(name).open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(instance: dict[str, Any], schema_name: str) -> None:
    """校验 instance dict 是否符合命名 Schema。失败抛 EvalSchemaError。"""
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
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
    raise EvalSchemaError(
        f"Schema '{schema_name}' 校验失败 ({len(errors)} 处)："
        f"{head.message} @ path={list(head.absolute_path)}",
        errors=flat,
    )


def validate_file(path: Path | str, schema_name: str) -> None:
    """加载磁盘 JSON 并按命名 Schema 校验。"""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"待校验文件不存在: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    validate(data, schema_name)


__all__ = [
    "SCHEMAS_DIR",
    "EvalSchemaError",
    "load_schema",
    "validate",
    "validate_file",
]
