"""evaluation/metrics.py 第五十二轮 edges 测试（Round 484）。

补强 edges49 未触及的角度：
- 构造子第二十四批（_null empty reason / _ratio negative / _ratio very small / _bool_metric 接受 None / _int_metric 接受 str-like / 重复调用一致）
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十四批（无重复 / 排序稳定 / hashable / iterable）
- _strip_unicode_whitespace 第二十四批（vertical tab / form feed / 信息分隔符 / 各种 unicode 空格）
- compute_automatic_metrics 第二十四批（更多混合场景 / source_type 'unknown' / expectations 类型 / image_base_dir 默认）
- _pdf_locator_ratio 第二十四批（None locator / empty dict locator / 无 type / mixed types）
- _docx_locator_ratio 第二十四批（locator None / 完全无 structural key / table_index valid / section valid）
- _is_valid_bbox 第二十四批（None / str / dict / set / generator / bool 单独）
- _image_resource_ratio 第二十四批（resource_path None / 空字符串 / 绝对路径 / 相对路径 / 多 image）
- _chunk_reference_ratio 第二十四批（chunks 空 / elements 空 / ids 重复 / 多 ids 部分无效）
- _text_preservation 第二十四批（相同字符不同顺序 / 长 stream / 全 image elements / chunks 文本不同）
- _heading_boundary_ratio 第二十四批（无 chunks / heading 无 element_id / chunk 缺 ids / 多 chunk 同 first id）
- _silent_drop_count 第二十四批（expectations empty dict / element_count_by_type empty / multiple types / negative drop）
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.metrics import (
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
from evaluation import metrics as mmod


# ---------- 构造子第二十四批 ----------


def test_null_with_empty_string_reason_batch24():
    """_null 接受空字符串 reason。"""
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_returns_fresh_dict_each_call_batch24():
    """每次调用返回新 dict。"""
    a = _null("x")
    b = _null("x")
    assert a == b
    assert a is not b


def test_ratio_negative_value_batch24():
    """_ratio 接受负数（不强制 [0,1]）。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_very_small_value_batch24():
    """极小正数。"""
    out = _ratio(1e-10)
    assert out["value"] == 1e-10


def test_ratio_large_value_batch24():
    """大于 1 的值（不强制 [0,1]）。"""
    out = _ratio(2.5)
    assert out["value"] == 2.5


def test_bool_metric_accepts_none_batch24():
    """_bool_metric(None) → False。"""
    out = _bool_metric(None)
    assert out["value"] is False


def test_bool_metric_accepts_empty_string_batch24():
    out = _bool_metric("")
    assert out["value"] is False


def test_bool_metric_accepts_nonempty_string_batch24():
    out = _bool_metric("x")
    assert out["value"] is True


def test_int_metric_accepts_negative_batch24():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_accepts_zero_batch24():
    out = _int_metric(0)
    assert out["value"] == 0


def test_int_metric_returns_fresh_dict_batch24():
    a = _int_metric(1)
    b = _int_metric(1)
    assert a == b
    assert a is not b


def test_constructors_consistent_value_field_batch24():
    """所有构造子返回 dict 含 'value' key。"""
    assert "value" in _null("x")
    assert "value" in _ratio(0.5)
    assert "value" in _bool_metric(True)
    assert "value" in _int_metric(1)


def test_constructors_consistent_reason_field_batch24():
    """所有构造子返回 dict 含 'reason' key。"""
    assert "reason" in _null("x")
    assert "reason" in _ratio(0.5)
    assert "reason" in _bool_metric(True)
    assert "reason" in _int_metric(1)


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十四批 ----------


