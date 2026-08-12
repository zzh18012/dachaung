"""evaluation/metrics.py 第五十九轮 edges 测试（Round 540）。

补强 edges57 未触及的角度（第三十二批）。
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any

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


# ---------- _TEXT_TYPES 第三十二批 ----------


def test_text_types_is_tuple_batch32():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_contains_header_batch32():
    assert "header" in _TEXT_TYPES


def test_text_types_contains_footer_batch32():
    assert "footer" in _TEXT_TYPES


def test_text_types_contains_caption_batch32():
    assert "caption" in _TEXT_TYPES


def test_text_types_contains_list_item_batch32():
    assert "list_item" in _TEXT_TYPES


def test_text_types_contains_table_batch32():
    assert "table" in _TEXT_TYPES


def test_text_types_heading_first_batch32():
    """heading 在首位。"""
    assert _TEXT_TYPES[0] == "heading"


def test_text_types_paragraph_second_batch32():
    """paragraph 在第二位。"""
    assert _TEXT_TYPES[1] == "paragraph"


def test_text_types_does_not_contain_image_batch32():
    assert "image" not in _TEXT_TYPES


def test_text_types_all_strings_batch32():
    for t in _TEXT_TYPES:
        assert isinstance(t, str)


# ---------- _PDF_BBOX_REQUIRED_TYPES 第三十二批 ----------


def test_pdf_bbox_required_types_is_tuple_batch32():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_contains_caption_batch32():
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_contains_list_item_batch32():
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_paragraph_index_batch32():
    """paragraph 索引位置。"""
    assert _PDF_BBOX_REQUIRED_TYPES.index("paragraph") == 1


def test_pdf_bbox_required_types_list_item_last_batch32():
    """list_item 在末位。"""
    assert _PDF_BBOX_REQUIRED_TYPES[-1] == "list_item"


def test_pdf_bbox_required_types_subset_of_text_types_batch32():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_does_not_contain_table_batch32():
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_header_batch32():
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


# ---------- _NOT_EVALUATED 第三十二批 ----------


def test_not_evaluated_constant_value_batch32():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch32():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_has_underscore_batch32():
    assert "_" in _NOT_EVALUATED


def test_not_evaluated_module_level_batch32():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


# ---------- 构造器第三十二批 ----------


def test_null_reason_arbitrary_string_batch32():
    out = _null("custom_reason_42")
    assert out["value"] is None
    assert out["reason"] == "custom_reason_42"


def test_null_returns_dict_batch32():
    assert isinstance(_null("x"), dict)


def test_null_keys_count_batch32():
    assert len(_null("x")) == 2


def test_ratio_half_batch32():
    out = _ratio(0.5)
    assert out["value"] == 0.5
    assert out["reason"] is None


def test_ratio_returns_float_batch32():
    """即使传 int，也强制 float。"""
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_ratio_value_annotation_unchanged_batch32():
    out = _ratio(0.0)
    assert out["value"] == 0.0


def test_bool_metric_accepts_int_batch32():
    """bool(int) 容许 → True/False。"""
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_accepts_string_batch32():
    out = _bool_metric("non-empty")
    assert out["value"] is True


def test_int_metric_large_value_batch32():
    out = _int_metric(10**18)
    assert out["value"] == 10**18


def test_int_metric_returns_int_batch32():
    out = _int_metric(5)
    assert isinstance(out["value"], int)


def test_int_metric_negative_value_batch32():
    out = _int_metric(-100)
    assert out["value"] == -100


# ---------- compute_automatic_metrics 第三十二批 ----------


def test_compute_automatic_metrics_error_with_code_only_batch32():
    """document=None，error={"code": "X"} → pipeline_success=False, error_code=X。"""
    out = compute_automatic_metrics(None, {"code": "X"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "X"


def test_compute_automatic_metrics_schema_valid_pipeline_failed_batch32():
    out = compute_automatic_metrics(None, {"code": "X"}, "pdf", None)
    assert out["schema_valid"]["value"] is None
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_automatic_metrics_no_modification_to_chunks_batch32():
    doc = {
        "elements": [{"type": "paragraph", "content": "hi", "element_id": "e1"}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
    }
    import json
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before


def test_compute_automatic_metrics_image_base_dir_path_batch32(tmp_path):
    """image_base_dir 是 Path；文件不存在 → 0.0（有 image element）。"""
    doc = {
        "elements": [{"type": "image", "element_id": "i1", "resource_path": "x.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 0.0
    assert out["image_resource_exists_ratio"]["reason"] is None


def test_compute_automatic_metrics_expectations_none_batch32():
    doc = {
        "elements": [{"type": "paragraph", "content": "hi", "element_id": "e1"}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_automatic_metrics_with_expectations_batch32():
    doc = {
        "elements": [{"type": "paragraph", "content": "hi", "element_id": "e1"}],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 1


def test_compute_automatic_metrics_element_count_by_type_value_is_dict_batch32():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "a", "element_id": "e1"},
            {"type": "heading", "content": "b", "element_id": "e2"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    v = out["element_count_by_type"]["value"]
    assert isinstance(v, dict)
    assert v["paragraph"] == 1
    assert v["heading"] == 1


def test_compute_automatic_metrics_unknown_type_counted_batch32():
    doc = {
        "elements": [{"type": "weird", "content": "x", "element_id": "e1"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"]["weird"] == 1


# ---------- _pdf_locator_ratio 第三十二批 ----------


def test_pdf_locator_ratio_page_zero_batch32():
    """page=0 < 1 → 不通过。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch32():
    elements = [{"type": "paragraph", "source_locator": {"page": -5}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_with_bool_batch32():
    """bbox 含 bool → 不通过。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [True, 0.0, 1.0, 1.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_nan_batch32():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [float("nan"), 0.0, 1.0, 1.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_table_does_not_need_bbox_batch32():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES → page 即可。"""
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_locator_missing_batch32():
    """locator 缺失 → page=None → 不通过。"""
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第三十二批 ----------


def test_docx_locator_ratio_empty_locator_dict_batch32():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_arbitrary_structural_key_batch32():
    """任意一个 structural_key 即通过。"""
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_and_paragraph_index_batch32():
    """同时含 section 和 paragraph_index 仍通过（不要求多个）。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"section": 1, "paragraph_index": 2},
        }
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_page_and_bbox_together_batch32():
    """同时含 page 和 bbox → 不通过（一个就够 reject）。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 1, 1], "section": 1},
        }
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_relationship_id_only_batch32():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "r1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_locator_none_batch32():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    # None or {} → no structural_keys → 0.0
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第三十二批 ----------


