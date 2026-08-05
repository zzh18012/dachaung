r"""evaluation/metrics.py 边角测试 - 第九轮（Round 208）。

补强已有 base/edges/edges2-8（共 ~1239 测试）未覆盖的深度：
- 模块常量精确值（_TEXT_TYPES 元组内容、_PDF_BBOX_REQUIRED_TYPES 元组内容）
- _NOT_EVALUATED 字符串值
- 各 helper 签名（future annotations → return_annotation 是字符串）
- _null/_ratio/_bool_metric/_int_metric 精确 keys 集合
- _is_valid_bbox 穷举矩阵（complex/Decimal/tuple/set/dict/generator/NaN/Inf/bool）
- _pdf_locator_ratio page 类型边界（float/str/bool None）
- _docx_locator_ratio 结构键 7 个逐一验证
- _image_resource_ratio 多图片混合 + 空 resource_path
- _chunk_reference_ratio chunk source_element_ids 各种非 list 形态
- _text_preservation 内容形态（content is None / chunks text 是非字符串）
- _heading_boundary_ratio chunk first id 重复
- _silent_drop_count expectations 形态（None / {} / 缺 element_count_by_type）
- compute_automatic_metrics 13 metric 名精确集合 / 错误码传播
- 模块 imports / __all__ / future annotations / 无 _silence_unused
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
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


# =========================================================================
# 模块常量精确值
# =========================================================================


def test_not_evaluated_constant_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_constant_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_exact_contents():
    assert set(_TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_text_types_length_is_seven():
    assert len(_TEXT_TYPES) == 7


def test_text_types_does_not_contain_image():
    assert "image" not in _TEXT_TYPES


def test_text_types_no_duplicates():
    assert len(set(_TEXT_TYPES)) == len(_TEXT_TYPES)


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_exact_contents():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {
        "heading", "paragraph", "caption", "list_item",
    }


def test_pdf_bbox_required_types_length_is_four():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_no_duplicates():
    assert len(set(_PDF_BBOX_REQUIRED_TYPES)) == len(_PDF_BBOX_REQUIRED_TYPES)


def test_pdf_bbox_required_types_subset_of_text_types():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_excludes_table_header_footer():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


# =========================================================================
# 构造器签名 + 精确 keys
# =========================================================================


def test_null_signature():
    sig = inspect.signature(_null)
    params = list(sig.parameters)
    assert params == ["reason"]


def test_null_return_annotation_is_dict_str_any():
    sig = inspect.signature(_null)
    # from __future__ import annotations → 字符串
    assert sig.return_annotation == "dict[str, Any]"


def test_null_keys_exact():
    m = _null("r")
    assert set(m.keys()) == {"value", "reason"}


def test_null_value_is_none():
    assert _null("any")["value"] is None


def test_ratio_signature():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters)
    assert params == ["value"]


def test_ratio_return_annotation_is_dict_str_any():
    sig = inspect.signature(_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_ratio_keys_exact():
    m = _ratio(0.5)
    assert set(m.keys()) == {"value", "reason"}


def test_ratio_negative_value_returned_as_is():
    """_ratio 不做 0..1 截断，原样返回。"""
    m = _ratio(-0.5)
    assert m["value"] == -0.5


def test_ratio_above_one_returned_as_is():
    m = _ratio(1.5)
    assert m["value"] == 1.5


def test_ratio_float_class_even_for_int_input():
    m = _ratio(1)
    assert type(m["value"]) is float


def test_bool_metric_signature():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters)
    assert params == ["value"]


def test_bool_metric_return_annotation_is_dict_str_any():
    sig = inspect.signature(_bool_metric)
    assert sig.return_annotation == "dict[str, Any]"


def test_bool_metric_keys_exact():
    m = _bool_metric(True)
    assert set(m.keys()) == {"value", "reason"}


def test_bool_metric_coerces_int_one_to_true():
    m = _bool_metric(1)
    assert m["value"] is True


def test_bool_metric_coerces_int_zero_to_false():
    m = _bool_metric(0)
    assert m["value"] is False


def test_bool_metric_coerces_empty_string_to_false():
    m = _bool_metric("")
    assert m["value"] is False


def test_bool_metric_coerces_nonempty_string_to_true():
    m = _bool_metric("x")
    assert m["value"] is True


def test_bool_metric_value_is_bool_type():
    m = _bool_metric(1)
    assert type(m["value"]) is bool


def test_int_metric_signature():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters)
    assert params == ["value"]


def test_int_metric_return_annotation_is_dict_str_any():
    sig = inspect.signature(_int_metric)
    assert sig.return_annotation == "dict[str, Any]"


def test_int_metric_keys_exact():
    m = _int_metric(5)
    assert set(m.keys()) == {"value", "reason"}


def test_int_metric_coerces_float_to_int():
    m = _int_metric(3.7)
    assert m["value"] == 3
    assert type(m["value"]) is int


def test_int_metric_coerces_bool_to_int():
    m = _int_metric(True)
    assert m["value"] == 1


def test_int_metric_negative_value():
    m = _int_metric(-5)
    assert m["value"] == -5


# =========================================================================
# _is_valid_bbox 穷举矩阵
# =========================================================================


def test_is_valid_bbox_signature():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters)
    assert params == ["bbox"]


def test_is_valid_bbox_return_annotation_is_bool_str():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_is_valid_bbox_four_ints():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_four_floats():
    assert _is_valid_bbox([1.0, 2.5, 3.7, 4.2]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([1, 2.5, 3, 4.0]) is True


def test_is_valid_bbox_zero_values():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_very_large_finite():
    assert _is_valid_bbox([1e308, -1e308, 1e308, -1e308]) is True


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_three():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_list_five():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_tuple():
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_set():
    s = {1, 2, 3, 4}
    assert _is_valid_bbox(s) is False


def test_is_valid_bbox_dict():
    assert _is_valid_bbox({"x": 1, "y": 2, "w": 3, "h": 4}) is False


def test_is_valid_bbox_string():
    assert _is_valid_bbox("1234") is False


def test_is_valid_bbox_with_true_bool():
    """bool 是 int 子类，但代码显式拒绝。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_with_false_bool():
    assert _is_valid_bbox([1, 2, 3, False]) is False


