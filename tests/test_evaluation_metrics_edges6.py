r"""evaluation/metrics.py 边角测试 - 第六轮（Round 156）。

补强已有 base/edges/edges2-5（共 902 测试）未覆盖的深度：
- 常量精确性（_TEXT_TYPES, _PDF_BBOX_REQUIRED_TYPES, _NOT_EVALUATED）
- _null/_ratio/_bool_metric/_int_metric 返回结构精确
- _strip_unicode_whitespace 边界（NBSP、em space、line separator）
- _is_valid_bbox 边界（bool 拒绝、非有限数拒绝、长度!=4 拒绝）
- compute_automatic_metrics 各分支（error_code 形式、schema_valid 异常路径、by_type 聚合）
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path

import pytest

from evaluation.metrics import (
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
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


# =========================================================================
# 常量精确性
# =========================================================================


def test_text_types_count_is_seven():
    assert len(_TEXT_TYPES) == 7


def test_text_types_exact_members():
    expected = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")
    assert set(_TEXT_TYPES) == set(expected)


def test_text_types_excludes_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_count_is_four():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_exact_members():
    expected = ("heading", "paragraph", "caption", "list_item")
    assert set(_PDF_BBOX_REQUIRED_TYPES) == set(expected)


def test_pdf_bbox_required_types_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_excludes_table():
    """table 不需要 bbox（table 用 cells 表达）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_constants_are_tuples():
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_no_duplicates():
    assert len(_TEXT_TYPES) == len(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_no_duplicates():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == len(set(_PDF_BBOX_REQUIRED_TYPES))


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric 返回结构
# =========================================================================


def test_null_returns_correct_shape():
    m = _null("some_reason")
    assert m == {"value": None, "reason": "some_reason"}


def test_null_returns_new_dict_each_call():
    a = _null("x")
    b = _null("x")
    assert a == b
    assert a is not b


def test_null_value_is_none():
    m = _null("x")
    assert m["value"] is None


def test_null_reason_is_str():
    m = _null("x")
    assert isinstance(m["reason"], str)


def test_null_empty_reason():
    m = _null("")
    assert m["reason"] == ""


def test_ratio_returns_correct_shape():
    m = _ratio(0.5)
    assert m == {"value": 0.5, "reason": None}


def test_ratio_value_is_float():
    m = _ratio(1)
    assert isinstance(m["value"], float)
    assert m["value"] == 1.0


def test_ratio_returns_new_dict_each_call():
    a = _ratio(0.5)
    b = _ratio(0.5)
    assert a is not b


def test_ratio_zero():
    m = _ratio(0)
    assert m["value"] == 0.0


def test_ratio_one():
    m = _ratio(1)
    assert m["value"] == 1.0


def test_bool_metric_returns_correct_shape():
    m = _bool_metric(True)
    assert m == {"value": True, "reason": None}


def test_bool_metric_coerces_to_bool():
    """对 truthy 输入强制 bool()。"""
    m1 = _bool_metric(1)
    m2 = _bool_metric(0)
    assert m1["value"] is True
    assert m2["value"] is False


def test_int_metric_returns_correct_shape():
    m = _int_metric(5)
    assert m == {"value": 5, "reason": None}


def test_int_metric_coerces_to_int():
    m = _int_metric(5.7)
    assert isinstance(m["value"], int)
    assert m["value"] == 5


def test_int_metric_negative():
    m = _int_metric(-3)
    assert m["value"] == -3


def test_int_metric_zero():
    m = _int_metric(0)
    assert m["value"] == 0


# =========================================================================
# _strip_unicode_whitespace 边界
# =========================================================================


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ascii_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_ascii_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_ascii_cr():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_vertical_tab():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_form_feed():
    assert _strip_unicode_whitespace("a\x0cb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    """Non-breaking space (U+00A0) 应被剥离。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """Em space (U+2003) 应被剥离。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """En space (U+2002) 应被剥离。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """全角空格 (U+3000) 应被剥离。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """Line separator (U+2028) 应被剥离。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """Paragraph separator (U+2029) 应被剥离。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """非空白字符（包括标点、emoji、中文）全部保留。"""
    s = "hello,世界!🎉"
    assert _strip_unicode_whitespace(s) == s


def test_strip_unicode_whitespace_all_whitespace():
    """全空白字符串 → 空串。"""
    assert _strip_unicode_whitespace(" \t\n\r 　") == ""


def test_strip_unicode_whitespace_does_not_sort():
    """不重排字符顺序。"""
    assert _strip_unicode_whitespace("c b a") == "cba"


# =========================================================================
# _is_valid_bbox 边界
# =========================================================================


def test_is_valid_bbox_none_returns_false():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_returns_false():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_returns_false():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_list_returns_false():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_valid_int_four():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_valid_float_four():
    assert _is_valid_bbox([1.5, 2.5, 3.5, 4.5]) is True


def test_is_valid_bbox_valid_mixed_int_float():
    assert _is_valid_bbox([1, 2.5, 3, 4.5]) is True


def test_is_valid_bbox_bool_rejected():
    """True/False 是 int 子类，但应被拒绝。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([float("nan"), 2, 3, 4]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([float("inf"), 2, 3, 4]) is False


def test_is_valid_bbox_negative_inf_rejected():
    assert _is_valid_bbox([float("-inf"), 2, 3, 4]) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_tuple_rejected():
    """不是 list → False。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_zero_values_valid():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_valid():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


# =========================================================================
# _pdf_locator_ratio 边界
# =========================================================================


def test_pdf_locator_ratio_empty_returns_no_elements():
    m = _pdf_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid_no_bbox_required():
    """非 _PDF_BBOX_REQUIRED_TYPES 只需要 page≥1。"""
    elements = [
        {"type": "header", "source_locator": {"page": 1}},
        {"type": "footer", "source_locator": {"page": 2}},
        {"type": "table", "source_locator": {"page": 1}},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_heading_without_bbox_invalid():
    elements = [
        {"type": "heading", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_heading_with_valid_bbox_valid():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid():
    elements = [
        {"type": "header", "source_locator": {"page": 0}},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [
        {"type": "header", "source_locator": {"page": -1}},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_none_invalid():
    elements = [
        {"type": "header", "source_locator": {}},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_missing_locator_invalid():
    elements = [
        {"type": "header"},
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "header", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},  # ok
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
        {"type": "table", "source_locator": {"page": 1}},  # ok（table 不需 bbox）
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == pytest.approx(2 / 3)


def test_pdf_locator_ratio_returns_ratio_metric():
    """非空 elements 返回 _ratio (reason=None)。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["reason"] is None


# =========================================================================
# _docx_locator_ratio 边界
# =========================================================================


def test_docx_locator_ratio_empty_returns_no_elements():
    m = _docx_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_docx_locator_ratio_with_page_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_ratio_with_bbox_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [0, 0, 10, 10]}},
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_ratio_with_structural_key_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_ratio_section_key_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"section": "main"}},
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_ratio_no_structural_key_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"unrelated": "x"}},
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_ratio_missing_locator_invalid():
    elements = [{"type": "paragraph"}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_ratio_mixed():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # ok
        {"type": "paragraph", "source_locator": {"page": 1}},  # 含 page → 不行
        {"type": "paragraph", "source_locator": {"section": "x"}},  # ok
    ]
    m = _docx_locator_ratio(elements)
    assert m["value"] == pytest.approx(2 / 3)


