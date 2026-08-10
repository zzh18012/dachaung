"""evaluation/metrics.py 第三十八轮 edges 测试（Round 394）。

补强 edges36 未触及的角度：
- helpers 行为第十批（_null/_ratio/_bool_metric/_int_metric 更多边界）
- compute_automatic_metrics 行为深度第十批
- pdf/docx locator 行为深度第十批
- image_resource_ratio 行为深度第十批
- chunk_reference_ratio 行为深度第十批
- text_preservation 行为深度第十批
- heading_boundary_ratio 行为深度第十批
- silent_drop_count 行为深度第十批
- _is_valid_bbox 行为深度第十批
- _strip_unicode_whitespace 行为深度第十批
- module source forbidden tokens 第十三批
- module source 字符串精确补强第九批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
"""

from __future__ import annotations

import inspect
import json
import math
import os
from collections import Counter
from pathlib import Path

import pytest

from evaluation import metrics as mmod
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


# ---------- helpers 行为第十批 ----------


def test_null_returns_dict_with_value_none_batch10():
    out = _null("reason_x")
    assert out == {"value": None, "reason": "reason_x"}


def test_null_returns_dict_type_batch10():
    assert isinstance(_null("x"), dict)


def test_null_value_is_none_batch10():
    assert _null("x")["value"] is None


def test_null_reason_preserved_batch10():
    for r in ("a", "b", "c", "中文", "🎉", ""):
        assert _null(r)["reason"] == r


def test_null_idempotent_batch10():
    out1 = _null("x")
    out2 = _null("x")
    assert out1 == out2


def test_ratio_returns_dict_with_value_float_batch10():
    out = _ratio(0.5)
    assert isinstance(out["value"], float)
    assert out["value"] == 0.5


def test_ratio_int_input_converted_to_float_batch10():
    out = _ratio(1)  # int → float
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_ratio_zero_batch10():
    assert _ratio(0.0)["value"] == 0.0


def test_ratio_one_batch10():
    assert _ratio(1.0)["value"] == 1.0


def test_ratio_negative_batch10():
    """ratio 接受负值（不限制 [0,1]，算法自管）。"""
    assert _ratio(-0.5)["value"] == -0.5


def test_ratio_reason_none_batch10():
    assert _ratio(0.5)["reason"] is None


def test_bool_metric_true_batch10():
    out = _bool_metric(True)
    assert out["value"] is True
    assert out["reason"] is None


def test_bool_metric_false_batch10():
    out = _bool_metric(False)
    assert out["value"] is False
    assert out["reason"] is None


def test_bool_metric_truthy_value_batch10():
    """truthy 值转为 True。"""
    assert _bool_metric(1)["value"] is True
    assert _bool_metric("non-empty")["value"] is True


def test_bool_metric_falsy_value_batch10():
    """falsy 值转为 False。"""
    assert _bool_metric(0)["value"] is False
    assert _bool_metric("")["value"] is False


def test_int_metric_zero_batch10():
    out = _int_metric(0)
    assert out["value"] == 0
    assert isinstance(out["value"], int)


def test_int_metric_negative_batch10():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_large_batch10():
    assert _int_metric(10**9)["value"] == 10**9


def test_int_metric_float_input_truncated_batch10():
    """float 输入 → int 截断。"""
    assert _int_metric(3.99)["value"] == 3


def test_int_metric_bool_input_batch10():
    """bool 输入 → int(True)=1, int(False)=0。"""
    assert _int_metric(True)["value"] == 1
    assert _int_metric(False)["value"] == 0


def test_helpers_return_dict_with_value_reason_only_batch10():
    """所有 helper 都只含 value+reason 两 key。"""
    for out in (_null("x"), _ratio(0.5), _bool_metric(True), _int_metric(1)):
        assert set(out.keys()) == {"value", "reason"}


# ---------- compute_automatic_metrics 行为深度第十批 ----------


def test_compute_metrics_returns_dict_batch10():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_document_none_returns_14_keys_batch10():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # pipeline_success + error_code + schema_valid + 11 个 null 指标
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


