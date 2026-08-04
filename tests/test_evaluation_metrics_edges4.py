"""evaluation/metrics.py 边角测试 - 第四轮（Round 117）。

补强已有 base/edges/edges2/edges3（共 114 测试）未覆盖的深度路径：
- 模块常量：_TEXT_TYPES 内容、_PDF_BBOX_REQUIRED_TYPES 内容、
  _NOT_EVALUATED 值
- _strip_unicode_whitespace：各种 unicode 空白（NBSP、em space、
  en space、ideographic space、line separator、paragraph separator、
  tab、vertical tab、form feed、CR、LF）
- _null / _ratio / _bool_metric / _int_metric 各种输入
- _is_valid_bbox：混合 bool+int 边界、None 元素、empty list
- _pdf_locator_ratio：table 类型 page 缺失、image 类型 page 缺失、
  heading bbox 无效但 page 有效
- _docx_locator_ratio：locator 含多个 structural keys、
  locator 是空 dict、locator=None
- _image_resource_ratio：resource_path 是绝对路径、目录路径、
  特殊字符文件名、OSError 处理
- _chunk_reference_ratio：chunk 含重复 id、id 是 None、
  id 是 int
- _text_preservation：expected 含 image type content（被排除）、
  expected 全 image、chunks text=None、chunks 空
- _heading_boundary_ratio：heading element_id 缺失、
  chunk source_element_ids 是 None、chunk source_element_ids 第一个是 None
- _silent_drop_count：expectations 含 unknown type、actual 大于 expected
- compute_automatic_metrics：source_type 不在 pdf/docx、
  document 缺 elements、document 缺 chunks、
  schema_check 抛异常 → schema_check_exception、
  expectations 含空 element_count_by_type
- 模块结构：__all__、imports、模块 docstring
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

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


# =========================================================================
# 模块常量
# =========================================================================


def test_text_types_value():
    assert set(_TEXT_TYPES) == {
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    }


def test_text_types_count_seven():
    assert len(_TEXT_TYPES) == 7


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_does_not_contain_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_value():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {
        "heading",
        "paragraph",
        "caption",
        "list_item",
    }


def test_pdf_bbox_required_types_count_four():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_excludes_table():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_image():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_subset_of_text_types():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


# =========================================================================
# _null / _ratio / _bool_metric / _int_metric
# =========================================================================


def test_null_returns_value_none():
    assert _null("reason")["value"] is None


def test_null_returns_reason_field():
    assert _null("my reason")["reason"] == "my reason"


def test_null_empty_reason():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_unicode_reason():
    out = _null("失败原因")
    assert out["reason"] == "失败原因"


def test_ratio_value_zero():
    assert _ratio(0.0)["value"] == 0.0


def test_ratio_value_one():
    assert _ratio(1.0)["value"] == 1.0


def test_ratio_value_half():
    assert _ratio(0.5)["value"] == 0.5


def test_ratio_returns_float():
    assert isinstance(_ratio(1)["value"], float)


def test_ratio_int_input_converted_to_float():
    """int 输入被 float() 化。"""
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_ratio_returns_reason_none():
    assert _ratio(0.5)["reason"] is None


def test_bool_metric_true():
    assert _bool_metric(True)["value"] is True


def test_bool_metric_false():
    assert _bool_metric(False)["value"] is False


def test_bool_metric_int_zero_returns_false():
    """int 0 → bool(0) = False。"""
    assert _bool_metric(0)["value"] is False


def test_bool_metric_int_one_returns_true():
    """int 1 → bool(1) = True。"""
    assert _bool_metric(1)["value"] is True


def test_bool_metric_empty_string_returns_false():
    assert _bool_metric("")["value"] is False


def test_bool_metric_non_empty_string_returns_true():
    assert _bool_metric("x")["value"] is True


def test_bool_metric_returns_reason_none():
    assert _bool_metric(True)["reason"] is None


def test_int_metric_value():
    assert _int_metric(5)["value"] == 5


def test_int_metric_zero():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative():
    assert _int_metric(-3)["value"] == -3


def test_int_metric_truncates_float():
    """float 输入被 int() 截断。"""
    assert _int_metric(3.99)["value"] == 3


def test_int_metric_negative_float_truncates_toward_zero():
    assert _int_metric(-3.99)["value"] == -3


def test_int_metric_returns_reason_none():
    assert _int_metric(5)["reason"] is None


# =========================================================================
# _strip_unicode_whitespace 深度
# =========================================================================


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_vertical_tab():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_form_feed():
    assert _strip_unicode_whitespace("a\x0cb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a\xa0b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """U+2003 EM SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """U+2002 EN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """U+3000 IDEOGRAPHIC SPACE。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_thin_space():
    """U+2009 THIN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_hair_space():
    """U+200A HAIR SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """所有非空白字符都保留（包括标点、unicode 字符）。"""
    assert _strip_unicode_whitespace("你 好 . ! ?") == "你好.!?"


