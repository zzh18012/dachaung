r"""app/models.py 边角测试 - 第五轮（Round 142）。

补强已有 base/edges/edges2/edges3（共 307 测试）未覆盖的深度：
- SCHEMA_VERSION 常量
- Element/Chunk __post_init__ 边界（empty id / empty content / empty resource）
- Relation/WarningRecord/ErrorRecord to_dict 字段顺序
- Document to_dict 含 schema_version + 13 个键
- dataclass 字段顺序与默认值
- Element.metadata default_factory 独立实例
- Chunk.metadata/source_spans default_factory
- 模块结构
- 签名深度
"""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, is_dataclass, fields
from typing import Any, get_args, get_origin

import pytest

from app.models import (
    SCHEMA_VERSION,
    Chunk,
    Document,
    Element,
    ErrorRecord,
    Relation,
    SourceType,
    WarningRecord,
)
from app.models import (
    ElementType as _ElementType,
)
import app.models as _models_module


# =========================================================================
# SCHEMA_VERSION 常量
# =========================================================================


def test_schema_version_is_str():
    assert isinstance(SCHEMA_VERSION, str)


def test_schema_version_value():
    assert SCHEMA_VERSION == "0.1.0"


# =========================================================================
# ElementType / SourceType
# =========================================================================


def test_element_type_values():
    args = get_args(_ElementType)
    assert set(args) == {
        "heading", "paragraph", "list_item", "table",
        "image", "caption", "header", "footer",
    }


def test_element_type_count_eight():
    args = get_args(_ElementType)
    assert len(args) == 8


def test_source_type_values():
    args = get_args(SourceType)
    assert set(args) == {"pdf", "docx", "markdown", "html", "text", "ipynb"}


def test_source_type_count_six():
    args = get_args(SourceType)
    assert len(args) == 6


# =========================================================================
# Element __post_init__ 边界
# =========================================================================


def test_element_empty_id_raises():
    with pytest.raises(ValueError, match="element_id"):
        Element(
            element_id="",
            type="paragraph",
            content="x",
            source_locator={"line": 1},
        )


def test_element_both_content_and_resource_path_ok():
    """content 和 resource_path 都给 → OK。"""
    e = Element(
        element_id="e1",
        type="image",
        content="caption",
        resource_path="img.png",
        source_locator={"line": 1},
    )
    assert e.content == "caption"
    assert e.resource_path == "img.png"


def test_element_content_only_ok():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
    )
    assert e.content == "hello"
    assert e.resource_path is None


def test_element_resource_path_only_ok():
    e = Element(
        element_id="e1",
        type="image",
        resource_path="img.png",
        source_locator={"line": 1},
    )
    assert e.resource_path == "img.png"
    assert e.content is None


def test_element_empty_content_string_treated_as_falsy():
    """content='' → falsy → 需要 resource_path 兜底。"""
    with pytest.raises(ValueError):
        Element(
            element_id="e1",
            type="paragraph",
            content="",
            source_locator={"line": 1},
        )


def test_element_empty_content_with_resource_path_ok():
    """content='' + resource_path → OK（resource_path 兜底）。"""
    e = Element(
        element_id="e1",
        type="image",
        content="",
        resource_path="img.png",
        source_locator={"line": 1},
    )
    assert e.resource_path == "img.png"


def test_element_default_confidence_one():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
    )
    assert e.confidence == 1.0


def test_element_default_metadata_independent_per_instance():
    """default_factory=field(dict) → 每个实例的 metadata 是独立 dict。"""
    e1 = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
    )
    e2 = Element(
        element_id="e2",
        type="paragraph",
        content="y",
        source_locator={"line": 1},
    )
    e1.metadata["k"] = "v1"
    assert "k" not in e2.metadata


def test_element_to_dict_returns_dict():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
    )
    d = e.to_dict()
    assert isinstance(d, dict)


def test_element_to_dict_contains_all_fields():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
    )
    d = e.to_dict()
    expected = {
        "element_id", "type", "source_locator", "parent_id",
        "content", "resource_path", "confidence", "metadata",
    }
    assert set(d.keys()) == expected


# =========================================================================
# Element 字段顺序
# =========================================================================


def test_element_field_order():
    flds = [f.name for f in fields(Element)]
    # 必填字段在前，可选字段在后
    assert flds == [
        "element_id",
        "type",
        "source_locator",
        "parent_id",
        "content",
        "resource_path",
        "confidence",
        "metadata",
    ]


def test_element_field_count_eight():
    assert len(fields(Element)) == 8


# =========================================================================
# Chunk __post_init__ 边界
# =========================================================================


def test_chunk_empty_id_raises():
    with pytest.raises(ValueError, match="chunk_id"):
        Chunk(
            chunk_id="",
            text="hello",
            source_element_ids=["e1"],
        )


def test_chunk_empty_text_raises():
    with pytest.raises(ValueError, match="文本不能为空"):
        Chunk(
            chunk_id="c1",
            text="",
            source_element_ids=["e1"],
        )


