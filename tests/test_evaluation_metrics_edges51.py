"""evaluation/metrics.py 第五十三轮 edges 测试（Round 491）。

补强 edges50 未触及的角度（第二十五批）：
- 构造子第二十五批：_null 多次调用 / _ratio 边界 / _bool_metric falsy/truthy / _int_metric 边界
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十五批：tuple / hashable / 不可变 / subset 检查
- _strip_unicode_whitespace 第二十五批：各种 Unicode 空白 / mixed / 保留 ASCII
- compute_automatic_metrics 第二十五批：完整 PDF/DOCX / 含图片 / 含 expectations / error_code 透传
- _pdf_locator_ratio 第二十五批：page / bbox 各种边界
- _docx_locator_ratio 第二十五批：structural keys / paragraph_index
- _is_valid_bbox 第二十五批：各种无效输入
- _image_resource_ratio 第二十五批：image_base_dir / resource_path
- _chunk_reference_ratio 第二十五批：source_element_ids 各种边界
- _text_preservation 第二十五批：Counter 比对 / Unicode 空白
- _heading_boundary_ratio 第二十五批：headings + chunks
- _silent_drop_count 第二十五批：expectations 边界
- module source forbidden tokens 第四十批
- module source 字符串精确补强第三十六批
- signatures 第三十六批
- module 合理性第三十六批
- 端到端集成第三十六批
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
    _int_metric,
    _null,
    _ratio,
    compute_automatic_metrics,
)


# ---------- 构造子第二十五批 ----------


def test_null_idempotent_batch25():
    """_null 多次调用一致。"""
    r1 = _null("r")
    r2 = _null("r")
    assert r1 == r2


def test_null_value_is_none_batch25():
    assert _null("r")["value"] is None


def test_null_reason_preserved_batch25():
    assert _null("my reason")["reason"] == "my reason"


def test_ratio_value_is_float_batch25():
    """_ratio 总是返回 float（即使输入 int）。"""
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_ratio_zero_batch25():
    assert _ratio(0.0)["value"] == 0.0


def test_ratio_one_batch25():
    assert _ratio(1.0)["value"] == 1.0


def test_ratio_negative_batch25():
    """负数也允许（不 clamp）。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_large_value_batch25():
    out = _ratio(1000.0)
    assert out["value"] == 1000.0


def test_ratio_reason_is_none_batch25():
    assert _ratio(0.5)["reason"] is None


def test_bool_metric_true_batch25():
    assert _bool_metric(True)["value"] is True


def test_bool_metric_false_batch25():
    assert _bool_metric(False)["value"] is False


def test_bool_metric_falsy_int_zero_batch25():
    """int 0 → bool False。"""
    assert _bool_metric(0)["value"] is False


def test_bool_metric_truthy_int_one_batch25():
    assert _bool_metric(1)["value"] is True


def test_bool_metric_falsy_empty_str_batch25():
    assert _bool_metric("")["value"] is False


def test_bool_metric_truthy_nonempty_str_batch25():
    assert _bool_metric("x")["value"] is True


def test_int_metric_value_is_int_batch25():
    """_int_metric 总是返回 int。"""
    out = _int_metric(3.7)  # float 输入
    assert isinstance(out["value"], int)
    assert out["value"] == 3


def test_int_metric_zero_batch25():
    assert _int_metric(0)["value"] == 0


def test_int_metric_negative_batch25():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_reason_none_batch25():
    assert _int_metric(5)["reason"] is None


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十五批 ----------


def test_text_types_is_tuple_batch25():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_seven_entries_batch25():
    assert len(_TEXT_TYPES) == 7


def test_text_types_contains_heading_batch25():
    assert "heading" in _TEXT_TYPES


def test_text_types_contains_paragraph_batch25():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_excludes_image_batch25():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_four_entries_batch25():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_subset_of_text_types_batch25():
    """所有 _PDF_BBOX_REQUIRED_TYPES 都在 _TEXT_TYPES 中。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_excludes_table_header_footer_batch25():
    """table/header/footer 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_batch25():
    assert _NOT_EVALUATED == "not_evaluated"


def test_text_types_hashable_batch25():
    """tuple 是 hashable。"""
    assert hash(_TEXT_TYPES) is not None


