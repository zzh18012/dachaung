"""source_type 契约：常量、规范化与一致性校验（Stage 8 批次 20）。

分层（批次 20 设计裁决 D1）：
- schema 层（document.schema.json 0.6.0 分支）：source_type pattern +
  locator family 封闭枚举 + family 驱动的 locator 形状校验。
- 运行时层（本模块 + parser_registry）：声明规范化、类型→family 全局
  唯一绑定、parse 路径的契约一致性检查。

locator family 本批封闭（D3）：不新增 family；新 family 需独立批次。
"""

from __future__ import annotations

import re

SOURCE_TYPE_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"

SOURCE_TYPE_RE = re.compile(SOURCE_TYPE_PATTERN)

LOCATOR_FAMILIES: frozenset[str] = frozenset(
    {"page_geometry", "structural_index", "line_address", "container_line"}
)

BUILTIN_SOURCE_TYPE_FAMILIES: dict[str, str] = {
    "pdf": "page_geometry",
    "docx": "structural_index",
    "markdown": "line_address",
    "html": "line_address",
    "text": "line_address",
    "ipynb": "container_line",
}


class ContractViolationError(ValueError):
    """契约声明不合法（规范化/一致性失败）。register() 包装为
    ParserRegistrationError，plugin_loader 归入 plugin_register_failed。"""


def normalize_source_type(value: object) -> str:
    """校验单个 source_type 声明并原样返回。

    规则（D4 裁决补充：声明字段必须不可漂移）：
    - 必须是 str，非 None / 非空；
    - 首尾不得含空白（拒绝 " Myx " 这类隐性差异，不做静默 strip）；
    - 满足 ^[a-z][a-z0-9_]{0,31}$（Q2 裁决：小写字母开头，最长 32）。
    """
    if not isinstance(value, str):
        raise ContractViolationError(
            f"source_type 必须是 str，得到 {type(value).__name__}"
        )
    if not value:
        raise ContractViolationError("source_type 不得为空字符串")
    if value != value.strip():
        raise ContractViolationError(
            f"source_type 首尾含空白: {value!r}（声明必须已是规范形式）"
        )
    if not SOURCE_TYPE_RE.fullmatch(value):
        raise ContractViolationError(
            f"source_type 不符合 pattern {SOURCE_TYPE_PATTERN}: {value!r}"
        )
    return value


def normalize_locator_family(value: object) -> str | None:
    """校验 locator_family 声明；None 合法（表示不声明，见组合规则）。"""
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ContractViolationError(
            f"locator_family 必须是非空 str 或 None，得到 {value!r}"
        )
    if value != value.strip():
        raise ContractViolationError(
            f"locator_family 首尾含空白: {value!r}"
        )
    if value not in LOCATOR_FAMILIES:
        raise ContractViolationError(
            f"locator_family 必须属于封闭枚举 {sorted(LOCATOR_FAMILIES)}: {value!r}"
        )
    return value


def normalize_parser_contract(
    source_types: object, locator_family: object
) -> tuple[tuple[str, ...], str | None]:
    """规范化 parser 的 (source_types, locator_family) 声明组合。

    组合规则（D4 裁决）：
    - source_types：str 视为单元素 tuple；tuple/list 逐项规范化；
      空声明非法（契约强制声明）。
    - locator_family：None 仅当声明全部是内置类型时合法；声明包含新
      类型时必须给出且属于封闭枚举。
    - 一致性：locator_family 非 None 时，必须等于每个已声明内置类型
      的既有 family 绑定（如 ("pdf","docx") 与任何单值 family 都不相容）。

    返回 (规范化类型 tuple, family)；失败抛 ContractViolationError。
    """
    if isinstance(source_types, str):
        raw: tuple[object, ...] = (source_types,)
    elif isinstance(source_types, (tuple, list)):
        raw = tuple(source_types)
    else:
        raise ContractViolationError(
            "source_types 必须是 str 或 tuple/list of str，得到 "
            f"{type(source_types).__name__}"
        )
    if not raw:
        raise ContractViolationError(
            "source_types 声明不得为空（契约强制声明：parser 必须声明其产出的 source_type 集合）"
        )
    types = tuple(normalize_source_type(t) for t in raw)

    family = normalize_locator_family(locator_family)

    new_types = [t for t in types if t not in BUILTIN_SOURCE_TYPE_FAMILIES]
    if new_types and family is None:
        raise ContractViolationError(
            f"声明包含非内置 source_type {new_types}，必须同时声明 locator_family（四选一: {sorted(LOCATOR_FAMILIES)}）"
        )
    if family is not None:
        for t in types:
            builtin = BUILTIN_SOURCE_TYPE_FAMILIES.get(t)
            if builtin is not None and builtin != family:
                raise ContractViolationError(
                    f"locator_family={family} 与内置类型 {t} 的既有绑定 "
                    f"{builtin} 不一致（内置绑定不可改）"
                )
    return types, family
