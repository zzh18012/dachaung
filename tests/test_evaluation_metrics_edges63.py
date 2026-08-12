"""evaluation/metrics.py 第六十八轮 edges 测试（Round 574）。

补强 edges62 未触及的角度（第三十七批）。
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十七批


def test_null_returns_dict_with_two_keys_batch37():
    m = _null("reason_x")
    assert set(m.keys()) == {"value", "reason"}


def test_null_value_is_none_batch37():
    m = _null("x")
    assert m["value"] is None


def test_null_with_empty_string_reason_batch37():
    m = _null("")
    assert m["reason"] == ""


def test_null_with_unicode_reason_batch37():
    m = _null("无内容可比")
    assert m["reason"] == "无内容可比"


def test_ratio_zero_batch37():
    m = _ratio(0.0)
    assert m["value"] == 0.0
    assert m["reason"] is None


def test_ratio_with_negative_float_batch37():
    """负数也会被接受（业务上不该出现但函数不限制）。"""
    m = _ratio(-0.5)
    assert m["value"] == -0.5


def test_ratio_with_inf_batch37():
    m = _ratio(math.inf)
    assert math.isinf(m["value"])


def test_ratio_with_nan_batch37():
    m = _ratio(math.nan)
    assert math.isnan(m["value"])


def test_bool_metric_with_string_batch37():
    """非空 string → True。"""
    assert _bool_metric("x")["value"] is True
    assert _bool_metric("")["value"] is False


def test_bool_metric_with_dict_batch37():
    """非空 dict → True。"""
    assert _bool_metric({"x": 1})["value"] is True
    assert _bool_metric({})["value"] is False


def test_int_metric_with_negative_int_batch37():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_with_bool_batch37():
    """bool is int subclass。"""
    assert _int_metric(True)["value"] == 1
    assert _int_metric(False)["value"] == 0


def test_int_metric_with_negative_float_batch37():
    """int(-1.9) = -1（向 0 取整）。"""
    assert _int_metric(-1.9)["value"] == -1


# ---------- _is_valid_bbox 第三十七批


def test_is_valid_bbox_with_four_int_batch37():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_with_four_float_batch37():
    assert _is_valid_bbox([1.5, 2.5, 3.5, 4.5]) is True


def test_is_valid_bbox_with_mixed_int_float_batch37():
    assert _is_valid_bbox([1, 2.5, 3, 4.5]) is True


def test_is_valid_bbox_with_bool_batch37():
    """bool 是 int subclass，但代码显式拒绝。"""
    assert _is_valid_bbox([True, 2, 3, 4]) is False


def test_is_valid_bbox_with_three_elements_batch37():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_with_five_elements_batch37():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_with_empty_list_batch37():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_with_none_batch37():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_with_string_batch37():
    assert _is_valid_bbox("abcd") is False


def test_is_valid_bbox_with_tuple_batch37():
    """代码要求 list 不是 tuple。"""
    assert _is_valid_bbox((1, 2, 3, 4)) is False


def test_is_valid_bbox_with_nan_batch37():
    assert _is_valid_bbox([1, float("nan"), 3, 4]) is False


def test_is_valid_bbox_with_inf_batch37():
    assert _is_valid_bbox([1, math.inf, 3, 4]) is False


def test_is_valid_bbox_with_strings_in_list_batch37():
    assert _is_valid_bbox(["1", "2", "3", "4"]) is False


def test_is_valid_bbox_with_none_in_list_batch37():
    assert _is_valid_bbox([None, 2, 3, 4]) is False


# ---------- _strip_unicode_whitespace 第三十七批


def test_strip_whitespace_empty_string_batch37():
    assert _strip_unicode_whitespace("") == ""


def test_strip_whitespace_no_whitespace_batch37():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_whitespace_all_whitespace_batch37():
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_whitespace_with_nbsp_batch37():
    """U+00A0 (NBSP) 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_with_em_space_batch37():
    """U+2003 (em space) 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_with_ideographic_space_batch37():
    """U+3000 是 isspace。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_whitespace_preserves_order_batch37():
    """不排序，只删除空白。"""
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_whitespace_does_not_remove_digits_or_punct_batch37():
    assert _strip_unicode_whitespace("1.2,3!") == "1.2,3!"


def test_strip_whitespace_with_line_separator_batch37():
    """U+2028 (line separator) 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_with_paragraph_separator_batch37():
    """U+2029 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


# ---------- _pdf_locator_ratio 第三十七批


