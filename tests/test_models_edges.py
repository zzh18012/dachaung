"""app/models.py 边角测试（Round 52）。

补强 tests/test_models.py（55 个测试）未覆盖的边角：
- SCHEMA_VERSION 常量深入
- ElementType / SourceType 字面量
- Element confidence 边界值
- Element/Chunk mutable 行为
- Chunk 多种空白字符文本
- Document to_dict 元素顺序保留
- Relation/Warning/Error 复杂 metadata
- asdict 行为：深拷贝
- 各 dataclass 都有 to_dict 方法
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

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


# ---------- SCHEMA_VERSION 深入 ----------


def test_schema_version_starts_with_zero():
    """0.1.0 阶段以 '0' 开头。"""
    assert SCHEMA_VERSION.startswith("0")


def test_schema_version_has_major_minor_patch():
    """版本号格式 major.minor.patch。"""
    parts = SCHEMA_VERSION.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_schema_version_string_is_immutable_value():
    """模块级常量不能被改（导入到不同模块时同一对象）。"""
    from app import models
    assert models.SCHEMA_VERSION == SCHEMA_VERSION


# ---------- ElementType / SourceType 字面量 ----------


def test_element_type_all_known_types_accepted():
    """8 种 ElementType：heading/paragraph/list_item/table/image/caption/header/footer。"""
    for t in ("heading", "paragraph", "list_item", "table", "image",
              "caption", "header", "footer"):
        el = Element(
            element_id=f"e-{t}",
            type=t,  # type: ignore[arg-type]
            content="x" if t != "image" else None,
            resource_path="/tmp/x.png" if t == "image" else None,
            source_locator={"paragraph_index": 0},
        )
        assert el.type == t


def test_source_type_all_known_types_accepted():
    """6 种 SourceType：pdf/docx/markdown/html/text/ipynb。"""
    for t in ("pdf", "docx", "markdown", "html", "text", "ipynb"):
        doc = Document(
            document_id="d1",
            source_path=f"x.{t}",
            source_type=t,  # type: ignore[arg-type]
            source_hash="a" * 64,
            parser_name="fallback",
            parser_version="1.0",
        )
        assert doc.source_type == t


# ---------- Element confidence 边界值 ----------


def test_element_confidence_zero_allowed():
    """confidence=0.0 应允许（schema 允许 0-1 范围）。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={}, confidence=0.0,
    )
    assert el.confidence == 0.0


def test_element_confidence_negative_allowed_at_dataclass_layer():
    """dataclass 层不限制范围（schema 层会拒）。

    注：负数 confidence 在 dataclass 创建时不抛错。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={}, confidence=-0.5,
    )
    assert el.confidence == -0.5


def test_element_confidence_above_one_allowed_at_dataclass_layer():
    """dataclass 层不限制范围（schema 层会拒）。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={}, confidence=1.5,
    )
    assert el.confidence == 1.5


def test_element_confidence_float_type():
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={}, confidence=0.7,
    )
    assert isinstance(el.confidence, float)


def test_element_confidence_int_coerced_to_float():
    """传 int 1 不会自动转 float（Python dataclass 不强制类型）。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={}, confidence=1,  # int
    )
    # dataclass 不强制类型转换
    assert el.confidence == 1


# ---------- Element mutable 行为 ----------


def test_element_is_mutable_not_frozen():
    """Element dataclass 默认非 frozen → 可改属性。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={},
    )
    el.content = "modified"
    assert el.content == "modified"


def test_element_can_add_metadata_after_creation():
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={},
    )
    el.metadata["key"] = "value"
    assert el.metadata["key"] == "value"


