"""evaluation/metrics.py 第三十轮 edges 测试（Round 340）。

重点补强 edges28 未触及的角度：
- _ratio/_null/_bool_metric/_int_metric 数学边界第五批
- _text_preservation 边界第二批（precision/recall 计算 / equal 与 precision 不一致 / Counter 多集）
- _pdf_locator_ratio 边界第二批（page=0/负数/非 int/bbox 异常类型组合）
- _docx_locator_ratio 边界第二批（locator 含 page / bbox / structural keys 各种组合）
- _image_resource_ratio 边界第二批（resource_path None/空 / 文件 size=0 / 多 candidate）
- _chunk_reference_ratio 边界第二批（重复 id / 部分 valid / 全 invalid）
- _heading_boundary_ratio 边界第二批（多 chunks/多 headings / chunk 无 ids）
- _silent_drop_count 边界第二批（多类型 partial / actual>expected / expectations 缺 key）
- module source forbidden tokens 第五批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import math
import types
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _bool_metric,
    _chunk_reference_ratio,
    compute_automatic_metrics,
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
)


# ---------- _ratio/_null/_bool_metric/_int_metric 数学边界第五批 ----------


def test_ratio_returns_dict_with_value_and_reason():
    out = _ratio(0.5)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_value_is_float():
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_ratio_reason_is_none():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_ratio_with_int_input_converts_to_float():
    out = _ratio(1)
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_ratio_with_zero_returns_zero():
    out = _ratio(0)
    assert out["value"] == 0.0


def test_ratio_with_very_small_negative():
    out = _ratio(-0.0001)
    assert out["value"] == -0.0001


def test_ratio_with_numeric_string_works():
    """float("0.5")=0.5 不抛异常。"""
    out = _ratio("0.5")  # type: ignore[arg-type]
    assert out["value"] == 0.5


def test_ratio_with_none_input_raises():
    with pytest.raises((TypeError, AttributeError)):
        _ratio(None)  # type: ignore[arg-type]


def test_null_returns_value_none():
    out = _null("reason")
    assert out["value"] is None


def test_null_returns_reason_str():
    out = _null("reason")
    assert out["reason"] == "reason"


def test_null_with_unicode_reason():
    out = _null("无元素")
    assert out["reason"] == "无元素"


def test_null_with_multiline_reason():
    out = _null("line1\nline2")
    assert "\n" in out["reason"]


def test_null_with_emoji_reason():
    out = _null("🚨")
    assert out["reason"] == "🚨"


def test_bool_metric_value_is_bool():
    out = _bool_metric(1)
    assert isinstance(out["value"], bool)


def test_bool_metric_with_int_0_returns_false():
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_with_int_1_returns_true():
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_with_string_returns_true():
    """bool('yes') = True（非空字符串）。"""
    out = _bool_metric("yes")  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_with_empty_string_returns_false():
    """bool("") = False。"""
    out = _bool_metric("")  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_non_empty_string_returns_true():
    out = _bool_metric("x")  # type: ignore[arg-type]
    assert out["value"] is True


def test_int_metric_value_is_int():
    out = _int_metric(3.7)
    assert isinstance(out["value"], int)
    assert out["value"] == 3


def test_int_metric_with_negative_float():
    out = _int_metric(-2.99)
    assert out["value"] == -2


def test_int_metric_with_numeric_string_works():
    """int('5')=5（Python 自动转换）。"""
    out = _int_metric("5")  # type: ignore[arg-type]
    assert out["value"] == 5


def test_int_metric_with_bool_true_returns_1():
    """bool 是 int 子类；int(True)=1。"""
    out = _int_metric(True)
    assert out["value"] == 1


def test_int_metric_with_bool_false_returns_0():
    out = _int_metric(False)
    assert out["value"] == 0


# ---------- _text_preservation 边界第二批 ----------


def test_text_preservation_perfect_match_returns_true_and_1():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_completely_different_returns_false():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "xyz"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_partial_match_actual_subset_of_expected():
    """actual = "abc", expected = "abcdef" → precision=1, recall=0.5。"""
    elements = [{"type": "paragraph", "content": "abcdef"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5


def test_text_preservation_partial_match_actual_superset_of_expected():
    """actual = "abcdef", expected = "abc" → precision=0.5, recall=1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcdef"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == pytest.approx(0.5)
    assert out["recall"]["value"] == 1.0


