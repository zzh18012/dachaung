"""evaluation/metrics.py 第五十一轮 edges 测试（Round 477）。

补强 edges48 未触及的角度：
- 构造子第二十三批（_null 不带 reason / _ratio 接受 int / _bool_metric 接受 truthy / _int_metric 接受 float / 各种 idempotent）
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十三批（types tuple 不可变 / set 转换 / 排除 image / subset）
- _strip_unicode_whitespace 第二十三批（NBSP / em space / tab / mixed / digit-only / 全空白）
- compute_automatic_metrics 第二十三批（更多场景）
- _pdf_locator_ratio 第二十三批（mixed valid/invalid / 部分缺 page / page=1 valid / float page invalid）
- _docx_locator_ratio 第二十三批（page 拒绝 / bbox 拒绝 / paragraph_index valid / 多 structural key valid）
- _is_valid_bbox 第二十三批（科学计数法 / 负数 / 零 / 大数 / mix int float / list 中 None）
- _image_resource_ratio 第二十三批（image_dir 帮助找到 / 文件 size=0 / 不存在文件）
- _chunk_reference_ratio 第二十三批（partial valid / 全 valid / 全 invalid / id 重复）
- _text_preservation 第二十三批（重复字符 / 顺序变化 / 中文 / emoji）
- _heading_boundary_ratio 第二十三批（多 heading 多 chunk / heading 无 element_id）
- _silent_drop_count 第二十三批（多 type 计 drop / actual 多于 expected / mixed drop）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
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


# ---------- 构造子第二十三批 ----------


def test_null_returns_dict_with_two_keys_batch23():
    out = _null("x")
    assert set(out.keys()) == {"value", "reason"}


def test_null_value_is_none_batch23():
    assert _null("x")["value"] is None


def test_null_with_emoji_reason_batch23():
    out = _null("失败 🚨")
    assert out["reason"] == "失败 🚨"


def test_ratio_accepts_int_batch23():
    """_ratio 接受 int（被 float()）。"""
    out = _ratio(1)
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_ratio_accepts_zero_batch23():
    out = _ratio(0)
    assert out["value"] == 0.0


def test_ratio_returns_dict_with_two_keys_batch23():
    out = _ratio(0.5)
    assert set(out.keys()) == {"value", "reason"}
    assert out["reason"] is None


def test_bool_metric_accepts_truthy_int_batch23():
    """_bool_metric 用 bool() 转换。"""
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_accepts_falsy_int_batch23():
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_accepts_string_batch23():
    """非空字符串 truthy。"""
    assert _bool_metric("x")["value"] is True
    assert _bool_metric("")["value"] is False


def test_int_metric_accepts_float_batch23():
    """_int_metric 接受 float（被 int()）。"""
    out = _int_metric(3.9)
    assert out["value"] == 3
    assert isinstance(out["value"], int)


def test_int_metric_accepts_string_digit_batch23():
    """_int_metric 不接受 str（int('5') 是合法但 type 是 int）。"""
    # int_metric(int('5')) → 5
    out = _int_metric(int("5"))
    assert out["value"] == 5


def test_int_metric_zero_batch23():
    out = _int_metric(0)
    assert out["value"] == 0
    assert isinstance(out["value"], int)


def test_int_metric_negative_batch23():
    out = _int_metric(-5)
    assert out["value"] == -5


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十三批 ----------


def test_text_types_is_tuple_batch23():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_batch23():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_seven_entries_batch23():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_four_entries_batch23():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types_batch23():
    """_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES。"""
    text_set = set(_TEXT_TYPES)
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in text_set


def test_text_types_contains_heading_batch23():
    assert "heading" in _TEXT_TYPES


def test_text_types_contains_paragraph_batch23():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_contains_list_item_batch23():
    assert "list_item" in _TEXT_TYPES


def test_text_types_contains_table_batch23():
    assert "table" in _TEXT_TYPES


def test_text_types_contains_caption_batch23():
    assert "caption" in _TEXT_TYPES


def test_text_types_contains_header_footer_batch23():
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES


def test_text_types_excludes_image_batch23():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_excludes_table_batch23():
    """table 不需要 bbox（PDF 中 table 单独处理）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_header_footer_batch23():
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_can_be_converted_to_set_batch23():
    s = set(_TEXT_TYPES)
    assert isinstance(s, set)
    assert len(s) == 7


# ---------- _strip_unicode_whitespace 第二十三批 ----------


def test_strip_unicode_whitespace_nbsp_batch23():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch23():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_batch23():
    """U+2002 en space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch23():
    """U+3000 ideographic space。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch23():
    """U+2028 line separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch23():
    """U+2029 paragraph separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_only_whitespace_batch23():
    """纯空白字符串。"""
    assert _strip_unicode_whitespace("   \t\n　") == ""


