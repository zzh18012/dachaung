"""批次 20 Phase C 测试：pipeline 运行时契约检查。

process_single 在 schema 校验之后、写盘之前验证：
- 产出 source_type ∈ parser 声明的 source_types；
- 每个 element 的 locator.family == 该 source_type 的全局绑定。

失败 → 结构化错误 parser_contract_mismatch + 不写盘（schema 已放行
的"合法但违背声明"产出在此拦截）。
"""

from __future__ import annotations

import pytest

import app.parser_registry as pr
from app.models import Document, Element
from app.parser_registry import declared_source_types, list_parsers, register
from app.parsers.base import Parser
from app.pipeline import process_single


@pytest.fixture
def fresh_registry(monkeypatch):
    monkeypatch.setattr(pr, "_registry", dict(pr._registry))
    monkeypatch.setattr(pr, "_source_type_families", dict(pr._source_type_families))
    return pr._registry


class _StubParser(Parser):
    """产出可控的桩 parser：默认声明 text 并如实产出。"""

    name = "stub_contract"
    version = "test/1.0"
    supported_extensions = (".txt",)
    priority = 1
    source_types = ("text",)
    locator_family = "line_address"
    produces_source_type = "text"
    produces_family = "line_address"

    def parse(self, path, source_hash):
        el = Element(
            element_id="e1",
            type="paragraph",
            content="x",
            source_locator={"family": type(self).produces_family, "line": 1},
        )
        return Document(
            document_id="d" + source_hash[:8],
            source_path=str(path),
            source_type=type(self).produces_source_type,
            source_hash=source_hash,
            parser_name=self.name,
            parser_version=self.version,
            elements=[el],
        )


def _input(tmp_path):
    p = tmp_path / "in.txt"
    p.write_text("hello\n", encoding="utf-8")
    return p


def _errors_of(doc_and_errors):
    document, errors = doc_and_errors
    return document, [e.code for e in errors], errors


def test_contract_ok_passes(fresh_registry, tmp_path):
    register(_StubParser)
    document, errors = process_single(
        _input(tmp_path), tmp_path / "out.json",
        parser_name="stub_contract", write_json=False,
    )
    assert errors == [] and document is not None


def test_source_type_outside_declaration_rejected(fresh_registry, tmp_path):
    class _Liar(_StubParser):
        name = "stub_liar_type"
        # 声明 text，产出 html（line_address 形状对两者都 schema 合法，
        # 只有契约检查能拦截）
        produces_source_type = "html"

    register(_Liar)
    out = tmp_path / "out.json"
    document, codes, errors = _errors_of(
        process_single(_input(tmp_path), out, parser_name="stub_liar_type",
                       write_json=True)
    )
    assert document is None
    assert codes == ["parser_contract_mismatch"]
    details = errors[0].details
    assert details["actual_source_type"] == "html"
    assert details["declared_source_types"] == ["text"]
    assert not out.exists(), "契约失败不得写盘"


def test_family_mismatch_rejected_even_when_schema_valid(fresh_registry, tmp_path):
    class _MyxParser(_StubParser):
        name = "stub_myx"
        source_types = ("myx",)
        locator_family = "line_address"
        produces_source_type = "myx"
        # family=page_geometry + page 在 0.6.0 schema 下按 family 路由
        # 校验通过——只有契约检查能拦截
        produces_family = "page_geometry"

        def parse(self, path, source_hash):
            doc = super().parse(path, source_hash)
            doc.elements[0].source_locator = {
                "family": "page_geometry", "page": 1,
            }
            return doc

    register(_MyxParser)
    out = tmp_path / "out.json"
    document, codes, errors = _errors_of(
        process_single(_input(tmp_path), out, parser_name="stub_myx",
                       write_json=True)
    )
    assert document is None
    assert codes == ["parser_contract_mismatch"]
    details = errors[0].details
    assert details["expected_locator_family"] == "line_address"
    assert details["offending_element_ids"] == ["e1"]
    assert not out.exists()


def test_str_declaration_normalized_everywhere(fresh_registry, tmp_path):
    class _StrDecl(_StubParser):
        name = "stub_strdecl"
        source_types = "myx2"  # str 声明：register 视为单元素 tuple
        locator_family = "line_address"
        produces_source_type = "myx2"

    register(_StrDecl)
    assert declared_source_types(_StrDecl) == ("myx2",)
    entry = next(p for p in list_parsers() if p["name"] == "stub_strdecl")
    assert entry["source_types"] == ["myx2"], "str 声明不得被逐字符拆分"
    document, errors = process_single(
        _input(tmp_path), tmp_path / "out.json",
        parser_name="stub_strdecl", write_json=False,
    )
    assert errors == [] and document is not None
    assert document.source_type == "myx2"


def test_builtin_parser_contract_still_passes(tmp_path):
    # 既有内置路径回归：markdown 全链（声明 markdown/line_address）
    md = tmp_path / "in.md"
    md.write_text("# t\n\nbody\n", encoding="utf-8")
    document, errors = process_single(
        md, tmp_path / "out.json", parser_name="markdown", write_json=False,
    )
    assert errors == [] and document is not None
