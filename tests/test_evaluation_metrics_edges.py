"""evaluation/metrics.py 边角测试（Round 64）。

补强 tests/test_metrics.py（90+ 测试）未覆盖的：
- 模块常量 _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 深度
- _null / _ratio / _bool_metric / _int_metric 边角（None/falsy/truthy）
- _pdf_locator_ratio table/image 不需 bbox / 多类型混合
- _docx_locator_ratio 多 structural key / page+bbox 同时存在
- _is_valid_bbox 负数 / mixed int+float
- _image_resource_ratio image_base_dir 拼接 / relative path
- _chunk_reference_ratio 重复 source_id / source_id 缺失
- _strip_unicode_whitespace 保留非空白 / 多种 Unicode whitespace
- _text_preservation 单 chunk equal / precision/recall with repeats
- _heading_boundary_ratio 单 chunk 多 heading
- _silent_drop_count 各 type overfed 不减 / actual == expected
- compute_automatic_metrics schema exception / metrics key 完整集
"""

from __future__ import annotations

from pathlib import Path

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


# ---------- 模块常量 ----------


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_includes_common_text_types():
    """_TEXT_TYPES 应含 heading/paragraph/list_item/table/caption/header/footer。"""
    for t in ("heading", "paragraph", "list_item", "table", "caption", "header", "footer"):
        assert t in _TEXT_TYPES


def test_text_types_excludes_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_subset_of_text_types():
    """所有需 bbox 的类型都属 text_types。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_excludes_table():
    """table 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_image():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_is_string():
    assert isinstance(_NOT_EVALUATED, str)
    assert _NOT_EVALUATED == "not_evaluated"


# ---------- _null helper ----------


def test_null_returns_dict_with_two_keys():
    result = _null("reason")
    assert isinstance(result, dict)
    assert set(result.keys()) == {"value", "reason"}


def test_null_value_is_none():
    assert _null("any")["value"] is None


def test_null_reason_passed_through():
    assert _null("my_reason")["reason"] == "my_reason"


def test_null_with_empty_reason():
    result = _null("")
    assert result["reason"] == ""


def test_null_with_unicode_reason():
    result = _null("中文原因")
    assert result["reason"] == "中文原因"


# ---------- _ratio helper ----------


def test_ratio_returns_dict_with_two_keys():
    result = _ratio(0.5)
    assert set(result.keys()) == {"value", "reason"}


def test_ratio_value_is_float_type():
    assert isinstance(_ratio(0.5)["value"], float)


def test_ratio_int_input_converted_to_float():
    result = _ratio(1)  # type: ignore[arg-type]
    assert isinstance(result["value"], float)
    assert result["value"] == 1.0


def test_ratio_reason_is_none():
    assert _ratio(0.5)["reason"] is None


def test_ratio_zero_value():
    result = _ratio(0.0)
    assert result["value"] == 0.0


def test_ratio_one_value():
    result = _ratio(1.0)
    assert result["value"] == 1.0


def test_ratio_negative_value_accepted():
    """负数也接受（不在 helper 层校验业务范围）。"""
    result = _ratio(-0.5)  # type: ignore[arg-type]
    assert result["value"] == -0.5


# ---------- _bool_metric helper ----------


def test_bool_metric_returns_dict_two_keys():
    result = _bool_metric(True)
    assert set(result.keys()) == {"value", "reason"}


def test_bool_metric_value_is_bool_type():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(False)["value"], bool)


def test_bool_metric_true_value():
    assert _bool_metric(True)["value"] is True


def test_bool_metric_false_value():
    assert _bool_metric(False)["value"] is False


def test_bool_metric_coerces_truthy_int():
    """1 → True（bool() 转换）。"""
    assert _bool_metric(1)["value"] is True  # type: ignore[arg-type]


def test_bool_metric_coerces_falsy_int():
    assert _bool_metric(0)["value"] is False  # type: ignore[arg-type]


def test_bool_metric_coerces_empty_string():
    assert _bool_metric("")["value"] is False  # type: ignore[arg-type]


def test_bool_metric_coerces_non_empty_string():
    assert _bool_metric("x")["value"] is True  # type: ignore[arg-type]


def test_bool_metric_coerces_none_to_false():
    assert _bool_metric(None)["value"] is False  # type: ignore[arg-type]


def test_bool_metric_coerces_empty_list_to_false():
    assert _bool_metric([])["value"] is False  # type: ignore[arg-type]


def test_bool_metric_coerces_non_empty_list_to_true():
    assert _bool_metric([1])["value"] is True  # type: ignore[arg-type]


def test_bool_metric_reason_is_none():
    assert _bool_metric(True)["reason"] is None


# ---------- _int_metric helper ----------


def test_int_metric_returns_dict_two_keys():
    result = _int_metric(5)
    assert set(result.keys()) == {"value", "reason"}


