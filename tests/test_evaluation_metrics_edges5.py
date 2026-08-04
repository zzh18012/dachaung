r"""evaluation/metrics.py 边角测试 - 第五轮（Round 132）。

补强已有 base/edges/edges2/edges3/edges4（共 624 测试）未覆盖的深度路径：
- _null / _ratio / _bool_metric / _int_metric 深度：
  - 返回 dict 结构与值
  - 各类型断言
  - 默认 reason
- _strip_unicode_whitespace 深度：
  - 各种 Unicode 空白（NBSP/em/en space/ideographic space/line separator 等）
  - 混合空白
  - 不删除非空白
- _is_valid_bbox 深度：
  - 4 元素 list
  - int / float / bool / NaN / Inf
  - 长度边界
- _pdf_locator_ratio 深度：
  - 空 elements
  - page 缺失 / 0 / 负数 / 字符串
  - bbox 缺失 / 退化 / NaN
- _docx_locator_ratio 深度：
  - 空 elements
  - 含 page/bbox 的元素拒
  - 各种 structural_keys
- _image_resource_ratio 深度：
  - 无 image
  - resource_path 缺失
  - 文件不存在
  - 0 size 文件
- _chunk_reference_ratio 深度：
  - 空 chunks
  - chunk 无 source_element_ids
  - 部分匹配
- _text_preservation 深度：
  - 空 elements / chunks
  - 字符顺序
  - 重复字符
- _heading_boundary_ratio 深度：
  - 无 heading
  - 多 heading
- _silent_drop_count 深度：
  - 无 expectations
  - 多 type 求和
  - 负数不出现
- compute_automatic_metrics 综合
- 模块结构 / 签名
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from typing import Any

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
# _null / _ratio / _bool_metric / _int_metric 深度
# =========================================================================


def test_null_returns_dict_with_two_keys():
    result = _null("reason")
    assert set(result.keys()) == {"value", "reason"}


def test_null_value_is_none():
    assert _null("x")["value"] is None


def test_null_reason_is_argument():
    assert _null("my_reason")["reason"] == "my_reason"


def test_null_signature_one_param():
    sig = inspect.signature(_null)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "reason" in params


def test_null_return_annotation_dict():
    sig = inspect.signature(_null)
    ret = sig.return_annotation
    assert "dict" in str(ret).lower()


def test_ratio_returns_dict_with_two_keys():
    result = _ratio(0.5)
    assert set(result.keys()) == {"value", "reason"}


def test_ratio_value_is_float():
    assert isinstance(_ratio(0.5)["value"], float)


def test_ratio_value_preserved():
    assert _ratio(0.7)["value"] == 0.7


def test_ratio_reason_is_none():
    assert _ratio(0.5)["reason"] is None


def test_ratio_zero_value():
    assert _ratio(0.0)["value"] == 0.0


def test_ratio_one_value():
    assert _ratio(1.0)["value"] == 1.0


def test_ratio_int_input_converted_to_float():
    result = _ratio(1)
    assert isinstance(result["value"], float)


def test_ratio_signature_one_param():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "value" in params


def test_bool_metric_returns_dict_with_two_keys():
    result = _bool_metric(True)
    assert set(result.keys()) == {"value", "reason"}


def test_bool_metric_value_is_bool():
    assert isinstance(_bool_metric(True)["value"], bool)


def test_bool_metric_true():
    assert _bool_metric(True)["value"] is True


def test_bool_metric_false():
    assert _bool_metric(False)["value"] is False


def test_bool_metric_reason_is_none():
    assert _bool_metric(True)["reason"] is None


def test_bool_metric_int_input_converted():
    """int 1 → bool True。"""
    result = _bool_metric(1)
    assert result["value"] is True


def test_bool_metric_signature_one_param():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "value" in params


def test_int_metric_returns_dict_with_two_keys():
    result = _int_metric(5)
    assert set(result.keys()) == {"value", "reason"}


def test_int_metric_value_is_int():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_value_preserved():
    assert _int_metric(42)["value"] == 42


def test_int_metric_reason_is_none():
    assert _int_metric(0)["reason"] is None


def test_int_metric_zero():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_float_input_converted():
    """float → int（截断）。"""
    result = _int_metric(3.9)
    assert isinstance(result["value"], int)
    assert result["value"] == 3


def test_int_metric_signature_one_param():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "value" in params


# =========================================================================
# _strip_unicode_whitespace 深度
# =========================================================================


def test_strip_unicode_whitespace_signature_one_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "s" in params


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_ascii_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ascii_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_ascii_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_ascii_carriage_return():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_ascii_form_feed():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_ascii_vertical_tab():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_nbsp():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a\xa0b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """U+2003 EM SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """U+2002 EN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_thin_space():
    """U+2009 THIN SPACE。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """U+3000 IDEOGRAPHIC SPACE（中文全角空格）。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_only_whitespace_returns_empty():
    assert _strip_unicode_whitespace("   \t\n\xa0　") == ""


def test_strip_unicode_whitespace_mixed():
    # 删除全部空白（含中间），保留所有非空白字符
    assert _strip_unicode_whitespace(" a\tb\xc1\n d ") == "ab\xc1d"


def test_strip_unicode_whitespace_preserves_punctuation():
    assert _strip_unicode_whitespace("a, b. c!") == "a,b.c!"


def test_strip_unicode_whitespace_preserves_unicode_chars():
    assert _strip_unicode_whitespace("中文 测试") == "中文测试"


def test_strip_unicode_whitespace_preserves_emoji():
    assert _strip_unicode_whitespace("a 🎉 b") == "a🎉b"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("x"), str)


def test_strip_unicode_whitespace_idempotent():
    text = "hello world"
    once = _strip_unicode_whitespace(text)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


# =========================================================================
# _is_valid_bbox 深度
# =========================================================================


def test_is_valid_bbox_signature_one_param():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "bbox" in params


def test_is_valid_bbox_returns_bool():
    assert isinstance(_is_valid_bbox([0, 0, 100, 100]), bool)


def test_is_valid_bbox_four_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_four_floats():
    assert _is_valid_bbox([0.0, 0.5, 100.5, 200.0]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.5, 100, 200.5]) is True


def test_is_valid_bbox_negative_values():
    assert _is_valid_bbox([-10, -10, 100, 100]) is True


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_three_elements():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_five_elements():
    assert _is_valid_bbox([0, 0, 100, 100, 50]) is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string():
    assert _is_valid_bbox("not a list") is False


def test_is_valid_bbox_dict():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_tuple():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_bool_in_list():
    """bool 是 int 子类，但函数显式拒绝。"""
    assert _is_valid_bbox([True, 0, 100, 100]) is False


def test_is_valid_bbox_all_bools():
    assert _is_valid_bbox([True, False, True, False]) is False


def test_is_valid_bbox_string_element():
    assert _is_valid_bbox([0, 0, "100", 100]) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([0, 0, None, 100]) is False


def test_is_valid_bbox_nan():
    assert _is_valid_bbox([0, 0, float("nan"), 100]) is False


def test_is_valid_bbox_inf():
    assert _is_valid_bbox([0, 0, float("inf"), 100]) is False


def test_is_valid_bbox_neg_inf():
    assert _is_valid_bbox([0, 0, float("-inf"), 100]) is False


def test_is_valid_bbox_zero_bbox():
    """全 0 bbox 合法（数值上有效）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_huge_values():
    assert _is_valid_bbox([1e10, 1e10, 2e10, 2e10]) is True


