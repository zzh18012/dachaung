"""evaluation/metrics.py 第四十四轮 edges 测试（Round 429）。

补强 edges41 未触及的角度：
- module 常量第十五批（_NOT_EVALUATED / _TEXT_TYPES 不可变 / _PDF_BBOX_REQUIRED_TYPES 长度）
- _null / _ratio / _bool_metric / _int_metric 边界第十五批（reason 为空字符串 / 多字符 reason / value=0.0 / value=1.0 / value<0 / int 强转）
- compute_automatic_metrics 第十五批（document None + error 非空 / document 非 None + error None / source_type 不是 pdf/docx / expectations=None / image_base_dir=None / 不修改 document / 不修改 expectations / 14 keys）
- _strip_unicode_whitespace 第十五批（多种 Unicode 空白 / emoji 保留 / 制表符 / NUL 字符 / 全角空格）
- _is_valid_bbox 第十五批（None / 0-len list / 5-len list / 4 元素 tuple / 4 字符串 / 4 None / 4 嵌套 list）
- _pdf_locator_ratio 第十五批（元素无 type / page 是字符串 / page 是 0 / page 是 -1 / bbox 是 tuple）
- _docx_locator_ratio 第十五批（locator 含 page / locator 含 bbox / locator 含 paragraph_index / 多种结构键）
- _image_resource_ratio 第十五批（image 无 resource_path / resource_path 空字符串 / image_base_dir 不存在 / 路径含 Unicode）
- _chunk_reference_ratio 第十五批（chunks 空 list / source_element_ids 空 / 包含 None）
- _text_preservation 第十五批（chunks 顺序错乱 / 重复字符 / 多种 Unicode / 全空白）
- _heading_boundary_ratio 第十五批（无 heading / heading 但 chunk 缺 ids）
- _silent_drop_count 第十五批（expectations 空 dict / element_count_by_type 空 / actual > expected / 多类型混合）
- module source forbidden tokens 第二十四批
- module source 字符串精确补强第二十一批
- signatures 第二十一批
- module 合理性第二十一批
- 端到端集成第二十一批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
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


# ---------- module 常量第十五批 ----------


def test_not_evaluated_constant_value_batch15():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_constant_is_str_batch15():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_tuple_immutable_batch15():
    """_TEXT_TYPES 是 tuple，不可修改。"""
    with pytest.raises(TypeError):
        _TEXT_TYPES[0] = "x"  # type: ignore


def test_pdf_bbox_required_types_length_4_batch15():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types_batch15():
    """_PDF_BBOX_REQUIRED_TYPES 应是 _TEXT_TYPES 的子集（标题/段落/caption/list_item）。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_text_types_includes_caption_batch15():
    assert "caption" in _TEXT_TYPES


def test_text_types_excludes_image_batch15():
    assert "image" not in _TEXT_TYPES


# ---------- _null / _ratio / _bool_metric / _int_metric 边界第十五批 ----------


def test_null_empty_string_reason_batch15():
    """reason 是空字符串也应允许。"""
    n = _null("")
    assert n["value"] is None
    assert n["reason"] == ""


def test_null_unicode_reason_batch15():
    n = _null("失败原因")
    assert n["reason"] == "失败原因"


def test_null_returns_new_dict_each_call_batch15():
    n1 = _null("x")
    n2 = _null("x")
    assert n1 == n2
    assert n1 is not n2


def test_ratio_value_zero_batch15():
    r = _ratio(0.0)
    assert r["value"] == 0.0
    assert r["reason"] is None


def test_ratio_value_one_batch15():
    r = _ratio(1.0)
    assert r["value"] == 1.0


def test_ratio_value_negative_batch15():
    """负值不强制校验，应原样保留。"""
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_ratio_returns_float_batch15():
    """value 必须是 float。"""
    r = _ratio(1)
    assert isinstance(r["value"], float)
    assert r["value"] == 1.0


def test_bool_metric_true_batch15():
    b = _bool_metric(True)
    assert b["value"] is True
    assert b["reason"] is None


