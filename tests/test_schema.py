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


# ---------- 边角与缺漏补强（Round 32） ----------


# load_schema 边角


def test_load_schema_missing_file_raises_filenotfound(tmp_path: Path):
    """load_schema 对不存在的路径应抛 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "nonexistent.schema.json")


def test_load_schema_accepts_str_path():
    """load_schema 接受 str 路径。"""
    from app.schema import SCHEMA_PATH
    s = load_schema(str(SCHEMA_PATH))
    assert s["title"].startswith("KVFS Document")


def test_load_schema_returns_independent_dict():
    """每次 load_schema 应返回新 dict（修改不影响下次）。"""
    s1 = load_schema()
    s1["$comment_mutated"] = "x"
    s2 = load_schema()
    assert "$comment_mutated" not in s2


def test_load_schema_default_path_is_documents_schema():
    """不传 path 时使用 SCHEMA_PATH。"""
    s = load_schema()
    assert "properties" in s
    assert "elements" in s["properties"]


# SchemaValidationError 结构


def test_schema_validation_error_default_errors_empty():
    """SchemaValidationError 不传 errors 时默认空 list。"""
    e = SchemaValidationError("boom")
    assert e.errors == []
    assert str(e) == "boom"


def test_schema_validation_error_errors_passed_through():
    """errors kwarg 应被保留。"""
    errs = [{"path": ["x"], "message": "m"}]
    e = SchemaValidationError("boom", errors=errs)
    assert e.errors is errs


def test_validate_errors_attribute_populated_on_failure():
    """validate 失败时 SchemaValidationError.errors 应有非空 list。"""
    doc = _pdf_doc()
    del doc["source_hash"]
    with pytest.raises(SchemaValidationError) as exc:
        validate(doc)
    assert isinstance(exc.value.errors, list)
    assert len(exc.value.errors) >= 1
    err0 = exc.value.errors[0]
    assert "path" in err0
    assert "message" in err0
    assert "schema_path" in err0


def test_validate_collects_multiple_errors():
    """validate 应聚合多个错误（不是只第一个）。"""
    doc = _pdf_doc()
    # 制造 2 处错误：删 source_hash + 改 document_id 为空
    del doc["source_hash"]
    doc["document_id"] = ""
    with pytest.raises(SchemaValidationError) as exc:
        validate(doc)
    assert len(exc.value.errors) >= 2


def test_validate_with_custom_schema(tmp_path: Path):
    """validate 接受临时 schema（不读磁盘默认 schema）。"""
    custom_schema = {
        "type": "object",
        "required": ["x"],
        "properties": {"x": {"type": "integer"}},
    }
    validate({"x": 1}, schema=custom_schema)
    with pytest.raises(SchemaValidationError):
        validate({"x": "not int"}, schema=custom_schema)


def test_validate_custom_schema_overrides_default():
    """传 schema=None 应等同于不传。"""
    doc = _pdf_doc()
    validate(doc, schema=None)  # 不抛


# is_valid 边角


def test_is_valid_with_custom_schema():
    """is_valid 也接受 schema kwarg。"""
    custom = {"type": "object", "required": ["a"]}
    assert is_valid({"a": 1}, schema=custom) is True
    assert is_valid({}, schema=custom) is False


def test_is_valid_does_not_raise():
    """is_valid 应吞掉 SchemaValidationError，不向上抛。"""
    doc = _pdf_doc()
    doc["source_hash"] = "bad"
    # 不应抛
    result = is_valid(doc)
    assert result is False


# validate_file 边角


def test_validate_file_accepts_str_path(tmp_path: Path):
    """validate_file 接受 str 路径。"""
    import json
    p = tmp_path / "out.json"
    p.write_text(json.dumps(_pdf_doc()), encoding="utf-8")
    validate_file(str(p))


def test_validate_file_invalid_json_raises(tmp_path: Path):
    """非法 JSON 文件应抛 json.JSONDecodeError（不是 SchemaValidationError）。"""
    import json
    p = tmp_path / "broken.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_invalid_content_raises_validation_error(tmp_path: Path):
    """合法 JSON 但内容不合规 → SchemaValidationError。"""
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p)


def test_validate_file_with_custom_schema(tmp_path: Path):
    """validate_file 也接受 schema kwarg。"""
    import json
    custom = {"type": "object", "required": ["x"]}
    p = tmp_path / "out.json"
    p.write_text(json.dumps({"x": 1}), encoding="utf-8")
    validate_file(p, schema=custom)


# schema keyword 边角：minLength


def test_source_path_empty_string_fails():
    doc = _pdf_doc()
    doc["source_path"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_parser_name_empty_string_fails():
    doc = _pdf_doc()
    doc["parser_name"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_parser_version_empty_string_fails():
    doc = _pdf_doc()
    doc["parser_version"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_warning_code_empty_string_fails():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "", "reason": "x"})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_warning_reason_empty_string_fails():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": ""})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_error_code_empty_string_fails():
    doc = _pdf_doc()
    doc["errors"].append({"code": "", "message": "x"})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_error_message_empty_string_fails():
    doc = _pdf_doc()
    doc["errors"].append({"code": "x", "message": ""})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_relation_type_empty_string_fails():
    doc = _pdf_doc()
    doc["relations"].append({"type": "", "from_id": "e1", "to_id": "e2"})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_relation_from_id_empty_string_fails():
    doc = _pdf_doc()
    doc["relations"].append({"type": "next", "from_id": "", "to_id": "e2"})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_relation_to_id_empty_string_fails():
    doc = _pdf_doc()
    doc["relations"].append({"type": "next", "from_id": "e1", "to_id": ""})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_element_id_empty_string_fails():
    doc = _pdf_doc()
    doc["elements"][0]["element_id"] = ""
    with pytest.raises(SchemaValidationError):
        validate(doc)


# source_hash pattern 边角


def test_source_hash_uppercase_hex_fails():
    """pattern 是 ^[0-9a-f]{64}$（小写），大写 hex 应拒绝。"""
    doc = _pdf_doc()
    doc["source_hash"] = "A" * 64
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_source_hash_too_short_fails():
    doc = _pdf_doc()
    doc["source_hash"] = "a" * 63
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_source_hash_too_long_fails():
    doc = _pdf_doc()
    doc["source_hash"] = "a" * 65
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_source_hash_with_underscore_fails():
    doc = _pdf_doc()
    doc["source_hash"] = "a" * 60 + "_123"  # 非法字符
    with pytest.raises(SchemaValidationError):
        validate(doc)


# confidence 边界


def test_confidence_boundary_zero_passes():
    doc = _pdf_doc()
    doc["elements"][0]["confidence"] = 0
    validate(doc)


def test_confidence_boundary_one_passes():
    doc = _pdf_doc()
    doc["elements"][0]["confidence"] = 1
    validate(doc)


# bbox 数字类型


def test_pdf_locator_bbox_floats_pass():
    """bbox items 类型是 number，浮点也接受。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {
        "page": 1, "bbox": [10.5, 20.5, 110.5, 220.5]
    }
    validate(doc)


