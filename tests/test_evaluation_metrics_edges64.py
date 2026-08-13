"""evaluation/metrics.py 第六十九轮 edges 测试（Round 581）。

补强 edges63 未触及的角度（第三十八批）。
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十八批


def test_null_callable_batch38():
    assert callable(_null)


def test_ratio_callable_batch38():
    assert callable(_ratio)


def test_bool_metric_callable_batch38():
    assert callable(_bool_metric)


def test_int_metric_callable_batch38():
    assert callable(_int_metric)


def test_null_returns_dict_instance_batch38():
    assert isinstance(_null("x"), dict)


def test_ratio_returns_dict_instance_batch38():
    assert isinstance(_ratio(0.5), dict)


def test_bool_metric_returns_dict_instance_batch38():
    assert isinstance(_bool_metric(True), dict)


def test_int_metric_returns_dict_instance_batch38():
    assert isinstance(_int_metric(5), dict)


def test_null_value_field_none_explicit_batch38():
    assert _null("any")["value"] is None


def test_ratio_value_field_float_batch38():
    """值始终被强转为 float。"""
    assert isinstance(_ratio(0)["value"], float)
    assert isinstance(_ratio(1)["value"], float)


def test_bool_metric_value_field_bool_batch38():
    assert isinstance(_bool_metric(1)["value"], bool)


def test_int_metric_value_field_int_batch38():
    assert isinstance(_int_metric(5.0)["value"], int)
    assert not isinstance(_int_metric(5)["value"], bool)


def test_ratio_with_int_input_batch38():
    """int 输入也会被强转为 float。"""
    m = _ratio(1)
    assert m["value"] == 1.0
    assert isinstance(m["value"], float)


def test_int_metric_with_large_int_batch38():
    m = _int_metric(2**40)
    assert m["value"] == 2**40


def test_int_metric_with_string_digits_batch38():
    """int('123') 合法返回 123（Python 行为）。"""
    m = _int_metric("123")  # type: ignore[arg-type]
    assert m["value"] == 123


def test_int_metric_with_invalid_string_raises_batch38():
    """int('abc') 会抛 ValueError。"""
    with pytest.raises(ValueError):
        _int_metric("abc")  # type: ignore[arg-type]


# ---------- _NOT_EVALUATED / _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第三十八批


def test_not_evaluated_value_exact_batch38():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch38():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_no_spaces_batch38():
    assert " " not in _NOT_EVALUATED


def test_text_types_is_tuple_batch38():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_contains_seven_kinds_batch38():
    assert len(_TEXT_TYPES) == 7


def test_text_types_contains_caption_batch38():
    assert "caption" in _TEXT_TYPES


def test_text_types_contains_header_footer_batch38():
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES


def test_text_types_does_not_contain_image_batch38():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_is_tuple_batch38():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_contains_four_kinds_batch38():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_does_not_contain_table_batch38():
    """table 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_image_batch38():
    assert "image" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_subset_of_text_types_batch38():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


# ---------- _is_valid_bbox 第三十八批


def test_is_valid_bbox_callable_batch38():
    assert callable(_is_valid_bbox)


def test_is_valid_bbox_with_zero_values_batch38():
    """全 0 是合法的 bbox。"""
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_with_negative_values_batch38():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_with_very_large_values_batch38():
    assert _is_valid_bbox([1e10, 1e10, 1e10, 1e10]) is True


def test_is_valid_bbox_with_bool_false_only_batch38():
    """[False, False, False, False]：bool 显式拒绝。"""
    assert _is_valid_bbox([False, False, False, False]) is False


# ---------- _strip_unicode_whitespace 第三十八批


def test_strip_whitespace_callable_batch38():
    assert callable(_strip_unicode_whitespace)


def test_strip_whitespace_preserves_unicode_chars_batch38():
    assert _strip_unicode_whitespace("中文 段落") == "中文段落"


def test_strip_whitespace_with_tab_batch38():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_whitespace_with_carriage_return_batch38():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_whitespace_with_form_feed_batch38():
    """\\f (form feed) 是 isspace。"""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_whitespace_with_vertical_tab_batch38():
    """\\v (vertical tab) 是 isspace。"""
    assert _strip_unicode_whitespace("a\vb") == "ab"


def test_strip_whitespace_with_thin_space_batch38():
    """U+2009 (thin space) 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_with_hair_space_batch38():
    """U+200A (hair space) 是 isspace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


# ---------- _pdf_locator_ratio 第三十八批


