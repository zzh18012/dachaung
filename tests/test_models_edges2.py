"""app/models.py 边角测试 - 第二轮（Round 72）。

补强 tests/test_models.py（55）+ tests/test_models_edges.py（59）未覆盖的：
- 模块结构与导入
- SCHEMA_VERSION 不变性
- Element 边角：parent_id None、confidence 默认 1.0、metadata 隔离、to_dict 字段集
- Chunk 边角：source_element_ids 含空字符串、source_spans 隔离、to_dict 字段集
- Relation 边角：空字符串字段接受、to_dict 字段集
- WarningRecord/ErrorRecord：details None vs empty dict vs non-empty dict、to_dict 字段集
- Document：to_dict 完整字段集、SCHEMA_VERSION 写入、metadata 隔离、嵌套结构
- 类型严格性
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
from typing import Any

import pytest

from app.models import (
    SCHEMA_VERSION,
    Document,
    Element,
    Chunk,
    Relation,
    WarningRecord,
    ErrorRecord,
)


# ---------- 模块结构 ----------


def test_module_has_schema_version():
    import app.models as mod
    assert hasattr(mod, "SCHEMA_VERSION")


def test_module_has_element_type():
    import app.models as mod
    assert hasattr(mod, "ElementType")


def test_module_has_source_type():
    import app.models as mod
    assert hasattr(mod, "SourceType")


def test_schema_version_constant_value_0_1_0():
    assert SCHEMA_VERSION == "0.1.0"


def test_schema_version_is_str():
    assert isinstance(SCHEMA_VERSION, str)


def test_module_imports_dataclass():
    import app.models as mod
    assert hasattr(mod, "dataclass")


def test_module_imports_field():
    import app.models as mod
    assert hasattr(mod, "field")


def test_module_imports_asdict():
    import app.models as mod
    assert hasattr(mod, "asdict")


def test_module_imports_any():
    import app.models as mod
    assert hasattr(mod, "Any")


def test_module_imports_literal():
    import app.models as mod
    assert hasattr(mod, "Literal")


def test_module_imports_optional():
    import app.models as mod
    assert hasattr(mod, "Optional")


def test_module_does_not_have_all():
    import app.models as mod
    assert not hasattr(mod, "__all__")


# ---------- Element 边角 ----------


def test_element_default_parent_id_is_none():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.parent_id is None


def test_element_default_confidence_is_one():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.confidence == 1.0


def test_element_default_metadata_is_empty_dict():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.metadata == {}


def test_element_metadata_default_isolated_per_instance():
    e1 = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    e2 = Element(element_id="e2", type="paragraph", source_locator={}, content="y")
    e1.metadata["k"] = "v"
    assert e2.metadata == {}


def test_element_to_dict_returns_seven_keys_exact():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    d = e.to_dict()
    assert set(d.keys()) == {
        "element_id",
        "type",
        "source_locator",
        "parent_id",
        "content",
        "resource_path",
        "confidence",
        "metadata",
    }


def test_element_to_dict_returns_dict_type():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert isinstance(e.to_dict(), dict)


def test_element_source_locator_passed_through():
    loc = {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}
    e = Element(element_id="e1", type="paragraph", source_locator=loc, content="x")
    assert e.to_dict()["source_locator"] == loc


def test_element_resource_path_default_none():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.resource_path is None


def test_element_confidence_passed_through():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x", confidence=0.5)
    assert e.confidence == 0.5


def test_element_parent_id_passed_through():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        parent_id="e0",
    )
    assert e.parent_id == "e0"


def test_element_with_resource_path_only():
    e = Element(
        element_id="e1",
        type="image",
        source_locator={"page": 1, "bbox": [0, 0, 100, 100]},
        resource_path="images/img1.png",
    )
    assert e.content is None
    assert e.resource_path == "images/img1.png"


def test_element_with_both_content_and_resource_path():
    e = Element(
        element_id="e1",
        type="image",
        source_locator={"page": 1, "bbox": [0, 0, 100, 100]},
        content="alt text",
        resource_path="images/img1.png",
    )
    assert e.content == "alt text"
    assert e.resource_path == "images/img1.png"


def test_element_raises_when_both_content_and_resource_empty():
    with pytest.raises(ValueError):
        Element(element_id="e1", type="paragraph", source_locator={}, content=None, resource_path=None)


def test_element_raises_when_content_empty_string_and_resource_none():
    with pytest.raises(ValueError):
        Element(element_id="e1", type="paragraph", source_locator={}, content="", resource_path=None)


def test_element_ok_with_whitespace_content_and_resource_none():
    """whitespace content 是 truthy → 通过 __post_init__（与 schema 行为可能不同）。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="   ",
        resource_path=None,
    )
    # whitespace string truthy → 不 raise
    assert e.content == "   "


