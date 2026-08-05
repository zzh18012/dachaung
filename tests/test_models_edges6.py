r"""app/models.py 边角测试 - 第六轮（Round 172）。

补强已有 base/edges/edges2-5（共 474 测试）未覆盖的深度：
- SCHEMA_VERSION 常量
- ElementType / SourceType 各合法值
- Element/Chunk/Relation/WarningRecord/ErrorRecord/Document 各 dataclass
- to_dict 字段顺序与默认值
- __post_init__ 校验路径
- 模块结构
- 综合行为
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, fields, is_dataclass
from typing import Any, get_args, get_origin

import pytest

from app.models import (
    SCHEMA_VERSION,
    Document,
    Element,
    ElementType,
    ErrorRecord,
    Relation,
    SourceType,
    WarningRecord,
    Chunk,
)


# =========================================================================
# SCHEMA_VERSION 常量
# =========================================================================


def test_schema_version_value():
    assert SCHEMA_VERSION == "0.1.0"


def test_schema_version_is_str():
    assert isinstance(SCHEMA_VERSION, str)


def test_schema_version_format():
    """X.Y.Z 格式。"""
    parts = SCHEMA_VERSION.split(".")
    assert len(parts) == 3
    for p in parts:
        assert p.isdigit()


# =========================================================================
# ElementType / SourceType Literal
# =========================================================================


def test_element_type_args_exact():
    args = set(get_args(ElementType))
    assert args == {
        "heading", "paragraph", "list_item", "table", "image", "caption", "header", "footer"
    }


def test_element_type_args_count_8():
    args = get_args(ElementType)
    assert len(args) == 8


def test_source_type_args_exact():
    args = set(get_args(SourceType))
    assert args == {"pdf", "docx", "markdown", "html", "text", "ipynb"}


def test_source_type_args_count_6():
    args = get_args(SourceType)
    assert len(args) == 6


# =========================================================================
# Element dataclass
# =========================================================================


def test_element_is_dataclass():
    assert is_dataclass(Element)


def test_element_field_count_8():
    fs = fields(Element)
    assert len(fs) == 8


def test_element_field_names_exact():
    fs = fields(Element)
    names = {f.name for f in fs}
    assert names == {
        "element_id",
        "type",
        "source_locator",
        "parent_id",
        "content",
        "resource_path",
        "confidence",
        "metadata",
    }


def test_element_required_fields_no_default():
    """element_id/type/source_locator 必填（无 default）。"""
    fs = {f.name: f for f in fields(Element)}
    from dataclasses import _MISSING_TYPE
    for name in ("element_id", "type", "source_locator"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_element_optional_fields_defaults():
    fs = {f.name: f for f in fields(Element)}
    assert fs["parent_id"].default is None
    assert fs["content"].default is None
    assert fs["resource_path"].default is None
    assert fs["confidence"].default == 1.0


def test_element_metadata_default_factory_dict():
    """metadata 用 default_factory=dict（每实例独立）。"""
    fs = {f.name: f for f in fields(Element)}
    assert callable(fs["metadata"].default_factory)


def test_element_post_init_empty_id_raises():
    with pytest.raises(ValueError) as exc:
        Element(element_id="", type="paragraph", source_locator={}, content="x")
    assert "不能为空" in str(exc.value)


def test_element_post_init_no_content_no_resource_raises():
    with pytest.raises(ValueError) as exc:
        Element(element_id="e1", type="paragraph", source_locator={})
    assert "至少有 content 或 resource_path" in str(exc.value)


def test_element_post_init_empty_content_no_resource_raises():
    """content='' falsy 且 resource_path=None → raise。"""
    with pytest.raises(ValueError):
        Element(element_id="e1", type="paragraph", source_locator={}, content="")


def test_element_post_init_only_resource_path_ok():
    """resource_path 给值（content=None）→ OK。"""
    e = Element(
        element_id="e1",
        type="image",
        source_locator={},
        content=None,
        resource_path="path.png",
    )
    assert e.resource_path == "path.png"


def test_element_post_init_both_content_and_resource_path_ok():
    e = Element(
        element_id="e1",
        type="table",
        source_locator={},
        content="x",
        resource_path="y",
    )
    assert e.content == "x"
    assert e.resource_path == "y"


def test_element_to_dict_returns_dict():
    e = Element(element_id="e1", type="paragraph", source_locator={"line": 1}, content="x")
    d = e.to_dict()
    assert isinstance(d, dict)


def test_element_to_dict_has_all_fields():
    e = Element(element_id="e1", type="paragraph", source_locator={"line": 1}, content="x")
    d = e.to_dict()
    assert set(d.keys()) == {
        "element_id", "type", "source_locator", "parent_id",
        "content", "resource_path", "confidence", "metadata",
    }


def test_element_to_dict_value_preserved():
    e = Element(
        element_id="e1",
        type="heading",
        source_locator={"page": 1},
        parent_id="p1",
        content="Title",
        confidence=0.8,
        metadata={"level": 1},
    )
    d = e.to_dict()
    assert d["element_id"] == "e1"
    assert d["type"] == "heading"
    assert d["source_locator"] == {"page": 1}
    assert d["parent_id"] == "p1"
    assert d["content"] == "Title"
    assert d["confidence"] == 0.8
    assert d["metadata"] == {"level": 1}


# =========================================================================
# Chunk dataclass
# =========================================================================


def test_chunk_is_dataclass():
    assert is_dataclass(Chunk)


def test_chunk_field_count_5():
    assert len(fields(Chunk)) == 5


def test_chunk_field_names_exact():
    fs = fields(Chunk)
    names = {f.name for f in fs}
    assert names == {"chunk_id", "text", "source_element_ids", "metadata", "source_spans"}


def test_chunk_required_fields():
    fs = {f.name: f for f in fields(Chunk)}
    from dataclasses import _MISSING_TYPE
    for name in ("chunk_id", "text", "source_element_ids"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_chunk_optional_defaults():
    fs = {f.name: f for f in fields(Chunk)}
    assert callable(fs["metadata"].default_factory)
    assert callable(fs["source_spans"].default_factory)


def test_chunk_post_init_empty_chunk_id_raises():
    with pytest.raises(ValueError) as exc:
        Chunk(chunk_id="", text="x", source_element_ids=["e1"])
    assert "chunk_id" in str(exc.value)


def test_chunk_post_init_empty_source_ids_raises():
    with pytest.raises(ValueError) as exc:
        Chunk(chunk_id="c1", text="x", source_element_ids=[])
    assert "source_element_id" in str(exc.value)


def test_chunk_post_init_empty_text_raises():
    with pytest.raises(ValueError) as exc:
        Chunk(chunk_id="c1", text="", source_element_ids=["e1"])
    assert "文本不能为空" in str(exc.value)


def test_chunk_to_dict_returns_dict():
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    assert isinstance(c.to_dict(), dict)


def test_chunk_to_dict_has_all_fields():
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    d = c.to_dict()
    assert set(d.keys()) == {"chunk_id", "text", "source_element_ids", "metadata", "source_spans"}


# =========================================================================
# Relation dataclass
# =========================================================================


def test_relation_is_dataclass():
    assert is_dataclass(Relation)


def test_relation_field_count_4():
    assert len(fields(Relation)) == 4


def test_relation_field_names_exact():
    fs = fields(Relation)
    names = {f.name for f in fs}
    assert names == {"type", "from_id", "to_id", "metadata"}


def test_relation_required_fields():
    fs = {f.name: f for f in fields(Relation)}
    from dataclasses import _MISSING_TYPE
    for name in ("type", "from_id", "to_id"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_relation_metadata_default_factory():
    fs = {f.name: f for f in fields(Relation)}
    assert callable(fs["metadata"].default_factory)


def test_relation_to_dict_returns_dict():
    r = Relation(type="parent", from_id="a", to_id="b")
    assert isinstance(r.to_dict(), dict)


def test_relation_to_dict_has_all_fields():
    r = Relation(type="parent", from_id="a", to_id="b", metadata={"k": "v"})
    d = r.to_dict()
    assert set(d.keys()) == {"type", "from_id", "to_id", "metadata"}


# =========================================================================
# WarningRecord dataclass
# =========================================================================


def test_warning_record_is_dataclass():
    assert is_dataclass(WarningRecord)


def test_warning_record_field_count_3():
    assert len(fields(WarningRecord)) == 3


def test_warning_record_field_names_exact():
    fs = fields(WarningRecord)
    names = {f.name for f in fs}
    assert names == {"code", "reason", "details"}


def test_warning_record_required_fields():
    fs = {f.name: f for f in fields(WarningRecord)}
    from dataclasses import _MISSING_TYPE
    for name in ("code", "reason"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_warning_record_details_default_none():
    fs = {f.name: f for f in fields(WarningRecord)}
    assert fs["details"].default is None


def test_warning_record_to_dict_no_details():
    """details=None → to_dict 不含 details 键。"""
    w = WarningRecord(code="x", reason="y")
    d = w.to_dict()
    assert "details" not in d
    assert d == {"code": "x", "reason": "y"}


def test_warning_record_to_dict_with_details():
    w = WarningRecord(code="x", reason="y", details={"k": "v"})
    d = w.to_dict()
    assert d["details"] == {"k": "v"}


def test_warning_record_to_dict_returns_dict():
    w = WarningRecord(code="x", reason="y")
    assert isinstance(w.to_dict(), dict)


# =========================================================================
# ErrorRecord dataclass
# =========================================================================


def test_error_record_is_dataclass():
    assert is_dataclass(ErrorRecord)


def test_error_record_field_count_3():
    assert len(fields(ErrorRecord)) == 3


def test_error_record_field_names_exact():
    fs = fields(ErrorRecord)
    names = {f.name for f in fs}
    assert names == {"code", "message", "details"}


def test_error_record_required_fields():
    fs = {f.name: f for f in fields(ErrorRecord)}
    from dataclasses import _MISSING_TYPE
    for name in ("code", "message"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_error_record_details_default_none():
    fs = {f.name: f for f in fields(ErrorRecord)}
    assert fs["details"].default is None


def test_error_record_to_dict_no_details():
    e = ErrorRecord(code="x", message="y")
    d = e.to_dict()
    assert "details" not in d
    assert d == {"code": "x", "message": "y"}


def test_error_record_to_dict_with_details():
    e = ErrorRecord(code="x", message="y", details={"k": "v"})
    d = e.to_dict()
    assert d["details"] == {"k": "v"}


# =========================================================================
# Document dataclass
# =========================================================================


def test_document_is_dataclass():
    assert is_dataclass(Document)


def test_document_field_count_12():
    assert len(fields(Document)) == 12


def test_document_field_names_exact():
    fs = fields(Document)
    names = {f.name for f in fs}
    assert names == {
        "document_id", "source_path", "source_type", "source_hash",
        "parser_name", "parser_version",
        "elements", "chunks", "relations",
        "warnings", "errors", "metadata",
    }


def test_document_required_fields():
    fs = {f.name: f for f in fields(Document)}
    from dataclasses import _MISSING_TYPE
    for name in ("document_id", "source_path", "source_type", "source_hash", "parser_name", "parser_version"):
        assert isinstance(fs[name].default, _MISSING_TYPE)


def test_document_collection_fields_default_factory():
    """elements/chunks/relations/warnings/errors/metadata 都用 default_factory。"""
    fs = {f.name: f for f in fields(Document)}
    for name in ("elements", "chunks", "relations", "warnings", "errors", "metadata"):
        assert callable(fs[name].default_factory)


def test_document_to_dict_returns_dict():
    d = _minimal_doc()
    assert isinstance(d.to_dict(), dict)


def test_document_to_dict_has_schema_version():
    d = _minimal_doc()
    out = d.to_dict()
    assert "schema_version" in out
    assert out["schema_version"] == SCHEMA_VERSION


def test_document_to_dict_has_all_top_keys():
    d = _minimal_doc()
    out = d.to_dict()
    expected = {
        "schema_version", "document_id", "source_path", "source_type", "source_hash",
        "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert set(out.keys()) == expected


def test_document_to_dict_serializes_nested():
    """to_dict 应递归调用 Element.to_dict 等。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    r = Relation(type="parent", from_id="a", to_id="b")
    w = WarningRecord(code="x", reason="y")
    er = ErrorRecord(code="x", message="y")
    d = _minimal_doc()
    d.elements = [e]
    d.chunks = [c]
    d.relations = [r]
    d.warnings = [w]
    d.errors = [er]
    out = d.to_dict()
    assert isinstance(out["elements"][0], dict)
    assert isinstance(out["chunks"][0], dict)
    assert isinstance(out["relations"][0], dict)
    assert isinstance(out["warnings"][0], dict)
    assert isinstance(out["errors"][0], dict)