# =========================================================================
# _pdf_locator_ratio 深度
# =========================================================================


def test_pdf_locator_ratio_empty_returns_null():
    result = _pdf_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid_page_only():
    """非文本类型只需 page≥1。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1}},
        {"type": "image", "source_locator": {"page": 2}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_text_requires_bbox():
    """文本类型还需要 bbox。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox → invalid
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_text_with_valid_bbox():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        }
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_no_locator_invalid():
    elements = [{"type": "image"}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_locator_none_invalid():
    elements = [{"type": "image", "source_locator": None}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {"type": "image", "source_locator": {"page": 0}},  # invalid
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.5


def test_pdf_locator_ratio_returns_dict_with_value_reason():
    result = _pdf_locator_ratio([])
    assert "value" in result
    assert "reason" in result


# =========================================================================
# _docx_locator_ratio 深度
# =========================================================================


def test_docx_locator_ratio_empty_returns_null():
    result = _docx_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_docx_locator_ratio_with_paragraph_index():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_table_index():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_section():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_rejects_page():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_rejects_bbox():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_rejects_no_structural_key():
    elements = [{"type": "paragraph", "source_locator": {"random_key": "x"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_locator():
    elements = [{"type": "paragraph"}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_mixed():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.5


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_no_images_returns_null():
    elements = [{"type": "paragraph"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_empty_list_returns_null():
    result = _image_resource_ratio([], None)
    assert result["value"] is None


def test_image_resource_ratio_image_no_resource_path():
    elements = [{"type": "image"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_image_empty_resource_path():
    elements = [{"type": "image", "resource_path": ""}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_existing_file(tmp_path: Path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"fake png")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_missing_file(tmp_path: Path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "missing.png")}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_zero_size_file(tmp_path: Path):
    """0 size 文件视为不存在。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_with_image_base_dir(tmp_path: Path):
    """resource_path 是文件名，配合 image_base_dir 找到。"""
    base = tmp_path
    img_file = base / "img.png"
    img_file.write_bytes(b"png")
    elements = [{"type": "image", "resource_path": "img.png"}]
    result = _image_resource_ratio(elements, base)
    assert result["value"] == 1.0


def test_image_resource_ratio_half_existing(tmp_path: Path):
    img1 = tmp_path / "img1.png"
    img1.write_bytes(b"png")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.5


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_null():
    elements = [{"element_id": "e1"}]
    result = _chunk_reference_ratio(elements, [])
    assert result["value"] is None
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_chunk_no_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunk_ids_none():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_ids_key():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_invalid_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_half_valid():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["missing"]},  # invalid
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.5


# =========================================================================
# _text_preservation 深度
# =========================================================================


def test_text_preservation_returns_dict_with_three_keys():
    result = _text_preservation([], [])
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_empty_both_returns_null_metrics():
    result = _text_preservation([], [])
    assert result["equal"]["value"] is True  # 空对空，相等
    assert result["precision"]["value"] is None
    assert result["recall"]["value"] is None


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_whitespace_only_diff():
    """空白差异不影响 equal（v1.1 口径）。"""
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "helloworld"}]  # 删了空格
    result = _text_preservation(elements, chunks)
    # 删除空白后两者都是 "helloworld"
    assert result["equal"]["value"] is True


def test_text_preservation_missing_char_in_chunks():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # common=2, |actual|=2, |expected|=3
    assert result["precision"]["value"] == 1.0
    assert abs(result["recall"]["value"] - 2 / 3) < 1e-9


def test_text_preservation_extra_char_in_chunks():
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # common=2, |actual|=3, |expected|=2
    assert abs(result["precision"]["value"] - 2 / 3) < 1e-9
    assert result["recall"]["value"] == 1.0


def test_text_preservation_image_excluded():
    """image element 的 content 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "hello"},
        {"type": "image", "content": "image data"},
    ]
    chunks = [{"text": "hello"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_order_matters_for_equal():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "acb"}]
    result = _text_preservation(elements, chunks)
    # 顺序不同 → equal False，但 precision/recall = 1.0（多集合相同）
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_repeated_chars():
    """重复字符在多集合中保留。"""
    elements = [{"type": "paragraph", "content": "aab"}]
    chunks = [{"text": "ab"}]
    result = _text_preservation(elements, chunks)
    # expected: {a:2, b:1}, actual: {a:1, b:1}
    # common = min(2,1)+min(1,1) = 1+1 = 2
    # precision = 2/2 = 1.0, recall = 2/3
    assert abs(result["precision"]["value"] - 1.0) < 1e-9
    assert abs(result["recall"]["value"] - 2 / 3) < 1e-9


def test_text_preservation_chunk_text_none():
    """chunk.text=None 视为空。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    result = _text_preservation(elements, chunks)
    # actual = ""
    assert result["precision"]["value"] is None
    assert result["recall"]["value"] == 0.0


def test_text_preservation_chunk_missing_text_key():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] is None


def test_text_preservation_element_content_none():
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    result = _text_preservation(elements, chunks)
    # 都为空 → equal True, precision/recall null
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] is None


# =========================================================================
# _heading_boundary_ratio 深度
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] is None
    assert result["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_heading_at_chunk_start():
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"source_element_ids": ["h1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_heading_not_at_chunk_start():
    """heading 不是任何 chunk 的首元素 → 0.0。"""
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_no_chunks_at_all():
    elements = [{"element_id": "h1", "type": "heading"}]
    chunks = []
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_half_matched():
    elements = [
        {"element_id": "h1", "type": "heading"},
        {"element_id": "h2", "type": "heading"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只匹配 h1
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.5


# =========================================================================
# _silent_drop_count 深度
# =========================================================================


def test_silent_drop_count_no_expectations_returns_null():
    result = _silent_drop_count({}, None)
    assert result["value"] is None
    assert result["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    result = _silent_drop_count({}, {})
    assert result["value"] is None


def test_silent_drop_count_no_element_count_by_type_returns_null():
    result = _silent_drop_count({}, {"other_key": "x"})
    assert result["value"] is None
    assert result["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type_returns_null():
    result = _silent_drop_count({}, {"element_count_by_type": {}})
    assert result["value"] is None


def test_silent_drop_count_no_drop_when_actual_matches():
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, exp)
    assert result["value"] == 0


def test_silent_drop_count_drop_when_actual_below():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, exp)
    assert result["value"] == 2


def test_silent_drop_count_no_negative_when_actual_above():
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, exp)
    assert result["value"] == 0


def test_silent_drop_count_multi_type_sum():
    by_type = {"paragraph": 3, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    # drop = (5-3) + (2-1) = 2 + 1 = 3
    result = _silent_drop_count(by_type, exp)
    assert result["value"] == 3


def test_silent_drop_count_expected_type_missing_in_actual():
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, exp)
    assert result["value"] == 5


def test_silent_drop_count_returns_int():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, exp)
    assert isinstance(result["value"], int)


# =========================================================================
# compute_automatic_metrics 综合
# =========================================================================


def test_compute_metrics_signature_five_params():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert len(params) == 5
    assert "document" in params
    assert "error" in params
    assert "source_type" in params
    assert "expectations" in params
    assert "image_base_dir" in params


def test_compute_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_metrics_expectations_required():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["expectations"].default is inspect.Parameter.empty


def test_compute_metrics_return_annotation_dict():
    sig = inspect.signature(compute_automatic_metrics)
    ret = sig.return_annotation
    assert "dict" in str(ret).lower()


def test_compute_metrics_document_none_all_pipeline_failed():
    result = compute_automatic_metrics(
        document=None, error={"code": "fail"}, source_type="pdf", expectations=None
    )
    assert result["pipeline_success"]["value"] is False
    assert result["error_code"]["value"] == "fail"
    assert result["schema_valid"]["value"] is None  # pipeline_failed


def test_compute_metrics_document_none_14_keys():
    result = compute_automatic_metrics(
        document=None, error=None, source_type="pdf", expectations=None
    )
    # pipeline_success, error_code, schema_valid + 11 个 null 指标 = 14
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
    assert set(result.keys()) == expected_keys
    assert len(result) == 14


def test_compute_metrics_minimal_document_success():
    """最小合法 document → pipeline_success True。"""
    document = {
        "elements": [],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert result["pipeline_success"]["value"] is True
    assert result["error_code"]["value"] is None


def test_compute_metrics_minimal_document_has_13_keys():
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    # 13 个 metric key
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(result.keys()) == expected_keys


def test_compute_metrics_pdf_source_docx_locator_null():
    """pdf 文档：docx_locator_valid_ratio = null。"""
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert result["docx_locator_valid_ratio"]["value"] is None


def test_compute_metrics_docx_source_pdf_locator_null():
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="docx", expectations=None
    )
    assert result["pdf_locator_valid_ratio"]["value"] is None


def test_compute_metrics_unknown_source_both_locators_null():
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="unknown", expectations=None
    )
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["value"] is None


def test_compute_metrics_empty_source_both_locators_null():
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="", expectations=None
    )
    assert result["pdf_locator_valid_ratio"]["value"] is None
    assert result["docx_locator_valid_ratio"]["value"] is None


def test_compute_metrics_element_count_total_value():
    document = {
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert result["element_count_total"]["value"] == 2


def test_compute_metrics_element_count_by_type_value():
    document = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert result["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


def test_compute_metrics_no_expectations_silent_drop_null():
    document = {"elements": [], "chunks": []}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=None
    )
    assert result["silent_drop_count"]["value"] is None


def test_compute_metrics_with_expectations_silent_drop_value():
    document = {"elements": [{"type": "paragraph"}], "chunks": []}
    exp = {"element_count_by_type": {"paragraph": 5}}
    result = compute_automatic_metrics(
        document=document, error=None, source_type="pdf", expectations=exp
    )
    assert result["silent_drop_count"]["value"] == 4  # 5-1


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_math():
    from evaluation import metrics as mod
    assert hasattr(mod, "math")


def test_module_imports_counter():
    from evaluation import metrics as mod
    assert hasattr(mod, "Counter")


def test_module_imports_path():
    from evaluation import metrics as mod
    assert hasattr(mod, "Path")


def test_module_imports_any():
    from evaluation import metrics as mod
    assert hasattr(mod, "Any")


def test_module_has_text_types_constant():
    from evaluation import metrics as mod
    assert hasattr(mod, "_TEXT_TYPES")


def test_module_text_types_exact():
    from evaluation import metrics as mod
    assert set(mod._TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table", "caption", "header", "footer"
    }


def test_module_text_types_excludes_image():
    from evaluation import metrics as mod
    assert "image" not in mod._TEXT_TYPES


def test_module_pdf_bbox_required_types_constant():
    from evaluation import metrics as mod
    assert hasattr(mod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_pdf_bbox_required_types_exact():
    from evaluation import metrics as mod
    assert set(mod._PDF_BBOX_REQUIRED_TYPES) == {
        "heading", "paragraph", "caption", "list_item"
    }


def test_module_pdf_bbox_required_types_excludes_table_image():
    from evaluation import metrics as mod
    assert "table" not in mod._PDF_BBOX_REQUIRED_TYPES
    assert "image" not in mod._PDF_BBOX_REQUIRED_TYPES


def test_module_not_evaluated_constant():
    from evaluation import metrics as mod
    assert hasattr(mod, "_NOT_EVALUATED")
    assert mod._NOT_EVALUATED == "not_evaluated"


def test_module_has_compute_automatic_metrics():
    from evaluation import metrics as mod
    assert hasattr(mod, "compute_automatic_metrics")


def test_module_has_helpers():
    from evaluation import metrics as mod
    assert hasattr(mod, "_null")
    assert hasattr(mod, "_ratio")
    assert hasattr(mod, "_bool_metric")
    assert hasattr(mod, "_int_metric")
    assert hasattr(mod, "_strip_unicode_whitespace")
    assert hasattr(mod, "_is_valid_bbox")
    assert hasattr(mod, "_pdf_locator_ratio")
    assert hasattr(mod, "_docx_locator_ratio")
    assert hasattr(mod, "_image_resource_ratio")
    assert hasattr(mod, "_chunk_reference_ratio")
    assert hasattr(mod, "_text_preservation")
    assert hasattr(mod, "_heading_boundary_ratio")
    assert hasattr(mod, "_silent_drop_count")


def test_module_all_is_list():
    from evaluation import metrics as mod
    assert isinstance(mod.__all__, list)


def test_module_all_length_one():
    from evaluation import metrics as mod
    assert len(mod.__all__) == 1


def test_module_all_only_compute_automatic_metrics():
    from evaluation import metrics as mod
    assert set(mod.__all__) == {"compute_automatic_metrics"}


def test_module_all_excludes_internal():
    from evaluation import metrics as mod
    for item in mod.__all__:
        assert not item.startswith("_")


def test_module_docstring_present():
    from evaluation import metrics as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_text_preservation():
    from evaluation import metrics as mod
    doc = mod.__doc__
    assert "text_preservation" in doc.lower() or "文本保留" in doc


def test_module_docstring_mentions_no_fabrication():
    from evaluation import metrics as mod
    doc = mod.__doc__
    assert "伪造" in doc or "fabrication" in doc.lower()


def test_module_docstring_mentions_pipeline_failed():
    from evaluation import metrics as mod
    doc = mod.__doc__
    assert "pipeline_failed" in doc or "失败" in doc


def test_module_uses_future_annotations():
    import ast
    from evaluation import metrics as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 各 helper 签名深度
# =========================================================================


def test_pdf_locator_ratio_signature_one_param():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "elements" in params


def test_docx_locator_ratio_signature_one_param():
    sig = inspect.signature(_docx_locator_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 1
    assert "elements" in params


def test_image_resource_ratio_signature_two_params():
    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "elements" in params
    assert "image_base_dir" in params


def test_chunk_reference_ratio_signature_two_params():
    sig = inspect.signature(_chunk_reference_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "elements" in params
    assert "chunks" in params


def test_text_preservation_signature_two_params():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "elements" in params
    assert "chunks" in params


def test_heading_boundary_ratio_signature_two_params():
    sig = inspect.signature(_heading_boundary_ratio)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "elements" in params
    assert "chunks" in params


def test_silent_drop_count_signature_two_params():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters.keys())
    assert len(params) == 2
    assert "by_type" in params
    assert "expectations" in params
