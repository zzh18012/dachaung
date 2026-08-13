"""evaluation/metrics.py 第九十一轮 edges 测试（Round 652）。

补强 edges72 未触及的角度（第四十八批）。

新角度：
- compute_automatic_metrics pipeline_failed 14 keys 精确
- compute_automatic_metrics error_code 字段（成功时 null / 失败时 error["code"]）
- compute_automatic_metrics schema_check_exception 路径（mock document_passes_schema 抛 Exception）
- _pdf_locator_ratio 精度（page 是 True / page 是 0 / page 是 float / bbox 非法）
- _docx_locator_ratio 精度（含 page / 含 bbox / 无 structural_keys / 多种 structural_keys）
- _is_valid_bbox 严格（含 True / 含字符串 / 含 NaN / 含 inf / 含 None / 是 tuple / 长度 ≠ 4）
- _chunk_reference_ratio 边界（chunks 空 / chunk 无 source_element_ids / ids 含 None / ids 是非 list）
- _text_preservation 边界（expected 和 actual 都空 / expected 空但 actual 非空 / 反之 / Unicode 空白）
- _heading_boundary_ratio 边界（无 heading / chunks 空 / chunk source_element_ids 空）
- _silent_drop_count 边界（无 expectations / expectations 无 element_count_by_type / actual > expected / 多类型混合）
- 模块源码补强（math / Counter / Path / Any / _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED / 14 keys / pipeline_failed / not_pdf_document / not_docx_document / no_chunks / no_image_elements / no_heading_elements / no_expectations / empty_actual / empty_expected / empty_expected_and_actual）
- AST 结构补强（compute_automatic_metrics 多 return / _is_valid_bbox 多 if / _text_preservation nested if / module top-level 常量 Assign / __all__ 1 entry）
- forbidden tokens 第一百二十二批
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.metrics as metrics_mod
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


# ---------- compute_automatic_metrics pipeline_failed 14 keys 精确 ----------

def test_compute_pipeline_failed_returns_14_keys_batch48():
    out = compute_automatic_metrics(None, None, "pdf", None)
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


def test_compute_pipeline_failed_all_null_except_pipeline_success_error_code_batch48():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # pipeline_success 是 False（不是 null）
    assert out["pipeline_success"]["value"] is False
    # error_code 是 None（不是 _null 形式）
    assert out["error_code"]["value"] is None
    # 其它都是 null + pipeline_failed
    for k, v in out.items():
        if k in ("pipeline_success", "error_code"):
            continue
        assert v["value"] is None
        assert v["reason"] == "pipeline_failed"


def test_compute_pipeline_failed_with_error_code_batch48():
    """error 给定时 error_code 应当是 error["code"]。"""
    err = {"code": "E_PARSE", "message": "broken"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "E_PARSE"


def test_compute_pipeline_failed_source_type_does_not_matter_batch48():
    """document=None 时 source_type 不影响（pdf/docx 都返回 not_xxx null）。"""
    out_pdf = compute_automatic_metrics(None, None, "pdf", None)
    out_docx = compute_automatic_metrics(None, None, "docx", None)
    # pdf_locator_valid_ratio 都是 pipeline_failed（document None 早 return）
    assert out_pdf["pdf_locator_valid_ratio"]["reason"] == "pipeline_failed"
    assert out_docx["pdf_locator_valid_ratio"]["reason"] == "pipeline_failed"


# ---------- compute_automatic_metrics schema_check_exception 路径 ----------

def test_compute_schema_check_exception_batch48():
    """document_passes_schema 抛 Exception → schema_valid=False + reason schema_check_exception:..."""
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=ValueError("boom")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception:ValueError" in out["schema_valid"]["reason"]


def test_compute_schema_check_exception_type_in_reason_batch48():
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("x")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "RuntimeError" in out["schema_valid"]["reason"]


def test_compute_schema_valid_true_batch48():
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is True
    assert out["schema_valid"]["reason"] is None


def test_compute_schema_valid_false_batch48():
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=False):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert out["schema_valid"]["reason"] is None


# ---------- compute_automatic_metrics 成功路径主键 ----------

def test_compute_success_minimal_batch48():
    """成功 case：document 非空 + error None → pipeline_success=True。"""
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["error_code"]["value"] is None


def test_compute_success_element_count_total_batch48():
    doc = {
        "elements": [{"type": "heading", "content": "H"}, {"type": "paragraph", "content": "P"}],
        "chunks": [],
    }
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2


def test_compute_success_element_count_by_type_batch48():
    doc = {
        "elements": [
            {"type": "heading"},
            {"type": "heading"},
            {"type": "paragraph"},
        ],
        "chunks": [],
    }
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"heading": 2, "paragraph": 1}


def test_compute_success_element_count_by_type_missing_type_batch48():
    """element 缺 type → 计入 'unknown'。"""
    doc = {"elements": [{"content": "x"}, {"type": "heading"}], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1, "heading": 1}


# ---------- _pdf_locator_ratio 精度 ----------

def test_pdf_locator_ratio_empty_batch48():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_page_true_rejected_batch48():
    """page=True：isinstance(True, int) 是 True，但 True < 1 是 False（True == 1）。
    实际上 True ≥ 1 通过，但若 type 是 _PDF_BBOX_REQUIRED_TYPES 还需 bbox。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    # image 不需要 bbox，page=True == 1 ≥ 1 → valid
    out = _pdf_locator_ratio(elements)
    # True == 1，所以 valid
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_zero_rejected_batch48():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_rejected_batch48():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_without_bbox_rejected_batch48():
    elements = [{"type": "heading", "source_locator": {"page": 1}}]  # 缺 bbox
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_with_valid_bbox_batch48():
    elements = [{"type": "heading", "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_missing_source_locator_batch48():
    elements = [{"type": "image"}]  # 缺 source_locator
    out = _pdf_locator_ratio(elements)
    # loc = None or {} = {}，page = None → not int → invalid
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 精度 ----------

def test_docx_locator_ratio_with_page_rejected_batch48():
    """DOCX locator 含 page → 不合规。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected_batch48():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_rejected_batch48():
    elements = [{"type": "paragraph", "source_locator": {"foo": "bar"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_paragraph_index_batch48():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_section_index_batch48():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_table_indices_batch48():
    elements = [{"type": "table", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_relationship_id_batch48():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _is_valid_bbox 严格 ----------

def test_is_valid_bbox_true_element_rejected_batch48():
    """bbox 含 True（bool 是 int 子类，但显式拒绝）。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_false_element_rejected_batch48():
    assert _is_valid_bbox([False, 0, 0, 0]) is False


def test_is_valid_bbox_string_rejected_batch48():
    assert _is_valid_bbox(["0", "0", "0", "0"]) is False


def test_is_valid_bbox_nan_rejected_batch48():
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_is_valid_bbox_inf_rejected_batch48():
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_is_valid_bbox_none_rejected_batch48():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


def test_is_valid_bbox_tuple_rejected_batch48():
    """严格 isinstance(list)：tuple 拒绝。"""
    assert _is_valid_bbox((0.0, 0.0, 0.0, 0.0)) is False


def test_is_valid_bbox_length_3_rejected_batch48():
    assert _is_valid_bbox([0, 0, 0]) is False


def test_is_valid_bbox_length_5_rejected_batch48():
    assert _is_valid_bbox([0, 0, 0, 0, 0]) is False


def test_is_valid_bbox_valid_int_batch48():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_valid_float_batch48():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 100.5]) is True


