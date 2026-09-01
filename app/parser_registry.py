"""Parser 注册表（Stage 8 批次 18，Option B 裁决）。

- `register(parser_cls)`：普通调用与装饰器两种写法等价（返回原类）
- `get_parser(name, image_output_dir=None)`：名称 → 实例；未知名
  ValueError（错误语义与旧 pipeline.get_parser 兼容）
- `discover_parser(path)`：扩展名 → 已注册且声明支持该扩展名的 parser
  中 priority 最小者的**名称**（pipeline/CLI 流转以名称为准）；
  无候选 ValueError；同扩展名同 priority 平局 → 先注册者胜 + UserWarning
- `list_parsers()`：按 (priority, name) 排序的元数据表

批次 21 Phase A（capability snapshot）：register() 校验通过后即构建
冻结 `ParserCapability` 快照；registry 一切核心路径（discover / list /
pipeline 契约检查）**只读快照，不再活读 Parser 类属性**——注册后改写
类属性不再影响注册表行为（registered capability is immutable，属
行为收紧修复，非兼容破坏）。快照非公开创作面：插件作者仍以类属性
声明能力（批次 18/19/20 契约零变化）。

批次 21 Phase B（discovery explainability）：`discover_parser_details()`
返回冻结 `DiscoveryResult`（候选列表 + 胜者 + 原因 + 平局说明），与
`discover_parser()` 共用同一决策实现；排序全序 (priority, 注册顺序)，
结果按需派生不缓存——能力唯一来源仍是 `_capabilities` 快照。

内置 parser 在本模块导入时按既有顺序注册；参考插件 markdown_enhanced
随项目分发并注册（定位：随项目分发的参考/增强插件，非第三方外部插件）。
外部插件接入方式：自定义模块 `import` 后 `@register`（不做
entry_points 自动扫描，显式优于隐式）；重名注册 import 时即 ValueError。
"""

from __future__ import annotations

import inspect
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.parsers.base import Parser
from app.source_types import (
    BUILTIN_SOURCE_TYPE_FAMILIES,
    ContractViolationError,
    normalize_parser_contract,
)

_registry: dict[str, type[Parser]] = {}

# 注册时冻结的能力快照（批次 21 Phase A）：核心路径唯一读取来源
_capabilities: dict[str, ParserCapability] = {}

# source_type → locator family 的全局唯一绑定（批次 20 D4）：
# 首个声明该类型的 parser 建立绑定，后注册者绑定不同 family 即拒绝
_source_type_families: dict[str, str] = {}


class ParserRegistrationError(ValueError):
    """register() 的缺名/重名等注册失败专用（ValueError 子类，向后兼容）。

    批次 19：plugin_loader 仅将本异常映射为 plugin_register_failed；
    插件模块顶层其他 ValueError 一律归为 plugin_import_failed。

    批次 21：能力声明非法（extensions/priority/version 格式不符）同抛
    本异常（顶层错误码不新增，details 级差异由错误文本标明字段名）。
    """


@dataclass(frozen=True)
class ParserCapability:
    """register() 时冻结的 parser 能力快照（批次 21 Phase A，D1 裁决 B）。

    六字段（GPT 批准）：name / source_types / locator_family /
    extensions / priority / version。extensions 是**输入能力**（能吃什么
    文件），source_types + locator_family 是**输出契约**（产出什么形状，
    D2：两轴独立，不建立 extension → source_type 固定映射）。
    registry 核心路径（discover / list / pipeline 契约检查）只读本快照。
    """

    name: str
    source_types: tuple[str, ...]
    locator_family: str | None
    extensions: tuple[str, ...]
    priority: int
    version: str


def _validated_extensions(parser_cls: type[Parser]) -> tuple[str, ...]:
    """归一并校验 supported_extensions：str 视为单元素（与 source_types
    同规），仅接受 tuple/list 容器；元素必须是小写、以点开头、长度 ≥ 2
    的字符串（如 ".md"）。非法即 ParserRegistrationError。
    """
    raw = getattr(parser_cls, "supported_extensions", ())
    if isinstance(raw, str):
        items = (raw,)
    elif isinstance(raw, (tuple, list)):
        items = tuple(raw)
    else:
        raise ParserRegistrationError(
            f"{parser_cls.__name__}.supported_extensions 必须是 str 或"
            f" str 元组，得到 {type(raw).__name__}"
        )
    for ext in items:
        if (
            not isinstance(ext, str)
            or len(ext) < 2
            or not ext.startswith(".")
            or ext != ext.lower()
        ):
            raise ParserRegistrationError(
                f"{parser_cls.__name__}.supported_extensions 元素非法:"
                f" {ext!r}（须为小写、点开头、长度≥2，如 '.md'）"
            )
    return items