def test_compute_metrics_document_none_pipeline_success_false_batch10():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_document_only_pipeline_success_true_batch10():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_error_pipeline_success_false_batch10():
    error = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_error_code_extracted_batch10():
    error = {"code": "my_error_code", "message": "boom"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["error_code"]["value"] == "my_error_code"


def test_compute_metrics_no_error_error_code_none_batch10():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_does_not_mutate_doc_batch10():
    doc = {"elements": [], "chunks": []}
    snapshot = json.dumps(doc, sort_keys=True)
    _ = compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == snapshot


def test_compute_metrics_does_not_mutate_error_batch10():
    error = {"code": "x", "message": "y"}
    snapshot = json.dumps(error, sort_keys=True)
    _ = compute_automatic_metrics(None, error, "pdf", None)
    assert json.dumps(error, sort_keys=True) == snapshot


def test_compute_metrics_idempotent_batch10():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_compute_metrics_kwargs_batch10():
    """compute_automatic_metrics 支持关键字参数。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_positional_args_batch10():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_element_count_total_batch10():
    doc = {
        "elements": [{"type": "paragraph"}, {"type": "heading"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2


def test_compute_metrics_element_count_by_type_batch10():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


# ---------- pdf/docx locator 行为深度第十批 ----------


def test_pdf_locator_empty_elements_returns_no_elements_batch10():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_valid_pdf_element_batch10():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}}
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_missing_page_batch10():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 100, 100]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_zero_batch10():
    elements = [{"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 100, 100]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_batch10():
    elements = [{"type": "paragraph", "source_locator": {"page": -1, "bbox": [0, 0, 100, 100]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_missing_bbox_for_text_type_batch10():
    """text type 缺 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_image_no_bbox_required_batch10():
    """image 不需要 bbox，只需 page。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_page_string_invalid_batch10():
    elements = [{"type": "paragraph", "source_locator": {"page": "1", "bbox": [0, 0, 100, 100]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_partial_valid_batch10():
    """部分 valid → ratio。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 100, 100]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_no_source_locator_batch10():
    """element 完全无 source_locator → 当作 {} → page None → invalid。"""
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_empty_elements_batch10():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_with_paragraph_index_batch10():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_section_batch10():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_relationship_id_batch10():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_page_invalid_batch10():
    """DOCX locator 不应有 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_invalid_batch10():
    """DOCX locator 不应有 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_no_structural_keys_invalid_batch10():
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "value"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_partial_valid_batch10():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"unknown_key": "x"}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- image_resource_ratio 行为深度第十批 ----------


def test_image_resource_no_images_returns_no_image_elements_batch10():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_image_no_resource_path_batch10():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_image_empty_resource_path_batch10():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_image_none_resource_path_batch10():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_existing_file_batch10(tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"fake image data")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_zero_size_file_batch10(tmp_path):
    """size==0 文件视为不存在。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_partial_batch10(tmp_path):
    """部分 image 资源存在。"""
    img_file = tmp_path / "exists.png"
    img_file.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image", "resource_path": str(tmp_path / "no.png")},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_with_base_dir_batch10(tmp_path):
    """resource_path 仅文件名 + image_base_dir 给定 → 拼接查找。"""
    img_file = tmp_path / "x.png"
    img_file.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_with_base_dir_not_found_batch10(tmp_path):
    """resource_path 文件名 + image_base_dir 给定但不存在 → 0.0。"""
    elements = [{"type": "image", "resource_path": "no.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


# ---------- chunk_reference_ratio 行为深度第十批 ----------


def test_chunk_reference_no_chunks_returns_no_chunks_batch10():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_no_elements_batch10():
    """无 elements → 所有 chunk 都无效（ids 都 not in 空 set）。"""
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_valid_ids_batch10():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_missing_id_batch10():
    """chunk 引用了不存在的 element_id → 0.0（整个 chunk 无效）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_no_source_element_ids_key_batch10():
    """chunk 无 source_element_ids → 视为无效。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_empty_source_element_ids_batch10():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_source_element_ids_none_batch10():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_partial_batch10():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["missing"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_all_valid_batch10():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}, {"element_id": "e3"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2", "e3"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- text_preservation 行为深度第十批 ----------


def test_text_preservation_empty_both_batch10():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match_batch10():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_image_excluded_batch10():
    """image element 不参与文本对比。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "should be excluded"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_chunk_text_batch10():
    """chunk 无 text 字段 → 当作 ""。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]
    out = _text_preservation(elements, chunks)
    # expected="abc", actual=""
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] == 0.0
    # precision：common / |actual| = 0 / 0 → null empty_actual
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_extra_chars_in_actual_batch10():
    """actual 含额外字符（重复）→ equal=False, precision<1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcX"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.75  # 3/4