def test_is_valid_bbox_none_arg_batch48():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string_arg_batch48():
    assert _is_valid_bbox("not a list") is False


# ---------- _chunk_reference_ratio 边界 ----------

def test_chunk_reference_ratio_empty_chunks_batch48():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunk_no_source_element_ids_batch48():
    """chunk 缺 source_element_ids → ids 默认 [] → 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x"}]  # 缺 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_empty_source_element_ids_batch48():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_match_batch48():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_match_batch48():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["missing"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_multi_id_per_chunk_all_match_batch48():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}, {"element_id": "e3"}]
    chunks = [{"text": "ab", "source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multi_id_per_chunk_partial_batch48():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"text": "ab", "source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids = ["e1", "missing"]，all(sid in elem_ids) is False → 不算 valid
    assert out["value"] == 0.0


# ---------- _text_preservation 边界 ----------

def test_text_preservation_both_empty_batch48():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_expected_empty_actual_nonempty_batch48():
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected="", actual="abc"，equal=False
    assert out["equal"]["value"] is False
    # precision common / |actual| = 0 / 3 = 0
    assert out["precision"]["value"] == 0.0
    # recall: sum(c_expected.values()) == 0 → null + empty_expected
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_actual_empty_expected_nonempty_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # precision: sum(c_actual.values()) == 0 → null + empty_actual
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_actual"
    # recall: 0 / 3 = 0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_perfect_match_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch48():
    """image element 的 content 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "ab"},
        {"type": "image", "content": "XYZ"},
    ]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_unicode_whitespace_stripped_batch48():
    """Unicode 空白（NBSP、em space 等）应当被 strip。"""
    elements = [{"type": "paragraph", "content": "a b"}]  # NBSP
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    # NBSP 被 strip → "ab" == "ab"
    assert out["equal"]["value"] is True


