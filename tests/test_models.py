"""统一文档模型 dataclass 的单元测试。"""

from __future__ import annotations

import pytest

from app.models import (
    Chunk,
    Document,
    Element,
    ErrorRecord,
    Relation,
    SCHEMA_VERSION_TABLE_CAPTION,
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
    assert d["schema_version"] == SCHEMA_VERSION_TABLE_CAPTION
    assert set(d.keys()) >= {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert d["elements"][0]["element_id"] == "e1"
    assert d["chunks"][0]["source_element_ids"] == ["e1"]
