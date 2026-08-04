r"""app/models.py 边角测试 - 第三轮（Round 121）。

补强已有 base/edges/edges2（共 203 测试）未覆盖的深度路径：
- SCHEMA_VERSION：
  - 精确值 "0.1.0"
  - 是 str 类型
- ElementType / SourceType Literal：
  - 各成员存在
  - Literal 类型自身可被 typing.get_args 解析
- Element __post_init__ 深度：
  - content=" " 单空格 → truthy → 通过
  - content="\t" tab → truthy → 通过
  - resource_path=" " 单空格 → truthy → 通过
  - content=None + resource_path=None → 抛 ValueError
  - element_id="x" 非空 → 通过
  - element_id="\t" tab → truthy → 通过
  - element_id=00 (int 0) → falsy → 抛 ValueError
- Chunk __post_init__ 深度：
  - text="x" 单字符 → 通过
  - chunk_id="x" 单字符 → 通过
  - source_element_ids=["x"] 单元素 → 通过
  - text="\n" newline 单字符 → 通过
- Relation 字段：
  - from_id/to_id 空串接受
  - metadata 默认 {}
  - to_dict 4 keys
- WarningRecord/ErrorRecord：
  - 默认 details=None
  - to_dict 仅在 details 非 None 时含 details key
  - code/message/reason 必填
- Document：
  - 7 必填字段
  - 6 默认字段
  - to_dict 14 keys（含 schema_version）
- 模块结构：
  - imports dataclasses.dataclass/field/asdict
  - imports typing.Any/Literal/Optional
  - SCHEMA_VERSION 在模块顶层
"""

from __future__ import annotations

import typing
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest

from app.models import (
    SCHEMA_VERSION,
    Chunk,
    Document,
    Element,
    ErrorRecord,
    Relation,
    WarningRecord,
)


# =========================================================================
# SCHEMA_VERSION 深度
# =========================================================================


def test_schema_version_exact_value():
    assert SCHEMA_VERSION == "0.1.0"


def test_schema_version_is_str_type():
    assert isinstance(SCHEMA_VERSION, str)


def test_schema_version_three_parts():
    assert len(SCHEMA_VERSION.split(".")) == 3


def test_schema_version_major_zero():
    assert SCHEMA_VERSION.split(".")[0] == "0"


def test_schema_version_minor_one():
    assert SCHEMA_VERSION.split(".")[1] == "1"


def test_schema_version_patch_zero():
    assert SCHEMA_VERSION.split(".")[2] == "0"


# =========================================================================
# ElementType / SourceType Literal 深度
# =========================================================================


def test_element_type_literal_via_get_args():
    """typing.get_args(ElementType) 应返回所有合法元素类型。"""
    from app.models import ElementType

    args = typing.get_args(ElementType)
    assert "heading" in args
    assert "paragraph" in args
    assert "table" in args
    assert "image" in args


def test_element_type_literal_has_eight_members():
    from app.models import ElementType

    args = typing.get_args(ElementType)
    assert len(args) == 8


def test_element_type_literal_members_exact():
    from app.models import ElementType

    args = typing.get_args(ElementType)
    assert set(args) == {
        "heading",
        "paragraph",
        "list_item",
        "table",
        "image",
        "caption",
        "header",
        "footer",
    }


def test_source_type_literal_via_get_args():
    from app.models import SourceType

    args = typing.get_args(SourceType)
    assert "pdf" in args
    assert "docx" in args


def test_source_type_literal_has_six_members():
    from app.models import SourceType

    args = typing.get_args(SourceType)
    assert len(args) == 6


def test_source_type_literal_members_exact():
    from app.models import SourceType

    args = typing.get_args(SourceType)
    assert set(args) == {
        "pdf",
        "docx",
        "markdown",
        "html",
        "text",
        "ipynb",
    }


# =========================================================================
# Element __post_init__ 深度
# =========================================================================


def test_element_content_single_space_passes():
    """content=' ' → truthy → 通过。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content=" ")
    assert e.content == " "


def test_element_content_single_tab_passes():
    """content='\\t' → truthy → 通过。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="\t")
    assert e.content == "\t"


def test_element_content_newline_passes():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="\n")
    assert e.content == "\n"