def test_int_metric_value_is_int_type():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_int_input():
    assert _int_metric(42)["value"] == 42


def test_int_metric_zero_value():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative_value():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_coerces_float_to_int():
    """float → int (truncation)。"""
    assert _int_metric(3.7)["value"] == 3  # type: ignore[arg-type]


def test_int_metric_coerces_bool_to_int():
    """bool 是 int 子类 → True=1, False=0。"""
    assert _int_metric(True)["value"] == 1  # type: ignore[arg-type]
    assert _int_metric(False)["value"] == 0  # type: ignore[arg-type]


def test_int_metric_reason_is_none():
    assert _int_metric(5)["reason"] is None


# ---------- _pdf_locator_ratio 边角 ----------


def test_pdf_locator_ratio_empty_returns_null_no_elements():
    result = _pdf_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_pdf_locator_ratio_table_type_does_not_require_bbox():
    """table 类型只需 page，不需 bbox。"""
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # 无 bbox
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_image_type_does_not_require_bbox():
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_heading_requires_bbox():
    """heading 类型必须 page + bbox。"""
    elements = [
        {"type": "heading", "source_locator": {"page": 1}},  # 无 bbox
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "heading", "source_locator": {"page": 1}},  # invalid (no bbox)
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},  # valid
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 2 / 3


def test_pdf_locator_ratio_page_zero_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": 0}},  # page=0 invalid
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": -1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_none_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": None}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_returns_dict_with_two_keys():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    result = _pdf_locator_ratio(elements)
    assert set(result.keys()) == {"value", "reason"}


def test_pdf_locator_ratio_missing_source_locator():
    """source_locator 缺失 → 当 {} 处理 → page 缺 → invalid。"""
    elements = [{"type": "table"}]  # 无 source_locator
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


# ---------- _docx_locator_ratio 边角 ----------


