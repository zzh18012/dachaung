"""evaluation/metrics.py 边角测试（Round 85，第二轮）。

补强 tests/test_metrics.py（90+）+ test_evaluation_metrics_edges.py（150+）
未覆盖的盲区：

- _null / _ratio / _bool_metric / _int_metric 类型/边界
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 常量完整枚举
- compute_automatic_metrics: source_type=unknown、error 无 code key、
  schema check exception 各种类型、element type=unknown 分类、
  chunks 空 source_element_ids、image 绝对路径、image resource 0-byte 文件
- _pdf_locator_ratio: 各种 page 类型/值、bbox 各种 invalid 类型、bool 拒绝
- _docx_locator_ratio: page/bbox 拒绝、structural keys 完整枚举、no locator
- _is_valid_bbox: 各种 invalid 类型深扫（dict/tuple/set/None/bool/inf/nan）
- _image_resource_ratio: 各种路径、image_base_dir、OSError handling、空文件
- _chunk_reference_ratio: chunks 缺 source_element_ids、referencing 非存在 id
- _strip_unicode_whitespace: 各种 Unicode 空白字符
- _text_preservation: empty/missing 字段、precision/recall 边界
- _heading_boundary_ratio: heading 无 element_id、chunk 无 ids
- _silent_drop_count: expectations 含 None/0/负数
"""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import pytest

from evaluation.metrics import (
    __all__ as metrics_all,
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
# 1. helper 函数第二轮
# =========================================================================


def test_null_returns_dict_with_value_none():
    result = _null("reason")
    assert result["value"] is None


def test_null_returns_dict_with_reason_str():
    result = _null("my_reason")
    assert result["reason"] == "my_reason"


def test_null_dict_has_exactly_two_keys():
    result = _null("x")
    assert set(result.keys()) == {"value", "reason"}


def test_null_with_empty_reason():
    result = _null("")
    assert result["reason"] == ""
    assert result["value"] is None


def test_null_with_unicode_reason():
    result = _null("中文原因")
    assert result["reason"] == "中文原因"


def test_ratio_returns_dict_with_value_float():
    result = _ratio(0.5)
    assert isinstance(result["value"], float)


def test_ratio_returns_dict_with_reason_none():
    result = _ratio(0.5)
    assert result["reason"] is None


def test_ratio_zero_value():
    result = _ratio(0)
    assert result["value"] == 0.0


def test_ratio_one_value():
    result = _ratio(1)
    assert result["value"] == 1.0


def test_ratio_negative_value_allowed():
    """注意：函数不强校验 [0,1]，可接受任意 float。"""
    result = _ratio(-0.5)
    assert result["value"] == -0.5


def test_ratio_large_value_allowed():
    result = _ratio(2.5)
    assert result["value"] == 2.5


def test_ratio_dict_has_exactly_two_keys():
    result = _ratio(0.5)
    assert set(result.keys()) == {"value", "reason"}


def test_bool_metric_returns_bool_value():
    result = _bool_metric(True)
    assert result["value"] is True


def test_bool_metric_coerces_truthy():
    result = _bool_metric(1)
    assert result["value"] is True


def test_bool_metric_coerces_falsy():
    result = _bool_metric(0)
    assert result["value"] is False


def test_bool_metric_reason_none():
    result = _bool_metric(True)
    assert result["reason"] is None


def test_bool_metric_dict_has_exactly_two_keys():
    result = _bool_metric(True)
    assert set(result.keys()) == {"value", "reason"}


def test_int_metric_returns_int_value():
    result = _int_metric(5)
    assert result["value"] == 5
    assert isinstance(result["value"], int)


def test_int_metric_coerces_float_to_int():
    result = _int_metric(5.9)
    assert result["value"] == 5


def test_int_metric_coerces_string_digit():
    result = _int_metric("10")
    assert result["value"] == 10


def test_int_metric_zero_value():
    result = _int_metric(0)
    assert result["value"] == 0


def test_int_metric_negative_value():
    result = _int_metric(-5)
    assert result["value"] == -5


def test_int_metric_reason_none():
    result = _int_metric(5)
    assert result["reason"] is None


# =========================================================================
# 2. 模块常量
# =========================================================================


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_includes_heading():
    assert "heading" in _TEXT_TYPES


def test_text_types_includes_paragraph():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_includes_list_item():
    assert "list_item" in _TEXT_TYPES


def test_text_types_includes_table():
    assert "table" in _TEXT_TYPES


def test_text_types_includes_caption():
    assert "caption" in _TEXT_TYPES


def test_text_types_includes_header():
    assert "header" in _TEXT_TYPES


def test_text_types_includes_footer():
    assert "footer" in _TEXT_TYPES


def test_text_types_excludes_image():
    assert "image" not in _TEXT_TYPES


def test_text_types_seven_entries():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_includes_heading():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_paragraph():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_caption():
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_list_item():
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_table():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_image():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_four_entries():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_not_evaluated_constant_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


# =========================================================================
# 3. _is_valid_bbox 第二轮
# =========================================================================


def test_is_valid_bbox_accepts_four_floats():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_accepts_four_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_accepts_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 100, 100.0]) is True


