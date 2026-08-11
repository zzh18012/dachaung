"""evaluation/metrics.py 第五十五轮 edges 测试（Round 505）。

补强 edges52 未触及的角度（第二十七批）：
- _strip_unicode_whitespace 第二十七批：ASCII 空白 / Unicode 空白 / NBSP / em space / tab/newline / 混合 / empty / 无空白 / 不可见字符
- _is_valid_bbox 第二十七批：list 4 ints / list 4 floats / bool 元素 / str 元素 / nan / inf / len 3 / len 5 / None / tuple
- _text_preservation 第二十七批：image excluded / content None / chunk text None / 多余空白 / NBSP / emoji / 全空 expected / 全空 actual
- _silent_drop_count 第二十七批：no expectations / expectations 空 dict / 缺 element_count_by_type / element_count_by_type 空 / actual > expected / actual == expected / 多 type
- _heading_boundary_ratio 第二十七批：no headings / no chunks / chunks empty source_ids / multiple matched / heading 不在 chunks
- _chunk_reference_ratio 第二十七批：no chunks / chunks no source_ids / partial / 全 missing / 单 source_id missing
- _image_resource_ratio 第二十七批：no images / no resource_path / 文件不存在 / 文件存在 / image_base_dir 拼接 / OSError
- _pdf_locator_ratio 第二十七批：no elements / page=0 / page=1 / text 类型缺 bbox / 非 text 类型无 bbox / page float
- _docx_locator_ratio 第二十七批：no elements / paragraph_index / page 拒 / 无结构键拒
- module source forbidden tokens 第四十三批
- module source 字符串精确补强第三十九批
- signatures 第三十九批
- module 合理性第三十九批
- 端到端集成第三十九批
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
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


# ---------- _strip_unicode_whitespace 第二十七批 ----------


def test_strip_unicode_whitespace_ascii_space_batch27():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_tab_batch27():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline_batch27():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return_batch27():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_form_feed_batch27():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab_batch27():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_nbsp_batch27():
    """NBSP (U+00A0) 应被删除。"""
    assert _strip_unicode_whitespace("a\xa0b") == "ab"


def test_strip_unicode_whitespace_em_space_batch27():
    """em space (U+2003) 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_batch27():
    """en space (U+2002) 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch27():
    """全角空格 (U+3000) 应被删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch27():
    """U+2028 line separator 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch27():
    """U+2029 paragraph separator 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_empty_string_batch27():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_only_whitespace_batch27():
    assert _strip_unicode_whitespace("   \t\n\xa0") == ""


def test_strip_unicode_whitespace_no_whitespace_batch27():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_mixed_batch27():
    assert _strip_unicode_whitespace("a b\tc\nd\xa0e") == "abcde"


def test_strip_unicode_whitespace_preserves_non_whitespace_batch27():
    """非空白字符（含标点、emoji）应原样保留。"""
    assert _strip_unicode_whitespace("a, b. c! d?") == "a,b.c!d?"


def test_strip_unicode_whitespace_emoji_preserved_batch27():
    """emoji 不被删除。"""
    assert _strip_unicode_whitespace("a 😀 b") == "a😀b"


def test_strip_unicode_whitespace_preserves_order_batch27():
    """不重排序，仅删除空白。"""
    assert _strip_unicode_whitespace("xyz abc") == "xyzabc"


# ---------- _is_valid_bbox 第二十七批 ----------


def test_is_valid_bbox_four_ints_batch27():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_four_floats_batch27():
    assert _is_valid_bbox([1.0, 2.5, 3.7, 4.1]) is True