# =========================================================================
# _chunk_reference_ratio 边界
# =========================================================================


def test_chunk_reference_ratio_empty_chunks_returns_no_chunks():
    m = _chunk_reference_ratio([], [])
    assert m["value"] is None
    assert m["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_chunk_reference_ratio_with_unknown_id():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["unknown"]},
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.5


def test_chunk_reference_ratio_empty_ids_skipped():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": []},  # 空 → 跳过
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == pytest.approx(1 / 2)


def test_chunk_reference_ratio_missing_ids_key():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {},  # 无 source_element_ids
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == pytest.approx(1 / 2)


def test_chunk_reference_ratio_ids_none():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": None},  # None → 视为 []
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


# =========================================================================
# _heading_boundary_ratio 边界
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    m = _heading_boundary_ratio([], [])
    assert m["value"] is None
    assert m["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_no_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    m = _heading_boundary_ratio(elements, [])
    assert m["value"] == 0.0


def test_heading_boundary_ratio_match_first_id():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1", "p1"]},  # h1 是首 → match
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_ratio_heading_not_first_no_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["p1", "h1"]},  # h1 不是首 → no match
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_heading_boundary_ratio_mixed_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},  # match h1
        {"source_element_ids": ["h3"]},  # match h3
        # h2 无 match
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == pytest.approx(2 / 3)


def test_heading_boundary_ratio_empty_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": []},  # 空 → 不贡献 first id
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


# =========================================================================
# _silent_drop_count 边界
# =========================================================================