def test_docx_locator_ratio_empty_returns_null():
    result = _docx_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_docx_locator_ratio_with_paragraph_index_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_section_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 0}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_table_index_valid():
    elements = [
        {"type": "table", "source_locator": {"table_index": 0}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_with_relationship_id_valid():
    elements = [
        {"type": "image", "source_locator": {"relationship_id": "rId1"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_page_key_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0, "page": 1}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_bbox_key_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0, "bbox": [1, 2, 3, 4]}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_structural_key_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"unknown_key": "value"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_missing_source_locator_invalid():
    elements = [{"type": "paragraph"}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},  # valid
        {"type": "paragraph", "source_locator": {"unknown_key": "x"}},  # invalid
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.5


# ---------- _is_valid_bbox 边角 ----------


def test_is_valid_bbox_returns_bool_type():
    assert isinstance(_is_valid_bbox([1, 2, 3, 4]), bool)


def test_is_valid_bbox_accepts_four_ints():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_accepts_four_floats():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_accepts_mixed_int_float():
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_rejects_bool():
    """bool 是 int 子类但应被拒绝。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False
    assert _is_valid_bbox([1, 2, 3, False]) is False


def test_is_valid_bbox_rejects_short_list():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_rejects_long_list():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_rejects_string_elements():
    assert _is_valid_bbox(["a", "b", "c", "d"]) is False


def test_is_valid_bbox_rejects_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_rejects_dict():
    assert _is_valid_bbox({"x": 1}) is False


def test_is_valid_bbox_rejects_tuple():
    """tuple 不是 list → 拒绝。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_accepts_negative_numbers():
    """负数也接受（不在 helper 层校验业务范围）。"""
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_rejects_nan():
    import math
    assert _is_valid_bbox([float("nan"), 2, 3, 4]) is False


def test_is_valid_bbox_rejects_inf():
    assert _is_valid_bbox([float("inf"), 2, 3, 4]) is False


def test_is_valid_bbox_rejects_mixed_with_nan():
    import math
    assert _is_valid_bbox([1.0, float("nan"), 3.0, 4.0]) is False


# ---------- _image_resource_ratio 边角 ----------


def test_image_resource_ratio_no_images_returns_null(tmp_path: Path):
    result = _image_resource_ratio([], tmp_path)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_with_existing_file(tmp_path: Path):
    """image_base_dir + resource_path 文件存在 → valid。"""
    img_file = tmp_path / "image.png"
    img_file.write_bytes(b"fake image bytes")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 1.0


def test_image_resource_ratio_with_relative_path(tmp_path: Path):
    """相对路径 + image_base_dir + .name 拼接。"""
    img_file = tmp_path / "image.png"
    img_file.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": "image.png"},  # 相对路径
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 1.0


def test_image_resource_ratio_with_missing_file(tmp_path: Path):
    elements = [
        {"type": "image", "resource_path": str(tmp_path / "nope.png")},
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_with_none_path(tmp_path: Path):
    elements = [
        {"type": "image", "resource_path": None},
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_with_empty_string_path(tmp_path: Path):
    elements = [
        {"type": "image", "resource_path": ""},
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_with_empty_file(tmp_path: Path):
    """0 字节文件不计 valid。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path: Path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"a")
    elements = [
        {"type": "image", "resource_path": str(img1)},  # valid
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},  # invalid
    ]
    result = _image_resource_ratio(elements, tmp_path)
    assert result["value"] == 0.5


def test_image_resource_ratio_no_base_dir_absolute_path(tmp_path: Path):
    """image_base_dir=None + 绝对路径 → 直接用绝对路径。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_no_base_dir_relative_path_invalid(tmp_path: Path):
    """image_base_dir=None + 相对路径 → 用 CWD 解析，通常不存在。"""
    elements = [
        {"type": "image", "resource_path": "nonexistent_relative.png"},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


# ---------- _chunk_reference_ratio 边角 ----------


def test_chunk_reference_ratio_no_chunks_returns_null():
    result = _chunk_reference_ratio([], [])
    assert result["value"] is None
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_duplicate_source_id_in_one_chunk():
    """chunk.source_element_ids 含重复 id（合法但仍 intact）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_unknown_id_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "eX"]}]  # eX 不在 elements
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_empty_ids_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_none_ids_invalid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_missing_ids_key_invalid():
    """chunk 无 source_element_ids key → 当 None → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 无 source_element_ids
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_mixed():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["eX"]},  # invalid
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.5


# ---------- _strip_unicode_whitespace 边角 ----------


def test_strip_unicode_whitespace_no_whitespace_unchanged():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_all_whitespace_returns_empty():
    assert _strip_unicode_whitespace("   \t\n\r") == ""


def test_strip_unicode_whitespace_only_spaces():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_handles_nbsp():
    """U+00A0 NBSP 应被删。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_handles_ideographic_space():
    """U+3000 全角空格应被删。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_handles_em_space():
    """U+2003 em space 应被删。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_punctuation():
    """标点不算空白。"""
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_whitespace_preserves_unicode_chars():
    """中文/emoji 不算空白。"""
    assert _strip_unicode_whitespace("中文 🎉 test") == "中文🎉test"


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("hello"), str)


# ---------- _text_preservation 边角 ----------


def test_text_preservation_equal_match():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_single_chunk_equal():
    elements = [{"type": "paragraph", "content": "abc"}, {"type": "heading", "content": "def"}]
    chunks = [{"text": "abcdef"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_excludes_image():
    """image content 不参与比对（content=None 也 OK）。"""
    elements = [
        {"type": "paragraph", "content": "hello"},
        {"type": "image", "content": None},
    ]
    chunks = [{"text": "hello"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_whitespace_only_diff_equal():
    """空白差异不报。"""
    elements = [{"type": "paragraph", "content": "a b"}]
    chunks = [{"text": "ab"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_both_empty_returns_null():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": ""}]
    result = _text_preservation(elements, chunks)
    assert result["precision"]["reason"] == "empty_expected_and_actual"
    assert result["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_non_empty_expected():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # actual 空 → precision null
    assert result["precision"]["reason"] == "empty_actual"
    # expected 非空 → recall 0
    assert result["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_non_empty_actual():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # actual 非空 → precision 0
    assert result["precision"]["value"] == 0.0
    # expected 空 → recall null
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_three_keys():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{"text": "x"}]
    result = _text_preservation(elements, chunks)
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_missing_content_uses_empty_string():
    """element 无 content key → 当 ""。"""
    elements = [{"type": "paragraph"}]  # 无 content
    chunks = [{"text": "x"}]
    result = _text_preservation(elements, chunks)
    # expected 空 → recall null
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_missing_text_in_chunk_uses_empty_string():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{}]  # 无 text
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False


# ---------- _heading_boundary_ratio 边角 ----------


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] is None
    assert result["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero():
    """有 heading 无 chunks → ratio=0.0（不 null）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    result = _heading_boundary_ratio(elements, [])
    assert result["value"] == 0.0


def test_heading_boundary_ratio_all_at_chunk_start():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_partial():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1", "p1"]},  # h1 是首
        {"source_element_ids": ["p2"]},  # h2 不是首
    ]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.5


def test_heading_boundary_ratio_none_at_start():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 不是首
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunk_no_ids_not_counted():
    """chunk 无 source_element_ids → 不贡献 chunk_first_ids。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]  # 空
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


# ---------- _silent_drop_count 边角 ----------


def test_silent_drop_count_no_expectations_returns_null():
    result = _silent_drop_count({"paragraph": 5}, None)
    assert result["value"] is None
    assert result["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    result = _silent_drop_count({"paragraph": 5}, {})
    assert result["value"] is None


def test_silent_drop_count_expectations_without_element_count_returns_null():
    result = _silent_drop_count({"paragraph": 5}, {"other_key": "value"})
    assert result["value"] is None
    assert result["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type_returns_null():
    result = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert result["value"] is None
    assert result["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_meets_expected_zero():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_exceeds_expected_zero():
    """actual > expected 不计负 drop。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_below_expected():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 2


def test_silent_drop_count_multiple_types_sum():
    by_type = {"paragraph": 3, "heading": 1}
    expectations = {
        "element_count_by_type": {"paragraph": 5, "heading": 2, "table": 1}
    }
    result = _silent_drop_count(by_type, expectations)
    # paragraph: 5-3=2, heading: 2-1=1, table: 1-0=1 → total 4
    assert result["value"] == 4


def test_silent_drop_count_expected_type_missing_in_actual():
    """期望有 table 但实际 by_type 无 table → drop=expected。"""
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5, "table": 2}}
    result = _silent_drop_count(by_type, expectations)
    # paragraph: 0 drop, table: 2-0=2 drop
    assert result["value"] == 2


def test_silent_drop_count_value_is_int():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert isinstance(result["value"], int)


# ---------- compute_automatic_metrics 边角 ----------


def test_compute_automatic_metrics_returns_dict_type():
    result = compute_automatic_metrics(None, None, "docx", None)
    assert isinstance(result, dict)


def test_compute_automatic_metrics_pipeline_failed_full_metric_set():
    """pipeline 失败 → 14 个 metric key 全部存在（含 null）。"""
    result = compute_automatic_metrics(None, {"code": "x", "message": "y"}, "docx", None)
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


def test_compute_automatic_metrics_pipeline_success_full_metric_set():
    """pipeline 成功 → 同样 14 个 key。"""
    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph", "content": "x",
                       "source_locator": {"paragraph_index": 0, "section": 0}}],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "docx", None)
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