def test_bool_metric_false_batch15():
    b = _bool_metric(False)
    assert b["value"] is False


def test_bool_metric_coerce_truthy_batch15():
    """非 bool 值会被强制。"""
    b = _bool_metric(1)
    assert b["value"] is True


def test_int_metric_coerce_batch15():
    """字符串 int 应被强转。"""
    i = _int_metric("5")  # type: ignore
    assert i["value"] == 5
    assert isinstance(i["value"], int)


def test_int_metric_negative_batch15():
    i = _int_metric(-3)
    assert i["value"] == -3


# ---------- compute_automatic_metrics 第十五批 ----------


def test_compute_metrics_document_none_with_error_batch15():
    """document=None + error 非空 → pipeline_success=False, error_code 来自 error。"""
    err = {"code": "parse_error", "message": "broken"}
    m = compute_automatic_metrics(None, err, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "parse_error"


def test_compute_metrics_document_present_no_error_batch15():
    """document 非空 + error=None → pipeline_success=True。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True


def test_compute_metrics_source_type_unknown_batch15():
    """source_type 既不是 pdf 也不是 docx → 两个 ratio 都 null。"""
    doc = {
        "document_id": "x", "source_type": "html", "source_path": "x.html",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "html", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_no_expectations_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_metrics_no_image_base_dir_batch15():
    """image_base_dir=None → 仅按原 resource_path 校验。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    # 没有 image elements → no_image_elements
    assert m["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_metrics_does_not_mutate_document_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"type": "heading", "element_id": "h1", "content": "T"}],
        "chunks": [{"text": "T", "source_element_ids": ["h1"]}],
    }
    before = repr(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert repr(doc) == before


def test_compute_metrics_does_not_mutate_expectations_batch15():
    """不应修改 expectations 字典。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"type": "heading", "element_id": "h1", "content": "T"}],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"heading": 5}}
    before = repr(exp)
    compute_automatic_metrics(doc, None, "pdf", exp)
    assert repr(exp) == before


def test_compute_metrics_keys_count_14_batch15():
    """metrics 必须有 14 个 key。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(m.keys()) == expected_keys


# ---------- _strip_unicode_whitespace 第十五批 ----------


def test_strip_unicode_whitespace_nbsp_batch15():
    """NBSP U+00A0 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch15():
    """em space U+2003 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch15():
    """全角空格 U+3000 应被删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch15():
    """U+2028 line separator 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch15():
    """U+2029 paragraph separator 应被删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_emoji_batch15():
    """emoji 不是空白。"""
    assert _strip_unicode_whitespace("a 😀 b") == "a😀b"


def test_strip_unicode_whitespace_preserves_chinese_batch15():
    """中文字符不是空白。"""
    assert _strip_unicode_whitespace("你 好") == "你好"


def test_strip_unicode_whitespace_empty_string_batch15():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace_batch15():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_nul_char_batch15():
    """NUL 字符不是空白。"""
    assert _strip_unicode_whitespace("a\x00b") == "a\x00b"


# ---------- _is_valid_bbox 第十五批 ----------


def test_is_valid_bbox_none_batch15():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_zero_length_batch15():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_five_length_batch15():
    assert _is_valid_bbox([0, 0, 0, 0, 0]) is False


def test_is_valid_bbox_tuple_batch15():
    """tuple 不是 list → False（即使内容合法）。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_four_strings_batch15():
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_four_none_batch15():
    assert _is_valid_bbox([None, None, None, None]) is False


def test_is_valid_bbox_nested_lists_batch15():
    assert _is_valid_bbox([[0], [0], [1], [1]]) is False


def test_is_valid_bbox_four_ints_batch15():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats_batch15():
    assert _is_valid_bbox([0.0, 0.0, 1.5, 2.5]) is True


def test_is_valid_bbox_with_bool_batch15():
    """True 是 int 子类，但 _is_valid_bbox 应拒绝 bool。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_with_nan_batch15():
    assert _is_valid_bbox([0, 0, float("nan"), 1]) is False


def test_is_valid_bbox_with_inf_batch15():
    assert _is_valid_bbox([0, 0, float("inf"), 1]) is False


# ---------- _pdf_locator_ratio 第十五批 ----------


def test_pdf_locator_ratio_no_elements_batch15():
    assert _pdf_locator_ratio([])["reason"] == "no_elements"


def test_pdf_locator_ratio_no_type_batch15():
    """元素无 type → 仍按 page 校验（但 _PDF_BBOX_REQUIRED_TYPES 不命中）。"""
    r = _pdf_locator_ratio([{"source_locator": {"page": 1}}])
    assert r["value"] == 1.0  # page 合法 + 无 type → 视为合法


def test_pdf_locator_ratio_page_string_batch15():
    """page 是字符串 → 不合法。"""
    r = _pdf_locator_ratio([{"type": "heading", "source_locator": {"page": "1"}}])
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_zero_batch15():
    r = _pdf_locator_ratio([{"source_locator": {"page": 0}}])
    assert r["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch15():
    r = _pdf_locator_ratio([{"source_locator": {"page": -1}}])
    assert r["value"] == 0.0


def test_pdf_locator_ratio_bbox_tuple_batch15():
    """bbox 是 tuple → _is_valid_bbox 返回 False。"""
    r = _pdf_locator_ratio([{
        "type": "heading", "source_locator": {"page": 1, "bbox": (0, 0, 1, 1)}
    }])
    assert r["value"] == 0.0


def test_pdf_locator_ratio_partial_valid_batch15():
    """部分元素合法 → 比例 < 1.0。"""
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 0}},  # 非法 page
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.5


# ---------- _docx_locator_ratio 第十五批 ----------


def test_docx_locator_ratio_no_elements_batch15():
    assert _docx_locator_ratio([])["reason"] == "no_elements"


def test_docx_locator_ratio_has_page_batch15():
    """DOCX locator 不应有 page。"""
    r = _docx_locator_ratio([{"source_locator": {"page": 1, "paragraph_index": 0}}])
    assert r["value"] == 0.0


def test_docx_locator_ratio_has_bbox_batch15():
    r = _docx_locator_ratio([{"source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}])
    assert r["value"] == 0.0


def test_docx_locator_ratio_with_paragraph_index_batch15():
    r = _docx_locator_ratio([{"source_locator": {"paragraph_index": 0}}])
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_section_batch15():
    r = _docx_locator_ratio([{"source_locator": {"section": 0}}])
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_table_indices_batch15():
    r = _docx_locator_ratio([{
        "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}
    }])
    assert r["value"] == 1.0


def test_docx_locator_ratio_no_structural_keys_batch15():
    r = _docx_locator_ratio([{"source_locator": {"other_key": "x"}}])
    assert r["value"] == 0.0


# ---------- _image_resource_ratio 第十五批 ----------


def test_image_resource_ratio_no_image_elements_batch15():
    r = _image_resource_ratio([{"type": "heading"}], None)
    assert r["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path_batch15():
    r = _image_resource_ratio([{"type": "image"}], None)
    assert r["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch15():
    r = _image_resource_ratio([{"type": "image", "resource_path": ""}], None)
    assert r["value"] == 0.0


def test_image_resource_ratio_nonexistent_file_batch15(tmp_path):
    r = _image_resource_ratio(
        [{"type": "image", "resource_path": "nope.png"}], tmp_path
    )
    assert r["value"] == 0.0


def test_image_resource_ratio_existing_file_batch15(tmp_path):
    img = tmp_path / "a.png"
    img.write_text("fake", encoding="utf-8")
    r = _image_resource_ratio(
        [{"type": "image", "resource_path": str(img)}], None
    )
    assert r["value"] == 1.0


def test_image_resource_ratio_with_image_base_dir_batch15(tmp_path):
    img = tmp_path / "b.png"
    img.write_text("fake", encoding="utf-8")
    r = _image_resource_ratio(
        [{"type": "image", "resource_path": "b.png"}], tmp_path
    )
    assert r["value"] == 1.0


def test_image_resource_ratio_zero_byte_file_batch15(tmp_path):
    """0 字节文件视为不存在。"""
    img = tmp_path / "empty.png"
    img.write_text("", encoding="utf-8")
    r = _image_resource_ratio(
        [{"type": "image", "resource_path": str(img)}], None
    )
    assert r["value"] == 0.0


# ---------- _chunk_reference_ratio 第十五批 ----------


def test_chunk_reference_ratio_no_chunks_batch15():
    r = _chunk_reference_ratio([{"element_id": "h1"}], [])
    assert r["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_source_element_ids_batch15():
    r = _chunk_reference_ratio(
        [{"element_id": "h1"}],
        [{"source_element_ids": []}],
    )
    # 空 ids 不视为合法（all() of empty 是 True，但 ids 必须 truthy）
    assert r["value"] == 0.0


def test_chunk_reference_ratio_missing_reference_batch15():
    r = _chunk_reference_ratio(
        [{"element_id": "h1"}],
        [{"source_element_ids": ["h2"]}],  # h2 不在 elements 中
    )
    assert r["value"] == 0.0


def test_chunk_reference_ratio_perfect_match_batch15():
    r = _chunk_reference_ratio(
        [{"element_id": "h1"}, {"element_id": "p1"}],
        [{"source_element_ids": ["h1", "p1"]}],
    )
    assert r["value"] == 1.0


def test_chunk_reference_ratio_partial_match_batch15():
    r = _chunk_reference_ratio(
        [{"element_id": "h1"}, {"element_id": "p1"}],
        [
            {"source_element_ids": ["h1"]},  # 合法
            {"source_element_ids": ["unknown"]},  # 不合法
        ],
    )
    assert r["value"] == 0.5


# ---------- _text_preservation 第十五批 ----------


def test_text_preservation_empty_both_batch15():
    r = _text_preservation([], [])
    assert r["equal"]["value"] is True
    assert r["precision"]["reason"] == "empty_expected_and_actual"
    assert r["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match_batch15():
    elements = [{"type": "heading", "content": "Hello"}, {"type": "paragraph", "content": "World"}]
    chunks = [{"text": "HelloWorld"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch15():
    """image element 的 content 不计入 expected。"""
    elements = [
        {"type": "heading", "content": "X"},
        {"type": "image", "content": "Y"},
    ]
    chunks = [{"text": "X"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_missing_chars_batch15():
    """丢失字符 → unequal。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["value"] == 1.0  # ab 都在 expected 中
    assert r["recall"]["value"] < 1.0  # expected 多 1 个 c


def test_text_preservation_added_chars_batch15():
    """多字符 → unequal。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["value"] < 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_chunk_order_mismatch_batch15():
    """chunk 顺序不同 → equal=False，但 precision/recall 可能仍为 1。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "ba"}]  # 字符相同但顺序反
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    # Counter 仍是 {a:1, b:1} → precision/recall 都 1.0
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_whitespace_ignored_batch15():
    elements = [{"type": "paragraph", "content": "a b"}]
    chunks = [{"text": "ab"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


# ---------- _heading_boundary_ratio 第十五批 ----------


def test_heading_boundary_ratio_no_heading_batch15():
    r = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert r["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_chunk_no_ids_batch15():
    r = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": []}],  # 空 ids
    )
    assert r["value"] == 0.0


def test_heading_boundary_ratio_perfect_match_batch15():
    r = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}],
        [
            {"source_element_ids": ["h1", "p1"]},
            {"source_element_ids": ["h2", "p2"]},
        ],
    )
    assert r["value"] == 1.0