def test_chunk_empty_source_ids_raises():
    with pytest.raises(ValueError, match="至少要有一个"):
        Chunk(
            chunk_id="c1",
            text="hello",
            source_element_ids=[],
        )


def test_chunk_minimal_valid():
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    assert c.chunk_id == "c1"
    assert c.text == "hello"
    assert c.source_element_ids == ["e1"]


def test_chunk_default_metadata_independent():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e2"])
    c1.metadata["k"] = "v"
    assert "k" not in c2.metadata


def test_chunk_default_source_spans_independent():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e2"])
    c1.source_spans.append({"start": 0, "end": 1})
    assert c2.source_spans == []


def test_chunk_field_order():
    flds = [f.name for f in fields(Chunk)]
    assert flds == [
        "chunk_id",
        "text",
        "source_element_ids",
        "metadata",
        "source_spans",
    ]


def test_chunk_field_count_five():
    assert len(fields(Chunk)) == 5


def test_chunk_to_dict_keys():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d = c.to_dict()
    expected = {"chunk_id", "text", "source_element_ids", "metadata", "source_spans"}
    assert set(d.keys()) == expected


# =========================================================================
# Relation 深度
# =========================================================================


def test_relation_to_dict_keys():
    r = Relation(type="parent", from_id="e1", to_id="e2")
    d = r.to_dict()
    assert set(d.keys()) == {"type", "from_id", "to_id", "metadata"}


def test_relation_default_metadata_independent():
    r1 = Relation(type="x", from_id="a", to_id="b")
    r2 = Relation(type="y", from_id="c", to_id="d")
    r1.metadata["k"] = "v"
    assert "k" not in r2.metadata


def test_relation_field_order():
    flds = [f.name for f in fields(Relation)]
    assert flds == ["type", "from_id", "to_id", "metadata"]


def test_relation_field_count_four():
    assert len(fields(Relation)) == 4


def test_relation_to_dict_returns_dict():
    r = Relation(type="x", from_id="a", to_id="b")
    assert isinstance(r.to_dict(), dict)


# =========================================================================
# WarningRecord 深度
# =========================================================================


def test_warning_record_to_dict_minimal():
    w = WarningRecord(code="warn", reason="x")
    d = w.to_dict()
    # 默认 details=None → to_dict 不含 details
    assert set(d.keys()) == {"code", "reason"}


def test_warning_record_to_dict_with_details():
    w = WarningRecord(code="warn", reason="x", details={"k": "v"})
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason", "details"}
    assert d["details"] == {"k": "v"}


def test_warning_record_to_dict_details_none_omitted():
    """details=None → 字段不出现在 to_dict 输出。"""
    w = WarningRecord(code="warn", reason="x", details=None)
    d = w.to_dict()
    assert "details" not in d


def test_warning_record_field_order():
    flds = [f.name for f in fields(WarningRecord)]
    assert flds == ["code", "reason", "details"]


def test_warning_record_field_count_three():
    assert len(fields(WarningRecord)) == 3


# =========================================================================
# ErrorRecord 深度
# =========================================================================


def test_error_record_to_dict_minimal():
    e = ErrorRecord(code="err", message="x")
    d = e.to_dict()
    assert set(d.keys()) == {"code", "message"}


def test_error_record_to_dict_with_details():
    e = ErrorRecord(code="err", message="x", details={"k": "v"})
    d = e.to_dict()
    assert set(d.keys()) == {"code", "message", "details"}


def test_error_record_to_dict_details_none_omitted():
    e = ErrorRecord(code="err", message="x", details=None)
    d = e.to_dict()
    assert "details" not in d


def test_error_record_field_order():
    flds = [f.name for f in fields(ErrorRecord)]
    assert flds == ["code", "message", "details"]


def test_error_record_field_count_three():
    assert len(fields(ErrorRecord)) == 3


# =========================================================================
# Document 深度
# =========================================================================


def test_document_to_dict_keys_count_thirteen():
    """schema_version + 12 Document 自身字段 = 13。"""
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
    )
    out = d.to_dict()
    assert len(out) == 13


def test_document_to_dict_contains_schema_version():
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
    )
    out = d.to_dict()
    assert out["schema_version"] == SCHEMA_VERSION


def test_document_to_dict_elements_serialized():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
    )
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        elements=[e],
    )
    out = d.to_dict()
    assert out["elements"] == [e.to_dict()]


def test_document_to_dict_chunks_serialized():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        chunks=[c],
    )
    out = d.to_dict()
    assert out["chunks"] == [c.to_dict()]


def test_document_to_dict_relations_serialized():
    r = Relation(type="parent", from_id="a", to_id="b")
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        relations=[r],
    )
    out = d.to_dict()
    assert out["relations"] == [r.to_dict()]


def test_document_to_dict_warnings_serialized():
    w = WarningRecord(code="warn", reason="x")
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        warnings=[w],
    )
    out = d.to_dict()
    assert out["warnings"] == [w.to_dict()]