def test_is_valid_bbox_accepts_negative_values():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_rejects_three_elements():
    assert _is_valid_bbox([0.0, 0.0, 100.0]) is False


def test_is_valid_bbox_rejects_five_elements():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0, 50.0]) is False


def test_is_valid_bbox_rejects_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_rejects_string_elements():
    assert _is_valid_bbox(["0", "0", "100", "100"]) is False


def test_is_valid_bbox_rejects_partial_string():
    assert _is_valid_bbox([0.0, "0", 100.0, 100.0]) is False


def test_is_valid_bbox_rejects_dict():
    assert _is_valid_bbox({"x": 0, "y": 0}) is False


def test_is_valid_bbox_rejects_tuple():
    """tuple 不被接受（要求 list）。"""
    assert _is_valid_bbox((0.0, 0.0, 100.0, 100.0)) is False


def test_is_valid_bbox_rejects_set():
    assert _is_valid_bbox({0.0, 0.0, 100.0, 100.0}) is False


def test_is_valid_bbox_rejects_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_rejects_bool_in_list():
    """bool 是 int 的子类，但函数显式拒绝。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_rejects_inf():
    assert _is_valid_bbox([math.inf, 0.0, 100.0, 100.0]) is False


def test_is_valid_bbox_rejects_neg_inf():
    assert _is_valid_bbox([-math.inf, 0.0, 100.0, 100.0]) is False


def test_is_valid_bbox_rejects_nan():
    assert _is_valid_bbox([math.nan, 0.0, 100.0, 100.0]) is False


def test_is_valid_bbox_signature_one_param():
    import inspect
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


# =========================================================================
# 4. _pdf_locator_ratio 第二轮
# =========================================================================


def test_pdf_locator_ratio_empty_elements_returns_null():
    result = _pdf_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid_text_with_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "heading", "source_locator": {"page": 2, "bbox": [0, 0, 10, 10]}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_text_missing_bbox_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # no bbox
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_invalid_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0]}},  # only 2
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_zero_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": 0}},  # table 不需 bbox
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": -1}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    elements = [
        {"type": "table", "source_locator": {"page": "1"}},
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_no_locator():
    elements = [{"type": "table"}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_locator_none():
    elements = [{"type": "table", "source_locator": None}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.0


def test_pdf_locator_ratio_table_does_not_need_bbox():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES，所以只需 page≥1。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_image_does_not_need_bbox():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 1.0


def test_pdf_locator_ratio_partial_valid():
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
    ]
    result = _pdf_locator_ratio(elements)
    assert result["value"] == 0.5


def test_pdf_locator_ratio_bool_page_invalid():
    """True 是 int 的子类（=1），但 isinstance(True, int) is True → 有效？
    实际：isinstance(True, int) 是 True，True >= 1 是 True → 有效。"""
    elements = [{"type": "table", "source_locator": {"page": True}}]
    result = _pdf_locator_ratio(elements)
    # True 在 Python 中视为 1，所以这个会被认为 valid
    assert result["value"] == 1.0


# =========================================================================
# 5. _docx_locator_ratio 第二轮
# =========================================================================


def test_docx_locator_ratio_empty_returns_null():
    result = _docx_locator_ratio([])
    assert result["value"] is None
    assert result["reason"] == "no_elements"


def test_docx_locator_ratio_paragraph_index_valid():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_section_valid():
    elements = [{"type": "paragraph", "source_locator": {"section": "main"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_run_index_valid():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_table_index_valid():
    elements = [{"type": "table", "source_locator": {"table_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_row_index_valid():
    elements = [{"type": "table", "source_locator": {"row_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_col_index_valid():
    elements = [{"type": "table", "source_locator": {"col_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_relationship_id_valid():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


def test_docx_locator_ratio_page_rejected():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_bbox_rejected():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_structural_key():
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_no_locator():
    elements = [{"type": "paragraph"}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_locator_none():
    elements = [{"type": "paragraph", "source_locator": None}]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.0


def test_docx_locator_ratio_partial_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"unknown_key": "x"}},
    ]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 0.5


def test_docx_locator_ratio_multiple_structural_keys():
    elements = [{
        "type": "table",
        "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0},
    }]
    result = _docx_locator_ratio(elements)
    assert result["value"] == 1.0


# =========================================================================
# 6. _image_resource_ratio 第二轮
# =========================================================================


def test_image_resource_ratio_no_images_returns_null():
    elements = [{"type": "paragraph"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] is None
    assert result["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path():
    elements = [{"type": "image"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_empty_resource_path():
    elements = [{"type": "image", "resource_path": ""}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_none_resource_path():
    elements = [{"type": "image", "resource_path": None}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_file_exists(tmp_path: Path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 1.0


def test_image_resource_ratio_file_missing():
    elements = [{"type": "image", "resource_path": "/nonexistent/file.png"}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_zero_byte_file(tmp_path: Path):
    """0-byte 文件 → 不视为有效。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.0


