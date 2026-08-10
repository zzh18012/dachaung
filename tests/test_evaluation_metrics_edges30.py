"""evaluation/metrics.py 第三十一轮 edges 测试（Round 346）。

重点补强 edges29 未触及的角度：
- _null/_ratio/_bool_metric/_int_metric 行为深度第六批（更多 type coercion / str / bytes / bool）
- _TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED 常量第三批
- compute_automatic_metrics 行为深度第三批（error.code 传播 / image_base_dir / schema_valid 异常路径 / by_type 累计）
- _image_resource_ratio 行为深度第三批（resource_path 是 Path/绝对路径/各种异常）
- _chunk_reference_ratio 行为深度第三批（source_element_ids 是 None/空/含重复）
- _heading_boundary_ratio 行为深度第三批（chunk ids 顺序 / heading 无 element_id）
- _silent_drop_count 行为深度第三批（expectations 含 0 / actual > expected / type 不在 expectations）
- _is_valid_bbox 行为深度第三批（更多类型组合）
- _strip_unicode_whitespace 行为深度第三批（各种 Unicode 空白 / 中文 / emoji）
- _text_preservation 行为深度第三批（precision != recall / Counter min 语义）
- module source forbidden tokens 第八批
- module source 字符串精确补强（更多）
- signatures 精确补强（更多）
- 模块整体合理性（更多）
- 端到端集成补强（更多）
"""

from __future__ import annotations

import inspect
import math
import types
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
    _bool_metric,
    _chunk_reference_ratio,
    compute_automatic_metrics,
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
)


# ---------- _null/_ratio/_bool_metric/_int_metric 行为深度第六批 ----------


def test_null_with_empty_reason():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_with_unicode_reason():
    out = _null("中文原因")
    assert out["reason"] == "中文原因"


def test_null_with_long_reason():
    long_reason = "x" * 1000
    out = _null(long_reason)
    assert out["reason"] == long_reason


def test_null_with_special_chars_reason():
    out = _null("reason: 'with quotes' and \"double\"")
    assert "quotes" in out["reason"]


def test_null_returns_dict_with_2_keys():
    out = _null("r")
    assert len(out) == 2
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_with_float_value():
    out = _ratio(0.123456789)
    assert out["value"] == 0.123456789


def test_ratio_with_inf_raises_or_returns():
    """float('inf') 是合法 float 但不应当出现 ratio 中。"""
    try:
        out = _ratio(float("inf"))
        assert math.isinf(out["value"])
    except (TypeError, ValueError, OverflowError):
        pass


def test_ratio_with_nan_returns_nan():
    """float('nan') 是合法 float 但语义无意义。"""
    out = _ratio(float("nan"))
    assert math.isnan(out["value"])


def test_ratio_with_bool_input():
    """bool 是 int 的子类；float(True) = 1.0。"""
    out = _ratio(True)  # type: ignore[arg-type]
    assert out["value"] == 1.0


def test_ratio_with_false_bool_input():
    out = _ratio(False)  # type: ignore[arg-type]
    assert out["value"] == 0.0


def test_bool_metric_returns_value_true():
    out = _bool_metric(True)
    assert out["value"] is True


def test_bool_metric_returns_value_false():
    out = _bool_metric(False)
    assert out["value"] is False


def test_bool_metric_with_truthy_input():
    """bool(1) = True。"""
    out = _bool_metric(1)  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_with_falsy_input():
    """bool(0) = False。"""
    out = _bool_metric(0)  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_empty_string():
    """bool('') = False。"""
    out = _bool_metric("")  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_nonempty_string():
    """bool('x') = True。"""
    out = _bool_metric("x")  # type: ignore[arg-type]
    assert out["value"] is True


def test_bool_metric_with_none_input():
    """bool(None) = False。"""
    out = _bool_metric(None)  # type: ignore[arg-type]
    assert out["value"] is False


def test_bool_metric_with_list_input():
    """bool([]) = False, bool([1]) = True。"""
    assert _bool_metric([])["value"] is False  # type: ignore[arg-type]
    assert _bool_metric([1])["value"] is True  # type: ignore[arg-type]


def test_int_metric_with_int_input():
    out = _int_metric(42)
    assert out["value"] == 42
    assert isinstance(out["value"], int)


