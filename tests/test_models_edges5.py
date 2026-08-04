r"""app/models.py 边角测试 - 第六轮（Round 149）。

补强已有 base/edges/edges2/edges3/edges4（共 383 测试）未覆盖的深度：
- 模块结构（imports 细节、SCHEMA_VERSION 值、Literal 类型）
- Element 特殊值（resource_path=""、confidence 边界、metadata 多类型）
- Chunk 特殊值（text=" " 空白、source_element_ids 含空字符串、source_spans）
- Relation 特殊值（type=""、from_id=""、to_id=""、metadata 类型）
- WarningRecord/ErrorRecord 边界对比
- Document 默认值独立性、to_dict 引用关系
- asdict 行为对比
- round-trip 序列化
- dataclass 字段默认值类型
"""

from __future__ import annotations

import inspect
from dataclasses import asdict, fields, is_dataclass
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


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_asdict():
    """models.py 应导入 asdict（用于 to_dict）。"""
    import app.models as mod
    src = inspect.getsource(mod)
    assert "asdict" in src


def test_module_imports_dataclass_decorator():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "@dataclass" in src


def test_module_imports_field():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "field(" in src


def test_module_imports_optional():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "Optional" in src


def test_module_imports_literal():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "Literal" in src


def test_module_imports_any():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "Any" in src


def test_module_no_all_attribute():
    import app.models as mod
    assert not hasattr(mod, "__all__")


def test_module_uses_future_annotations():
    import app.models as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_mentions_unified():
    """docstring 应提及"统一"。"""
    import app.models as mod
    assert "统一" in mod.__doc__ or "Unified" in mod.__doc__


def test_module_docstring_mentions_dataclass():
    import app.models as mod
    assert "dataclass" in mod.__doc__.lower()


def test_module_has_six_dataclasses():
    """应定义 6 个 @dataclass：Element/Chunk/Relation/WarningRecord/ErrorRecord/Document。"""
    import app.models as mod
    classes = [
        v for k, v in vars(mod).items()
        if inspect.isclass(v) and is_dataclass(v)
    ]
    # 仅直接定义（不在 import 中）
    defined = [c for c in classes if c.__module__ == "app.models"]
    assert {c.__name__ for c in defined} == {
        "Element", "Chunk", "Relation",
        "WarningRecord", "ErrorRecord", "Document",
    }


# =========================================================================
# SCHEMA_VERSION / Literal 类型
# =========================================================================


def test_schema_version_value_0_1_0():
    assert SCHEMA_VERSION == "0.1.0"


def test_schema_version_pattern():
    """X.Y.Z 格式。"""
    import re
    assert re.match(r"^\d+\.\d+\.\d+$", SCHEMA_VERSION)


def test_element_type_is_literal():
    """ElementType 是 typing.Literal。"""
    assert get_origin(_ElementType) is not None


def test_source_type_is_literal():
    assert get_origin(SourceType) is not None


def test_element_type_count_matches_source():
    """ElementType 8 项，SourceType 6 项。"""
    assert len(get_args(_ElementType)) == 8
    assert len(get_args(SourceType)) == 6


# =========================================================================
# Element 特殊值
# =========================================================================


def test_element_resource_path_empty_string_only_ok():
    """content=None + resource_path="" → falsy → 应 raise。"""
    with pytest.raises(ValueError):
        Element(
            element_id="e1",
            type="paragraph",
            resource_path="",
            source_locator={"line": 1},
        )


def test_element_both_empty_strings_raises():
    """content='' + resource_path='' → 都 falsy → raise。"""
    with pytest.raises(ValueError):
        Element(
            element_id="e1",
            type="paragraph",
            content="",
            resource_path="",
            source_locator={"line": 1},
        )


def test_element_whitespace_content_ok():
    """content=' '（空白）→ truthy → OK。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content=" ",
        source_locator={"line": 1},
    )
    assert e.content == " "


def test_element_whitespace_resource_path_ok():
    """resource_path=' '（空白）→ truthy → OK（虽不合理但 dataclass 不挡）。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        resource_path=" ",
        source_locator={"line": 1},
    )
    assert e.resource_path == " "