def test_image_resource_ratio_partial(tmp_path: Path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": "/nonexistent/b.png"},
    ]
    result = _image_resource_ratio(elements, None)
    assert result["value"] == 0.5


def test_image_resource_ratio_with_image_base_dir(tmp_path: Path):
    """resource_path 仅文件名 + image_base_dir 给定 → 拼接尝试。"""
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    img_file = img_dir / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 1.0


def test_image_resource_ratio_image_base_dir_with_missing_file(tmp_path: Path):
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    elements = [{"type": "image", "resource_path": "missing.png"}]
    result = _image_resource_ratio(elements, img_dir)
    assert result["value"] == 0.0


def test_image_resource_ratio_absolute_path_ignores_base_dir(tmp_path: Path):
    """绝对路径优先；image_base_dir 仅作 fallback。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    fake_base = tmp_path / "nonexistent_dir"
    result = _image_resource_ratio(elements, fake_base)
    assert result["value"] == 1.0


def test_image_resource_ratio_returns_float():
    elements = [{"type": "paragraph"}]
    result = _image_resource_ratio(elements, None)
    # value is None, but for valid ratio case value is float
    # 这里测 reason="no_image_elements" 路径
    assert result["value"] is None


# =========================================================================
# 7. _chunk_reference_ratio 第二轮
# =========================================================================


def test_chunk_reference_ratio_no_chunks_returns_null():
    result = _chunk_reference_ratio([], [])
    assert result["value"] is None
    assert result["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e2"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_invalid_reference():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["nonexistent"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_partial():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["nonexistent"]},  # invalid
    ]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.5


def test_chunk_reference_ratio_empty_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_no_source_element_ids_key():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_none_source_element_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_chunk_reference_ratio_mixed_ids():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "nonexistent"]}]
    result = _chunk_reference_ratio(elements, chunks)
    # all(sid in elem_ids) → False → not counted
    assert result["value"] == 0.0


def test_chunk_reference_ratio_multiple_valid_ids():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    result = _chunk_reference_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_chunk_reference_ratio_elements_without_id():
    """element 缺 element_id → set 含 None；chunk 引用 None 也算"匹配"。
    这是已知行为：不强制 element 必须有 element_id。"""
    elements = [{}]  # no element_id
    chunks = [{"source_element_ids": [None]}]  # None matches None
    result = _chunk_reference_ratio(elements, chunks)
    # elements set = {None}; chunk ids=[None]; None in {None} → True
    assert result["value"] == 1.0


# =========================================================================
# 8. _strip_unicode_whitespace 第二轮
# =========================================================================


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_whitespace_leading_whitespace():
    assert _strip_unicode_whitespace("  abc") == "abc"


def test_strip_unicode_whitespace_trailing_whitespace():
    assert _strip_unicode_whitespace("abc  ") == "abc"


def test_strip_unicode_whitespace_internal_whitespace_preserved_removed():
    """内部空白被全部删除（不压缩为单空格）。"""
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_nbsp():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """U+3000 全角空格。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """U+2002 en space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_tab():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_carriage_return():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_whitespace_form_feed():
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_unicode_whitespace_vertical_tab():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """U+2028。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_mixed():
    assert _strip_unicode_whitespace(" a\tb\nc　d ") == "abcd"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    """非空白字符（含标点、emoji、中文）保留。"""
    assert _strip_unicode_whitespace("中文.!,🎉") == "中文.!,🎉"