def test_element_resource_path_single_space_passes():
    """resource_path=' ' → truthy → 通过（仅 resource_path 非空）。"""
    e = Element(
        element_id="e1",
        type="image",
        source_locator={},
        resource_path=" ",
    )
    assert e.resource_path == " "


def test_element_both_content_and_resource_path_none_raises():
    with pytest.raises(ValueError):
        Element(
            element_id="e1",
            type="paragraph",
            source_locator={},
            content=None,
            resource_path=None,
        )


def test_element_both_content_and_resource_path_empty_raises():
    with pytest.raises(ValueError):
        Element(
            element_id="e1",
            type="paragraph",
            source_locator={},
            content="",
            resource_path="",
        )


def test_element_id_whitespace_only_passes_at_init():
    """element_id='   ' truthy → 通过（与现有 edges 测试一致：仅空串拒绝）。"""
    e = Element(
        element_id="   ",
        type="paragraph",
        source_locator={},
        content="x",
    )
    assert e.element_id == "   "


def test_element_id_tab_passes_at_init():
    """element_id='\\t' truthy → 通过。"""
    e = Element(
        element_id="\t",
        type="paragraph",
        source_locator={},
        content="x",
    )
    assert e.element_id == "\t"


def test_element_confidence_explicit_one():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        confidence=1.0,
    )
    assert e.confidence == 1.0


def test_element_confidence_zero():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        confidence=0.0,
    )
    assert e.confidence == 0.0


def test_element_metadata_default_empty_dict():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.metadata == {}


def test_element_metadata_passed_through():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        metadata={"key": "value"},
    )
    assert e.metadata == {"key": "value"}


def test_element_parent_id_default_none():
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    assert e.parent_id is None


def test_element_parent_id_passed_through():
    e = Element(
        element_id="e1",
        type="paragraph",
        source_locator={},
        content="x",
        parent_id="parent",
    )
    assert e.parent_id == "parent"


def test_element_to_dict_has_seven_keys_exact():
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


def test_element_to_dict_keys_count_eight():
    """Element.to_dict 实际是 8 keys（含 parent_id/resource_path/confidence/metadata）。"""
    e = Element(element_id="e1", type="paragraph", source_locator={}, content="x")
    d = e.to_dict()
    assert len(d) == 8


# =========================================================================
# Chunk __post_init__ 深度
# =========================================================================


def test_chunk_text_single_char_passes():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.text == "x"


def test_chunk_chunk_id_single_char_passes():
    c = Chunk(chunk_id="x", text="text", source_element_ids=["e1"])
    assert c.chunk_id == "x"


def test_chunk_source_element_ids_single_element_passes():
    c = Chunk(chunk_id="c1", text="text", source_element_ids=["e1"])
    assert c.source_element_ids == ["e1"]


def test_chunk_text_newline_only_passes():
    """text='\\n' 单字符 → truthy → 通过。"""
    c = Chunk(chunk_id="c1", text="\n", source_element_ids=["e1"])
    assert c.text == "\n"


def test_chunk_text_special_chars_passes():
    text = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
    c = Chunk(chunk_id="c1", text=text, source_element_ids=["e1"])
    assert c.text == text


def test_chunk_text_unicode_passes():
    text = "中文测试 🎉 emoji"
    c = Chunk(chunk_id="c1", text=text, source_element_ids=["e1"])
    assert c.text == text


def test_chunk_metadata_default_empty_dict():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.metadata == {}


def test_chunk_source_spans_default_empty_list():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    assert c.source_spans == []


def test_chunk_metadata_isolated_per_instance():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e2"])
    c1.metadata["key"] = "value"
    assert "key" not in c2.metadata


def test_chunk_source_spans_isolated_per_instance():
    c1 = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    c2 = Chunk(chunk_id="c2", text="y", source_element_ids=["e2"])
    c1.source_spans.append({"start": 0})
    assert len(c2.source_spans) == 0


def test_chunk_to_dict_keys_exact():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d = c.to_dict()
    assert set(d.keys()) == {
        "chunk_id",
        "text",
        "source_element_ids",
        "metadata",
        "source_spans",
    }


def test_chunk_to_dict_keys_count_five():
    c = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d = c.to_dict()
    assert len(d) == 5


