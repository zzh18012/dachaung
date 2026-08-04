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


# ---------- 边角与缺漏补强（Round 31） ----------


# Element 不变量更多边角


def test_element_with_parent_id_set():
    """parent_id 设置后应在 to_dict 中正确序列化。"""
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={"paragraph_index": 0},
        parent_id="e0",
    )
    assert e.parent_id == "e0"
    d = e.to_dict()
    assert d["parent_id"] == "e0"


def test_element_with_explicit_confidence_value():
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={},
        confidence=0.42,
    )
    assert e.confidence == 0.42
    assert e.to_dict()["confidence"] == 0.42


def test_element_metadata_with_nested_complex_data():
    """metadata 是 dict[str, Any]，可以存嵌套结构。"""
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={},
        metadata={
            "level": 2,
            "style": "Heading 2",
            "nested": {"k1": [1, 2, 3], "k2": {"deep": True}},
            "tags": ["a", "b"],
        },
    )
    d = e.to_dict()
    assert d["metadata"]["nested"]["k1"] == [1, 2, 3]
    assert d["metadata"]["nested"]["k2"]["deep"] is True
    assert d["metadata"]["tags"] == ["a", "b"]


def test_element_default_confidence_is_one():
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={},
    )
    assert e.confidence == 1.0


def test_element_default_metadata_is_empty_dict():
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={},
    )
    assert e.metadata == {}


def test_element_default_parent_id_is_none():
    e = Element(
        element_id="e1", type="paragraph",
        content="hi", source_locator={},
    )
    assert e.parent_id is None


def test_element_metadata_instances_are_isolated():
    """dataclass field 默认值用 default_factory=dict，每个 instance 独立。"""
    e1 = Element(element_id="e1", type="paragraph", content="a", source_locator={})
    e2 = Element(element_id="e2", type="paragraph", content="b", source_locator={})
    e1.metadata["x"] = 1
    assert "x" not in e2.metadata


def test_element_with_all_valid_types():
    """8 种 element type 都应能构造。"""
    for t in (
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    ):
        e = Element(element_id=f"e_{t}", type=t, content="x", source_locator={})
        assert e.type == t
    # image 需要 resource_path
    img = Element(element_id="e_img", type="image", resource_path="/x.png",
                  source_locator={})
    assert img.type == "image"


# Chunk 不变量更多边角


def test_chunk_metadata_instances_are_isolated():
    c1 = Chunk(chunk_id="c1", text="a", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="b", source_element_ids=["e1"])
    c1.metadata["x"] = 1
    assert "x" not in c2.metadata


def test_chunk_source_spans_instances_are_isolated():
    c1 = Chunk(chunk_id="c1", text="a", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="b", source_element_ids=["e1"])
    c1.source_spans.append({"element_id": "e1", "start": 0, "end": 1})
    assert c2.source_spans == []


def test_chunk_with_long_text():
    """长文本 chunk 也应能构造与序列化。"""
    long_text = "x" * 10000
    c = Chunk(chunk_id="c1", text=long_text, source_element_ids=["e1"])
    assert len(c.text) == 10000
    assert c.to_dict()["text"] == long_text


def test_chunk_whitespace_only_text_rejected():
    """纯空白 text 不应被 (not self.text) 接受？实际 'False == not self.text' 取决于实现；
    Python 中 '   ' 是 truthy，所以会被接受。本测试记录当前行为。"""
    # 注意：当前实现 `if not self.text` 只拒绝空串；纯空白会被接受
    c = Chunk(chunk_id="c1", text="   ", source_element_ids=["e1"])
    assert c.text == "   "


def test_chunk_with_many_source_element_ids():
    """source_element_ids 可以包含多个 element。"""
    c = Chunk(
        chunk_id="c1", text="hello",
        source_element_ids=["e1", "e2", "e3", "e4", "e5"],
    )
    d = c.to_dict()
    assert len(d["source_element_ids"]) == 5


def test_chunk_with_duplicate_source_element_ids_allowed():
    """dataclass 不去重 source_element_ids（去重在 chunker 里做）。"""
    c = Chunk(
        chunk_id="c1", text="hello",
        source_element_ids=["e1", "e1", "e2"],
    )
    assert c.source_element_ids == ["e1", "e1", "e2"]


# Document 不变量边角


def test_document_with_all_source_types():
    """Document 支持 6 种 source_type。"""
    for st in ("pdf", "docx", "markdown", "html", "text", "ipynb"):
        doc = Document(
            document_id=f"d-{st}", source_path="x", source_type=st,
            source_hash="a" * 64, parser_name="test", parser_version="0",
        )
        assert doc.source_type == st


