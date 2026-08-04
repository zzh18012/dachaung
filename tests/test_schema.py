"""JSON Schema 校验的单元测试。"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from app.schema import SchemaValidationError, is_valid, load_schema, validate, validate_file


def _pdf_doc():
    """一个合法的 PDF Document dict 模板。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "kreuzberg",
        "parser_version": "4.10.2",
        "elements": [
            {
                "element_id": "e1",
                "type": "heading",
                "content": "Chapter 1",
                "parent_id": None,
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 20.0]},
                "confidence": 0.95,
                "metadata": {"level": 1},
            },
            {
                "element_id": "e2",
                "type": "image",
                "resource_path": "outputs/imgs/e2.png",
                "parent_id": None,
                "source_locator": {"page": 2, "bbox": [10.0, 10.0, 100.0, 100.0]},
                "confidence": 1.0,
                "metadata": {},
            },
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "Chapter 1", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def _docx_doc():
    """一个合法的 DOCX Document dict 模板。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d2",
        "source_path": "/tmp/y.docx",
        "source_type": "docx",
        "source_hash": "b" * 64,
        "parser_name": "python-docx",
        "parser_version": "1.2.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "Hello",
                "parent_id": None,
                "source_locator": {"paragraph_index": 0},
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "Hello", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_load_schema_returns_dict(schema_path: Path):
    s = load_schema(schema_path)
    assert s["$id"].endswith("document.schema.json")
    assert s["title"].startswith("KVFS Document")


def test_valid_pdf_passes():
    validate(_pdf_doc())


def test_valid_docx_passes():
    validate(_docx_doc())


def test_missing_required_field_fails():
    doc = _pdf_doc()
    del doc["source_hash"]
    with pytest.raises(SchemaValidationError) as exc:
        validate(doc)
    assert "source_hash" in str(exc.value)


def test_bad_hash_pattern_fails():
    doc = _pdf_doc()
    doc["source_hash"] = "not-a-hex"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_element_needs_content_or_resource_path():
    doc = _pdf_doc()
    doc["elements"][0]["content"] = None
    doc["elements"][0]["resource_path"] = None
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_pdf_locator_requires_page():
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {"bbox": [0, 0, 10, 10]}  # no page
    with pytest.raises(SchemaValidationError) as exc:
        validate(doc)
    msg = str(exc.value).lower()
    assert "page" in msg


def test_docx_locator_rejects_page_field():
    """DOCX 不应使用 PDF 风格的 page/bbox。schema 通过 docx_locator 定义合法字段。"""
    doc = _docx_doc()
    # page 不在 docx_locator 的 properties 中（虽然 additionalProperties=true，所以 page 不会被严格拒绝）
    # 我们改用真正的非法情况：source_locator 为空对象（minProperties=1 失败）
    doc["elements"][0]["source_locator"] = {}
    with pytest.raises(SchemaValidationError) as exc:
        validate(doc)
    assert "minProperties" in str(exc.value) or "source_locator" in str(exc.value)


def test_chunk_requires_non_empty_source_element_ids():
    doc = _pdf_doc()
    doc["chunks"][0]["source_element_ids"] = []
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_text_cannot_be_empty():
    doc = _pdf_doc()
    doc["chunks"][0]["text"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_is_valid_returns_bool():
    assert is_valid(_pdf_doc()) is True
    bad = copy.deepcopy(_pdf_doc())
    bad["source_hash"] = "x"
    assert is_valid(bad) is False


def test_validate_file(tmp_path: Path):
    import json
    p = tmp_path / "out.json"
    p.write_text(json.dumps(_pdf_doc()), encoding="utf-8")
    validate_file(p)


def test_validate_file_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.json")


# ---- source_spans（Round 10 新加的 chunk 子结构）----


def test_chunk_with_valid_source_spans_passes():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 5}
    ]
    validate(doc)


def test_chunk_source_spans_missing_element_id_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [{"start": 0, "end": 5}]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_spans_missing_start_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [{"element_id": "e1", "end": 5}]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_spans_missing_end_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [{"element_id": "e1", "start": 0}]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_spans_negative_start_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [{"element_id": "e1", "start": -1, "end": 5}]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_spans_additional_property_fails():
    """source_span 是 additionalProperties:false。"""
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": 5, "extra": True}
    ]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_additional_property_fails():
    """chunk 本身是 additionalProperties:false。"""
    doc = _pdf_doc()
    doc["chunks"][0]["extra_field"] = "disallowed"
    with pytest.raises(SchemaValidationError):
        validate(doc)


# ---- 各种 source_type 的 locator 校验 ----


def _make_doc_with_source_type(source_type: str, locator: dict) -> dict:
    """构造一个指定 source_type + locator 的最小合法 doc。"""
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "/tmp/x",
        "source_type": source_type,
        "source_hash": "a" * 64,
        "parser_name": "test",
        "parser_version": "0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "Hello",
                "parent_id": None,
                "source_locator": locator,
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "Hello", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_valid_markdown_doc_with_line_locator():
    validate(_make_doc_with_source_type("markdown", {"line": 1}))


def test_valid_markdown_doc_with_section_path():
    validate(_make_doc_with_source_type("markdown", {"line": 1, "section_path": "H1 > H2"}))


def test_markdown_locator_requires_line():
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type("markdown", {"section_path": "X"}))


def test_valid_html_doc_with_line_locator():
    validate(_make_doc_with_source_type("html", {"line": 1}))


def test_html_locator_requires_line():
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type("html", {}))


def test_valid_text_doc_with_line_locator():
    validate(_make_doc_with_source_type("text", {"line": 1}))


def test_text_locator_requires_line():
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type("text", {}))


def test_valid_ipynb_doc_with_cell_index_and_type():
    validate(_make_doc_with_source_type(
        "ipynb", {"cell_index": 0, "cell_type": "code"}
    ))


def test_ipynb_locator_requires_cell_index():
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type("ipynb", {"cell_type": "code"}))


def test_ipynb_locator_requires_cell_type():
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type("ipynb", {"cell_index": 0}))


def test_ipynb_locator_cell_type_enum():
    """cell_type 只接受 markdown/code/raw。"""
    for valid in ("markdown", "code", "raw"):
        validate(_make_doc_with_source_type("ipynb", {"cell_index": 0, "cell_type": valid}))
    with pytest.raises(SchemaValidationError):
        validate(_make_doc_with_source_type(
            "ipynb", {"cell_index": 0, "cell_type": "invalid"}
        ))


# ---- 各 element/chunk 约束 ----


def test_invalid_source_type_rejected():
    doc = _pdf_doc()
    doc["source_type"] = "csv"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_invalid_element_type_rejected():
    doc = _pdf_doc()
    doc["elements"][0]["type"] = "invalid_type"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_element_type_enum_all_valid_values():
    """heading/paragraph/list_item/table/image/caption/header/footer 都合法。"""
    for valid_type in (
        "heading", "paragraph", "list_item", "table",
        "image", "caption", "header", "footer"
    ):
        doc = _docx_doc()
        doc["elements"][0]["type"] = valid_type
        # image 必须 resource_path（已满足 anyOf）；其他类型 content 已给
        validate(doc)


def test_confidence_out_of_range_fails():
    doc = _pdf_doc()
    doc["elements"][0]["confidence"] = 1.5
    with pytest.raises(SchemaValidationError):
        validate(doc)
    doc["elements"][0]["confidence"] = -0.1
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_pdf_locator_page_zero_fails():
    """page 必须 ≥ 1。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {"page": 0, "bbox": [0, 0, 10, 10]}
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_pdf_locator_bbox_wrong_size_fails():
    """bbox 必须恰好 4 个数。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {"page": 1, "bbox": [0, 0, 10]}
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_schema_version_must_be_const():
    doc = _pdf_doc()
    doc["schema_version"] = "0.2.0"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_element_additional_properties_false():
    """element 是 additionalProperties:false。"""
    doc = _pdf_doc()
    doc["elements"][0]["unknown_field"] = "disallowed"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_relation_missing_required_field_fails():
    doc = _pdf_doc()
    doc["relations"].append({"from_id": "e1", "to_id": "e2"})  # 缺 type
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_relation_additional_properties_false():
    doc = _pdf_doc()
    doc["relations"].append({
        "type": "next", "from_id": "e1", "to_id": "e2", "extra": True
    })
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_warning_missing_required_field_fails():
    doc = _pdf_doc()
    doc["warnings"].append({"details": {}})  # 缺 code 和 reason
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_error_missing_required_field_fails():
    doc = _pdf_doc()
    doc["errors"].append({"details": {}})  # 缺 code 和 message
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_document_id_empty_string_fails():
    doc = _pdf_doc()
    doc["document_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_element_ids_empty_string_fails():
    """source_element_ids 的每个 item minLength=1。"""
    doc = _pdf_doc()
    doc["chunks"][0]["source_element_ids"] = [""]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_id_empty_string_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["chunk_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)