def test_element_confidence_int_zero():
    """int 0 → 应被 dataclass 接受（confidence: float = 1.0）。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        confidence=0,
    )
    # dataclass 不强制类型转换
    assert e.confidence == 0


def test_element_confidence_float_zero():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        confidence=0.0,
    )
    assert e.confidence == 0.0


def test_element_confidence_int_one():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        confidence=1,
    )
    assert e.confidence == 1


def test_element_metadata_accepts_nested_dict():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        metadata={"outer": {"inner": "value"}},
    )
    assert e.metadata["outer"]["inner"] == "value"


def test_element_metadata_accepts_list_value():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        metadata={"tags": ["a", "b", "c"]},
    )
    assert e.metadata["tags"] == ["a", "b", "c"]


def test_element_metadata_accepts_int_value():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        metadata={"count": 42},
    )
    assert e.metadata["count"] == 42


def test_element_metadata_accepts_none_value():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        metadata={"k": None},
    )
    assert e.metadata["k"] is None


def test_element_metadata_accepts_bool_value():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"line": 1},
        metadata={"flag": True},
    )
    assert e.metadata["flag"] is True


def test_element_source_locator_empty_dict_ok():
    """source_locator 必填但可以是空 dict。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={},
    )
    assert e.source_locator == {}


def test_element_source_locator_with_multiple_keys():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={"page": 1, "bbox": [0, 0, 100, 100], "line": 5},
    )
    assert set(e.source_locator.keys()) == {"page", "bbox", "line"}


def test_element_parent_id_default_none():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={},
    )
    assert e.parent_id is None


def test_element_parent_id_explicit_value():
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={},
        parent_id="parent123",
    )
    assert e.parent_id == "parent123"


def test_element_to_dict_returns_new_dict_each_call():
    """to_dict 每次返回新 dict（asdict 行为）。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={},
    )
    d1 = e.to_dict()
    d2 = e.to_dict()
    assert d1 == d2
    assert d1 is not d2


def test_element_to_dict_metadata_modification_no_back_effect():
    """修改 to_dict 返回的 metadata 不影响原 Element。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content="x",
        source_locator={},
        metadata={"k": "v"},
    )
    d = e.to_dict()
    d["metadata"]["new"] = "x"
    assert "new" not in e.metadata


# =========================================================================
# Chunk 特殊值
# =========================================================================


def test_chunk_whitespace_text_does_not_raise():
    """text=" "（仅空白）→ truthy → OK（dataclass 用 `if not self.text`，空白非空字符串通过）。"""
    c = Chunk(chunk_id="c1", text=" ", source_element_ids=["e1"])
    assert c.text == " "


def test_chunk_source_element_ids_with_empty_string_only():
    """source_element_ids=[""] → 长度 1 → 不 raise（非空检查通过）。"""
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=[""])
    # dataclass 不检查空字符串
    assert c.source_element_ids == [""]


def test_chunk_source_element_ids_multiple():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1", "e2", "e3"],
    )
    assert len(c.source_element_ids) == 3


def test_chunk_metadata_nested_structure():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1"],
        metadata={"strategy": "sequential", "params": {"max_chars": 800}},
    )
    assert c.metadata["params"]["max_chars"] == 800


def test_chunk_source_spans_with_complex_structure():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1"],
        source_spans=[
            {"element_id": "e1", "start": 0, "end": 5, "text": "hello"},
            {"element_id": "e2", "start": 0, "end": 0},
        ],
    )
    assert len(c.source_spans) == 2
    assert c.source_spans[0]["text"] == "hello"


def test_chunk_to_dict_returns_new_dict_each_call():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d1 = c.to_dict()
    d2 = c.to_dict()
    assert d1 is not d2


def test_chunk_to_dict_does_not_share_metadata():
    c = Chunk(
        chunk_id="c1",
        text="x",
        source_element_ids=["e1"],
        metadata={"k": "v"},
    )
    d = c.to_dict()
    d["metadata"]["new"] = "x"
    assert "new" not in c.metadata