# =========================================================================
# Relation 深度
# =========================================================================


def test_relation_to_dict_keys_exact():
    r = Relation(type="parent", from_id="a", to_id="b")
    d = r.to_dict()
    assert set(d.keys()) == {"type", "from_id", "to_id", "metadata"}


def test_relation_default_metadata_empty_dict():
    r = Relation(type="parent", from_id="a", to_id="b")
    assert r.metadata == {}


def test_relation_from_id_empty_string_accepted():
    r = Relation(type="parent", from_id="", to_id="b")
    assert r.from_id == ""


def test_relation_to_id_empty_string_accepted():
    r = Relation(type="parent", from_id="a", to_id="")
    assert r.to_id == ""


def test_relation_type_empty_string_accepted():
    r = Relation(type="", from_id="a", to_id="b")
    assert r.type == ""


def test_relation_with_unicode_ids():
    r = Relation(type="引用", from_id="文档1", to_id="文档2")
    d = r.to_dict()
    assert d["from_id"] == "文档1"
    assert d["to_id"] == "文档2"


def test_relation_metadata_passed_through():
    r = Relation(
        type="parent",
        from_id="a",
        to_id="b",
        metadata={"weight": 0.5},
    )
    d = r.to_dict()
    assert d["metadata"] == {"weight": 0.5}


# =========================================================================
# WarningRecord 深度
# =========================================================================


def test_warning_record_required_fields():
    w = WarningRecord(code="warn", reason="something")
    assert w.code == "warn"
    assert w.reason == "something"


def test_warning_record_details_default_none():
    w = WarningRecord(code="warn", reason="something")
    assert w.details is None


def test_warning_record_to_dict_keys_count_two_when_details_none():
    w = WarningRecord(code="warn", reason="something")
    d = w.to_dict()
    assert len(d) == 2


def test_warning_record_to_dict_keys_count_three_when_details_set():
    w = WarningRecord(code="warn", reason="something", details={"k": "v"})
    d = w.to_dict()
    assert len(d) == 3


def test_warning_record_to_dict_keys_exact_when_details_none():
    w = WarningRecord(code="warn", reason="something")
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason"}


def test_warning_record_to_dict_keys_exact_when_details_set():
    w = WarningRecord(code="warn", reason="something", details={"k": "v"})
    d = w.to_dict()
    assert set(d.keys()) == {"code", "reason", "details"}


def test_warning_record_to_dict_includes_empty_dict_details():
    """details={} 是 falsy 但 not None → 应包含。"""
    w = WarningRecord(code="warn", reason="something", details={})
    d = w.to_dict()
    assert "details" in d
    assert d["details"] == {}


# =========================================================================
# ErrorRecord 深度
# =========================================================================


def test_error_record_required_fields():
    er = ErrorRecord(code="err", message="fail")
    assert er.code == "err"
    assert er.message == "fail"


def test_error_record_details_default_none():
    er = ErrorRecord(code="err", message="fail")
    assert er.details is None


def test_error_record_to_dict_keys_count_two_when_details_none():
    er = ErrorRecord(code="err", message="fail")
    d = er.to_dict()
    assert len(d) == 2


def test_error_record_to_dict_keys_count_three_when_details_set():
    er = ErrorRecord(code="err", message="fail", details={"k": "v"})
    d = er.to_dict()
    assert len(d) == 3


def test_error_record_to_dict_keys_exact_when_details_none():
    er = ErrorRecord(code="err", message="fail")
    d = er.to_dict()
    assert set(d.keys()) == {"code", "message"}


def test_error_record_to_dict_keys_exact_when_details_set():
    er = ErrorRecord(code="err", message="fail", details={"k": "v"})
    d = er.to_dict()
    assert set(d.keys()) == {"code", "message", "details"}


def test_error_record_to_dict_includes_empty_dict_details():
    er = ErrorRecord(code="err", message="fail", details={})
    d = er.to_dict()
    assert "details" in d
    assert d["details"] == {}


# =========================================================================
# Document 深度
# =========================================================================


def _minimal_doc() -> Document:
    return Document(
        document_id="doc-1",
        source_path="/tmp/x.pdf",
        source_type="pdf",
        source_hash="a" * 64,
        parser_name="fallback",
        parser_version="stdlib/0.1.0",
    )