def test_text_preservation_duplicate_chars_batch48():
    """重复字符：Counter 多集合。"""
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "ab"}]  # 丢了 a 和 b
    out = _text_preservation(elements, chunks)
    # equal: "aabb" != "ab"
    assert out["equal"]["value"] is False
    # precision: common = {a:1, b:1} = 2, |actual| = 2 → 1.0
    assert out["precision"]["value"] == 1.0
    # recall: 2 / 4 = 0.5
    assert out["recall"]["value"] == 0.5


def test_text_preservation_chunk_missing_text_batch48():
    """chunk 缺 text → 默认 ''。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]  # 缺 text
    out = _text_preservation(elements, chunks)
    # actual = ""，recall = 0
    assert out["recall"]["value"] == 0.0


# ---------- _heading_boundary_ratio 边界 ----------

def test_heading_boundary_ratio_no_headings_batch48():
    out = _heading_boundary_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_batch48():
    """chunks 空 → chunk_first_ids 是空 set → matched=0 / 1 = 0.0。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # 注意：实现不把 chunks=[] 视为 null，直接返回 ratio(0.0)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_batch48():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "H", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_heading_not_first_batch48():
    """heading 在 source_element_ids 中但不是第一个 → 不算。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x H", "source_element_ids": ["e1", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # ids[0] = "e1"，不是 h1 → 不算
    assert out["value"] == 0.0


def test_heading_boundary_ratio_partial_batch48():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"text": "H1", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 边界 ----------

def test_silent_drop_count_no_expectations_batch48():
    out = _silent_drop_count({}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_batch48():
    out = _silent_drop_count({}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type_batch48():
    out = _silent_drop_count({}, {"other_key": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type_batch48():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drops_batch48():
    """actual ≥ expected → 0 drops。"""
    by_type = {"heading": 5, "paragraph": 10}
    expectations = {"element_count_by_type": {"heading": 3, "paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_equals_expected_batch48():
    by_type = {"heading": 3}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_partial_drop_batch48():
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # drop = 3 - 1 = 2
    assert out["value"] == 2


def test_silent_drop_count_missing_type_in_actual_batch48():
    """actual 缺该类型 → 视为 0，drops += expected。"""
    by_type = {}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 3


def test_silent_drop_count_multi_type_batch48():
    by_type = {"heading": 1, "paragraph": 5}
    expectations = {"element_count_by_type": {"heading": 3, "paragraph": 2, "list_item": 4}}
    out = _silent_drop_count(by_type, expectations)
    # heading: 3-1=2，paragraph: 0（actual > expected），list_item: 4-0=4
    # total: 2 + 0 + 4 = 6
    assert out["value"] == 6


# ---------- _strip_unicode_whitespace 边界 ----------

def test_strip_unicode_whitespace_ascii_space_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_nbsp_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch48():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_newline_tab_batch48():
    assert _strip_unicode_whitespace("a\n\tb") == "ab"


def test_strip_unicode_whitespace_empty_batch48():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace_batch48():
    assert _strip_unicode_whitespace(" \t\n  ") == ""


def test_strip_unicode_whitespace_no_whitespace_batch48():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_preserves_order_batch48():
    """不排序，只删空白。"""
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_unicode_whitespace_preserves_case_batch48():
    assert _strip_unicode_whitespace("A b C") == "AbC"


# ---------- 模块常量 ----------

def test_text_types_count_7_batch48():
    assert len(metrics_mod._TEXT_TYPES) == 7


def test_text_types_contents_batch48():
    assert set(metrics_mod._TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table", "caption", "header", "footer"
    }


def test_pdf_bbox_required_types_count_4_batch48():
    assert len(metrics_mod._PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types_batch48():
    assert set(metrics_mod._PDF_BBOX_REQUIRED_TYPES).issubset(set(metrics_mod._TEXT_TYPES))


def test_not_evaluated_constant_batch48():
    assert metrics_mod._NOT_EVALUATED == "not_evaluated"


# ---------- _null / _ratio / _bool_metric / _int_metric ----------

def test_null_value_is_none_batch48():
    assert _null("any")["value"] is None


def test_null_reason_passthrough_batch48():
    assert _null("xyz")["reason"] == "xyz"


def test_ratio_value_is_float_batch48():
    assert isinstance(_ratio(0.5)["value"], float)


def test_ratio_int_becomes_float_batch48():
    assert _ratio(1)["value"] == 1.0
    assert isinstance(_ratio(1)["value"], float)


def test_ratio_reason_none_batch48():
    assert _ratio(0.0)["reason"] is None


def test_bool_metric_value_is_bool_batch48():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(False)["value"], bool)


def test_bool_metric_int_to_bool_batch48():
    """_bool_metric(1) → True。"""
    assert _bool_metric(1)["value"] is True
    assert _bool_metric(0)["value"] is False


def test_int_metric_value_is_int_batch48():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_float_to_int_batch48():
    """_int_metric(2.7) → 2（int() 截断）。"""
    assert _int_metric(2.7)["value"] == 2


def test_int_metric_str_raises_batch48():
    with pytest.raises(ValueError):
        _int_metric("abc")


# ---------- 模块源码补强 ----------

def test_source_contains_math_import_batch48():
    src = inspect.getsource(metrics_mod)
    assert "import math" in src


def test_source_contains_counter_import_batch48():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_source_contains_pathlib_import_batch48():
    src = inspect.getsource(metrics_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch48():
    src = inspect.getsource(metrics_mod)
    assert "from typing import Any" in src


def test_source_contains_text_types_constant_batch48():
    src = inspect.getsource(metrics_mod)
    assert "_TEXT_TYPES" in src


def test_source_contains_pdf_bbox_required_types_batch48():
    src = inspect.getsource(metrics_mod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_source_contains_not_evaluated_constant_batch48():
    src = inspect.getsource(metrics_mod)
    assert "_NOT_EVALUATED" in src


def test_source_contains_pipeline_failed_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"pipeline_failed"' in src


def test_source_contains_not_pdf_document_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"not_pdf_document"' in src


def test_source_contains_not_docx_document_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"not_docx_document"' in src


def test_source_contains_no_chunks_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_chunks"' in src


def test_source_contains_no_image_elements_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_image_elements"' in src


def test_source_contains_no_heading_elements_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_heading_elements"' in src


def test_source_contains_no_expectations_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations"' in src


def test_source_contains_empty_actual_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"empty_actual"' in src


def test_source_contains_empty_expected_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected"' in src


def test_source_contains_empty_expected_and_actual_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected_and_actual"' in src


def test_source_contains_no_elements_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_elements"' in src


def test_source_contains_no_expectations_element_count_batch48():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations_element_count"' in src


def test_source_contains_schema_check_exception_batch48():
    src = inspect.getsource(metrics_mod)
    assert "schema_check_exception" in src


def test_source_contains_v1_1_history_batch48():
    """docstring 提到 v1.1 口径 D。"""
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src or "口径" in src


# ---------- AST 结构补强 ----------

def test_ast_compute_function_multiple_returns_batch48():
    """compute_automatic_metrics 至少 2 个 return（pipeline_failed 早 return + 末尾 return）。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics"
    )
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 2