def test_chunk_to_dict_does_not_share_source_spans():
    c = Chunk(
        chunk_id="c1",
        text="x",
        source_element_ids=["e1"],
        source_spans=[{"element_id": "e1", "start": 0, "end": 1}],
    )
    d = c.to_dict()
    d["source_spans"].append({"element_id": "e2"})
    assert len(c.source_spans) == 1


# =========================================================================
# Relation 特殊值
# =========================================================================


def test_relation_empty_type_allowed():
    """type="" 不被 dataclass 校验拦截。"""
    r = Relation(type="", from_id="a", to_id="b")
    assert r.type == ""


def test_relation_empty_from_id_allowed():
    r = Relation(type="x", from_id="", to_id="b")
    assert r.from_id == ""


def test_relation_empty_to_id_allowed():
    r = Relation(type="x", from_id="a", to_id="")
    assert r.to_id == ""


def test_relation_metadata_nested():
    r = Relation(
        type="parent",
        from_id="a",
        to_id="b",
        metadata={"weight": 0.9, "extra": {"k": "v"}},
    )
    assert r.metadata["extra"]["k"] == "v"


def test_relation_to_dict_does_not_share_metadata():
    r = Relation(type="x", from_id="a", to_id="b", metadata={"k": "v"})
    d = r.to_dict()
    d["metadata"]["new"] = "x"
    assert "new" not in r.metadata


def test_relation_to_dict_returns_new_dict_each_call():
    r = Relation(type="x", from_id="a", to_id="b")
    d1 = r.to_dict()
    d2 = r.to_dict()
    assert d1 is not d2


# =========================================================================
# WarningRecord vs ErrorRecord 边界对比
# =========================================================================


def test_warning_record_field_names():
    flds = [f.name for f in fields(WarningRecord)]
    assert flds == ["code", "reason", "details"]


def test_error_record_field_names():
    flds = [f.name for f in fields(ErrorRecord)]
    assert flds == ["code", "message", "details"]


def test_warning_record_reason_vs_error_record_message():
    """WarningRecord 用 reason，ErrorRecord 用 message。"""
    w = WarningRecord(code="w", reason="r")
    e = ErrorRecord(code="e", message="m")
    assert "reason" in w.to_dict()
    assert "message" in e.to_dict()
    assert "reason" not in e.to_dict()
    assert "message" not in w.to_dict()


def test_warning_record_with_explicit_none_details():
    w = WarningRecord(code="w", reason="r", details=None)
    d = w.to_dict()
    assert "details" not in d


def test_error_record_with_explicit_none_details():
    e = ErrorRecord(code="e", message="m", details=None)
    d = e.to_dict()
    assert "details" not in d


def test_warning_record_with_empty_dict_details():
    """details={} → 显式 None? 不，{} is not None → 字段保留。"""
    w = WarningRecord(code="w", reason="r", details={})
    d = w.to_dict()
    # details={} is not None, so it's included
    assert d["details"] == {}


def test_error_record_with_empty_dict_details():
    e = ErrorRecord(code="e", message="m", details={})
    d = e.to_dict()
    assert d["details"] == {}


def test_warning_record_details_with_list():
    w = WarningRecord(code="w", reason="r", details=["a", "b"])
    d = w.to_dict()
    assert d["details"] == ["a", "b"]


def test_error_record_details_with_list():
    e = ErrorRecord(code="e", message="m", details=["a", "b"])
    d = e.to_dict()
    assert d["details"] == ["a", "b"]


def test_warning_record_to_dict_returns_new_each_call():
    w = WarningRecord(code="w", reason="r")
    d1 = w.to_dict()
    d2 = w.to_dict()
    assert d1 is not d2


def test_error_record_to_dict_returns_new_each_call():
    e = ErrorRecord(code="e", message="m")
    d1 = e.to_dict()
    d2 = e.to_dict()
    assert d1 is not d2