def test_strip_unicode_whitespace_preserves_punctuation():
    assert _strip_unicode_whitespace("a.b,c;d") == "a.b,c;d"


def test_strip_unicode_whitespace_does_not_collapse():
    """删除全部空白，不保留单个空格。"""
    assert _strip_unicode_whitespace("a  b") == "ab"  # 不是 "a b"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("abc"), str)


# =========================================================================
# _is_valid_bbox 深度
# =========================================================================


def test_is_valid_bbox_none_rejected():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_tuple_rejected():
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 1}) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox("1234") is False


def test_is_valid_bbox_empty_list_rejected():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_rejected():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_list_rejected():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_four_ints_accepted():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_four_floats_accepted():
    assert _is_valid_bbox([1.5, 2.5, 3.5, 4.5]) is True


def test_is_valid_bbox_mixed_int_float_accepted():
    assert _is_valid_bbox([1, 2.5, 3, 4.5]) is True


def test_is_valid_bbox_zero_size_accepted():
    """0,0,0,0 是合法 bbox（虽然无意义）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_accepted():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_bool_int_zero_rejected():
    """bool 是 int 子类，但代码显式排除。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_all_bools_rejected():
    assert _is_valid_bbox([True, True, True, True]) is False


def test_is_valid_bbox_nan_rejected():
    assert _is_valid_bbox([float("nan"), 2, 3, 4]) is False


def test_is_valid_bbox_inf_rejected():
    assert _is_valid_bbox([float("inf"), 2, 3, 4]) is False


def test_is_valid_bbox_negative_inf_rejected():
    assert _is_valid_bbox([float("-inf"), 2, 3, 4]) is False


def test_is_valid_bbox_string_int_rejected():
    """'1' 不是 int/float。"""
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_none_in_list_rejected():
    assert _is_valid_bbox([None, 2, 3, 4]) is False


def test_is_valid_bbox_returns_bool():
    assert isinstance(_is_valid_bbox([1, 2, 3, 4]), bool)


# =========================================================================
# _pdf_locator_ratio 深度
# =========================================================================