def test_is_valid_bbox_length_three_batch32():
    assert _is_valid_bbox([0.0, 0.0, 1.0]) is False


def test_is_valid_bbox_length_five_batch32():
    assert _is_valid_bbox([0.0, 0.0, 1.0, 1.0, 2.0]) is False


def test_is_valid_bbox_all_true_batch32():
    assert _is_valid_bbox([True, True, True, True]) is False


def test_is_valid_bbox_all_false_batch32():
    assert _is_valid_bbox([False, False, False, False]) is False


def test_is_valid_bbox_all_strings_batch32():
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_contains_none_batch32():
    assert _is_valid_bbox([0.0, None, 1.0, 1.0]) is False


def test_is_valid_bbox_contains_nan_batch32():
    assert _is_valid_bbox([0.0, float("nan"), 1.0, 1.0]) is False


def test_is_valid_bbox_contains_inf_batch32():
    assert _is_valid_bbox([0.0, float("inf"), 1.0, 1.0]) is False


def test_is_valid_bbox_contains_neg_inf_batch32():
    assert _is_valid_bbox([0.0, float("-inf"), 1.0, 1.0]) is False


def test_is_valid_bbox_all_zeros_batch32():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_all_negative_batch32():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_returns_bool_batch32():
    assert isinstance(_is_valid_bbox([0, 0, 0, 0]), bool)


# ---------- _image_resource_ratio 第三十二批 ----------


