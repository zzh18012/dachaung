"""统一文档模型 dataclass 的单元测试。"""

from __future__ import annotations

import pytest

from app.models import (
    Chunk,
    Document,
    Element,
    ErrorRecord,
    Relation,
    SCHEMA_VERSION,
    WarningRecord,
)


def test_element_text_basic():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello world",
        source_locator={"page": 1},
    )
    assert e.element_id == "e1"
    assert e.content == "hello world"
    assert e.resource_path is None
    assert e.confidence == 1.0
    assert e.parent_id is None


def test_element_image_uses_resource_path():
    e = Element(
        element_id="e2",
        type="image",
        resource_path="outputs/extracted/image_e2.png",
        source_locator={"page": 1, "bbox": [10.0, 20.0, 110.0, 220.0]},
    )
    assert e.content is None
    assert e.resource_path is not None


def test_element_requires_content_or_resource_path():
    with pytest.raises(ValueError, match="content 或 resource_path"):
        Element(
            element_id="e3",
            type="paragraph",
            source_locator={"page": 1},
        )


def test_element_rejects_empty_id():
    with pytest.raises(ValueError, match="element_id"):
        Element(
            element_id="",
            type="paragraph",
            content="x",
            source_locator={"page": 1},
        )


def test_chunk_requires_source_element_ids():
    with pytest.raises(ValueError, match="source_element_id"):
        Chunk(chunk_id="c1", text="x", source_element_ids=[])


def test_chunk_requires_text():
    with pytest.raises(ValueError, match="文本不能为空"):
        Chunk(chunk_id="c1", text="", source_element_ids=["e1"])


def test_chunk_rejects_empty_id():
    with pytest.raises(ValueError, match="chunk_id"):
        Chunk(chunk_id="", text="x", source_element_ids=["e1"])


def test_warning_and_error_to_dict_shapes():
    w = WarningRecord(code="parser_fallback", reason="kreuzberg ImportError")
    er = ErrorRecord(code="file_not_found", message="missing pdf")
    assert w.to_dict() == {"code": "parser_fallback", "reason": "kreuzberg ImportError"}
    assert er.to_dict() == {"code": "file_not_found", "message": "missing pdf"}


def test_warning_with_details():
    w = WarningRecord(
        code="low_confidence", reason="ocr", details={"score": 0.42}
    )
    d = w.to_dict()
    assert d["details"] == {"score": 0.42}


def test_document_to_dict_round_trip_keys():
    e = Element(
        element_id="e1",
        type="heading",
        content="Title",
        source_locator={"page": 1},
        metadata={"level": 1},
    )
    c = Chunk(chunk_id="c1", text="Title", source_element_ids=["e1"])
    doc = Document(
        document_id="d1",
        source_path="/tmp/x.pdf",
        source_type="pdf",
        source_hash="a" * 64,
        parser_name="kreuzberg",
        parser_version="4.10.2",
        elements=[e],
        chunks=[c],
        relations=[Relation(type="parent_child", from_id="e1", to_id="c1")],
    )
    d = doc.to_dict()
    assert d["schema_version"] == SCHEMA_VERSION
    assert set(d.keys()) >= {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert d["elements"][0]["element_id"] == "e1"
    assert d["chunks"][0]["source_element_ids"] == ["e1"]


# ---- 各种 to_dict 与默认值边角 ----


def test_element_to_dict_returns_all_fields():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hi",
        source_locator={"page": 1},
        parent_id="e0",
        confidence=0.5,
        metadata={"k": "v"},
    )
    d = e.to_dict()
    assert d["element_id"] == "e1"
    assert d["type"] == "paragraph"
    assert d["content"] == "hi"
    assert d["resource_path"] is None
    assert d["parent_id"] == "e0"
    assert d["source_locator"] == {"page": 1}
    assert d["confidence"] == 0.5
    assert d["metadata"] == {"k": "v"}


def test_element_resource_path_in_to_dict():
    e = Element(
        element_id="e1",
        type="image",
        resource_path="/x/y.png",
        source_locator={"page": 1},
    )
    d = e.to_dict()
    assert d["resource_path"] == "/x/y.png"
    assert d["content"] is None