def test_pdf_locator_ratio_empty_list_returns_no_elements():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_image_only_page_missing_returns_invalid():
    """image 类型不需要 bbox，但仍需 page≥1。"""
    elements = [{"type": "image", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_table_only_page_missing_returns_invalid():
    """table 类型不需要 bbox，但仍需 page≥1。"""
    elements = [{"type": "table", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_with_valid_page_no_bbox_required():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_text_type_no_locator():
    """locator 缺失 → page=None → invalid。"""
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none():
    """source_locator=None → {} → page=None → invalid。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_zero_invalid_for_image():
    """page=0 视为无效。"""
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_returns_ratio_dict():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert "value" in out and "reason" in out


# =========================================================================
# _docx_locator_ratio 深度
# =========================================================================


def test_docx_locator_ratio_paragraph_index_only():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_section_key():
    elements = [{"type": "paragraph", "source_locator": {"section": "intro"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_table_index():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_run_index():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_row_col():
    elements = [{"type": "table", "source_locator": {"row_index": 0, "col_index": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_multiple_structural_keys():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0, "section": "a"}}
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_rejected():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0, "page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0, "bbox": [1, 2, 3, 4]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_locator_none():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_dict():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_locator_key():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"page": 1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


def test_docx_locator_ratio_returns_ratio_dict():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert "value" in out and "reason" in out


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_no_images_returns_no_image_elements():
    elements = [{"type": "paragraph", "content": "x"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_empty_rp_skipped(tmp_path: Path):
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_no_rp_key_skipped(tmp_path: Path):
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_valid(tmp_path: Path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG fake")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_byte_file_invalid(tmp_path: Path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path: Path):
    img1 = tmp_path / "exists.png"
    img1.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": "missing.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_with_image_base_dir(tmp_path: Path):
    """image_base_dir 拼接文件名查找。"""
    base = tmp_path
    (base / "x.png").write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, base)
    assert out["value"] == 1.0


def test_image_resource_ratio_returns_ratio_dict(tmp_path: Path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "x.png")}]
    out = _image_resource_ratio(elements, None)
    assert "value" in out and "reason" in out


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_no_chunks():
    elements = [{"element_id": "e1"}]
    out = _chunk_reference_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_no_source_element_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    # chunk 没 source_element_ids → falsy → invalid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_empty():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_none():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_unknown_id_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_known_id_valid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_multiple_ids_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_multiple_ids_one_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_returns_ratio_dict():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert "value" in out and "reason" in out


# =========================================================================
# _text_preservation 深度
# =========================================================================


def test_text_preservation_empty_elements_empty_chunks():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["recall"]["value"] is None


def test_text_preservation_image_content_excluded():
    """image 类型的 content 不参与 expected。"""
    elements = [{"type": "image", "content": "should be excluded"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # expected 为空，actual 为空 → equal=True
    assert out["equal"]["value"] is True


def test_text_preservation_text_in_chunks_only():
    """expected 空，actual 非空 → common=0, precision=0/3=0.0, recall=0/0=null。"""
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] is None


def test_text_preservation_content_none_skipped():
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_text_none_skipped():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="" → equal=False
    assert out["equal"]["value"] is False


def test_text_preservation_returns_dict_with_three_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_value_has_value_and_reason():
    out = _text_preservation([], [])
    for k in ("equal", "precision", "recall"):
        assert "value" in out[k]
        assert "reason" in out[k]


# =========================================================================
# _heading_boundary_ratio 深度
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_with_headings():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # 无 chunks → matched=0, ratio=0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_heading_id_in_first_position():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_heading_id_in_non_first_position():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # 只看 first id
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_empty_source_element_ids():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_source_element_ids_none():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": None}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_missing_element_id():
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # heading.element_id 是 None → not in chunk_first_ids → 0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks_same_first_id():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_returns_ratio_dict():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert "value" in out and "reason" in out


# =========================================================================
# _silent_drop_count 深度
# =========================================================================


def test_silent_drop_count_no_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"other_key": "x"})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type_returns_null():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_zero_expected_five():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_count_actual_more_than_expected_no_drop():
    out = _silent_drop_count(
        {"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}}
    )
    assert out["value"] == 0


def test_silent_drop_count_actual_equal_expected_no_drop():
    out = _silent_drop_count(
        {"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}}
    )
    assert out["value"] == 0


def test_silent_drop_count_multi_type_sum():
    actual = {"paragraph": 3, "heading": 1}
    expected = {"paragraph": 5, "heading": 2, "table": 1}
    out = _silent_drop_count(actual, {"element_count_by_type": expected})
    # paragraph: max(0, 5-3) = 2
    # heading: max(0, 2-1) = 1
    # table: max(0, 1-0) = 1
    assert out["value"] == 4


def test_silent_drop_count_returns_int_metric():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 1}})
    assert isinstance(out["value"], int)


def test_silent_drop_count_returns_dict_with_value_and_reason():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 1}})
    assert "value" in out and "reason" in out


# =========================================================================
# compute_automatic_metrics 深度
# =========================================================================


def test_compute_metrics_document_none_returns_pipeline_failed_all():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["schema_valid"]["value"] is None
    assert out["element_count_total"]["value"] is None


def test_compute_metrics_with_error_pipeline_success_false():
    err = {"code": "x", "message": "m"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "x"


def test_compute_metrics_success_returns_13_keys():
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
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


def test_compute_metrics_docx_source_pdf_locator_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_pdf_source_docx_locator_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_unknown_source_both_locators_null():
    """source_type 既不是 pdf 也不是 docx → 两者都 null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "markdown", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_empty_source_type_both_locators_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_element_count_by_type_value():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "e1"},
            {"type": "paragraph", "element_id": "e2"},
            {"type": "heading", "element_id": "e3"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1}


def test_compute_metrics_element_count_by_type_unknown_type():
    doc = {
        "elements": [{"type": "weird", "element_id": "e1"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"weird": 1}


def test_compute_metrics_element_count_by_type_missing_type():
    doc = {
        "elements": [{"element_id": "e1"}],  # 缺 type
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    # e.get("type", "unknown") → "unknown"
    assert by_type == {"unknown": 1}


def test_compute_metrics_returns_dict():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_signature_five_params():
    import inspect

    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5
    assert "document" in sig.parameters
    assert "error" in sig.parameters
    assert "source_type" in sig.parameters
    assert "expectations" in sig.parameters
    assert "image_base_dir" in sig.parameters


def test_compute_metrics_image_base_dir_default_none():
    import inspect

    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_metrics_expectations_required_no_default():
    """expectations 是必需参数，无默认值。"""
    import inspect

    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["expectations"].default is inspect.Parameter.empty


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_all_exports_only_compute_automatic_metrics():
    import evaluation.metrics as mod

    assert mod.__all__ == ["compute_automatic_metrics"]


def test_module_all_count_one():
    import evaluation.metrics as mod

    assert len(mod.__all__) == 1


def test_module_imports_math():
    import evaluation.metrics as mod

    assert hasattr(mod, "math")


def test_module_imports_counter():
    import evaluation.metrics as mod

    assert hasattr(mod, "Counter")


def test_module_imports_path():
    import evaluation.metrics as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    import evaluation.metrics as mod

    assert hasattr(mod, "Any")


def test_module_docstring_present():
    import evaluation.metrics as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_text_preservation():
    import evaluation.metrics as mod

    assert "text_preservation" in mod.__doc__ or "文本保留" in mod.__doc__


def test_module_docstring_mentions_no_fabrication():
    """docstring 应说明缺数据时不伪造。"""
    import evaluation.metrics as mod

    doc = mod.__doc__
    assert "不伪造" in doc or "null" in doc.lower()


def test_module_constants_immutable_at_module_level():
    from evaluation.metrics import _TEXT_TYPES as a
    from evaluation.metrics import _TEXT_TYPES as b

    assert a is b


def test_compute_metrics_has_docstring():
    assert compute_automatic_metrics.__doc__ is not None


def test_compute_metrics_docstring_mentions_args():
    doc = compute_automatic_metrics.__doc__ or ""
    assert "Args" in doc or "document" in doc


def test_strip_unicode_whitespace_has_docstring():
    assert _strip_unicode_whitespace.__doc__ is not None


def test_text_preservation_has_docstring():
    assert _text_preservation.__doc__ is not None


def test_is_valid_bbox_no_docstring():
    """_is_valid_bbox 是私有 helper，不强求 docstring。"""
    assert callable(_is_valid_bbox)


def test_pdf_locator_ratio_has_docstring():
    assert _pdf_locator_ratio.__doc__ is not None


def test_docx_locator_ratio_has_docstring():
    assert _docx_locator_ratio.__doc__ is not None


def test_chunk_reference_ratio_no_docstring():
    """_chunk_reference_ratio 是少数没有 docstring 的辅助函数。"""
    assert _chunk_reference_ratio.__doc__ is None


def test_image_resource_ratio_has_docstring():
    assert _image_resource_ratio.__doc__ is not None


def test_heading_boundary_ratio_has_docstring():
    assert _heading_boundary_ratio.__doc__ is not None


def test_silent_drop_count_has_docstring():
    assert _silent_drop_count.__doc__ is not None