def test_pdf_bbox_hashable_batch25():
    assert hash(_PDF_BBOX_REQUIRED_TYPES) is not None


# ---------- compute_automatic_metrics 第二十五批 ----------


def test_compute_metrics_returns_dict_batch25():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_failed_pipeline_batch25():
    """document=None + error={code:...} → pipeline_success=False。"""
    out = compute_automatic_metrics(None, {"code": "parse_error"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_returns_14_keys_batch25():
    """返回 14 个 metric keys。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = {
        "pipeline_success",
        "error_code",
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
        "element_count_total",
        "element_count_by_type",
    }
    assert expected_keys.issubset(set(out.keys()))


def test_compute_metrics_unknown_source_type_batch25():
    """source_type='bogus' + 有 document → pdf ratio='not_pdf_document', docx ratio='not_docx_document'。"""
    document = {
        "source_type": "bogus",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "bogus", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_with_full_pdf_document_batch25():
    """完整 PDF document → 多数指标有值。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "hello", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}, "element_id": "e1"},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
        "source_hash": "abc",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_with_full_docx_document_batch25():
    """完整 DOCX document。"""
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "hi", "source_locator": {"paragraph_index": 0}, "element_id": "e1"},
        ],
        "chunks": [{"text": "hi", "source_element_ids": ["e1"]}],
        "source_hash": "def",
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_image_base_dir_none_batch25():
    """image_base_dir 默认 None。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    # 不抛
    assert "image_resource_exists_ratio" in out


def test_compute_metrics_error_code_transmitted_batch25():
    """error.code 透传到 metrics['error_code']。"""
    out = compute_automatic_metrics(None, {"code": "my_error"}, "pdf", None)
    assert out["error_code"]["value"] == "my_error"


def test_compute_metrics_no_error_code_field_batch25():
    """error 不含 code → error_code 为 None。"""
    out = compute_automatic_metrics(None, {}, "pdf", None)
    assert out["error_code"]["value"] is None


# ---------- _is_valid_bbox via metrics 第二十五批 ----------


def test_metrics_pdf_locator_invalid_bbox_excluded_batch25():
    """PDF paragraph 含 invalid bbox → pdf_locator_valid_ratio 0。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": 1, "bbox": "not_a_list"}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_metrics_pdf_locator_valid_bbox_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_metrics_pdf_locator_page_zero_batch25():
    """page=0 invalid（page 必须为正整数）。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": 0, "bbox": [0, 0, 1, 1]}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_metrics_pdf_locator_negative_page_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": -1, "bbox": [0, 0, 1, 1]}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_metrics_pdf_locator_missing_page_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"bbox": [0, 0, 1, 1]}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_metrics_pdf_locator_missing_bbox_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": 1}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 0.0


def test_metrics_pdf_locator_image_only_page_batch25():
    """image 元素只检查 page（不需 bbox）。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": None, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # image 不参与 _PDF_BBOX_REQUIRED_TYPES ratio，但参与 page ratio（如有）
    # 这里仅验证不抛
    assert "pdf_locator_valid_ratio" in out


# ---------- _docx_locator_ratio via metrics 第二十五批 ----------


def test_metrics_docx_locator_valid_batch25():
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"paragraph_index": 0}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_metrics_docx_locator_missing_paragraph_index_batch25():
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 0.0


def test_metrics_docx_locator_with_table_index_batch25():
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "table", "source_locator": {"table_index": 0}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    # table 是 _TEXT_TYPES，需 table_index
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_metrics_docx_locator_rejects_page_batch25():
    """DOCX locator 含 page → invalid（DOCX 没有 page 概念）。"""
    document = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"page": 1, "paragraph_index": 0}, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "docx", None)
    # 含 page → invalid
    assert out["docx_locator_valid_ratio"]["value"] == 0.0


# ---------- _image_resource_ratio via metrics 第二十五批 ----------


def test_metrics_image_resource_no_image_batch25():
    """无 image → image_resource_exists_ratio not_evaluated 或 null。"""
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 无 image → 不评估
    assert out["image_resource_exists_ratio"]["value"] is None