def test_element_empty_string_content_rejected():
    """空字符串 content（且无 resource_path）→ __post_init__ 拒绝。"""
    with pytest.raises(ValueError):
        Element(element_id="e1", type="paragraph", content="", source_locator={})


def test_element_both_content_and_resource_path_allowed():
    """anyOf 是 OR 关系但 schema 层允许两者都有；dataclass 也不拒绝。"""
    e = Element(
        element_id="e1", type="image",
        content="caption text",
        resource_path="/x.png",
        source_locator={},
    )
    assert e.content == "caption text"
    assert e.resource_path == "/x.png"


def test_chunk_to_dict_includes_all_fields():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1", "e2"],
        metadata={"strategy": "isolated_table"},
        source_spans=[{"element_id": "e1", "start": 0, "end": 5}],
    )
    d = c.to_dict()
    assert d["chunk_id"] == "c1"
    assert d["text"] == "hello"
    assert d["source_element_ids"] == ["e1", "e2"]
    assert d["metadata"] == {"strategy": "isolated_table"}
    assert d["source_spans"] == [{"element_id": "e1", "start": 0, "end": 5}]


def test_chunk_default_source_spans_is_empty_list():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.source_spans == []


def test_chunk_default_metadata_is_empty_dict():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.metadata == {}


def test_relation_to_dict():
    r = Relation(type="next", from_id="e1", to_id="e2", metadata={"weight": 1.0})
    d = r.to_dict()
    assert d == {"type": "next", "from_id": "e1", "to_id": "e2", "metadata": {"weight": 1.0}}


def test_relation_default_metadata_is_empty():
    r = Relation(type="next", from_id="e1", to_id="e2")
    assert r.metadata == {}


def test_warning_record_to_dict_omits_details_when_none():
    w = WarningRecord(code="x", reason="y")
    d = w.to_dict()
    assert "details" not in d
    assert d == {"code": "x", "reason": "y"}


def test_error_record_to_dict_omits_details_when_none():
    er = ErrorRecord(code="x", message="y")
    d = er.to_dict()
    assert "details" not in d
    assert d == {"code": "x", "message": "y"}


def test_error_record_to_dict_with_details():
    er = ErrorRecord(code="x", message="y", details={"k": "v"})
    assert er.to_dict() == {"code": "x", "message": "y", "details": {"k": "v"}}


def test_document_default_collections_are_empty():
    doc = Document(
        document_id="d1",
        source_path="/tmp/x",
        source_type="pdf",
        source_hash="a" * 64,
        parser_name="test",
        parser_version="0",
    )
    assert doc.elements == []
    assert doc.chunks == []
    assert doc.relations == []
    assert doc.warnings == []
    assert doc.errors == []
    assert doc.metadata == {}


def test_document_to_dict_serializes_warnings_and_errors():
    doc = Document(
        document_id="d1",
        source_path="/tmp/x",
        source_type="pdf",
        source_hash="a" * 64,
        parser_name="test",
        parser_version="0",
        warnings=[WarningRecord(code="w1", reason="r1")],
        errors=[ErrorRecord(code="e1", message="m1")],
    )
    d = doc.to_dict()
    assert d["warnings"] == [{"code": "w1", "reason": "r1"}]
    assert d["errors"] == [{"code": "e1", "message": "m1"}]


def test_document_to_dict_metadata_pass_through():
    doc = Document(
        document_id="d1",
        source_path="/tmp/x",
        source_type="docx",
        source_hash="a" * 64,
        parser_name="test",
        parser_version="0",
        metadata={"any": "value", "nested": {"k": 1}},
    )
    d = doc.to_dict()
    assert d["metadata"] == {"any": "value", "nested": {"k": 1}}


def test_schema_version_constant_value():
    """SCHEMA_VERSION 是模块级常量，必须与 schema 里的 const 一致。"""
    assert SCHEMA_VERSION == "0.1.0"
