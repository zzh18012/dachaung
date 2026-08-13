"""evaluation/metrics.py 第七十轮 edges 测试（Round 589）。

补强 edges64 未触及的角度（第三十九批）。
"""

from __future__ import annotations

import inspect
import json
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十九批


def test_null_with_empty_string_batch39():
    """空字符串作为 reason 也合法。"""
    out = _null("")
    assert out == {"value": None, "reason": ""}


def test_null_with_unicode_reason_batch39():
    out = _null("中文原因")
    assert out["reason"] == "中文原因"


def test_null_with_long_reason_batch39():
    s = "x" * 200
    out = _null(s)
    assert out["reason"] == s
    assert len(out["reason"]) == 200


def test_ratio_with_negative_input_batch39():
    """_ratio 不强校验范围；负数也会被 float()。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_with_nan_input_batch39():
    """NaN 是合法 float 输入。"""
    out = _ratio(float("nan"))
    assert math.isnan(out["value"])


def test_ratio_with_inf_input_batch39():
    out = _ratio(float("inf"))
    assert out["value"] == float("inf")


def test_ratio_with_zero_batch39():
    out = _ratio(0)
    assert out["value"] == 0.0
    assert isinstance(out["value"], float)


def test_ratio_with_one_batch39():
    out = _ratio(1)
    assert out["value"] == 1.0


def test_bool_metric_with_truthy_string_batch39():
    """bool('x') == True。"""
    out = _bool_metric("x")  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_with_empty_string_batch39():
    out = _bool_metric("")  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_zero_int_batch39():
    out = _bool_metric(0)  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_value_is_python_bool_not_numpy_batch39():
    out = _bool_metric(True)
    # Python 内置 bool，不是 numpy.bool_ 等
    assert type(out["value"]) is bool


def test_int_metric_with_negative_value_batch39():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_with_bool_input_batch39():
    """int(True) == 1；int(False) == 0。"""
    assert _int_metric(True)["value"] == 1  # type: ignore[arg-type]
    assert _int_metric(False)["value"] == 0  # type: ignore[arg-type]


def test_int_metric_with_float_input_batch39():
    """int(2.9) == 2（截断）。"""
    out = _int_metric(2.9)  # type: ignore[arg-type]
    assert out["value"] == 2


def test_int_metric_does_not_accept_list_batch39():
    """int([1,2]) 抛 TypeError。"""
    with pytest.raises(TypeError):
        _int_metric([1, 2])  # type: ignore[arg-type]


# ---------- _NOT_EVALUATED / _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第三十九批


def test_not_evaluated_is_lowercase_batch39():
    assert _NOT_EVALUATED.islower()


def test_not_evaluated_is_underscore_separated_batch39():
    assert "_" in _NOT_EVALUATED


def test_text_types_does_not_contain_table_batch39_or_does_it():
    """_TEXT_TYPES 是否含 table？看实际行为（含 table）。"""
    assert "table" in _TEXT_TYPES


def test_text_types_no_duplicates_batch39():
    assert len(set(_TEXT_TYPES)) == len(_TEXT_TYPES)


def test_pdf_bbox_required_types_no_duplicates_batch39():
    assert len(set(_PDF_BBOX_REQUIRED_TYPES)) == len(_PDF_BBOX_REQUIRED_TYPES)


def test_pdf_bbox_required_types_contains_heading_paragraph_batch39():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


# ---------- _is_valid_bbox 第三十九批


def test_is_valid_bbox_tuple_input_batch39():
    """tuple 也是合法的序列容器；当前实现要求 list → False。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_with_three_values_batch39():
    assert _is_valid_bbox([0, 0, 1]) is False


def test_is_valid_bbox_with_five_values_batch39():
    assert _is_valid_bbox([0, 0, 1, 1, 2]) is False


def test_is_valid_bbox_with_nan_value_batch39():
    """math.isfinite(nan) == False → False。"""
    assert _is_valid_bbox([0, 0, float("nan"), 1]) is False


def test_is_valid_bbox_with_inf_value_batch39():
    assert _is_valid_bbox([0, 0, float("inf"), 1]) is False


def test_is_valid_bbox_with_string_value_batch39():
    assert _is_valid_bbox([0, 0, "x", 1]) is False


def test_is_valid_bbox_with_none_value_batch39():
    assert _is_valid_bbox([0, 0, None, 1]) is False


def test_is_valid_bbox_with_empty_list_batch39():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_with_none_input_batch39():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_with_dict_input_batch39():
    """dict 不是 list → False。"""
    assert _is_valid_bbox({"x": 0}) is False


# ---------- _strip_unicode_whitespace 第三十九批


def test_strip_whitespace_empty_string_batch39():
    assert _strip_unicode_whitespace("") == ""