def test_compute_automatic_metrics_pipeline_success_true_when_no_error_and_document():
    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "docx", None)
    assert result["pipeline_success"]["value"] is True


def test_compute_automatic_metrics_pipeline_success_false_when_error():
    result = compute_automatic_metrics(None, {"code": "x", "message": "y"}, "docx", None)
    assert result["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_pipeline_success_false_when_document_none():
    """document=None 且 error=None → False（边界情况）。"""
    result = compute_automatic_metrics(None, None, "docx", None)
    assert result["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_error_code_none_when_no_error():
    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "docx", None)
    assert result["error_code"]["value"] is None


def test_compute_automatic_metrics_error_code_value_passes_through():
    result = compute_automatic_metrics(
        None, {"code": "custom_code", "message": "x"}, "docx", None
    )
    assert result["error_code"]["value"] == "custom_code"


def test_compute_automatic_metrics_schema_valid_false_when_invalid_document():
    """document 不符合 schema → schema_valid=False。"""
    result = compute_automatic_metrics(
        {"invalid": "shape"}, None, "docx", None
    )
    assert result["schema_valid"]["value"] is False


def test_compute_automatic_metrics_pdf_source_uses_pdf_locator():
    """source_type=pdf → pdf_locator 计算而非 null。"""
    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.pdf",
        "source_type": "pdf",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "table",
                       "source_locator": {"page": 1}}],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "pdf", None)
    assert result["pdf_locator_valid_ratio"]["value"] == 1.0
    # docx locator 应是 null + reason
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_docx_source_uses_docx_locator():
    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [{"element_id": "e1", "type": "paragraph",
                       "source_locator": {"paragraph_index": 0, "section": 0}}],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "docx", None)
    assert result["docx_locator_valid_ratio"]["value"] == 1.0
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_schema_check_exception_handled(monkeypatch):
    """schema_check 抛异常 → schema_valid=False + reason 含 exception 类型。"""
    import evaluation.metrics as mod
    import evaluation.schema_validation as sv

    def _raise(doc):
        raise RuntimeError("mock schema error")

    monkeypatch.setattr(sv, "document_passes_schema", _raise)
    # 重新 import 以让 metrics 模块的延迟 import 拿到 patched 版本
    # （因为 metrics.py 内是 from evaluation.schema_validation import document_passes_schema）

    document = {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    result = compute_automatic_metrics(document, None, "docx", None)
    assert result["schema_valid"]["value"] is False
    assert "schema_check_exception" in result["schema_valid"]["reason"]
    assert "RuntimeError" in result["schema_valid"]["reason"]


# ---------- __all__ ----------


def test_metrics_module_all_only_compute_automatic_metrics():
    import evaluation.metrics as mod
    assert mod.__all__ == ["compute_automatic_metrics"]


def test_metrics_module_has_compute_automatic_metrics():
    import evaluation.metrics as mod
    assert hasattr(mod, "compute_automatic_metrics")