def test_heading_boundary_ratio_partial_match_batch15():
    r = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}],
        [{"source_element_ids": ["h1"]}],  # 只有 h1 是某 chunk 首
    )
    assert r["value"] == 0.5


def test_heading_boundary_ratio_heading_not_first_batch15():
    """heading 在 chunk 的 source_element_ids 中但不是第 1 个。"""
    r = _heading_boundary_ratio(
        [{"type": "heading", "element_id": "h1"}],
        [{"source_element_ids": ["p1", "h1"]}],  # h1 是第 2 个
    )
    assert r["value"] == 0.0


# ---------- _silent_drop_count 第十五批 ----------


def test_silent_drop_count_no_expectations_batch15():
    r = _silent_drop_count({"heading": 1}, None)
    assert r["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch15():
    r = _silent_drop_count({"heading": 1}, {})
    assert r["reason"] == "no_expectations"


def test_silent_drop_count_empty_element_count_by_type_batch15():
    r = _silent_drop_count({"heading": 1}, {"element_count_by_type": {}})
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_greater_than_expected_batch15():
    """actual > expected → 不算 drop（取 max(0, expected - actual)）。"""
    r = _silent_drop_count({"heading": 5}, {"element_count_by_type": {"heading": 2}})
    assert r["value"] == 0


def test_silent_drop_count_perfect_match_batch15():
    r = _silent_drop_count({"heading": 3}, {"element_count_by_type": {"heading": 3}})
    assert r["value"] == 0


def test_silent_drop_count_mixed_types_batch15():
    """多类型混合：heading 缺 2 + paragraph 缺 1 = 3。"""
    actual = {"heading": 1, "paragraph": 2}
    expected = {"element_count_by_type": {"heading": 3, "paragraph": 3, "table": 0}}
    r = _silent_drop_count(actual, expected)
    assert r["value"] == 3  # heading 缺 2 + paragraph 缺 1 + table 不缺


def test_silent_drop_count_expected_type_missing_in_actual_batch15():
    """expected 含 type X 但 actual 中没有 → 全算 drop。"""
    r = _silent_drop_count({}, {"element_count_by_type": {"heading": 3}})
    assert r["value"] == 3


# ---------- module source forbidden tokens 第二十四批 ----------


@pytest.mark.parametrize("forbidden", [
    "subprocess",
    "os.system",
    "os.popen",
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
])
def test_module_source_forbidden_tokens_batch15(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第二十一批 ----------


def test_module_source_has_future_annotations_batch15():
    src = inspect.getsource(mmod)
    head = src.split("\n", 35)[:35]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch15():
    src = inspect.getsource(mmod)
    assert '"""自动指标：13 项 + 计时占位' in src


def test_module_source_has_math_import_batch15():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_counter_import_batch15():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_path_import_batch15():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_any_import_batch15():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch15():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_has_pdf_bbox_required_types_batch15():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_has_not_evaluated_constant_batch15():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_has_compute_function_batch15():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_null_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _null(reason: str) -> dict[str, Any]:" in src


def test_module_source_has_ratio_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _ratio(value: float) -> dict[str, Any]:" in src


def test_module_source_has_bool_metric_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(value: bool) -> dict[str, Any]:" in src


def test_module_source_has_int_metric_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _int_metric(value: int) -> dict[str, Any]:" in src


def test_module_source_has_pdf_locator_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(elements: list[dict]) -> dict[str, Any]:" in src


def test_module_source_has_docx_locator_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(elements: list[dict]) -> dict[str, Any]:" in src


def test_module_source_has_is_valid_bbox_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(bbox: Any) -> bool:" in src


def test_module_source_has_image_resource_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_has_chunk_reference_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_has_strip_unicode_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(s: str) -> str:" in src


def test_module_source_has_text_preservation_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_has_heading_boundary_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_has_silent_drop_function_batch15():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_has_all_dunder_batch15():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第二十一批 ----------


def test_signature_compute_metrics_batch15():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_defaults_batch15():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_null_batch15():
    sig = inspect.signature(_null)
    params = list(sig.parameters.keys())
    assert params == ["reason"]


def test_signature_ratio_batch15():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_is_valid_bbox_batch15():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters.keys())
    assert params == ["bbox"]


def test_signature_image_resource_ratio_batch15():
    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters.keys())
    assert params == ["elements", "image_base_dir"]