def _minimal_doc() -> Document:
    return Document(
        document_id="doc-x",
        source_path="/tmp/x.txt",
        source_type="text",
        source_hash="a" * 64,
        parser_name="text",
        parser_version="1.0",
    )


# =========================================================================
# 模块结构
# =========================================================================


def test_module_no_explicit_all():
    """models.py 没有 __all__（全部公共导出）。"""
    import app.models as mod
    assert not hasattr(mod, "__all__")


def test_module_uses_future_annotations():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_dataclass():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from dataclasses import" in src
    for name in ("dataclass", "field", "asdict"):
        assert name in src


def test_module_imports_typing():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from typing import" in src
    for name in ("Any", "Literal", "Optional"):
        assert name in src


def test_module_docstring_present():
    import app.models as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_business_code_isolation():
    """docstring 提及业务代码不依赖 Kreuzberg/pdfplumber/python-docx。"""
    import app.models as mod
    doc = mod.__doc__
    assert "业务代码" in doc
    assert "Kreuzberg" in doc or "pdfplumber" in doc


def test_module_exports_all_dataclasses():
    import app.models as mod
    for cls in (Element, Chunk, Relation, WarningRecord, ErrorRecord, Document):
        assert hasattr(mod, cls.__name__)


def test_module_exports_constants():
    import app.models as mod
    assert hasattr(mod, "SCHEMA_VERSION")
    assert hasattr(mod, "ElementType")
    assert hasattr(mod, "SourceType")