def test_text_types_no_duplicates_batch24():
    assert len(_TEXT_TYPES) == len(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_no_duplicates_batch24():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == len(set(_PDF_BBOX_REQUIRED_TYPES))


def test_text_types_is_tuple_batch24():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_batch24():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_iterable_batch24():
    """可 iterate。"""
    for t in _TEXT_TYPES:
        assert isinstance(t, str)


def test_text_types_hashable_items_batch24():
    """tuple 内每个元素 hashable。"""
    for t in _TEXT_TYPES:
        hash(t)


def test_pdf_bbox_required_types_subset_of_text_types_batch24():
    """_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_text_types_excludes_image_batch24():
    assert "image" not in _TEXT_TYPES


def test_text_types_includes_paragraph_heading_list_item_batch24():
    assert "paragraph" in _TEXT_TYPES
    assert "heading" in _TEXT_TYPES
    assert "list_item" in _TEXT_TYPES


def test_pdf_bbox_required_types_excludes_table_header_footer_batch24():
    """table/header/footer 不在 PDF bbox 必填列表（这些类型无 bbox 也算 valid）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


# ---------- _strip_unicode_whitespace 第二十四批 ----------


def test_strip_unicode_whitespace_vertical_tab_batch24():
    """\\v (vertical tab) 是 isspace() True。"""
    assert _strip_unicode_whitespace("a\vb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch24():
    """\\f (form feed)。"""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch24():
    """\\r (carriage return)。"""
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_only_whitespace_returns_empty_batch24():
    assert _strip_unicode_whitespace("   \t\n\v\f\r") == ""


def test_strip_unicode_whitespace_no_whitespace_batch24():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_empty_string_batch24():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_preserves_digits_batch24():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_preserves_punctuation_batch24():
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_whitespace_preserves_unicode_letters_batch24():
    assert _strip_unicode_whitespace("中文 字") == "中文字"


def test_strip_unicode_whitespace_preserves_emoji_batch24():
    """emoji 是非空白字符，保留。"""
    assert _strip_unicode_whitespace("🚀 🎉") == "🚀🎉"


def test_strip_unicode_whitespace_nbsp_batch24():
    """NBSP (\\u00a0) 是 isspace() True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch24():
    """em space (\\u2003)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


# ---------- compute_automatic_metrics 第二十四批 ----------


def test_compute_metrics_source_type_unknown_excludes_both_locators_batch24():
    """source_type='unknown' → pdf/docx locator 都是 null。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "unknown", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_default_image_base_dir_batch24():
    """image_base_dir 默认 None。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # 没图 → no_image_elements
    assert m["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_metrics_error_only_no_document_batch24():
    """error 非 None + document=None → pipeline_success=False。"""
    err = {"code": "PARSE_FAIL", "message": "x"}
    m = compute_automatic_metrics(None, err, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "PARSE_FAIL"


def test_compute_metrics_error_code_none_when_no_error_batch24():
    """无 error 时 error_code.value=None。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_metrics_returns_dict_batch24():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(m, dict)


def test_compute_metrics_has_all_required_keys_batch24():
    """成功路径返回的 dict 含所有顶层指标 key。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    for k in (
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
    ):
        assert k in m, f"missing key: {k}"


def test_compute_metrics_element_count_zero_for_empty_batch24():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_pipeline_failed_returns_11_null_metrics_batch24():
    """document=None 时返回 11 个 null 指标。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    null_metrics_count = sum(1 for v in m.values() if v.get("reason") == "pipeline_failed")
    # 应当至少 11 个（schema_valid + element_count_total 等）
    assert null_metrics_count >= 11


# ---------- _pdf_locator_ratio 第二十四批 ----------


def test_pdf_locator_ratio_no_locator_key_batch24():
    """元素缺 source_locator → loc = {} → page not int → invalid。"""
    elements = [{"type": "image"}, {"type": "image"}]
    out = _pdf_locator_ratio(elements)
    # image type 不需要 bbox 但仍需 page≥1
    # loc = {} → page None → invalid
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch24():
    """source_locator=None → loc = None or {} = {}。"""
    elements = [{"type": "image", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_zero_invalid_batch24():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid_batch24():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_without_bbox_invalid_batch24():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_valid_bbox_valid_batch24():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_image_with_page_only_valid_batch24():
    """image 不需要 bbox，只需要 page。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_mixed_valid_invalid_batch24():
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {"type": "image", "source_locator": {"page": 0}},  # invalid
        {"type": "image", "source_locator": {}},  # invalid
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == pytest.approx(1 / 3)


# ---------- _docx_locator_ratio 第二十四批 ----------


def test_docx_locator_ratio_table_index_valid_batch24():
    elements = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_valid_batch24():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_valid_batch24():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_locator_none_batch24():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    # None or {} = {} → 无 structural key → invalid
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_locator_batch24():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_locator_key_batch24():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_rejects_page_batch24():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    # page 在 → invalid（即使 paragraph_index 也在）
    assert out["value"] == 0.0


def test_docx_locator_ratio_rejects_bbox_batch24():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_mixed_batch24():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "paragraph", "source_locator": {}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == pytest.approx(1 / 3)


# ---------- _is_valid_bbox 第二十四批 ----------


def test_is_valid_bbox_none_batch24():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_str_batch24():
    assert _is_valid_bbox("0,0,1,1") is False


def test_is_valid_bbox_dict_batch24():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_set_batch24():
    assert _is_valid_bbox({0, 1, 2, 3}) is False


def test_is_valid_bbox_tuple_batch24():
    """tuple 不是 list。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_three_items_batch24():
    assert _is_valid_bbox([0, 0, 1]) is False


def test_is_valid_bbox_five_items_batch24():
    assert _is_valid_bbox([0, 0, 1, 1, 1]) is False


def test_is_valid_bbox_bool_inside_batch24():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_all_int_batch24():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_all_float_batch24():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_nan_invalid_batch24():
    assert _is_valid_bbox([0, 0, float("nan"), 100]) is False


def test_is_valid_bbox_inf_invalid_batch24():
    assert _is_valid_bbox([0, 0, float("inf"), 100]) is False


# ---------- _image_resource_ratio 第二十四批 ----------


def test_image_resource_ratio_no_resource_path_batch24():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    # 无 resource_path → valid=0 → ratio=0
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch24():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_nonexistent_file_batch24(tmp_path):
    elements = [{"type": "image", "resource_path": "nonexistent.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_batch24(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_size_file_batch24(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch24(tmp_path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": str(img1)},  # valid
        {"type": "image", "resource_path": "nope.png"},  # invalid
        {"type": "image"},  # no resource_path → invalid
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == pytest.approx(1 / 3)


def test_image_resource_ratio_no_image_elements_batch24():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_base_dir_with_filename_batch24(tmp_path):
    """resource_path 是裸文件名 → image_base_dir 帮助找到。"""
    img = tmp_path / "only_name.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": "only_name.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 用 image_base_dir/Path(rp).name 找
    assert out["value"] == 1.0


# ---------- _chunk_reference_ratio 第二十四批 ----------


def test_chunk_reference_ratio_no_chunks_batch24():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_chunks_list_batch24():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_elements_batch24():
    """elements 空 → chunks 的 ids 都查不到 → 0 valid。"""
    out = _chunk_reference_ratio([], [{"source_element_ids": ["e1"]}])
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_ids_key_batch24():
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 缺 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    # ids = [] or [] = [] → empty → 不算 valid → 0/1
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_empty_ids_batch24():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch24():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_valid_batch24():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["nonexistent"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_multi_ids_all_valid_batch24():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}, {"element_id": "e3"}]
    chunks = [{"source_element_ids": ["e1", "e2", "e3"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multi_ids_partial_invalid_batch24():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]  # missing 不在 elements
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _text_preservation 第二十四批 ----------


def test_text_preservation_empty_both_returns_null_metrics_batch24():
    out = _text_preservation([], [])
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"
    assert out["equal"]["value"] is True


def test_text_preservation_identical_content_batch24():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_actual_missing_content_batch24():
    """actual 空 + expected 非空 → precision null / recall 0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    # actual = "" → empty_actual → precision null
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_expected_missing_content_batch24():
    """expected 空 + actual 非空 → recall null / precision 0。"""
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["recall"]["reason"] == "empty_expected"
    assert out["precision"]["value"] == 0.0


def test_text_preservation_image_excluded_batch24():
    """image 元素的 content 不计入 expected。"""
    elements = [
        {"type": "paragraph", "content": "ab"},
        {"type": "image", "content": "should_be_ignored"},
    ]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_returns_three_keys_batch24():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_duplicate_chars_batch24():
    """重复字符保留。"""
    elements = [{"type": "paragraph", "content": "aaabbb"}]
    chunks = [{"text": "aaabbb"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


# ---------- _heading_boundary_ratio 第二十四批 ----------


def test_heading_boundary_ratio_no_headings_batch24():
    out = _heading_boundary_ratio([], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_batch24():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_no_chunk_with_first_id_batch24():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_match_batch24():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match_batch24():
    elements = [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}]
    chunks = [{"source_element_ids": ["h1"]}]  # 只有 h1 被匹配
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_heading_no_element_id_batch24():
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h.get('element_id') = None → 不在 chunk_first_ids → 0 match
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunks_missing_first_id_batch24():
    """chunks 都没 source_element_ids。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}, {"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _silent_drop_count 第二十四批 ----------


def test_silent_drop_count_no_expectations_batch24():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch24():
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_key_batch24():
    out = _silent_drop_count({}, {"required_markers": ["x"]})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_batch24():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drop_batch24():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_full_drop_batch24():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_count_partial_drop_batch24():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 2


def test_silent_drop_count_actual_more_than_expected_batch24():
    """actual > expected → 不计负 drop。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_multiple_types_batch24():
    by_type = {"paragraph": 1, "heading": 0, "list_item": 2}
    exp = {"element_count_by_type": {"paragraph": 3, "heading": 2, "list_item": 2}}
    out = _silent_drop_count(by_type, exp)
    # paragraph: 3-1=2; heading: 2-0=2; list_item: 2-2=0
    assert out["value"] == 4


def test_silent_drop_count_unknown_type_in_expectations_batch24():
    """expectations 含 by_type 没有的 type → 按 actual=0 算 drop。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5, "table": 3}})
    # paragraph: 0 drop; table: 3 drop
    assert out["value"] == 3


# ---------- module source forbidden tokens 第三十九批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch24(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch24():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch24():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch24():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch24():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch24():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_asyncio_import_batch24():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch24():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch24():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch24():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch24():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch24():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_pandas_import_batch24():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch24():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


def test_module_source_no_csv_import_batch24():
    src = inspect.getsource(mmod)
    assert "import csv" not in src


def test_module_source_no_os_import_batch24():
    src = inspect.getsource(mmod)
    assert "import os" not in src


# ---------- module source 字符串精确补强第三十五批 ----------


def test_module_source_has_future_annotations_batch24():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import_batch24():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_counter_import_batch24():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import_batch24():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch24():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch24():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES =" in src


def test_module_source_has_pdf_bbox_required_types_constant_batch24():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES =" in src


def test_module_source_has_null_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_has_ratio_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_has_bool_metric_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_has_int_metric_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_has_compute_automatic_metrics_function_batch24():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_strip_unicode_whitespace_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_has_text_preservation_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_has_is_valid_bbox_function_batch24():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


# ---------- signatures 第三十五批 ----------


def test_signature_null_one_param_batch24():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "reason"


def test_signature_ratio_one_param_batch24():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_bool_metric_one_param_batch24():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_int_metric_one_param_batch24():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_compute_metrics_five_params_batch24():
    sig = inspect.signature(compute_automatic_metrics)
    names = list(sig.parameters.keys())
    assert names == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_image_base_dir_default_none_batch24():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_ratio_one_param_batch24():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "elements"


def test_signature_is_valid_bbox_one_param_batch24():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "bbox"


# ---------- module 合理性第三十五批 ----------


def test_module_all_contains_only_compute_metrics_batch24():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_does_not_import_evaluation_runner_batch24():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch24():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_manifest_batch24():
    src = inspect.getsource(mmod)
    assert "from evaluation.manifest" not in src


def test_module_does_not_import_evaluation_report_batch24():
    src = inspect.getsource(mmod)
    assert "from evaluation.report" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch24():
    src = inspect.getsource(mmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_app_pipeline_batch24():
    src = inspect.getsource(mmod)
    assert "from app.pipeline" not in src


def test_module_does_not_import_app_parsers_batch24():
    src = inspect.getsource(mmod)
    assert "from app.parsers" not in src


def test_module_does_not_import_app_chunkers_top_level_batch24():
    """app.chunkers 不在顶层 import（避免循环）。"""
    src = inspect.getsource(mmod)
    lines = src.splitlines()
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from app.chunkers") and line[0] != " ":
            pytest.fail("app.chunkers 不应在顶层 import")


def test_module_constants_not_in_all_batch24():
    """构造子 / 私有常量不应在 __all__。"""
    assert "_null" not in mmod.__all__
    assert "_ratio" not in mmod.__all__
    assert "_TEXT_TYPES" not in mmod.__all__


def test_module_no_main_block_batch24():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src


def test_module_compute_metrics_is_public_batch24():
    assert not compute_automatic_metrics.__name__.startswith("_")


def test_module_has_module_docstring_batch24():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


# ---------- 端到端集成第三十五批 ----------


def test_e2e_compute_metrics_empty_document_batch24():
    """空 document → 多数 ratio 都是 null/0/1。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 0


def test_e2e_compute_metrics_full_document_batch24():
    """完整 document 计算。"""
    doc = {
        "elements": [
            {"element_id": "h1", "type": "heading", "content": "Title"},
            {"element_id": "p1", "type": "paragraph", "content": "Body"},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 2
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_pipeline_failed_batch24():
    """document=None + error → pipeline_success=False。"""
    m = compute_automatic_metrics(None, {"code": "E", "message": "x"}, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "E"
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_with_expectations_batch24():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = compute_automatic_metrics(doc, None, "pdf", exp)
    # 期望 5 实际 1 → drop=4
    assert m["silent_drop_count"]["value"] == 4


def test_e2e_compute_metrics_no_expectations_batch24():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_e2e_compute_metrics_docx_batch24():
    """docx source_type。"""
    doc = {
        "elements": [
            {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_compute_metrics_element_count_by_type_batch24():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}