def test_document_to_dict_errors_serialized():
    er = ErrorRecord(code="err", message="x")
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        errors=[er],
    )
    out = d.to_dict()
    assert out["errors"] == [er.to_dict()]


def test_document_default_metadata_independent():
    d1 = Document(
        document_id="d1", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d2 = Document(
        document_id="d2", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d1.metadata["k"] = "v"
    assert "k" not in d2.metadata


def test_document_field_order():
    flds = [f.name for f in fields(Document)]
    assert flds == [
        "document_id", "source_path", "source_type", "source_hash",
        "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors",
        "metadata",
    ]


def test_document_field_count_twelve():
    assert len(fields(Document)) == 12


# =========================================================================
# dataclass 属性
# =========================================================================


def test_element_is_dataclass():
    assert is_dataclass(Element)


def test_chunk_is_dataclass():
    assert is_dataclass(Chunk)


def test_relation_is_dataclass():
    assert is_dataclass(Relation)


def test_warning_record_is_dataclass():
    assert is_dataclass(WarningRecord)


def test_error_record_is_dataclass():
    assert is_dataclass(ErrorRecord)


def test_document_is_dataclass():
    assert is_dataclass(Document)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_no_all_attribute():
    """app/models.py 不定义 __all__（公开 API 通过模块属性访问）。"""
    assert not hasattr(_models_module, "__all__")


def test_module_imports_dataclasses():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import" in src


def test_module_imports_typing():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from typing import" in src


def test_module_uses_future_annotations():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.models as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_dataclass():
    import app.models as mod
    assert "dataclass" in mod.__doc__.lower()


# =========================================================================
# 签名深度（to_dict / __post_init__）
# =========================================================================


def test_element_to_dict_no_args():
    sig = inspect.signature(Element.to_dict)
    assert len(sig.parameters) == 1  # self


def test_chunk_to_dict_no_args():
    sig = inspect.signature(Chunk.to_dict)
    assert len(sig.parameters) == 1


def test_relation_to_dict_no_args():
    sig = inspect.signature(Relation.to_dict)
    assert len(sig.parameters) == 1


def test_warning_record_to_dict_no_args():
    sig = inspect.signature(WarningRecord.to_dict)
    assert len(sig.parameters) == 1


def test_error_record_to_dict_no_args():
    sig = inspect.signature(ErrorRecord.to_dict)
    assert len(sig.parameters) == 1


def test_document_to_dict_no_args():
    sig = inspect.signature(Document.to_dict)
    assert len(sig.parameters) == 1


# =========================================================================
# JSON 序列化
# =========================================================================


def test_element_to_dict_json_serializable():
    import json
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1, "page": 1},
        metadata={"k": "v"},
    )
    s = json.dumps(e.to_dict())
    parsed = json.loads(s)
    assert parsed["element_id"] == "e1"


def test_chunk_to_dict_json_serializable():
    import json
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1"],
        metadata={"strategy": "x"},
        source_spans=[{"element_id": "e1", "start": 0, "end": 5}],
    )
    s = json.dumps(c.to_dict())
    parsed = json.loads(s)
    assert parsed["chunk_id"] == "c1"


def test_document_to_dict_json_serializable():
    import json
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
    )
    d = Document(
        document_id="d1",
        source_path="x.pdf",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="fallback",
        parser_version="1.0",
        elements=[e],
    )
    s = json.dumps(d.to_dict())
    parsed = json.loads(s)
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert parsed["document_id"] == "d1"


# =========================================================================
# Element / Chunk 边界值
# =========================================================================


def test_element_with_all_optional_fields():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={"line": 1},
        parent_id="parent",
        content="hello",
        resource_path=None,
        confidence=0.8,
        metadata={"lang": "en"},
    )
    assert e.parent_id == "parent"
    assert e.confidence == 0.8
    assert e.metadata == {"lang": "en"}


def test_chunk_with_metadata_and_spans():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1", "e2"],
        metadata={"strategy": "sequential", "char_count": 5},
        source_spans=[
            {"element_id": "e1", "start": 0, "end": 5},
            {"element_id": "e2", "start": 0, "end": 0},
        ],
    )
    assert c.metadata["char_count"] == 5
    assert len(c.source_spans) == 2


def test_document_with_all_list_fields_populated():
    e = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    r = Relation(type="x", from_id="a", to_id="b")
    w = WarningRecord(code="w", reason="r")
    er = ErrorRecord(code="e", message="m")
    d = Document(
        document_id="d1", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
        elements=[e], chunks=[c], relations=[r],
        warnings=[w], errors=[er],
        metadata={"key": "value"},
    )
    out = d.to_dict()
    assert len(out["elements"]) == 1
    assert len(out["chunks"]) == 1
    assert len(out["relations"]) == 1
    assert len(out["warnings"]) == 1
    assert len(out["errors"]) == 1