# =========================================================================
# Document 特殊值与边界
# =========================================================================


def test_document_empty_document_id_allowed_at_dataclass_layer():
    """document_id='' 不被 dataclass 校验拦截（无 __post_init__）。"""
    d = Document(
        document_id="",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
    )
    assert d.document_id == ""


def test_document_empty_source_path_allowed():
    d = Document(
        document_id="d1",
        source_path="",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
    )
    assert d.source_path == ""


def test_document_short_source_hash_allowed_at_dataclass_layer():
    """source_hash='' 不被 dataclass 校验（无 __post_init__）。"""
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="",
        parser_name="x",
        parser_version="x",
    )
    assert d.source_hash == ""


def test_document_metadata_accepts_complex_structure():
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        metadata={
            "stats": {"elements": 10, "chunks": 5},
            "tags": ["important", "reviewed"],
            "score": 0.85,
        },
    )
    assert d.metadata["stats"]["elements"] == 10
    assert d.metadata["tags"][0] == "important"


def test_document_to_dict_metadata_shared_reference():
    """Document.to_dict 用 self.metadata 直接引用（不复制）。"""
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
        metadata={"k": "v"},
    )
    out = d.to_dict()
    # out["metadata"] 与 d.metadata 是同一对象（Document.to_dict 不复制）
    assert out["metadata"] is d.metadata


def test_document_to_dict_elements_not_shared():
    e = Element(element_id="e1", type="paragraph", content="x", source_locator={})
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
    out["elements"].append(Element(
        element_id="e2", type="paragraph", content="y", source_locator={}
    ).to_dict())
    assert len(d.elements) == 1


def test_document_to_dict_returns_new_each_call():
    d = Document(
        document_id="d1",
        source_path="x",
        source_type="pdf",
        source_hash="0" * 64,
        parser_name="x",
        parser_version="x",
    )
    d1 = d.to_dict()
    d2 = d.to_dict()
    assert d1 is not d2
    assert d1 == d2


