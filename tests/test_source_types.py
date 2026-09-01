"""批次 20 Phase A 测试：source_type 契约常量、规范化与注册表绑定。

覆盖设计裁决 D3（family 封闭）、D4（声明契约 + normalize + 映射唯一）、
D5/Q1（Document.source_type 放宽为 str、SourceType Literal 保留）。
"""

from __future__ import annotations

import pytest

import app.parser_registry as pr
from app.models import Document, SourceType
from app.parser_registry import ParserRegistrationError, register, source_type_family
from app.parsers.base import Parser
from app.source_types import (
    BUILTIN_SOURCE_TYPE_FAMILIES,
    LOCATOR_FAMILIES,
    ContractViolationError,
    normalize_locator_family,
    normalize_parser_contract,
    normalize_source_type,
)


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    return pr._registry


def _make_parser_cls(name: str, source_types, locator_family=None) -> type[Parser]:
    class _P(Parser):
        def parse(self, path, source_hash):  # pragma: no cover - 测试桩
            raise NotImplementedError

    _P.name = name
    _P.source_types = source_types
    _P.locator_family = locator_family
    return _P


# ---------- D3：family 封闭枚举 ----------

def test_locator_families_closed_set():
    assert LOCATOR_FAMILIES == frozenset(
        {"page_geometry", "structural_index", "line_address", "container_line"}
    )


def test_builtin_source_type_families_mapping():
    assert BUILTIN_SOURCE_TYPE_FAMILIES == {
        "pdf": "page_geometry",
        "docx": "structural_index",
        "markdown": "line_address",
        "html": "line_address",
        "text": "line_address",
        "ipynb": "container_line",
    }


# ---------- normalize_source_type（D4 补充：声明不可漂移） ----------

def test_normalize_source_type_accepts_valid():
    assert normalize_source_type("myx") == "myx"
    assert normalize_source_type("a") == "a"
    assert normalize_source_type("a" + "b" * 31) == "a" + "b" * 31  # 恰 32 字符


@pytest.mark.parametrize(
    "bad",
    [
        None,
        123,
        "",
        " Myx ",   # 首尾空白，拒绝而非静默 strip
        "Myx",     # 大写
        "myX",
        "1abc",    # 数字开头
        "_myx",    # 下划线开头
        "my-x",    # 连字符
        "a" + "b" * 32,  # 33 字符超长
        "a b",
    ],
)
def test_normalize_source_type_rejects(bad):
    with pytest.raises(ContractViolationError):
        normalize_source_type(bad)


# ---------- normalize_locator_family ----------

def test_normalize_locator_family_none_ok():
    assert normalize_locator_family(None) is None


def test_normalize_locator_family_valid_members():
    for fam in ("page_geometry", "structural_index", "line_address", "container_line"):
        assert normalize_locator_family(fam) == fam


@pytest.mark.parametrize(
    "bad", ["", "   ", "line address", "LineAddress", "no_such_family", 5]
)
def test_normalize_locator_family_rejects(bad):
    with pytest.raises(ContractViolationError):
        normalize_locator_family(bad)


# ---------- normalize_parser_contract 组合规则 ----------

def test_contract_builtin_single_type_family_none_ok():
    assert normalize_parser_contract(("pdf",), None) == (("pdf",), None)


def test_contract_str_treated_as_single_tuple():
    assert normalize_parser_contract("markdown", "line_address") == (
        ("markdown",),
        "line_address",
    )


def test_contract_multi_builtin_two_families_none_ok():
    # fallback/kreuzberg 形态：pdf+docx 绑定不同 family，只能声明 None
    assert normalize_parser_contract(("pdf", "docx"), None) == (
        ("pdf", "docx"),
        None,
    )


def test_contract_new_type_requires_family():
    with pytest.raises(ContractViolationError, match="locator_family"):
        normalize_parser_contract(("myx",), None)


def test_contract_new_type_with_family_ok():
    assert normalize_parser_contract(("myx",), "line_address") == (
        ("myx",),
        "line_address",
    )


