"""Round 89 — app/schema.py 边角覆盖（第二轮）。

互补于已有：
- tests/test_schema.py（117 测试）
- tests/test_schema_edges.py（58 测试）

第二轮重点：document.schema.json 字段语义深度、source_locator 各分支边界、
SchemaValidationError 类、SCHEMA_PATH 常量、_silence_unused_import。
不修改 app/schema.py。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app import schema as schema_module
from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    __all__ as schema_all,
    _silence_unused_import,
    is_valid,
    load_schema,
    validate,
    validate_file,
)


# =============================================================================
# 基础 fixture
# =============================================================================


def _valid_pdf_document():
    return {
        "schema_version": "0.1.0",
        "document_id": "doc1",
        "source_path": "test.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "parent_id": None,
                "source_locator": {"page": 1},
                "content": "hello",
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {
                "chunk_id": "c1",
                "text": "hello",
                "source_element_ids": ["e1"],
                "metadata": {},
            }
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _valid_docx_document():
    d = _valid_pdf_document()
    d["source_type"] = "docx"
    d["source_path"] = "test.docx"
    d["elements"][0]["source_locator"] = {"paragraph_index": 0}
    return d


def _valid_markdown_document():
    d = _valid_pdf_document()
    d["source_type"] = "markdown"
    d["source_path"] = "test.md"
    d["elements"][0]["source_locator"] = {"line": 1}
    return d


def _valid_html_document():
    d = _valid_pdf_document()
    d["source_type"] = "html"
    d["source_path"] = "test.html"
    d["elements"][0]["source_locator"] = {"line": 1}
    return d


def _valid_text_document():
    d = _valid_pdf_document()
    d["source_type"] = "text"
    d["source_path"] = "test.txt"
    d["elements"][0]["source_locator"] = {"line": 1}
    return d


def _valid_ipynb_document():
    d = _valid_pdf_document()
    d["source_type"] = "ipynb"
    d["source_path"] = "test.ipynb"
    d["elements"][0]["source_locator"] = {
        "cell_index": 0,
        "cell_type": "code",
    }
    return d


# =============================================================================
# SCHEMA_PATH 常量深度
# =============================================================================


def test_schema_path_is_path_object():
    assert isinstance(SCHEMA_PATH, Path)


def test_schema_path_is_absolute():
    assert SCHEMA_PATH.is_absolute()


def test_schema_path_resolved_no_relative_components():
    """SCHEMA_PATH 用 .resolve()，不应含 .. 或 .。"""
    s = str(SCHEMA_PATH)
    assert ".." not in s.split("schemas")


def test_schema_path_filename():
    assert SCHEMA_PATH.name == "document.schema.json"


def test_schema_path_parent_named_schemas():
    assert SCHEMA_PATH.parent.name == "schemas"


def test_schema_path_file_exists():
    assert SCHEMA_PATH.is_file()


def test_schema_path_in_module_dict():
    assert "SCHEMA_PATH" in dir(schema_module)


def test_schema_path_is_pathlib_path_not_str():
    assert not isinstance(SCHEMA_PATH, str)


# =============================================================================
# SchemaValidationError 类深度
# =============================================================================


def test_schema_validation_error_is_exception_subclass():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_not_value_error():
    assert not issubclass(SchemaValidationError, ValueError)


def test_schema_validation_error_not_key_error():
    assert not issubclass(SchemaValidationError, KeyError)


def test_schema_validation_error_init_with_message_only():
    e = SchemaValidationError("msg")
    assert str(e) == "msg"
    assert e.errors == []


def test_schema_validation_error_init_with_none_errors():
    e = SchemaValidationError("msg", None)
    assert e.errors == []


def test_schema_validation_error_init_with_empty_list_errors():
    e = SchemaValidationError("msg", [])
    assert e.errors == []


def test_schema_validation_error_init_with_errors_passthrough():
    errs = [{"path": [], "message": "x"}]
    e = SchemaValidationError("msg", errs)
    assert e.errors is errs


def test_schema_validation_error_args():
    e = SchemaValidationError("msg")
    assert e.args == ("msg",)


def test_schema_validation_error_can_be_raised():
    with pytest.raises(SchemaValidationError):
        raise SchemaValidationError("x")


def test_schema_validation_error_caught_as_exception():
    try:
        raise SchemaValidationError("x")
    except Exception as e:
        assert isinstance(e, SchemaValidationError)


def test_schema_validation_error_repr_has_class_name():
    e = SchemaValidationError("msg")
    assert "SchemaValidationError" in repr(e)


def test_schema_validation_error_errors_attribute_writable():
    e = SchemaValidationError("msg")
    e.errors = [{"x": 1}]
    assert e.errors == [{"x": 1}]


def test_schema_validation_error_chained_with_cause():
    try:
        try:
            raise ValueError("orig")
        except ValueError as ve:
            raise SchemaValidationError("wrapped") from ve
    except SchemaValidationError as e:
        assert isinstance(e.__cause__, ValueError)


# =============================================================================
# load_schema 函数深度
# =============================================================================


def test_load_schema_default_returns_dict():
    s = load_schema()
    assert isinstance(s, dict)


def test_load_schema_default_path_is_document_schema():
    s = load_schema()
    assert s.get("$id") == "https://kvfs.local/schemas/document.schema.json"


def test_load_schema_returns_fresh_dict_each_call():
    s1 = load_schema()
    s2 = load_schema()
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_modifications_do_not_leak():
    s1 = load_schema()
    s1["$test_mod"] = "x"
    s2 = load_schema()
    assert "$test_mod" not in s2


def test_load_schema_str_path_accepted(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    s = load_schema(str(p))
    assert s == {"type": "object"}


def test_load_schema_pathlib_path_accepted(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    s = load_schema(p)
    assert s == {"type": "object"}


def test_load_schema_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "missing.json")


def test_load_schema_directory_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path)


def test_load_schema_invalid_json_raises_jsonerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_empty_file_raises_jsonerror(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_error_message_contains_path(tmp_path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as exc:
        load_schema(p)
    assert str(p) in str(exc.value)


def test_load_schema_unicode_filename(tmp_path):
    p = tmp_path / "测试.json"
    p.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    s = load_schema(p)
    assert s == {"type": "object"}


def test_load_schema_unicode_content(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text(
        json.dumps({"type": "object", "description": "测试"}, ensure_ascii=False),
        encoding="utf-8",
    )
    s = load_schema(p)
    assert s["description"] == "测试"


# =============================================================================
# validate — 默认 schema 行为
# =============================================================================


def test_validate_returns_none_on_valid_pdf():
    assert validate(_valid_pdf_document()) is None


def test_validate_returns_none_on_valid_docx():
    assert validate(_valid_docx_document()) is None


def test_validate_returns_none_on_valid_markdown():
    assert validate(_valid_markdown_document()) is None


def test_validate_returns_none_on_valid_html():
    assert validate(_valid_html_document()) is None


def test_validate_returns_none_on_valid_text():
    assert validate(_valid_text_document()) is None


def test_validate_returns_none_on_valid_ipynb():
    assert validate(_valid_ipynb_document()) is None


def test_validate_does_not_mutate_input_on_success():
    import copy
    d = _valid_pdf_document()
    before = copy.deepcopy(d)
    validate(d)
    assert d == before


def test_validate_does_not_mutate_input_on_failure():
    import copy
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    before = copy.deepcopy(d)
    with pytest.raises(SchemaValidationError):
        validate(d)
    assert d == before


# =============================================================================
# validate — 顶层字段深度
# =============================================================================


def test_validate_schema_version_const_rejects_other():
    d = _valid_pdf_document()
    d["schema_version"] = "1.0.0"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_schema_version_must_be_string():
    d = _valid_pdf_document()
    d["schema_version"] = 0.1
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_document_id_empty_rejected():
    d = _valid_pdf_document()
    d["document_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_path_empty_rejected():
    d = _valid_pdf_document()
    d["source_path"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_hash_uppercase_rejected():
    d = _valid_pdf_document()
    d["source_hash"] = "A" * 64
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_hash_short_rejected():
    d = _valid_pdf_document()
    d["source_hash"] = "a" * 63
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_hash_long_rejected():
    d = _valid_pdf_document()
    d["source_hash"] = "a" * 65
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_hash_non_hex_rejected():
    d = _valid_pdf_document()
    d["source_hash"] = "z" * 64
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_parser_name_empty_rejected():
    d = _valid_pdf_document()
    d["parser_name"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_parser_version_empty_rejected():
    d = _valid_pdf_document()
    d["parser_version"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_type_invalid_rejected():
    d = _valid_pdf_document()
    d["source_type"] = "xml"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_source_type_lowercase_only():
    """enum 都是小写，PDF/pdf 大小写敏感。"""
    d = _valid_pdf_document()
    d["source_type"] = "PDF"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_top_level_extra_field_accepted():
    """document.schema.json 根未设 additionalProperties:false → 允许额外字段。"""
    d = _valid_pdf_document()
    d["unknown_field"] = "x"
    validate(d)  # 不抛


def test_validate_missing_required_field_rejected():
    d = _valid_pdf_document()
    del d["document_id"]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_metadata_any_object_accepts():
    d = _valid_pdf_document()
    d["metadata"] = {"any": {"nested": [1, 2, 3]}, "list": []}
    validate(d)


def test_validate_metadata_must_be_object():
    d = _valid_pdf_document()
    d["metadata"] = "string"
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — element 字段深度
# =============================================================================


def test_validate_element_type_enum_all_eight_values():
    for t in (
        "heading", "paragraph", "list_item", "table",
        "image", "caption", "header", "footer",
    ):
        d = _valid_pdf_document()
        d["elements"][0]["type"] = t
        validate(d)


def test_validate_element_type_invalid_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["type"] = "unknown"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_missing_content_and_resource_path_rejected():
    d = _valid_pdf_document()
    del d["elements"][0]["content"]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_resource_path_only_accepts():
    d = _valid_pdf_document()
    del d["elements"][0]["content"]
    d["elements"][0]["resource_path"] = "images/x.png"
    validate(d)


def test_validate_element_empty_content_rejected():
    """anyOf 要求 content minLength:1 或 resource_path minLength:1。"""
    d = _valid_pdf_document()
    d["elements"][0]["content"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_confidence_zero_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["confidence"] = 0
    validate(d)


def test_validate_element_confidence_one_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["confidence"] = 1
    validate(d)


def test_validate_element_confidence_above_one_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["confidence"] = 1.5
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_confidence_negative_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["confidence"] = -0.1
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_parent_id_null_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["parent_id"] = None
    validate(d)


def test_validate_element_parent_id_string_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["parent_id"] = "e0"
    validate(d)


def test_validate_element_extra_field_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["unknown"] = "x"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_element_metadata_any_object():
    d = _valid_pdf_document()
    d["elements"][0]["metadata"] = {"foo": [1, 2, 3]}
    validate(d)


def test_validate_element_id_empty_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["element_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — PDF source_locator 深度
# =============================================================================


def test_validate_pdf_locator_page_one_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1}
    validate(d)


def test_validate_pdf_locator_page_large_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 9999}
    validate(d)


def test_validate_pdf_locator_page_zero_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 0}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_page_negative_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": -1}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_page_missing_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_with_bbox_accepts():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "bbox": [0, 0, 100, 100]}
    validate(d)


def test_validate_pdf_locator_bbox_three_items_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "bbox": [0, 0, 100]}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_bbox_five_items_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "bbox": [0, 0, 100, 100, 50]}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_bbox_empty_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "bbox": []}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_bbox_string_items_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "bbox": ["a", "b", "c", "d"]}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_pdf_locator_extra_field_accepted():
    """pdf_locator additionalProperties:true。"""
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": 1, "custom": "info"}
    validate(d)


def test_validate_pdf_locator_page_string_rejected():
    d = _valid_pdf_document()
    d["elements"][0]["source_locator"] = {"page": "1"}
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — DOCX source_locator 深度
# =============================================================================


def test_validate_docx_locator_paragraph_index_zero_accepts():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"paragraph_index": 0}
    validate(d)


def test_validate_docx_locator_paragraph_index_negative_rejected():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"paragraph_index": -1}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_docx_locator_min_properties_one():
    """docx_locator 要求 minProperties:1。"""
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_docx_locator_section_string_accepts():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"section": "intro"}
    validate(d)


def test_validate_docx_locator_section_integer_accepts():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"section": 1}
    validate(d)


def test_validate_docx_locator_full_structure_accepts():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {
        "section": 1,
        "paragraph_index": 0,
        "run_index": 0,
        "table_index": 0,
        "row_index": 0,
        "col_index": 0,
        "relationship_id": "rId1",
    }
    validate(d)


def test_validate_docx_locator_extra_field_accepted():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"paragraph_index": 0, "custom": "x"}
    validate(d)


def test_validate_docx_locator_table_index_negative_rejected():
    d = _valid_docx_document()
    d["elements"][0]["source_locator"] = {"table_index": -1}
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — markdown/html/text locator
# =============================================================================


def test_validate_markdown_locator_line_one_accepts():
    d = _valid_markdown_document()
    d["elements"][0]["source_locator"] = {"line": 1}
    validate(d)


def test_validate_markdown_locator_line_zero_rejected():
    d = _valid_markdown_document()
    d["elements"][0]["source_locator"] = {"line": 0}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_markdown_locator_line_missing_rejected():
    d = _valid_markdown_document()
    d["elements"][0]["source_locator"] = {}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_markdown_locator_with_section_path_accepts():
    d = _valid_markdown_document()
    d["elements"][0]["source_locator"] = {"line": 1, "section_path": "Intro"}
    validate(d)


def test_validate_html_locator_with_section_path_accepts():
    d = _valid_html_document()
    d["elements"][0]["source_locator"] = {"line": 1, "section_path": "body"}
    validate(d)


def test_validate_text_locator_extra_field_accepted():
    """text_locator additionalProperties:true。"""
    d = _valid_text_document()
    d["elements"][0]["source_locator"] = {"line": 1, "anything": "yes"}
    validate(d)


# =============================================================================
# validate — ipynb locator
# =============================================================================


def test_validate_ipynb_locator_cell_index_zero_accepts():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": 0, "cell_type": "code"}
    validate(d)


def test_validate_ipynb_locator_cell_index_negative_rejected():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": -1, "cell_type": "code"}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_ipynb_locator_cell_type_invalid_rejected():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": 0, "cell_type": "output"}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_ipynb_locator_cell_type_markdown_accepts():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": 0, "cell_type": "markdown"}
    validate(d)


def test_validate_ipynb_locator_cell_type_raw_accepts():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": 0, "cell_type": "raw"}
    validate(d)


def test_validate_ipynb_locator_missing_cell_index_rejected():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_type": "code"}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_ipynb_locator_missing_cell_type_rejected():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {"cell_index": 0}
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_ipynb_locator_with_line_and_section_accepts():
    d = _valid_ipynb_document()
    d["elements"][0]["source_locator"] = {
        "cell_index": 0,
        "cell_type": "code",
        "line": 1,
        "section_path": "section",
    }
    validate(d)


# =============================================================================
# validate — chunk 字段深度
# =============================================================================


def test_validate_chunk_id_empty_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["chunk_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_text_empty_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["text"] = ""
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_element_ids_empty_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_element_ids"] = []
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_element_ids_empty_string_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_element_ids"] = [""]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_extra_field_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["unknown"] = "x"
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_metadata_any_object():
    d = _valid_pdf_document()
    d["chunks"][0]["metadata"] = {"foo": "bar"}
    validate(d)


def test_validate_chunk_source_spans_valid():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 5}
    ]
    validate(d)


def test_validate_chunk_source_spans_start_zero_accepts():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 0}
    ]
    validate(d)


def test_validate_chunk_source_spans_start_negative_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": -1, "end": 5}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_end_negative_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": -1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_missing_element_id_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"start": 0, "end": 5}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_missing_start_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "end": 5}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_missing_end_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_extra_field_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 5, "extra": 1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_chunk_source_spans_element_id_empty_rejected():
    d = _valid_pdf_document()
    d["chunks"][0]["source_spans"] = [
        {"element_id": "", "start": 0, "end": 5}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — relation/warning/error 字段深度
# =============================================================================


def test_validate_relation_valid():
    d = _valid_pdf_document()
    d["relations"] = [
        {"type": "contains", "from_id": "e1", "to_id": "e2", "metadata": {}}
    ]
    validate(d)


def test_validate_relation_missing_type_rejected():
    d = _valid_pdf_document()
    d["relations"] = [{"from_id": "e1", "to_id": "e2"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_relation_missing_from_id_rejected():
    d = _valid_pdf_document()
    d["relations"] = [{"type": "x", "to_id": "e2"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_relation_missing_to_id_rejected():
    d = _valid_pdf_document()
    d["relations"] = [{"type": "x", "from_id": "e1"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_relation_extra_field_rejected():
    d = _valid_pdf_document()
    d["relations"] = [
        {"type": "x", "from_id": "e1", "to_id": "e2", "extra": 1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_relation_type_empty_rejected():
    d = _valid_pdf_document()
    d["relations"] = [
        {"type": "", "from_id": "e1", "to_id": "e2"}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_relation_metadata_optional():
    d = _valid_pdf_document()
    d["relations"] = [
        {"type": "x", "from_id": "e1", "to_id": "e2"}
    ]
    validate(d)


def test_validate_warning_valid():
    d = _valid_pdf_document()
    d["warnings"] = [
        {"code": "low_confidence", "reason": "OCR uncertain", "details": {}}
    ]
    validate(d)


def test_validate_warning_missing_code_rejected():
    d = _valid_pdf_document()
    d["warnings"] = [{"reason": "x"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_warning_missing_reason_rejected():
    d = _valid_pdf_document()
    d["warnings"] = [{"code": "x"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_warning_extra_field_rejected():
    d = _valid_pdf_document()
    d["warnings"] = [
        {"code": "x", "reason": "y", "extra": 1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_warning_details_optional():
    d = _valid_pdf_document()
    d["warnings"] = [{"code": "x", "reason": "y"}]
    validate(d)


def test_validate_warning_details_any_object():
    d = _valid_pdf_document()
    d["warnings"] = [
        {"code": "x", "reason": "y", "details": {"any": [1, 2]}}
    ]
    validate(d)


def test_validate_error_valid():
    d = _valid_pdf_document()
    d["errors"] = [
        {"code": "parse_failed", "message": "boom", "details": {}}
    ]
    validate(d)


def test_validate_error_missing_code_rejected():
    d = _valid_pdf_document()
    d["errors"] = [{"message": "x"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_error_missing_message_rejected():
    d = _valid_pdf_document()
    d["errors"] = [{"code": "x"}]
    with pytest.raises(SchemaValidationError):
        validate(d)


def test_validate_error_extra_field_rejected():
    d = _valid_pdf_document()
    d["errors"] = [
        {"code": "x", "message": "y", "extra": 1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(d)


# =============================================================================
# validate — 错误格式与排序
# =============================================================================


def test_validate_failure_message_has_count():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert "1 处" in str(exc.value)


def test_validate_failure_message_has_path():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert "schema_version" in str(exc.value)


def test_validate_failure_errors_is_list():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert isinstance(exc.value.errors, list)


def test_validate_failure_each_error_has_three_keys():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    d["document_id"] = ""
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    for e in exc.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


def test_validate_failure_path_is_list():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert isinstance(exc.value.errors[0]["path"], list)


def test_validate_failure_schema_path_is_list():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert isinstance(exc.value.errors[0]["schema_path"], list)


def test_validate_failure_message_is_str():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert isinstance(exc.value.errors[0]["message"], str)


def test_validate_multiple_errors_count_correct():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    d["document_id"] = ""
    d["source_path"] = ""
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    assert "3 处" in str(exc.value)


def test_validate_empty_dict_multiple_errors():
    with pytest.raises(SchemaValidationError) as exc:
        validate({})
    # 所有 13 个 required 字段缺失
    assert len(exc.value.errors) >= 10  # 至少 10 个错误


def test_validate_sorts_errors_by_path():
    """errors 按 absolute_path 排序。"""
    d = _valid_pdf_document()
    # 故意制造 2 个错误，path 排序不同
    d["chunks"] = [{"chunk_id": "", "text": "x", "source_element_ids": ["e1"], "metadata": {}}]
    d["document_id"] = ""
    with pytest.raises(SchemaValidationError) as exc:
        validate(d)
    paths = [tuple(e["path"]) for e in exc.value.errors]
    # 排序：空 tuple（document_id）在 'chunks' 之前
    assert paths == sorted(paths)


# =============================================================================
# validate — 自定义 schema
# =============================================================================


def test_validate_with_custom_schema_accepts(tmp_path):
    custom = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
    validate({"x": 1}, custom)


def test_validate_with_custom_schema_rejects():
    custom = {"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]}
    with pytest.raises(SchemaValidationError):
        validate({"x": "string"}, custom)


def test_validate_with_custom_schema_overrides_default():
    """传 custom schema → 不用 document.schema.json。"""
    permissive = {"type": "object"}
    # 任意 dict 都通过 permissive schema
    validate({}, permissive)


def test_validate_with_empty_schema_accepts_anything():
    """空 schema dict 不约束。"""
    validate({}, {})


def test_validate_with_type_only_schema():
    validate({}, {"type": "object"})
    with pytest.raises(SchemaValidationError):
        validate("not object", {"type": "object"})


# =============================================================================
# validate — 非 dict 输入
# =============================================================================


def test_validate_list_input_fails():
    with pytest.raises(SchemaValidationError):
        validate([1, 2, 3])


def test_validate_string_input_fails():
    with pytest.raises(SchemaValidationError):
        validate("string")


def test_validate_none_input_fails():
    with pytest.raises(SchemaValidationError):
        validate(None)


def test_validate_int_input_fails():
    with pytest.raises(SchemaValidationError):
        validate(42)


# =============================================================================
# is_valid 函数深度
# =============================================================================


def test_is_valid_true_for_valid_pdf():
    assert is_valid(_valid_pdf_document()) is True


def test_is_valid_false_for_invalid_pdf():
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    assert is_valid(d) is False


def test_is_valid_returns_bool_not_truthy_value():
    """明确返回 True/False 实例，不是 truthy 值。"""
    result = is_valid(_valid_pdf_document())
    assert result is True


def test_is_valid_does_not_raise():
    """不抛任何异常。"""
    is_valid({})
    is_valid(None)
    is_valid("string")


def test_is_valid_with_custom_schema_true():
    assert is_valid({"x": 1}, {"type": "object"}) is True


def test_is_valid_with_custom_schema_false():
    assert is_valid("x", {"type": "object"}) is False


# =============================================================================
# validate_file 函数深度
# =============================================================================


def test_validate_file_accepts_str_path(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_valid_pdf_document()), encoding="utf-8")
    validate_file(str(p))


def test_validate_file_accepts_pathlib_path(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_valid_pdf_document()), encoding="utf-8")
    validate_file(p)


def test_validate_file_returns_none_on_success(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps(_valid_pdf_document()), encoding="utf-8")
    assert validate_file(p) is None


def test_validate_file_missing_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json")


def test_validate_file_directory_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path)


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_empty_file_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_invalid_content_raises_schema_error(tmp_path):
    p = tmp_path / "bad.json"
    d = _valid_pdf_document()
    d["schema_version"] = "wrong"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p)


def test_validate_file_with_custom_schema(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    validate_file(p, {"type": "object", "required": ["x"]})


def test_validate_file_with_custom_schema_fails(tmp_path):
    p = tmp_path / "doc.json"
    p.write_text(json.dumps({"x": "string"}), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p, {"type": "object", "properties": {"x": {"type": "integer"}}})


def test_validate_file_unicode_filename(tmp_path):
    p = tmp_path / "测试.json"
    p.write_text(json.dumps(_valid_pdf_document()), encoding="utf-8")
    validate_file(p)


def test_validate_file_nested_path(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    p = nested / "doc.json"
    p.write_text(json.dumps(_valid_pdf_document()), encoding="utf-8")
    validate_file(p)


def test_validate_file_unicode_content(tmp_path):
    p = tmp_path / "doc.json"
    d = _valid_pdf_document()
    d["elements"][0]["content"] = "你好世界"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    validate_file(p)


# =============================================================================
# _silence_unused_import 函数
# =============================================================================


def test_silence_unused_import_returns_none():
    assert _silence_unused_import() is None


def test_silence_unused_import_takes_no_arguments():
    import inspect
    sig = inspect.signature(_silence_unused_import)
    assert len(sig.parameters) == 0


def test_silence_unused_import_callable():
    assert callable(_silence_unused_import)


def test_silence_unused_import_in_module():
    assert hasattr(schema_module, "_silence_unused_import")


def test_silence_unused_import_not_in_all():
    assert "_silence_unused_import" not in schema_all


# =============================================================================
# __all__ 与模块结构
# =============================================================================


def test_all_exports_is_list():
    assert isinstance(schema_all, list)


def test_all_exports_count_six():
    assert len(schema_all) == 6


def test_all_exports_exact_set():
    assert set(schema_all) == {
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    }


def test_all_exports_match_module_attributes():
    for name in schema_all:
        assert hasattr(schema_module, name)


def test_all_exports_no_underscore_prefix():
    for name in schema_all:
        assert not name.startswith("_")


def test_module_imports_json():
    assert hasattr(schema_module, "json")


def test_module_imports_path():
    assert hasattr(schema_module, "Path")


def test_module_imports_draft202012_validator():
    assert hasattr(schema_module, "Draft202012Validator")
    assert schema_module.Draft202012Validator is Draft202012Validator


def test_module_imports_jsvalidation_error():
    """JSValidationError 用于类型提示可见性。"""
    from jsonschema.exceptions import ValidationError as JSValidationError
    assert hasattr(schema_module, "JSValidationError")
    assert schema_module.JSValidationError is JSValidationError


def test_module_path_is_absolute():
    assert schema_module.__file__


# =============================================================================
# 函数签名
# =============================================================================


def test_load_schema_signature_default_param():
    import inspect
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.keys())
    assert params == ["path"]
    assert sig.parameters["path"].default is SCHEMA_PATH


def test_validate_signature_two_params():
    import inspect
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["document", "schema"]


def test_validate_schema_default_none():
    import inspect
    sig = inspect.signature(validate)
    assert sig.parameters["schema"].default is None


def test_is_valid_signature_two_params():
    import inspect
    sig = inspect.signature(is_valid)
    params = list(sig.parameters.keys())
    assert params == ["document", "schema"]


def test_validate_file_signature_two_params():
    import inspect
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema"]