def test_int_metric_with_bool_input():
    """bool 是 int 子类；int(True) = 1。"""
    out = _int_metric(True)  # type: ignore[arg-type]
    assert out["value"] == 1
    assert isinstance(out["value"], int)


def test_int_metric_with_float_input_truncates():
    """int(3.7) = 3。"""
    out = _int_metric(3.7)  # type: ignore[arg-type]
    assert out["value"] == 3


def test_int_metric_with_negative_int():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_with_zero():
    out = _int_metric(0)
    assert out["value"] == 0


def test_int_metric_with_huge_int():
    out = _int_metric(10**18)
    assert out["value"] == 10**18


def test_int_metric_with_string_numeric():
    """int('5') = 5（不抛）。"""
    out = _int_metric("5")  # type: ignore[arg-type]
    assert out["value"] == 5


def test_int_metric_with_string_raises():
    """int('x') 抛 ValueError。"""
    with pytest.raises(ValueError):
        _int_metric("x")  # type: ignore[arg-type]


def test_int_metric_returns_dict_with_2_keys():
    out = _int_metric(1)
    assert set(out.keys()) == {"value", "reason"}
    assert out["reason"] is None


def test_helpers_return_dict_with_value_first():
    """所有 4 helper 都返回 {value: ..., reason: ...}，value 在前。"""
    null_out = _null("r")
    ratio_out = _ratio(0.5)
    bool_out = _bool_metric(True)
    int_out = _int_metric(1)
    for out in (null_out, ratio_out, bool_out, int_out):
        keys = list(out.keys())
        assert keys[0] == "value"
        assert keys[1] == "reason"


def test_helpers_do_not_share_state():
    """helper 返回的 dict 应是独立的（不应共享引用）。"""
    a = _null("r")
    b = _null("r")
    a["value"] = "modified"
    assert b["value"] is None


def test_helpers_dict_is_mutable():
    """返回的 dict 是普通 dict，可修改。"""
    out = _ratio(0.5)
    out["value"] = 0.99
    assert out["value"] == 0.99


# ---------- _TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED 常量第三批 ----------


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


def test_text_types_count_is_7():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_count_is_4():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types():
    """PDF bbox 必备类型应是 _TEXT_TYPES 的子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_pdf_bbox_required_types_includes_heading():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_paragraph():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_caption():
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_includes_list_item():
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_table():
    """table 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_header():
    """header 不需要 bbox。"""
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_excludes_footer():
    """footer 不需要 bbox。"""
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_constant_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_constant_type():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


# ---------- compute_automatic_metrics 行为深度第三批 ----------


def test_compute_metrics_error_code_propagates():
    """error.code 在 metrics["error_code"]["value"]。"""
    error = {"code": "PARSE_FAILED", "message": "x"}
    out = compute_automatic_metrics(
        document=None,
        error=error,
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] == "PARSE_FAILED"


def test_compute_metrics_error_code_none_when_no_error():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["error_code"]["value"] is None