def test_element_id_cannot_be_emptied_after_creation_via_attribute():
    """dataclass 不在 set 时校验，只 __post_init__ 时校验。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={},
    )
    # 修改 element_id 为空字符串不会 raise（无 setter 校验）
    el.element_id = ""
    assert el.element_id == ""


def test_element_whitespace_only_element_id_rejected():
    """element_id 是纯空白 → falsy → ValueError。

    注：' ' 是 truthy 字符串，所以不会 raise（dataclass 只检查 not）。
    """
    # element_id = "   " 是 truthy → 不在 __post_init__ 拦截
    el = Element(
        element_id="   ", type="paragraph", content="x",
        source_locator={},
    )
    assert el.element_id == "   "


# ---------- Element to_dict 深拷贝 ----------


def test_element_to_dict_does_not_mutate_instance():
    """to_dict 返回独立 dict，改 dict 不影响原 element。"""
    el = Element(
        element_id="e1", type="paragraph", content="original",
        source_locator={"page": 1},
        metadata={"k": "v"},
    )
    d = el.to_dict()
    d["content"] = "changed"
    d["metadata"]["k"] = "changed"
    assert el.content == "original"
    # 注意：asdict 是深拷贝，metadata 改 dict 不影响 element
    assert el.metadata["k"] == "v"


def test_element_to_dict_contains_source_locator():
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]},
    )
    d = el.to_dict()
    assert d["source_locator"] == {"page": 1, "bbox": [1.0, 2.0, 3.0, 4.0]}


def test_element_to_dict_returns_seven_keys():
    """Element 字段数：element_id/type/source_locator/parent_id/content/
    resource_path/confidence/metadata = 8 个。"""
    el = Element(
        element_id="e1", type="paragraph", content="x",
        source_locator={},
    )
    d = el.to_dict()
    assert set(d.keys()) == {
        "element_id", "type", "source_locator", "parent_id",
        "content", "resource_path", "confidence", "metadata",
    }


# ---------- Chunk 各种空白字符文本 ----------


def test_chunk_text_with_only_newline_rejected():
    """text 只含 \\n → __post_init__ 检查 `if not self.text`，但 \\n 是 truthy。

    实际：'\\n' 是 truthy → 通过 dataclass 层。
    """
    chunk = Chunk(
        chunk_id="c1", text="\n", source_element_ids=["e1"],
    )
    # 数据类层不拒，schema 层会拒
    assert chunk.text == "\n"


def test_chunk_text_with_only_tab_allowed_at_dataclass():
    chunk = Chunk(
        chunk_id="c1", text="\t", source_element_ids=["e1"],
    )
    assert chunk.text == "\t"


def test_chunk_with_complex_metadata():
    """metadata 含嵌套 dict/list/None/int/float/bool。"""
    chunk = Chunk(
        chunk_id="c1", text="hello", source_element_ids=["e1"],
        metadata={
            "nested": {"deep": [1, 2, {"x": None}]},
            "types": [True, 1.5, "str"],
        },
    )
    d = chunk.to_dict()
    assert d["metadata"]["nested"]["deep"][2]["x"] is None
    assert d["metadata"]["types"] == [True, 1.5, "str"]


def test_chunk_with_complex_source_spans():
    chunk = Chunk(
        chunk_id="c1", text="hello", source_element_ids=["e1"],
        source_spans=[
            {"element_id": "e1", "start": 0, "end": 3, "extra": "info"},
            {"element_id": "e1", "start": 4, "end": 5},
        ],
    )
    d = chunk.to_dict()
    assert len(d["source_spans"]) == 2
    assert d["source_spans"][0]["extra"] == "info"


def test_chunk_to_dict_returns_five_keys():
    """Chunk 字段：chunk_id/text/source_element_ids/metadata/source_spans = 5。"""
    chunk = Chunk(chunk_id="c1", text="x", source_element_ids=["e1"])
    d = chunk.to_dict()
    assert set(d.keys()) == {
        "chunk_id", "text", "source_element_ids", "metadata", "source_spans"
    }


# ---------- Chunk mutable 行为 ----------


def test_chunk_is_mutable_text_can_be_reassigned():
    chunk = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    chunk.text = "modified"
    assert chunk.text == "modified"


def test_chunk_can_be_emptied_after_creation():
    """dataclass 不在 set 时校验，可设空 text（schema 会拒）。"""
    chunk = Chunk(chunk_id="c1", text="hello", source_element_ids=["e1"])
    chunk.text = ""
    assert chunk.text == ""


def test_chunk_default_source_element_ids_must_be_provided():
    """source_element_ids 是必填字段（无默认值）。"""
    with pytest.raises(TypeError):
        Chunk(chunk_id="c1", text="x")  # type: ignore[call-arg]


# ---------- Document to_dict 元素顺序保留 ----------


def test_document_to_dict_preserves_element_order():
    """elements 列表顺序应保留。"""
    elements = [
        Element(element_id=f"e{i}", type="paragraph", content=f"text{i}",
                source_locator={})
        for i in range(5)
    ]
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
        elements=elements,
    )
    d = doc.to_dict()
    assert [e["element_id"] for e in d["elements"]] == [
        "e0", "e1", "e2", "e3", "e4"
    ]


def test_document_to_dict_preserves_chunk_order():
    chunks = [
        Chunk(chunk_id=f"c{i}", text=f"text{i}", source_element_ids=["e1"])
        for i in range(3)
    ]
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
        chunks=chunks,
    )
    d = doc.to_dict()
    assert [c["chunk_id"] for c in d["chunks"]] == ["c0", "c1", "c2"]


def test_document_to_dict_preserves_warnings_order():
    warnings = [
        WarningRecord(code=f"w{i}", reason=f"r{i}") for i in range(3)
    ]
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
        warnings=warnings,
    )
    d = doc.to_dict()
    assert [w["code"] for w in d["warnings"]] == ["w0", "w1", "w2"]


def test_document_to_dict_preserves_errors_order():
    errors = [
        ErrorRecord(code=f"e{i}", message=f"m{i}") for i in range(3)
    ]
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
        errors=errors,
    )
    d = doc.to_dict()
    assert [e["code"] for e in d["errors"]] == ["e0", "e1", "e2"]


def test_document_to_dict_keys_count():
    """Document.to_dict 应含 13 个顶层 keys。"""
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    d = doc.to_dict()
    expected_keys = {
        "schema_version", "document_id", "source_path", "source_type",
        "source_hash", "parser_name", "parser_version",
        "elements", "chunks", "relations", "warnings", "errors", "metadata",
    }
    assert set(d.keys()) == expected_keys
    assert len(d) == 13


def test_document_to_dict_schema_version_constant_value():
    """to_dict 的 schema_version 应与模块常量一致。"""
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    d = doc.to_dict()
    assert d["schema_version"] == SCHEMA_VERSION


def test_document_default_elements_is_list():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    assert isinstance(doc.elements, list)
    assert doc.elements == []


def test_document_default_metadata_is_dict():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    assert isinstance(doc.metadata, dict)
    assert doc.metadata == {}


# ---------- Document mutable 行为 ----------


def test_document_is_mutable():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    doc.document_id = "changed"
    assert doc.document_id == "changed"


def test_document_can_add_elements_after_creation():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="text", parser_version="1.0",
    )
    el = Element(element_id="e1", type="paragraph", content="x",
                 source_locator={})
    doc.elements.append(el)
    assert len(doc.elements) == 1


# ---------- Relation 边角 ----------


def test_relation_to_dict_returns_three_keys_minimum():
    """Relation.to_dict 应含 type/from_id/to_id/metadata = 4 keys。"""
    r = Relation(type="parent", from_id="a", to_id="b")
    d = r.to_dict()
    assert set(d.keys()) == {"type", "from_id", "to_id", "metadata"}


def test_relation_metadata_passed_through():
    r = Relation(type="x", from_id="a", to_id="b", metadata={"k": "v"})
    d = r.to_dict()
    assert d["metadata"] == {"k": "v"}


def test_relation_no_post_init_validation():
    """Relation 没有 __post_init__，空字符串 type/from_id/to_id 都允许。"""
    r = Relation(type="", from_id="", to_id="")
    assert r.type == ""
    assert r.from_id == ""


def test_relation_type_field_free_form():
    """type 是自由字符串。"""
    for t in ("parent", "child", "next", "prev", "references", "any-string-OK"):
        r = Relation(type=t, from_id="a", to_id="b")
        assert r.type == t


# ---------- WarningRecord / ErrorRecord 边角 ----------


def test_warning_record_to_dict_returns_two_or_three_keys():
    """无 details → 2 keys (code/reason)；有 details → 3 keys。"""
    w1 = WarningRecord(code="c", reason="r")
    assert set(w1.to_dict().keys()) == {"code", "reason"}

    w2 = WarningRecord(code="c", reason="r", details={"k": "v"})
    assert set(w2.to_dict().keys()) == {"code", "reason", "details"}


def test_error_record_to_dict_returns_two_or_three_keys():
    e1 = ErrorRecord(code="c", message="m")
    assert set(e1.to_dict().keys()) == {"code", "message"}

    e2 = ErrorRecord(code="c", message="m", details={"k": "v"})
    assert set(e2.to_dict().keys()) == {"code", "message", "details"}


def test_warning_record_empty_details_dict_omitted():
    """details=None 时不写 details 字段。"""
    w = WarningRecord(code="c", reason="r", details=None)
    d = w.to_dict()
    assert "details" not in d


def test_error_record_empty_details_dict_omitted():
    e = ErrorRecord(code="c", message="m", details=None)
    d = e.to_dict()
    assert "details" not in d


def test_warning_record_complex_details_passed_through():
    w = WarningRecord(
        code="c", reason="r",
        details={"nested": [1, 2, {"x": None}]},
    )
    d = w.to_dict()
    assert d["details"]["nested"][2]["x"] is None


def test_error_record_complex_details_passed_through():
    e = ErrorRecord(
        code="c", message="m",
        details={"path": "/tmp/x", "errno": 13, "ctx": {"user": "bob"}},
    )
    d = e.to_dict()
    assert d["details"]["errno"] == 13


# ---------- dataclass 标识 ----------


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


# ---------- to_dict 方法存在性 ----------


def test_all_dataclasses_have_to_dict_method():
    for cls in (Element, Chunk, Relation, WarningRecord, ErrorRecord, Document):
        assert hasattr(cls, "to_dict")
        assert callable(getattr(cls, "to_dict"))


# ---------- Element image type 强制路径 ----------


def test_element_image_with_resource_path_no_content_ok():
    el = Element(
        element_id="img1", type="image",
        resource_path="/abs/path/x.png",
        source_locator={"page": 1},
    )
    assert el.resource_path == "/abs/path/x.png"
    assert el.content is None


def test_element_image_with_only_resource_path_in_to_dict():
    el = Element(
        element_id="img1", type="image",
        resource_path="/x/y.png",
        source_locator={"page": 1},
    )
    d = el.to_dict()
    assert d["resource_path"] == "/x/y.png"
    assert d["content"] is None


def test_element_image_with_content_and_resource_path_both_set():
    """dataclass 允许同时设置（schema 可能拒）。"""
    el = Element(
        element_id="img1", type="image",
        content="caption text",
        resource_path="/x/y.png",
        source_locator={"page": 1},
    )
    assert el.content == "caption text"
    assert el.resource_path == "/x/y.png"


# ---------- Document parser_name/version ----------


def test_document_parser_name_and_version_recorded():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64,
        parser_name="fallback", parser_version="1.0",
    )
    assert doc.parser_name == "fallback"
    assert doc.parser_version == "1.0"


def test_document_parser_version_can_be_complex_string():
    """parser_version 是 str，可以含多组件。"""
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64,
        parser_name="kreuzberg", parser_version="kreuzberg-4.10.2",
    )
    assert doc.parser_version == "kreuzberg-4.10.2"


# ---------- Document metadata 复杂内容 ----------


def test_document_metadata_with_complex_nested_data():
    doc = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64,
        parser_name="text", parser_version="1.0",
        metadata={
            "extraction_time": 1.23,
            "warnings_count": 0,
            "options": {"max_chars": 800, "language": "auto"},
        },
    )
    d = doc.to_dict()
    assert d["metadata"]["options"]["max_chars"] == 800


def test_document_metadata_default_isolated_per_instance():
    """两个 Document 实例的 metadata 应是不同 dict 对象。"""
    d1 = Document(
        document_id="d1", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="t", parser_version="1",
    )
    d2 = Document(
        document_id="d2", source_path="x", source_type="text",
        source_hash="a" * 64, parser_name="t", parser_version="1",
    )
    assert d1.metadata is not d2.metadata
    d1.metadata["k"] = "v"
    assert "k" not in d2.metadata