def test_element_ok_with_whitespace_content_and_resource():
    """whitespace content + resource → OK（content falsy 但 resource truthy）。"""
    e = Element(
        element_id="e1",
        type="image",
        source_locator={},
        content="   ",
        resource_path="x.png",
    )
    assert e.content == "   "


def test_element_unicode_metadata():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        metadata={"中文key": "值 🎉"},
    )
    assert e.to_dict()["metadata"]["中文key"] == "值 🎉"


def test_element_is_dataclass():
    assert is_dataclass(Element)


def test_element_to_dict_callable():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert callable(e.to_dict)


def test_element_to_dict_returns_new_object():
    """to_dict 返回新对象（不与 e 共享引用）。"""
    e = Element(element_id="e1", type="paragraph", source_locator={"a": 1}, content="x")
    d = e.to_dict()
    d["metadata"]["new"] = "value"
    assert "new" not in e.metadata  # 隔离


# ---------- Chunk 边角 ----------


def test_chunk_to_dict_returns_five_keys_exact():
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    d = c.to_dict()
    assert set(d.keys()) == {
        "chunk_id",
        "text",
        "source_element_ids",
        "metadata",
        "source_spans",
    }


def test_chunk_default_metadata_is_empty_dict():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.metadata == {}


def test_chunk_default_source_spans_is_empty_list():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.source_spans == []


def test_chunk_metadata_isolated_per_instance():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e1"])
    c1.metadata["k"] = "v"
    assert c2.metadata == {}


def test_chunk_source_spans_isolated_per_instance():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e1"])
    c1.source_spans.append({"start": 0, "end": 1})
    assert c2.source_spans == []


def test_chunk_source_element_ids_with_empty_string_in_list():
    """source_element_ids=[''] → 列表非空（truthy）→ 通过 __post_init__ 校验。"""
    c = Chunk(chunk_id="c1", text="x", source_element_ids=[""])
    assert c.source_element_ids == [""]


def test_chunk_with_complex_metadata():
    c = Chunk(
        chunk_id="c1",
        text="x",
        source_element_ids=["e1"],
        metadata={"strategy": "structural", "max_chars": 800, "char_count": 100},
    )
    d = c.to_dict()
    assert d["metadata"]["strategy"] == "structural"


def test_chunk_with_complex_source_spans():
    spans = [
        {"element_id": "e1", "start": 0, "end": 5},
        {"element_id": "e1", "start": 6, "end": 10},
    ]
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"], source_spans=spans)
    assert c.to_dict()["source_spans"] == spans


def test_chunk_to_dict_returns_dict_type():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert isinstance(c.to_dict(), dict)


def test_chunk_text_passed_through():
    c = Chunk(chunk_id="c1", text="hello world", source_element_ids=["e1"])
    assert c.text == "hello world"


def test_chunk_unicode_text():
    c = Chunk(chunk_id="c1", text="中文 🎉", source_element_ids=["e1"])
    assert c.to_dict()["text"] == "中文 🎉"


def test_chunk_is_dataclass():
    assert is_dataclass(Chunk)


def test_chunk_raises_when_chunk_id_empty():
    with pytest.raises(ValueError):
        Chunk(chunk_id="", text="x", source_element_ids=["e1"])


def test_chunk_raises_when_text_empty():
    with pytest.raises(ValueError):
        Chunk(chunk_id="c1", text="", source_element_ids=["e1"])


def test_chunk_raises_when_source_element_ids_empty():
    with pytest.raises(ValueError):
        Chunk(chunk_id="c1", text="x", source_element_ids=[])


def test_chunk_ok_with_whitespace_only_text():
    """__post_init__ 用 `if not self.text` → whitespace 仍 truthy → 通过。"""
    c = Chunk(chunk_id="c1", text="   ", source_element_ids=["e1"])
    assert c.text == "   "