def test_compute_metrics_pipeline_success_true_when_doc_present():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_pipeline_success_false_when_doc_none():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_false_when_both_none():
    """document=None + error=None → pipeline_success=False（document is None）。"""
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_schema_valid_for_minimal_doc():
    """document 含最少字段 → schema_valid=True。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # schema_valid 是 bool
    assert out["schema_valid"]["reason"] is None


def test_compute_metrics_returns_11_metric_keys_when_pipeline_failed():
    """document=None → 返回 4 + 11 keys（pipeline_success/error_code/schema_valid/element_count_*）。"""
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
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


def test_compute_metrics_returns_14_metric_keys_when_pipeline_succeeded():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
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


def test_compute_metrics_by_type_counts_correctly():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "h"},
            {"type": "paragraph", "element_id": "p1", "content": "p1"},
            {"type": "paragraph", "element_id": "p2", "content": "p2"},
            {"type": "image", "element_id": "i1"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"heading": 1, "paragraph": 2, "image": 1}


def test_compute_metrics_element_count_total_correct():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [{"element_id": f"e{i}"} for i in range(5)],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_total"]["value"] == 5


def test_compute_metrics_with_image_base_dir_none():
    """image_base_dir=None 也能工作。"""
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert "image_resource_exists_ratio" in out


def test_compute_metrics_with_image_base_dir_path(tmp_path):
    """image_base_dir 是 Path。"""
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=tmp_path,
    )
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_metrics_doc_with_elements_no_chunks():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "source_locator": {"sha256": "x"},
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="docx",
        expectations=None,
    )
    # 无 chunks → chunk_reference_intact_ratio = null no_chunks
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_metrics_does_not_modify_document():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [{"type": "heading", "element_id": "h1", "content": "h"}],
        "chunks": [{"text": "h", "source_element_ids": ["h1"]}],
    }
    import json as _json
    before = _json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    after = _json.dumps(doc, sort_keys=True)
    assert before == after


def test_compute_metrics_idempotent():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [],
        "chunks": [],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_compute_metrics_returns_dict():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_unknown_source_type():
    """source_type 不是 pdf/docx → pdf_locator_ratio null not_pdf + docx null not_docx。"""
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="unknown",
        expectations=None,
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_with_expectations_none():
    """expectations=None → silent_drop_count null no_expectations。"""
    out = compute_automatic_metrics(
        document={
            "document_id": "d1",
            "source_type": "pdf",
            "source_locator": {"sha256": "x"},
            "elements": [],
            "chunks": [],
        },
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_metrics_with_expectations_empty():
    out = compute_automatic_metrics(
        document={
            "document_id": "d1",
            "source_type": "pdf",
            "source_locator": {"sha256": "x"},
            "elements": [],
            "chunks": [],
        },
        error=None,
        source_type="pdf",
        expectations={},
    )
    assert out["silent_drop_count"]["reason"] == "no_expectations"


# ---------- _image_resource_ratio 行为深度第三批 ----------


def test_image_resource_ratio_with_resource_path_none():
    """resource_path=None → 跳过（不算 valid）。"""
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    # valid=0, total=1 → 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_with_resource_path_empty_string():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_no_image_returns_null():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_with_existing_file(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_with_zero_size_file(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    # size=0 → 不算 valid → 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_with_image_base_dir(tmp_path):
    """resource_path 是文件名，image_base_dir 拼接后能找到。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG" + b"0" * 50)
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_valid_invalid(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG" + b"0" * 50)
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "nonexistent.png"},
        {"type": "image", "resource_path": None},
    ]
    out = _image_resource_ratio(elements, None)
    # 1 valid out of 3 → 1/3
    assert out["value"] == pytest.approx(1 / 3)


def test_image_resource_ratio_oserror_continues():
    """OSError 不应中断（如 Path 含非法字符）。"""
    # 用一个非常长的 path 触发 OSError
    elements = [{"type": "image", "resource_path": "x" * 10000}]
    out = _image_resource_ratio(elements, None)
    # OSError caught, ok=False → 0/1=0.0
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 行为深度第三批 ----------