def test_silent_drop_count_no_expectations_returns_null():
    m = _silent_drop_count({}, None)
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    m = _silent_drop_count({}, {})
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_returns_null():
    m = _silent_drop_count({}, {"other_field": "x"})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_returns_null():
    m = _silent_drop_count({}, {"element_count_by_type": {}})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_matches_expected():
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 0


def test_silent_drop_count_actual_exceeds_expected():
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    # 实际 > 期望 → 不算 drop
    assert m["value"] == 0


def test_silent_drop_count_actual_less_than_expected():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 2  # 5 - 3


def test_silent_drop_count_missing_type_in_actual():
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 5


def test_silent_drop_count_multiple_types_summed():
    by_type = {"paragraph": 3, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2, "table": 1}}
    m = _silent_drop_count(by_type, exp)
    # paragraph: 5-3=2, heading: 2-1=1, table: 1-0=1 → total=4
    assert m["value"] == 4


# =========================================================================
# compute_automatic_metrics 各分支
# =========================================================================


def test_compute_metrics_pipeline_failed_returns_13_metrics():
    """document=None + error=任意 → pipeline_success=False + 12 null metrics。"""
    m = compute_automatic_metrics(
        document=None, error={"code": "x"}, source_type="pdf", expectations=None
    )
    # 1 pipeline_success + 1 error_code + 1 schema_valid + 11 null（element_count_total 到 silent_drop_count）
    assert len(m) == 14
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "x"
    assert m["schema_valid"]["value"] is None
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    for name in ("element_count_total", "silent_drop_count"):
        assert m[name]["value"] is None
        assert m[name]["reason"] == "pipeline_failed"


def test_compute_metrics_pipeline_failed_error_none_returns_none_error_code():
    """document=None + error=None → error_code.value=None（仍 pipeline_failed）。"""
    m = compute_automatic_metrics(
        document=None, error=None, source_type="pdf", expectations=None
    )
    assert m["error_code"]["value"] is None
    assert m["pipeline_success"]["value"] is False


def test_compute_metrics_minimal_document_pdf():
    """最小合法 document（空 elements/chunks）→ 各指标 null。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 0
    assert m["pdf_locator_valid_ratio"]["value"] is None
    assert m["pdf_locator_valid_ratio"]["reason"] == "no_elements"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert m["image_resource_exists_ratio"]["reason"] == "no_image_elements"
    assert m["chunk_reference_intact_ratio"]["reason"] == "no_chunks"
    assert m["heading_boundary_compliance"]["reason"] == "no_heading_elements"
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_metrics_minimal_document_docx():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None
    )
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_element_count_by_type_aggregation():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
            {"type": "image"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1, "image": 1}


def test_compute_metrics_element_count_missing_type_defaults_unknown():
    doc = {
        "elements": [{"element_id": "e1"}],  # 无 type
        "chunks": [],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"unknown": 1}


def test_compute_metrics_text_preservation_equal_empty():
    """空 elements + 空 chunks → equal=True, precision/recall=null。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"
    assert m["text_char_multiset_recall"]["reason"] == "empty_expected_and_actual"