# ---------- Relation 边角 ----------


def test_relation_to_dict_returns_four_keys_exact():
    """Relation.to_dict 用 asdict → 总返 4 个 key（含 metadata 默认 {}）。"""
    r = Relation(type="parent", from_id="a", to_id="b")
    d = r.to_dict()
    assert set(d.keys()) == {"type", "from_id", "to_id", "metadata"}


def test_relation_default_metadata_is_empty_dict():
    r = Relation(type="t", from_id="a", to_id="b")
    assert r.metadata == {}


def test_relation_metadata_isolated_per_instance():
    r1 = Relation(type="t", from_id="a", to_id="b")
    r2 = Relation(type="t", from_id="c", to_id="d")
    r1.metadata["k"] = "v"
    assert r2.metadata == {}


def test_relation_to_dict_includes_metadata_when_set():
    r = Relation(type="t", from_id="a", to_id="b", metadata={"level": 2})
    d = r.to_dict()
    assert d["metadata"] == {"level": 2}


def test_relation_with_empty_strings_accepted():
    """Relation 没有 __post_init__ 校验，空字符串接受。"""
    r = Relation(type="", from_id="", to_id="")
    assert r.type == ""
    assert r.from_id == ""
    assert r.to_id == ""


def test_relation_unicode_type():
    r = Relation(type="父子", from_id="a", to_id="b")
    assert r.type == "父子"


def test_relation_is_dataclass():
    assert is_dataclass(Relation)


# ---------- WarningRecord 边角 ----------


def test_warning_record_to_dict_returns_two_keys_when_details_none():
    w = WarningRecord(code="x", reason="y")
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason"}


def test_warning_record_to_dict_includes_details_when_set():
    w = WarningRecord(code="x", reason="y", details={"k": "v"})
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason", "details"}


def test_warning_record_to_dict_includes_details_when_empty_dict():
    """空 dict 也算 not None → 包含。"""
    w = WarningRecord(code="x", reason="y", details={})
    d = w.to_dict()
    assert "details" in d


def test_warning_record_details_default_none():
    w = WarningRecord(code="x", reason="y")
    assert w.details is None


def test_warning_record_unicode_code_reason():
    w = WarningRecord(code="代码", reason="原因 🎉")
    d = w.to_dict()
    assert d["code"] == "代码"
    assert d["reason"] == "原因 🎉"


def test_warning_record_with_complex_details():
    w = WarningRecord(code="x", reason="y", details={"nested": {"deep": [1, 2, 3]}})
    assert w.to_dict()["details"] == {"nested": {"deep": [1, 2, 3]}}


def test_warning_record_is_dataclass():
    assert is_dataclass(WarningRecord)


def test_warning_record_is_mutable():
    w = WarningRecord(code="x", reason="y")
    w.code = "new"
    assert w.code == "new"


# ---------- ErrorRecord 边角 ----------


def test_error_record_to_dict_returns_two_keys_when_details_none():
    er = ErrorRecord(code="x", message="y")
    d = er.to_dict()
    assert set(d.keys()) == {"code", "message"}


def test_error_record_to_dict_includes_details_when_set():
    er = ErrorRecord(code="x", message="y", details={"k": "v"})
    d = er.to_dict()
    assert set(d.keys()) == {"code", "message", "details"}


def test_error_record_to_dict_includes_details_when_empty_dict():
    er = ErrorRecord(code="x", message="y", details={})
    d = er.to_dict()
    assert "details" in d


def test_error_record_details_default_none():
    er = ErrorRecord(code="x", message="y")
    assert er.details is None


def test_error_record_unicode_message():
    er = ErrorRecord(code="x", message="错误消息 🎉")
    assert er.to_dict()["message"] == "错误消息 🎉"


def test_error_record_with_complex_details():
    er = ErrorRecord(
        code="x",
        message="y",
        details={"validation_errors": [{"path": [0], "msg": "fail"}]},
    )
    assert er.to_dict()["details"]["validation_errors"][0]["path"] == [0]


def test_error_record_is_dataclass():
    assert is_dataclass(ErrorRecord)


def test_error_record_is_mutable():
    er = ErrorRecord(code="x", message="y")
    er.code = "new"
    assert er.code == "new"


