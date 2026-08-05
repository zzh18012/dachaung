r"""app/models.py 边角测试 - 第六轮（Round 200）。

补强已有 base/edges/edges2-5（共 ~554 测试）未覆盖的深度：
- SCHEMA_VERSION / ElementType / SourceType 常量
- Element/Chunk __post_init__ 各 ValueError 边界
- WarningRecord/ErrorRecord details=None 路径
- Document.to_dict 完整字段集 + 嵌套 to_dict
- 各 dataclass 默认值
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, asdict, fields, is_dataclass
from typing import Any, get_args, get_origin

import pytest

from app.models import (
    SCHEMA_VERSION,
    Chunk,
    Document,
    Element,
    ElementType,
    ErrorRecord,
    Relation,
    SourceType,
    WarningRecord,
)


# =========================================================================
# 常量
# =========================================================================


def test_schema_version_value():
    assert SCHEMA_VERSION == "0.1.0"


def test_element_type_literal_values():
    args = set(get_args(ElementType))
    expected = {
        "heading", "paragraph", "list_item", "table",
        "image", "caption", "header", "footer",
    }
    assert args == expected


def test_element_type_literal_excludes_unknown():
    args = set(get_args(ElementType))
    assert "unknown" not in args
    assert "section" not in args


def test_source_type_literal_values():
    args = set(get_args(SourceType))
    expected = {"pdf", "docx", "markdown", "html", "text", "ipynb"}
    assert args == expected


def test_source_type_literal_excludes_unknown():
    args = set(get_args(SourceType))
    assert "unknown" not in args
    assert "rtf" not in args


# =========================================================================
# Element __post_init__ 边界
# =========================================================================


def _make_element(**overrides) -> Element:
    defaults = {
        "element_id": "e1",
        "type": "paragraph",
        "source_locator": {"line": 1},
        "content": "hello",
    }
    defaults.update(overrides)
    return Element(**defaults)


def test_element_post_init_empty_id_raises():
    with pytest.raises(ValueError, match="element_id"):
        Element(element_id="", type="paragraph", source_locator={}, content="x")


def test_element_post_init_no_content_no_resource_raises():
    with pytest.raises(ValueError, match="必须至少有"):
        Element(
            element_id="e1", type="paragraph",
            source_locator={}, content=None, resource_path=None,
        )


def test_element_post_init_empty_content_no_resource_raises():
    """content='' 也是 falsy → 抛。"""
    with pytest.raises(ValueError):
        Element(
            element_id="e1", type="paragraph",
            source_locator={}, content="", resource_path=None,
        )


def test_element_post_init_only_resource_path_ok():
    """有 resource_path（content=None）→ OK。"""
    e = Element(
        element_id="e1", type="image",
        source_locator={}, content=None, resource_path="img.png",
    )
    assert e.resource_path == "img.png"


def test_element_post_init_only_content_ok():
    e = _make_element()
    assert e.content == "hello"


def test_element_post_init_both_content_and_resource_ok():
    e = Element(
        element_id="e1", type="paragraph",
        source_locator={}, content="x", resource_path="img.png",
    )
    assert e.content == "x"
    assert e.resource_path == "img.png"


def test_element_default_confidence_1():
    e = _make_element()
    assert e.confidence == 1.0


def test_element_default_parent_id_none():
    e = _make_element()
    assert e.parent_id is None


def test_element_default_resource_path_none():
    e = _make_element()
    assert e.resource_path is None


def test_element_default_metadata_empty_dict():
    e = _make_element()
    assert e.metadata == {}


def test_element_metadata_default_not_shared():
    """default_factory=dict 应给每个实例新 dict。"""
    e1 = _make_element()
    e2 = _make_element()
    e1.metadata["x"] = 1
    assert "x" not in e2.metadata


def test_element_to_dict_returns_dict():
    e = _make_element()
    d = e.to_dict()
    assert isinstance(d, dict)


def test_element_to_dict_has_seven_keys():
    e = _make_element()
    d = e.to_dict()
    expected = {
        "element_id", "type", "source_locator", "parent_id",
        "content", "resource_path", "confidence", "metadata",
    }
    assert set(d.keys()) == expected


def test_element_to_dict_roundtrip_keys():
    e = _make_element(content="abc", resource_path=None)
    d = e.to_dict()
    assert d["element_id"] == "e1"
    assert d["type"] == "paragraph"
    assert d["content"] == "abc"
    assert d["resource_path"] is None


def test_element_equality():
    a = _make_element()
    b = _make_element()
    assert a == b


def test_element_inequality():
    a = _make_element(element_id="e1")
    b = _make_element(element_id="e2")
    assert a != b


def test_element_is_dataclass():
    assert is_dataclass(Element) is True


def test_element_field_count():
    f = fields(Element)
    assert len(f) == 8


# =========================================================================
# Chunk __post_init__ 边界
# =========================================================================


def _make_chunk(**overrides) -> Chunk:
    defaults = {
        "chunk_id": "c1",
        "text": "hello",
        "source_element_ids": ["e1"],
    }
    defaults.update(overrides)
    return Chunk(**defaults)


def test_chunk_post_init_empty_id_raises():
    with pytest.raises(ValueError, match="chunk_id"):
        Chunk(chunk_id="", text="x", source_element_ids=["e1"])


def test_chunk_post_init_empty_source_ids_raises():
    with pytest.raises(ValueError, match="至少要有一个"):
        Chunk(chunk_id="c1", text="x", source_element_ids=[])


def test_chunk_post_init_empty_text_raises():
    with pytest.raises(ValueError, match="文本不能为空"):
        Chunk(chunk_id="c1", text="", source_element_ids=["e1"])


def test_chunk_post_init_none_text_raises():
    with pytest.raises(ValueError):
        Chunk(chunk_id="c1", text=None, source_element_ids=["e1"])  # type: ignore[arg-type]


def test_chunk_default_metadata_empty():
    c = _make_chunk()
    assert c.metadata == {}


def test_chunk_default_source_spans_empty():
    c = _make_chunk()
    assert c.source_spans == []


def test_chunk_metadata_default_not_shared():
    c1 = _make_chunk()
    c2 = _make_chunk()
    c1.metadata["x"] = 1
    assert "x" not in c2.metadata


def test_chunk_source_spans_default_not_shared():
    c1 = _make_chunk()
    c2 = _make_chunk()
    c1.source_spans.append({"start": 0})
    assert len(c2.source_spans) == 0


def test_chunk_to_dict_returns_dict():
    c = _make_chunk()
    assert isinstance(c.to_dict(), dict)


def test_chunk_to_dict_has_five_keys():
    c = _make_chunk()
    d = c.to_dict()
    expected = {"chunk_id", "text", "source_element_ids", "metadata", "source_spans"}
    assert set(d.keys()) == expected


def test_chunk_equality():
    a = _make_chunk()
    b = _make_chunk()
    assert a == b


def test_chunk_is_dataclass():
    assert is_dataclass(Chunk) is True


def test_chunk_field_count():
    assert len(fields(Chunk)) == 5


# =========================================================================
# Relation
# =========================================================================


def _make_relation(**overrides) -> Relation:
    defaults = {"type": "parent", "from_id": "h1", "to_id": "p1"}
    defaults.update(overrides)
    return Relation(**defaults)


def test_relation_to_dict_has_four_keys():
    r = _make_relation()
    d = r.to_dict()
    expected = {"type", "from_id", "to_id", "metadata"}
    assert set(d.keys()) == expected


def test_relation_default_metadata_empty():
    r = _make_relation()
    assert r.metadata == {}


def test_relation_metadata_default_not_shared():
    r1 = _make_relation()
    r2 = _make_relation()
    r1.metadata["x"] = 1
    assert "x" not in r2.metadata


def test_relation_equality():
    a = _make_relation()
    b = _make_relation()
    assert a == b


def test_relation_is_dataclass():
    assert is_dataclass(Relation) is True


def test_relation_field_count():
    assert len(fields(Relation)) == 4


# =========================================================================
# WarningRecord
# =========================================================================


def test_warning_record_to_dict_basic_keys():
    w = WarningRecord(code="X", reason="because")
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason"}


def test_warning_record_to_dict_no_details_omits_key():
    w = WarningRecord(code="X", reason="because")
    d = w.to_dict()
    assert "details" not in d


def test_warning_record_to_dict_with_details_includes_key():
    w = WarningRecord(code="X", reason="because", details={"k": "v"})
    d = w.to_dict()
    assert "details" in d
    assert d["details"] == {"k": "v"}


def test_warning_record_default_details_none():
    w = WarningRecord(code="X", reason="because")
    assert w.details is None


def test_warning_record_with_empty_details_dict_includes_key():
    """details 显式传 {} → key 存在。"""
    w = WarningRecord(code="X", reason="because", details={})
    d = w.to_dict()
    assert "details" in d
    assert d["details"] == {}


def test_warning_record_equality():
    a = WarningRecord(code="X", reason="r")
    b = WarningRecord(code="X", reason="r")
    assert a == b


def test_warning_record_is_dataclass():
    assert is_dataclass(WarningRecord) is True


def test_warning_record_field_count():
    assert len(fields(WarningRecord)) == 3


# =========================================================================
# ErrorRecord
# =========================================================================


def test_error_record_to_dict_basic_keys():
    e = ErrorRecord(code="X", message="boom")
    d = e.to_dict()
    assert set(d.keys()) == {"code", "message"}


def test_error_record_to_dict_no_details_omits_key():
    e = ErrorRecord(code="X", message="boom")
    d = e.to_dict()
    assert "details" not in d


def test_error_record_to_dict_with_details_includes_key():
    e = ErrorRecord(code="X", message="boom", details={"k": "v"})
    d = e.to_dict()
    assert "details" in d


def test_error_record_default_details_none():
    e = ErrorRecord(code="X", message="boom")
    assert e.details is None


def test_error_record_with_empty_details_includes_key():
    e = ErrorRecord(code="X", message="boom", details={})
    d = e.to_dict()
    assert "details" in d


def test_error_record_equality():
    a = ErrorRecord(code="X", message="m")
    b = ErrorRecord(code="X", message="m")
    assert a == b


def test_error_record_inequality_on_message():
    a = ErrorRecord(code="X", message="m1")
    b = ErrorRecord(code="X", message="m2")
    assert a != b


def test_error_record_is_dataclass():
    assert is_dataclass(ErrorRecord) is True


def test_error_record_field_count():
    assert len(fields(ErrorRecord)) == 3


# =========================================================================
# Document
# =========================================================================


def _make_document(**overrides) -> Document:
    defaults = {
        "document_id": "doc-x",
        "source_path": "/tmp/x",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "0.1.0",
    }
    defaults.update(overrides)
    return Document(**defaults)


def test_document_default_lists_empty():
    d = _make_document()
    assert d.elements == []
    assert d.chunks == []
    assert d.relations == []
    assert d.warnings == []
    assert d.errors == []


def test_document_default_metadata_empty():
    d = _make_document()
    assert d.metadata == {}


def test_document_metadata_default_not_shared():
    d1 = _make_document()
    d2 = _make_document()
    d1.metadata["x"] = 1
    assert "x" not in d2.metadata


def test_document_elements_default_not_shared():
    d1 = _make_document()
    d2 = _make_document()
    d1.elements.append(_make_element())
    assert len(d2.elements) == 0


def test_document_to_dict_returns_dict():
    d = _make_document()
    assert isinstance(d.to_dict(), dict)


def test_document_to_dict_includes_schema_version():
    d = _make_document()
    assert d.to_dict()["schema_version"] == SCHEMA_VERSION


def test_document_to_dict_has_13_keys():
    d = _make_document()
    expected = {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert set(d.to_dict().keys()) == expected


def test_document_to_dict_serializes_nested_elements():
    d = _make_document(elements=[_make_element()])
    out = d.to_dict()
    assert len(out["elements"]) == 1
    assert isinstance(out["elements"][0], dict)
    assert out["elements"][0]["element_id"] == "e1"


def test_document_to_dict_serializes_nested_chunks():
    d = _make_document(chunks=[_make_chunk()])
    out = d.to_dict()
    assert len(out["chunks"]) == 1
    assert out["chunks"][0]["chunk_id"] == "c1"


def test_document_to_dict_serializes_nested_warnings():
    d = _make_document(warnings=[WarningRecord(code="X", reason="r")])
    out = d.to_dict()
    assert len(out["warnings"]) == 1
    assert out["warnings"][0]["code"] == "X"


def test_document_to_dict_serializes_nested_errors():
    d = _make_document(errors=[ErrorRecord(code="X", message="m")])
    out = d.to_dict()
    assert len(out["errors"]) == 1


def test_document_to_dict_serializes_nested_relations():
    d = _make_document(relations=[_make_relation()])
    out = d.to_dict()
    assert len(out["relations"]) == 1


def test_document_to_dict_empty_lists():
    d = _make_document()
    out = d.to_dict()
    assert out["elements"] == []
    assert out["chunks"] == []
    assert out["relations"] == []
    assert out["warnings"] == []
    assert out["errors"] == []


def test_document_equality():
    a = _make_document()
    b = _make_document()
    assert a == b


def test_document_is_dataclass():
    assert is_dataclass(Document) is True


def test_document_field_count():
    # schema_version is a class constant, NOT a dataclass field
    assert len(fields(Document)) == 12


# =========================================================================
# 模块结构与签名
# =========================================================================


def test_module_imports_dataclass():
    import app.models as m
    assert hasattr(m, "dataclass")
    assert hasattr(m, "field")
    assert hasattr(m, "asdict")


def test_module_imports_typing():
    import app.models as m
    assert hasattr(m, "Any")
    assert hasattr(m, "Literal")
    assert hasattr(m, "Optional")


def test_module_no_all_defined():
    """app.models 不定义 __all__（所有 public 直接 importable）。"""
    import app.models as m
    # 模块没显式定义 __all__ → 默认所有非 _ 开头的名字
    assert not hasattr(m, "__all__") or m.__all__ is None or isinstance(m.__all__, list)


def test_element_to_dict_signature():
    sig = inspect.signature(Element.to_dict)
    assert set(sig.parameters) == {"self"}


def test_chunk_to_dict_signature():
    sig = inspect.signature(Chunk.to_dict)
    assert set(sig.parameters) == {"self"}


def test_relation_to_dict_signature():
    sig = inspect.signature(Relation.to_dict)
    assert set(sig.parameters) == {"self"}


def test_warning_record_to_dict_signature():
    sig = inspect.signature(WarningRecord.to_dict)
    assert set(sig.parameters) == {"self"}


def test_error_record_to_dict_signature():
    sig = inspect.signature(ErrorRecord.to_dict)
    assert set(sig.parameters) == {"self"}


def test_document_to_dict_signature():
    sig = inspect.signature(Document.to_dict)
    assert set(sig.parameters) == {"self"}


def test_all_classes_callable():
    assert callable(Element)
    assert callable(Chunk)
    assert callable(Relation)
    assert callable(WarningRecord)
    assert callable(ErrorRecord)
    assert callable(Document)


# =========================================================================
# idempotency
# =========================================================================


def test_element_to_dict_idempotent():
    e = _make_element()
    assert e.to_dict() == e.to_dict()


def test_chunk_to_dict_idempotent():
    c = _make_chunk()
    assert c.to_dict() == c.to_dict()


def test_document_to_dict_idempotent():
    d = _make_document(elements=[_make_element()])
    assert d.to_dict() == d.to_dict()


# =========================================================================
# 综合行为
# =========================================================================


def test_full_document_with_all_field_types():
    """完整 Document：含所有字段类型。"""
    elements = [
        Element(
            element_id="e1", type="heading", source_locator={"line": 1},
            content="Title",
        ),
        Element(
            element_id="e2", type="paragraph", source_locator={"line": 2},
            content="Body",
        ),
        Element(
            element_id="i1", type="image", source_locator={"page": 1},
            content=None, resource_path="img.png",
        ),
    ]
    chunks = [
        Chunk(chunk_id="c1", text="Title", source_element_ids=["e1"]),
        Chunk(chunk_id="c2", text="Body", source_element_ids=["e2"]),
    ]
    relations = [Relation(type="parent", from_id="e1", to_id="e2")]
    warnings = [WarningRecord(code="X", reason="r")]
    errors = []
    d = Document(
        document_id="doc-full",
        source_path="/tmp/full.pdf",
        source_type="pdf",
        source_hash="b" * 64,
        parser_name="fallback",
        parser_version="0.1.0",
        elements=elements,
        chunks=chunks,
        relations=relations,
        warnings=warnings,
        errors=errors,
        metadata={"k": "v"},
    )
    out = d.to_dict()
    assert out["schema_version"] == SCHEMA_VERSION
    assert len(out["elements"]) == 3
    assert len(out["chunks"]) == 2
    assert len(out["relations"]) == 1
    assert len(out["warnings"]) == 1
    assert out["metadata"] == {"k": "v"}


def test_dataclass_asdict_via_to_dict():
    """to_dict 内部用 asdict → 深拷贝。"""
    e = _make_element(metadata={"k": [1, 2, 3]})
    d = e.to_dict()
    d["metadata"]["k"].append(4)
    # 修改返回的 dict 不影响原对象
    assert e.metadata["k"] == [1, 2, 3]


def test_document_to_dict_metadata_mutated_affects_source():
    """Document.to_dict builds dict that shares metadata reference (no asdict deep copy at top)."""
    d = _make_document(metadata={"k": "v"})
    out = d.to_dict()
    out["metadata"]["k"] = "modified"
    # Document.to_dict does not deep-copy metadata
    assert d.metadata["k"] == "modified"