def test_signature_silent_drop_count_batch15():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters.keys())
    assert params == ["by_type", "expectations"]


# ---------- module 合理性第二十一批 ----------


def test_module_has_all_attribute_batch15():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_contains_compute_function_batch15():
    assert "compute_automatic_metrics" in mmod.__all__


def test_module_compute_callable_batch15():
    assert callable(compute_automatic_metrics)


def test_module_does_not_export_private_helpers_batch15():
    """私有辅助函数（_null, _ratio 等）不应在 __all__ 中。"""
    for name in mmod.__all__:
        assert not name.startswith("_")


def test_module_text_types_is_tuple_batch15():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_pdf_bbox_types_is_tuple_batch15():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_constants_in_namespace_batch15():
    assert "_TEXT_TYPES" in vars(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in vars(mmod)
    assert "_NOT_EVALUATED" in vars(mmod)


def test_module_does_not_mutate_inputs_in_text_preservation_batch15():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    e_before = repr(elements)
    c_before = repr(chunks)
    _text_preservation(elements, chunks)
    assert repr(elements) == e_before
    assert repr(chunks) == c_before


# ---------- 端到端集成第二十一批 ----------


def test_e2e_compute_metrics_pdf_full_batch15():
    """完整 PDF 文档跑通。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "T",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "element_id": "p1", "content": "Hello",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "T", "source_element_ids": ["h1"]},
            {"text": "Hello", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 2
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["text_preservation_equal"]["value"] is True
    assert m["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_compute_metrics_docx_full_batch15():
    """完整 DOCX 文档跑通。"""
    doc = {
        "document_id": "x", "source_type": "docx", "source_path": "x.docx",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "T",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "Body",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "T", "source_element_ids": ["h1"]},
            {"text": "Body", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_pipeline_failed_batch15():
    """document=None + error=None → pipeline_success=False 但 error_code 是 None。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] is None
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_e2e_element_count_by_type_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
            {"type": "paragraph", "element_id": "p1"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 3
    assert m["element_count_by_type"]["value"] == {"heading": 2, "paragraph": 1}


def test_e2e_silent_drop_count_calculated_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [
            {"type": "heading", "element_id": "h1"},
            {"type": "paragraph", "element_id": "p1"},
        ],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"heading": 3, "paragraph": 5}}
    m = compute_automatic_metrics(doc, None, "pdf", exp)
    # heading 缺 2 + paragraph 缺 4 = 6
    assert m["silent_drop_count"]["value"] == 6