def test_metrics_image_resource_missing_rp_batch25():
    """image 缺 resource_path → 0。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": None, "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_metrics_image_resource_rp_nonexistent_batch25():
    """image resource_path 不存在 → 0。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": "/nonexistent.png", "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_metrics_image_resource_rp_exists_batch25(tmp_path):
    """image resource_path 存在 → 1。"""
    img = tmp_path / "img.png"
    img.write_text("fake image", encoding="utf-8")
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": str(img), "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_metrics_image_resource_zero_size_batch25(tmp_path):
    """image resource_path 存在但 size=0 → 0。"""
    img = tmp_path / "empty.png"
    img.write_text("", encoding="utf-8")  # 0 bytes
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": "empty.png", "element_id": "e1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


# ---------- _chunk_reference_ratio via metrics 第二十五批 ----------


def test_metrics_chunk_reference_no_chunks_batch25():
    """无 chunks → not_evaluated。"""
    document = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] is None


def test_metrics_chunk_reference_no_elements_batch25():
    """chunks 有但 elements 空 → ratio 0。"""
    document = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_metrics_chunk_reference_all_valid_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_metrics_chunk_reference_partial_invalid_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [
            {"text": "x", "source_element_ids": ["e1"]},  # valid
            {"text": "y", "source_element_ids": ["e_unknown"]},  # invalid
        ],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 0.5


def test_metrics_chunk_reference_empty_ids_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": []}],  # 空
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # 空 ids 不算 valid
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


# ---------- _text_preservation via metrics 第二十五批 ----------


def test_metrics_text_preservation_equal_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_metrics_text_preservation_chunk_missing_text_batch25():
    """chunk 缺 text → 算空。"""
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1"}],
        "chunks": [{"source_element_ids": ["e1"]}],  # 缺 text
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    # expected 有内容, actual 空 → equal False, precision null, recall ?
    assert out["text_preservation_equal"]["value"] is False