# ---------- Document 边角 ----------


def test_document_to_dict_returns_13_keys_exact():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    d = doc.to_dict()
    assert set(d.keys()) == {
        "schema_version",
        "document_id",
        "source_path",
        "source_type",
        "source_hash",
        "parser_name",
        "parser_version",
        "elements",
        "chunks",
        "relations",
        "warnings",
        "errors",
        "metadata",
    }


def test_document_to_dict_includes_schema_version_constant():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.to_dict()["schema_version"] == SCHEMA_VERSION


def test_document_default_elements_is_empty_list():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.elements == []


def test_document_default_chunks_is_empty_list():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.chunks == []


def test_document_default_relations_is_empty_list():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.relations == []


def test_document_default_warnings_is_empty_list():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.warnings == []


def test_document_default_errors_is_empty_list():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.errors == []


def test_document_default_metadata_is_empty_dict():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert doc.metadata == {}


def test_document_metadata_isolated_per_instance():
    d1 = Document(
        document_id="d1",
        source_path="x",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="p",
        parser_version="1",
    )
    d2 = Document(
        document_id="d2",
        source_path="x",
        source_type="docx",
        source_hash="b" * 64,
        parser_name="p",
        parser_version="1",
    )
    d1.metadata["k"] = "v"
    assert d2.metadata == {}


def test_document_with_full_nested_structure():
    e = Element(element_id="e1", type="paragraph", source_locator={"paragraph_index": 0}, content="text")
    c = Chunk(chunk_id="c1", text="text", source_element_ids=["e1"])
    r = Relation(type="parent", from_id="e0", to_id="e1")
    w = WarningRecord(code="x", reason="y")
    er = ErrorRecord(code="z", message="m")
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
        elements=[e],
        chunks=[c],
        relations=[r],
        warnings=[w],
        errors=[er],
        metadata={"k": "v"},
    )
    d = doc.to_dict()
    assert d["elements"][0]["element_id"] == "e1"
    assert d["chunks"][0]["chunk_id"] == "c1"
    assert d["relations"][0]["type"] == "parent"
    assert d["warnings"][0]["code"] == "x"
    assert d["errors"][0]["code"] == "z"
    assert d["metadata"] == {"k": "v"}


def test_document_is_dataclass():
    assert is_dataclass(Document)


def test_document_is_mutable():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    doc.document_id = "modified"
    assert doc.document_id == "modified"


def test_document_to_dict_returns_dict_type():
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
    )
    assert isinstance(doc.to_dict(), dict)


def test_document_to_dict_shares_metadata_reference():
    """to_dict 返回 'metadata': self.metadata（直接引用，不深拷贝）。

    调用方不应直接修改返回的 dict；如需独立副本，自行 copy()。
    """
    doc = Document(
        document_id="d1",
        source_path="x.docx",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="1.0",
        metadata={"k": "v"},
    )
    d = doc.to_dict()
    d["metadata"]["new"] = "value"
    # 共享引用 → doc.metadata 也被修改
    assert "new" in doc.metadata


def test_document_parser_version_complex_string():
    doc = Document(
        document_id="d1",
        source_path="x",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="p",
        parser_version="fallback=0.5.1+gd4e8f2c",
    )
    assert doc.parser_version == "fallback=0.5.1+gd4e8f2c"


def test_document_unicode_metadata():
    doc = Document(
        document_id="d1",
        source_path="x",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="p",
        parser_version="1",
        metadata={"标题": "中文报告", "标签": ["a", "b"]},
    )
    assert doc.to_dict()["metadata"]["标题"] == "中文报告"


# ---------- 嵌套 dataclass.to_dict 一致性 ----------


def test_all_dataclasses_have_to_dict_method():
    classes = (Element, Chunk, Relation, WarningRecord, ErrorRecord, Document)
    for cls in classes:
        assert hasattr(cls, "to_dict")


def test_all_dataclasses_callable_to_dict():
    """to_dict 在实例上可调用。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    r = Relation(type="t", from_id="a", to_id="b")
    w = WarningRecord(code="c", reason="r")
    er = ErrorRecord(code="c", message="m")
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="p",
        parser_version="1",
    )
    for obj in (e, c, r, w, er, d):
        assert callable(obj.to_dict)