def test_is_valid_bbox_mixed_int_float_batch27():
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_negative_values_batch27():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_zero_values_batch27():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_with_true_batch27():
    """True 是 bool → 无效（实现显式排除 bool）。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_with_false_batch27():
    assert _is_valid_bbox([1, False, 3, 4]) is False


def test_is_valid_bbox_with_str_batch27():
    assert _is_valid_bbox(["1", 2, 3, 4]) is False


def test_is_valid_bbox_with_nan_batch27():
    assert _is_valid_bbox([float("nan"), 2, 3, 4]) is False


def test_is_valid_bbox_with_inf_batch27():
    assert _is_valid_bbox([float("inf"), 2, 3, 4]) is False


def test_is_valid_bbox_with_neg_inf_batch27():
    assert _is_valid_bbox([float("-inf"), 2, 3, 4]) is False


def test_is_valid_bbox_len_three_batch27():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_len_five_batch27():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_empty_list_batch27():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_none_batch27():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_tuple_batch27():
    """tuple 不是 list → 无效（实现要求 list）。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_dict_batch27():
    assert _is_valid_bbox({"x": 1}) is False


def test_is_valid_bbox_string_batch27():
    assert _is_valid_bbox("abcd") is False


# ---------- _text_preservation 第二十七批 ----------


