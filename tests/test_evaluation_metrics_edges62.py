"""evaluation/metrics.py 第六十三轮 edges 测试（Round 567）。

补强 edges61 未触及的角度（第三十六批）。
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _image_resource_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _silent_drop_count,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十六批


def test_null_no_args_raises_batch36():
    with pytest.raises(TypeError):
        _null()  # type: ignore[no-value-for-parameter]


def test_null_returns_fresh_dict_batch36():
    """_null 每次返回新 dict（不共享 reference）。"""
    a = _null("x")
    b = _null("x")
    assert a == b
    assert a is not b
    a["value"] = "mutated"
    assert b["value"] is None


def test_ratio_no_args_raises_batch36():
    with pytest.raises(TypeError):
        _ratio()  # type: ignore[no-value-for-parameter]


def test_ratio_int_one_batch36():
    m = _ratio(1)
    assert m["value"] == 1.0
    assert isinstance(m["value"], float)


def test_ratio_with_string_raises_batch36():
    """float("hello") raises ValueError。"""
    with pytest.raises(ValueError):
        _ratio("hello")  # type: ignore[arg-type]


def test_bool_metric_with_int_one_batch36():
    assert _bool_metric(1)["value"] is True


def test_bool_metric_with_int_zero_batch36():
    assert _bool_metric(0)["value"] is False


def test_bool_metric_with_none_batch36():
    assert _bool_metric(None)["value"] is False


def test_bool_metric_with_list_batch36():
    """非空 list → True。"""
    assert _bool_metric([1])["value"] is True
    assert _bool_metric([])["value"] is False


def test_int_metric_with_string_digit_batch36():
    """int("5") = 5。"""
    assert _int_metric("5")["value"] == 5


def test_int_metric_with_float_huge_batch36():
    m = _int_metric(1234.5678)
    assert m["value"] == 1234


def test_int_metric_with_float_inf_batch36():
    """int(inf) raises OverflowError。"""
    with pytest.raises(OverflowError):
        _int_metric(math.inf)


def test_int_metric_with_none_raises_batch36():
    with pytest.raises(TypeError):
        _int_metric(None)  # type: ignore[arg-type]


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 第三十六批


def test_text_types_count_7_batch36():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_count_4_batch36():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types_batch36():
    """PDF_BBOX 是 TEXT 的真子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES) < set(_TEXT_TYPES)


def test_caption_in_both_tuples_batch36():
    assert "caption" in _TEXT_TYPES
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_table_in_text_not_in_pdf_bbox_batch36():
    assert "table" in _TEXT_TYPES
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_header_footer_in_text_not_in_pdf_bbox_batch36():
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_image_not_in_text_types_batch36():
    assert "image" not in _TEXT_TYPES


def test_not_evaluated_value_batch36():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch36():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- _pdf_locator_ratio 第三十六批


def test_pdf_locator_ratio_mixed_valid_invalid_batch36():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 10, 10]}},  # page=0 无效
        {"type": "image", "source_locator": {"page": 1}},  # image 不需要 bbox
    ]
    out = _pdf_locator_ratio(elements)
    # 2/3 valid
    assert out["value"] == 2 / 3
    assert out["reason"] is None


def test_pdf_locator_ratio_all_invalid_page_batch36():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_bbox_for_paragraph_batch36():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_locator_batch36():
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch36():
    """source_locator 显式 None。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_only_no_bbox_batch36():
    """image 不需要 bbox，page 有效即算。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_table_no_bbox_batch36():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES，page 有效即算。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 第三十六批