def test_text_preservation_with_image_excluded():
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "ignored"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_only_images_expected_empty():
    elements = [{"type": "image", "content": "img"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected = "" (all images), actual = "abc"
    assert out["equal"]["value"] is False
    # precision: actual=""? no, actual="abc" → c_actual=Counter({'a':1,'b':1,'c':1})
    # recall: expected="" → c_expected=Counter() → empty_expected
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_no_chunks_actual_empty():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="" → precision null empty_actual, recall 0.0
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_both_empty_returns_empty_expected_and_actual():
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"
    assert out["equal"]["value"] is True  # "" == ""


def test_text_preservation_with_whitespace_only():
    """expected = "   ", actual = "" → strip 后都为空 → empty_expected_and_actual。"""
    elements = [{"type": "paragraph", "content": "   "}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True  # "" == ""
    # 都空 → empty_expected_and_actual
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_with_duplicates():
    """expected = "aabbcc", actual = "abcabc" → equal=False, 但 multiset 相同。"""
    elements = [{"type": "paragraph", "content": "aabbcc"}]
    chunks = [{"text": "abcabc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_returns_3_keys():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{"text": "x"}]
    out = _text_preservation(elements, chunks)
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_does_not_modify_inputs():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    elem_before = repr(elements)
    chunk_before = repr(chunks)
    _text_preservation(elements, chunks)
    assert repr(elements) == elem_before
    assert repr(chunks) == chunk_before


def test_text_preservation_with_many_chunks():
    elements = [{"type": "paragraph", "content": "abcdef"}]
    chunks = [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]
    out = _text_preservation(elements, chunks)
    # expected="abcdef", actual="abcdef"
    assert out["equal"]["value"] is True


# ---------- _pdf_locator_ratio 边界第二批 ----------


def test_pdf_locator_page_zero_not_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_not_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_float_not_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1.5, "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_string_not_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": "1", "bbox": [0.0, 0.0, 1.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_type_missing_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # missing bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_type_with_short_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_image_does_not_need_bbox():
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # image 不需要 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_no_locator_dict():
    elements = [
        {"type": "paragraph"},  # no source_locator
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_locator_none():
    elements = [
        {"type": "paragraph", "source_locator": None},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0.0, 0.0, 1.0, 1.0]}},
        {"type": "image", "source_locator": {"page": 2}},
    ]
    out = _pdf_locator_ratio(elements)
    # 2/3 valid
    assert out["value"] == pytest.approx(2 / 3)


def test_pdf_locator_no_elements_returns_null():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


# ---------- _docx_locator_ratio 边界第二批 ----------


def test_docx_locator_with_paragraph_index_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_section_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"section": "intro"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_relationship_id_valid():
    elements = [
        {"type": "image", "source_locator": {"relationship_id": "rId1"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_page_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    # 含 page → 不合法
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_no_structural_keys_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"unknown_key": "value"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_empty_locator_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_locator_none_treated_as_empty():
    elements = [
        {"type": "paragraph", "source_locator": None},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_no_locator_key():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "image", "source_locator": {"relationship_id": "rId1"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == pytest.approx(2 / 3)


def test_docx_locator_table_indices_valid():
    elements = [
        {"type": "table", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_run_index_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"run_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_no_elements_returns_null():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


# ---------- _image_resource_ratio 边界第二批 ----------


def test_image_resource_with_no_resource_path(tmp_path):
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, tmp_path)
    # images exist but no resource_path → valid=0
    assert out["value"] == 0.0


def test_image_resource_with_empty_resource_path(tmp_path):
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_with_none_resource_path(tmp_path):
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_with_existing_file(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data with length")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_with_size_zero_file(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_with_nonexistent_file(tmp_path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "no.png")}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_with_image_base_dir_filename_only(tmp_path):
    """resource_path 只写文件名，image_base_dir 拼接。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data with length")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_with_image_base_dir_absolute_path(tmp_path):
    """resource_path 是绝对路径，image_base_dir 不影响（candidates 含两个）。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data with length")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    # 第一个 candidate 是绝对路径，命中
    assert out["value"] == 1.0


def test_image_resource_no_image_elements_returns_null(tmp_path):
    elements = [{"type": "paragraph", "content": "x"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_mixed_valid_invalid(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data with length")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "nonexistent.png"},
        {"type": "image"},  # no resource_path
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == pytest.approx(1 / 3)


def test_image_resource_with_directory_instead_of_file(tmp_path):
    """resource_path 是目录，is_file() False。"""
    elements = [{"type": "image", "resource_path": str(tmp_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 边界第二批 ----------


def test_chunk_reference_with_valid_ids():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_with_unknown_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_with_some_unknown_id_partial():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["unknown"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_with_duplicate_id_in_one_chunk():
    """重复 id 但都 valid 仍视为 valid（all 满足）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_with_empty_ids_in_chunk():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids 空 → falsy → not valid
    assert out["value"] == 0.0


def test_chunk_reference_with_source_element_ids_none():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_with_missing_source_element_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # no source_element_ids key
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_no_chunks_returns_null():
    elements = [{"element_id": "e1"}]
    out = _chunk_reference_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_element_without_id():
    elements = [{}]  # no element_id
    chunks = [{"source_element_ids": ["anything"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # element_id None → set has None
    # 'anything' not in {None} → invalid
    assert out["value"] == 0.0


def test_chunk_reference_no_elements():
    elements = []
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # elem_ids = {None}, 'e1' not in → 0
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 边界第二批 ----------


def test_heading_boundary_no_headings_returns_null():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_perfect_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_no_chunk_starts_with_heading():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_partial_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # only h1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_chunk_with_empty_ids():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids 为空，matched=0
    assert out["value"] == 0.0


def test_heading_boundary_chunk_with_missing_ids_key():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_heading_no_element_id():
    elements = [{"type": "heading"}]  # no element_id
    chunks = [{"source_element_ids": ["anything"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h.get("element_id") None, not in chunk_first_ids
    assert out["value"] == 0.0


def test_heading_boundary_heading_id_appears_in_later_position():
    """heading 必须是 chunk 的第一个 source_element_id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 在第二位
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids = {"p1"}, h1 不在
    assert out["value"] == 0.0


def test_heading_boundary_multiple_chunks_with_same_first_id_dedup():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},  # 重复
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # 1 heading matched, len(headings)=1 → 1.0
    assert out["value"] == 1.0


def test_heading_boundary_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids 空 → matched=0 → 0.0
    assert out["value"] == 0.0


# ---------- _silent_drop_count 边界第二批 ----------


def test_silent_drop_no_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None


def test_silent_drop_no_element_count_by_type_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"other_key": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_empty_element_count_by_type_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None


def test_silent_drop_actual_equals_expected_returns_0():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_actual_greater_than_expected_returns_0():
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    # max(0, 5-10) = 0
    assert out["value"] == 0


def test_silent_drop_partial_drop_sums():
    by_type = {"paragraph": 3, "heading": 2}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 4}}
    out = _silent_drop_count(by_type, expectations)
    # (5-3) + (4-2) = 4
    assert out["value"] == 4


def test_silent_drop_expected_type_missing_in_actual():
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    # actual.get("paragraph", 0) = 0, 0 < 5 → drop 5
    assert out["value"] == 5


def test_silent_drop_extra_type_in_actual_ignored():
    by_type = {"paragraph": 5, "image": 100}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    # only paragraph checked; image ignored
    assert out["value"] == 0


def test_silent_drop_returns_int():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert isinstance(out["value"], int)


def test_silent_drop_does_not_modify_inputs():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    by_before = repr(by_type)
    exp_before = repr(expectations)
    _silent_drop_count(by_type, expectations)
    assert repr(by_type) == by_before
    assert repr(expectations) == exp_before


# ---------- _strip_unicode_whitespace 数学边界第五批 ----------


def test_strip_unicode_whitespace_with_form_feed_only():
    assert _strip_unicode_whitespace("\x0c") == ""


def test_strip_unicode_whitespace_with_nbsp():
    """NBSP   isspace() True。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_with_em_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_with_en_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_with_ideographic_space():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_with_line_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_with_paragraph_separator():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_chinese():
    assert _strip_unicode_whitespace("你好 世界") == "你好世界"


def test_strip_unicode_whitespace_preserves_digits():
    assert _strip_unicode_whitespace("a 1 b") == "a1b"


def test_strip_unicode_whitespace_preserves_punctuation():
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("x"), str)


# ---------- _is_valid_bbox 数学边界补强 ----------


def test_is_valid_bbox_with_4_floats():
    assert _is_valid_bbox([0.0, 0.0, 1.0, 1.0]) is True


def test_is_valid_bbox_with_4_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_with_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 1, 1.0]) is True


def test_is_valid_bbox_with_3_elements():
    assert _is_valid_bbox([0.0, 0.0, 1.0]) is False


def test_is_valid_bbox_with_5_elements():
    assert _is_valid_bbox([0.0, 0.0, 1.0, 1.0, 1.0]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([0.0, 0.0, 1.0, float("nan")]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([0.0, 0.0, 1.0, float("inf")]) is False


def test_is_valid_bbox_with_negative_inf():
    assert _is_valid_bbox([0.0, 0.0, 1.0, float("-inf")]) is False


def test_is_valid_bbox_with_negative_values():
    """负值是有限数，仍然 valid。"""
    assert _is_valid_bbox([-1.0, -1.0, 1.0, 1.0]) is True


def test_is_valid_bbox_returns_bool():
    assert isinstance(_is_valid_bbox([0.0, 0.0, 1.0, 1.0]), bool)


def test_is_valid_bbox_with_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_with_dict():
    assert _is_valid_bbox({}) is False


def test_is_valid_bbox_with_tuple():
    """非 list 都 False（即使内容合法）。"""
    assert _is_valid_bbox((0.0, 0.0, 1.0, 1.0)) is False


def test_is_valid_bbox_with_string():
    assert _is_valid_bbox("abc") is False


def test_is_valid_bbox_with_bool_in_list():
    """True 是 int 子类但显式拒绝。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_with_string_in_list():
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_with_none_in_list():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


# ---------- module source forbidden tokens 第五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "argparse", "asdl", "asyncio",
        "audioop", "base64", "binascii", "binhex", "calendar",
        "concurrent", "contextlib", "copyreg", "crypt",
        "curses", "datetime", "dl", "docxml",
        "dummy_threading", "email", "encodings", "ensurepip",
        "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath",
        "gensui", "getopt", "getpass", "gettext",
        "glob", "gopherlib", "heapq", "html",
        "http", "imaplib", "ihooks", "imghdr",
        "importlib", "inspect", "ipaddress", "itertools",
        "keyword", "linecache", "locale", "logging",
        "lzma", "mailbox", "mailcap", "markupbase",
        "md5", "mhlib", "mimetypes", "mimify",
        "mmap", "msilib", "multifile", "multiprocessing",
        "mutex", "netrc", "nis", "nntplib",
        "numbers", "opcode", "operator", "optparse",
        "os2emxpath", "parser", "pdb", "pickle",
        "pickletools", "pipes", "pkgutil", "platform",
        "plistlib", "poplib", "posixfile", "posixpath",
        "profile", "pstats", "pty", "pyclbr",
        "py_compile", "pydoc", "queue", "quopri",
        "random", "readline", "reprlib", "rexec",
        "rfc822", "rlcompleter", "robotparser", "runpy",
        "sched", "secrets", "select", "sets",
        "sgmlop", "sgmllib", "sha", "shelve",
        "shlex", "shutil", "signal", "site",
        "smtplib", "smtpd", "sndhdr", "socket",
        "socketserver", "spawn", "spwd", "sqlite3",
        "ssl", "stat", "stringprep", "struct",
        "subprocess", "sunau", "sunaudio", "symtable",
        "sys", "sysconfig", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "threading",
        "time", "timeit", "tomllib", "token",
        "tokenize", "trace", "traceback", "tracemalloc",
        "tty", "turtle", "types", "unicodedata",
        "unittest", "urllib", "urllib2", "urlparse",
        "user", "userdict", "userlist", "usersite",
        "uuid", "venv", "warnings", "wave",
        "weakref", "webbrowser", "whichdb", "wsgiref",
        "xdrlib", "xml", "xmlrpc", "zipapp",
        "zipfile", "zipimport", "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_fifth_batch(token):
    """这些 stdlib 模块不应出现在 metrics.py。"""
    src = inspect.getsource(mmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_math():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_imports_counter():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_imports_path():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_defines_text_types():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src
    assert '"heading"' in src
    assert '"paragraph"' in src
    assert '"list_item"' in src
    assert '"table"' in src
    assert '"caption"' in src
    assert '"header"' in src
    assert '"footer"' in src


def test_module_source_defines_pdf_bbox_required_types():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_defines_not_evaluated_constant():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(mmod)
    assert "async " not in src


def test_module_source_no_global():
    src = inspect.getsource(mmod)
    assert "global " not in src


def test_module_source_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_source_no_class():
    src = inspect.getsource(mmod)
    body_lines = [l for l in src.splitlines() if not l.strip().startswith(("#", '"', "'"))]
    body = "\n".join(body_lines)
    assert "\nclass " not in body


def test_module_source_no_decorators():
    src = inspect.getsource(mmod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_no_lambda():
    src = inspect.getsource(mmod)
    assert "lambda " not in src


def test_module_source_has_all_with_1_entry():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


def test_module_source_compute_automatic_metrics_has_5_params():
    src = inspect.getsource(compute_automatic_metrics)
    assert "document" in src
    assert "error" in src
    assert "source_type" in src
    assert "expectations" in src
    assert "image_base_dir" in src


def test_module_source_compute_automatic_metrics_lazy_imports_schema_validation():
    """延迟 import 避免循环依赖。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_module_source_compute_automatic_metrics_returns_dict_with_13_keys():
    """成功路径返回 13 个 metric + error_code + schema_valid + pipeline_success。"""
    src = inspect.getsource(compute_automatic_metrics)
    # 主路径会 set 这些 key
    expected_keys = [
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
    ]
    for k in expected_keys:
        assert f'"{k}"' in src, f"missing metric key {k} in source"


def test_module_source_text_preservation_uses_strip_unicode_whitespace():
    src = inspect.getsource(_text_preservation)
    assert "_strip_unicode_whitespace(expected_raw)" in src
    assert "_strip_unicode_whitespace(actual_raw)" in src


def test_module_source_text_preservation_uses_counter():
    src = inspect.getsource(_text_preservation)
    assert "Counter(expected)" in src
    assert "Counter(actual)" in src


def test_module_source_text_preservation_uses_intersection():
    src = inspect.getsource(_text_preservation)
    assert "c_expected & c_actual" in src


def test_module_source_pdf_locator_uses_isinstance():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src
    assert "page < 1" in src


def test_module_source_pdf_locator_uses_pdf_bbox_required_types():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_pdf_locator_uses_is_valid_bbox():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_is_valid_bbox(bbox)" in src


def test_module_source_docx_locator_uses_structural_keys_tuple():
    src = inspect.getsource(_docx_locator_ratio)
    assert "structural_keys" in src
    assert '"section"' in src
    assert '"paragraph_index"' in src
    assert '"run_index"' in src
    assert '"table_index"' in src
    assert '"row_index"' in src
    assert '"col_index"' in src
    assert '"relationship_id"' in src


def test_module_source_docx_locator_uses_any():
    src = inspect.getsource(_docx_locator_ratio)
    assert "any(k in loc for k in structural_keys)" in src


def test_module_source_image_resource_uses_path():
    src = inspect.getsource(_image_resource_ratio)
    assert "Path(rp)" in src


def test_module_source_image_resource_uses_isfile_and_stat():
    src = inspect.getsource(_image_resource_ratio)
    assert "p.is_file()" in src
    assert "p.stat().st_size" in src


def test_module_source_image_resource_uses_image_base_dir():
    src = inspect.getsource(_image_resource_ratio)
    assert "image_base_dir" in src


def test_module_source_chunk_reference_uses_set_comprehension():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "{e.get(\"element_id\") for e in elements}" in src


def test_module_source_chunk_reference_uses_all():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "all(sid in elem_ids for sid in ids)" in src


def test_module_source_heading_boundary_uses_set_add():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids = set()" in src
    assert "chunk_first_ids.add(ids[0])" in src


def test_module_source_silent_drop_uses_max_zero_pattern():
    """silent_drop 用 if actual < exp 而非 max(0, ...)。"""
    src = inspect.getsource(_silent_drop_count)
    assert "if actual < exp:" in src
    assert "drops += (exp - actual)" in src


def test_module_source_silent_drop_iterates_items():
    src = inspect.getsource(_silent_drop_count)
    assert ".items()" in src


def test_module_source_strip_unicode_whitespace_uses_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "ch.isspace()" in src


# ---------- signatures 精确补强 ----------


def test_compute_automatic_metrics_signature_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_compute_automatic_metrics_no_varargs_varkw():
    sig = inspect.signature(compute_automatic_metrics)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_pdf_locator_ratio_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_docx_locator_ratio_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_image_resource_ratio_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_chunk_reference_ratio_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_text_preservation_2_params():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_heading_boundary_ratio_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_strip_unicode_whitespace_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_null_1_param():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_ratio_1_param():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_bool_metric_1_param():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_int_metric_1_param():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_no_varargs_varkw_in_any_helper():
    helpers = [
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
        _strip_unicode_whitespace,
        _is_valid_bbox,
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
    ]
    for fn in helpers:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(mmod, types.ModuleType)


def test_module_namespace_name():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_has_1_entry():
    assert len(mmod.__all__) == 1


def test_module_all_only_compute_automatic_metrics():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_has_1_public_function():
    public = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == mmod.__name__
        and not v.__name__.startswith("_")
    ]
    assert len(public) == 1
    assert public[0].__name__ == "compute_automatic_metrics"


def test_module_has_13_private_functions():
    private = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == mmod.__name__
        and v.__name__.startswith("_")
        and not v.__name__.startswith("__")
    ]
    assert len(private) == 13


def test_module_has_3_constants():
    """_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED。"""
    src = inspect.getsource(mmod)
    const_count = sum(
        1 for line in src.splitlines()
        if line.startswith("_TEXT_TYPES =")
        or line.startswith("_PDF_BBOX_REQUIRED_TYPES =")
        or line.startswith("_NOT_EVALUATED =")
    )
    assert const_count == 3


def test_module_no_class():
    classes = [
        v for v in vars(mmod).values()
        if isinstance(v, type) and v.__module__ == mmod.__name__
    ]
    assert len(classes) == 0


def test_module_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_callable_compute_automatic_metrics():
    assert callable(compute_automatic_metrics)


def test_module_callable_helpers():
    assert callable(_pdf_locator_ratio)
    assert callable(_docx_locator_ratio)
    assert callable(_image_resource_ratio)
    assert callable(_chunk_reference_ratio)
    assert callable(_text_preservation)
    assert callable(_heading_boundary_ratio)
    assert callable(_silent_drop_count)
    assert callable(_strip_unicode_whitespace)
    assert callable(_is_valid_bbox)
    assert callable(_null)
    assert callable(_ratio)
    assert callable(_bool_metric)
    assert callable(_int_metric)


# ---------- 端到端集成补强 ----------


def test_e2e_compute_metrics_minimal_pdf():
    doc = {
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 0


def test_e2e_compute_metrics_with_error():
    error = {"code": "parse_failed"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"


def test_e2e_compute_metrics_with_expectations_no_drop():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=expectations
    )
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_compute_metrics_with_expectations_with_drop():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=expectations
    )
    # 5-1=4 drop
    assert out["silent_drop_count"]["value"] == 4


def test_e2e_compute_metrics_docx_with_no_text_elements():
    doc = {
        "elements": [{"type": "image", "element_id": "e1"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    # all images → expected empty
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_pdf_with_valid_locators():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "element_id": "e1",
                "content": "x",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 1.0, 1.0]},
            },
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_docx_with_invalid_locator_has_page():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "element_id": "e1",
                "content": "x",
                "source_locator": {"page": 1, "paragraph_index": 0},
            },
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 0.0


def test_e2e_compute_metrics_does_not_modify_document():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    before = repr(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert repr(doc) == before


def test_e2e_compute_metrics_returns_dict_with_14_keys():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 14 metric keys
    assert len(out) == 14


def test_e2e_compute_metrics_keys_exact():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
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


def test_e2e_compute_metrics_deterministic():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_compute_metrics_with_unicode_content():
    doc = {
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "你好世界"}],
        "chunks": [{"text": "你好世界", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0


def test_e2e_compute_metrics_image_resource_with_existing_file(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG fake data with length")
    doc = {
        "elements": [
            {"type": "image", "element_id": "e1", "resource_path": str(img)},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_returns_json_serializable():
    import json
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_compute_metrics_each_metric_value_is_dict_with_2_keys():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    for k, v in out.items():
        if k == "element_count_by_type":
            # value 是 dict，但仍是 {value, reason} 结构
            assert isinstance(v, dict)
            assert set(v.keys()) == {"value", "reason"}
            continue
        assert isinstance(v, dict)
        assert set(v.keys()) == {"value", "reason"}