def test_image_resource_ratio_rp_none_batch32(tmp_path):
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_rp_empty_string_batch32(tmp_path):
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_no_resource_path_key_batch32(tmp_path):
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_partial_existence_batch32(tmp_path):
    """两个 image，一个文件存在一个不存在 → 0.5。"""
    (tmp_path / "a.png").write_bytes(b"\x89PNG\r\n")
    elements = [
        {"type": "image", "resource_path": "a.png"},
        {"type": "image", "resource_path": "b.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


def test_image_resource_ratio_file_size_zero_batch32(tmp_path):
    """存在但 size=0 → 不通过。"""
    (tmp_path / "empty.png").write_bytes(b"")
    elements = [{"type": "image", "resource_path": "empty.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_absolute_path_batch32(tmp_path):
    """绝对路径 file 存在。"""
    p = tmp_path / "abs.png"
    p.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(p)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_no_images_returns_null_batch32(tmp_path):
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


# ---------- _chunk_reference_ratio 第三十二批 ----------


def test_chunk_reference_ratio_element_id_missing_batch32():
    """element 缺 element_id → elem_ids 集合含 None。"""
    elements = [{"type": "paragraph"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # "e1" not in {None} → 0/1 = 0.0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_string_id_batch32():
    elements = [{"type": "paragraph", "element_id": ""}]
    chunks = [{"text": "x", "source_element_ids": [""]}]
    out = _chunk_reference_ratio(elements, chunks)
    # "" in {""} → 1/1
    assert out["value"] == 1.0


def test_chunk_reference_ratio_chunk_referencing_same_element_batch32():
    """两个 chunk 都引用同一 element_id → 都通过。"""
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},
        {"text": "y", "source_element_ids": ["e1"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_returns_float_batch32():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert isinstance(out["value"], float)


def test_chunk_reference_ratio_partial_match_batch32():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},
        {"text": "y", "source_element_ids": ["missing"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _strip_unicode_whitespace 第三十二批 ----------


def test_strip_unicode_whitespace_nbsp_batch32():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_em_space_batch32():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_batch32():
    """U+2002 en space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch32():
    """U+3000 ideographic space。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch32():
    """U+2028 line separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch32():
    """U+2029 paragraph separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_zero_width_not_whitespace_batch32():
    """U+200B zero-width space 不是 isspace → 保留。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_preserves_order_batch32():
    assert _strip_unicode_whitespace("cba") == "cba"


def test_strip_unicode_whitespace_returns_str_batch32():
    assert isinstance(_strip_unicode_whitespace(""), str)


# ---------- _text_preservation 第三十二批 ----------


def test_text_preservation_only_image_batch32():
    """所有 elements 是 image → expected_raw="" → equal=True, prec/recall null。"""
    elements = [{"type": "image", "content": "", "element_id": "i1"}]
    chunks = [{"text": "", "source_element_ids": ["i1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_chunk_none_text_batch32():
    """chunk 缺 text key → text 默认 ""。"""
    elements = [{"type": "paragraph", "content": "abc", "element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual="" → equal=False
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_image_content_not_in_multiset_batch32():
    """image content 不进入 expected。"""
    elements = [
        {"type": "image", "content": "XYZ", "element_id": "i1"},
        {"type": "paragraph", "content": "ab", "element_id": "e1"},
    ]
    chunks = [{"text": "ab", "source_element_ids": ["e1", "i1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_duplicate_chars_multiset_batch32():
    """重复字符通过 multiset。"""
    elements = [{"type": "paragraph", "content": "aabb", "element_id": "e1"}]
    chunks = [{"text": "bbaa", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    # equal=False (顺序不同), precision/recall=1.0 (multiset 相同)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_returns_three_keys_batch32():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_partial_overlap_batch32():
    elements = [{"type": "paragraph", "content": "abcd", "element_id": "e1"}]
    chunks = [{"text": "abef", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    # common = "ab" = 2, |actual|=4, |expected|=4 → 0.5
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 0.5


# ---------- _heading_boundary_ratio 第三十二批 ----------


def test_heading_boundary_ratio_heading_no_element_id_batch32():
    """heading 缺 element_id → 不能匹配任何 chunk。"""
    elements = [{"type": "heading", "content": "x"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # headings=[h], chunk_first_ids={"e1"}, h.element_id=None not in → 0/1
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_first_id_nonexistent_batch32():
    """chunk 首个 id 在 elements 中不存在仍计入 chunk_first_ids（不要求存在）。"""
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["missing"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks_same_first_batch32():
    """多 chunk 同 first_id 仍算 1 个 heading 命中。"""
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_no_chunks_batch32():
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_returns_dict_batch32():
    elements = [{"type": "heading", "content": "x", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert isinstance(out, dict)


# ---------- _silent_drop_count 第三十二批 ----------


def test_silent_drop_count_expected_zero_batch32():
    """expected 含 0，actual=0 → drop=0。"""
    by_type = {"paragraph": 0}
    out = _silent_drop_count(by_type, {"element_count_by_type": {"paragraph": 0}})
    assert out["value"] == 0


def test_silent_drop_count_actual_greater_than_expected_batch32():
    """actual > expected → 不计 drop（不报负）。"""
    by_type = {"paragraph": 5}
    out = _silent_drop_count(by_type, {"element_count_by_type": {"paragraph": 2}})
    assert out["value"] == 0


def test_silent_drop_count_multiple_types_partial_drop_batch32():
    by_type = {"paragraph": 1, "heading": 5, "table": 3}
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 5, "table": 10}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph drop=2, heading drop=0, table drop=7 → total=9
    assert out["value"] == 9


def test_silent_drop_count_by_type_empty_batch32():
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5


def test_silent_drop_count_returns_int_batch32():
    by_type = {"paragraph": 1}
    out = _silent_drop_count(by_type, {"element_count_by_type": {"paragraph": 3}})
    assert isinstance(out["value"], int)


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_subprocess_batch32():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch32():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch32():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch32():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch32():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_text_types_constant_batch32():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_required_constant_batch32():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_not_evaluated_constant_batch32():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


def test_module_source_contains_null_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_compute_automatic_metrics_func_batch32():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_pdf_locator_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_is_valid_bbox_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_image_resource_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_reference_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_strip_unicode_whitespace_batch32():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_text_preservation_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_heading_boundary_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_silent_drop_count_func_batch32():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_contains_math_import_batch32():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_counter_import_batch32():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


# ---------- signatures 第四十五批 ----------


def test_signature_null_return_batch32():
    sig = inspect.signature(_null)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_null_reason_annotation_batch32():
    sig = inspect.signature(_null)
    assert sig.parameters["reason"].annotation == "str"


def test_signature_ratio_return_batch32():
    sig = inspect.signature(_ratio)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_ratio_value_annotation_batch32():
    sig = inspect.signature(_ratio)
    assert sig.parameters["value"].annotation == "float"


def test_signature_bool_metric_value_annotation_batch32():
    sig = inspect.signature(_bool_metric)
    assert sig.parameters["value"].annotation == "bool"


def test_signature_int_metric_value_annotation_batch32():
    sig = inspect.signature(_int_metric)
    assert sig.parameters["value"].annotation == "int"


def test_signature_compute_automatic_metrics_source_type_batch32():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["source_type"].annotation == "str"


def test_signature_compute_automatic_metrics_return_batch32():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_compute_automatic_metrics_image_base_dir_optional_batch32():
    sig = inspect.signature(compute_automatic_metrics)
    ps = str(sig.parameters["image_base_dir"].annotation)
    assert "Path" in ps and "None" in ps


def test_signature_is_valid_bbox_return_bool_batch32():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_signature_strip_unicode_whitespace_return_str_batch32():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.return_annotation == "str"


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch32():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch32():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch32():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_has_all_export_batch32():
    src = inspect.getsource(mmod)
    assert "__all__" in src


def test_module_all_has_compute_automatic_metrics_batch32():
    src = inspect.getsource(mmod)
    assert '"compute_automatic_metrics"' in src


def test_module_no_main_block_batch32():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_compute_automatic_metrics_full_pdf_batch32():
    """端到端 PDF：完整 pipeline 输出。"""
    doc = {
        "elements": [
            {
                "type": "heading",
                "content": "title",
                "element_id": "h1",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 30.0]},
            },
            {
                "type": "paragraph",
                "content": "hello",
                "element_id": "e1",
                "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 50.0]},
            },
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_pipeline_failed_passes_all_null_batch32():
    """端到端 pipeline 失败 → 所有 ratio null。"""
    out = compute_automatic_metrics(None, {"code": "X"}, "pdf", None)
    for k in [
        "element_count_total",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    ]:
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_idempotent_full_run_batch32():
    """端到端：两次调用相同结果。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_no_input_modification_batch32():
    """端到端：不修改 document / error / expectations。"""
    import json
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    error = None
    expectations = {"element_count_by_type": {"paragraph": 1}}
    doc_before = json.dumps(doc, sort_keys=True)
    err_before = json.dumps(error, sort_keys=True) if error else "null"
    exp_before = json.dumps(expectations, sort_keys=True)
    compute_automatic_metrics(doc, error, "pdf", expectations)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(expectations, sort_keys=True) == exp_before


def test_e2e_returns_dict_batch32():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_e2e_silent_drop_with_expectations_batch32():
    """端到端：expectations 提供 element_count_by_type。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 2}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # paragraph drop=2, heading drop=2 → total=4
    assert out["silent_drop_count"]["value"] == 4


def test_e2e_docx_locator_valid_for_docx_source_type_batch32():
    """端到端：docx 文档，source_type=docx → docx_locator_valid_ratio 计算。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "x",
                "element_id": "e1",
                "source_locator": {"paragraph_index": 0, "section": 1},
            }
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    # pdf_locator_valid_ratio should be null
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