def test_docx_locator_ratio_paragraph_index_batch36():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_batch36():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_relationship_id_batch36():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_row_col_batch36():
    elements = [{"type": "table", "source_locator": {
        "table_index": 0, "row_index": 0, "col_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_run_index_batch36():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_rejected_batch36():
    """带 page 的 locator 被拒绝。"""
    elements = [{"type": "paragraph", "source_locator": {
        "page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected_batch36():
    elements = [{"type": "paragraph", "source_locator": {
        "bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_batch36():
    """没有任何 structural key → 0/1。"""
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_locator_batch36():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第三十六批


def test_is_valid_bbox_four_ints_batch36():
    assert _is_valid_bbox([0, 0, 100, 50]) is True


def test_is_valid_bbox_four_floats_batch36():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 50.5]) is True


def test_is_valid_bbox_mixed_int_float_batch36():
    assert _is_valid_bbox([0, 0.0, 100, 50.5]) is True


def test_is_valid_bbox_three_elements_batch36():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_five_elements_batch36():
    assert _is_valid_bbox([0, 0, 100, 50, 0]) is False


def test_is_valid_bbox_with_bool_batch36():
    """bool 是 int 子类但被拒绝。"""
    assert _is_valid_bbox([True, 0, 100, 50]) is False


def test_is_valid_bbox_with_nan_batch36():
    assert _is_valid_bbox([0, 0, math.nan, 50]) is False


def test_is_valid_bbox_with_inf_batch36():
    assert _is_valid_bbox([0, 0, math.inf, 50]) is False


def test_is_valid_bbox_with_string_batch36():
    assert _is_valid_bbox(["0", "0", "100", "50"]) is False


def test_is_valid_bbox_none_batch36():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_tuple_batch36():
    """非 list → False。"""
    assert _is_valid_bbox((0, 0, 100, 50)) is False


# ---------- _image_resource_ratio 第三十六批


def test_image_resource_ratio_missing_resource_path_batch36():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch36():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_none_resource_path_batch36():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_batch36(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_empty_file_batch36(tmp_path):
    """存在但 size=0 → 不算。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_with_image_base_dir_batch36(tmp_path):
    """resource_path 只写文件名，靠 image_base_dir 拼接。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, image_base_dir=tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_batch36(tmp_path):
    img = tmp_path / "ok.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "missing.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 第三十六批


def test_chunk_reference_ratio_partial_invalid_batch36():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e3"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_mixed_valid_invalid_batch36():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1", "e2"]},  # all valid
        {"source_element_ids": ["e1", "e3"]},  # partial → invalid (all() False)
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_chunk_with_empty_ids_batch36():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": []},  # empty → not counted
        {"source_element_ids": ["e1"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_missing_ids_field_batch36():
    elements = [{"element_id": "e1"}]
    chunks = [
        {},  # no source_element_ids field
        {"source_element_ids": ["e1"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_no_chunks_batch36():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_no_elements_batch36():
    """elements=[] → elem_ids=set()，所有 ids 都视为 invalid。"""
    out = _chunk_reference_ratio([], [{"source_element_ids": ["x"]}])
    assert out["value"] == 0.0


# ---------- _strip_unicode_whitespace 第三十六批


def test_strip_unicode_whitespace_nbsp_batch36():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch36():
    """U+2003 EM SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch36():
    """U+3000 IDEOGRAPHIC SPACE。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch36():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch36():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_digits_batch36():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_preserves_special_chars_batch36():
    assert _strip_unicode_whitespace("!@#$%^&*()") == "!@#$%^&*()"


def test_strip_unicode_whitespace_preserves_chinese_batch36():
    assert _strip_unicode_whitespace("你 好 世 界") == "你好世界"


def test_strip_unicode_whitespace_empty_string_batch36():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_only_whitespace_batch36():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_no_whitespace_batch36():
    assert _strip_unicode_whitespace("hello") == "hello"


# ---------- _text_preservation 第三十六批


def test_text_preservation_equal_simple_batch36():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_equal_false_extra_in_chunk_batch36():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_image_excluded_batch36():
    """image 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "should_be_excluded"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_ignored_batch36():
    """空白差异不破坏 equality。"""
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_content_batch36():
    elements = [{"type": "paragraph"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # expected="" actual="" → equal=True, precision/recall=null
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_missing_text_batch36():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]  # no text field
    out = _text_preservation(elements, chunks)
    # actual="" expected="abc" → equal=False, precision null (empty_actual), recall 0/3=0
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_element_missing_type_batch36():
    """element 没有 type → 视为 text（不是 image）。"""
    elements = [{"content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_precision_half_batch36():
    """expected=abc, actual=abcabc → precision = 3/6 = 0.5。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcabc"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 1.0


def test_text_preservation_recall_half_batch36():
    """expected=abcabc, actual=abc → precision=1.0, recall=0.5。"""
    elements = [{"type": "paragraph", "content": "abcabc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5


def test_text_preservation_does_not_mutate_inputs_batch36():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    import copy
    e_before = copy.deepcopy(elements)
    c_before = copy.deepcopy(chunks)
    _text_preservation(elements, chunks)
    assert elements == e_before
    assert chunks == c_before


# ---------- _heading_boundary_ratio 第三十六批


def test_heading_boundary_ratio_no_chunks_batch36():
    """chunks=[] 但有 headings → 0/N=0.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_no_headings_batch36():
    out = _heading_boundary_ratio(
        [{"type": "paragraph", "element_id": "p1"}],
        [{"source_element_ids": ["p1"]}],
    )
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_chunks_no_ids_batch36():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]  # no source_element_ids
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunks_empty_ids_batch36():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_heading_not_first_id_batch36():
    """heading 在 chunk 的 source_element_ids 中但不是第一个 → 不算。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_headings_partial_batch36():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # only h1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 第三十六批


def test_silent_drop_count_no_expectations_batch36():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch36():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type_batch36():
    out = _silent_drop_count({"paragraph": 5}, {"other_key": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type_batch36():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_more_than_expected_batch36():
    """actual > expected → drop=0。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_partial_drop_batch36():
    out = _silent_drop_count(
        {"paragraph": 3},
        {"element_count_by_type": {"paragraph": 5, "heading": 2}},
    )
    # paragraph: 5-3=2; heading: 2-0=2; total=4
    assert out["value"] == 4


def test_silent_drop_count_returns_int_metric_batch36():
    out = _silent_drop_count(
        {"paragraph": 1},
        {"element_count_by_type": {"paragraph": 3}},
    )
    assert isinstance(out["value"], int)
    assert out["value"] == 2


def test_silent_drop_count_no_drop_batch36():
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


# ---------- compute_automatic_metrics 第三十六批


def test_compute_metrics_returns_dict_batch36():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_keys_count_pipeline_failed_batch36():
    """pipeline 失败 → 返回 14 个 key（pipeline_success + error_code + schema_valid + 11 null）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_keys_when_success_batch36():
    """成功 → 14 个 key（含 error_code 但 error 为 None）。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(out.keys()) == expected_keys


def test_compute_metrics_error_code_present_batch36():
    err = {"code": "E_PARSE", "message": "broken"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "E_PARSE"


def test_compute_metrics_error_code_none_when_success_batch36():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_unknown_source_type_batch36():
    """source_type 既非 pdf 也非 docx → locator metrics 都是 not_*_document。"""
    doc = {"source_type": "txt", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "txt", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_with_pdf_locator_batch36():
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_with_docx_locator_batch36():
    doc = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_with_expectations_batch36():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # actual paragraph=1, expected=5 → drop=4
    assert out["silent_drop_count"]["value"] == 4


# ---------- module source forbidden tokens 第五十三批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch36(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch36():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_future_annotations_batch36():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_math_import_batch36():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_counter_import_batch36():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_contains_pathlib_import_batch36():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_text_types_const_batch36():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_contains_pdf_bbox_const_batch36():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_contains_not_evaluated_const_batch36():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_null_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_compute_func_batch36():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_pdf_locator_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_is_valid_bbox_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_image_resource_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_reference_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_strip_whitespace_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_text_preservation_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_heading_boundary_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_silent_drop_func_batch36():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_contains_no_image_elements_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"no_image_elements"' in src


def test_module_source_contains_no_chunks_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"no_chunks"' in src


def test_module_source_contains_no_heading_elements_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"no_heading_elements"' in src


def test_module_source_contains_no_expectations_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"no_expectations"' in src


def test_module_source_contains_empty_actual_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"empty_actual"' in src


def test_module_source_contains_empty_expected_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"empty_expected"' in src


def test_module_source_contains_empty_expected_and_actual_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"empty_expected_and_actual"' in src


def test_module_source_contains_no_elements_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"no_elements"' in src


def test_module_source_contains_pipeline_failed_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_not_pdf_document_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"not_pdf_document"' in src


def test_module_source_contains_not_docx_document_reason_batch36():
    src = inspect.getsource(mmod)
    assert '"not_docx_document"' in src


def test_module_source_contains_all_only_compute_batch36():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第四十九批


def test_signature_null_one_param_batch36():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_one_param_batch36():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_one_param_batch36():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_int_metric_one_param_batch36():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_metrics_params_batch36():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document", "error", "source_type", "expectations", "image_base_dir"
    ]


def test_signature_compute_metrics_image_base_dir_optional_batch36():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_one_param_batch36():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_one_param_batch36():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_is_valid_bbox_one_param_batch36():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]
    assert sig.return_annotation == "bool"


def test_signature_image_resource_two_params_batch36():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_two_params_batch36():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_strip_whitespace_one_param_batch36():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]
    assert sig.return_annotation == "str"


def test_signature_text_preservation_two_params_batch36():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_two_params_batch36():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_silent_drop_count_two_params_batch36():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


# ---------- module 合理性第四十九批


def test_module_imports_math_batch36():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch36():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch36():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch36():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_has_text_types_const_batch36():
    assert hasattr(mmod, "_TEXT_TYPES")
    assert isinstance(mmod._TEXT_TYPES, tuple)


def test_module_has_pdf_bbox_required_types_const_batch36():
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert isinstance(mmod._PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_has_not_evaluated_const_batch36():
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_has_compute_func_batch36():
    assert callable(mmod.compute_automatic_metrics)


def test_module_all_only_compute_batch36():
    assert mmod.__all__ == ["compute_automatic_metrics"]


# ---------- 端到端集成第四十九批


def test_e2e_compute_metrics_full_pdf_batch36():
    """完整 PDF 文档跑指标。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]}},
            {"type": "paragraph", "content": "hello", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_compute_metrics_idempotent_batch36():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    o1 = compute_automatic_metrics(doc, None, "pdf", None)
    o2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert o1 == o2


def test_e2e_compute_metrics_does_not_mutate_doc_batch36():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    import copy
    before = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == before


def test_e2e_compute_metrics_with_all_metrics_evaluated_batch36():
    """所有指标都能 evaluate（非 null）的完整场景。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]}},
            {"type": "paragraph", "content": "body", "element_id": "p1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
        ],
        "chunks": [
            {"text": "titlebody", "source_element_ids": ["h1", "p1"]},
        ],
    }
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["pipeline_success"]["value"] is True
    assert out["silent_drop_count"]["value"] == 0