def test_module_no_silence_unused():
    import app.models as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_element_to_dict_equivalent_to_asdict():
    """Element.to_dict() == asdict(e)（直接调用 asdict）。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.to_dict() == asdict(e)


def test_chunk_to_dict_equivalent_to_asdict():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.to_dict() == asdict(c)


def test_relation_to_dict_equivalent_to_asdict():
    r = Relation(type="t", from_id="a", to_id="b")
    assert r.to_dict() == asdict(r)


def test_warning_record_to_dict_differs_from_asdict():
    """WarningRecord.to_dict 自定义（None details 时不含键），与 asdict 不同。"""
    w = WarningRecord(code="x", reason="y")
    assert w.to_dict() != asdict(w)
    # asdict 会保留 details=None


def test_error_record_to_dict_differs_from_asdict():
    e = ErrorRecord(code="x", message="y")
    assert e.to_dict() != asdict(e)


def test_warning_record_to_dict_idempotent():
    w = WarningRecord(code="x", reason="y", details={"k": "v"})
    assert w.to_dict() == w.to_dict()


def test_element_post_init_message_has_id():
    try:
        Element(element_id="myid", type="paragraph", source_locator={})
    except ValueError as e:
        assert "myid" in str(e)


def test_chunk_post_init_message_has_id():
    try:
        Chunk(chunk_id="mychunk", text="", source_element_ids=["e1"])
    except ValueError as e:
        assert "mychunk" in str(e)


def test_metadata_default_factory_per_instance():
    """Element 默认 metadata 在不同实例间独立。"""
    a = Element(element_id="a", type="paragraph", source_locator={}, content="x")
    b = Element(element_id="b", type="paragraph", source_locator={}, content="x")
    a.metadata["k"] = "v"
    assert "k" not in b.metadata