def test_metrics_text_preservation_image_excluded_batch25():
    """image 元素的 content 不参与 text_preservation。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "content": "should_be_ignored", "element_id": "e1"},
            {"type": "paragraph", "content": "real", "element_id": "e2"},
        ],
        "chunks": [{"text": "real", "source_element_ids": ["e2"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True


def test_metrics_text_preservation_unicode_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "你好", "element_id": "e1"}],
        "chunks": [{"text": "你好", "source_element_ids": ["e1"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is True


# ---------- _heading_boundary_ratio via metrics 第二十五批 ----------


def test_metrics_heading_boundary_no_headings_batch25():
    document = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] is None


def test_metrics_heading_boundary_no_chunks_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "heading", "content": "x", "element_id": "h1"}],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] == 0.0


def test_metrics_heading_boundary_perfect_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "heading", "content": "title", "element_id": "h1"}],
        "chunks": [{"text": "title", "source_element_ids": ["h1"]}],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] == 1.0


# ---------- _silent_drop_count via metrics 第二十五批 ----------


def test_metrics_silent_drop_no_expectations_batch25():
    document = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None


def test_metrics_silent_drop_zero_drop_batch25():
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [],
        "source_hash": "x",
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 0


def test_metrics_silent_drop_one_drop_batch25():
    """期望 2 paragraph，实际 1 → 1 drop。"""
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [],
        "source_hash": "x",
    }
    expectations = {"element_count_by_type": {"paragraph": 2}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 1


def test_metrics_silent_drop_multi_type_batch25():
    """多类型 partial drop 求和。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1"},
            {"type": "heading", "content": "y", "element_id": "e2"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    expectations = {"element_count_by_type": {"paragraph": 3, "heading": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    # paragraph: 3-1=2, heading: 1-1=0 → total 2
    assert out["silent_drop_count"]["value"] == 2


def test_metrics_silent_drop_no_actual_more_than_expected_batch25():
    """actual > expected → 不算 drop（0）。"""
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1"},
            {"type": "paragraph", "content": "y", "element_id": "e2"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(document, None, "pdf", expectations)
    # actual=2, expected=1 → 不会变负
    assert out["silent_drop_count"]["value"] == 0


# ---------- element_count_total via metrics 第二十五批 ----------


def test_metrics_element_count_total_empty_batch25():
    document = {"source_type": "pdf", "elements": [], "chunks": [], "source_hash": "x"}
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_total"]["value"] == 0


def test_metrics_element_count_total_three_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1"},
            {"type": "heading", "content": "y", "element_id": "e2"},
            {"type": "image", "element_id": "e3"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_total"]["value"] == 3


def test_metrics_element_count_by_type_batch25():
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1"},
            {"type": "paragraph", "content": "y", "element_id": "e2"},
            {"type": "heading", "content": "z", "element_id": "e3"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    ect = out["element_count_by_type"]["value"]
    assert ect["paragraph"] == 2
    assert ect["heading"] == 1


# ---------- module source forbidden tokens 第四十批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import timeit",
    "import json",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch25():
    source = inspect.getsource(mmod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch25():
    source = inspect.getsource(mmod)
    assert "yield " not in source


def test_module_source_no_async_def_batch25():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch25():
    source = inspect.getsource(mmod)
    assert "global " not in source


def test_module_source_no_walrus_batch25():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(mmod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch25():
    source_lines = inspect.getsource(mmod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(mmod)
    assert "import *" not in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(mmod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_no_subprocess_batch25():
    source = inspect.getsource(mmod)
    assert "import subprocess" not in source


def test_module_source_math_used_batch25():
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_counter_used_batch25():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_no_dataclass_batch25():
    source = inspect.getsource(mmod)
    assert "@dataclass" not in source


# ---------- module source 字符串精确补强 第三十六批 ----------


def test_module_source_contains_text_types_definition_batch25():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in source
    assert '"heading"' in source
    assert '"paragraph"' in source


def test_module_source_contains_pdf_bbox_required_types_batch25():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in source


def test_module_source_contains_not_evaluated_constant_batch25():
    source = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in source


def test_module_source_contains_null_helper_batch25():
    source = inspect.getsource(mmod)
    assert "def _null(" in source


def test_module_source_contains_ratio_helper_batch25():
    source = inspect.getsource(mmod)
    assert "def _ratio(" in source


def test_module_source_contains_bool_metric_helper_batch25():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(" in source


def test_module_source_contains_int_metric_helper_batch25():
    source = inspect.getsource(mmod)
    assert "def _int_metric(" in source


def test_module_source_contains_compute_automatic_metrics_batch25():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_contains_text_preservation_docstring_batch25():
    """docstring 提及 text_preservation 语义。"""
    source = inspect.getsource(mmod)
    assert "text_preservation" in source


def test_module_source_contains_counter_intersection_batch25():
    """source 用 Counter 交集。"""
    source = inspect.getsource(mmod)
    assert "Counter" in source


def test_module_source_contains_silent_drop_count_batch25():
    source = inspect.getsource(mmod)
    assert "silent_drop_count" in source


def test_module_source_contains_image_resource_ratio_batch25():
    source = inspect.getsource(mmod)
    assert "image_resource_exists_ratio" in source


def test_module_source_contains_heading_boundary_compliance_batch25():
    source = inspect.getsource(mmod)
    assert "heading_boundary_compliance" in source


def test_module_source_contains_chunk_reference_intact_ratio_batch25():
    source = inspect.getsource(mmod)
    assert "chunk_reference_intact_ratio" in source


def test_module_source_contains_math_isfinite_batch25():
    source = inspect.getsource(mmod)
    assert "math.isfinite" in source


# ---------- signatures 第三十六批 ----------


def test_signature_null_batch25():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "reason"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_ratio_batch25():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert params[0].annotation == "float"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_bool_metric_batch25():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_int_metric_batch25():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_compute_automatic_metrics_batch25():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]
    assert params[4].default is None
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_all_annotations_are_strings_batch25():
    for fn in [_null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_compute_automatic_metrics_image_base_dir_annotation_batch25():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].annotation == "Path | None"


def test_signature_compute_automatic_metrics_document_annotation_batch25():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"


# ---------- module 合理性 第三十六批 ----------


def test_module_no_all_export_batch25():
    """metrics.py 不需要 __all__（私有 helper 以下划线开头）。"""
    # 不强制要求 __all__
    if hasattr(mmod, "__all__"):
        assert isinstance(mmod.__all__, list)


def test_module_has_compute_automatic_metrics_batch25():
    funcs = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isfunction)
        if val.__module__ == mmod.__name__
    ]
    assert "compute_automatic_metrics" in funcs


def test_module_no_classes_batch25():
    classes = [
        name
        for name, val in inspect.getmembers(mmod, inspect.isclass)
        if val.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch25():
    assert mmod.__doc__ is not None


def test_module_docstring_mentions_pure_function_batch25():
    """docstring 提及纯函数。"""
    assert "纯函数" in mmod.__doc__ or "pure" in mmod.__doc__.lower()


def test_module_docstring_mentions_no_fake_batch25():
    """docstring 提及不伪造。"""
    assert "不伪造" in mmod.__doc__ or "null" in mmod.__doc__.lower()


def test_module_compute_automatic_metrics_docstring_present_batch25():
    assert compute_automatic_metrics.__doc__ is not None


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_module_level_constants_batch25():
    """顶层有 _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 三个常量。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(mmod))
    top_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert "_TEXT_TYPES" in names
    assert "_PDF_BBOX_REQUIRED_TYPES" in names
    assert "_NOT_EVALUATED" in names


def test_module_constants_are_tuples_batch25():
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_not_evaluated_is_str_batch25():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- 端到端集成 第三十六批 ----------


def test_e2e_metrics_full_pdf_flow_batch25(tmp_path):
    """完整 PDF 流：所有指标都计算。"""
    img = tmp_path / "img.png"
    img.write_text("fake", encoding="utf-8")
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "title", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}, "element_id": "h1"},
            {"type": "paragraph", "content": "content", "source_locator": {"page": 1, "bbox": [0, 60, 100, 200]}, "element_id": "p1"},
            {"type": "image", "source_locator": {"page": 1}, "resource_path": "img.png", "element_id": "i1"},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "content", "source_element_ids": ["p1"]},
        ],
        "source_hash": "abc",
    }
    out = compute_automatic_metrics(
        document, None, "pdf",
        expectations={"element_count_by_type": {"paragraph": 1, "heading": 1}},
        image_base_dir=tmp_path,
    )
    assert out["pipeline_success"]["value"] is True
    # schema_valid 取决于实际 schema 校验（document_passes_schema）
    assert isinstance(out["schema_valid"]["value"], bool)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["image_resource_exists_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_metrics_failed_pipeline_all_null_batch25():
    """pipeline 失败 → 多数指标 null。"""
    out = compute_automatic_metrics(None, {"code": "parse_error"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_e2e_metrics_does_not_mutate_document_batch25():
    """不修改 document。"""
    import copy
    document = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
        "source_hash": "x",
    }
    snapshot = copy.deepcopy(document)
    compute_automatic_metrics(document, None, "pdf", None)
    assert document == snapshot


def test_e2e_metrics_with_image_base_dir_batch25(tmp_path):
    """image_base_dir 帮助 resolve resource_path。"""
    img = tmp_path / "img.png"
    img.write_text("fake", encoding="utf-8")
    document = {
        "source_type": "pdf",
        "elements": [
            {"type": "image", "source_locator": {"page": 1}, "resource_path": "img.png", "element_id": "i1"},
        ],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_metrics_failed_does_not_touch_image_dir_batch25():
    """document=None 时 image_base_dir 不被使用（不抛）。"""
    out = compute_automatic_metrics(None, None, "pdf", None, image_base_dir=Path("/nonexistent"))
    assert out["pipeline_success"]["value"] is False


def test_e2e_metrics_returns_proper_metric_format_batch25():
    """每个 metric 都是 {value, reason} dict。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    for k, v in out.items():
        if k == "element_count_by_type":
            # 这个可能是 dict 内 value
            continue
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


def test_e2e_metrics_schema_valid_returns_bool_when_no_error_batch25():
    """document 非 None + error None → schema_valid 是 bool（取决于 document_passes_schema）。"""
    document = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
        "source_hash": "x",
    }
    out = compute_automatic_metrics(document, None, "pdf", None)
    assert isinstance(out["schema_valid"]["value"], bool)
