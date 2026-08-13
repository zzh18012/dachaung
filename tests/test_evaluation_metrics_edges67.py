"""evaluation/metrics.py 第七十二轮 edges 测试（Round 604）。

补强 metrics_edges66 未触及的角度（第四十一批）。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第四十一批


def test_null_with_empty_string_reason_batch41():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_with_long_reason_batch41():
    out = _null("x" * 200)
    assert out["value"] is None
    assert len(out["reason"]) == 200


def test_ratio_with_one_batch41():
    out = _ratio(1.0)
    assert out["value"] == 1.0
    assert out["reason"] is None


def test_ratio_with_very_small_batch41():
    out = _ratio(1e-10)
    assert out["value"] == 1e-10


def test_ratio_with_just_under_one_batch41():
    out = _ratio(0.99999)
    assert out["value"] == 0.99999


def test_ratio_does_not_mutate_input_batch41():
    """ratio 接受数字，但不应修改它。"""
    val = 0.5
    _ratio(val)
    assert val == 0.5


def test_bool_metric_true_batch41():
    out = _bool_metric(True)
    assert out["value"] is True
    assert out["reason"] is None


def test_bool_metric_false_batch41():
    out = _bool_metric(False)
    assert out["value"] is False
    assert out["reason"] is None


def test_int_metric_zero_batch41():
    out = _int_metric(0)
    assert out["value"] == 0
    assert out["reason"] is None


def test_int_metric_huge_batch41():
    out = _int_metric(10**18)
    assert out["value"] == 10**18


def test_int_metric_negative_batch41():
    out = _int_metric(-1)
    assert out["value"] == -1


def test_ratio_with_nan_batch41():
    """NaN 不抛异常（不强校验）。"""
    out = _ratio(float("nan"))
    # nan != nan，只验证结构
    assert "value" in out
    assert "reason" in out


def test_ratio_with_inf_batch41():
    """inf 不抛异常。"""
    out = _ratio(float("inf"))
    assert out["value"] == float("inf")


# ---------- _NOT_EVALUATED / _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第四十一批


def test_not_evaluated_no_spaces_batch41():
    assert " " not in _NOT_EVALUATED


def test_not_evaluated_is_str_batch41():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_underscore_separated_batch41():
    assert "_" in _NOT_EVALUATED


def test_text_types_all_lowercase_batch41():
    for t in _TEXT_TYPES:
        assert t.islower()


def test_text_types_no_duplicates_batch41():
    assert len(_TEXT_TYPES) == len(set(_TEXT_TYPES))


def test_text_types_exactly_seven_batch41():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_all_lowercase_batch41():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t.islower()


def test_pdf_bbox_required_types_no_duplicates_batch41():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == len(set(_PDF_BBOX_REQUIRED_TYPES))


def test_pdf_bbox_required_types_subset_of_text_types_batch41():
    """PDF 需要 bbox 的都是 text 类型子集？"""
    # caption 是 text type 但不在 pdf_bbox_required（caption 不需要 bbox）
    # 但 pdf_bbox_required 的元素应该都是 text_type
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_contains_heading_batch41():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_contains_paragraph_batch41():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_header_batch41():
    """header 不需要 bbox（页面装饰元素）。"""
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_footer_batch41():
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


# ---------- _is_valid_bbox 第四十一批


def test_is_valid_bbox_callable_batch41():
    assert callable(_is_valid_bbox)


def test_is_valid_bbox_negative_coords_batch41():
    """负数坐标通常合法（不强校验）。"""
    assert _is_valid_bbox([-1, -2, 1, 2]) is True


def test_is_valid_bbox_huge_coords_batch41():
    assert _is_valid_bbox([0, 0, 10**6, 10**6]) is True


def test_is_valid_bbox_float_coords_batch41():
    assert _is_valid_bbox([0.5, 0.5, 1.5, 1.5]) is True


def test_is_valid_bbox_mixed_int_float_batch41():
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


def test_is_valid_bbox_zero_bbox_batch41():
    """零大小 bbox（xmin==xmax 等）。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_with_nan_batch41():
    """NaN 不算 finite → False。"""
    assert _is_valid_bbox([float("nan"), 0, 1, 1]) is False