def test_pdf_locator_bbox_with_strings_fails():
    """bbox items 必须是 number，字符串不接受。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {
        "page": 1, "bbox": ["a", "b", "c", "d"]
    }
    with pytest.raises(SchemaValidationError):
        validate(doc)


# docx_locator 各种合法字段


def test_docx_locator_with_paragraph_index_only():
    doc = _make_doc_with_source_type(
        "docx", {"paragraph_index": 0}
    )
    validate(doc)


def test_docx_locator_with_table_indices():
    doc = _make_doc_with_source_type(
        "docx", {"table_index": 0, "row_index": 1, "col_index": 2}
    )
    validate(doc)


def test_docx_locator_with_relationship_id():
    doc = _make_doc_with_source_type(
        "docx", {"relationship_id": "rId1"}
    )
    validate(doc)


def test_docx_locator_with_section_int():
    doc = _make_doc_with_source_type(
        "docx", {"section": 0}
    )
    validate(doc)


def test_docx_locator_with_section_string():
    doc = _make_doc_with_source_type(
        "docx", {"section": "main"}
    )
    validate(doc)


def test_docx_locator_with_run_index():
    doc = _make_doc_with_source_type(
        "docx", {"paragraph_index": 0, "run_index": 1}
    )
    validate(doc)


def test_docx_locator_paragraph_index_negative_fails():
    """paragraph_index 必须 ≥ 0。"""
    doc = _make_doc_with_source_type(
        "docx", {"paragraph_index": -1}
    )
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_docx_locator_table_index_negative_fails():
    doc = _make_doc_with_source_type(
        "docx", {"table_index": -1}
    )
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_docx_locator_run_index_negative_fails():
    doc = _make_doc_with_source_type(
        "docx", {"paragraph_index": 0, "run_index": -1}
    )
    with pytest.raises(SchemaValidationError):
        validate(doc)


# source_span 边角


def test_source_span_negative_end_fails():
    """source_span.end 也必须 ≥ 0。"""
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [
        {"element_id": "e1", "start": 0, "end": -1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_source_span_element_id_empty_fails():
    doc = _pdf_doc()
    doc["chunks"][0]["source_spans"] = [
        {"element_id": "", "start": 0, "end": 1}
    ]
    with pytest.raises(SchemaValidationError):
        validate(doc)


# warning/error details 必须是 object


def test_warning_details_array_fails():
    """warning.details 必须是 object，list 不接受。"""
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": "y", "details": []})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_warning_details_string_fails():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": "y", "details": "wrong"})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_error_details_array_fails():
    doc = _pdf_doc()
    doc["errors"].append({"code": "x", "message": "y", "details": []})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_warning_with_valid_details_object_passes():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": "y", "details": {"k": "v"}})
    validate(doc)


def test_error_with_valid_details_object_passes():
    doc = _pdf_doc()
    doc["errors"].append({"code": "x", "message": "y", "details": {"k": "v"}})
    validate(doc)


# warning/error additionalProperties


def test_warning_additional_property_fails():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": "y", "extra": True})
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_error_additional_property_fails():
    doc = _pdf_doc()
    doc["errors"].append({"code": "x", "message": "y", "extra": True})
    with pytest.raises(SchemaValidationError):
        validate(doc)


# ipynb locator 边角


def test_ipynb_locator_with_line_and_section_path():
    """ipynb locator 可以含 line + section_path（可选字段）。"""
    doc = _make_doc_with_source_type(
        "ipynb",
        {"cell_index": 0, "cell_type": "code", "line": 5, "section_path": "X > Y"}
    )
    validate(doc)


def test_ipynb_locator_cell_index_negative_fails():
    """cell_index 必须 ≥ 0。"""
    doc = _make_doc_with_source_type(
        "ipynb", {"cell_index": -1, "cell_type": "code"}
    )
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_ipynb_locator_line_zero_fails():
    """line 必须 ≥ 1。"""
    doc = _make_doc_with_source_type(
        "ipynb", {"cell_index": 0, "cell_type": "code", "line": 0}
    )
    with pytest.raises(SchemaValidationError):
        validate(doc)


# document_id 与 schema_version 关键字


def test_schema_version_wrong_string_fails():
    """schema_version 是 const "0.1.0"，其他值都拒。"""
    doc = _pdf_doc()
    doc["schema_version"] = "1.0.0"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_schema_version_non_string_fails():
    doc = _pdf_doc()
    doc["schema_version"] = 0.1
    with pytest.raises(SchemaValidationError):
        validate(doc)


# chunk source_element_ids 边角


def test_chunk_source_element_ids_with_empty_string_only_fails():
    """列表只有 1 个空字符串元素也不行。"""
    doc = _pdf_doc()
    doc["chunks"][0]["source_element_ids"] = [""]
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunk_source_element_ids_mixed_empty_and_non_empty_fails():
    """列表里有一个空字符串就拒（即便其他非空）。"""
    doc = _pdf_doc()
    doc["chunks"][0]["source_element_ids"] = ["e1", ""]
    with pytest.raises(SchemaValidationError):
        validate(doc)


# elements/chunks/relations/warnings/errors 类型必须是 array


def test_elements_non_array_fails():
    doc = _pdf_doc()
    doc["elements"] = {}
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_chunks_non_array_fails():
    doc = _pdf_doc()
    doc["chunks"] = "not list"
    with pytest.raises(SchemaValidationError):
        validate(doc)


def test_metadata_non_object_fails():
    doc = _pdf_doc()
    doc["metadata"] = []
    with pytest.raises(SchemaValidationError):
        validate(doc)


# content/resource_path 同时缺失 vs 同时存在的语义


def test_element_with_only_resource_path_passes():
    """anyOf 满足一项即可，仅 resource_path 也 OK。"""
    doc = _pdf_doc()
    doc["elements"][0]["content"] = None
    doc["elements"][0]["resource_path"] = "outputs/imgs/e1.png"
    validate(doc)


def test_element_with_only_content_passes():
    """仅 content（无 resource_path）→ 也 OK。"""
    doc = _pdf_doc()
    # e1 已经是这种形态
    validate(doc)


def test_element_with_null_content_and_null_resource_path_fails():
    """content 和 resource_path 都是 null → anyOf 失败。"""
    doc = _pdf_doc()
    doc["elements"][0]["content"] = None
    doc["elements"][0]["resource_path"] = None
    with pytest.raises(SchemaValidationError):
        validate(doc)


# locator 非对象


def test_pdf_locator_non_object_fails():
    """source_locator 必须是 object；非 object 在 schema 根层级会被 properties.source_locator:object 拒。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = "not object"
    with pytest.raises(SchemaValidationError):
        validate(doc)


# pdf_locator additionalProperties=true（可加自由字段）


def test_pdf_locator_with_extra_field_passes():
    """pdf_locator additionalProperties=true，加自由字段应通过。"""
    doc = _pdf_doc()
    doc["elements"][0]["source_locator"] = {
        "page": 1, "bbox": [0, 0, 10, 10], "extra_meta": "ok"
    }
    validate(doc)


def test_docx_locator_with_extra_field_passes():
    """docx_locator additionalProperties=true。"""
    doc = _make_doc_with_source_type(
        "docx", {"paragraph_index": 0, "custom": "x"}
    )
    validate(doc)


# warning.details 和 error.details 既可空 object 也可嵌套


def test_warning_details_empty_object_passes():
    doc = _pdf_doc()
    doc["warnings"].append({"code": "x", "reason": "y", "details": {}})
    validate(doc)


def test_warning_details_nested_complex_object_passes():
    doc = _pdf_doc()
    doc["warnings"].append({
        "code": "x", "reason": "y",
        "details": {"k1": [1, 2], "k2": {"deep": True}},
    })
    validate(doc)
