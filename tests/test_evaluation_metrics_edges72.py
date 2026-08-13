"""evaluation/metrics.py 第八十九轮 edges 测试（Round 644）。

补强 edges71 未触及的角度（第四十八批）。

新角度：
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 常量属性
- _null / _ratio / _bool_metric / _int_metric 工厂函数
- compute_automatic_metrics 各种 document/error 组合
- _pdf_locator_ratio 各种元素
- _docx_locator_ratio 各种 locator
- _is_valid_bbox 各种 bbox
- _image_resource_ratio 各种 image
- _chunk_reference_ratio 各种 chunks
- _strip_unicode_whitespace 各种字符
- _text_preservation 各种 text/chunks
- _heading_boundary_ratio 各种 heading
- _silent_drop_count 各种 expectations
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十四批
"""

from __future__ import annotations

import ast
import inspect
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.metrics as metrics_mod
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


# ---------- 常量属性 ----------

def test_text_types_count_7_batch48():
    assert len(_TEXT_TYPES) == 7


def test_text_types_exact_batch48():
    assert set(_TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_text_types_is_tuple_batch48():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_count_4_batch48():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_exact_batch48():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {
        "heading", "paragraph", "caption", "list_item",
    }


def test_pdf_bbox_required_subset_of_text_types_batch48():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_not_evaluated_value_batch48():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch48():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_no_image_batch48():
    assert "image" not in _TEXT_TYPES


# ---------- 工厂函数 ----------

def test_null_returns_dict_batch48():
    out = _null("reason_x")
    assert out == {"value": None, "reason": "reason_x"}


def test_null_value_is_none_batch48():
    assert _null("x")["value"] is None


def test_ratio_returns_dict_batch48():
    out = _ratio(0.5)
    assert out == {"value": 0.5, "reason": None}


def test_ratio_value_is_float_batch48():
    assert isinstance(_ratio(0)["value"], float)


def test_ratio_accepts_int_batch48():
    """int 输入应被 float() 转换。"""
    out = _ratio(1)
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_bool_metric_returns_dict_batch48():
    out = _bool_metric(True)
    assert out == {"value": True, "reason": None}


def test_bool_metric_value_is_bool_batch48():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(1)["value"], bool)  # 1 → True


def test_int_metric_returns_dict_batch48():
    out = _int_metric(42)
    assert out == {"value": 42, "reason": None}


def test_int_metric_value_is_int_batch48():
    assert isinstance(_int_metric(0)["value"], int)


def test_int_metric_accepts_str_int_batch48():
    """'42' 通过 int() 转。"""
    out = _int_metric("42")
    assert out["value"] == 42


# ---------- compute_automatic_metrics document None / error ----------

def test_compute_pipeline_failed_14_keys_batch48():
    """document None → 14 metrics（pipeline_success + error_code + schema_valid + 11 null）."""
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert len(out) == 14