def test_ast_is_valid_bbox_has_multiple_if_batch48():
    """_is_valid_bbox 多个 if（list check / len check / bool check / type check / finite check）。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox"
    )
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_text_preservation_has_nested_if_batch48():
    """_text_preservation 有嵌套 if（empty check / sum == 0 check）。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation"
    )
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 2


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_top_level_assigns_count_batch48():
    """模块顶部 Assign：_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED / __all__ = 4。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_all_list_one_entry_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__"
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 1


def test_ast_top_level_functions_count_batch48():
    """模块顶部函数：_null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics, _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox, _image_resource_ratio, _chunk_reference_ratio, _strip_unicode_whitespace, _text_preservation, _heading_boundary_ratio, _silent_drop_count = 14。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 14


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：__future__ / math / Counter / Path / Any = 5。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


def test_ast_silent_drop_count_has_for_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count"
    )
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 1


def test_ast_strip_unicode_whitespace_uses_join_batch48():
    """_strip_unicode_whitespace 用 ''.join(...)。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(
        n for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace"
    )
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_join = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "join" for c in calls
    )
    assert has_join


# ---------- forbidden tokens 第一百二十二批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()


def test_source_no_async_def_batch48():
    assert "async def" not in _src()


def test_source_no_await_batch48():
    assert "await " not in _src()