def test_chunk_reference_ratio_chunks_empty_returns_null():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_no_chunks_arg():
    """chunks=[]。"""
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_chunks_with_empty_ids():
    """chunks 全无 source_element_ids。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # valid=0/1=0.0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_with_none_ids():
    chunks = [{"text": "x", "source_element_ids": None}]
    elements = [{"element_id": "e1"}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids=None → []  → 不算 valid → 0.0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunks_with_missing_ids_key():
    chunks = [{"text": "x"}]  # 无 source_element_ids
    elements = [{"element_id": "e1"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_valid():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"text": "a", "source_element_ids": ["e1"]},
        {"text": "b", "source_element_ids": ["e_unknown"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    # 1 valid out of 2 → 0.5
    assert out["value"] == 0.5


def test_chunk_reference_ratio_duplicate_ids_in_chunk():
    """重复 id 仍 valid（all 检查通过）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "a", "source_element_ids": ["e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_ids_subset_of_elements():
    """chunk 引用多个 element_id，部分未知 → invalid。"""
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"text": "a", "source_element_ids": ["e1", "e3"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # e3 不在 elements 中 → invalid → 0/1=0.0
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 行为深度第三批 ----------


def test_heading_boundary_ratio_no_headings_returns_null():
    elements = [{"type": "paragraph"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_returns_zero():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # 无 chunks → chunk_first_ids 空 → matched=0 → 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"text": "a", "source_element_ids": ["h1"]},
        {"text": "b", "source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"text": "a", "source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # 1 matched out of 2 headings → 0.5
    assert out["value"] == 0.5


def test_heading_boundary_ratio_heading_no_element_id():
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"text": "a", "source_element_ids": ["x"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # h.get("element_id") = None, None not in {"x"} → matched=0 → 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunk_ids_only_first_matters():
    """只看 chunk 第一个 source_element_id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "a", "source_element_ids": ["first", "h1"]},  # h1 是第 2 个
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids = {"first"}，h1 不在 → matched=0 → 0.0
    assert out["value"] == 0.0


def test_heading_boundary_ratio_chunks_with_empty_ids_skipped():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "a", "source_element_ids": []},  # 空 → skip
        {"text": "b", "source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_dedup_via_set():
    """两个 chunks 第一个 id 相同只算一次（set 去重）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"text": "a", "source_element_ids": ["h1"]},
        {"text": "b", "source_element_ids": ["h1"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # set 去重后 chunk_first_ids = {"h1"} → matched=1 → 1.0
    assert out["value"] == 1.0


# ---------- _silent_drop_count 行为深度第三批 ----------


def test_silent_drop_count_no_expectations():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations():
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_by_type():
    out = _silent_drop_count({}, {"other_key": "x"})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count_by_type():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_equals_expected():
    by_type = {"heading": 2}
    expectations = {"element_count_by_type": {"heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_greater_than_expected():
    by_type = {"heading": 5}
    expectations = {"element_count_by_type": {"heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    # actual > expected → max(0, 2-5)=0 → drops=0
    assert out["value"] == 0


def test_silent_drop_count_partial_drop():
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # max(0, 3-1)=2 → drops=2
    assert out["value"] == 2


def test_silent_drop_count_multiple_types_summed():
    by_type = {"heading": 0, "paragraph": 2}
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    # heading: max(0,1-0)=1; paragraph: max(0,5-2)=3 → drops=4
    assert out["value"] == 4


def test_silent_drop_count_type_not_in_actual():
    by_type = {}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # actual.get("heading", 0)=0 → max(0,3-0)=3
    assert out["value"] == 3


def test_silent_drop_count_returns_int_value():
    out = _silent_drop_count({"a": 0}, {"element_count_by_type": {"a": 1}})
    assert isinstance(out["value"], int)


# ---------- _is_valid_bbox 行为深度第三批 ----------


def test_is_valid_bbox_valid_4_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_valid_4_floats():
    assert _is_valid_bbox([0.0, 0.0, 1.5, 2.5]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.5, 100, 200.5]) is True


def test_is_valid_bbox_negative_values():
    assert _is_valid_bbox([-1, -1, 0, 0]) is True


def test_is_valid_bbox_zero_bbox():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_3_elements():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_5_elements():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_none_input():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string_input():
    assert _is_valid_bbox("0,0,1,1") is False


def test_is_valid_bbox_dict_input():
    assert _is_valid_bbox({"x": 0, "y": 0}) is False


def test_is_valid_bbox_tuple_input():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_with_bool_true():
    """bool 是 int 子类但被显式拒绝。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_with_bool_false():
    assert _is_valid_bbox([False, 0, 0, 0]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_is_valid_bbox_with_string_element():
    assert _is_valid_bbox(["0", 0, 0, 0]) is False


def test_is_valid_bbox_with_none_element():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


def test_is_valid_bbox_with_dict_element():
    assert _is_valid_bbox([{}, 0, 0, 0]) is False


# ---------- _strip_unicode_whitespace 行为深度第三批 ----------


def test_strip_with_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_with_leading_space():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_with_trailing_space():
    assert _strip_unicode_whitespace("hello ") == "hello"


def test_strip_with_both_spaces():
    assert _strip_unicode_whitespace(" hello ") == "hello"


def test_strip_with_internal_space():
    """内部空格也删除（不只是 strip）。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_tab():
    assert _strip_unicode_whitespace("hello\tworld") == "helloworld"


def test_strip_with_newline():
    assert _strip_unicode_whitespace("hello\nworld") == "helloworld"


def test_strip_with_carriage_return():
    assert _strip_unicode_whitespace("hello\rworld") == "helloworld"


def test_strip_with_form_feed():
    assert _strip_unicode_whitespace("hello\fworld") == "helloworld"


def test_strip_with_vertical_tab():
    assert _strip_unicode_whitespace("hello\vworld") == "helloworld"


def test_strip_with_nbsp():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_em_space():
    """U+2003 EM SPACE。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_en_space():
    """U+2002 EN SPACE。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_ideographic_space():
    """U+3000 IDEOGRAPHIC SPACE。"""
    assert _strip_unicode_whitespace("hello　world") == "helloworld"


def test_strip_with_line_separator():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_with_multiple_whitespace_types():
    s = "hello \t\n 　world"
    assert _strip_unicode_whitespace(s) == "helloworld"


def test_strip_with_only_whitespace():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_with_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_preserves_emoji():
    assert _strip_unicode_whitespace("hello 🌍 world") == "hello🌍world"


def test_strip_preserves_chinese():
    assert _strip_unicode_whitespace("你好 世界") == "你好世界"


def test_strip_preserves_digits():
    assert _strip_unicode_whitespace("hello 123 world") == "hello123world"


def test_strip_preserves_punctuation():
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


def test_strip_preserves_unicode_letters():
    assert _strip_unicode_whitespace("café à Paris") == "caféàParis"


# ---------- _text_preservation 行为深度第三批 ----------


def test_text_preservation_no_elements_no_chunks():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_chunks_missing_text():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]  # 无 text
    out = _text_preservation(elements, chunks)
    # actual = "" → not equal
    assert out["equal"]["value"] is False
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_elements_missing_content():
    elements = [{}]  # 无 content
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_with_image_ignored():
    """image element 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image"},  # 无 content
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_returns_3_metric_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_equal_dict_has_value_reason():
    out = _text_preservation([{"content": "x", "type": "paragraph"}], [{"text": "x"}])
    assert set(out["equal"].keys()) == {"value", "reason"}
    assert set(out["precision"].keys()) == {"value", "reason"}
    assert set(out["recall"].keys()) == {"value", "reason"}


def test_text_preservation_precision_recall_difference():
    """precision=common/actual，recall=common/expected。"""
    # expected: "aaa" (3 a's)
    # actual: "a" (1 a)
    # common = min(3, 1) = 1
    # precision = 1/1 = 1.0
    # recall = 1/3 ≈ 0.333
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == pytest.approx(1 / 3)


def test_text_preservation_counter_intersection_takes_min():
    """Counter 交集对每个字符取 min。"""
    # expected: "ab" → {a:1, b:1}
    # actual: "aa" → {a:2}
    # common = min(1,2)=1 for a + min(0,1)=0 for b → 1
    # precision = 1/2 = 0.5
    # recall = 1/2 = 0.5
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 0.5


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_dummy_thread", "_markupbase", "_strptime", "_threading_local",
        "_weakrefset", "_collections_abc", "_compat_pickle", "_sitebuiltins",
        "_sysconfigdata", "_pyio", "_dummy_backtrace", "abc", "aifc", "antigravity",
        "argparse", "asdl", "ast", "asyncio", "atexit", "audioop",
        "base64", "bdb", "binascii", "binhex", "builtins",
        "bz2", "cProfile", "calendar", "cgi", "cgitb", "cmath",
        "cmd", "code", "codecs", "codeop", "colorsys", "compileall",
        "configparser", "contextvars", "contextlib", "copyreg", "concurrent",
        "copy", "crypt", "curses", "dataclasses", "datetime",
        "decimal", "difflib", "dis", "distutils", "doctest",
        "email", "encodings", "ensurepip", "enum", "errno",
        "faulthandler", "fcntl", "filecmp", "fileinput", "fnmatch",
        "formatter", "fractions", "ftplib", "functools", "gc",
        "genericpath", "getopt", "getpass", "gettext", "glob",
        "grp", "gzip", "hashlib", "heapq", "hmac",
        "html", "http", "idlelib", "imaplib", "imghdr",
        "importlib", "inspect", "ipaddress", "itertools", "keyword",
        "lib2to3", "linecache", "locale", "logging", "lzma",
        "mailbox", "mailcap", "marshal", "mimetypes",
        "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing",
        "netrc", "nis", "nntplib", "ntpath", "numbers",
        "opcode", "operator", "optparse", "ossaudiodev", "parser",
        "pdb", "pickle", "pickletools", "pipes", "pkgutil",
        "platform", "plistlib", "poplib", "posix", "posixpath",
        "pprint", "profile", "pstats", "pty", "pwd",
        "py_compile", "pyclbr", "pydoc", "pydoc_data", "pyexpat",
        "queue", "quopri", "random", "readline",
        "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex",
        "shutil", "signal", "site", "smtpd", "smtplib",
        "sndhdr", "socket", "socketserver", "spwd", "sqlite3",
        "sre_compile", "sre_constants", "sre_parse", "ssl", "stat",
        "statistics", "string", "stringprep", "subprocess", "sunau",
        "symtable", "syslog", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap",
        "threading", "time", "timeit", "tkinter", "token",
        "tokenize", "trace", "tracemalloc", "tty", "turtle",
        "turtledemo", "types", "unicodedata", "unittest", "urllib",
        "uu", "uuid", "venv", "warnings", "wave",
        "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
        "xdrlib", "xmlrpc", "zipapp", "zipfile", "zipimport",
        "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_eighth_batch(token):
    """这些 stdlib 不应出现在 metrics.py（仅 math/Counter/Path/Any）。"""
    src = inspect.getsource(mmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(mmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_pure_function():
    src = inspect.getsource(mmod)
    assert "纯函数" in src


def test_module_source_docstring_mentions_counter():
    src = inspect.getsource(mmod)
    assert "Counter" in src


def test_module_source_docstring_mentions_no_modify():
    src = inspect.getsource(mmod)
    assert "不修改" in src


def test_module_source_docstring_mentions_unicode_whitespace():
    src = inspect.getsource(mmod)
    assert "Unicode 空白" in src or "Unicode" in src


def test_module_source_docstring_mentions_no_fake():
    src = inspect.getsource(mmod)
    assert "不伪造" in src


def test_module_source_imports_math():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_imports_counter():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_imports_path():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_5_module_level_imports_only():
    """5 module-level imports: __future__, math, Counter, Path, Any（不含 lazy import）。"""
    src = inspect.getsource(mmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")  # module-level only
    ]
    assert len(import_lines) == 5


def test_module_source_no_relative_import():
    src = inspect.getsource(mmod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(mmod)
    assert "import *" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(mmod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def" not in src


def test_module_source_no_global():
    src = inspect.getsource(mmod)
    assert "global " not in src


def test_module_source_no_decorators_at_module_level():
    src = inspect.getsource(mmod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_no_class_definition():
    src = inspect.getsource(mmod)
    body_lines = [
        (i, line) for i, line in enumerate(src.splitlines())
        if not line.strip().startswith(("#", '"', "'"))
    ]
    for i, line in body_lines:
        if line.startswith("class "):
            pytest.fail(f"unexpected class at line {i}: {line}")


def test_module_source_has_3_module_level_constants():
    src = inspect.getsource(mmod)
    const_count = sum(1 for line in src.splitlines() if line.startswith("_") and " = " in line and not line.startswith("__"))
    assert const_count >= 3  # _TEXT_TYPES, _PDF_BBOX_REQUIRED_TYPES, _NOT_EVALUATED


def test_module_source_defines_text_types():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES = " in src


def test_module_source_defines_pdf_bbox_required_types():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = " in src


def test_module_source_defines_not_evaluated():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_has_compute_automatic_metrics_function():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_helper_functions():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src
    assert "def _docx_locator_ratio(" in src
    assert "def _is_valid_bbox(" in src
    assert "def _image_resource_ratio(" in src
    assert "def _chunk_reference_ratio(" in src
    assert "def _strip_unicode_whitespace(" in src
    assert "def _text_preservation(" in src
    assert "def _heading_boundary_ratio(" in src
    assert "def _silent_drop_count(" in src


def test_module_source_has_4_one_liner_helpers():
    src = inspect.getsource(mmod)
    assert "def _null(" in src
    assert "def _ratio(" in src
    assert "def _bool_metric(" in src
    assert "def _int_metric(" in src


def test_module_source_no_eval_exec():
    src = inspect.getsource(mmod)
    assert "eval(" not in src
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(mmod)
    assert "compile(" not in src


def test_module_source_no_os_import():
    src = inspect.getsource(mmod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_uses_math_isfinite():
    src = inspect.getsource(mmod)
    assert "math.isfinite" in src


def test_module_source_uses_counter_intersection():
    src = inspect.getsource(mmod)
    assert "c_expected & c_actual" in src


def test_module_source_uses_dot_join_or_iter():
    src = inspect.getsource(mmod)
    assert ".join(" in src or "for ch in s" in src


def test_module_source_uses_isspace():
    src = inspect.getsource(mmod)
    assert "ch.isspace()" in src or ".isspace()" in src


def test_module_source_all_with_1_entry():
    src = inspect.getsource(mmod)
    assert "__all__" in src
    assert '"compute_automatic_metrics"' in src


def test_module_source_lazy_imports_schema_validation():
    """compute_automatic_metrics 内部 lazy import schema_validation。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import" in src


def test_module_source_compute_metrics_uses_try_except_for_schema():
    src = inspect.getsource(compute_automatic_metrics)
    assert "try:" in src
    assert "except Exception" in src


# ---------- signatures 精确补强 ----------


def test_compute_automatic_metrics_signature_param_count_5():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_signature_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_no_varargs():
    sig = inspect.signature(compute_automatic_metrics)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_null_signature_1_param():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_null_param_name():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_null_param_annotation_str():
    sig = inspect.signature(_null)
    a = sig.parameters["reason"].annotation
    assert a is str or a == "str"


def test_null_return_annotation_dict():
    sig = inspect.signature(_null)
    assert "dict" in str(sig.return_annotation)


def test_ratio_signature_1_param():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_ratio_param_annotation_float():
    sig = inspect.signature(_ratio)
    a = sig.parameters["value"].annotation
    assert a is float or a == "float"


def test_ratio_return_annotation_dict():
    sig = inspect.signature(_ratio)
    assert "dict" in str(sig.return_annotation)


def test_bool_metric_signature_1_param():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_int_metric_signature_1_param():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_pdf_locator_ratio_signature_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_docx_locator_ratio_signature_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_signature_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_image_resource_ratio_signature_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_chunk_reference_ratio_signature_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_strip_unicode_whitespace_signature_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_text_preservation_signature_2_params():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_heading_boundary_ratio_signature_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_signature_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_no_function_has_varargs():
    functions = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType) and v.__module__ == mmod.__name__
    ]
    for fn in functions:
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds, f"{fn.__name__} has VAR_POSITIONAL"
        assert inspect.Parameter.VAR_KEYWORD not in kinds, f"{fn.__name__} has VAR_KEYWORD"


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(mmod, types.ModuleType)


def test_module_namespace_name():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_namespace_has_file():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_namespace_has_doc():
    assert mmod.__doc__ is not None


def test_module_namespace_has_all():
    assert hasattr(mmod, "__all__")


def test_module_all_has_1_entry():
    assert len(mmod.__all__) == 1


def test_module_all_entries_exact():
    assert set(mmod.__all__) == {"compute_automatic_metrics"}


def test_module_namespace_has_compute_automatic_metrics():
    assert hasattr(mmod, "compute_automatic_metrics")


def test_module_namespace_has_constants():
    assert hasattr(mmod, "_TEXT_TYPES")
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_has_helpers_callable():
    assert callable(_null)
    assert callable(_ratio)
    assert callable(_bool_metric)
    assert callable(_int_metric)
    assert callable(_pdf_locator_ratio)
    assert callable(_docx_locator_ratio)
    assert callable(_is_valid_bbox)
    assert callable(_image_resource_ratio)
    assert callable(_chunk_reference_ratio)
    assert callable(_strip_unicode_whitespace)
    assert callable(_text_preservation)
    assert callable(_heading_boundary_ratio)
    assert callable(_silent_drop_count)
    assert callable(compute_automatic_metrics)


def test_module_no_user_classes():
    classes = [
        v for v in vars(mmod).values()
        if isinstance(v, type) and v.__module__ == mmod.__name__
    ]
    assert len(classes) == 0


def test_module_helpers_module_eq_metrics():
    functions = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType) and v.__module__ == mmod.__name__
    ]
    for fn in functions:
        assert fn.__module__ == "evaluation.metrics"


def test_module_has_14_module_level_functions():
    """compute_automatic_metrics + 4 helpers + 9 子函数 = 14。"""
    functions = [
        v for v in vars(mmod).values()
        if isinstance(v, types.FunctionType) and v.__module__ == mmod.__name__
    ]
    assert len(functions) == 14


# ---------- 端到端集成补强 ----------


def test_e2e_full_pdf_doc_with_image(tmp_path):
    """完整 PDF 文档 + 1 张存在的图片。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG" + b"0" * 50)
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [
            {
                "type": "heading",
                "element_id": "h1",
                "content": "Title",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]},
            },
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "Hello",
                "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]},
            },
            {
                "type": "image",
                "element_id": "i1",
                "resource_path": str(img),
                "source_locator": {"page": 1},
            },
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Hello", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=tmp_path,
    )
    assert out["element_count_total"]["value"] == 3
    assert out["image_resource_exists_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_full_docx_doc():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "source_locator": {"sha256": "x"},
        "elements": [
            {
                "type": "heading",
                "element_id": "h1",
                "content": "Title",
                "source_locator": {"section": 0, "paragraph_index": 0},
            },
            {
                "type": "paragraph",
                "element_id": "p1",
                "content": "Hello",
                "source_locator": {"section": 0, "paragraph_index": 1},
            },
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Hello", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_text_preservation_real_case():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello world"},
            {"type": "paragraph", "element_id": "p2", "content": "foo bar"},
        ],
        "chunks": [
            {"text": "hello ", "source_element_ids": ["p1"]},
            {"text": "world", "source_element_ids": ["p1"]},
            {"text": "foo ", "source_element_ids": ["p2"]},
            {"text": "bar", "source_element_ids": ["p2"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # expected: "helloworldfoobar"
    # actual: "hello worldfoo bar" → strip ws → "helloworldfoobar"
    # equal = True
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_silent_drop_real_case():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [
            {"type": "heading", "element_id": "h1"},
            {"type": "paragraph", "element_id": "p1"},
            {"type": "paragraph", "element_id": "p2"},
        ],
        "chunks": [],
    }
    expectations = {
        "element_count_by_type": {
            "heading": 2,
            "paragraph": 5,
        }
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=expectations,
    )
    # actual: heading=1, paragraph=2
    # silent_drop: max(0,2-1)+max(0,5-2) = 1+3 = 4
    assert out["silent_drop_count"]["value"] == 4


def test_e2e_does_not_mutate_inputs_dict():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"heading": 1}}
    import json as _json
    doc_before = _json.dumps(doc, sort_keys=True)
    exp_before = _json.dumps(expectations, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", expectations)
    assert _json.dumps(doc, sort_keys=True) == doc_before
    assert _json.dumps(expectations, sort_keys=True) == exp_before


def test_e2e_with_error_no_document():
    error = {"code": "PARSE_FAILED", "message": "x"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["error_code"]["value"] == "PARSE_FAILED"
    assert out["pipeline_success"]["value"] is False
    # 所有 element_count_* 应是 null
    assert out["element_count_total"]["reason"] == "pipeline_failed"


def test_e2e_idempotent_complex():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "source_locator": {"sha256": "x"},
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "T"},
            {"type": "paragraph", "element_id": "p1", "content": "B"},
        ],
        "chunks": [{"text": "TB", "source_element_ids": ["h1", "p1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_json_serializable_output():
    import json as _json
    out = compute_automatic_metrics(
        document={
            "document_id": "d1",
            "source_type": "pdf",
            "source_locator": {"sha256": "x"},
            "elements": [],
            "chunks": [],
        },
        error=None,
        source_type="pdf",
        expectations=None,
    )
    s = _json.dumps(out)
    assert isinstance(s, str)


def test_e2e_call_with_all_kwargs():
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert isinstance(out, dict)


def test_e2e_call_with_all_positional():
    out = compute_automatic_metrics(None, None, "pdf", None, None)
    assert isinstance(out, dict)