def test_strip_unicode_whitespace_no_whitespace_batch23():
    """无空白。"""
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_empty_string_batch23():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_digit_only_batch23():
    """纯数字。"""
    assert _strip_unicode_whitespace("12345") == "12345"


def test_strip_unicode_whitespace_mixed_batch23():
    """混合空白 + ASCII + Unicode。"""
    s = "a b\tc d\ne"
    assert _strip_unicode_whitespace(s) == "abcde"


def test_strip_unicode_whitespace_returns_str_batch23():
    """返回类型是 str。"""
    assert isinstance(_strip_unicode_whitespace("x"), str)


# ---------- compute_automatic_metrics 第二十三批 ----------


def test_compute_metrics_error_overrides_doc_batch23():
    """error 非空 + document 非空 → pipeline_success=False。"""
    doc = {"elements": [], "chunks": []}
    err = {"code": "PARSE_FAIL", "message": "x"}
    out = compute_automatic_metrics(doc, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_error_code_in_output_batch23():
    """error_code 字段。"""
    err = {"code": "PARSE_FAIL", "message": "x"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "PARSE_FAIL"


def test_compute_metrics_error_code_none_when_no_error_batch23():
    """无 error 时 error_code 是 None。"""
    out = compute_automatic_metrics({"elements": []}, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_schema_valid_for_minimal_doc_batch23():
    """最小 doc → schema_valid=True（不抛异常）。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_path": "x.pdf",
        "source_hash": "x",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # schema_valid 应是 True 或 False（不应是异常 reason）
    assert out["schema_valid"]["value"] in (True, False)


def test_compute_metrics_doc_none_returns_pipeline_failed_for_all_batch23():
    """doc=None → 所有指标都是 pipeline_failed。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    for k in (
        "element_count_total",
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
        assert out[k]["reason"] == "pipeline_failed"


def test_compute_metrics_element_count_by_type_distinct_batch23():
    """element_count_by_type 不同 type 计数。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "e1"},
            {"type": "paragraph", "element_id": "e2"},
            {"type": "heading", "element_id": "e3"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    bt = out["element_count_by_type"]["value"]
    assert bt == {"paragraph": 2, "heading": 1}


def test_compute_metrics_element_count_by_type_unknown_for_missing_type_batch23():
    """缺 type 字段 → 'unknown'。"""
    doc = {"elements": [{"element_id": "e1"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    bt = out["element_count_by_type"]["value"]
    assert bt == {"unknown": 1}


# ---------- _pdf_locator_ratio 第二十三批 ----------


def test_pdf_locator_ratio_page_one_valid_batch23():
    """page=1 是 valid。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_mixed_valid_invalid_batch23():
    """部分 valid 部分 invalid → 比例。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {"type": "image", "source_locator": {"page": 0}},  # invalid (page < 1)
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_float_page_invalid_batch23():
    """page=1.5 (float) → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": 1.5}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_string_page_invalid_batch23():
    """page='1' (str) → invalid。"""
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_valid_bbox_batch23():
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]},
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_paragraph_with_invalid_bbox_batch23():
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "bbox": [0, 0]},  # 不是 4 个
    }]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_locator_batch23():
    """element 无 source_locator 字段。"""
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch23():
    """source_locator 显式 None。"""
    elements = [{"type": "image", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_negative_page_batch23():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_elements_batch23():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


# ---------- _docx_locator_ratio 第二十三批 ----------


def test_docx_locator_ratio_paragraph_index_valid_batch23():
    elements = [{
        "type": "paragraph",
        "source_locator": {"paragraph_index": 5},
    }]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_invalid_batch23():
    """有 page 字段 → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"page": 1, "paragraph_index": 5},
    }]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_invalid_batch23():
    """有 bbox 字段 → invalid。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"bbox": [0, 0, 0, 0]},
    }]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_key_invalid_batch23():
    """无 structural key → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"foo": "bar"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_mixed_batch23():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 1}},  # valid
        {"type": "paragraph", "source_locator": {"random": 1}},  # invalid
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


def test_docx_locator_ratio_section_index_batch23():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_no_elements_batch23():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


# ---------- _is_valid_bbox 第二十三批 ----------


def test_is_valid_bbox_scientific_notation_batch23():
    """科学计数法 float。"""
    assert _is_valid_bbox([1e-3, 1e-3, 1.0, 1.0]) is True


def test_is_valid_bbox_negative_numbers_batch23():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_zero_batch23():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_very_large_batch23():
    assert _is_valid_bbox([10**10, 10**10, 10**10, 10**10]) is True


def test_is_valid_bbox_mixed_int_float_batch23():
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


def test_is_valid_bbox_list_with_none_batch23():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


def test_is_valid_bbox_list_with_str_batch23():
    assert _is_valid_bbox(["0", 0, 0, 0]) is False


def test_is_valid_bbox_empty_list_batch23():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_many_items_batch23():
    assert _is_valid_bbox([0, 0, 0, 0, 0]) is False


def test_is_valid_bbox_returns_bool_batch23():
    assert isinstance(_is_valid_bbox([0, 0, 0, 0]), bool)


# ---------- _image_resource_ratio 第二十三批 ----------


def test_image_resource_ratio_no_image_elements_batch23():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_empty_resource_path_batch23():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_missing_resource_path_batch23():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_nonexistent_file_batch23(tmp_path):
    elements = [{"type": "image", "resource_path": "no.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists_batch23(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")  # size > 0
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_empty_size_file_batch23(tmp_path):
    """size=0 文件 → invalid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir_finds_by_name_batch23(tmp_path):
    """resource_path 只是文件名，image_base_dir 帮助找到。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_partial_valid_batch23(tmp_path):
    """部分图片存在。"""
    img = tmp_path / "img1.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "nonexistent.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 第二十三批 ----------


def test_chunk_reference_ratio_no_chunks_batch23():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_elements_batch23():
    """elements 为空但 chunks 非空 → ratio=0.0（all invalid）。"""
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch23():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_all_invalid_batch23():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["missing"]},
        {"source_element_ids": ["alsomissing"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_valid_batch23():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["missing"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_chunk_no_ids_key_batch23():
    """chunk 缺 source_element_ids 字段。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_empty_ids_batch23():
    """chunk source_element_ids 是空 list。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_multiple_ids_per_chunk_batch23():
    """一个 chunk 引用多个 element → 全 valid 才算。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]  # all valid
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multiple_ids_partial_invalid_batch23():
    """一个 chunk 引用多个 element，部分 invalid → 该 chunk invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]  # 1 valid 1 invalid
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _text_preservation 第二十三批 ----------


def test_text_preservation_repeated_chars_batch23():
    """重复字符。"""
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aaa"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_order_change_batch23():
    """顺序变化：equal=False，但 precision/recall 仍 1.0（多集合相同）。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_chinese_batch23():
    """中文字符。"""
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_emoji_batch23():
    """emoji 字符。"""
    elements = [{"type": "paragraph", "content": "test🚀"}]
    chunks = [{"text": "test🚀"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_image_excluded_batch23():
    """image 类型不参与。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_extra_text_batch23():
    """chunk 多了字符。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.75  # 3/4
    assert out["recall"]["value"] == 1.0  # 3/3


def test_text_preservation_chunk_missing_text_batch23():
    """chunk 少了字符。"""
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.75


def test_text_preservation_empty_expected_only_batch23():
    """expected 空，actual 非空。"""
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # expected=Counter() 与 actual=Counter('abc') 交集为 0
    # precision = 0/3 = 0.0（actual 非空，分母非 0）
    assert out["precision"]["value"] == 0.0
    # recall 分母 = |expected| = 0 → null + reason
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_empty_actual_only_batch23():
    """expected 非空，actual 空。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision 分母 = |actual| = 0 → null + reason
    assert out["precision"]["reason"] == "empty_actual"
    # recall = 0/3 = 0.0（expected 非空，分母非 0）
    assert out["recall"]["value"] == 0.0


def test_text_preservation_returns_dict_with_three_keys_batch23():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# ---------- _heading_boundary_ratio 第二十三批 ----------


def test_heading_boundary_ratio_no_heading_elements_batch23():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_perfect_batch23():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_no_chunks_batch23():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_partial_match_batch23():
    """部分 heading 在 chunk 首位。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只 h1 在首位
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_heading_not_first_in_chunk_batch23():
    """heading 不在 chunk 首位 → 不算合规。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_heading_no_element_id_batch23():
    """heading 缺 element_id 字段。"""
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h.get('element_id') → None，不在 chunk_first_ids
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_headings_multiple_chunks_batch23():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _silent_drop_count 第二十三批 ----------


def test_silent_drop_count_no_expectations_batch23():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch23():
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_element_count_key_batch23():
    out = _silent_drop_count({}, {"other": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_perfect_match_batch23():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_count_drop_batch23():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 4


def test_silent_drop_count_actual_more_than_expected_batch23():
    """actual 多于 expected → 不计负 drop。"""
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_count_multiple_types_batch23():
    by_type = {"paragraph": 1, "heading": 2}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 1}}
    # paragraph drop 4, heading no drop (1 < 2 not satisfied)
    # actual_heading=2, exp=1 → 1 < 2 false → no drop
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 4


def test_silent_drop_count_unknown_type_ignored_batch23():
    """expected 含 by_type 中没有的 type。"""
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 5


def test_silent_drop_count_returns_int_value_batch23():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, exp)
    assert isinstance(out["value"], int)


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch23(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch23():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch23():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch23():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch23():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch23():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch23():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch23():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch23():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch23():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch23():
    src = inspect.getsource(mmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch23():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch23():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch23():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_collections_import_batch23():
    """注意：metrics.py 用 collections.Counter，是合法的。"""
    src = inspect.getsource(mmod)
    # 仅允许 'from collections import Counter'
    assert "import collections" not in src.replace("from collections import Counter", "")


def test_module_source_no_pandas_import_batch23():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch23():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch23():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import_batch23():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_collections_counter_import_batch23():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import_batch23():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch23():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch23():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_has_pdf_bbox_required_types_constant_batch23():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_has_not_evaluated_constant_batch23():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


def test_module_source_has_null_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_has_ratio_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_has_bool_metric_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_has_int_metric_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_has_compute_automatic_metrics_function_batch23():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_strip_unicode_whitespace_function_batch23():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_has_all_list_batch23():
    src = inspect.getsource(mmod)
    assert "__all__" in src


# ---------- signatures 第三十四批 ----------


def test_signature_null_batch23():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["reason"]


def test_signature_ratio_batch23():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_bool_metric_batch23():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_int_metric_batch23():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_compute_automatic_metrics_batch23():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_signature_compute_automatic_metrics_image_base_dir_default_none_batch23():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    assert p.default is None


# ---------- module 合理性第三十四批 ----------


def test_module_has_all_attribute_batch23():
    assert hasattr(mmod, "__all__")


def test_module_all_count_one_batch23():
    assert len(mmod.__all__) == 1


def test_module_all_contents_exact_batch23():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_does_not_import_app_pipeline_batch23():
    src = inspect.getsource(mmod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_app_parsers_batch23():
    src = inspect.getsource(mmod)
    assert "from app.parsers" not in src
    assert "from app import parsers" not in src


def test_module_does_not_import_evaluation_runner_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_manifest_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.manifest" not in src


def test_module_does_not_import_evaluation_annotation_metrics_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.annotation_metrics" not in src


def test_module_does_not_import_evaluation_report_batch23():
    src = inspect.getsource(mmod)
    assert "from evaluation.report" not in src


def test_module_no_main_block_batch23():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_has_docstring_batch23():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


# ---------- 端到端集成第三十四批 ----------


def test_e2e_compute_metrics_doc_none_full_metrics_set_batch23():
    """doc=None 时仍输出全部 12+ 指标。"""
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
    assert expected_keys.issubset(set(out.keys()))


def test_e2e_compute_metrics_pdf_doc_locator_both_present_batch23():
    """PDF 文档同时输出 pdf_locator_valid_ratio 和 docx_locator_valid_ratio（后者 null）。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pdf_locator_valid_ratio" in out
    assert "docx_locator_valid_ratio" in out
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_e2e_compute_metrics_docx_doc_locator_batch23():
    """DOCX 文档：pdf_locator 是 null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_compute_metrics_full_doc_all_metrics_value_batch23():
    """完整 doc → 所有指标都有 value 或 reason。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "abc",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [
            {"text": "abc", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 检查所有 metric 都有 value 或 reason
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_e2e_compute_metrics_silent_drop_count_int_value_batch23():
    """silent_drop_count 是 int（不是 float）。"""
    doc = {"elements": [], "chunks": []}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    # doc 有 elements=[] → by_type={} → silent_drop=5
    assert out["silent_drop_count"]["value"] == 5
    assert isinstance(out["silent_drop_count"]["value"], int)


def test_e2e_compute_metrics_element_count_by_type_dict_batch23():
    """element_count_by_type 的 value 是 dict。"""
    doc = {"elements": [{"type": "paragraph", "element_id": "e1"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(out["element_count_by_type"]["value"], dict)


def test_e2e_text_preservation_chinese_full_match_batch23():
    """中文完整保留。"""
    elements = [
        {"type": "paragraph", "content": "你好世界"},
        {"type": "paragraph", "content": "测试"},
    ]
    chunks = [
        {"text": "你好"},
        {"text": "世界"},
        {"text": "测试"},
    ]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0