def test_is_valid_bbox_with_all_bools():
    assert _is_valid_bbox([True, False, True, False]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([1, 2, 3, math.nan]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([1, 2, 3, math.inf]) is False


def test_is_valid_bbox_with_neg_inf():
    assert _is_valid_bbox([1, 2, 3, -math.inf]) is False


def test_is_valid_bbox_with_string_element():
    assert _is_valid_bbox([1, 2, 3, "4"]) is False


def test_is_valid_bbox_with_none_element():
    assert _is_valid_bbox([1, 2, 3, None]) is False


def test_is_valid_bbox_with_complex():
    assert _is_valid_bbox([1, 2, 3, complex(1, 2)]) is False


def test_is_valid_bbox_generator():
    gen = (x for x in [1, 2, 3, 4])
    assert _is_valid_bbox(gen) is False


# =========================================================================
# _pdf_locator_ratio 深度
# =========================================================================


def test_pdf_locator_ratio_signature():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters)
    assert params == ["elements"]


def test_pdf_locator_ratio_return_annotation_str():
    sig = inspect.signature(_pdf_locator_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_pdf_locator_ratio_empty_list_no_elements():
    m = _pdf_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_pdf_locator_ratio_page_zero_invalid():
    elems = [{"type": "list_item", "source_locator": {"page": 0, "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_negative_invalid():
    elems = [{"type": "list_item", "source_locator": {"page": -1, "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_float_invalid():
    elems = [{"type": "list_item", "source_locator": {"page": 1.5, "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_string_invalid():
    elems = [{"type": "list_item", "source_locator": {"page": "1", "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_page_bool_accepted_as_int_one():
    """bool 是 int 子类，True 被当成 1 接受（行为记录，不评判）。"""
    elems = [{"type": "list_item", "source_locator": {"page": True, "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_page_none_invalid():
    elems = [{"type": "list_item", "source_locator": {"page": None, "bbox": [1, 2, 3, 4]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_text_type_without_bbox_invalid():
    """heading/paragraph/caption/list_item 必须 bbox。"""
    elems = [{"type": "paragraph", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_text_type_with_bad_bbox_invalid():
    elems = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3]}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_non_text_type_no_bbox_needed():
    """image/table/header/footer 只需要 page。"""
    elems = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_image_only_needs_page():
    elems = [{"type": "image", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_header_only_needs_page():
    elems = [{"type": "header", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_footer_only_needs_page():
    elems = [{"type": "footer", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 1.0


def test_pdf_locator_ratio_missing_source_locator_invalid():
    elems = [{"type": "image"}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_source_locator_none_invalid():
    elems = [{"type": "image", "source_locator": None}]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.0


def test_pdf_locator_ratio_half_valid_mixed():
    elems = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {"type": "image", "source_locator": {"page": 0}},  # invalid
    ]
    m = _pdf_locator_ratio(elems)
    assert m["value"] == 0.5


def test_pdf_locator_ratio_returns_float():
    elems = [{"type": "image", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elems)
    assert isinstance(m["value"], float)


def test_pdf_locator_ratio_keys_exact():
    m = _pdf_locator_ratio([{"type": "image", "source_locator": {"page": 1}}])
    assert set(m.keys()) == {"value", "reason"}


# =========================================================================
# _docx_locator_ratio 深度
# =========================================================================


def test_docx_locator_ratio_signature():
    sig = inspect.signature(_docx_locator_ratio)
    params = list(sig.parameters)
    assert params == ["elements"]


def test_docx_locator_ratio_return_annotation_str():
    sig = inspect.signature(_docx_locator_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_docx_locator_ratio_empty_list():
    m = _docx_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_docx_locator_ratio_section_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"section": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_run_index_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"run_index": 1}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_table_index_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"table_index": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_row_index_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"row_index": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_col_index_only_valid():
    elems = [{"type": "paragraph", "source_locator": {"col_index": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_relationship_id_only_valid():
    elems = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


def test_docx_locator_ratio_page_present_invalid():
    elems = [{"type": "paragraph", "source_locator": {"page": 1, "section": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.0


def test_docx_locator_ratio_bbox_present_invalid():
    elems = [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "section": 0}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_invalid():
    elems = [{"type": "paragraph", "source_locator": {"other_key": "x"}}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.0


def test_docx_locator_ratio_missing_source_locator_invalid():
    elems = [{"type": "paragraph"}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.0


def test_docx_locator_ratio_source_locator_none_invalid():
    elems = [{"type": "paragraph", "source_locator": None}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.0


def test_docx_locator_ratio_half_valid_mixed():
    elems = [
        {"type": "paragraph", "source_locator": {"section": 0}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
    ]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 0.5


def test_docx_locator_ratio_keys_exact():
    m = _docx_locator_ratio([{"type": "paragraph", "source_locator": {"section": 0}}])
    assert set(m.keys()) == {"value", "reason"}


def test_docx_locator_ratio_all_structural_keys_at_once():
    """所有 7 个结构键都在 → 仍 valid。"""
    loc = {
        "section": 0, "paragraph_index": 0, "run_index": 0,
        "table_index": 0, "row_index": 0, "col_index": 0,
        "relationship_id": "rId1",
    }
    elems = [{"type": "paragraph", "source_locator": loc}]
    m = _docx_locator_ratio(elems)
    assert m["value"] == 1.0


# =========================================================================
# _image_resource_ratio 深度
# =========================================================================


def test_image_resource_ratio_signature():
    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters)
    assert params == ["elements", "image_base_dir"]


def test_image_resource_ratio_return_annotation_str():
    sig = inspect.signature(_image_resource_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_image_resource_ratio_empty_elements_no_image_reason():
    m = _image_resource_ratio([], None)
    assert m["value"] is None
    assert m["reason"] == "no_image_elements"


def test_image_resource_ratio_no_image_type_elements():
    elems = [{"type": "paragraph", "resource_path": "/x.png"}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] is None
    assert m["reason"] == "no_image_elements"


def test_image_resource_ratio_image_with_no_resource_path():
    elems = [{"type": "image"}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.0


def test_image_resource_ratio_image_with_empty_resource_path():
    elems = [{"type": "image", "resource_path": ""}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.0


def test_image_resource_ratio_image_with_none_resource_path():
    elems = [{"type": "image", "resource_path": None}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.0


def test_image_resource_ratio_image_with_existing_file(tmp_path):
    img_file = tmp_path / "x.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    elems = [{"type": "image", "resource_path": str(img_file)}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 1.0


def test_image_resource_ratio_image_with_nonexistent_file():
    elems = [{"type": "image", "resource_path": "/nonexistent/path/x.png"}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.0


def test_image_resource_ratio_zero_byte_file(tmp_path):
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elems = [{"type": "image", "resource_path": str(img_file)}]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.0


def test_image_resource_ratio_half_valid_mixed(tmp_path):
    img_file = tmp_path / "good.png"
    img_file.write_bytes(b"data")
    elems = [
        {"type": "image", "resource_path": str(img_file)},  # valid
        {"type": "image", "resource_path": "/nonexistent.png"},  # invalid
    ]
    m = _image_resource_ratio(elems, None)
    assert m["value"] == 0.5


def test_image_resource_ratio_keys_exact():
    elems = [{"type": "image"}]
    m = _image_resource_ratio(elems, None)
    assert set(m.keys()) == {"value", "reason"}


def test_image_resource_ratio_image_base_dir_filename_fallback(tmp_path):
    """resource_path 是文件名，image_base_dir 给定 → 拼接尝试。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"data")
    elems = [{"type": "image", "resource_path": "img.png"}]
    m = _image_resource_ratio(elems, tmp_path)
    assert m["value"] == 1.0


def test_image_resource_ratio_image_base_dir_uses_filename_only(tmp_path):
    """image_base_dir 拼接时只用 Path(rp).name，不是原 rp。"""
    subdir = tmp_path / "sub"
    subdir.mkdir()
    img_file = subdir / "img.png"
    img_file.write_bytes(b"data")
    elems = [{"type": "image", "resource_path": "sub/img.png"}]
    # image_base_dir = tmp_path, 用 Path("sub/img.png").name = "img.png" → 在 sub/ 找不到 → 拼接 tmp_path/img.png 找不到
    m = _image_resource_ratio(elems, tmp_path)
    assert m["value"] == 0.0


# =========================================================================
# _chunk_reference_ratio 深度
# =========================================================================


def test_chunk_reference_ratio_signature():
    sig = inspect.signature(_chunk_reference_ratio)
    params = list(sig.parameters)
    assert params == ["elements", "chunks"]


def test_chunk_reference_ratio_return_annotation_str():
    sig = inspect.signature(_chunk_reference_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_chunk_reference_ratio_empty_chunks_null():
    m = _chunk_reference_ratio([], [])
    assert m["value"] is None
    assert m["reason"] == "no_chunks"


def test_chunk_reference_ratio_no_chunks_with_elements_null():
    elems = [{"element_id": "e1"}]
    m = _chunk_reference_ratio(elems, [])
    assert m["value"] is None
    assert m["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_missing_source_element_ids():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x"}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_none():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": None}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_ratio_chunk_source_element_ids_empty():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_ratio_valid_single_id():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 1.0


def test_chunk_reference_ratio_unknown_id():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["eX"]}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_ratio_partial_invalid_in_one_chunk():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1", "eX"]}]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_ratio_half_chunks_valid():
    elems = [{"element_id": "e1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},  # valid
        {"text": "y", "source_element_ids": ["eX"]},  # invalid
    ]
    m = _chunk_reference_ratio(elems, chunks)
    assert m["value"] == 0.5


def test_chunk_reference_ratio_keys_exact():
    elems = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    m = _chunk_reference_ratio(elems, chunks)
    assert set(m.keys()) == {"value", "reason"}


def test_chunk_reference_ratio_elements_without_element_id():
    """element 没有 element_id → elem_ids 集合中含 None；chunk 引用 None 不会匹配。"""
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    m = _chunk_reference_ratio([{}], chunks)
    assert m["value"] == 0.0


# =========================================================================
# _strip_unicode_whitespace 签名 + 边界
# =========================================================================


def test_strip_unicode_whitespace_signature():
    sig = inspect.signature(_strip_unicode_whitespace)
    params = list(sig.parameters)
    assert params == ["s"]


def test_strip_unicode_whitespace_return_annotation_str():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.return_annotation == "str"


def test_strip_unicode_whitespace_ordinary_space():
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_preserves_punctuation():
    assert _strip_unicode_whitespace("a.b,c!d") == "a.b,c!d"


def test_strip_unicode_whitespace_mixed_in_text():
    assert _strip_unicode_whitespace("a b\tc\nd") == "abcd"


def test_strip_unicode_whitespace_only_removes_whitespace():
    """空格、tab、CR、LF、VT、FF 全空。"""
    for ch in [" ", "\t", "\n", "\r", "\x0b", "\x0c"]:
        assert _strip_unicode_whitespace(ch) == ""


def test_strip_unicode_whitespace_does_not_remove_zero_width_joiner():
    """U+200D (ZWJ) 不是空白。"""
    assert _strip_unicode_whitespace("a‍b") == "a‍b"


def test_strip_unicode_whitespace_does_not_remove_soft_hyphen():
    """U+00AD (soft hyphen) 不是空白。"""
    assert _strip_unicode_whitespace("a­b") == "a­b"


def test_strip_unicode_whitespace_does_not_remove_bom():
    """U+FEFF (BOM/ZWNBSP) isspace() 返回 False，不被删除。"""
    assert _strip_unicode_whitespace("﻿") == "﻿"


def test_strip_unicode_whitespace_idempotent():
    s = "  hello   world  "
    once = _strip_unicode_whitespace(s)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


# =========================================================================
# _text_preservation 签名 + 边界
# =========================================================================


def test_text_preservation_signature():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters)
    assert params == ["elements", "chunks"]


def test_text_preservation_return_annotation_str():
    sig = inspect.signature(_text_preservation)
    assert sig.return_annotation == "dict[str, Any]"


def test_text_preservation_returns_dict_with_three_keys_exact():
    m = _text_preservation([], [])
    assert set(m.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_both_empty_all_null():
    m = _text_preservation([], [])
    assert m["equal"]["value"] is True  # "" == "" is True
    assert m["precision"]["value"] is None
    assert m["recall"]["value"] is None


def test_text_preservation_both_empty_reason():
    m = _text_preservation([], [])
    assert m["precision"]["reason"] == "empty_expected_and_actual"
    assert m["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_only_whitespace_in_both():
    elems = [{"type": "paragraph", "content": "   "}]
    chunks = [{"text": " \t "}]
    m = _text_preservation(elems, chunks)
    # 都剥离后是空 → equal=True, precision/recall=null
    assert m["equal"]["value"] is True
    assert m["precision"]["value"] is None


def test_text_preservation_expected_has_content_actual_empty():
    elems = [{"type": "paragraph", "content": "abc"}]
    m = _text_preservation(elems, [])
    assert m["equal"]["value"] is False
    # common = 0, |actual| = 0 → precision null
    assert m["precision"]["value"] is None
    assert m["precision"]["reason"] == "empty_actual"
    # recall = 0 / 3 = 0.0
    assert m["recall"]["value"] == 0.0


def test_text_preservation_actual_has_content_expected_empty():
    chunks = [{"text": "abc"}]
    m = _text_preservation([], chunks)
    assert m["equal"]["value"] is False
    # common = 0, |actual| = 3 → precision = 0.0
    assert m["precision"]["value"] == 0.0
    # |expected| = 0 → recall null
    assert m["recall"]["value"] is None
    assert m["recall"]["reason"] == "empty_expected"


def test_text_preservation_image_excluded_from_expected():
    elems = [
        {"type": "image", "content": "img_data_should_be_ignored"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abc"}]
    m = _text_preservation(elems, chunks)
    assert m["equal"]["value"] is True


def test_text_preservation_content_none_skipped():
    elems = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    m = _text_preservation(elems, chunks)
    # both reduce to ""
    assert m["equal"]["value"] is True


def test_text_preservation_chunk_text_none_treated_as_empty():
    elems = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    m = _text_preservation(elems, chunks)
    assert m["equal"]["value"] is False


def test_text_preservation_perfect_match_precision_one():
    elems = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    m = _text_preservation(elems, chunks)
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 1.0


def test_text_preservation_actual_superset_precision_lt_one():
    """actual 多了字符 → precision < 1，recall = 1。"""
    elems = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcX"}]
    m = _text_preservation(elems, chunks)
    assert m["precision"]["value"] == 0.75  # 3/4
    assert m["recall"]["value"] == 1.0


def test_text_preservation_actual_subset_recall_lt_one():
    """actual 少了字符 → precision = 1，recall < 1。"""
    elems = [{"type": "paragraph", "content": "abcX"}]
    chunks = [{"text": "abc"}]
    m = _text_preservation(elems, chunks)
    assert m["precision"]["value"] == 1.0
    assert m["recall"]["value"] == 0.75  # 3/4


def test_text_preservation_reorder_breaks_equal():
    """顺序不同 → equal=False，但 precision/recall 仍可能 = 1。"""
    elems = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "ba"}]
    m = _text_preservation(elems, chunks)
    assert m["equal"]["value"] is False
    assert m["precision"]["value"] == 1.0  # 字符集合相同
    assert m["recall"]["value"] == 1.0


# =========================================================================
# _heading_boundary_ratio 深度
# =========================================================================


def test_heading_boundary_ratio_signature():
    sig = inspect.signature(_heading_boundary_ratio)
    params = list(sig.parameters)
    assert params == ["elements", "chunks"]


def test_heading_boundary_ratio_return_annotation_str():
    sig = inspect.signature(_heading_boundary_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_heading_boundary_ratio_no_headings_null():
    elems = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"text": "x", "source_element_ids": ["p1"]}]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] is None
    assert m["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_with_headings():
    elems = [{"type": "heading", "element_id": "h1"}]
    m = _heading_boundary_ratio(elems, [])
    # chunks 是空 → chunk_first_ids 空 → matched = 0
    assert m["value"] == 0.0


def test_heading_boundary_ratio_perfect_match():
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_ratio_heading_not_first():
    """chunk source_element_ids 有 h1 但不是第一个。"""
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["p1", "h1"]}]
    m = _heading_boundary_ratio(elems, chunks)
    # 第一个是 p1，h1 不在 first_ids 集合 → matched = 0
    assert m["value"] == 0.0


def test_heading_boundary_ratio_partial_match():
    elems = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},  # matched
        {"text": "y", "source_element_ids": ["other"]},  # not matched h2
    ]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 0.5


def test_heading_boundary_ratio_chunk_with_empty_ids_skipped():
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "x", "source_element_ids": []},  # skipped
        {"text": "y", "source_element_ids": ["h1"]},  # matched
    ]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_ratio_chunk_with_none_ids_skipped():
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "x", "source_element_ids": None},
        {"text": "y", "source_element_ids": ["h1"]},
    ]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_ratio_chunk_missing_source_element_ids():
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "x"},  # 没有 source_element_ids
    ]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 0.0


def test_heading_boundary_ratio_keys_exact():
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elems, chunks)
    assert set(m.keys()) == {"value", "reason"}


def test_heading_boundary_ratio_duplicate_first_ids():
    """两个 chunk 都用 h1 作为 first id；h1 仍只算 matched 一次。"""
    elems = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["h1"]},
    ]
    m = _heading_boundary_ratio(elems, chunks)
    assert m["value"] == 1.0


# =========================================================================
# _silent_drop_count 深度
# =========================================================================


def test_silent_drop_count_signature():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters)
    assert params == ["by_type", "expectations"]


def test_silent_drop_count_return_annotation_str():
    sig = inspect.signature(_silent_drop_count)
    assert sig.return_annotation == "dict[str, Any]"


def test_silent_drop_count_no_expectations():
    m = _silent_drop_count({}, None)
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_dict():
    m = _silent_drop_count({}, {})
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_expectations_without_element_count():
    m = _silent_drop_count({}, {"other_field": "x"})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type():
    m = _silent_drop_count({}, {"element_count_by_type": {}})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drop_when_actual_ge_expected():
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 0


def test_silent_drop_count_drop_when_actual_lt_expected():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 2


def test_silent_drop_count_actual_more_than_expected_no_drop():
    by_type = {"paragraph": 10}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 0


def test_silent_drop_count_actual_zero():
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 5


def test_silent_drop_count_multiple_types_summed():
    by_type = {"paragraph": 3, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    m = _silent_drop_count(by_type, exp)
    assert m["value"] == 3  # 2 + 1


def test_silent_drop_count_unknown_expected_type():
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": 5, "image": 3}}
    m = _silent_drop_count(by_type, exp)
    # image: actual=0, exp=3 → drop 3
    assert m["value"] == 3


def test_silent_drop_count_int_value():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert isinstance(m["value"], int)


def test_silent_drop_count_keys_exact():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, exp)
    assert set(m.keys()) == {"value", "reason"}


def test_silent_drop_count_element_count_by_type_none():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": None}
    m = _silent_drop_count(by_type, exp)
    # expectations.get(...) or {} → {} → not expected_counts → no_expectations_element_count
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


# =========================================================================
# compute_automatic_metrics 深度
# =========================================================================


def test_compute_automatic_metrics_signature():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters)
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_automatic_metrics_return_annotation_str():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.return_annotation == "dict[str, Any]"


def test_compute_automatic_metrics_no_keyword_only():
    sig = inspect.signature(compute_automatic_metrics)
    # 所有参数都是 positional-or-keyword
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.KEYWORD_ONLY


def test_compute_automatic_metrics_defaults_image_base_dir_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_returns_dict():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(m, dict)


def test_compute_automatic_metrics_keys_on_failure_exact():
    """document=None, error=None → pipeline_success=False 但 schema_valid 等都 null。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(m.keys()) == expected


def test_compute_automatic_metrics_pipeline_success_false_when_doc_none_error_none():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_error_code_none_when_no_error():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_automatic_metrics_error_code_propagated():
    error = {"code": "file_not_found", "message": "..."}
    m = compute_automatic_metrics(None, error, "pdf", None)
    assert m["error_code"]["value"] == "file_not_found"


def test_compute_automatic_metrics_error_code_none_on_success(tmp_path):
    """有 document + 没 error → error_code 是 None。"""
    doc = {
        "source_hash": "a" * 64,
        "source_type": "pdf",
        "document_id": "d",
        "elements": [],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_automatic_metrics_pipeline_success_false_when_error_with_doc():
    """error 给定时即使 document 也给定 → pipeline_success=False。"""
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [], "chunks": [],
    }
    error = {"code": "x", "message": "y"}
    m = compute_automatic_metrics(doc, error, "pdf", None)
    assert m["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_schema_valid_pipeline_failed_reason():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["schema_valid"]["value"] is None
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_failure_reason_pipeline_failed():
    m = compute_automatic_metrics(None, None, "pdf", None)
    for name in (
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert m[name]["reason"] == "pipeline_failed", name
        assert m[name]["value"] is None, name


def test_compute_automatic_metrics_docx_locator_null_for_pdf(tmp_path):
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["docx_locator_valid_ratio"]["value"] is None
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_pdf_locator_null_for_docx(tmp_path):
    doc = {
        "source_hash": "a" * 64, "source_type": "docx", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["pdf_locator_valid_ratio"]["value"] is None
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_other_source_type_both_null():
    doc = {
        "source_hash": "a" * 64, "source_type": "text", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "text", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_minimal_success_keys():
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(m.keys()) == expected


def test_compute_automatic_metrics_element_count_total_zero_for_empty():
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 0


def test_compute_automatic_metrics_by_type_empty_for_no_elements():
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [], "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_by_type"]["value"] == {}


def test_compute_automatic_metrics_by_type_groups_multiple():
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [
            {"element_id": "p1", "type": "paragraph", "content": "x"},
            {"element_id": "p2", "type": "paragraph", "content": "y"},
            {"element_id": "h1", "type": "heading", "content": "z"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1}


def test_compute_automatic_metrics_does_not_mutate_input():
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [{"element_id": "p1", "type": "paragraph", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    original_elements_count = len(doc["elements"])
    compute_automatic_metrics(doc, None, "pdf", None)
    assert len(doc["elements"]) == original_elements_count


def test_compute_automatic_metrics_image_base_dir_param_used(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    doc = {
        "source_hash": "a" * 64, "source_type": "pdf", "document_id": "d",
        "elements": [{"element_id": "im1", "type": "image", "resource_path": "x.png"}],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert m["image_resource_exists_ratio"]["value"] == 1.0


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.metrics as m
    assert set(m.__all__) == {"compute_automatic_metrics"}


def test_module_all_is_list():
    import evaluation.metrics as m
    assert isinstance(m.__all__, list)


def test_module_imports_math():
    import evaluation.metrics as m
    assert hasattr(m, "math")


def test_module_imports_counter():
    import evaluation.metrics as m
    assert hasattr(m, "Counter")


def test_module_imports_path():
    import evaluation.metrics as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.metrics as m
    assert hasattr(m, "Any")


def test_module_docstring_present():
    import evaluation.metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_principles():
    import evaluation.metrics as m
    doc = m.__doc__
    assert "纯函数" in doc or "pure" in doc.lower()
    assert "null" in doc.lower() or "reason" in doc.lower()


def test_module_docstring_mentions_text_preservation():
    import evaluation.metrics as m
    doc = m.__doc__
    assert "text_preservation" in doc or "文本保留" in doc


def test_module_uses_future_annotations():
    import evaluation.metrics as m
    sig = inspect.signature(m.compute_automatic_metrics)
    assert isinstance(sig.return_annotation, str)


def test_module_all_entries_exported():
    import evaluation.metrics as m
    for name in m.__all__:
        assert hasattr(m, name)


def test_module_no_silence_unused():
    import evaluation.metrics as m
    assert not hasattr(m, "_silence_unused_import")


def test_module_internal_helpers_present():
    """所有内部 helper 都可在模块命名空间访问。"""
    import evaluation.metrics as m
    for name in (
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ):
        assert hasattr(m, name), name