def test_compute_pipeline_failed_all_null_except_two_batch48():
    """document None：pipeline_success=False / error_code 有值 / 其他 12 个 null。"""
    out = compute_automatic_metrics(None, {"code": "boom"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "boom"
    for k in (
        "schema_valid", "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_compute_error_none_document_none_batch48():
    """error=None 且 document=None → pipeline_success False / error_code null。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


def test_compute_error_with_dict_batch48():
    out = compute_automatic_metrics(None, {"code": "parse_failed"}, "pdf", None)
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_schema_check_exception_batch48():
    """document 非 None 但 schema_check 抛异常 → schema_valid=False + reason。"""
    doc = {"id": "d1"}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception" in out["schema_valid"]["reason"]


# ---------- compute_automatic_metrics 完整 document ----------

def test_compute_complete_document_keys_batch48():
    """完整 document 应有 14 keys。"""
    doc = {
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "title"},
            {"element_id": "e2", "type": "paragraph", "content": "body"},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["e1"]},
            {"text": "body", "source_element_ids": ["e2"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(out) == 14


def test_compute_complete_pipeline_success_true_batch48():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_element_count_total_batch48():
    doc = {
        "elements": [{"type": "heading"}, {"type": "paragraph"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2


def test_compute_element_count_by_type_batch48():
    doc = {
        "elements": [
            {"type": "heading"},
            {"type": "heading"},
            {"type": "paragraph"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"heading": 2, "paragraph": 1}


def test_compute_pdf_locator_when_docx_batch48():
    """source_type=docx → pdf_locator_valid_ratio null not_pdf_document。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_docx_locator_when_pdf_batch48():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_no_chunks_chunk_reference_null_batch48():
    """chunks=[] → chunk_reference_intact_ratio null no_chunks。"""
    doc = {"elements": [{"element_id": "e1"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_no_image_image_null_batch48():
    """无 image element → image_resource_exists_ratio null no_image_elements。"""
    doc = {"elements": [{"type": "heading"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


# ---------- _pdf_locator_ratio 各种元素 ----------

def test_pdf_locator_empty_elements_batch48():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_all_valid_batch48():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_missing_page_batch48():
    elements = [{"type": "image", "source_locator": {"bbox": [0, 0, 10, 10]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_missing_bbox_batch48():
    elements = [{"type": "heading", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_image_no_bbox_needed_batch48():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_negative_page_batch48():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_bool_page_batch48():
    """bool 是 int 子类，True 通过 isinstance(page, int) 但 page < 1 False，True 不 < 1。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # True == 1, 1 >= 1, 所以 valid
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 各种 locator ----------

def test_docx_locator_empty_batch48():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_with_page_invalid_batch48():
    """DOCX 不应有 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_invalid_batch48():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_paragraph_index_batch48():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_table_index_batch48():
    elements = [{"type": "table", "source_locator": {"table_index": 1, "row_index": 2, "col_index": 3}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_no_structural_key_batch48():
    elements = [{"type": "paragraph", "source_locator": {"weird_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 各种 bbox ----------

def test_is_valid_bbox_valid_batch48():
    assert _is_valid_bbox([0, 0, 10, 10]) is True


def test_is_valid_bbox_with_floats_batch48():
    assert _is_valid_bbox([0.5, 1.5, 2.5, 3.5]) is True


def test_is_valid_bbox_wrong_length_batch48():
    assert _is_valid_bbox([0, 0, 10]) is False
    assert _is_valid_bbox([0, 0, 10, 10, 10]) is False


def test_is_valid_bbox_tuple_batch48():
    """tuple 不是 list。"""
    assert _is_valid_bbox((0, 0, 10, 10)) is False


def test_is_valid_bbox_with_bool_batch48():
    assert _is_valid_bbox([True, 0, 10, 10]) is False


def test_is_valid_bbox_with_str_batch48():
    assert _is_valid_bbox(["0", "0", "10", "10"]) is False


def test_is_valid_bbox_with_nan_batch48():
    assert _is_valid_bbox([float("nan"), 0, 10, 10]) is False


def test_is_valid_bbox_with_inf_batch48():
    assert _is_valid_bbox([float("inf"), 0, 10, 10]) is False


def test_is_valid_bbox_none_batch48():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_batch48():
    assert _is_valid_bbox([]) is False


# ---------- _image_resource_ratio 各种 image ----------

def test_image_ratio_no_images_batch48():
    out = _image_resource_ratio([], None)
    assert out["reason"] == "no_image_elements"


def test_image_ratio_no_other_types_count_as_image_batch48():
    """只有 heading 不算 image。"""
    elements = [{"type": "heading"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_ratio_missing_resource_path_batch48():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_empty_resource_path_batch48():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_none_resource_path_batch48():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_with_existing_file_batch48(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_ratio_with_zero_byte_file_batch48(tmp_path):
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_mixed_valid_invalid_batch48(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image", "resource_path": None},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_ratio_oserror_swallowed_batch48(tmp_path):
    """is_file() 抛 OSError 应被吞。"""
    elements = [{"type": "image", "resource_path": str(tmp_path / "x.png")}]
    with patch("pathlib.Path.is_file", side_effect=OSError("boom")):
        out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 各种 chunks ----------

def test_chunk_reference_no_chunks_batch48():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_all_valid_batch48():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_missing_id_batch48():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["eX"]}]  # eX 不在 elements
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_partial_match_batch48():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["eX"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_empty_ids_batch48():
    """source_element_ids=[] → 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_missing_ids_key_batch48():
    """chunk 缺 source_element_ids key → 当 [] 处理。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _strip_unicode_whitespace 各种字符 ----------

def test_strip_whitespace_ascii_spaces_batch48():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_whitespace_unicode_nbsp_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_em_space_batch48():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_whitespace_ideographic_space_batch48():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_whitespace_newline_tab_batch48():
    assert _strip_unicode_whitespace("a\nb\tc") == "abc"


def test_strip_whitespace_empty_batch48():
    assert _strip_unicode_whitespace("") == ""


def test_strip_whitespace_only_whitespace_batch48():
    assert _strip_unicode_whitespace("   \n\t  ") == ""


def test_strip_whitespace_no_whitespace_batch48():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_whitespace_preserves_order_batch48():
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_whitespace_chinese_batch48():
    assert _strip_unicode_whitespace("中 文") == "中文"


# ---------- _text_preservation 各种 ----------

def test_text_preservation_empty_both_batch48():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_missing_char_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ac"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0  # ac ⊆ abc
    assert out["recall"]["value"] < 1.0


def test_text_preservation_extra_char_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] < 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_reorder_not_equal_but_counter_same_batch48():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch48():
    """image element 的 content 不计入 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_insensitive_batch48():
    """chunker 词内硬切产生的额外空格不应误报。"""
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hel lo"}]  # 词内多了空格
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


# ---------- _heading_boundary_ratio 各种 ----------

def test_heading_boundary_no_heading_batch48():
    out = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_returns_zero_batch48():
    """有 heading 但无 chunks → 0.0（不是 null）。"""
    out = _heading_boundary_ratio([{"type": "heading", "element_id": "h1"}], [])
    assert out["value"] == 0.0


def test_heading_boundary_perfect_batch48():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_partial_batch48():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_wrong_first_id_batch48():
    """chunk source_element_ids 第一个不匹配 → 不算。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["x", "h1"]}]  # 第一个是 x
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _silent_drop_count 各种 ----------

def test_silent_drop_no_expectations_batch48():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expectations_batch48():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_no_element_count_key_batch48():
    out = _silent_drop_count({"paragraph": 5}, {"other": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_empty_element_count_batch48():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_zero_drop_batch48():
    """actual >= expected → drop=0。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_actual_less_batch48():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 2


def test_silent_drop_multi_type_batch48():
    by_type = {"paragraph": 3, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 3  # (5-3) + (2-1)


def test_silent_drop_expected_type_missing_in_actual_batch48():
    """expected 中的 type 在 actual 中不存在 → 全 drop。"""
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 5


def test_silent_drop_extra_type_in_actual_ignored_batch48():
    """actual 多余 type 忽略。"""
    by_type = {"paragraph": 5, "image": 99}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


# ---------- module source 字符串补强 ----------

def test_source_contains_纯函数_batch48():
    src = inspect.getsource(metrics_mod)
    assert "纯函数" in src


def test_source_contains_不修改_document_batch48():
    src = inspect.getsource(metrics_mod)
    assert "不修改 document" in src


def test_source_contains_v1_1_batch48():
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src


def test_source_contains_v1_0_batch48():
    src = inspect.getsource(metrics_mod)
    assert "v1.0" in src


def test_source_contains_口径_D_batch48():
    src = inspect.getsource(metrics_mod)
    assert "口径 D" in src or "口径D" in src


def test_source_contains_Counter_batch48():
    src = inspect.getsource(metrics_mod)
    assert "Counter" in src


def test_source_contains_pipeline_failed_batch48():
    src = inspect.getsource(metrics_mod)
    assert "pipeline_failed" in src


def test_source_contains_不返回_1_0_batch48():
    src = inspect.getsource(metrics_mod)
    assert "不返回 1.0" in src


def test_source_contains_not_evaluated_batch48():
    src = inspect.getsource(metrics_mod)
    assert "not_evaluated" in src


def test_source_contains_词内硬切_batch48():
    src = inspect.getsource(metrics_mod)
    assert "词内硬切" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    # _null / _ratio / _bool_metric / _int_metric / compute / _pdf / _docx / _is_valid_bbox / _image / _chunk_ref / _strip / _text_preservation / _heading / _silent_drop
    assert len(funcs) == 14


def test_ast_constants_count_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED + __all__
    assert len(assigns) == 4


def test_ast_text_types_is_tuple_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_TEXT_TYPES":
                assert isinstance(n.value, ast.Tuple)
                assert len(n.value.elts) == 7
                return
    pytest.fail("_TEXT_TYPES not found")


def test_ast_pdf_bbox_required_is_tuple_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_PDF_BBOX_REQUIRED_TYPES":
                assert isinstance(n.value, ast.Tuple)
                assert len(n.value.elts) == 4
                return
    pytest.fail("_PDF_BBOX_REQUIRED_TYPES not found")


def test_ast_not_evaluated_is_constant_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_NOT_EVALUATED":
                assert isinstance(n.value, ast.Constant)
                assert n.value.value == "not_evaluated"
                return
    pytest.fail("_NOT_EVALUATED not found")


def test_ast_compute_has_for_loops_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 1


def test_ast_compute_has_if_document_none_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics"][0]
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 3


def test_ast_is_valid_bbox_has_multiple_if_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox"][0]
    # 多个 if 嵌在 for 循环内，需 ast.walk
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 4


def test_ast_text_preservation_uses_counter_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation"][0]
    # Counter(...) Call 应出现
    counter_calls = []
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Counter":
            counter_calls.append(n)
    assert len(counter_calls) >= 2


def test_ast_silent_drop_has_for_loop_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count"][0]
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_image_ratio_has_try_batch48():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


# ---------- forbidden tokens 第一百一十四批 ----------

def test_source_no_eval_batch48():
    src = inspect.getsource(metrics_mod)
    assert "eval(" not in src


def test_source_no_exec_batch48():
    src = inspect.getsource(metrics_mod)
    assert "exec(" not in src


def test_source_no_compile_batch48():
    src = inspect.getsource(metrics_mod)
    assert "compile(" not in src


def test_source_no_globals_batch48():
    src = inspect.getsource(metrics_mod)
    assert "globals(" not in src


def test_source_no_locals_batch48():
    src = inspect.getsource(metrics_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch48():
    src = inspect.getsource(metrics_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch48():
    src = inspect.getsource(metrics_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch48():
    src = inspect.getsource(metrics_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch48():
    src = inspect.getsource(metrics_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch48():
    src = inspect.getsource(metrics_mod)
    assert "subprocess" not in src


def test_source_no_lambda_batch48():
    src = inspect.getsource(metrics_mod)
    assert "lambda" not in src


def test_source_no_yield_batch48():
    src = inspect.getsource(metrics_mod)
    assert "yield" not in src


def test_source_no_walrus_batch48():
    src = inspect.getsource(metrics_mod)
    assert ":=" not in src


def test_source_no_async_batch48():
    src = inspect.getsource(metrics_mod)
    assert "async def" not in src


def test_source_no_await_batch48():
    src = inspect.getsource(metrics_mod)
    assert "await " not in src