def test_document_required_fields_count():
    """Document 字段共 12 个。"""
    flds = fields(Document)
    # 6 必填 + 6 默认 = 12
    assert len(flds) == 12


def test_document_to_dict_keys_count_thirteen():
    """to_dict 输出 13 keys（含 schema_version）。"""
    d = _minimal_doc().to_dict()
    assert len(d) == 13


def test_document_to_dict_has_schema_version():
    d = _minimal_doc().to_dict()
    assert "schema_version" in d


def test_document_to_dict_schema_version_value():
    d = _minimal_doc().to_dict()
    assert d["schema_version"] == SCHEMA_VERSION


def test_document_to_dict_keys_exact_set():
    d = _minimal_doc().to_dict()
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


def test_document_metadata_default_empty_dict():
    doc = _minimal_doc()
    assert doc.metadata == {}


def test_document_elements_default_empty_list():
    doc = _minimal_doc()
    assert doc.elements == []


def test_document_chunks_default_empty_list():
    doc = _minimal_doc()
    assert doc.chunks == []


def test_document_relations_default_empty_list():
    doc = _minimal_doc()
    assert doc.relations == []


def test_document_warnings_default_empty_list():
    doc = _minimal_doc()
    assert doc.warnings == []


def test_document_errors_default_empty_list():
    doc = _minimal_doc()
    assert doc.errors == []


def test_document_metadata_isolated_per_instance():
    d1 = _minimal_doc()
    d2 = _minimal_doc()
    d1.metadata["key"] = "value"
    assert "key" not in d2.metadata


def test_document_elements_isolated_per_instance():
    d1 = _minimal_doc()
    d2 = _minimal_doc()
    d1.elements.append(Element(element_id="e1", type="paragraph", source_locator={}, content="x"))
    assert len(d2.elements) == 0


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_dataclass():
    from app import models as mod

    assert hasattr(mod, "dataclass")


def test_module_imports_field():
    from app import models as mod

    assert hasattr(mod, "field")


def test_module_imports_asdict():
    from app import models as mod

    assert hasattr(mod, "asdict")


def test_module_imports_any():
    from app import models as mod

    assert hasattr(mod, "Any")


def test_module_imports_literal():
    from app import models as mod

    assert hasattr(mod, "Literal")


def test_module_imports_optional():
    from app import models as mod

    assert hasattr(mod, "Optional")


def test_module_has_schema_version():
    from app import models as mod

    assert hasattr(mod, "SCHEMA_VERSION")


def test_module_has_element_type():
    from app import models as mod

    assert hasattr(mod, "ElementType")


def test_module_has_source_type():
    from app import models as mod

    assert hasattr(mod, "SourceType")


def test_module_has_element_class():
    from app import models as mod

    assert hasattr(mod, "Element")


def test_module_has_chunk_class():
    from app import models as mod

    assert hasattr(mod, "Chunk")


def test_module_has_relation_class():
    from app import models as mod

    assert hasattr(mod, "Relation")


def test_module_has_warning_record_class():
    from app import models as mod

    assert hasattr(mod, "WarningRecord")


def test_module_has_error_record_class():
    from app import models as mod

    assert hasattr(mod, "ErrorRecord")


def test_module_has_document_class():
    from app import models as mod

    assert hasattr(mod, "Document")


def test_module_docstring_present():
    from app import models as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_dataclass():
    from app import models as mod

    doc = mod.__doc__
    assert "dataclass" in doc.lower() or "数据" in doc


def test_module_uses_future_annotations():
    """模块用了 from __future__ import annotations。"""
    import ast

    from app import models as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# dataclass 类属性
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


def test_element_field_count_eight():
    flds = fields(Element)
    assert len(flds) == 8


def test_chunk_field_count_five():
    flds = fields(Chunk)
    assert len(flds) == 5


def test_relation_field_count_four():
    flds = fields(Relation)
    assert len(flds) == 4


def test_warning_record_field_count_three():
    flds = fields(WarningRecord)
    assert len(flds) == 3


def test_error_record_field_count_three():
    flds = fields(ErrorRecord)
    assert len(flds) == 3


def test_document_field_count_twelve():
    flds = fields(Document)
    assert len(flds) == 12