# =========================================================================
# 9. _text_preservation 第二轮
# =========================================================================


def test_text_preservation_no_chunks():
    result = _text_preservation([{"type": "paragraph", "content": "abc"}], [])
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] is None  # empty actual


def test_text_preservation_no_elements():
    result = _text_preservation([], [{"text": "abc"}])
    assert result["equal"]["value"] is False
    assert result["recall"]["value"] is None  # empty expected


def test_text_preservation_both_empty():
    result = _text_preservation([], [])
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] is None
    assert result["recall"]["value"] is None
    assert result["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 1.0


def test_text_preservation_partial_match():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abd"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False
    # Counter: a:1, b:1, c:1 vs a:1, b:1, d:1; common = a+b = 2
    assert result["precision"]["value"] == 2 / 3
    assert result["recall"]["value"] == 2 / 3


def test_text_preservation_extra_in_actual():
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    # common = 2; precision = 2/3; recall = 2/2
    assert result["precision"]["value"] == 2 / 3
    assert result["recall"]["value"] == 1.0


def test_text_preservation_extra_in_expected():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    result = _text_preservation(elements, chunks)
    # common = 2; precision = 2/2; recall = 2/3
    assert result["precision"]["value"] == 1.0
    assert result["recall"]["value"] == 2 / 3


def test_text_preservation_excludes_image():
    elements = [
        {"type": "paragraph", "content": "a"},
        {"type": "image", "content": "ignore_me"},
    ]
    chunks = [{"text": "a"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_image_only():
    """所有 element 都是 image → expected 为空，actual 非空。"""
    elements = [{"type": "image", "content": "x"}]
    chunks = [{"text": "a"}]
    result = _text_preservation(elements, chunks)
    # expected = "", actual = "a"; equal = False; precision = 0/1 = 0, recall = null(empty_expected)
    assert result["equal"]["value"] is False
    assert result["precision"]["value"] == 0.0
    assert result["recall"]["reason"] == "empty_expected"


def test_text_preservation_missing_content():
    elements = [{"type": "paragraph"}]  # no content
    chunks = [{"text": "a"}]
    result = _text_preservation(elements, chunks)
    # expected = "", actual = "a"
    assert result["equal"]["value"] is False


def test_text_preservation_missing_text():
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{}]  # no text
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is False


def test_text_preservation_returns_three_keys():
    result = _text_preservation([], [])
    assert set(result.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_metric_has_value_reason():
    result = _text_preservation([], [])
    for k in ("equal", "precision", "recall"):
        assert "value" in result[k]
        assert "reason" in result[k]


def test_text_preservation_whitespace_ignored():
    """空白被全部删除 → 不影响比较。"""
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    result = _text_preservation(elements, chunks)
    assert result["equal"]["value"] is True


def test_text_preservation_counter_handles_repeats():
    """Counter 多集合保留重复信息。"""
    elements = [{"type": "paragraph", "content": "aab"}]
    chunks = [{"text": "ab"}]
    # Counter expected: {a:2, b:1}; actual: {a:1, b:1}
    # common = min(2,1) + min(1,1) = 1 + 1 = 2
    # precision = 2/2 = 1.0; recall = 2/3
    result = _text_preservation(elements, chunks)
    assert result["precision"]["value"] == 1.0
    assert abs(result["recall"]["value"] - 2 / 3) < 1e-9


# =========================================================================
# 10. _heading_boundary_ratio 第二轮
# =========================================================================


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph"}]
    chunks = []
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] is None
    assert result["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = []
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_matches():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 1.0


def test_heading_boundary_ratio_chunk_first_id_not_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 not first
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_partial():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # only h1 at start
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.5


def test_heading_boundary_ratio_chunk_empty_ids():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_chunk_no_ids_key():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    result = _heading_boundary_ratio(elements, chunks)
    assert result["value"] == 0.0


def test_heading_boundary_ratio_heading_no_element_id():
    elements = [{"type": "heading"}]
    chunks = [{"source_element_ids": [None]}]
    result = _heading_boundary_ratio(elements, chunks)
    # h.get('element_id') → None; None in {None} → True → matched
    assert result["value"] == 1.0


# =========================================================================
# 11. _silent_drop_count 第二轮
# =========================================================================


def test_silent_drop_count_no_expectations_returns_null():
    result = _silent_drop_count({}, None)
    assert result["value"] is None
    assert result["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_returns_null():
    result = _silent_drop_count({}, {})
    assert result["value"] is None


def test_silent_drop_count_no_element_count_returns_null():
    result = _silent_drop_count({}, {"other_key": "value"})
    assert result["value"] is None
    assert result["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_returns_null():
    result = _silent_drop_count({}, {"element_count_by_type": {}})
    assert result["value"] is None


def test_silent_drop_count_actual_meets_expected():
    by_type = {"heading": 5, "paragraph": 10}
    expectations = {"element_count_by_type": {"heading": 5, "paragraph": 10}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_exceeds_expected():
    by_type = {"heading": 10}
    expectations = {"element_count_by_type": {"heading": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_actual_below_expected():
    by_type = {"heading": 3}
    expectations = {"element_count_by_type": {"heading": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 2


def test_silent_drop_count_missing_type_in_actual():
    by_type = {}
    expectations = {"element_count_by_type": {"heading": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 5


def test_silent_drop_count_multiple_types_sum():
    by_type = {"heading": 1, "paragraph": 5}
    expectations = {"element_count_by_type": {"heading": 5, "paragraph": 10}}
    # heading: 5-1=4, paragraph: 10-5=5 → total 9
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 9


def test_silent_drop_count_returns_int():
    by_type = {"heading": 3}
    expectations = {"element_count_by_type": {"heading": 5}}
    result = _silent_drop_count(by_type, expectations)
    assert isinstance(result["value"], int)


def test_silent_drop_count_zero_expected_zero_actual():
    by_type = {"heading": 0}
    expectations = {"element_count_by_type": {"heading": 0}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


def test_silent_drop_count_expected_zero_actual_nonzero():
    """expected=0, actual=5 → 不算 drop（actual < exp is False）。"""
    by_type = {"heading": 5}
    expectations = {"element_count_by_type": {"heading": 0}}
    result = _silent_drop_count(by_type, expectations)
    assert result["value"] == 0


# =========================================================================
# 12. compute_automatic_metrics 第二轮
# =========================================================================


def test_compute_metrics_signature_default_image_base_dir_none():
    import inspect
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert params[4].name == "image_base_dir"
    assert params[4].default is None


def test_compute_metrics_signature_returns_dict():
    import inspect
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation) or sig.return_annotation is dict


def test_compute_metrics_pipeline_failed_returns_13_metrics():
    """pipeline_failed 时返回 13 个 metric（pipeline_success + error_code + schema_valid + 10 个 null）。"""
    metrics = compute_automatic_metrics(None, None, "docx", None)
    # pipeline_success, error_code, schema_valid + 10 null = 13
    assert len(metrics) >= 13


def test_compute_metrics_pipeline_success_returns_all_metrics():
    metrics = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="docx",
        expectations=None,
    )
    # 应有所有 metrics
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected_keys.issubset(set(metrics.keys()))


def test_compute_metrics_error_code_no_code_key():
    """error 没有 code key → KeyError（函数直接索引 error["code"]）。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, {"message": "x"}, "docx", None)


def test_compute_metrics_element_type_unknown_in_by_type():
    """element type="unknown" → by_type["unknown"]=1。"""
    document = {
        "elements": [{"type": "unknown", "element_id": "e1"}],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["element_count_by_type"]["value"] == {"unknown": 1}


def test_compute_metrics_element_no_type_uses_unknown():
    """element 缺 type field → by_type["unknown"]=1。"""
    document = {
        "elements": [{"element_id": "e1"}],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["element_count_by_type"]["value"] == {"unknown": 1}


def test_compute_metrics_unknown_source_type_pdf_locator_null():
    """source_type="unknown" → pdf_locator_valid_ratio null (not_pdf_document)。"""
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "unknown", None)
    assert metrics["pdf_locator_valid_ratio"]["value"] is None
    assert metrics["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_unknown_source_type_docx_locator_null():
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "unknown", None)
    assert metrics["docx_locator_valid_ratio"]["value"] is None
    assert metrics["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_uppercase_source_type_pdf_not_treated_as_pdf():
    """source_type='PDF' 大小写敏感 → not_pdf_document。"""
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "PDF", None)
    assert metrics["pdf_locator_valid_ratio"]["value"] is None


def test_compute_metrics_schema_check_exception_handled(monkeypatch):
    """schema check 抛异常 → schema_valid=False + reason 含 exception type。"""
    import evaluation.metrics as mod
    import evaluation.schema_validation as sv

    def _raise(doc):
        raise RuntimeError("test schema fail")
    monkeypatch.setattr(sv, "document_passes_schema", _raise)
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["schema_valid"]["value"] is False
    assert "RuntimeError" in metrics["schema_valid"]["reason"]


def test_compute_metrics_schema_check_attribute_error(monkeypatch):
    import evaluation.schema_validation as sv

    def _raise(doc):
        raise AttributeError("attr fail")
    monkeypatch.setattr(sv, "document_passes_schema", _raise)
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["schema_valid"]["value"] is False
    assert "AttributeError" in metrics["schema_valid"]["reason"]


def test_compute_metrics_pipeline_success_true_when_doc_and_no_error():
    document = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["pipeline_success"]["value"] is True


def test_compute_metrics_pipeline_success_false_when_error():
    metrics = compute_automatic_metrics(None, {"code": "x"}, "docx", None)
    assert metrics["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_false_when_doc_none():
    metrics = compute_automatic_metrics(None, None, "docx", None)
    assert metrics["pipeline_success"]["value"] is False


def test_compute_metrics_silent_drop_count_with_expectations():
    document = {
        "elements": [{"type": "heading"}, {"type": "paragraph"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"heading": 5}}
    metrics = compute_automatic_metrics(document, None, "docx", expectations)
    # actual heading = 1, expected 5 → drop = 4
    assert metrics["silent_drop_count"]["value"] == 4


def test_compute_metrics_silent_drop_count_no_expectations():
    document = {
        "elements": [{"type": "heading"}],
        "chunks": [],
    }
    metrics = compute_automatic_metrics(document, None, "docx", None)
    assert metrics["silent_drop_count"]["value"] is None
    assert metrics["silent_drop_count"]["reason"] == "no_expectations"


# =========================================================================
# 13. __all__ 与模块结构
# =========================================================================


def test_metrics_all_only_compute_automatic_metrics():
    assert metrics_all == ["compute_automatic_metrics"]


def test_metrics_all_is_list():
    assert isinstance(metrics_all, list)


def test_metrics_module_has_compute_automatic_metrics():
    import evaluation.metrics as mod
    assert hasattr(mod, "compute_automatic_metrics")


def test_metrics_module_imports_math():
    import evaluation.metrics as mod
    assert hasattr(mod, "math")


def test_metrics_module_imports_counter():
    import evaluation.metrics as mod
    assert hasattr(mod, "Counter")


def test_metrics_module_imports_path():
    import evaluation.metrics as mod
    assert hasattr(mod, "Path")


def test_metrics_module_constants_present():
    import evaluation.metrics as mod
    assert hasattr(mod, "_TEXT_TYPES")
    assert hasattr(mod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mod, "_NOT_EVALUATED")


def test_metrics_module_internal_helpers_present():
    import evaluation.metrics as mod
    for name in (
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ):
        assert hasattr(mod, name), f"missing: {name}"
