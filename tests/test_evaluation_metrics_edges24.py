"""evaluation/metrics.py 第二十五轮 edges 测试（Round 310）。

重点补强 edges23 未触及的角度：
- _ratio / _null / _bool_metric / _int_metric 类型与值精确
- _ratio 不做范围 clamp（接受任意 float，包括负数/inf/nan）
- compute_automatic_metrics 参数 image_base_dir 默认 None
- _is_valid_bbox 边界（bool 拒绝、list 长度、math.isfinite）
- _strip_unicode_whitespace Unicode 类别深度
- _text_preservation 数学不变量与分支
- _silent_drop_count 两层 null 分支
- _chunk_reference_ratio 边界
- _heading_boundary_ratio 边界
- _image_resource_ratio 边界
- _pdf_locator_ratio / _docx_locator_ratio 互斥
- module source forbidden tokens
- module source 字符串精确
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.metrics as m
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


# ---------- _ratio / _null / _bool_metric / _int_metric 精确 ----------


def test_ratio_returns_float_for_int():
    r = _ratio(1)
    assert r["value"] == 1.0
    assert isinstance(r["value"], float)


def test_ratio_returns_float_for_float():
    r = _ratio(0.5)
    assert r["value"] == 0.5
    assert isinstance(r["value"], float)


def test_ratio_negative_zero_not_clamped():
    r = _ratio(-0.0)
    assert math.copysign(1.0, r["value"]) == -1.0  # 保留负号


def test_ratio_negative_value_not_clamped():
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_ratio_above_one_not_clamped():
    r = _ratio(2.5)
    assert r["value"] == 2.5


def test_ratio_inf_not_clamped():
    r = _ratio(math.inf)
    assert math.isinf(r["value"])


def test_ratio_nan_not_clamped():
    r = _ratio(math.nan)
    assert math.isnan(r["value"])


def test_ratio_reason_always_none():
    assert _ratio(0.5)["reason"] is None
    assert _ratio(math.inf)["reason"] is None
    assert _ratio(math.nan)["reason"] is None


def test_null_reason_preserved():
    assert _null("xyz") == {"value": None, "reason": "xyz"}


def test_null_value_always_none():
    assert _null("anything")["value"] is None


def test_bool_metric_true():
    assert _bool_metric(True) == {"value": True, "reason": None}


def test_bool_metric_false():
    assert _bool_metric(False) == {"value": False, "reason": None}


def test_bool_metric_coerces_truthy_int():
    assert _bool_metric(1) == {"value": True, "reason": None}


def test_bool_metric_coerces_falsy_int():
    assert _bool_metric(0) == {"value": False, "reason": None}


def test_bool_metric_coerces_empty_string():
    assert _bool_metric("") == {"value": False, "reason": None}


def test_bool_metric_coerces_nonempty_string():
    assert _bool_metric("x") == {"value": True, "reason": None}


def test_int_metric_returns_int():
    i = _int_metric(5)
    assert i["value"] == 5
    assert isinstance(i["value"], int)


def test_int_metric_truncates_float():
    i = _int_metric(3.99)
    assert i["value"] == 3


def test_int_metric_negative():
    i = _int_metric(-1)
    assert i["value"] == -1


def test_int_metric_reason_none():
    assert _int_metric(0)["reason"] is None


# ---------- 常量精确 ----------


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_seven_entries():
    assert len(_TEXT_TYPES) == 7


def test_text_types_entries_exact():
    assert set(_TEXT_TYPES) == {
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    }


def test_text_types_image_absent():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_four_entries():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_entries_exact():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {
        "heading",
        "paragraph",
        "caption",
        "list_item",
    }


def test_pdf_bbox_required_types_subset_of_text_types():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_excludes_table_header_footer():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_type_is_str():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- _is_valid_bbox 边界深度 ----------


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_short_list():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_list():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_four_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 100.5]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 100, 100.5]) is True


def test_is_valid_bbox_bool_rejected():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox(["0", 0, 0, 0]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([0, 0, math.inf, 100]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([0, 0, math.nan, 100]) is False


def test_is_valid_bbox_tuple_rejected():
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_negative_value_accepted():
    # 负坐标是合法 float，不拒绝
    assert _is_valid_bbox([-10, -10, 100, 100]) is True


def test_is_valid_bbox_zero_size_accepted():
    # 0x0 矩形是合法 float，不拒绝
    assert _is_valid_bbox([0, 0, 0, 0]) is True


# ---------- _strip_unicode_whitespace Unicode 类别深度 ----------


def test_strip_unicode_whitespace_ascii_spaces():
    assert _strip_unicode_whitespace("a b\tc\nd\re\ff") == "abcdef"


def test_strip_unicode_whitespace_nbsp():
    # U+00A0 NO-BREAK SPACE
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    # U+2003 EM SPACE
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    # U+2002 EN SPACE
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    # U+3000 IDEOGRAPHIC SPACE
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    # U+2028 LINE SEPARATOR
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    # U+2029 PARAGRAPH SEPARATOR
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_does_not_remove_non_whitespace():
    # 标点不删
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_whitespace_does_not_sort():
    # 不排序
    assert _strip_unicode_whitespace("cab") == "cab"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_only_whitespace():
    assert _strip_unicode_whitespace(" \t\n　") == ""


def test_strip_unicode_whitespace_preserves_digits():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_preserves_unicode_letters():
    # 中文不算空白
    assert _strip_unicode_whitespace("你 好") == "你好"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("a b"), str)


# ---------- _text_preservation 数学不变量 ----------


def test_text_preservation_empty_both_yields_null_precision_recall():
    elements = [{"type": "image", "content": ""}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_actual_nonempty_expected_empty_yields_null_recall():
    # expected = "" (image only), actual = "abc"
    elements = [{"type": "image", "content": "irrelevant"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected 为 ""，actual 为 "abc"，equal False
    assert out["equal"]["value"] is False
    # precision = common / |actual| = 0 / 3 = 0.0
    assert out["precision"]["value"] == 0.0
    # recall = common / |expected| = 0 / 0 → empty_expected null
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_actual_empty_expected_nonempty_yields_null_precision():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_full_match_yields_one_one():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_subset_actual_yields_precision_below_one():
    # expected "abc"，actual "ab" → recall=1.0, precision=1.0；不对
    # 改成 expected "abc"，actual "abcd" → precision=3/4, recall=3/3=1
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 1.0


def test_text_preservation_subset_expected_yields_recall_below_one():
    # expected "abcd"，actual "abc" → recall=3/4, precision=3/3=1
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.75


def test_text_preservation_returns_three_keys():
    elements: list[dict] = []
    chunks: list[dict] = []
    out = _text_preservation(elements, chunks)
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_excludes_image_from_expected():
    # image 不参与 expected
    elements = [
        {"type": "image", "content": "XYZ"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["recall"]["value"] == 1.0


def test_text_preservation_whitespace_ignored_in_expected():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_ignored_in_actual():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "a b c"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_reordering_breaks_equal_but_keeps_counter():
    # 顺序错乱 → equal False，但 Counter 看作相同 → p=r=1.0
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_dup_chars():
    # expected "aabb"，actual "abab" → equal False，counter 相同 → p=r=1.0
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "abab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_partial_dup():
    # expected "aaa"，actual "aa" → recall=2/3, precision=2/2=1
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2 / 3) < 1e-9


def test_text_preservation_missing_content_treated_as_empty():
    # element 没 content 字段 → 当空字符串
    elements = [{"type": "paragraph"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_text_none_treated_as_empty():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


# ---------- _silent_drop_count 两层 null ----------


def test_silent_drop_count_no_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_no_element_count_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"some_other_field": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drop_returns_zero():
    by_type = {"paragraph": 5, "heading": 2}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0
    assert out["reason"] is None


def test_silent_drop_count_actual_more_than_expected_no_drop():
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0  # max(0, ...)


def test_silent_drop_count_partial_drop():
    by_type = {"paragraph": 3, "heading": 2}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 2  # only paragraph dropped 2


def test_silent_drop_count_multi_type_drop_sums():
    by_type = {"paragraph": 3, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 4  # 2 + 2


def test_silent_drop_count_expected_type_missing_in_actual():
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 5  # actual=0, drop=5


def test_silent_drop_count_returns_int():
    by_type = {"paragraph": 0}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert isinstance(out["value"], int)


# ---------- _chunk_reference_ratio 边界 ----------


def test_chunk_reference_ratio_no_chunks_returns_null():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_chunks_list_returns_null():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_no_source_ids_skipped():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_ids_field_skipped():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_ids_none_skipped():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_yields_one():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_invalid_yields_half():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["eX"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_all_invalid_yields_zero():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["eX"]},
        {"source_element_ids": ["eY"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_ids_some_invalid():
    # 一个 chunk 的 ids 有 valid 也有 invalid → all() 为 False → 该 chunk 不算
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "eX"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 边界 ----------


def test_heading_boundary_no_headings_returns_null():
    out = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_yields_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_chunk_empty_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_heading_at_first_position_yields_one():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_heading_at_non_first_position_yields_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_partial_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_chunk_no_ids_field_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _image_resource_ratio 边界 ----------


def test_image_resource_no_images_returns_null(tmp_path):
    out = _image_resource_ratio([{"type": "paragraph"}], tmp_path)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_no_resource_path_skipped(tmp_path):
    elements = [{"type": "image"}, {"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_file_exists_yields_one(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_file_missing_yields_zero(tmp_path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "missing.png")}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_empty_file_skipped(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_partial_match(tmp_path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


def test_image_resource_no_base_dir_uses_path_only(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_base_dir_with_filename_fallback(tmp_path):
    """resource_path 只写文件名，image_base_dir 提供目录 → fallback 找到。"""
    img = tmp_path / "a.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": "a.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


# ---------- _pdf_locator_ratio / _docx_locator_ratio 互斥 ----------


def test_pdf_locator_no_elements_returns_null():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_page_valid_no_bbox_required():
    # table 类型不需要 bbox
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_paragraph_missing_bbox():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_paragraph_valid_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_page_zero_invalid():
    elements = [{"type": "table", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_invalid():
    elements = [{"type": "table", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_string_invalid():
    elements = [{"type": "table", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_missing_source_locator():
    elements = [{"type": "table"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_source_locator_none():
    elements = [{"type": "table", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_no_elements_returns_null():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_with_structural_key():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_page_rejected():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_rejected():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "section": 1}}
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_no_structural_key_rejected():
    elements = [{"type": "paragraph", "source_locator": {"foo": "bar"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_missing_source_locator():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- compute_automatic_metrics 行为深度 ----------


def test_compute_metrics_signature_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_metrics_signature_returns_dict_annotation():
    sig = inspect.signature(compute_automatic_metrics)
    # from __future__ 让 return_annotation 是字符串
    assert sig.return_annotation == "dict[str, Any]"


def test_compute_metrics_no_varargs_varkw():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_compute_metrics_first_5_params_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    names = list(sig.parameters.keys())
    assert names == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]
    for n in names[:4]:
        assert sig.parameters[n].default is inspect.Parameter.empty


def test_compute_metrics_document_none_returns_13_null_metrics():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # 13 个 metrics + error_code + pipeline_success
    # null 字段：schema_valid/element_count_total/element_count_by_type/pdf_locator_valid_ratio
    # /docx_locator_valid_ratio/image_resource_exists_ratio/chunk_reference_intact_ratio
    # /text_preservation_equal/text_char_multiset_precision/text_char_multiset_recall
    # /heading_boundary_compliance/silent_drop_count = 12 个 null
    null_keys = [
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
    ]
    for k in null_keys:
        assert out[k]["value"] is None, k
        assert out[k]["reason"] == "pipeline_failed", k


def test_compute_metrics_pipeline_success_false_when_document_none():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_false_when_error_present():
    err = {"code": "X"}
    out = compute_automatic_metrics({"elements": []}, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_true_when_document_and_no_error():
    out = compute_automatic_metrics({"elements": []}, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_error_code_present_when_error():
    err = {"code": "X"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "X"


def test_compute_metrics_error_code_none_when_no_error():
    out = compute_automatic_metrics({"elements": []}, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_pdf_yields_pdf_locator_value_docx_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_yields_docx_value_pdf_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_other_source_yields_both_not_applicable():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "html", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_returns_dict():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_keys_full_pipeline_failed():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert set(out.keys()) == {
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


def test_compute_metrics_element_count_total_zero_for_empty():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0


def test_compute_metrics_element_count_by_type_empty_dict_for_empty():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {}


def test_compute_metrics_element_count_by_type_groups():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


def test_compute_metrics_element_count_by_type_unknown_for_missing_type():
    doc = {"elements": [{"foo": "bar"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1}


# ---------- module source forbidden tokens ----------


@pytest.mark.parametrize(
    "token",
    [
        "import time",
        "import random",
        "import uuid",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import socket",
        "import email",
        "import html",
        "import http",
        "import urllib",
        "import sqlite3",
        "import csv",
        "import pickle",
        "import tempfile",
        "import shutil",
        "import glob",
        "import os",
        "import sys",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
        "import datetime",
        "import itertools",
        "import functools",
        "import collections.abc",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_math():
    src = inspect.getsource(m)
    assert "import math" in src


def test_module_source_has_from_collections_import_counter():
    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_compute_automatic_metrics_def():
    src = inspect.getsource(m)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_private_helpers_defs():
    src = inspect.getsource(m)
    for fn in (
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    ):
        assert f"def {fn}(" in src


def test_module_source_has_one_liners_defs():
    src = inspect.getsource(m)
    for fn in ("_null", "_ratio", "_bool_metric", "_int_metric"):
        assert f"def {fn}(" in src


def test_module_source_has_3_constants():
    src = inspect.getsource(m)
    assert "_TEXT_TYPES = " in src
    assert "_PDF_BBOX_REQUIRED_TYPES = " in src
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_has_image_excluded_comment():
    src = inspect.getsource(m)
    assert "image 不参与" in src or "image 不参与" in src


def test_module_source_has_counter_intersection_comment():
    src = inspect.getsource(m)
    assert "多集合交集" in src or "Counter" in src


def test_module_source_has_silent_drop_max_zero():
    src = inspect.getsource(m)
    # silent_drop_count = Σ max(0, ...) 但实现里用 if actual < exp
    assert "silent_drop_count" in src


def test_module_source_has_docstring_text_preservation_semantics():
    src = inspect.getsource(m)
    assert "text_preservation" in src
    assert "expected_sequence" in src
    assert "actual_sequence" in src


def test_module_source_has_v11_semantics_note():
    src = inspect.getsource(m)
    assert "v1.1" in src or "v1.0" in src


def test_module_source_has_pipeline_failed_reason():
    src = inspect.getsource(m)
    assert '"pipeline_failed"' in src


def test_module_source_has_no_elements_reason():
    src = inspect.getsource(m)
    assert '"no_elements"' in src


def test_module_source_has_no_chunks_reason():
    src = inspect.getsource(m)
    assert '"no_chunks"' in src


def test_module_source_has_no_image_elements_reason():
    src = inspect.getsource(m)
    assert '"no_image_elements"' in src


def test_module_source_has_no_heading_elements_reason():
    src = inspect.getsource(m)
    assert '"no_heading_elements"' in src


def test_module_source_has_no_expectations_reason():
    src = inspect.getsource(m)
    assert '"no_expectations"' in src


def test_module_source_has_empty_expected_and_actual_reason():
    src = inspect.getsource(m)
    assert '"empty_expected_and_actual"' in src


def test_module_source_has_empty_actual_reason():
    src = inspect.getsource(m)
    assert '"empty_actual"' in src


def test_module_source_has_empty_expected_reason():
    src = inspect.getsource(m)
    assert '"empty_expected"' in src


def test_module_source_has_not_pdf_document_reason():
    src = inspect.getsource(m)
    assert '"not_pdf_document"' in src


def test_module_source_has_not_docx_document_reason():
    src = inspect.getsource(m)
    assert '"not_docx_document"' in src


# ---------- signatures 精确 ----------


def test_compute_automatic_metrics_is_function():
    assert isinstance(compute_automatic_metrics, FunctionType)


def test_pdf_locator_ratio_is_function():
    assert isinstance(_pdf_locator_ratio, FunctionType)


def test_docx_locator_ratio_is_function():
    assert isinstance(_docx_locator_ratio, FunctionType)


def test_is_valid_bbox_is_function():
    assert isinstance(_is_valid_bbox, FunctionType)


def test_image_resource_ratio_is_function():
    assert isinstance(_image_resource_ratio, FunctionType)


def test_chunk_reference_ratio_is_function():
    assert isinstance(_chunk_reference_ratio, FunctionType)


def test_strip_unicode_whitespace_is_function():
    assert isinstance(_strip_unicode_whitespace, FunctionType)


def test_text_preservation_is_function():
    assert isinstance(_text_preservation, FunctionType)


def test_heading_boundary_ratio_is_function():
    assert isinstance(_heading_boundary_ratio, FunctionType)


def test_silent_drop_count_is_function():
    assert isinstance(_silent_drop_count, FunctionType)


def test_null_is_function():
    assert isinstance(_null, FunctionType)


def test_ratio_is_function():
    assert isinstance(_ratio, FunctionType)


def test_bool_metric_is_function():
    assert isinstance(_bool_metric, FunctionType)


def test_int_metric_is_function():
    assert isinstance(_int_metric, FunctionType)


def test_pdf_locator_ratio_namespace_is_metrics():
    assert _pdf_locator_ratio.__module__ == "evaluation.metrics"


def test_docx_locator_ratio_namespace_is_metrics():
    assert _docx_locator_ratio.__module__ == "evaluation.metrics"


def test_is_valid_bbox_namespace_is_metrics():
    assert _is_valid_bbox.__module__ == "evaluation.metrics"


def test_image_resource_ratio_namespace_is_metrics():
    assert _image_resource_ratio.__module__ == "evaluation.metrics"


def test_chunk_reference_ratio_namespace_is_metrics():
    assert _chunk_reference_ratio.__module__ == "evaluation.metrics"


def test_text_preservation_namespace_is_metrics():
    assert _text_preservation.__module__ == "evaluation.metrics"


def test_silent_drop_count_namespace_is_metrics():
    assert _silent_drop_count.__module__ == "evaluation.metrics"


# ---------- 端到端集成 ----------


def test_e2e_full_docx_pipeline_yields_all_metrics():
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "hello",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "hello", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_e2e_full_pdf_pipeline_with_bbox_yields_pdf_locator_one():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hi",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        ],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_silent_drop_with_expectations():
    doc = {
        "elements": [{"type": "paragraph"}, {"type": "paragraph"}],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 3


def test_e2e_image_resource_with_real_file(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    doc = {
        "elements": [{"type": "image", "resource_path": str(img)}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


# ---------- 模块整体合理性 ----------


def test_module_all_has_only_compute_automatic_metrics():
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_compute_automatic_metrics_is_only_public_callable():
    public = [n for n in dir(m) if not n.startswith("_") and callable(getattr(m, n))]
    # 排除 import 进来的 Counter / Path / math / Any / Counter 等
    own = [
        n for n in public
        if getattr(m, n).__module__ == "evaluation.metrics"
    ]
    assert own == ["compute_automatic_metrics"]


def test_module_has_no_class_definition():
    src = inspect.getsource(m)
    assert "class " not in src


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src
    assert 'if __name__ == "__main__":' not in src


def test_module_has_13_private_functions():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    # _null, _ratio, _bool_metric, _int_metric,
    # _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox,
    # _image_resource_ratio, _chunk_reference_ratio,
    # _strip_unicode_whitespace, _text_preservation,
    # _heading_boundary_ratio, _silent_drop_count = 13
    assert len(private_fns) == 13


def test_module_has_3_private_constants():
    private_consts = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and not callable(getattr(m, n))
    ]
    assert set(private_consts) == {
        "_TEXT_TYPES",
        "_PDF_BBOX_REQUIRED_TYPES",
        "_NOT_EVALUATED",
    }


def test_module_namespace_is_evaluation_metrics():
    assert m.__name__ == "evaluation.metrics"