def test_text_preservation_missing_chars_in_actual_batch10():
    """actual 缺字符 → equal=False, recall<1。"""
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] == 0.75  # Counter 交集 = {a,b,c} = 3, |expected|=4


def test_text_preservation_unicode_content_batch10():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_only_batch10():
    """expected 和 actual 仅含空白 → strip 后都为空 → empty_expected_and_actual。"""
    elements = [{"type": "paragraph", "content": "  \n\t "}]
    chunks = [{"text": " "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_returns_three_keys_batch10():
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_extra_chars_in_expected_only_batch10():
    """expected 有内容，actual 完全空 → equal=False, precision null, recall=0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


# ---------- heading_boundary_ratio 行为深度第十批 ----------


def test_heading_boundary_no_headings_returns_no_heading_elements_batch10():
    elements = [{"type": "paragraph"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_batch10():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_perfect_match_batch10():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_no_chunk_starts_with_heading_batch10():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 不是 first
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_partial_match_batch10():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只匹配 h1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_chunk_no_source_element_ids_batch10():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunk_empty_source_element_ids_batch10():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_multiple_headings_match_batch10():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1", "p1"]},
        {"source_element_ids": ["h2", "p2"]},
        {"source_element_ids": ["h3"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- silent_drop_count 行为深度第十批 ----------


def test_silent_drop_no_expectations_returns_no_expectations_batch10():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_no_expectations_dict_batch10():
    """falsy expectations（空 dict）→ no_expectations。"""
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_element_count_by_type_batch10():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_no_drop_batch10():
    by_type = {"paragraph": 5, "heading": 2}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_one_drop_batch10():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2  # 5 - 3


def test_silent_drop_actual_more_than_expected_batch10():
    """actual > expected → 不算 drop（max(0, ...) = 0）。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_mixed_types_batch10():
    by_type = {"paragraph": 5, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2  # heading: 3-1=2


def test_silent_drop_expected_type_missing_in_actual_batch10():
    by_type = {}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5


def test_silent_drop_returns_int_batch10():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert isinstance(out["value"], int)


# ---------- _is_valid_bbox 行为深度第十批 ----------


def test_is_valid_bbox_valid_4_ints_batch10():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_valid_4_floats_batch10():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 100.5]) is True


def test_is_valid_bbox_mixed_int_float_batch10():
    assert _is_valid_bbox([0, 0.0, 100, 100.5]) is True


def test_is_valid_bbox_negative_values_batch10():
    assert _is_valid_bbox([-1, -1, 100, 100]) is True


def test_is_valid_bbox_all_zeros_batch10():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_tuple_rejected_batch10():
    """tuple 不被接受（必须 list）。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_string_rejected_batch10():
    assert _is_valid_bbox(["0", "0", "100", "100"]) is False


def test_is_valid_bbox_none_rejected_batch10():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_rejected_batch10():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_short_rejected_batch10():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_too_long_rejected_batch10():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_string_element_rejected_batch10():
    assert _is_valid_bbox([0, 0, "100", 100]) is False


def test_is_valid_bbox_none_element_rejected_batch10():
    assert _is_valid_bbox([0, 0, None, 100]) is False


def test_is_valid_bbox_bool_element_rejected_batch10():
    """bool 是 int 的子类，但被显式拒绝。"""
    assert _is_valid_bbox([True, 0, 100, 100]) is False


def test_is_valid_bbox_dict_rejected_batch10():
    assert _is_valid_bbox({"x": 0, "y": 0, "w": 100, "h": 100}) is False


def test_is_valid_bbox_set_rejected_batch10():
    assert _is_valid_bbox({0, 0, 100, 100}) is False


def test_is_valid_bbox_list_of_tuples_rejected_batch10():
    assert _is_valid_bbox([(0, 0), (100, 100)]) is False


def test_is_valid_bbox_nan_rejected_batch10():
    assert _is_valid_bbox([0, 0, float("nan"), 100]) is False


def test_is_valid_bbox_inf_rejected_batch10():
    assert _is_valid_bbox([0, 0, float("inf"), 100]) is False


# ---------- _strip_unicode_whitespace 行为深度第十批 ----------


def test_strip_unicode_whitespace_empty_batch10():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace_batch10():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_all_whitespace_batch10():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_whitespace_internal_whitespace_kept_only_non_ws_batch10():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_leading_trailing_batch10():
    assert _strip_unicode_whitespace("  abc  ") == "abc"


def test_strip_unicode_whitespace_nbsp_batch10():
    """NBSP（U+00A0）是 isspace True → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch10():
    """em space（U+2003）→ 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_batch10():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch10():
    """全角空格（U+3000）→ 删除。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch10():
    """U+2028 line separator → isspace True → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch10():
    """U+2029 paragraph separator → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_punctuation_kept_batch10():
    """标点符号不是 isspace → 保留。"""
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_whitespace_unicode_letters_kept_batch10():
    """Unicode 字母不是 isspace → 保留。"""
    assert _strip_unicode_whitespace("你好 world") == "你好world"


def test_strip_unicode_whitespace_returns_str_batch10():
    assert isinstance(_strip_unicode_whitespace("x"), str)


def test_strip_unicode_whitespace_idempotent_batch10():
    """已无非空白后调用 → 不变。"""
    s = "abc"
    assert _strip_unicode_whitespace(_strip_unicode_whitespace(s)) == "abc"


def test_strip_unicode_whitespace_mixed_batch10():
    assert _strip_unicode_whitespace("  a\tb\nc\rd\fe f  ") == "abcdef"


def test_strip_unicode_whitespace_zero_width_not_stripped_batch10():
    """零宽字符（U+200B）isspace False → 不删除。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_bom_not_stripped_batch10():
    """BOM（U+FEFF）isspace False → 不删除。"""
    assert _strip_unicode_whitespace("﻿abc") == "﻿abc"


# ---------- module source forbidden tokens 第十三批 ----------


def test_metrics_source_no_os_system_batch10():
    source = inspect.getsource(mmod)
    assert "os.system" not in source


def test_metrics_source_no_subprocess_batch10():
    source = inspect.getsource(mmod)
    assert "subprocess.Popen" not in source
    assert "subprocess.check_call" not in source


def test_metrics_source_no_pickle_load_batch10():
    source = inspect.getsource(mmod)
    assert "pickle.load" not in source


def test_metrics_source_no_yaml_load_batch10():
    source = inspect.getsource(mmod)
    assert "yaml.load" not in source


def test_metrics_source_no_eval_exec_batch10():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_metrics_source_no_compile_batch10():
    source = inspect.getsource(mmod)
    assert "compile(" not in source


def test_metrics_source_no_sys_exit_batch10():
    source = inspect.getsource(mmod)
    assert "sys.exit" not in source
    assert "exit(" not in source
    assert "quit(" not in source


def test_metrics_source_no_global_keyword_batch10():
    source = inspect.getsource(mmod)
    assert "\nglobal " not in source


def test_metrics_source_no_class_def_batch10():
    source = inspect.getsource(mmod)
    assert "\nclass " not in source


def test_metrics_source_no_async_def_batch10():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_metrics_source_no_yield_batch10():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_metrics_source_no_walrus_batch10():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_metrics_source_no_unlink_remove_batch10():
    source = inspect.getsource(mmod)
    assert ".unlink(" not in source
    assert ".remove(" not in source


def test_metrics_source_no_logging_batch10():
    source = inspect.getsource(mmod)
    assert "logging" not in source
    assert "logger" not in source


def test_metrics_source_no_sleep_batch10():
    source = inspect.getsource(mmod)
    assert "time.sleep" not in source


def test_metrics_source_no_hardcoded_path_batch10():
    source = inspect.getsource(mmod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_math_batch10():
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_imports_counter_batch10():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_imports_path_batch10():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_has_text_types_constant_batch10():
    source = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in source


def test_module_source_has_pdf_bbox_required_types_batch10():
    source = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in source


def test_module_source_has_not_evaluated_constant_batch10():
    source = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in source


def test_module_source_has_null_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _null(reason: str)" in source


def test_module_source_has_ratio_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _ratio(value: float)" in source


def test_module_source_has_bool_metric_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(value: bool)" in source


def test_module_source_has_int_metric_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _int_metric(value: int)" in source


def test_module_source_has_compute_def_batch10():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_has_pdf_locator_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in source


def test_module_source_has_docx_locator_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in source


def test_module_source_has_is_valid_bbox_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in source


def test_module_source_has_image_resource_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in source


def test_module_source_has_chunk_reference_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in source


def test_module_source_has_strip_unicode_whitespace_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in source


def test_module_source_has_text_preservation_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _text_preservation(" in source


def test_module_source_has_heading_boundary_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in source


def test_module_source_has_silent_drop_def_batch10():
    source = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in source


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_uses_counter_intersection_batch10():
    source = inspect.getsource(mmod)
    assert "c_expected & c_actual" in source


def test_module_source_uses_math_isfinite_batch10():
    source = inspect.getsource(mmod)
    assert "math.isfinite" in source


def test_module_source_uses_isspace_batch10():
    source = inspect.getsource(mmod)
    assert ".isspace()" in source


def test_module_source_docstring_present_batch10():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_text_preservation_batch10():
    assert "text_preservation" in mmod.__doc__ or "text preservation" in mmod.__doc__.lower()


def test_module_source_docstring_mentions_pure_function_batch10():
    """docstring 提到纯函数（设计原则）。"""
    assert "纯函数" in mmod.__doc__ or "pure" in mmod.__doc__.lower()


# ---------- signatures 第十批 ----------


def test_signature_null_param_count_batch10():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_signature_null_param_name_batch10():
    sig = inspect.signature(_null)
    assert "reason" in sig.parameters


def test_signature_null_param_annotation_batch10():
    sig = inspect.signature(_null)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "str"


def test_signature_null_return_annotation_batch10():
    sig = inspect.signature(_null)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_ratio_param_count_batch10():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_signature_ratio_param_annotation_batch10():
    sig = inspect.signature(_ratio)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "float"


def test_signature_ratio_return_annotation_batch10():
    sig = inspect.signature(_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_bool_metric_param_count_batch10():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_signature_bool_metric_param_annotation_batch10():
    sig = inspect.signature(_bool_metric)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "bool"


def test_signature_int_metric_param_count_batch10():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_signature_int_metric_param_annotation_batch10():
    sig = inspect.signature(_int_metric)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "int"


def test_signature_compute_metrics_param_count_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_signature_compute_metrics_param_names_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    names = list(sig.parameters)
    assert names == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_param_kinds_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    # 前 4 个 POSITIONAL_OR_KEYWORD，最后 1 个也 POSITIONAL_OR_KEYWORD
    assert all(p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)


def test_signature_compute_metrics_image_base_dir_default_none_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    assert p.default is None


def test_signature_compute_metrics_return_annotation_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_helpers_function_type_batch10():
    for func in (_null, _ratio, _bool_metric, _int_metric):
        assert inspect.isfunction(func)


def test_signature_helpers_module_eq_batch10():
    for func in (_null, _ratio, _bool_metric, _int_metric):
        assert func.__module__ == "evaluation.metrics"


def test_signature_subfuncs_function_type_batch10():
    for func in (
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _strip_unicode_whitespace,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
    ):
        assert inspect.isfunction(func)


def test_signature_subfuncs_module_eq_batch10():
    for func in (
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _strip_unicode_whitespace,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
    ):
        assert func.__module__ == "evaluation.metrics"


def test_signature_compute_metrics_no_var_positional_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_compute_metrics_no_var_keyword_batch10():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十批 ----------


def test_module_no_all_attribute_batch10():
    """metrics.py 有 __all__ = ['compute_automatic_metrics']。"""
    assert hasattr(mmod, "__all__")
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_has_dunder_file_batch10():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_endswith_metrics_py_batch10():
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "metrics.py") or mmod.__file__.endswith(
        "evaluation/metrics.py"
    )


def test_module_dunder_name_batch10():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_function_count_batch10():
    """14 module-level functions + compute_automatic_metrics。"""
    funcs = [
        n
        for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    expected = {
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    }
    assert set(funcs) == expected


def test_module_no_user_classes_batch10():
    classes = [
        n for n, v in vars(mmod).items() if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_constants_count_batch10():
    consts = [
        n
        for n, v in vars(mmod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.ismodule(v)
        and not inspect.isclass(v)
    ]
    # annotations 是 from __future__ import annotations 注入
    assert set(consts) == {"_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED", "annotations"}


def test_module_text_types_value_batch10():
    assert mmod._TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_module_pdf_bbox_required_types_value_batch10():
    assert mmod._PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_module_not_evaluated_value_batch10():
    assert mmod._NOT_EVALUATED == "not_evaluated"


def test_module_pdf_bbox_required_subset_of_text_types_batch10():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集。"""
    assert set(mmod._PDF_BBOX_REQUIRED_TYPES).issubset(set(mmod._TEXT_TYPES))


def test_module_no_call_at_top_level_batch10():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "#",
                '"""',
                "'''",
                "",
                "_",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present_batch10():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_in_chinese_batch10():
    """docstring 含中文（设计原则）。"""
    assert "纯函数" in mmod.__doc__ or "指标" in mmod.__doc__


# ---------- 端到端集成第十批 ----------


def test_e2e_full_pdf_document_with_all_metrics_batch10():
    """完整 PDF 文档 → 所有 metric 都有合理值。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello world",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
                "element_id": "e1",
            },
        ],
        "chunks": [
            {"text": "hello world", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 1
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_full_docx_document_with_all_metrics_batch10():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"paragraph_index": 0},
                "element_id": "e1",
            },
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_full_chain_with_error_dict_batch10():
    """document None + error dict → 14 个 null/false metrics。"""
    error = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"
    # 后续 metric 都 null
    for k in ("element_count_total", "text_preservation_equal", "silent_drop_count"):
        assert out[k]["value"] is None


def test_e2e_kwargs_consistent_with_positional_batch10():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out1 == out2


def test_e2e_no_unexpected_exceptions_batch10():
    """连续调用不抛。"""
    for _ in range(3):
        compute_automatic_metrics(None, None, "pdf", None)


def test_e2e_image_element_no_bbox_batch10():
    """image element 无 bbox → image_resource metric 仍正常。"""
    doc = {
        "elements": [{"type": "image", "resource_path": "/nonexistent.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "image_resource_exists_ratio" in out


def test_e2e_docx_with_relationship_id_batch10():
    doc = {
        "elements": [
            {
                "type": "image",
                "source_locator": {"relationship_id": "rId1"},
            }
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_none_elements_list_batch10():
    """document 无 elements key → 默认 []。"""
    doc = {"chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0


def test_e2e_three_headings_partial_batch10():
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1"},
            {"type": "heading", "element_id": "h2"},
            {"type": "heading", "element_id": "h3"},
        ],
        "chunks": [{"source_element_ids": ["h1"]}],  # 只匹配 h1
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] == 1.0 / 3


def test_e2e_full_chain_keys_check_batch10():
    """compute_automatic_metrics 完整链路：14 个 key。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(out) == 14


def test_e2e_idempotent_under_repeated_calls_batch10():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    out3 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2 == out3


def test_e2e_minimal_doc_returns_pipeline_success_true_batch10():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_e2e_module_can_be_imported_batch10():
    import evaluation.metrics as m
    assert m is mmod