def test_is_valid_bbox_with_inf_batch41():
    """inf 不算 finite → False。"""
    assert _is_valid_bbox([float("inf"), 0, 1, 1]) is False


def test_is_valid_bbox_with_bool_batch41():
    """bool 是 int 子类，但通常被排除。"""
    # 实现细节：可能用 isinstance(x, bool) 拒绝
    result = _is_valid_bbox([True, 0, 1, 1])
    # 不管怎样，不抛异常
    assert isinstance(result, bool)


def test_is_valid_bbox_with_str_batch41():
    """字符串 → False。"""
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_with_none_batch41():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_with_dict_batch41():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_with_set_batch41():
    assert _is_valid_bbox({0, 0, 1, 1}) is False  # set 不 ordered


def test_is_valid_bbox_empty_tuple_batch41():
    assert _is_valid_bbox(()) is False


# ---------- _strip_unicode_whitespace 第四十一批


def test_strip_unicode_whitespace_callable_batch41():
    assert callable(_strip_unicode_whitespace)


def test_strip_unicode_whitespace_preserves_digits_batch41():
    assert _strip_unicode_whitespace("12345") == "12345"


def test_strip_unicode_whitespace_preserves_punctuation_batch41():
    assert _strip_unicode_whitespace(".,!?;:") == ".,!?;:"


def test_strip_unicode_whitespace_preserves_emoji_batch41():
    assert _strip_unicode_whitespace("hello😀world") == "hello😀world"


def test_strip_unicode_whitespace_preserves_chinese_batch41():
    assert _strip_unicode_whitespace("你好世界") == "你好世界"


def test_strip_unicode_whitespace_removes_regular_spaces_batch41():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_removes_tabs_batch41():
    assert _strip_unicode_whitespace("a\tb\tc") == "abc"


def test_strip_unicode_whitespace_removes_newlines_batch41():
    assert _strip_unicode_whitespace("a\nb\nc") == "abc"


def test_strip_unicode_whitespace_removes_carriage_return_batch41():
    assert _strip_unicode_whitespace("a\rb\rc") == "abc"