def test_text_preservation_image_excluded_batch27():
    """image element 的 content 应被排除。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},  # 应被忽略
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_content_none_batch27():
    """element content=None → 视为空。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # expected = "", actual = "" → 都为空 → null
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_text_none_batch27():
    """chunk text=None → 视为空。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # expected = "abc", actual = ""
    # precision: actual empty → null empty_actual
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_extra_whitespace_batch27():
    """多余空白被去除，仍视为 equal。"""
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "a   b    c"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_nbsp_normalized_batch27():
    """NBSP 也被去除。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "a\xa0b\xa0c"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_emoji_preserved_batch27():
    """emoji 应保留，能匹配。"""
    elements = [{"type": "paragraph", "content": "hello 😀 world"}]
    chunks = [{"text": "hello😀world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_unicode_escape_batch27():
    elements = [{"type": "paragraph", "content": "café"}]
    chunks = [{"text": "café"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_chars_batch27():
    """actual 比 expected 少 → equal False, recall<1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 2/2 = 1.0; recall = 2/3
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_extra_chars_batch27():
    """actual 比 expected 多 → equal False, precision<1。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 2/3; recall = 2/2 = 1.0
    assert out["precision"]["value"] == pytest.approx(2 / 3)
    assert out["recall"]["value"] == 1.0


def test_text_preservation_both_empty_batch27():
    """expected 和 actual 都空 → null empty_expected_and_actual。"""
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True  # "" == "" → True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_returns_three_keys_batch27():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_chunk_order_matters_batch27():
    """顺序敏感：乱序的 chunks → equal False。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]  # 反序
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # 但 precision/recall 仍 1.0（多集合相同）
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


# ---------- _silent_drop_count 第二十七批 ----------


def test_silent_drop_count_no_expectations_batch27():
    out = _silent_drop_count({"paragraph": 10}, None)
    assert out["reason"] == "no_expectations"
    assert out["value"] is None


def test_silent_drop_count_expectations_empty_dict_batch27():
    out = _silent_drop_count({"paragraph": 10}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type_batch27():
    """expectations 不含 element_count_by_type → no_expectations_element_count。"""
    out = _silent_drop_count({"paragraph": 10}, {"other_field": "x"})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_element_count_by_type_empty_batch27():
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_greater_than_expected_batch27():
    """actual > expected → drops=0（max(0, neg)=0）。"""
    out = _silent_drop_count({"paragraph": 15}, {"element_count_by_type": {"paragraph": 10}})
    assert out["value"] == 0


def test_silent_drop_count_actual_equal_expected_batch27():
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 10}})
    assert out["value"] == 0


def test_silent_drop_count_actual_less_than_expected_batch27():
    out = _silent_drop_count({"paragraph": 7}, {"element_count_by_type": {"paragraph": 10}})
    assert out["value"] == 3


def test_silent_drop_count_actual_missing_type_batch27():
    """expected 含 type 但 actual 不含 → actual=0, drop=expected。"""
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_count_multiple_types_batch27():
    """多 type 求和。"""
    by_type = {"paragraph": 8, "heading": 1, "table": 2}
    exp = {"element_count_by_type": {"paragraph": 10, "heading": 2, "table": 2}}
    out = _silent_drop_count(by_type, exp)
    # paragraph: 10-8=2, heading: 2-1=1, table: max(0, 2-2)=0
    assert out["value"] == 3


def test_silent_drop_count_extra_actual_types_ignored_batch27():
    """actual 多余 type 不影响（不算负 drop）。"""
    by_type = {"paragraph": 10, "image": 5}
    exp = {"element_count_by_type": {"paragraph": 10}}
    out = _silent_drop_count(by_type, exp)
    # paragraph: 0, image 不在 expected 中 → 不计
    assert out["value"] == 0


def test_silent_drop_count_returns_int_metric_batch27():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0
    assert isinstance(out["value"], int)


# ---------- _heading_boundary_ratio 第二十七批 ----------


def test_heading_boundary_no_headings_batch27():
    out = _heading_boundary_ratio(
        [{"type": "paragraph", "element_id": "p1"}],
        [{"source_element_ids": ["p1"]}],
    )
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_batch27():
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [],
    )
    # 有 heading 无 chunks → ratio 0
    assert out["value"] == 0.0
    assert out["reason"] is None


def test_heading_boundary_chunks_empty_source_ids_batch27():
    """chunks 都 source_element_ids=[] → 无匹配。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": []}],
    )
    assert out["value"] == 0.0


def test_heading_boundary_chunks_none_source_ids_batch27():
    """chunks 都无 source_element_ids key → 视为 []。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{}],
    )
    assert out["value"] == 0.0


def test_heading_boundary_perfect_match_batch27():
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": ["h1", "p1"]}],
    )
    # h1 是 chunk 第一个 → matched=1, ratio=1.0
    assert out["value"] == 1.0


def test_heading_boundary_heading_not_first_batch27():
    """heading 在 source_element_ids 但不是第一个 → 不算合规。"""
    out = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": ["p1", "h1"]}],
    )
    # h1 在 chunk 中但不是第一个 → not matched
    assert out["value"] == 0.0


def test_heading_boundary_multiple_headings_partial_batch27():
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
        ],
        [
            {"source_element_ids": ["h1", "p1"]},
            {"source_element_ids": ["p2"]},  # h2 不在任何 chunk 首
        ],
    )
    # h1 matched, h2 not matched → 1/2 = 0.5
    assert out["value"] == 0.5


def test_heading_boundary_multiple_headings_perfect_batch27():
    out = _heading_boundary_ratio(
        [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
        ],
        [
            {"source_element_ids": ["h1", "p1"]},
            {"source_element_ids": ["h2", "p2"]},
        ],
    )
    assert out["value"] == 1.0


def test_heading_boundary_heading_without_element_id_batch27():
    """heading 无 element_id → h.get('element_id')=None → 不在 chunk_first_ids。"""
    out = _heading_boundary_ratio(
        [{"type": "heading"}],  # 无 element_id
        [{"source_element_ids": ["h1"]}],
    )
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 第二十七批 ----------


def test_chunk_reference_ratio_no_chunks_batch27():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunks_no_source_ids_batch27():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}],
        [{}],  # 无 source_element_ids
    )
    # 空 source_ids 不算 valid → 0/1 = 0.0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_empty_source_ids_batch27():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}],
        [{"source_element_ids": []}],
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_perfect_batch27():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}, {"element_id": "e2"}],
        [{"source_element_ids": ["e1", "e2"]}],
    )
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_batch27():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}, {"element_id": "e2"}],
        [
            {"source_element_ids": ["e1"]},  # valid
            {"source_element_ids": ["e_missing"]},  # invalid
        ],
    )
    # 1/2 = 0.5
    assert out["value"] == 0.5


def test_chunk_reference_ratio_all_missing_batch27():
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}],
        [{"source_element_ids": ["x"]}, {"source_element_ids": ["y"]}],
    )
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_partial_source_ids_batch27():
    """chunk 含部分 missing 的 source_ids → 整个 chunk 算 invalid。"""
    out = _chunk_reference_ratio(
        [{"element_id": "e1"}, {"element_id": "e2"}],
        [{"source_element_ids": ["e1", "missing"]}],  # 部分缺失
    )
    # all() → False → 0/1 = 0.0
    assert out["value"] == 0.0


# ---------- _image_resource_ratio 第二十七批 ----------


def test_image_resource_ratio_no_images_batch27():
    out = _image_resource_ratio([{"type": "paragraph"}], None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path_batch27():
    out = _image_resource_ratio([{"type": "image"}], None)
    # rp=None → 不计 valid → 0/1
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch27():
    out = _image_resource_ratio([{"type": "image", "resource_path": ""}], None)
    # rp="" → falsy → 不计 valid
    assert out["value"] == 0.0


def test_image_resource_ratio_file_does_not_exist_batch27(tmp_path):
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(tmp_path / "missing.png")}],
        None,
    )
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists_batch27(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG fake")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(p)}],
        None,
    )
    assert out["value"] == 1.0


def test_image_resource_ratio_empty_file_batch27(tmp_path):
    """0 字节文件 → size=0 → 不算 valid。"""
    p = tmp_path / "empty.png"
    p.write_bytes(b"")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": str(p)}],
        None,
    )
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir_concat_batch27(tmp_path):
    """resource_path 只是文件名，image_base_dir 提供目录 → 拼接后能找到。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG fake")
    out = _image_resource_ratio(
        [{"type": "image", "resource_path": "img.png"}],
        tmp_path,
    )
    assert out["value"] == 1.0


def test_image_resource_ratio_oserror_safe_batch27(tmp_path):
    """is_file 抛 OSError → 不崩溃。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG")
    with patch("pathlib.Path.is_file", side_effect=OSError("boom")):
        out = _image_resource_ratio(
            [{"type": "image", "resource_path": str(p)}],
            None,
        )
    # OSError 容错 → 不算 valid → 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch27(tmp_path):
    """一半图片存在，一半不存在。"""
    p = tmp_path / "exists.png"
    p.write_bytes(b"\x89PNG")
    out = _image_resource_ratio(
        [
            {"type": "image", "resource_path": str(p)},
            {"type": "image", "resource_path": str(tmp_path / "missing.png")},
        ],
        None,
    )
    assert out["value"] == 0.5


# ---------- _pdf_locator_ratio 第二十七批 ----------


def test_pdf_locator_ratio_no_elements_batch27():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_page_zero_batch27():
    out = _pdf_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": 0, "bbox": [1, 2, 3, 4]}}]
    )
    # page=0 → invalid → 0/1
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch27():
    out = _pdf_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": -1, "bbox": [1, 2, 3, 4]}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_float_batch27():
    """page 是 float → invalid（实现要求 int）。"""
    out = _pdf_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": 1.0, "bbox": [1, 2, 3, 4]}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_string_batch27():
    """page 是 string → invalid。"""
    out = _pdf_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": "1", "bbox": [1, 2, 3, 4]}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_missing_bbox_batch27():
    """text 类型缺 bbox → invalid。"""
    out = _pdf_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": 1}}]
    )
    assert out["value"] == 0.0


def test_pdf_locator_ratio_non_text_no_bbox_ok_batch27():
    """非 text 类型不需要 bbox。"""
    out = _pdf_locator_ratio(
        [{"type": "image", "source_locator": {"page": 1}}]
    )
    assert out["value"] == 1.0


def test_pdf_locator_ratio_perfect_batch27():
    out = _pdf_locator_ratio(
        [
            {"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
            {"type": "heading", "source_locator": {"page": 2, "bbox": [1, 2, 3, 4]}},
        ]
    )
    assert out["value"] == 1.0


def test_pdf_locator_ratio_no_source_locator_batch27():
    """element 无 source_locator → loc={} → page=None → invalid。"""
    out = _pdf_locator_ratio([{"type": "paragraph"}])
    assert out["value"] == 0.0


def test_pdf_locator_ratio_source_locator_none_batch27():
    """source_locator=None → loc={}（实现 `or {}`）。"""
    out = _pdf_locator_ratio([{"type": "paragraph", "source_locator": None}])
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第二十七批 ----------


def test_docx_locator_ratio_no_elements_batch27():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_paragraph_index_batch27():
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    )
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_index_batch27():
    out = _docx_locator_ratio(
        [{"type": "table", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}}]
    )
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_batch27():
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"section": "main"}}]
    )
    assert out["value"] == 1.0


def test_docx_locator_ratio_rejects_page_batch27():
    """有 page → 拒。"""
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_rejects_bbox_batch27():
    """有 bbox → 拒。"""
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "paragraph_index": 0}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_batch27():
    """无任何结构键 → invalid。"""
    out = _docx_locator_ratio(
        [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    )
    assert out["value"] == 0.0


def test_docx_locator_ratio_mixed_batch27():
    out = _docx_locator_ratio(
        [
            {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "source_locator": {"page": 1}},
            {"type": "paragraph", "source_locator": {"unknown": "x"}},
        ]
    )
    # 1 valid / 3 = 0.333
    assert out["value"] == pytest.approx(1 / 3)


def test_docx_locator_ratio_no_source_locator_batch27():
    out = _docx_locator_ratio([{"type": "paragraph"}])
    assert out["value"] == 0.0


def test_docx_locator_ratio_relationship_id_batch27():
    out = _docx_locator_ratio(
        [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    )
    assert out["value"] == 1.0


# ---------- module source forbidden tokens 第四十三批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import json",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch27():
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token: {tok}"


def test_module_source_no_eval_exec_batch27():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch27():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch27():
    source = inspect.getsource(mmod)
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch27():
    source = inspect.getsource(mmod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_environ_batch27():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_no_subprocess_batch27():
    source = inspect.getsource(mmod)
    assert "subprocess" not in source


def test_module_source_no_argparse_batch27():
    source = inspect.getsource(mmod)
    assert "argparse" not in source


def test_module_source_no_dataclass_batch27():
    source = inspect.getsource(mmod)
    assert "@dataclass" not in source
    assert "from dataclasses" not in source


def test_module_source_no_class_keyword_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_uses_from_future_annotations_batch27():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_math_allowed_batch27():
    """metrics.py 允许 import math（isfinite 用）。"""
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_collections_counter_allowed_batch27():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_pathlib_path_allowed_batch27():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_no_module_level_mutables_batch27():
    """不应有 module-level 私有 mutable。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            name = node.targets[0].id
            if name.startswith("_") and not name.startswith("__") and name not in ("_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"):
                # 这三个是 tuple / str（immutable），允许
                pytest.fail(f"private module-level mutable: {name}")


# ---------- module source 字符串精确补强第三十九批 ----------


def test_module_source_contains_compute_automatic_metrics_batch27():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics" in source


def test_module_source_contains_text_types_constant_batch27():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in source


def test_module_source_contains_pdf_bbox_required_types_batch27():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in source


def test_module_source_contains_not_evaluated_batch27():
    source = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in source


def test_module_source_contains_pipeline_failed_batch27():
    source = inspect.getsource(mmod)
    assert "pipeline_failed" in source


def test_module_source_contains_no_elements_batch27():
    source = inspect.getsource(mmod)
    assert "no_elements" in source


def test_module_source_contains_no_chunks_batch27():
    source = inspect.getsource(mmod)
    assert "no_chunks" in source


def test_module_source_contains_no_image_elements_batch27():
    source = inspect.getsource(mmod)
    assert "no_image_elements" in source


def test_module_source_contains_no_heading_elements_batch27():
    source = inspect.getsource(mmod)
    assert "no_heading_elements" in source


def test_module_source_contains_no_expectations_batch27():
    source = inspect.getsource(mmod)
    assert "no_expectations" in source


def test_module_source_contains_empty_expected_and_actual_batch27():
    source = inspect.getsource(mmod)
    assert "empty_expected_and_actual" in source


def test_module_source_contains_strip_unicode_whitespace_batch27():
    source = inspect.getsource(mmod)
    assert "_strip_unicode_whitespace" in source
    assert "isspace" in source


def test_module_source_contains_is_valid_bbox_batch27():
    source = inspect.getsource(mmod)
    assert "_is_valid_bbox" in source
    assert "math.isfinite" in source


def test_module_source_contains_counter_intersection_batch27():
    source = inspect.getsource(mmod)
    assert "& c_actual" in source or "c_actual & c_expected" in source or "c_expected & c_actual" in source


# ---------- signatures 第三十九批 ----------


def test_signature_null_batch27():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]
    assert sig.parameters["reason"].annotation == "str"


def test_signature_ratio_batch27():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]
    assert sig.parameters["value"].annotation == "float"


def test_signature_bool_metric_batch27():
    sig = inspect.signature(_bool_metric)
    assert sig.parameters["value"].annotation == "bool"


def test_signature_int_metric_batch27():
    sig = inspect.signature(_int_metric)
    assert sig.parameters["value"].annotation == "int"


def test_signature_compute_automatic_metrics_batch27():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_automatic_metrics_defaults_batch27():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_ratio_batch27():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_ratio_batch27():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_image_resource_ratio_batch27():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_ratio_batch27():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_text_preservation_batch27():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_ratio_batch27():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_silent_drop_count_batch27():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


def test_signature_all_annotations_are_strings_batch27():
    for fn in [
        _null, _ratio, _bool_metric, _int_metric,
        compute_automatic_metrics, _pdf_locator_ratio, _docx_locator_ratio,
        _is_valid_bbox, _image_resource_ratio, _chunk_reference_ratio,
        _strip_unicode_whitespace, _text_preservation,
        _heading_boundary_ratio, _silent_drop_count,
    ]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十九批 ----------


def test_module_all_present_batch27():
    assert hasattr(mmod, "__all__")


def test_module_all_only_compute_batch27():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_has_many_functions_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    expected = {
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    }
    assert set(funcs) == expected


def test_module_no_classes_batch27():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch27():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__.strip()) > 0