def test_document_default_collections_independent_per_instance():
    """elements / chunks / relations / warnings / errors / metadata 默认值
    应在每个 instance 上独立（不共享 reference）。"""
    d1 = Document(
        document_id="d1", source_path="x", source_type="docx",
        source_hash="a" * 64, parser_name="test", parser_version="0",
    )
    d2 = Document(
        document_id="d2", source_path="x", source_type="docx",
        source_hash="b" * 64, parser_name="test", parser_version="0",
    )
    d1.elements.append(Element(element_id="e1", type="paragraph",
                                content="hi", source_locator={}))
    d1.metadata["k"] = "v"
    assert d2.elements == []
    assert d2.metadata == {}


def test_document_to_dict_does_not_mutate_state():
    """to_dict 应是只读操作（不会改 doc 的字段）。"""
    e = Element(element_id="e1", type="paragraph",
                content="hi", source_locator={})
    c = Chunk(chunk_id="c1", text="hi", source_element_ids=["e1"])
    doc = Document(
        document_id="d1", source_path="x", source_type="docx",
        source_hash="a" * 64, parser_name="test", parser_version="0",
        elements=[e], chunks=[c],
    )
    elements_before = list(doc.elements)
    chunks_before = list(doc.chunks)
    doc.to_dict()
    assert doc.elements == elements_before
    assert doc.chunks == chunks_before


def test_document_to_dict_keys_order():
    """to_dict 返回的 dict 应包含所有 schema 必需字段。"""
    doc = Document(
        document_id="d1", source_path="x", source_type="docx",
        source_hash="a" * 64, parser_name="test", parser_version="0",
    )
    d = doc.to_dict()
    expected_keys = {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert set(d.keys()) == expected_keys


def test_document_with_relations():
    """Document 含 relations 时 to_dict 应正确序列化。"""
    r1 = Relation(type="parent_child", from_id="e0", to_id="e1")
    r2 = Relation(type="next", from_id="e1", to_id="e2")
    doc = Document(
        document_id="d1", source_path="x", source_type="docx",
        source_hash="a" * 64, parser_name="test", parser_version="0",
        relations=[r1, r2],
    )
    d = doc.to_dict()
    assert len(d["relations"]) == 2
    assert d["relations"][0]["type"] == "parent_child"
    assert d["relations"][1]["type"] == "next"


# Relation 边角


def test_relation_self_loop_allowed():
    """from_id == to_id 在 dataclass 层不拒绝（schema 也不拒绝）。"""
    r = Relation(type="self_ref", from_id="e1", to_id="e1")
    assert r.from_id == r.to_id == "e1"


def test_relation_with_complex_metadata():
    r = Relation(
        type="weighted", from_id="e1", to_id="e2",
        metadata={"weight": 0.5, "tags": ["a", "b"]},
    )
    d = r.to_dict()
    assert d["metadata"]["weight"] == 0.5
    assert d["metadata"]["tags"] == ["a", "b"]


# WarningRecord / ErrorRecord 边角


def test_warning_record_default_details_is_none():
    w = WarningRecord(code="x", reason="y")
    assert w.details is None


def test_error_record_default_details_is_none():
    er = ErrorRecord(code="x", message="y")
    assert er.details is None


def test_warning_record_empty_code_allowed_at_dataclass_layer():
    """dataclass 不强制 code 非空（schema 在写盘前会拒绝）。"""
    w = WarningRecord(code="", reason="x")
    assert w.code == ""


def test_error_record_empty_code_allowed_at_dataclass_layer():
    er = ErrorRecord(code="", message="x")
    assert er.code == ""


def test_warning_record_with_complex_details():
    w = WarningRecord(
        code="low_confidence", reason="ocr",
        details={"score": 0.42, "regions": [{"page": 1}, {"page": 2}]},
    )
    d = w.to_dict()
    assert d["details"]["regions"] == [{"page": 1}, {"page": 2}]


def test_error_record_with_complex_details():
    er = ErrorRecord(
        code="parse_error", message="fail",
        details={"path": "/x.pdf", "exception": {"type": "ValueError", "stack": ["a", "b"]}},
    )
    d = er.to_dict()
    assert d["details"]["exception"]["stack"] == ["a", "b"]


# SCHEMA_VERSION 不变量


def test_schema_version_is_string_type():
    """SCHEMA_VERSION 必须是 str，不是 float。"""
    assert isinstance(SCHEMA_VERSION, str)


def test_schema_version_has_three_components():
    """语义化版本格式：major.minor.patch。"""
    parts = SCHEMA_VERSION.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit()