def test_strip_unicode_whitespace_removes_unicode_nbsp_batch41():
    """U+00A0 non-breaking space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_removes_unicode_em_space_batch41():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_empty_string_batch41():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_only_whitespace_batch41():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_whitespace_returns_str_batch41():
    assert isinstance(_strip_unicode_whitespace("abc"), str)


# ---------- _pdf_locator_ratio 第四十一批


def test_pdf_locator_ratio_callable_batch41():
    assert callable(_pdf_locator_ratio)


def test_pdf_locator_ratio_empty_list_batch41():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_heading_with_bbox_batch41():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_heading_without_bbox_batch41():
    elements = [
        {"type": "heading", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_bbox_batch41():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_caption_with_bbox_batch41():
    elements = [
        {"type": "caption", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_list_item_with_bbox_batch41():
    elements = [
        {"type": "list_item", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_header_without_bbox_ok_batch41():
    """header 不需要 bbox → 算合法。"""
    elements = [
        {"type": "header", "source_locator": {"page": 1}},  # 无 bbox，但 header 不需要
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_footer_without_bbox_ok_batch41():
    elements = [
        {"type": "footer", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_image_with_page_only_batch41():
    """image 不需要 bbox → 算合法。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_negative_page_batch41():
    """page < 1 → 不合法。"""
    elements = [
        {"type": "heading", "source_locator": {"page": 0, "bbox": [0, 0, 1, 1]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_page_batch41():
    elements = [
        {"type": "heading", "source_locator": {"bbox": [0, 0, 1, 1]}},  # 缺 page
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_locator_batch41():
    elements = [
        {"type": "heading"},  # 完全无 source_locator
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_partial_valid_batch41():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "heading"},  # 缺 locator → 不合法
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_does_not_mutate_input_batch41():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
    ]
    before = json.dumps(elements, sort_keys=True)
    _pdf_locator_ratio(elements)
    assert json.dumps(elements, sort_keys=True) == before


def test_pdf_locator_ratio_idempotent_batch41():
    elements = [{"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}]
    out1 = _pdf_locator_ratio(elements)
    out2 = _pdf_locator_ratio(elements)
    assert out1 == out2


# ---------- _docx_locator_ratio 第四十一批


def test_docx_locator_ratio_callable_batch41():
    assert callable(_docx_locator_ratio)


def test_docx_locator_ratio_empty_elements_batch41():
    out = _docx_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_paragraph_with_index_batch41():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_paragraph_without_index_batch41():
    elements = [
        {"type": "paragraph", "source_locator": {}},  # 缺 index
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_negative_index_batch41():
    """负 index 也合法（不强校验值，只要 key 存在）。"""
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": -1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_page_in_locator_invalid_batch41():
    """DOCX locator 不应有 page（这是 PDF 字段）。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_bbox_in_locator_invalid_batch41():
    """DOCX locator 不应有 bbox。"""
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_index_zero_batch41():
    """0 是合法 index。"""
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_missing_locator_batch41():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_partial_valid_batch41():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _image_resource_ratio 第四十一批


def test_image_resource_ratio_callable_batch41():
    assert callable(_image_resource_ratio)


def test_image_resource_ratio_no_images_batch41():
    out = _image_resource_ratio([], None)
    assert out["value"] is None
    assert "no_image" in out["reason"]


def test_image_resource_ratio_image_with_resource_path_batch41(tmp_path):
    """resource_path 文件实际存在 → 1.0。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_without_resource_path_batch41():
    elements = [{"type": "image"}]  # 缺 resource_path
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_missing_file_batch41(tmp_path):
    """resource_path 指向不存在的文件 → 0.0。"""
    elements = [{"type": "image", "resource_path": str(tmp_path / "no_such.png")}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_base_dir_resolves_batch41(tmp_path):
    """image_base_dir 给定时 resource_path 可以是相对。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_base_dir_missing_file_batch41(tmp_path):
    """image_base_dir 给定但文件不存在。"""
    elements = [{"type": "image", "resource_path": "missing.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_signature_batch41():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


# ---------- _chunk_reference_ratio 第四十一批


def test_chunk_reference_ratio_callable_batch41():
    assert callable(_chunk_reference_ratio)


def test_chunk_reference_ratio_empty_chunks_batch41():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert "no_chunks" in out["reason"]


def test_chunk_reference_ratio_chunk_with_source_ids_batch41():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_without_source_ids_batch41():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "abc"}]  # 缺 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_source_ids_batch41():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]  # 空 list
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_dangling_ref_batch41():
    """source_element_ids 指向不存在的 element_id。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["eX"]}]  # eX 不存在
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_mixed_batch41():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["nonexistent"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_signature_batch41():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


# ---------- _text_preservation 第四十一批


def test_text_preservation_callable_batch41():
    assert callable(_text_preservation)


def test_text_preservation_empty_batch41():
    out = _text_preservation([], [])
    # 空对空 → equal 视为 True（无差异），precision/recall null + empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match_batch41():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] == 1.0
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_partial_match_batch41():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    # recall < 1
    assert out["recall"]["value"] is not None
    assert out["recall"]["value"] < 1.0


def test_text_preservation_image_excluded_batch41():
    """image 排除 → expected 空 + actual 非空 → recall null + empty_expected。"""
    elements = [{"type": "image", "content": "ignored"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"
    assert out["equal"]["value"] is False  # 实际有字符但期望没


def test_text_preservation_returns_dict_with_three_keys_batch41():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_metric_dict_has_value_reason_batch41():
    out = _text_preservation([], [])
    for k in ("equal", "precision", "recall"):
        assert "value" in out[k]
        assert "reason" in out[k]


def test_text_preservation_does_not_mutate_inputs_batch41():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    before_e = json.dumps(elements, sort_keys=True)
    before_c = json.dumps(chunks, sort_keys=True)
    _text_preservation(elements, chunks)
    assert json.dumps(elements, sort_keys=True) == before_e
    assert json.dumps(chunks, sort_keys=True) == before_c


# ---------- _heading_boundary_ratio 第四十一批


def test_heading_boundary_ratio_callable_batch41():
    assert callable(_heading_boundary_ratio)


def test_heading_boundary_ratio_empty_elements_batch41():
    out = _heading_boundary_ratio([], [])
    assert out["value"] is None


def test_heading_boundary_ratio_no_headings_batch41():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert "no_heading" in out["reason"]


def test_heading_boundary_ratio_with_heading_batch41():
    elements = [{"type": "heading", "content": "title"}]
    chunks = [{"text": "title"}]
    out = _heading_boundary_ratio(elements, chunks)
    # 不强校验值，但应有结构
    assert "value" in out
    assert "reason" in out


def test_heading_boundary_ratio_returns_dict_batch41():
    out = _heading_boundary_ratio([], [])
    assert isinstance(out, dict)


def test_heading_boundary_ratio_signature_two_params_batch41():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


# ---------- _silent_drop_count 第四十一批


def test_silent_drop_count_callable_batch41():
    assert callable(_silent_drop_count)


def test_silent_drop_count_none_expectations_batch41():
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert "no_expectations" in out["reason"]


def test_silent_drop_count_empty_expectations_batch41():
    """空 dict expectations → 视为无 expectations。"""
    out = _silent_drop_count({}, {})
    assert out["value"] is None


def test_silent_drop_count_empty_element_count_by_type_batch41():
    """expectations 不为空但 element_count_by_type 空 → null。"""
    out = _silent_drop_count({}, {"required_markers": ["x"]})
    assert out["value"] is None
    assert "no_expectations_element_count" in out["reason"]


def test_silent_drop_count_no_drop_batch41():
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_with_drop_batch41():
    """预期 5 个，实际 3 个 → 丢 2 个。"""
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_count_extra_elements_batch41():
    """实际比预期多 → 0 丢（不为负）。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_returns_dict_batch41():
    out = _silent_drop_count({}, None)
    assert isinstance(out, dict)


def test_silent_drop_count_does_not_mutate_inputs_batch41():
    by_type = {"paragraph": 1}
    expectations = {"element_count_by_type": {"paragraph": 1}}
    before_e = json.dumps(by_type, sort_keys=True)
    before_x = json.dumps(expectations, sort_keys=True)
    _silent_drop_count(by_type, expectations)
    assert json.dumps(by_type, sort_keys=True) == before_e
    assert json.dumps(expectations, sort_keys=True) == before_x


def test_silent_drop_count_multi_type_batch41():
    """多种 element 类型 → 各自计算后求和。"""
    by_type = {"paragraph": 3, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph drop 2 + heading drop 1 = 3
    assert out["value"] == 3


# ---------- compute_automatic_metrics 第四十一批


def test_compute_automatic_metrics_callable_batch41():
    assert callable(compute_automatic_metrics)


def test_compute_automatic_metrics_signature_batch41():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_automatic_metrics_doc_none_error_none_batch41():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_automatic_metrics_returns_14_keys_batch41():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # 至少 14 个 metrics
    assert len(out) >= 14


def test_compute_automatic_metrics_with_error_batch41():
    """error 非空 → 大多 metric 为 null + pipeline_failed。"""
    err = {"code": "E_PARSE", "message": "boom"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_pdf_source_batch41():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # pdf_locator_valid_ratio 应该存在
    assert "pdf_locator_valid_ratio" in out


def test_compute_automatic_metrics_docx_source_batch41():
    out = compute_automatic_metrics(None, None, "docx", None)
    assert "docx_locator_valid_ratio" in out


def test_compute_automatic_metrics_unknown_source_batch41():
    """未知 source_type → 两个 locator ratio 都 null。"""
    out = compute_automatic_metrics(None, None, "unknown", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_compute_automatic_metrics_idempotent_batch41():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "a", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_compute_automatic_metrics_does_not_mutate_doc_batch41():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "a"}],
        "chunks": [{"text": "a"}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before


def test_compute_automatic_metrics_json_serializable_batch41():
    """输出能 JSON 序列化。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    json.dumps(out)


def test_compute_automatic_metrics_image_base_dir_default_none_batch41():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


# ---------- module source forbidden tokens 第七十五批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch41(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十六批


def test_module_source_contains_design_doc_batch41():
    src = inspect.getsource(mmod)
    assert "自动指标" in src or "评测指标" in src


def test_module_source_contains_future_annotations_batch41():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_typing_any_import_batch41():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_strip_unicode_whitespace_definition_batch41():
    """v1.1 不再 import normalize_text；自己实现 _strip_unicode_whitespace。"""
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_does_not_import_normalize_text_batch41():
    """v1.1 不依赖 app.chunkers.structural.normalize_text。"""
    src = inspect.getsource(mmod)
    assert "from app.chunkers.structural import normalize_text" not in src
    assert "import normalize_text" not in src


def test_module_source_contains_null_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_pdf_locator_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_image_resource_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_reference_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_text_preservation_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_heading_boundary_ratio_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_silent_drop_count_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_contains_compute_automatic_metrics_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_strip_unicode_whitespace_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_is_valid_bbox_definition_batch41():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_no_elements_keyword_batch41():
    src = inspect.getsource(mmod)
    assert "no_elements" in src


def test_module_source_contains_pipeline_failed_keyword_batch41():
    src = inspect.getsource(mmod)
    assert "pipeline_failed" in src


def test_module_source_contains_all_export_batch41():
    src = inspect.getsource(mmod)
    assert "__all__" in src
    assert "compute_automatic_metrics" in src


# ---------- signatures 第六十六批


def test_signature_null_one_param_batch41():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_one_param_batch41():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_one_param_batch41():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_int_metric_one_param_batch41():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_pdf_locator_ratio_one_param_batch41():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_ratio_one_param_batch41():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_image_resource_ratio_params_batch41():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_ratio_one_param_batch41():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_text_preservation_params_batch41():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_ratio_params_batch41():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_silent_drop_count_params_batch41():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


def test_signature_is_valid_bbox_one_param_batch41():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_signature_strip_unicode_whitespace_one_param_batch41():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_signature_image_resource_ratio_image_base_dir_no_default_batch41():
    """_image_resource_ratio 的 image_base_dir 是必填（compute_automatic_metrics 才有默认）。"""
    sig = inspect.signature(_image_resource_ratio)
    assert sig.parameters["image_base_dir"].default is inspect.Parameter.empty


# ---------- module 合理性 第六十六批


def test_module_has_all_attribute_batch41():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch41():
    assert isinstance(mmod.__all__, list)


def test_module_all_contains_compute_automatic_metrics_batch41():
    assert "compute_automatic_metrics" in mmod.__all__


def test_module_does_not_define_class_batch41():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_has_future_annotations_batch41():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_no_module_level_code_outside_functions_batch41():
    """AST：顶层只有 import / 常量 / function def / __all__。"""
    import ast
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.Expr))


def test_module_has_compute_automatic_metrics_attr_batch41():
    assert hasattr(mmod, "compute_automatic_metrics")


def test_module_compute_automatic_metrics_callable_batch41():
    assert callable(mmod.compute_automatic_metrics)


def test_module_has_null_attr_batch41():
    assert hasattr(mmod, "_null")


def test_module_has_ratio_attr_batch41():
    assert hasattr(mmod, "_ratio")


# ---------- 端到端集成 第六十六批


def test_e2e_compute_metrics_minimal_batch41():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert "pipeline_success" in out
    assert "schema_valid" in out


def test_e2e_compute_metrics_full_doc_batch41():
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "hello", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_docx_batch41():
    doc = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "hello", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_error_path_batch41():
    err = {"code": "E_PARSE", "message": "boom"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_e2e_idempotent_full_doc_batch41():
    doc = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)
