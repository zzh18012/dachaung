"""批次 21 Phase A 测试：ParserCapability 冻结快照。

裁决 D1（Option B）核心要求：快照建立后 registry 核心路径（discover /
list / pipeline 契约检查）不得再读 Parser 类属性——GPT 给出的状态漂移
场景（注册后改写 priority/source_types）必须被快照拦截。
另覆盖 register() 新增的能力声明校验（extensions/priority/version）。
"""

from __future__ import annotations

import pytest

import app.parser_registry as pr
from app.parser_registry import (
    ParserCapability,
    capability,
    declared_source_types,
    discover_parser,
    get_parser,
    list_parsers,
    register,
)
from app.parsers.base import Parser


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    monkeypatch.setattr(pr, "_capabilities", dict(pr._capabilities))
    return pr._capabilities


def _make_parser_cls(name: str, exts=(".t1",), priority: int = 50,
                     source_types=("text",), locator_family="line_address",
                     version: str = "test/1.0") -> type[Parser]:
    class _P(Parser):
        def parse(self, path, source_hash):  # pragma: no cover - 测试桩
            raise NotImplementedError

    _P.name = name
    _P.supported_extensions = exts
    _P.priority = priority
    _P.source_types = source_types
    _P.locator_family = locator_family
    _P.version = version
    return _P


# ---------- 快照存在性与六字段 ----------

def test_capability_snapshot_six_fields(fresh_registry):
    register(_make_parser_cls("cap_fields"))
    cap = capability("cap_fields")
    assert isinstance(cap, ParserCapability)
    assert cap.name == "cap_fields"
    assert cap.source_types == ("text",)
    assert cap.locator_family == "line_address"
    assert cap.extensions == (".t1",)
    assert cap.priority == 50
    assert cap.version == "test/1.0"


def test_capability_frozen(fresh_registry):
    register(_make_parser_cls("cap_frozen"))
    cap = capability("cap_frozen")
    with pytest.raises(Exception):
        cap.priority = 1  # type: ignore[misc]


def test_capability_lookup_by_class_or_name(fresh_registry):
    cls = _make_parser_cls("cap_lookup")
    register(cls)
    assert capability(cls) is capability("cap_lookup")


def test_capability_unregistered_name_raises(fresh_registry):
    with pytest.raises(pr.ParserRegistrationError, match="未注册"):
        capability("never_registered")
    with pytest.raises(pr.ParserRegistrationError, match="未注册"):
        declared_source_types(_make_parser_cls("never_registered"))


# ---------- 防漂移（GPT 裁决的核心场景） ----------

def test_post_registration_priority_mutation_ignored(fresh_registry):
    """GPT 给出的漂移场景：注册后改 priority 不得影响 discover。"""
    cls = _make_parser_cls("drift_a", (".drift",), priority=100)
    register(cls)
    cls.priority = 1  # 注册后改写——快照必须不认
    assert capability("drift_a").priority == 100
    # 另一个 priority 更小的 parser 仍应胜出
    register(_make_parser_cls("drift_b", (".drift",), priority=20))
    assert discover_parser("x.drift") == "drift_b"


def test_post_registration_extensions_mutation_ignored(fresh_registry):
    cls = _make_parser_cls("drift_ext", (".d1",))
    register(cls)
    cls.supported_extensions = (".d2",)
    assert capability("drift_ext").extensions == (".d1",)
    with pytest.raises(ValueError, match="无已注册 parser"):
        discover_parser("x.d2")


def test_post_registration_source_types_mutation_ignored(fresh_registry):
    """pipeline 契约检查读快照：注册后改 source_types 声明不得生效。"""
    cls = _make_parser_cls("drift_types", source_types=("text",))
    register(cls)
    cls.source_types = ("html",)
    assert declared_source_types(cls) == ("text",)
    row = next(r for r in list_parsers() if r["name"] == "drift_types")
    assert row["source_types"] == ["text"]


def test_post_registration_version_mutation_ignored(fresh_registry):
    cls = _make_parser_cls("drift_ver", version="orig/1")
    register(cls)
    cls.version = "hacked/9"
    assert capability("drift_ver").version == "orig/1"
    assert next(
        r for r in list_parsers() if r["name"] == "drift_ver"
    )["version"] == "orig/1"


# ---------- 声明校验（D5：不新增顶层错误码） ----------

def test_extensions_validation_rejects_bad_forms(fresh_registry):
    for bad in ((".MD",), ("md",), ("m",), ("",), (".md", 42), 42, {".md"}):
        with pytest.raises(pr.ParserRegistrationError):
            register(
                _make_parser_cls("bad_ext", exts=bad)
            )


def test_extensions_str_accepted_as_single(fresh_registry):
    """str 声明视为单元素（与批次 20 source_types 同规）。"""
    register(_make_parser_cls("str_ext", exts=".t9"))
    assert capability("str_ext").extensions == (".t9",)


def test_extensions_list_accepted_normalized_to_tuple(fresh_registry):
    register(_make_parser_cls("list_ext", exts=[".la", ".lb"]))
    assert capability("list_ext").extensions == (".la", ".lb")


def test_priority_validation_rejects_non_positive(fresh_registry):
    for bad in (0, -5, True, "10", 1.5, None):
        with pytest.raises(pr.ParserRegistrationError):
            register(_make_parser_cls("bad_pri", priority=bad))


def test_version_validation_rejects_empty(fresh_registry):
    for bad in ("", None, 42):
        with pytest.raises(pr.ParserRegistrationError):
            register(_make_parser_cls("bad_ver", version=bad))


def test_registration_error_is_value_error_subclass(fresh_registry):
    """批次 19 映射依赖：ParserRegistrationError 仍是 ValueError，
    plugin_loader 归类 plugin_register_failed 不变。"""
    with pytest.raises(ValueError):
        register(_make_parser_cls("still_ve", priority=0))


# ---------- 兼容性：既有行为零变化 ----------

def test_discover_semantics_unchanged_on_builtins():
    assert discover_parser("x.md") == "markdown_enhanced"
    assert discover_parser("x.pdf") == "fallback"
    assert discover_parser("x.docx") == "fallback"
    assert discover_parser("x.html") == "html"
    assert discover_parser("x.txt") == "text"
    assert discover_parser("x.ipynb") == "ipynb"


def test_list_parsers_row_shape_unchanged():
    rows = {r["name"]: r for r in list_parsers()}
    assert set(rows["fallback"].keys()) == {
        "name", "priority", "extensions", "version",
        "source_types", "locator_family",
    }
    assert rows["fallback"]["extensions"] == [".pdf", ".docx"]
    assert rows["fallback"]["source_types"] == ["pdf", "docx"]
    assert rows["fallback"]["locator_family"] is None
    assert rows["markdown_enhanced"]["priority"] == 5
    assert rows["markdown"]["source_types"] == ["markdown"]
    assert rows["markdown"]["locator_family"] == "line_address"


def test_get_parser_still_instantiates_classes(fresh_registry):
    register(_make_parser_cls("inst_me"))
    assert isinstance(get_parser("inst_me"), Parser)


def test_priority_tie_registration_order_preserved(fresh_registry):
    register(_make_parser_cls("tie_a", (".tie21",), priority=7))
    register(_make_parser_cls("tie_b", (".tie21",), priority=7))
    with pytest.warns(UserWarning, match="同优先级"):
        assert discover_parser("x.tie21") == "tie_a"