def test_strip_whitespace_only_whitespace_batch39():
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_whitespace_no_whitespace_batch39():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_whitespace_single_char_batch39():
    assert _strip_unicode_whitespace("a") == "a"


def test_strip_whitespace_consecutive_whitespace_batch39():
    """连续多个空白字符都被删除。"""
    assert _strip_unicode_whitespace("a   b\t\tc") == "abc"


def test_strip_whitespace_unicode_nbsp_batch39():
    """U+00A0 NBSP 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_ideographic_space_batch39():
    """U+3000 ideographic space 是 isspace。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_whitespace_em_space_batch39():
    """U+2003 em space 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_preserves_digits_batch39():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_whitespace_preserves_punctuation_batch39():
    assert _strip_unicode_whitespace("a. b, c!") == "a.b,c!"


# ---------- _pdf_locator_ratio 第三十九批


def test_pdf_locator_with_string_page_batch39():
    """page='1'（字符串）→ 不是 int → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": "1"}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_float_page_batch39():
    """page=1.0（float）→ 不是 int → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": 1.0}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_bool_page_true_batch39():
    """page=True → isinstance(True, int) True，但 True >= 1 → valid。

    注意：Python 中 bool 是 int 子类，True == 1。
    """
    elements = [{"type": "table", "source_locator": {"page": True}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_with_bool_page_false_batch39():
    """page=False == 0 → False < 1 → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": False}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_page_zero_batch39():
    elements = [{"type": "table", "source_locator": {"page": 0}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_negative_page_batch39():
    elements = [{"type": "table", "source_locator": {"page": -1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_without_source_locator_batch39():
    """element 没有 source_locator 字段 → loc = {} → invalid。"""
    elements = [{"type": "table"}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_none_source_locator_batch39():
    """source_locator 显式 None → loc = {} → invalid。"""
    elements = [{"type": "table", "source_locator": None}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_missing_page_key_batch39():
    """source_locator 有键但无 page → page=None → invalid。"""
    elements = [{"type": "table", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_paragraph_invalid_bbox_batch39():
    """paragraph 必须有合法 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0]}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_partial_validity_half_batch39():
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "table", "source_locator": {"page": 0}},  # invalid
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.5


# ---------- _docx_locator_ratio 第三十九批


def test_docx_locator_with_table_index_batch39():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_row_col_index_batch39():
    elements = [{"type": "table", "source_locator": {"row_index": 0, "col_index": 1}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_relationship_id_batch39():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_bbox_invalidates_batch39():
    """含 bbox → invalid（DOCX 不该有 bbox）。"""
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0, "bbox": [0, 0, 1, 1]}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_with_empty_source_locator_batch39():
    elements = [{"type": "paragraph", "source_locator": {}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_partial_validity_batch39():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"unknown": "x"}},  # invalid
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.5


def test_docx_locator_returns_float_batch39():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert isinstance(m["value"], float)


def test_docx_locator_does_not_mutate_input_batch39():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    before = str(elements)
    _docx_locator_ratio(elements)
    assert str(elements) == before


# ---------- _image_resource_ratio 第三十九批


def test_image_resource_empty_string_resource_path_batch39():
    """resource_path='' → falsy → invalid。"""
    elements = [{"type": "image", "resource_path": ""}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_empty_file_batch39(tmp_path):
    """文件存在但 size=0 → invalid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_nonexistent_image_base_dir_batch39():
    """image_base_dir 不存在 → Path.is_file() 返回 False → invalid。"""
    elements = [{"type": "image", "resource_path": "x.png"}]
    m = _image_resource_ratio(elements, Path("/nonexistent_dir_xyz"))
    assert m["value"] == 0.0


def test_image_resource_partial_batch39(tmp_path):
    """一半图片存在一半不存在 → 0.5。"""
    img1 = tmp_path / "exists.png"
    img1.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": "/nonexistent/missing.png"},
    ]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.5


def test_image_resource_non_image_elements_ignored_batch39(tmp_path):
    """非 image 元素被忽略；只看 image。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [
        {"type": "paragraph", "resource_path": "/nonexistent/paragraph.png"},
        {"type": "image", "resource_path": str(img)},
    ]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 1.0


def test_image_resource_returns_float_batch39(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img)}]
    m = _image_resource_ratio(elements, None)
    assert isinstance(m["value"], float)


# ---------- _chunk_reference_ratio 第三十九批


def test_chunk_reference_chunk_missing_ids_key_batch39():
    """chunk 无 source_element_ids 键 → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_empty_ids_list_batch39():
    """source_element_ids=[] → 当 falsy → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_returns_float_batch39():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert isinstance(m["value"], float)


def test_chunk_reference_all_valid_batch39():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_chunk_reference_no_chunks_returns_null_batch39():
    """空 chunks 列表 → null + no_chunks。"""
    m = _chunk_reference_ratio([], [])
    assert m["value"] is None
    assert m["reason"] == "no_chunks"


# ---------- _text_preservation 第三十九批


def test_text_preservation_image_only_with_empty_actual_batch39():
    """只 image 元素 + chunks 空 → expected empty, actual empty。"""
    elements = [{"type": "image", "content": "abc"}]
    out = _text_preservation(elements, [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_missing_text_key_batch39():
    """chunk 无 text 键 → 当作 ''。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_element_missing_content_batch39():
    """element 无 content 键 → 当作 ''。"""
    elements = [{"type": "paragraph"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_single_chunk_full_match_batch39():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_text_with_extra_chars_in_actual_batch39():
    """actual 比 expected 多字符 → equal=False。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # common = 3 (a,b,c)
    # precision = 3/4
    # recall = 3/3 = 1.0
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 1.0


def test_text_preservation_text_missing_chars_in_actual_batch39():
    """actual 比 expected 少字符 → equal=False。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # common = 2 (a,b)
    # precision = 2/2 = 1.0
    # recall = 2/3
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_unicode_text_batch39():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_repeated_chars_batch39():
    """重复字符的多集合行为。"""
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    # expected: {a:2, b:2}
    # actual: {a:1, b:1}
    # common: a:1, b:1 → 2
    # precision = 2/2 = 1.0
    # recall = 2/4 = 0.5
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5


def test_text_preservation_chunk_text_int_input_batch39():
    """chunk text 是 int 0 → 当作 ''（c.get('text') or ''）。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": 0}]  # type: ignore[dict-item]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_actual"


# ---------- _heading_boundary_ratio 第三十九批


def test_heading_boundary_no_chunks_batch39():
    """空 chunks → matched=0 → ratio 0.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    m = _heading_boundary_ratio(elements, [])
    assert m["value"] == 0.0


def test_heading_boundary_no_headings_returns_null_batch39():
    """无 heading 元素 → null + no_heading_elements。"""
    elements = [{"type": "paragraph", "element_id": "p1"}]
    m = _heading_boundary_ratio(elements, [])
    assert m["value"] is None
    assert m["reason"] == "no_heading_elements"


def test_heading_boundary_chunk_no_ids_key_batch39():
    """chunk 无 source_element_ids → ids=[] → 不贡献 first id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_heading_boundary_two_chunks_match_one_heading_batch39():
    """两个 chunk 都以 h1 开头 + 一个 h2 heading 未匹配 → 0.5。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.5


def test_heading_boundary_returns_float_batch39():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert isinstance(m["value"], float)


# ---------- _silent_drop_count 第三十九批


def test_silent_drop_count_returns_int_metric_format_batch39():
    """返回 _int_metric 格式：{value: int, reason: None}。"""
    m = _silent_drop_count({"a": 1}, {"element_count_by_type": {"a": 5}})
    assert m == {"value": 4, "reason": None}


def test_silent_drop_count_empty_expectations_returns_null_batch39():
    m = _silent_drop_count({"a": 1}, {})
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_none_expectations_returns_null_batch39():
    m = _silent_drop_count({"a": 1}, None)
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_empty_expected_counts_returns_null_batch39():
    """expectations 有键但 element_count_by_type 为空 → null。"""
    m = _silent_drop_count({"a": 1}, {"element_count_by_type": {}})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expected_in_by_type_missing_batch39():
    """expected 含 by_type 没有的 type → 实际是 0，drop 全部。"""
    m = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert m["value"] == 5


def test_silent_drop_count_actual_greater_than_expected_batch39():
    """actual > expected → 不计入 drop（max(0, exp-actual)）。"""
    m = _silent_drop_count({"a": 10}, {"element_count_by_type": {"a": 5}})
    assert m["value"] == 0


def test_silent_drop_count_actual_equal_expected_batch39():
    m = _silent_drop_count({"a": 5}, {"element_count_by_type": {"a": 5}})
    assert m["value"] == 0


# ---------- compute_automatic_metrics 第三十九批


def test_compute_metrics_returns_dict_batch39():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_total_key_count_batch39():
    """doc=None 时返回 14 个键（pipeline_success / error_code / schema_valid + 11 个 null 指标）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_doc_none_keys_exact_batch39():
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = {
        "pipeline_success",
        "error_code",
        "schema_valid",
        "element_count_total",
        "element_count_by_type",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(out.keys()) == expected_keys


def test_compute_metrics_error_dict_no_message_key_batch39():
    """error dict 只要含 code 即可，message 可缺。"""
    error = {"code": "x"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["error_code"]["value"] == "x"


def test_compute_metrics_minimal_doc_all_metrics_present_batch39():
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 全部 14 个键都应存在
    assert "silent_drop_count" in out
    assert "heading_boundary_compliance" in out


def test_compute_metrics_minimal_doc_no_elements_locator_null_batch39():
    """空 elements → locator ratio null + no_elements。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_minimal_doc_no_chunks_chunk_ref_null_batch39():
    """空 chunks → chunk_reference_intact_ratio null + no_chunks。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_metrics_minimal_doc_no_heading_null_batch39():
    """无 heading → heading_boundary null + no_heading_elements。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"


def test_compute_metrics_docx_source_pdf_locator_null_batch39():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_does_not_mutate_input_batch39():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before


def test_compute_metrics_pipeline_success_with_doc_and_no_error_batch39():
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_pipeline_success_false_when_doc_none_batch39():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_false_when_error_set_batch39():
    """error is not None → pipeline_success=False（即使 doc 非 None）。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    error = {"code": "x"}
    out = compute_automatic_metrics(doc, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_schema_check_exception_batch39():
    """document_passes_schema 抛异常时 schema_valid 应记录 schema_check_exception:...。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert out["schema_valid"]["reason"] == "schema_check_exception:RuntimeError"


def test_compute_metrics_error_code_no_code_key_raises_batch39():
    """error dict 无 code → 抛 KeyError（直接 error["code"] 访问）。"""
    error = {"message": "x"}
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, error, "pdf", None)


# ---------- module source forbidden tokens 第六十三批


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
def test_module_source_no_forbidden_tokens_batch39(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十九批


def test_module_source_contains_design_doc_batch39():
    src = inspect.getsource(mmod)
    assert "纯函数" in src


def test_module_source_contains_text_types_definition_batch39():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_definition_batch39():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_null_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_compute_function_batch39():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_counter_import_batch39():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_contains_math_import_batch39():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_pathlib_import_batch39():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch39():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_text_preservation_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_strip_whitespace_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_is_valid_bbox_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_pdf_locator_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_image_resource_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_reference_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_heading_boundary_helper_batch39():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


# ---------- signatures 第五十九批


def test_signature_null_one_param_batch39():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_one_param_batch39():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_one_param_batch39():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_int_metric_one_param_batch39():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_metrics_five_params_batch39():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_image_base_dir_optional_batch39():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_metrics_returns_dict_batch39():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation)


def test_signature_silent_drop_count_two_params_batch39():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


# ---------- module 合理性第五十九批


def test_module_has_all_attribute_batch39():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch39():
    assert isinstance(mmod.__all__, list)


def test_module_all_only_compute_automatic_metrics_batch39():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_all_len_one_batch39():
    assert len(mmod.__all__) == 1


def test_module_does_not_export_helpers_batch39():
    """私有 _xxx 不在 __all__。"""
    for name in ("_null", "_ratio", "_bool_metric", "_int_metric",
                 "_text_preservation", "_strip_unicode_whitespace", "_is_valid_bbox"):
        assert name not in mmod.__all__


def test_module_does_not_define_class_batch39():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_normalize_text_not_imported_batch39():
    src = inspect.getsource(mmod)
    assert "import normalize_text" not in src
    assert "from app.chunkers" not in src


def test_module_text_preservation_uses_strip_unicode_whitespace_batch39():
    src = inspect.getsource(mmod)
    assert "_strip_unicode_whitespace(expected_raw)" in src
    assert "_strip_unicode_whitespace(actual_raw)" in src


def test_module_has_future_annotations_batch39():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


# ---------- 端到端集成第五十九批


def test_e2e_compute_metrics_full_pdf_with_image_batch39(tmp_path):
    """完整 PDF + image + chunks + expectations。"""
    img = tmp_path / "fig.png"
    img.write_bytes(b"data")
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
            {"type": "image", "element_id": "e2",
             "source_locator": {"page": 1}, "resource_path": str(img)},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["e1"]},
        ],
    }
    expectations = {"element_count_by_type": {"heading": 1, "image": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations, image_base_dir=tmp_path)
    assert out["pipeline_success"]["value"] is True
    assert out["image_resource_exists_ratio"]["value"] == 1.0
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_compute_metrics_text_preservation_with_strip_batch39():
    """text_preservation 在含空白场景下应正确判定 equal。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "Hello World", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [
            {"text": "HelloWorld", "source_element_ids": ["e1"]},  # 无空白
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # strip 后都为 "HelloWorld"
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_e2e_compute_metrics_idempotent_batch39():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_e2e_compute_metrics_json_serializable_batch39():
    """输出全 JSON serializable。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    json.dumps(out, ensure_ascii=False)


def test_e2e_compute_metrics_no_mutate_when_pipeline_failed_batch39():
    """doc=None 路径也不修改 error dict。"""
    error = {"code": "x", "message": "y"}
    error_before = json.dumps(error, sort_keys=True)
    compute_automatic_metrics(None, error, "pdf", None)
    assert json.dumps(error, sort_keys=True) == error_before