def _validated_priority(parser_cls: type[Parser]) -> int:
    raw = getattr(parser_cls, "priority", 100)
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 1:
        raise ParserRegistrationError(
            f"{parser_cls.__name__}.priority 必须为正整数（小者优先），"
            f"得到 {raw!r}"
        )
    return raw


def _validated_version(parser_cls: type[Parser]) -> str:
    raw = getattr(parser_cls, "version", "")
    if not isinstance(raw, str) or not raw:
        raise ParserRegistrationError(
            f"{parser_cls.__name__}.version 必须为非空字符串"
        )
    return raw


def register(parser_cls: type[Parser]) -> type[Parser]:
    """注册 parser 类；兼作装饰器。重名/缺名/契约声明非法均抛
    ParserRegistrationError（显式失败优于静默）。

    批次 20：注册时强制校验 (source_types, locator_family) 契约组合，
    并维护 source_type → family 的全局唯一绑定（首个声明者建立绑定，
    后续不同绑定即拒绝；同绑定多 parser 并存合法，如多个 markdown parser）。

    批次 21 Phase A：校验通过后构建冻结 ParserCapability 快照存入
    _capabilities；此后核心路径只读快照（注册后改写类属性不再生效）。
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
    extensions = _validated_extensions(parser_cls)
    priority = _validated_priority(parser_cls)
    version = _validated_version(parser_cls)
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
    _capabilities[name] = ParserCapability(
        name=name,
        source_types=declared_types,
        locator_family=_family,
        extensions=extensions,
        priority=priority,
        version=version,
    )
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


@dataclass(frozen=True)
class DiscoveryCandidate:
    """发现候选（批次 21 Phase B）：按决策序 (priority, 注册顺序) 排列。

    registration_order 是 _capabilities 的插入序号（0 起）——同 priority
    平局时的先注册者胜依据，使选择完全可解释、可复现。
    """

    name: str
    priority: int
    registration_order: int


@dataclass(frozen=True)
class DiscoveryResult:
    """扩展名发现的完整解释（批次 21 Phase B，D3 裁决）。

    只读诊断（winner/reason/candidates），按需从 _capabilities 派生、
    不缓存（能力唯一来源仍是 _capabilities 快照）。本结果不发
    UserWarning——告警是 discover_parser 决策路径的行为，诊断只陈述。
    """

    extension: str
    candidates: tuple[DiscoveryCandidate, ...]  # 已按 (priority, 注册序) 排序
    winner: str | None  # 无候选时 None
    reason: str
    tied_names: tuple[str, ...]  # 真实平局（最优 priority 多候选）时的候选名（含胜者，注册序）；无平局为空

    @property
    def resolved(self) -> bool:
        return self.winner is not None


def discover_parser_details(path: str | Path) -> DiscoveryResult:
    """扩展名 → 完整发现解释（候选列表 + 胜者 + 原因）。

    与 discover_parser 同一决策实现（后者委托本函数）；排序全序
    (priority, 注册顺序)，确定性可复现。无候选不抛异常——返回
    winner=None 的结果（诊断用途，调用方自行陈述）。
    """
    ext = Path(path).suffix.lower()
    candidates = tuple(
        sorted(
            (
                DiscoveryCandidate(
                    name=name, priority=cap.priority, registration_order=idx
                )
                for idx, (name, cap) in enumerate(_capabilities.items())
                if ext in cap.extensions
            ),
            key=lambda c: (c.priority, c.registration_order),
        )
    )
    if not candidates:
        return DiscoveryResult(
            extension=ext,
            candidates=(),
            winner=None,
            reason=f"无已注册 parser 支持扩展名 {ext or '(无)'}",
            tied_names=(),
        )
    winner = candidates[0]
    at_best = [c.name for c in candidates if c.priority == winner.priority]
    # 仅真实平局（最优 priority 有多个候选）才非空；单候选不成"平局"，
    # 否则 discover_parser 的告警条件会误触发
    tied_names = tuple(at_best) if len(at_best) > 1 else ()
    if len(candidates) == 1:
        reason = (
            f"扩展名 {ext} 唯一候选 {winner.name}"
            f"（priority={winner.priority}）"
        )
    elif tied_names:
        reason = (
            f"扩展名 {ext} 共 {len(candidates)} 个候选，priority 最小"
            f" {winner.priority} 平局: {', '.join(tied_names)}；"
            f"先注册者 {winner.name} 胜（registration_order="
            f"{winner.registration_order}）"
        )
    else:
        runner = candidates[1]
        reason = (
            f"扩展名 {ext} 共 {len(candidates)} 个候选，priority 最小者 "
            f"{winner.name}（{winner.priority} < {runner.priority}）"
        )
    return DiscoveryResult(
        extension=ext,
        candidates=candidates,
        winner=winner.name,
        reason=reason,
        tied_names=tied_names,
    )


def discover_parser(path: str | Path) -> str:
    """扩展名 → priority 最小的已注册 parser 名称。

    返回 str（非 Parser 实例）；实例化统一走 get_parser(name)。
    显式 --parser 永远覆盖本发现。平局（同扩展名同 priority）取先
    注册者并发 UserWarning。

    批次 21 Phase A：候选集与排序只读 _capabilities 快照（注册后改写
    类属性不影响发现结果）。
    批次 21 Phase B：决策逻辑委托 discover_parser_details（唯一实现，
    防止两份决策来源漂移）；本函数保持原返回值与告警行为不变。
    """
    result = discover_parser_details(path)
    if result.winner is None:
        raise ValueError(
            f"无已注册 parser 支持扩展名 {result.extension or '(无)'}"
        )
    if result.tied_names:
        warnings.warn(
            f"扩展名 {result.extension} 存在多个同优先级"
            f"({result.candidates[0].priority}) parser: "
            f"{', '.join(result.tied_names)}；取先注册的 {result.winner}",
            stacklevel=2,
        )
    return result.winner


def list_parsers() -> list[dict[str, Any]]:
    """按 (priority, name) 排序的已注册 parser 元数据表（读快照）。"""
    return [
        {
            "name": cap.name,
            "priority": cap.priority,
            "extensions": list(cap.extensions),
            "version": cap.version,
            "source_types": list(cap.source_types),
            "locator_family": cap.locator_family,
        }
        for cap in sorted(
            _capabilities.values(), key=lambda c: (c.priority, c.name)
        )
    ]


def registered_names() -> list[str]:
    """当前已注册 parser 名称快照（plugin_loader 用于加载前后 diff）。"""
    return sorted(_registry)


def declared_source_types(parser_cls: type[Parser]) -> tuple[str, ...]:
    """读取 parser 注册时冻结的 source_types 快照（批次 21 Phase A）。

    供 pipeline 契约检查（批次 20 Phase C）以注册口径读取；注册后改写
    类属性不再改变此结果。未注册的类没有快照——显式失败优于静默
    活读（ParserRegistrationError）。
    """
    cap = _capabilities.get(getattr(parser_cls, "name", None))
    if cap is None:
        raise ParserRegistrationError(
            f"{parser_cls.__name__}（name="
            f"{getattr(parser_cls, 'name', None)!r}）未注册，无能力快照；"
            f"能力读取只针对已注册 parser"
        )
    return cap.source_types


def capability(parser_cls_or_name: type[Parser] | str) -> ParserCapability:
    """名称或类 → 冻结能力快照（诊断/测试用；未注册即显式失败）。"""
    name = (
        parser_cls_or_name
        if isinstance(parser_cls_or_name, str)
        else getattr(parser_cls_or_name, "name", None)
    )
    cap = _capabilities.get(name)
    if cap is None:
        raise ParserRegistrationError(
            f"parser 未注册，无能力快照: {name!r}"
        )
    return cap


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
    "DiscoveryCandidate",
    "DiscoveryResult",
    "ParserCapability",
    "capability",
    "declared_source_types",
    "discover_parser",
    "discover_parser_details",
    "get_parser",
    "list_parsers",
    "register",
]
