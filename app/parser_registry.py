"""Parser 注册表（Stage 8 批次 18，Option B 裁决）。

- `register(parser_cls)`：普通调用与装饰器两种写法等价（返回原类）
- `get_parser(name, image_output_dir=None)`：名称 → 实例；未知名
  ValueError（错误语义与旧 pipeline.get_parser 兼容）
- `discover_parser(path)`：扩展名 → 已注册且声明支持该扩展名的 parser
  中 priority 最小者的**名称**（pipeline/CLI 流转以名称为准）；
  无候选 ValueError；同扩展名同 priority 平局 → 先注册者胜 + UserWarning
- `list_parsers()`：按 (priority, name) 排序的元数据表

内置 parser 在本模块导入时按既有顺序注册；参考插件 markdown_enhanced
随项目分发并注册（定位：随项目分发的参考/增强插件，非第三方外部插件）。
外部插件接入方式：自定义模块 `import` 后 `@register`（不做
entry_points 自动扫描，显式优于隐式）；重名注册 import 时即 ValueError。
"""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path
from typing import Any

from app.parsers.base import Parser
from app.source_types import (
    BUILTIN_SOURCE_TYPE_FAMILIES,
    ContractViolationError,
    normalize_parser_contract,
)

_registry: dict[str, type[Parser]] = {}

# source_type → locator family 的全局唯一绑定（批次 20 D4）：
# 首个声明该类型的 parser 建立绑定，后注册者绑定不同 family 即拒绝
_source_type_families: dict[str, str] = {}


class ParserRegistrationError(ValueError):
    """register() 的缺名/重名等注册失败专用（ValueError 子类，向后兼容）。

    批次 19：plugin_loader 仅将本异常映射为 plugin_register_failed；
    插件模块顶层其他 ValueError 一律归为 plugin_import_failed。
    """


def register(parser_cls: type[Parser]) -> type[Parser]:
    """注册 parser 类；兼作装饰器。重名/缺名/契约声明非法均抛
    ParserRegistrationError（显式失败优于静默）。

    批次 20：注册时强制校验 (source_types, locator_family) 契约组合，
    并维护 source_type → family 的全局唯一绑定（首个声明者建立绑定，
    后续不同绑定即拒绝；同绑定多 parser 并存合法，如多个 markdown parser）。
    """
    name = getattr(parser_cls, "name", None)
    if not name or name == "abstract":
        raise ParserRegistrationError(
            f"{parser_cls.__name__} 必须定义非 'abstract' 的 name 类属性"
        )
    if name in _registry:
        raise ParserRegistrationError(
            f"parser 重名注册: {name}（已注册: {_registry[name].__qualname__}）"
        )
    try:
        declared_types, _family = normalize_parser_contract(
            getattr(parser_cls, "source_types", ()),
            getattr(parser_cls, "locator_family", None),
        )
    except ContractViolationError as e:
        raise ParserRegistrationError(
            f"{parser_cls.__name__} 契约声明无效: {e}"
        ) from e
    for st in declared_types:
        binding = BUILTIN_SOURCE_TYPE_FAMILIES.get(st) or _family
        existing = _source_type_families.get(st)
        if existing is not None and existing != binding:
            raise ParserRegistrationError(
                f"source_type '{st}' 已全局绑定 locator family "
                f"'{existing}'，{parser_cls.__name__} 声明 '{binding}'"
                f"（类型→family 唯一，先注册者胜）"
            )
    _registry[name] = parser_cls
    for st in declared_types:
        binding = BUILTIN_SOURCE_TYPE_FAMILIES.get(st) or _family
        _source_type_families.setdefault(st, binding)
    return parser_cls


def _instantiate(
    cls: type[Parser], image_output_dir: Path | str | None
) -> Parser:
    params = inspect.signature(cls.__init__).parameters
    if image_output_dir is not None and "image_output_dir" in params:
        return cls(image_output_dir=image_output_dir)
    return cls()


def get_parser(name: str, image_output_dir: Path | str | None = None) -> Parser:
    """名称 → parser 实例。image_output_dir 仅传给接受该参数的构造器。"""
    if name not in _registry:
        raise ValueError(f"未知 parser: {name}（支持: {', '.join(_registry)}）")
    return _instantiate(_registry[name], image_output_dir)


def discover_parser(path: str | Path) -> str:
    """扩展名 → priority 最小的已注册 parser 名称。

    返回 str（非 Parser 实例）；实例化统一走 get_parser(name)。
    显式 --parser 永远覆盖本发现。平局（同扩展名同 priority）取先
    注册者并发 UserWarning。
    """
    ext = Path(path).suffix.lower()
    candidates = [
        (cls.priority, name)
        for name, cls in _registry.items()
        if ext in cls.supported_extensions
    ]
    if not candidates:
        raise ValueError(f"无已注册 parser 支持扩展名 {ext or '(无)'}")
    best = min(p for p, _ in candidates)
    tied = [name for p, name in candidates if p == best]
    if len(tied) > 1:
        warnings.warn(
            f"扩展名 {ext} 存在多个同优先级({best}) parser: "
            f"{', '.join(tied)}；取先注册的 {tied[0]}",
            stacklevel=2,
        )
    return tied[0]


def list_parsers() -> list[dict[str, Any]]:
    """按 (priority, name) 排序的已注册 parser 元数据表。"""
    return [
        {
            "name": name,
            "priority": cls.priority,
            "extensions": list(cls.supported_extensions),
            "version": cls.version,
            "source_types": list(cls.source_types),
            "locator_family": cls.locator_family,
        }
        for name, cls in sorted(
            _registry.items(), key=lambda kv: (kv[1].priority, kv[0])
        )
    ]


def registered_names() -> list[str]:
    """当前已注册 parser 名称快照（plugin_loader 用于加载前后 diff）。"""
    return sorted(_registry)


def source_type_family(source_type: str) -> str | None:
    """source_type → locator family 绑定查询（内置映射优先，其次注册表）。

    供 pipeline 契约一致性检查（批次 20 Phase C）与测试使用。
    未知类型返回 None。
    """
    if source_type in BUILTIN_SOURCE_TYPE_FAMILIES:
        return BUILTIN_SOURCE_TYPE_FAMILIES[source_type]
    return _source_type_families.get(source_type)


def _register_builtins() -> None:
    # 顺序即注册顺序：决定错误信息列举顺序与 priority 平局的先注册者
    from app.parsers.fallback_parser import FallbackParser
    from app.parsers.html_parser import HtmlParser
    from app.parsers.ipynb_parser import IpynbParser
    from app.parsers.kreuzberg_parser import KreuzbergParser
    from app.parsers.markdown_parser import MarkdownParser
    from app.parsers.text_parser import TextParser

    register(FallbackParser)
    register(KreuzbergParser)
    register(MarkdownParser)
    register(HtmlParser)
    register(TextParser)
    register(IpynbParser)
    # 插件经类上的 @register 装饰器在 import 时自注册（外部插件同款接入
    # 方式）；import 置于内置显式注册之后，保持注册顺序 = 内置在前
    import app.parsers.plugins.markdown_enhanced  # noqa: F401


_register_builtins()


__all__ = [
    "discover_parser",
    "get_parser",
    "list_parsers",
    "register",
]