def test_compute_metrics_text_preservation_perfect_match():
    doc = {
        "elements": [{"type": "paragraph", "content": "hello"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["text_preservation_equal"]["value"] is True
    assert m["text_char_multiset_precision"]["value"] == 1.0
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_compute_metrics_text_preservation_extra_chars_in_chunks():
    doc = {
        "elements": [{"type": "paragraph", "content": "ab"}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["text_preservation_equal"]["value"] is False
    # precision = 2/3 (a,b in actual; c extra)
    assert m["text_char_multiset_precision"]["value"] == pytest.approx(2 / 3)
    # recall = 2/2 (a,b 都在 actual)
    assert m["text_char_multiset_recall"]["value"] == 1.0


def test_compute_metrics_text_preservation_missing_chars_in_chunks():
    doc = {
        "elements": [{"type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "ab", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["text_preservation_equal"]["value"] is False
    # precision = 2/2 (a,b in actual 都 expected)
    assert m["text_char_multiset_precision"]["value"] == 1.0
    # recall = 2/3 (a,b 在 actual；c 丢失)
    assert m["text_char_multiset_recall"]["value"] == pytest.approx(2 / 3)


def test_compute_metrics_schema_check_exception_returns_false_with_reason(
    monkeypatch,
):
    """document_passes_schema 抛异常 → schema_valid=False + exception reason。"""
    doc = {"elements": [], "chunks": []}

    import evaluation.metrics as metrics_mod
    import evaluation.schema_validation as sv_mod

    def _raise(_doc):
        raise ValueError("test error")

    monkeypatch.setattr(sv_mod, "document_passes_schema", _raise)

    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert m["schema_valid"]["value"] is False
    assert "ValueError" in m["schema_valid"]["reason"]


def test_compute_metrics_image_resource_ratio_calls_subfunction():
    doc = {
        "elements": [{"type": "image", "resource_path": "/nonexistent.png"}],
        "chunks": [],
    }
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    # 文件不存在 → ratio=0.0
    assert m["image_resource_exists_ratio"]["value"] == 0.0


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_definition_exact():
    """metrics.py __all__ 只导出 compute_automatic_metrics。"""
    import evaluation.metrics as mod
    assert mod.__all__ == ["compute_automatic_metrics"]


def test_module_imports_math():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "import math" in src


def test_module_imports_counter():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from collections import Counter" in src


def test_module_imports_path():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_uses_future_annotations():
    import evaluation.metrics as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.metrics as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_no_fabrication():
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "不伪造" in doc


def test_module_docstring_mentions_no_return_one():
    """docstring 提及"不返回 1.0"。"""
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "1.0" in doc or "不返回" in doc


def test_module_docstring_mentions_text_preservation_semantics():
    """docstring 详述 text_preservation 语义。"""
    import evaluation.metrics as mod
    doc = mod.__doc__
    assert "text_preservation" in doc or "expected_sequence" in doc


def test_module_constants_present():
    import evaluation.metrics as mod
    assert hasattr(mod, "_TEXT_TYPES")
    assert hasattr(mod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mod, "_NOT_EVALUATED")


def test_module_helper_functions_present():
    import evaluation.metrics as mod
    assert callable(mod._null)
    assert callable(mod._ratio)
    assert callable(mod._bool_metric)
    assert callable(mod._int_metric)
    assert callable(mod._strip_unicode_whitespace)
    assert callable(mod._is_valid_bbox)


def test_module_no_silence_unused():
    import evaluation.metrics as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_compute_automatic_metrics_signature_five_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_param_names_exact():
    sig = inspect.signature(compute_automatic_metrics)
    assert set(sig.parameters) == {
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    }


def test_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_document_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_compute_automatic_metrics_return_annotation_dict():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation).lower()


def test_null_signature_one_param():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1
    assert "reason" in sig.parameters


def test_ratio_signature_one_param():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


def test_bool_metric_signature_one_param():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_int_metric_signature_one_param():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_strip_unicode_whitespace_signature_one_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1
    assert "s" in sig.parameters


def test_is_valid_bbox_signature_one_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_pdf_locator_ratio_signature_one_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert set(sig.parameters) == {"elements"}


def test_docx_locator_ratio_signature_one_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert set(sig.parameters) == {"elements"}


def test_image_resource_ratio_signature_two_params():
    sig = inspect.signature(_image_resource_ratio)
    assert set(sig.parameters) == {"elements", "image_base_dir"}


def test_chunk_reference_ratio_signature_two_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert set(sig.parameters) == {"elements", "chunks"}


def test_text_preservation_signature_two_params():
    sig = inspect.signature(_text_preservation)
    assert set(sig.parameters) == {"elements", "chunks"}


def test_heading_boundary_ratio_signature_two_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert set(sig.parameters) == {"elements", "chunks"}


def test_silent_drop_count_signature_two_params():
    sig = inspect.signature(_silent_drop_count)
    assert set(sig.parameters) == {"by_type", "expectations"}


# =========================================================================
# 综合行为
# =========================================================================


def test_compute_metrics_does_not_mutate_input():
    doc = {
        "elements": [{"type": "paragraph", "content": "hello"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    import copy
    doc_before = copy.deepcopy(doc)
    compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert doc == doc_before


def test_strip_unicode_whitespace_idempotent():
    s = "a b\tc\nd"
    once = _strip_unicode_whitespace(s)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


def test_is_valid_bbox_consistent():
    """同一输入多次调用结果一致。"""
    assert _is_valid_bbox([1, 2, 3, 4]) is True
    assert _is_valid_bbox([1, 2, 3, 4]) is True
    assert _is_valid_bbox([1, 2, 3]) is False
    assert _is_valid_bbox([1, 2, 3]) is False


def test_null_ratio_helpers_independent():
    """_null 和 _ratio 返回独立 dict。"""
    n = _null("x")
    r = _ratio(0.5)
    assert n is not r
    assert n["value"] is None
    assert r["value"] == 0.5