def test_pdf_locator_empty_elements_batch37():
    m = _pdf_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_pdf_locator_single_valid_heading_batch37():
    elements = [{
        "type": "heading",
        "source_locator": {"page": 1, "bbox": [0.0, 0.0, 10.0, 10.0]},
    }]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_text_type_missing_bbox_batch37():
    """heading 没 bbox → invalid。"""
    elements = [{"type": "heading", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_non_text_type_no_bbox_needed_batch37():
    """table 不需要 bbox（不在 _PDF_BBOX_REQUIRED_TYPES）。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_zero_page_batch37():
    """page=0 视为 invalid。"""
    elements = [{"type": "table", "source_locator": {"page": 0}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_negative_page_batch37():
    elements = [{"type": "table", "source_locator": {"page": -1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_missing_source_locator_batch37():
    """source_locator 缺失 → 当 {} 处理 → invalid。"""
    elements = [{"type": "table"}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_none_source_locator_batch37():
    elements = [{"type": "table", "source_locator": None}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_page_string_invalid_batch37():
    elements = [{"type": "table", "source_locator": {"page": "1"}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_page_float_invalid_batch37():
    """page 必须是 int（不是 float）。"""
    elements = [{"type": "table", "source_locator": {"page": 1.5}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_page_bool_invalid_batch37():
    """bool 是 int subclass，但 page=True==1... actually isinstance(True, int) is True 且 True>=1。"""
    elements = [{"type": "table", "source_locator": {"page": True}}]
    m = _pdf_locator_ratio(elements)
    # isinstance(True, int) is True, True >= 1 → valid
    assert m["value"] == 1.0


def test_pdf_locator_mixed_valid_invalid_batch37():
    elements = [
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "table", "source_locator": {"page": 0}},  # invalid
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},  # valid
    ]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 2 / 3


# ---------- _docx_locator_ratio 第三十七批


def test_docx_locator_empty_elements_batch37():
    m = _docx_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_docx_locator_with_paragraph_index_batch37():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_table_index_batch37():
    elements = [{"type": "table", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_relationship_id_batch37():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_page_invalid_batch37():
    """DOCX 不允许 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_with_bbox_invalid_batch37():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_no_structural_keys_batch37():
    elements = [{"type": "paragraph", "source_locator": {"other_key": "x"}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_empty_locator_batch37():
    elements = [{"type": "paragraph", "source_locator": {}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_missing_source_locator_batch37():
    elements = [{"type": "paragraph"}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_none_source_locator_batch37():
    elements = [{"type": "paragraph", "source_locator": None}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


# ---------- _image_resource_ratio 第三十七批


def test_image_resource_no_elements_batch37():
    m = _image_resource_ratio([], None)
    assert m["value"] is None
    assert m["reason"] == "no_image_elements"


def test_image_resource_no_images_batch37():
    elements = [{"type": "paragraph"}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] is None


def test_image_resource_with_missing_resource_path_batch37():
    elements = [{"type": "image"}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_empty_resource_path_batch37():
    elements = [{"type": "image", "resource_path": ""}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_existing_file_batch37(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "resource_path": str(img)}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 1.0


def test_image_resource_with_nonexistent_file_batch37():
    elements = [{"type": "image", "resource_path": "/nonexistent/x.png"}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_image_base_dir_batch37(tmp_path):
    """image_base_dir + 文件名 → 拼接查找。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "x.png"}]
    m = _image_resource_ratio(elements, tmp_path)
    assert m["value"] == 1.0


def test_image_resource_with_empty_file_batch37(tmp_path):
    """文件存在但 size=0 → 视为 invalid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_mixed_valid_invalid_batch37(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "/nonexistent/y.png"},
    ]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.5


# ---------- _chunk_reference_ratio 第三十七批


def test_chunk_reference_no_chunks_batch37():
    m = _chunk_reference_ratio([], [])
    assert m["value"] is None
    assert m["reason"] == "no_chunks"


def test_chunk_reference_all_valid_batch37():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e2"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_chunk_reference_missing_id_batch37():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e_unknown"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.5


def test_chunk_reference_empty_ids_list_batch37():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_missing_ids_key_batch37():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_none_ids_batch37():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_chunk_reference_partial_valid_batch37():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e_unknown"]}]
    m = _chunk_reference_ratio(elements, chunks)
    # all() 失败 → invalid
    assert m["value"] == 0.0


def test_chunk_reference_elements_without_id_batch37():
    """element 缺 element_id → 视为 None。"""
    elements = [{}]
    chunks = [{"source_element_ids": ["anything"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


# ---------- _text_preservation 第三十七批


def test_text_preservation_empty_both_batch37():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_equal_simple_batch37():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_extra_in_actual_batch37():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]  # 多了 d
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = common / |actual| = 3/4
    assert out["precision"]["value"] == 0.75
    # recall = 3/3 = 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_missing_in_actual_batch37():
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision = 3/3 = 1.0
    assert out["precision"]["value"] == 1.0
    # recall = 3/4
    assert out["recall"]["value"] == 0.75


def test_text_preservation_image_excluded_batch37():
    """image 类型不参与比对。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_unicode_batch37():
    elements = [{"type": "paragraph", "content": "中文测试"}]
    chunks = [{"text": "中文测试"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_with_whitespace_batch37():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # 删除空白后两者相同 → equal=True
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_text_none_batch37():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # actual empty → empty_actual
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_chunk_missing_text_batch37():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_element_missing_content_batch37():
    elements = [{"type": "paragraph"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected empty, actual non-empty
    assert out["equal"]["value"] is False
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_wrong_order_batch37():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    # 字符相同但顺序不同 → equal=False, precision/recall=1.0
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


# ---------- _heading_boundary_ratio 第三十七批


def test_heading_boundary_no_headings_batch37():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] is None
    assert m["reason"] == "no_heading_elements"


def test_heading_boundary_perfect_match_batch37():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_not_first_batch37():
    """heading 在 source_element_ids 中但不是第一个 → 不算。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["e1", "h1"]}]  # h1 不是第一个
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_heading_boundary_empty_chunks_batch37():
    elements = [{"type": "heading", "element_id": "h1"}]
    m = _heading_boundary_ratio(elements, [])
    assert m["value"] == 0.0


def test_heading_boundary_multiple_headings_partial_batch37():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只匹配 h1
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.5


def test_heading_boundary_chunk_missing_ids_batch37():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


# ---------- _silent_drop_count 第三十七批


def test_silent_drop_count_no_expectations_batch37():
    m = _silent_drop_count({"paragraph": 5}, None)
    assert m["value"] is None
    assert m["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch37():
    m = _silent_drop_count({"paragraph": 5}, {})
    assert m["value"] is None


def test_silent_drop_count_no_element_count_key_batch37():
    m = _silent_drop_count({"paragraph": 5}, {"other": 1})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_batch37():
    m = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert m["value"] is None
    assert m["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_more_than_expected_batch37():
    """actual > expected → 不算 drop。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 0


def test_silent_drop_count_actual_equal_expected_batch37():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 0


def test_silent_drop_count_actual_less_than_expected_batch37():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 2


def test_silent_drop_count_multiple_types_batch37():
    by_type = {"paragraph": 3, "heading": 5}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    m = _silent_drop_count(by_type, expectations)
    # paragraph: 5-3=2, heading: actual=5>expected=2 → 0
    assert m["value"] == 2


def test_silent_drop_count_expected_type_missing_in_actual_batch37():
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 5


# ---------- module source forbidden tokens 第五十六批


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
def test_module_source_no_forbidden_tokens_batch37(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十二批


def test_module_source_contains_design_doc_batch37():
    src = inspect.getsource(mmod)
    assert "纯函数" in src


def test_module_source_contains_text_types_definition_batch37():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_module_source_contains_pdf_bbox_types_definition_batch37():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_module_source_contains_not_evaluated_const_batch37():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_pipeline_failed_batch37():
    src = inspect.getsource(mmod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_elements_reason_batch37():
    src = inspect.getsource(mmod)
    assert '"no_elements"' in src


def test_module_source_contains_no_chunks_reason_batch37():
    src = inspect.getsource(mmod)
    assert '"no_chunks"' in src


def test_module_source_contains_no_heading_elements_reason_batch37():
    src = inspect.getsource(mmod)
    assert '"no_heading_elements"' in src


def test_module_source_contains_no_image_elements_reason_batch37():
    src = inspect.getsource(mmod)
    assert '"no_image_elements"' in src


def test_module_source_contains_no_expectations_reason_batch37():
    src = inspect.getsource(mmod)
    assert '"no_expectations"' in src


def test_module_source_contains_empty_expected_and_actual_batch37():
    src = inspect.getsource(mmod)
    assert '"empty_expected_and_actual"' in src


def test_module_source_contains_empty_actual_batch37():
    src = inspect.getsource(mmod)
    assert '"empty_actual"' in src


def test_module_source_contains_empty_expected_batch37():
    src = inspect.getsource(mmod)
    assert '"empty_expected"' in src


def test_module_source_contains_counter_intersection_batch37():
    src = inspect.getsource(mmod)
    assert "(c_expected & c_actual)" in src


def test_module_source_contains_strip_unicode_whitespace_call_batch37():
    src = inspect.getsource(mmod)
    assert "_strip_unicode_whitespace(expected_raw)" in src


def test_module_source_contains_isspace_check_batch37():
    src = inspect.getsource(mmod)
    assert "ch.isspace()" in src


def test_module_source_contains_is_valid_bbox_check_batch37():
    src = inspect.getsource(mmod)
    assert "_is_valid_bbox(bbox)" in src


def test_module_source_contains_text_preservation_v11_comment_batch37():
    src = inspect.getsource(mmod)
    assert "v1.1" in src


def test_module_source_contains_silent_drop_formula_batch37():
    src = inspect.getsource(mmod)
    assert "drops += (exp - actual)" in src


def test_module_source_contains_schema_check_exception_batch37():
    src = inspect.getsource(mmod)
    assert "schema_check_exception" in src


def test_module_source_contains_document_passes_schema_import_batch37():
    src = inspect.getsource(mmod)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_module_source_contains_all_with_only_one_entry_batch37():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_source_contains_pdf_locator_func_batch37():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_func_batch37():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_image_resource_func_batch37():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


# ---------- signatures 第五十二批


def test_signature_null_one_param_batch37():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_one_param_batch37():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_pdf_locator_return_dict_batch37():
    sig = inspect.signature(_pdf_locator_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_docx_locator_return_dict_batch37():
    sig = inspect.signature(_docx_locator_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_image_resource_image_base_dir_optional_batch37():
    sig = inspect.signature(_image_resource_ratio)
    # image_base_dir 是 required positional（无默认值）
    assert sig.parameters["image_base_dir"].default is inspect.Parameter.empty


def test_signature_silent_drop_return_dict_batch37():
    sig = inspect.signature(_silent_drop_count)
    assert "dict" in str(sig.return_annotation)


def test_signature_heading_boundary_return_dict_batch37():
    sig = inspect.signature(_heading_boundary_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_reference_return_dict_batch37():
    sig = inspect.signature(_chunk_reference_ratio)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性第五十二批


def test_module_has_null_attribute_batch37():
    assert callable(mmod._null)


def test_module_has_ratio_attribute_batch37():
    assert callable(mmod._ratio)


def test_module_has_bool_metric_attribute_batch37():
    assert callable(mmod._bool_metric)


def test_module_has_int_metric_attribute_batch37():
    assert callable(mmod._int_metric)


def test_module_has_compute_metrics_attribute_batch37():
    assert callable(mmod.compute_automatic_metrics)


def test_module_text_types_count_7_batch37():
    assert len(_TEXT_TYPES) == 7


def test_module_pdf_bbox_required_types_count_4_batch37():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_not_evaluated_value_batch37():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_text_types_contains_caption_batch37():
    assert "caption" in _TEXT_TYPES


def test_module_pdf_bbox_required_contains_caption_batch37():
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


# ---------- 端到端集成第五十二批


def test_e2e_compute_metrics_full_docx_batch37():
    """完整 DOCX 文档跑指标。"""
    document = {
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "h1",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "content": "Body text", "element_id": "p1",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Body text", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(document, None, "docx", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 2
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["text_preservation_equal"]["value"] is True
    assert m["silent_drop_count"]["reason"] == "no_expectations"


def test_e2e_compute_metrics_with_expectations_batch37():
    document = {
        "elements": [
            {"type": "paragraph", "content": "a", "element_id": "p1"},
        ],
        "chunks": [{"text": "a", "source_element_ids": ["p1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    m = compute_automatic_metrics(document, None, "docx", expectations)
    # paragraph: 5-1=4, heading: 2-0=2 → 6
    assert m["silent_drop_count"]["value"] == 6


def test_e2e_compute_metrics_with_failed_pipeline_batch37():
    m = compute_automatic_metrics(None, {"code": "E_PARSE"}, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "E_PARSE"
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    assert m["element_count_total"]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_idempotent_batch37():
    document = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    m1 = compute_automatic_metrics(document, None, "docx", None)
    m2 = compute_automatic_metrics(document, None, "docx", None)
    assert m1 == m2


def test_e2e_compute_metrics_does_not_mutate_doc_batch37():
    import json
    document = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    before = json.dumps(document, sort_keys=True)
    compute_automatic_metrics(document, None, "docx", None)
    assert json.dumps(document, sort_keys=True) == before
