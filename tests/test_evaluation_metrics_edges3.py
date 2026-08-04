"""evaluation/metrics.py 边角测试 - 第三轮（Round 97）。

补强已有 ? + 190 测试未覆盖的：
- _pdf_locator_ratio 算法路径：page=0/-1/None、bbox=None、bbox 不合法、
  非 PDF 文本类型不要 bbox
- _docx_locator_ratio 算法路径：loc 含 page/bbox 被拒、loc 含各种结构键、
  空 loc 被拒
- _is_valid_bbox 算法路径：bool 值被拒、NaN/Inf 被拒、各种长度、各种类型
- _image_resource_ratio 算法路径：no images、empty rp、不存在 rp、
  rp 含子目录、image_base_dir 拼接
- _chunk_reference_ratio 算法路径：no chunks、empty source_element_ids、
  孤儿引用、混合
- _strip_unicode_whitespace：各种 Unicode 空白类型
- _text_preservation：full match / partial / both empty / empty expected only /
  empty actual only
- _heading_boundary_ratio：no headings、所有 heading 命中、部分命中、零命中
- _silent_drop_count：no expectations / empty expectations / drop=0 / 多类型 drop
- compute_automatic_metrics pipeline_success=false 全部 null 路径
- compute_automatic_metrics schema_valid exception path

不修改任何源码。
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import pytest

from evaluation.metrics import (
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
# _pdf_locator_ratio 第三轮
# =========================================================================


def test_pdf_locator_ratio_empty_elements_returns_no_elements():
    assert _pdf_locator_ratio([]) == {"value": None, "reason": "no_elements"}


def test_pdf_locator_ratio_page_zero_treated_invalid():
    """page=0 → < 1 → 不计入 valid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 0}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_negative_treated_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": -1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_none_treated_invalid():
    elements = [{"type": "paragraph", "source_locator": {"page": None}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_missing_treated_invalid():
    elements = [{"type": "paragraph", "source_locator": {}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_text_type_requires_bbox():
    """paragraph 类型需要 page + bbox 都合法。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]  # 缺 bbox
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_text_type_with_valid_bbox():
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]},
    }]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_table_does_not_require_bbox():
    """table 类型不在 _PDF_BBOX_REQUIRED_TYPES → 仅需 page。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_image_does_not_require_bbox():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
        {"type": "paragraph", "source_locator": {"page": 0}},  # invalid (page<1)
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0 / 3


# =========================================================================
# _docx_locator_ratio 第三轮
# =========================================================================


def test_docx_locator_ratio_empty_elements_returns_no_elements():
    assert _docx_locator_ratio([]) == {"value": None, "reason": "no_elements"}


def test_docx_locator_ratio_with_page_rejected():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected():
    elements = [{
        "type": "paragraph",
        "source_locator": {"bbox": [0, 0, 10, 10], "paragraph_index": 0},
    }]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_with_paragraph_index_accepted():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_section_accepted():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_table_index_accepted():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_run_index_accepted():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_row_col_accepted():
    elements = [{"type": "table", "source_locator": {"row_index": 0, "col_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id_accepted():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_empty_locator_rejected():
    elements = [{"type": "paragraph", "source_locator": {}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_with_no_locator_key_rejected():
    elements = [{"type": "paragraph"}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_mixed():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (page)
        {"type": "paragraph", "source_locator": {}},  # invalid (no key)
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0 / 3


# =========================================================================
# _is_valid_bbox 第三轮
# =========================================================================


def test_is_valid_bbox_none_rejected():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_short_list_rejected():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_list_rejected():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_four_ints_accepted():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats_accepted():
    assert _is_valid_bbox([0.5, 1.5, 2.5, 3.5]) is True


def test_is_valid_bbox_mixed_int_float_accepted():
    assert _is_valid_bbox([0, 1.5, 100, 100.5]) is True


def test_is_valid_bbox_bool_int_zero_rejected():
    """bool True 即使值=1 也被拒。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox(["0", "0", "100", "100"]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_is_valid_bbox_negative_inf_rejected():
    assert _is_valid_bbox([float("-inf"), 0, 0, 0]) is False


def test_is_valid_bbox_tuple_rejected():
    """bbox 必须是 list，不是 tuple。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_zero_size_accepted():
    """零大小 bbox 也算 valid（仅类型/数值校验，不校验大小）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_accepted():
    assert _is_valid_bbox([-10.5, -20.5, 10.5, 20.5]) is True


# =========================================================================
# _image_resource_ratio 第三轮
# =========================================================================


def test_image_resource_ratio_no_images_returns_no_image_elements():
    elements = [{"type": "paragraph", "content": "x"}]
    r = _image_resource_ratio(elements, None)
    assert r == {"value": None, "reason": "no_image_elements"}


def test_image_resource_ratio_empty_rp_skipped(tmp_path: Path):
    elements = [{"type": "image", "resource_path": ""}]
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 0.0


def test_image_resource_ratio_missing_rp_counts_as_invalid(tmp_path: Path):
    elements = [{"type": "image", "resource_path": "no_such.png"}]
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 0.0


def test_image_resource_ratio_existing_rp(tmp_path: Path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_ratio_zero_byte_file_skipped(tmp_path: Path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_with_image_base_dir_fallback(tmp_path: Path):
    """resource_path 仅文件名 + image_base_dir 给定 → 拼接尝试。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]  # 仅文件名
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path: Path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},  # valid
        {"type": "image", "resource_path": "missing.png"},  # invalid
    ]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.5


# =========================================================================
# _chunk_reference_ratio 第三轮
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_no_chunks():
    elements = [{"element_id": "e1"}]
    r = _chunk_reference_ratio(elements, [])
    assert r == {"value": None, "reason": "no_chunks"}


def test_chunk_reference_ratio_empty_ids_skipped():
    """chunk 的 source_element_ids=[] → 不计入 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_orphan_ids_invalid():
    """chunk 引用不存在的 element_id → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e99"]}]  # e99 不存在
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_partial_valid():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["e99"]},  # invalid
    ]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_chunk_reference_ratio_null_ids_treated_empty():
    """source_element_ids=None → 视为 []。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 第三轮
# =========================================================================


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ascii_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_bom_ufeff_not_treated_as_whitespace():
    """U+FEFF (BOM) 在 Python str.isspace() 中返回 False → 不被删除。"""
    assert _strip_unicode_whitespace("a﻿b") == "a﻿b"


def test_strip_unicode_whitespace_only_whitespace():
    assert _strip_unicode_whitespace("   \t\n 　") == ""


def test_strip_unicode_whitespace_preserves_non_whitespace_unicode():
    assert _strip_unicode_whitespace("你好 world") == "你好world"


def test_strip_unicode_whitespace_preserves_emoji():
    assert _strip_unicode_whitespace("😀😁😂") == "😀😁😂"


# =========================================================================
# _text_preservation 第三轮
# =========================================================================


def _text_metrics(elements, chunks):
    return _text_preservation(elements, chunks)


def test_text_preservation_full_match():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is True
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 1.0


def test_text_preservation_partial_match():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hell"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is False
    # common = 4, |actual| = 4, |expected| = 5
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 0.8


def test_text_preservation_both_empty():
    elements = [{"type": "image", "content": None}]  # image 不算
    chunks = [{"text": ""}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is True
    assert m["precision"] == {"value": None, "reason": "empty_expected_and_actual"}
    assert m["recall"] == {"value": None, "reason": "empty_expected_and_actual"}


def test_text_preservation_empty_expected_only():
    """expected 空，actual 非空 → precision null(empty_expected), recall null(empty_expected).

    等等：empty_expected_and_actual 仅当两者都空。
    expected=空, actual="a" → common = 0, |actual| = 1, |expected| = 0
    → precision = 0/1 = 0.0；recall = empty_expected (None).
    """
    elements = [{"type": "image", "content": None}]  # 无文本 element
    chunks = [{"text": "a"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is False
    assert m["precision"]["value"] == 0.0  # 0/1
    assert m["recall"] == {"value": None, "reason": "empty_expected"}


def test_text_preservation_empty_actual_only():
    """expected="a", actual="" → precision null(empty_actual), recall = 0/1 = 0.0."""
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{"text": ""}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is False
    assert m["precision"] == {"value": None, "reason": "empty_actual"}
    assert m["recall"]["value"] == 0.0


def test_text_preservation_order_matters_for_equal():
    """字符相同但顺序不同 → equal=False 但 precision/recall 仍可能为 1.0（multiset 比较）。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is False
    # multiset 相同 → precision/recall = 1.0
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 1.0


def test_text_preservation_repeats_preserved_in_multiset():
    """重复字符 multiset 比较。"""
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is False
    # common = min(3, 2) = 2; |actual| = 2; |expected| = 3
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 2.0 / 3


def test_text_preservation_multiple_elements_concat():
    """多 element 拼接后比对。"""
    elements = [
        {"type": "paragraph", "content": "hello"},
        {"type": "paragraph", "content": "world"},
    ]
    chunks = [{"text": "helloworld"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is True


def test_text_preservation_image_excluded():
    elements = [
        {"type": "paragraph", "content": "a"},
        {"type": "image", "content": "ignored_image_text"},
    ]
    chunks = [{"text": "a"}]
    m = _text_metrics(elements, chunks)
    assert m["equal"]["value"] is True


def test_text_preservation_whitespace_only_treated_as_empty():
    """expected 全是空白 → strip 后为空。"""
    elements = [{"type": "paragraph", "content": "   \n\t  "}]
    chunks = [{"text": ""}]
    m = _text_metrics(elements, chunks)
    # 两者都空 → empty_expected_and_actual
    assert m["equal"]["value"] is True
    assert m["precision"] == {"value": None, "reason": "empty_expected_and_actual"}


# =========================================================================
# _heading_boundary_ratio 第三轮
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r == {"value": None, "reason": "no_heading_elements"}


def test_heading_boundary_ratio_no_chunks_returns_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r["value"] == 0.0


def test_heading_boundary_ratio_all_matched():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1", "other"]},
        {"source_element_ids": ["h2"]},
    ]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_ratio_partial_matched():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1", "other"]}]  # 只匹配 h1
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_heading_boundary_ratio_zero_matched():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]  # h1 不在首
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_ratio_heading_not_first_in_chunk():
    """heading 是 chunk 的第二个 source_element_id → 不算匹配。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


# =========================================================================
# _silent_drop_count 第三轮
# =========================================================================


def test_silent_drop_count_no_expectations_returns_null():
    r = _silent_drop_count({"paragraph": 5}, None)
    assert r == {"value": None, "reason": "no_expectations"}


def test_silent_drop_count_empty_expectations_returns_null():
    r = _silent_drop_count({"paragraph": 5}, {})
    assert r == {"value": None, "reason": "no_expectations"}


def test_silent_drop_count_no_element_count_by_type_returns_null():
    r = _silent_drop_count({"paragraph": 5}, {"other_field": "x"})
    assert r == {"value": None, "reason": "no_expectations_element_count"}


def test_silent_drop_count_empty_element_count_by_type_returns_null():
    r = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert r == {"value": None, "reason": "no_expectations_element_count"}


def test_silent_drop_count_no_drop_when_actual_ge_expected():
    r = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert r["value"] == 0


def test_silent_drop_count_drop_when_actual_lt_expected():
    r = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert r["value"] == 2


def test_silent_drop_count_missing_type_in_actual_counts_as_drop():
    """expected 含某类型但 actual 中无 → 视为 0 → drop=expected. """
    r = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert r["value"] == 5


def test_silent_drop_count_multi_type_sum():
    by_type = {"paragraph": 3, "heading": 1}  # actual
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2, "table": 1}}
    r = _silent_drop_count(by_type, exp)
    # paragraph: 5-3=2; heading: 2-1=1; table: 1-0=1 → total=4
    assert r["value"] == 4


def test_silent_drop_count_actual_more_than_expected_no_negative():
    """actual > expected → max(0, ...) = 0. """
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, exp)
    assert r["value"] == 0


# =========================================================================
# compute_automatic_metrics 失败路径
# =========================================================================


def test_compute_metrics_pipeline_failed_all_metrics_null():
    metrics = compute_automatic_metrics(
        document=None,
        error={"code": "file_not_found", "message": "missing"},
        source_type="docx",
        expectations=None,
    )
    # pipeline_success = False
    assert metrics["pipeline_success"]["value"] is False
    # 所有依赖 document 的指标都 null
    for name in (
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
        assert metrics[name]["value"] is None
        assert metrics[name]["reason"] == "pipeline_failed"


def test_compute_metrics_pipeline_failed_error_code_recorded():
    metrics = compute_automatic_metrics(
        document=None,
        error={"code": "my_error", "message": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert metrics["error_code"]["value"] == "my_error"


def test_compute_metrics_pipeline_failed_schema_valid_null():
    metrics = compute_automatic_metrics(
        document=None,
        error={"code": "x", "message": "y"},
        source_type="docx",
        expectations=None,
    )
    assert metrics["schema_valid"] == {"value": None, "reason": "pipeline_failed"}


def test_compute_metrics_success_no_error_pipeline_success_true():
    """成功路径：document 给定 + error=None。"""
    document = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1",
                       "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(
        document=document,
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert metrics["pipeline_success"]["value"] is True
    assert metrics["error_code"]["value"] is None


def test_compute_metrics_success_pdf_locator_not_pdf_when_docx():
    """source_type=docx → pdf_locator_valid_ratio null + reason. """
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["pdf_locator_valid_ratio"] == {"value": None, "reason": "not_pdf_document"}


def test_compute_metrics_success_docx_locator_not_docx_when_pdf():
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert metrics["docx_locator_valid_ratio"] == {"value": None, "reason": "not_docx_document"}


def test_compute_metrics_pdf_locator_no_elements_returns_no_elements():
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert metrics["pdf_locator_valid_ratio"] == {"value": None, "reason": "no_elements"}


def test_compute_metrics_docx_locator_no_elements_returns_no_elements():
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["docx_locator_valid_ratio"] == {"value": None, "reason": "no_elements"}


def test_compute_metrics_image_resource_no_images_returns_no_image_elements():
    document = {"elements": [{"type": "paragraph"}], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["image_resource_exists_ratio"] == {
        "value": None, "reason": "no_image_elements"
    }


def test_compute_metrics_chunk_reference_no_chunks_returns_no_chunks():
    document = {"elements": [{"element_id": "e1"}], "chunks": []}
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["chunk_reference_intact_ratio"] == {
        "value": None, "reason": "no_chunks"
    }


def test_compute_metrics_heading_boundary_no_headings():
    document = {
        "elements": [{"type": "paragraph", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["heading_boundary_compliance"] == {
        "value": None, "reason": "no_heading_elements"
    }


def test_compute_metrics_silent_drop_no_expectations():
    document = {
        "elements": [{"type": "paragraph", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert metrics["silent_drop_count"] == {"value": None, "reason": "no_expectations"}


def test_compute_metrics_returns_dict_with_all_keys():
    """返回 metrics dict 含所有 13 项指标 + error_code。"""
    document = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x",
                       "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx",
        expectations={"element_count_by_type": {"paragraph": 1}},
    )
    expected_keys = {
        "pipeline_success",
        "schema_valid",
        "error_code",
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
    assert set(metrics.keys()) == expected_keys


def test_compute_metrics_each_value_is_dict_with_value_and_reason():
    """每个 metric 都是 {value, reason} 结构。"""
    document = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x",
                       "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    for name, m in metrics.items():
        assert isinstance(m, dict), f"{name} is not a dict"
        assert "value" in m, f"{name} missing value"
        assert "reason" in m, f"{name} missing reason"


# =========================================================================
# 内部辅助：_null / _ratio / _bool_metric / _int_metric
# =========================================================================


def test_null_with_long_reason_string():
    r = _null("a" * 200)
    assert r["reason"] == "a" * 200


def test_ratio_with_inf_value():
    """inf 不是合法 ratio 但函数不校验。"""
    r = _ratio(float("inf"))
    assert r["value"] == float("inf")


def test_ratio_with_nan_value():
    r = _ratio(float("nan"))
    assert math.isnan(r["value"])


def test_bool_metric_with_int_zero():
    assert _bool_metric(0)["value"] is False


def test_bool_metric_with_int_one():
    assert _bool_metric(1)["value"] is True


def test_bool_metric_with_empty_string():
    assert _bool_metric("")["value"] is False


def test_bool_metric_with_non_empty_string():
    assert _bool_metric("x")["value"] is True


def test_bool_metric_with_empty_list():
    assert _bool_metric([])["value"] is False


def test_bool_metric_with_non_empty_list():
    assert _bool_metric([1])["value"] is True


def test_int_metric_truncates_float():
    """int(3.99) = 3 (truncate)。"""
    assert _int_metric(3.99)["value"] == 3


def test_int_metric_negative_float():
    assert _int_metric(-2.7)["value"] == -2