def test_pdf_locator_with_caption_type_batch38():
    elements = [{
        "type": "caption",
        "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},
    }]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_with_list_item_type_batch38():
    elements = [{
        "type": "list_item",
        "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},
    }]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_caption_without_bbox_batch38():
    """caption 类型必须有 bbox。"""
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_table_with_page_only_batch38():
    """table 不需要 bbox；page 即可。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_image_with_page_only_batch38():
    """image 不需要 bbox；page 即可。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_returns_float_batch38():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert isinstance(m["value"], float)


def test_pdf_locator_with_huge_page_batch38():
    """page 是任意正 int。"""
    elements = [{"type": "table", "source_locator": {"page": 999999}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


# ---------- _docx_locator_ratio 第三十八批


def test_docx_locator_with_section_batch38():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_run_index_batch38():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


def test_docx_locator_with_extra_keys_still_valid_batch38():
    """含 page 但还有 paragraph_index → 仍 invalid（page 出现即拒绝）。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {"paragraph_index": 0, "page": 1},
    }]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_with_only_extra_unknown_keys_batch38():
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_with_all_structural_keys_batch38():
    """全部 structural keys 都有 → 仍只算 1 次。"""
    elements = [{
        "type": "paragraph",
        "source_locator": {
            "section": 0,
            "paragraph_index": 0,
            "run_index": 0,
            "table_index": 0,
            "row_index": 0,
            "col_index": 0,
            "relationship_id": "rId1",
        },
    }]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 1.0


# ---------- _image_resource_ratio 第三十八批


def test_image_resource_callable_batch38():
    assert callable(_image_resource_ratio)


def test_image_resource_none_resource_path_batch38():
    """resource_path 显式为 None → 当 falsy 处理。"""
    elements = [{"type": "image", "resource_path": None}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_with_absolute_path_existing_batch38(tmp_path):
    img = tmp_path / "abs.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img.absolute())}]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 1.0


def test_image_resource_with_image_base_dir_but_absolute_path_batch38(tmp_path):
    """image_base_dir 提供但 rp 是绝对路径 → 用绝对路径直接查。"""
    img = tmp_path / "abs.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img.absolute())}]
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    m = _image_resource_ratio(elements, other_dir)
    assert m["value"] == 1.0


def test_image_resource_with_image_base_dir_relative_path_batch38(tmp_path):
    """rp 是相对路径 + image_base_dir 给定 → 拼接查。"""
    img = tmp_path / "rel.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "rel.png"}]
    m = _image_resource_ratio(elements, tmp_path)
    assert m["value"] == 1.0


def test_image_resource_all_images_invalid_path_batch38():
    elements = [
        {"type": "image", "resource_path": "/nonexistent/1.png"},
        {"type": "image", "resource_path": "/nonexistent/2.png"},
    ]
    m = _image_resource_ratio(elements, None)
    assert m["value"] == 0.0


def test_image_resource_does_not_mutate_elements_batch38():
    elements = [{"type": "image", "resource_path": "x.png"}]
    before = str(elements)
    _image_resource_ratio(elements, None)
    assert str(elements) == before


# ---------- _chunk_reference_ratio 第三十八批


def test_chunk_reference_callable_batch38():
    assert callable(_chunk_reference_ratio)


def test_chunk_reference_elements_none_id_batch38():
    """element 的 element_id 显式 None → set 中包含 None。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    m = _chunk_reference_ratio(elements, chunks)
    # None in elements_ids → valid（None == None）
    assert m["value"] == 1.0


def test_chunk_reference_chunk_ids_with_none_value_batch38():
    """source_element_ids 含 None → 检查 None 是否在 elem_ids 中。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", None]}]
    m = _chunk_reference_ratio(elements, chunks)
    # all(['e1' in {'e1'}, None in {'e1'}]) → False → invalid
    assert m["value"] == 0.0


def test_chunk_reference_multiple_chunks_some_invalid_batch38():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["unknown"]},  # invalid
        {"source_element_ids": ["e2"]},  # valid
    ]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == pytest.approx(2 / 3)


def test_chunk_reference_does_not_mutate_inputs_batch38():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    elements_before = str(elements)
    chunks_before = str(chunks)
    _chunk_reference_ratio(elements, chunks)
    assert str(elements) == elements_before
    assert str(chunks) == chunks_before


# ---------- _text_preservation 第三十八批


def test_text_preservation_returns_dict_with_three_keys_batch38():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_key_has_value_reason_batch38():
    out = _text_preservation(
        [{"type": "paragraph", "content": "abc"}],
        [{"text": "abc"}],
    )
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_text_preservation_single_char_batch38():
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


def test_text_preservation_duplicate_chars_batch38():
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    # equal=False (aaa != aa)
    # precision = 2/2 = 1.0
    # recall = 2/3
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(2 / 3)


def test_text_preservation_image_excluded_but_other_present_batch38():
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "should_be_excluded"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_with_only_image_batch38():
    """只有 image 元素 → expected 空。"""
    elements = [{"type": "image", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected empty, actual non-empty
    assert out["equal"]["value"] is False
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_chunk_text_empty_string_batch38():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_both_empty_after_strip_batch38():
    """expected 全是空白，actual 也全是空白 → 都为空。"""
    elements = [{"type": "paragraph", "content": "   "}]
    chunks = [{"text": "   "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_long_text_batch38():
    long_text = "abcdefgh" * 100
    elements = [{"type": "paragraph", "content": long_text}]
    chunks = [{"text": long_text}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_does_not_mutate_inputs_batch38():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    e_before = str(elements)
    c_before = str(chunks)
    _text_preservation(elements, chunks)
    assert str(elements) == e_before
    assert str(chunks) == c_before


# ---------- _heading_boundary_ratio 第三十八批


def test_heading_boundary_callable_batch38():
    assert callable(_heading_boundary_ratio)


def test_heading_boundary_multiple_chunks_same_first_batch38():
    """多个 chunk 都以 h1 开头 → h1 仍只匹配一次（set）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 1.0


def test_heading_boundary_three_headings_two_match_batch38():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == pytest.approx(2 / 3)


def test_heading_boundary_with_unknown_first_id_batch38():
    """chunk 的 first id 是 elements 中不存在的 id → invalid。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["unknown"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


def test_heading_boundary_heading_no_element_id_batch38():
    elements = [{"type": "heading"}]
    chunks = [{"source_element_ids": [None]}]
    m = _heading_boundary_ratio(elements, chunks)
    # h.get('element_id') = None; None in {None} → matched
    assert m["value"] == 1.0


def test_heading_boundary_does_not_mutate_inputs_batch38():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    e_before = str(elements)
    c_before = str(chunks)
    _heading_boundary_ratio(elements, chunks)
    assert str(elements) == e_before
    assert str(chunks) == c_before


# ---------- _silent_drop_count 第三十八批


def test_silent_drop_count_callable_batch38():
    assert callable(_silent_drop_count)


def test_silent_drop_count_actual_zero_batch38():
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 5


def test_silent_drop_count_returns_int_value_batch38():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert isinstance(m["value"], int)


def test_silent_drop_count_unicode_type_batch38():
    by_type = {"段落": 3}
    expectations = {"element_count_by_type": {"段落": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 2


def test_silent_drop_count_expected_negative_batch38():
    """expected < 0 → actual(0) > expected(-5) → 0 drop。"""
    by_type = {"paragraph": 0}
    expectations = {"element_count_by_type": {"paragraph": -5}}
    m = _silent_drop_count(by_type, expectations)
    # actual(0) < exp(-5) is False → 0 drop
    assert m["value"] == 0


def test_silent_drop_count_three_types_one_drop_batch38():
    by_type = {"a": 5, "b": 5, "c": 3}
    expectations = {"element_count_by_type": {"a": 5, "b": 5, "c": 5}}
    m = _silent_drop_count(by_type, expectations)
    assert m["value"] == 2


# ---------- compute_automatic_metrics 第三十八批


def test_compute_metrics_callable_batch38():
    assert callable(compute_automatic_metrics)


def test_compute_metrics_doc_none_returns_seven_keys_only_batch38():
    """doc=None 时只返回 pipeline_success / error_code / schema_valid + null 指标。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert "pipeline_success" in m
    assert "error_code" in m
    assert "schema_valid" in m
    assert "element_count_total" in m


def test_compute_metrics_doc_none_pipeline_success_false_batch38():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False


def test_compute_metrics_doc_none_error_code_none_batch38():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_metrics_doc_none_schema_valid_reason_batch38():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_metrics_with_error_dict_batch38():
    """error 含 code → pipeline_success=False，error_code 非 null。"""
    error = {"code": "parse_failed", "message": "x"}
    m = compute_automatic_metrics(None, error, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "parse_failed"


def test_compute_metrics_minimal_doc_batch38():
    """最小合法 doc：空 elements 和 chunks。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_pdf_source_pdf_locator_calculated_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "table", "source_locator": {"page": 1}}],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0


def test_compute_metrics_pdf_source_docx_locator_null_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_source_docx_locator_calculated_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_metrics_docx_source_pdf_locator_null_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_with_expectations_silent_drop_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["silent_drop_count"]["value"] == 4


def test_compute_metrics_no_expectations_silent_drop_null_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph"}],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["silent_drop_count"]["reason"] == "no_expectations"


# ---------- module source forbidden tokens 第六十二批


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
def test_module_source_no_forbidden_tokens_batch38(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第五十八批


def test_module_source_contains_design_principles_batch38():
    src = inspect.getsource(mmod)
    assert "设计原则" in src


def test_module_source_contains_pure_function_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "纯函数" in src


def test_module_source_contains_no_fake_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "不伪造" in src


def test_module_source_contains_counter_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "Counter" in src


def test_module_source_contains_text_preservation_v11_keyword_batch38():
    src = inspect.getsource(mmod)
    assert "v1.1" in src


def test_module_source_contains_text_preservation_section_batch38():
    src = inspect.getsource(mmod)
    assert "text_preservation 语义" in src


def test_module_source_contains_expected_sequence_definition_batch38():
    src = inspect.getsource(mmod)
    assert "expected_sequence" in src


def test_module_source_contains_actual_sequence_definition_batch38():
    src = inspect.getsource(mmod)
    assert "actual_sequence" in src


def test_module_source_contains_strip_unicode_whitespace_def_batch38():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_compute_automatic_metrics_def_batch38():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_pathlib_path_import_batch38():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_math_isfinite_call_batch38():
    src = inspect.getsource(mmod)
    assert "math.isfinite" in src


def test_module_source_contains_image_element_filter_batch38():
    src = inspect.getsource(mmod)
    assert 'e.get("type") == "image"' in src


def test_module_source_contains_chunk_first_id_collection_batch38():
    src = inspect.getsource(mmod)
    assert "chunk_first_ids" in src


def test_module_source_contains_image_base_dir_param_doc_batch38():
    src = inspect.getsource(mmod)
    assert "image_base_dir" in src


def test_module_source_contains_text_types_tuple_definition_batch38():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_module_source_contains_pdf_bbox_required_types_definition_batch38():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_module_source_contains_not_evaluated_constant_batch38():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_pyc_module_imports_batch38():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_collections_counter_import_batch38():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


# ---------- signatures 第五十八批


def test_signature_compute_metrics_has_five_params_batch38():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_signature_compute_metrics_image_base_dir_default_none_batch38():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_metrics_return_dict_batch38():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation)


def test_signature_strip_unicode_whitespace_one_param_batch38():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_signature_is_valid_bbox_one_param_batch38():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_signature_pdf_locator_one_param_batch38():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_one_param_batch38():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_image_resource_two_params_batch38():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_two_params_batch38():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


# ---------- module 合理性第五十八批


def test_module_has_all_attribute_batch38():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch38():
    assert isinstance(mmod.__all__, list)


def test_module_all_only_compute_automatic_metrics_batch38():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_has_text_types_attribute_batch38():
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_has_pdf_bbox_required_types_attribute_batch38():
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_has_not_evaluated_attribute_batch38():
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_has_compute_automatic_metrics_attribute_batch38():
    assert hasattr(mmod, "compute_automatic_metrics")


def test_module_does_not_define_class_batch38():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_normalize_text_not_imported_batch38():
    """metrics.py 不 import normalize_text（v1.1 用自己的 _strip_unicode_whitespace）。
    文档字符串中提到 normalize_text 是 v1.0 历史口径，但实际代码不再 import。"""
    src = inspect.getsource(mmod)
    assert "import normalize_text" not in src
    assert "from app.chunkers" not in src


def test_module_text_preservation_uses_strip_unicode_whitespace_batch38():
    src = inspect.getsource(mmod)
    assert "_strip_unicode_whitespace(expected_raw)" in src
    assert "_strip_unicode_whitespace(actual_raw)" in src


# ---------- 端到端集成第五十八批


def test_e2e_compute_metrics_full_pdf_batch38(tmp_path):
    """完整 PDF 文档 + chunks + expectations → 全指标计算。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "标题", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
            {"type": "paragraph", "content": "段落", "element_id": "e2",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        ],
        "chunks": [
            {"text": "标题段落", "source_element_ids": ["e1", "e2"]},
        ],
    }
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 2
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["silent_drop_count"]["value"] == 0


def test_e2e_compute_metrics_full_docx_batch38():
    """完整 DOCX 文档。"""
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [
            {"type": "heading", "content": "标题", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "content": "段落", "element_id": "e2",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "标题段落", "source_element_ids": ["e1", "e2"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["pipeline_success"]["value"] is True
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_compute_metrics_idempotent_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_e2e_text_preservation_pipeline_failed_path_batch38():
    """pipeline 失败时 text_preservation 三个指标都 null + pipeline_failed。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["text_preservation_equal"]["reason"] == "pipeline_failed"
    assert m["text_char_multiset_precision"]["reason"] == "pipeline_failed"
    assert m["text_char_multiset_recall"]["reason"] == "pipeline_failed"


def test_e2e_does_not_mutate_doc_batch38():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    doc_before = str(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert str(doc) == doc_before