def test_document_metadata_default_independent_across_three():
    d1 = Document(
        document_id="d1", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d2 = Document(
        document_id="d2", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d3 = Document(
        document_id="d3", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d1.metadata["k1"] = "v1"
    d2.metadata["k2"] = "v2"
    assert "k1" not in d2.metadata
    assert "k1" not in d3.metadata
    assert "k2" not in d1.metadata
    assert "k2" not in d3.metadata


def test_document_elements_default_independent():
    d1 = Document(
        document_id="d1", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    d2 = Document(
        document_id="d2", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    e1 = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    d1.elements.append(e1)
    assert len(d2.elements) == 0


# =========================================================================
# asdict 行为对比
# =========================================================================


def test_element_to_dict_equals_asdict():
    """to_dict 内部调 asdict，结果应一致。"""
    e = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
        metadata={"k": "v"},
    )
    assert e.to_dict() == asdict(e)


def test_chunk_to_dict_equals_asdict():
    c = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1"],
        metadata={"strategy": "x"},
        source_spans=[{"element_id": "e1", "start": 0, "end": 5}],
    )
    assert c.to_dict() == asdict(c)


def test_relation_to_dict_equals_asdict():
    r = Relation(type="parent", from_id="a", to_id="b", metadata={"k": "v"})
    assert r.to_dict() == asdict(r)


# =========================================================================
# round-trip 序列化
# =========================================================================


def test_element_roundtrip_via_constructor():
    """Element → to_dict → 重新构造 Element 应等价。"""
    e1 = Element(
        element_id="e1",
        type="paragraph",
        content="hello",
        source_locator={"line": 1},
        metadata={"k": "v"},
    )
    d = e1.to_dict()
    e2 = Element(**d)
    assert e1 == e2
    assert e1.to_dict() == e2.to_dict()


def test_chunk_roundtrip_via_constructor():
    c1 = Chunk(
        chunk_id="c1",
        text="hello",
        source_element_ids=["e1"],
        metadata={"k": "v"},
    )
    d = c1.to_dict()
    c2 = Chunk(**d)
    assert c1 == c2


def test_relation_roundtrip_via_constructor():
    r1 = Relation(type="x", from_id="a", to_id="b", metadata={"k": "v"})
    d = r1.to_dict()
    r2 = Relation(**d)
    assert r1 == r2


def test_document_to_dict_json_roundtrip():
    """Document.to_dict() 应可 JSON 序列化与反序列化。"""
    import json
    e = Element(element_id="e1", type="paragraph", content="hello", source_locator={"line": 1})
    c = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    d1 = Document(
        document_id="d1", source_path="x.pdf", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
        elements=[e], chunks=[c],
    )
    s = json.dumps(d1.to_dict())
    parsed = json.loads(s)
    assert parsed["document_id"] == "d1"
    assert parsed["schema_version"] == SCHEMA_VERSION
    assert len(parsed["elements"]) == 1
    assert len(parsed["chunks"]) == 1


# =========================================================================
# dataclass 字段默认值类型
# =========================================================================


def test_element_confidence_field_default():
    fld = next(f for f in fields(Element) if f.name == "confidence")
    assert fld.default == 1.0


def test_element_metadata_field_default_factory():
    fld = next(f for f in fields(Element) if f.name == "metadata")
    assert fld.default_factory is not None


def test_chunk_metadata_field_default_factory():
    fld = next(f for f in fields(Chunk) if f.name == "metadata")
    assert fld.default_factory is not None


def test_chunk_source_spans_field_default_factory():
    fld = next(f for f in fields(Chunk) if f.name == "source_spans")
    assert fld.default_factory is not None


def test_relation_metadata_field_default_factory():
    fld = next(f for f in fields(Relation) if f.name == "metadata")
    assert fld.default_factory is not None


def test_warning_record_details_default_none():
    fld = next(f for f in fields(WarningRecord) if f.name == "details")
    assert fld.default is None


def test_error_record_details_default_none():
    fld = next(f for f in fields(ErrorRecord) if f.name == "details")
    assert fld.default is None


def test_document_elements_default_factory():
    fld = next(f for f in fields(Document) if f.name == "elements")
    assert fld.default_factory is not None


def test_document_chunks_default_factory():
    fld = next(f for f in fields(Document) if f.name == "chunks")
    assert fld.default_factory is not None


def test_document_metadata_default_factory():
    fld = next(f for f in fields(Document) if f.name == "metadata")
    assert fld.default_factory is not None


# =========================================================================
# 综合行为
# =========================================================================


def test_all_dataclasses_have_to_dict():
    """6 个 dataclass 都应有 to_dict 方法。"""
    for cls in [Element, Chunk, Relation, WarningRecord, ErrorRecord, Document]:
        assert hasattr(cls, "to_dict")
        assert callable(getattr(cls, "to_dict"))


def test_all_dataclasses_have_post_init_or_not():
    """Element/Chunk 有 __post_init__；其他无。"""
    assert hasattr(Element, "__post_init__")
    assert hasattr(Chunk, "__post_init__")
    # Relation/WarningRecord/ErrorRecord/Document 无自定义 __post_init__
    # dataclass 默认会生成空 __post_init__? 实际不会


def test_dataclass_equality_same_args():
    """相同参数构造的两个实例应相等。"""
    e1 = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    e2 = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    assert e1 == e2


def test_dataclass_inequality_different_args():
    e1 = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    e2 = Element(element_id="e2", type="paragraph", content="x", source_locator={})
    assert e1 != e2


def test_dataclass_repr_contains_class_name():
    e = Element(element_id="e1", type="paragraph", content="x", source_locator={})
    assert "Element" in repr(e)


def test_document_to_dict_includes_schema_version_first():
    """to_dict 第一个 key 应是 schema_version。"""
    d = Document(
        document_id="d1", source_path="x", source_type="pdf",
        source_hash="0" * 64, parser_name="x", parser_version="x",
    )
    out = d.to_dict()
    first_key = next(iter(out.keys()))
    assert first_key == "schema_version"