def test_module_docstring_mentions_text_preservation_batch27():
    assert "text_preservation" in mmod.__doc__ or "文本保留" in mmod.__doc__


def test_module_docstring_mentions_pure_function_batch27():
    assert "纯函数" in mmod.__doc__ or "pure" in mmod.__doc__.lower()


def test_module_uses_from_future_annotations_batch27():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_text_types_constant_immutable_batch27():
    """_TEXT_TYPES 应是 tuple（immutable）。"""
    from evaluation.metrics import _TEXT_TYPES
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_pdf_bbox_required_types_immutable_batch27():
    from evaluation.metrics import _PDF_BBOX_REQUIRED_TYPES
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_all_entries_accessible_batch27():
    for name in mmod.__all__:
        assert hasattr(mmod, name)


# ---------- 端到端集成第三十九批 ----------


def test_e2e_compute_metrics_full_pdf_batch27():
    document = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello world",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
        ],
        "chunks": [
            {"text": "hello world", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 1
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_full_docx_batch27():
    document = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pipeline_success"]["value"] is True
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_pipeline_failed_batch27():
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "x"
    for name in ("element_count_total", "pdf_locator_valid_ratio"):
        assert out[name]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_no_mutation_batch27():
    document = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    import copy
    snap = copy.deepcopy(document)
    compute_automatic_metrics(document, None, "pdf", None)
    assert document == snap


def test_e2e_compute_metrics_with_expectations_batch27():
    document = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    # actual paragraph = 1, expected = 5 → drop = 4
    assert out["silent_drop_count"]["value"] == 4


def test_e2e_compute_metrics_keys_count_batch27():
    """compute_automatic_metrics 返回 dict 含 13 个 key（成功路径）。"""
    document = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x",
                       "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    expected = {
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
    assert set(out.keys()) == expected


def test_e2e_compute_metrics_pipeline_failed_keys_count_batch27():
    """失败路径 → 12 个 key（无 schema_valid 之外的 11 个 + pipeline_success/error_code/schema_valid）。"""
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    expected = {
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
    assert set(out.keys()) == expected