def test_contract_mixed_new_and_builtin_consistent_ok():
    assert normalize_parser_contract(("myx", "markdown"), "line_address") == (
        ("myx", "markdown"),
        "line_address",
    )


def test_contract_family_conflicts_with_builtin_binding_rejected():
    # pdf 的既有绑定是 page_geometry，声明 line_address 即不一致
    with pytest.raises(ContractViolationError, match="内置类型 pdf"):
        normalize_parser_contract(("pdf",), "line_address")


def test_contract_multi_builtin_with_any_single_family_rejected():
    with pytest.raises(ContractViolationError, match="docx"):
        normalize_parser_contract(("pdf", "docx"), "page_geometry")


def test_contract_empty_declaration_rejected():
    with pytest.raises(ContractViolationError, match="不得为空"):
        normalize_parser_contract((), None)


def test_contract_non_tuple_declaration_rejected():
    with pytest.raises(ContractViolationError, match="str 或 tuple"):
        normalize_parser_contract(42, None)


def test_contract_declares_whitespace_type_rejected():
    with pytest.raises(ContractViolationError):
        normalize_parser_contract((" myx",), "line_address")


# ---------- 注册表集成：强制声明 + 全局唯一绑定 ----------

def test_builtin_import_binds_all_six_type_families():
    for st, fam in BUILTIN_SOURCE_TYPE_FAMILIES.items():
        assert source_type_family(st) == fam


def test_source_type_family_unknown_returns_none():
    assert source_type_family("no_such_type") is None


def test_register_rejects_missing_contract(fresh_registry):
    with pytest.raises(ParserRegistrationError, match="契约声明无效"):
        register(_make_parser_cls("no_contract", ()))


def test_register_rejects_new_type_without_family(fresh_registry):
    with pytest.raises(ParserRegistrationError, match="契约声明无效"):
        register(_make_parser_cls("myx_nofam", ("myx",)))


def test_register_new_type_establishes_global_binding(fresh_registry):
    register(_make_parser_cls("myx_a", ("myx",), "line_address"))
    assert source_type_family("myx") == "line_address"


def test_register_conflicting_family_for_same_type_rejected(fresh_registry):
    register(_make_parser_cls("myx_a", ("myx",), "line_address"))
    with pytest.raises(ParserRegistrationError, match="已全局绑定"):
        register(_make_parser_cls("myx_b", ("myx",), "structural_index"))


def test_register_same_binding_multiple_parsers_ok(fresh_registry):
    # 同 source_type + 同 family 的多 parser 并存合法（如多个 markdown parser）
    register(_make_parser_cls("md_a", ("markdown",), "line_address"))
    register(_make_parser_cls("md_b", ("markdown",), "line_address"))
    assert source_type_family("markdown") == "line_address"


def test_register_multi_format_parser_ok(fresh_registry):
    # fallback 形态：声明两类内置类型 + family=None
    register(_make_parser_cls("multi_fmt", ("pdf", "docx"), None))
    assert source_type_family("pdf") == "page_geometry"
    assert source_type_family("docx") == "structural_index"


# ---------- D5/Q1：Document.source_type 放宽 ----------

def test_document_accepts_extension_source_type():
    doc = Document(
        document_id="doc-x",
        source_path="a.myx",
        source_type="myx",
        source_hash="0" * 64,
        parser_name="myx_test",
        parser_version="test/1.0",
    )
    assert doc.source_type == "myx"
    assert doc.to_dict()["source_type"] == "myx"


def test_source_type_literal_retained():
    # Literal 保留供内置 parser 类型提示（Q1 裁决要求）
    assert set(SourceType.__args__) == {
        "pdf", "docx", "markdown", "html", "text", "ipynb",
    }


def test_parser_base_contract_defaults():
    # 基类默认空声明：register 会拒绝（强制显式声明）
    assert Parser.source_types == ()
    assert Parser.locator_family is None