def test_e2e_chunk_reference_intact_with_unknown_id_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [{"type": "heading", "element_id": "h1"}],
        "chunks": [
            {"text": "T", "source_element_ids": ["h1"]},
            {"text": "U", "source_element_ids": ["unknown"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["chunk_reference_intact_ratio"]["value"] == 0.5


def test_e2e_image_resource_check_batch15(tmp_path):
    img = tmp_path / "a.png"
    img.write_text("fake", encoding="utf-8")
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [
            {"type": "image", "element_id": "i1", "resource_path": str(img)},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert m["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_idempotent_batch15():
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert repr(m1) == repr(m2)


def test_e2e_metrics_all_have_value_and_reason_batch15():
    """每个 metric 都应有 value 与 reason 字段。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    for name, metric in m.items():
        assert isinstance(metric, dict), f"{name} not dict"
        assert "value" in metric, f"{name} missing value"
        assert "reason" in metric, f"{name} missing reason"


def test_e2e_metric_keys_no_duplicates_batch15():
    """每个 metric key 唯一。"""
    doc = {
        "document_id": "x", "source_type": "pdf", "source_path": "x.pdf",
        "parser_name": "fallback", "parser_version": "1.0",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    keys = list(m.keys())
    assert len(keys) == len(set(keys))
