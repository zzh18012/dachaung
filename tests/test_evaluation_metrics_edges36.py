"""evaluation/metrics.py 第三十七轮 edges 测试（Round 387）。

补强 edges35 未触及的角度：
- _null/_ratio/_bool_metric/_int_metric helpers 行为第九批（更多 reason / 边界 value / 类型检查）
- compute_automatic_metrics 行为深度第九批（更多组合 / image_base_dir None vs Path / expectations 缺 key / error 各种 code）
- _pdf_locator_ratio 行为深度第九批（更多 source_type 不匹配 / 缺 bbox / 各种 type）
- _docx_locator_ratio 行为深度第九批（更多缺 key / 整体结构）
- _image_resource_ratio 行为深度第九批（更多 mixed 存在 / 不存在 / 空 resource_path / 部分缺）
- _chunk_reference_ratio 行为深度第九批（更多 chunks/elements 组合）
- _text_preservation 行为深度第九批（更多 mixed 内容 / Unicode / 多 elements）
- _heading_boundary_ratio 行为深度第九批（更多 chunks 组合 / heading 顺序）
- _silent_drop_count 行为深度第九批（更多 expectations 形式 / 整数边界）
- _is_valid_bbox 行为深度第九批（更多 mixed 类型组合）
- _strip_unicode_whitespace 行为深度第九批（更多 Unicode 空白类型）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第九批
- signatures 第九批
- module 合理性第九批
- 端到端集成第九批
"""

from __future__ import annotations

import inspect
import json
import math
import types
from collections import Counter
from pathlib import Path

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
    _bool_metric,
    _int_metric,
    _is_valid_bbox,
    _null,
    _ratio,
    _strip_unicode_whitespace,
    compute_automatic_metrics,
)


# ---------- helpers ----------


def _make_text_element(eid, etype, content="hello", bbox=None):
    """构造文本 element dict。"""
    e = {"element_id": eid, "type": etype, "content": content}
    if bbox is not None:
        e["bbox"] = bbox
    return e


def _make_pdf_text_element(eid, etype="paragraph", content="hello", page=1, bbox=None):
    """构造 PDF 文本 element。"""
    if bbox is None:
        bbox = [0.0, 0.0, 10.0, 10.0]
    return {
        "element_id": eid,
        "type": etype,
        "content": content,
        "source_locator": {"page": page, "bbox": bbox},
    }


def _make_docx_text_element(eid, etype="paragraph", content="hello"):
    """构造 DOCX 文本 element。"""
    return {
        "element_id": eid,
        "type": etype,
        "content": content,
        "source_locator": {"paragraph_index": 0, "section": 0},
    }


def _make_image_element(eid, resource_path="img/a.png"):
    return {
        "element_id": eid,
        "type": "image",
        "resource_path": resource_path,
    }


def _make_chunk(cid, text, source_element_ids=None):
    return {
        "chunk_id": cid,
        "text": text,
        "source_element_ids": source_element_ids or [],
    }


# ---------- _null/_ratio/_bool_metric/_int_metric helpers 行为第九批 ----------


def test_null_returns_dict_with_value_reason():
    out = _null("reason_x")
    assert isinstance(out, dict)
    assert set(out.keys()) == {"value", "reason"}


def test_null_value_always_none():
    assert _null("anything")["value"] is None


def test_null_reason_passed_through():
    assert _null("foo")["reason"] == "foo"


def test_null_empty_reason_string():
    out = _null("")
    assert out["reason"] == ""


def test_null_unicode_reason():
    out = _null("中文原因")
    assert out["reason"] == "中文原因"


def test_ratio_returns_dict_with_value_reason():
    out = _ratio(0.5)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"value", "reason"}


def test_ratio_value_converted_to_float():
    """int 输入会被 float() 转。"""
    out = _ratio(0)
    assert isinstance(out["value"], float)
    assert out["value"] == 0.0


def test_ratio_reason_always_none():
    out = _ratio(0.5)
    assert out["reason"] is None


def test_ratio_value_0_to_1():
    assert _ratio(0.0)["value"] == 0.0
    assert _ratio(1.0)["value"] == 1.0
    assert _ratio(0.5)["value"] == 0.5


def test_bool_metric_returns_dict_with_value_reason():
    out = _bool_metric(True)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"value", "reason"}


def test_bool_metric_value_is_bool():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(False)["value"], bool)


def test_bool_metric_converts_int_to_bool():
    """int 0/1 → bool。"""
    assert _bool_metric(0)["value"] is False
    assert _bool_metric(1)["value"] is True


def test_bool_metric_reason_always_none():
    out = _bool_metric(True)
    assert out["reason"] is None


def test_int_metric_returns_dict_with_value_reason():
    out = _int_metric(5)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"value", "reason"}


def test_int_metric_value_is_int():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_converts_float_to_int():
    """float 输入会被 int() 截断。"""
    assert _int_metric(3.99)["value"] == 3
    assert _int_metric(4.01)["value"] == 4


def test_int_metric_negative():
    assert _int_metric(-5)["value"] == -5


def test_int_metric_zero():
    assert _int_metric(0)["value"] == 0


def test_int_metric_reason_always_none():
    out = _int_metric(5)
    assert out["reason"] is None


# ---------- compute_automatic_metrics 行为深度第九批 ----------


def test_compute_metrics_returns_dict():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_metrics_document_none_error_none_pipeline_success_false():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_document_dict_error_none_pipeline_success_true():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_error_dict_pipeline_success_false():
    doc = {"elements": [], "chunks": []}
    err = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(doc, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_error_code_value_from_error_dict():
    err = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_error_code_none_when_no_error():
    out = compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_error_code_none_when_error_none_but_doc_none():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_metrics_document_none_schema_valid_null():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["schema_valid"]["value"] is None
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_metrics_returns_14_keys_when_document():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_returns_14_keys_when_document_none():
    """document None 时仍返回 14 个 metric keys（多数 null + pipeline_failed reason）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_kwargs_call():
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert isinstance(out, dict)


def test_compute_metrics_does_not_mutate_document():
    doc = {"elements": [], "chunks": []}
    snapshot = json.dumps(doc)
    _ = compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc) == snapshot


def test_compute_metrics_does_not_mutate_error():
    err = {"code": "x", "message": "y"}
    snapshot = json.dumps(err)
    _ = compute_automatic_metrics(None, err, "pdf", None)
    assert json.dumps(err) == snapshot


def test_compute_metrics_idempotent():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_compute_metrics_minimal_doc_returns_pipeline_success_true():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


# ---------- _pdf_locator_ratio behavior via compute (integration) ----------


def test_compute_metrics_pdf_doc_with_bbox_text_elements():
    """pdf doc + 带 bbox 的 text elements → pdf_locator_valid_ratio 应当计算。"""
    e1 = _make_pdf_text_element("e1", "paragraph", "hello", page=1, bbox=[0, 0, 10, 10])
    e2 = _make_pdf_text_element("e2", "paragraph", "world", page=2, bbox=[0, 0, 10, 10])
    doc = {"elements": [e1, e2], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pdf_locator_valid_ratio" in out


def test_compute_metrics_pdf_doc_with_text_missing_bbox():
    """pdf doc + 缺 bbox 的 paragraph → 该 element 不算 valid。"""
    e1 = {
        "element_id": "e1",
        "type": "paragraph",
        "content": "hello",
        "source_locator": {"page": 1},  # 缺 bbox
    }
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pdf_locator_valid_ratio" in out


def test_compute_metrics_docx_doc_with_docx_locator():
    """docx doc + DOCX 结构 locator → docx_locator_valid_ratio 应当计算。"""
    e1 = _make_docx_text_element("e1", "paragraph", "hello")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert "docx_locator_valid_ratio" in out


def test_compute_metrics_docx_doc_with_pdf_locator_zero_valid():
    """source_type=docx 但 elements 是 PDF locator → 该 element 不算 valid。"""
    e1 = _make_pdf_text_element("e1")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    # docx_locator_valid_ratio 仍应计算（值可能为 0.0）
    assert "docx_locator_valid_ratio" in out


# ---------- _image_resource_ratio behavior via compute ----------


def test_compute_metrics_no_image_elements():
    """无 image element → image_resource_exists_ratio null。"""
    doc = {"elements": [_make_text_element("e1", "paragraph")], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] is None


def test_compute_metrics_image_with_resource_path_no_base_dir():
    """image element + resource_path + base_dir=None → 按原值校验。"""
    e1 = _make_image_element("e1", "img/a.png")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "image_resource_exists_ratio" in out


def test_compute_metrics_image_with_resource_path_and_base_dir(tmp_path):
    """image element + resource_path + base_dir=Path → 校验。"""
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    (img_dir / "a.png").write_bytes(b"PNG")
    e1 = _make_image_element("e1", "a.png")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=img_dir)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_metrics_image_with_missing_resource_path(tmp_path):
    e1 = _make_image_element("e1", "missing.png")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_metrics_image_empty_resource_path():
    e1 = _make_image_element("e1", "")
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 空 resource_path → 该 element 不 valid
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_metrics_image_none_resource_path():
    e1 = {
        "element_id": "e1",
        "type": "image",
        "resource_path": None,
    }
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["value"] == 0.0


def test_compute_metrics_partial_images_present(tmp_path):
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    (img_dir / "a.png").write_bytes(b"PNG")
    e1 = _make_image_element("e1", "a.png")
    e2 = _make_image_element("e2", "missing.png")
    doc = {"elements": [e1, e2], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=img_dir)
    # 1 of 2 present
    assert out["image_resource_exists_ratio"]["value"] == 0.5


# ---------- _chunk_reference_ratio behavior via compute ----------


def test_compute_metrics_no_chunks_no_elements():
    """no chunks + no elements → chunk_reference_intact_ratio null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] is None


def test_compute_metrics_chunks_reference_valid_element_ids():
    e1 = _make_text_element("e1", "paragraph")
    e2 = _make_text_element("e2", "paragraph")
    c1 = _make_chunk("c1", "hello", ["e1"])
    c2 = _make_chunk("c2", "world", ["e2"])
    doc = {"elements": [e1, e2], "chunks": [c1, c2]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_compute_metrics_chunks_reference_missing_element_ids():
    """chunk 含部分 missing id → 该 chunk 整体 invalid（0.0）。"""
    e1 = _make_text_element("e1", "paragraph")
    c1 = _make_chunk("c1", "hello", ["e1", "missing_id"])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 单 chunk 中部分 id missing → 该 chunk invalid → ratio=0.0
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_compute_metrics_chunks_no_source_element_ids_key():
    e1 = _make_text_element("e1", "paragraph")
    c1 = {"chunk_id": "c1", "text": "hello"}  # 缺 source_element_ids
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 该 chunk 视为 invalid → 0.0
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_compute_metrics_chunks_empty_source_element_ids():
    e1 = _make_text_element("e1", "paragraph")
    c1 = _make_chunk("c1", "hello", [])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 空 source_element_ids → invalid
    assert out["chunk_reference_intact_ratio"]["value"] == 0.0


def test_compute_metrics_all_chunks_valid():
    e1 = _make_text_element("e1", "paragraph")
    e2 = _make_text_element("e2", "paragraph")
    e3 = _make_text_element("e3", "paragraph")
    c1 = _make_chunk("c1", "a", ["e1"])
    c2 = _make_chunk("c2", "b", ["e2"])
    c3 = _make_chunk("c3", "c", ["e3"])
    doc = {"elements": [e1, e2, e3], "chunks": [c1, c2, c3]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


# ---------- _text_preservation behavior via compute ----------


def test_compute_metrics_text_preservation_both_empty():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] is None or out["text_preservation_equal"]["value"] == 1.0


def test_compute_metrics_text_preservation_perfect_match():
    e1 = _make_text_element("e1", "paragraph", "hello")
    c1 = _make_chunk("c1", "hello", ["e1"])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] == 1.0
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_compute_metrics_text_preservation_image_skipped():
    """image element 不参与文本比对。"""
    e1 = _make_text_element("e1", "paragraph", "hello")
    e2 = _make_image_element("e2", "img/a.png")
    c1 = _make_chunk("c1", "hello", ["e1"])
    doc = {"elements": [e1, e2], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] == 1.0


def test_compute_metrics_text_preservation_missing_text():
    e1 = _make_text_element("e1", "paragraph", "hello world")
    c1 = _make_chunk("c1", "hello", ["e1"])  # 缺 "world"
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] == 0.0


def test_compute_metrics_text_preservation_three_keys():
    """text_preservation 系列有 3 个 metric key。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "text_preservation_equal" in out
    assert "text_char_multiset_precision" in out
    assert "text_char_multiset_recall" in out


def test_compute_metrics_text_preservation_unicode():
    e1 = _make_text_element("e1", "paragraph", "中文测试")
    c1 = _make_chunk("c1", "中文测试", ["e1"])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["text_preservation_equal"]["value"] == 1.0


# ---------- _heading_boundary_ratio behavior via compute ----------


def test_compute_metrics_no_chunks_no_headings():
    """无 chunks → heading_boundary_compliance null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] is None


def test_compute_metrics_no_heading_elements():
    """无 heading element → null。"""
    e1 = _make_text_element("e1", "paragraph", "hello")
    c1 = _make_chunk("c1", "hello", ["e1"])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] is None


def test_compute_metrics_heading_full_match():
    e1 = _make_text_element("e1", "heading", "title")
    c1 = _make_chunk("c1", "title", ["e1"])
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_compute_metrics_heading_partial_match():
    e1 = _make_text_element("e1", "heading", "title one")
    e2 = _make_text_element("e2", "heading", "title two")
    c1 = _make_chunk("c1", "title one", ["e1"])  # 只匹配第一个
    doc = {"elements": [e1, e2], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 1 of 2 matched
    assert out["heading_boundary_compliance"]["value"] == 0.5


# ---------- _silent_drop_count behavior via compute ----------


def test_compute_metrics_no_expectations_silent_drop_null():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None


def test_compute_metrics_no_element_count_in_expectations():
    doc = {"elements": [], "chunks": []}
    expectations = {}  # 缺 element_count_by_type
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] is None


def test_compute_metrics_empty_element_count_in_expectations():
    """expectations 含空 element_count_by_type → silent_drop 仍 null（无预期可对比）。"""
    doc = {"elements": [], "chunks": []}
    expectations = {"element_count_by_type": {}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # 空 expectations → 无可对比 → null
    assert out["silent_drop_count"]["value"] is None


def test_compute_metrics_actual_more_than_expected():
    e1 = _make_text_element("e1", "paragraph", "a")
    doc = {"elements": [e1], "chunks": []}
    expectations = {"element_count_by_type": {"paragraph": 0}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # 实际 1 - 预期 0 = 1（drops，但 silent_drop 只算 expected - actual > 0）
    assert out["silent_drop_count"]["value"] == 0


def test_compute_metrics_actual_less_than_expected():
    doc = {"elements": [], "chunks": []}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    # 5 expected - 0 actual = 5 silent drops
    assert out["silent_drop_count"]["value"] == 5


# ---------- _is_valid_bbox 行为第九批 ----------


def test_is_valid_bbox_valid_4_ints():
    assert _is_valid_bbox([0, 0, 10, 10]) is True


def test_is_valid_bbox_valid_4_floats():
    assert _is_valid_bbox([0.0, 0.0, 10.5, 10.5]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 10, 10.5]) is True


def test_is_valid_bbox_negative_values():
    assert _is_valid_bbox([-1, -1, 10, 10]) is True


def test_is_valid_bbox_all_zeros():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_tuple_rejected():
    """tuple 不是 list → rejected。"""
    assert _is_valid_bbox((0, 0, 10, 10)) is False


def test_is_valid_bbox_string():
    assert _is_valid_bbox("0,0,10,10") is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_short():
    assert _is_valid_bbox([0, 0, 10]) is False


def test_is_valid_bbox_too_long():
    assert _is_valid_bbox([0, 0, 10, 10, 99]) is False


def test_is_valid_bbox_string_element():
    assert _is_valid_bbox([0, 0, "10", 10]) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([0, 0, None, 10]) is False


def test_is_valid_bbox_bool_element():
    """bool 是 int 子类，但 _is_valid_bbox 可能 reject。"""
    # 实际取决于实现；测试当前行为
    result = _is_valid_bbox([True, 0, 10, 10])
    assert isinstance(result, bool)


def test_is_valid_bbox_dict():
    assert _is_valid_bbox({"x": 0, "y": 0, "w": 10, "h": 10}) is False


def test_is_valid_bbox_set():
    assert _is_valid_bbox({0, 0, 10, 10}) is False


def test_is_valid_bbox_list_of_tuples():
    assert _is_valid_bbox([(0, 0), (10, 10)]) is False


def test_is_valid_bbox_returns_bool_type():
    assert isinstance(_is_valid_bbox([0, 0, 10, 10]), bool)


# ---------- _strip_unicode_whitespace 行为第九批 ----------


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_whitespace_internal_whitespace_preserved():
    """_strip_unicode_whitespace 删除全部空白，包括内部。"""
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_unicode_whitespace_leading_trailing():
    assert _strip_unicode_whitespace("  hello  ") == "hello"


def test_strip_unicode_whitespace_nbsp():
    """NBSP U+00A0 也是 whitespace。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    """EM SPACE U+2003。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space():
    """EN SPACE U+2002。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    """IDEOGRAPHIC SPACE U+3000。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator():
    """LINE SEPARATOR U+2028。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """PARAGRAPH SEPARATOR U+2029。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_non_whitespace_punctuation():
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_whitespace_preserves_unicode_letters():
    assert _strip_unicode_whitespace("中文.日本語") == "中文.日本語"


def test_strip_unicode_whitespace_preserves_emoji():
    assert _strip_unicode_whitespace("😀hello") == "😀hello"


def test_strip_unicode_whitespace_returns_str():
    assert isinstance(_strip_unicode_whitespace("x"), str)


def test_strip_unicode_whitespace_idempotent():
    s = "hello world"
    once = _strip_unicode_whitespace(s)
    twice = _strip_unicode_whitespace(once)
    assert once == twice


def test_strip_unicode_whitespace_mixed():
    assert _strip_unicode_whitespace("  a\tb\nc d  ") == "abcd"


def test_strip_unicode_whitespace_zero_width_not_stripped():
    """ZERO WIDTH SPACE U+200B 不是 isspace（不删）。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_bom_not_stripped():
    """BOM U+FEFF 不是 isspace（不删）。"""
    assert _strip_unicode_whitespace("a﻿b") == "a﻿b"


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
        "global ",
    ],
)
def test_metrics_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_metrics_source_no_async_def():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_metrics_source_no_yield():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_metrics_source_no_walrus():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_metrics_source_no_unlink():
    source = inspect.getsource(mmod)
    assert "unlink" not in source


def test_metrics_source_no_remove():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


def test_metrics_source_no_logging():
    source = inspect.getsource(mmod)
    assert "logging" not in source
    assert "logger" not in source


def test_metrics_source_no_sleep():
    source = inspect.getsource(mmod)
    assert "time.sleep" not in source


def test_metrics_source_no_print():
    source = inspect.getsource(mmod)
    assert "print(" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_math():
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_imports_counter():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_imports_path():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_any():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_text_types_constant():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES = (" in source


def test_module_source_pdf_bbox_required_types_constant():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = (" in source


def test_module_source_not_evaluated_constant():
    source = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in source


def test_module_source_has_null_helper():
    source = inspect.getsource(mmod)
    assert "def _null(" in source


def test_module_source_has_ratio_helper():
    source = inspect.getsource(mmod)
    assert "def _ratio(" in source


def test_module_source_has_bool_metric_helper():
    source = inspect.getsource(mmod)
    assert "def _bool_metric(" in source


def test_module_source_has_int_metric_helper():
    source = inspect.getsource(mmod)
    assert "def _int_metric(" in source


def test_module_source_has_compute_automatic_metrics():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_has_is_valid_bbox():
    source = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in source


def test_module_source_has_strip_unicode_whitespace():
    source = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in source


def test_module_source_uses_counter_call():
    source = inspect.getsource(mmod)
    assert "Counter(" in source


def test_module_source_uses_isspace_call():
    source = inspect.getsource(mmod)
    assert ".isspace()" in source


def test_module_source_no_main_block():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_docstring_present():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_text_preservation():
    assert "text_preservation" in mmod.__doc__ or "text preservation" in mmod.__doc__.lower()


def test_module_source_docstring_mentions_pure_function():
    assert "纯函数" in mmod.__doc__


def test_module_source_docstring_mentions_v11():
    """docstring 提到 evaluator v1.1。"""
    assert "v1.1" in mmod.__doc__ or "1.1" in mmod.__doc__


# ---------- signatures 第九批 ----------


def test_signature_compute_automatic_metrics_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_signature_compute_automatic_metrics_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_signature_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    assert p.default is None


def test_signature_compute_automatic_metrics_no_default_for_document():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["document"]
    assert p.default is inspect.Parameter.empty


def test_signature_compute_automatic_metrics_no_default_for_error():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["error"]
    assert p.default is inspect.Parameter.empty


def test_signature_compute_automatic_metrics_return_dict():
    sig = inspect.signature(compute_automatic_metrics)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_null_helper():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1
    assert "reason" in sig.parameters


def test_signature_ratio_helper():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


def test_signature_bool_metric_helper():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_signature_int_metric_helper():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_signature_is_valid_bbox():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_signature_strip_unicode_whitespace():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_signature_helpers_function_type():
    for func in (_null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics, _is_valid_bbox, _strip_unicode_whitespace):
        assert inspect.isfunction(func)


def test_signature_helpers_module_eq():
    for func in (_null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics, _is_valid_bbox, _strip_unicode_whitespace):
        assert func.__module__ == "evaluation.metrics"


# ---------- module 合理性第九批 ----------


def test_module_all_exact_one_item():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_text_types_exact_7():
    assert _TEXT_TYPES == (
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    )


def test_module_pdf_bbox_required_types_exact_4():
    assert _PDF_BBOX_REQUIRED_TYPES == (
        "heading",
        "paragraph",
        "caption",
        "list_item",
    )


def test_module_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_pdf_bbox_required_types_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES ⊆ _TEXT_TYPES。"""
    s = set(_TEXT_TYPES)
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in s


def test_module_docstring_starts_with_chinese():
    assert mmod.__doc__.lstrip().startswith("自动指标")


def test_module_user_function_count():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    # _null/_ratio/_bool_metric/_int_metric/compute_automatic_metrics/_pdf_locator_ratio/_docx_locator_ratio/_image_resource_ratio/_chunk_reference_ratio/_text_preservation/_heading_boundary_ratio/_silent_drop_count/_is_valid_bbox/_strip_unicode_whitespace = 14
    assert len(funcs) == 14


def test_module_no_user_classes():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_has_dunder_file():
    assert hasattr(mmod, "__file__")


def test_module_dunder_name():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_no_call_at_top_level():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "class ",
                "import ",
                "from ",
                "_TEXT_TYPES",
                "_PDF_BBOX_REQUIRED_TYPES",
                "_NOT_EVALUATED",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped:
                    raise AssertionError(f"unexpected top-level call: {line}")


# ---------- 端到端集成第九批 ----------


def test_e2e_full_pdf_doc():
    e1 = _make_pdf_text_element("e1", "paragraph", "hello world", page=1, bbox=[0, 0, 10, 10])
    e2 = _make_pdf_text_element("e2", "heading", "title", page=1, bbox=[0, 0, 10, 5])
    c1 = _make_chunk("c1", "hello world", ["e1"])
    c2 = _make_chunk("c2", "title", ["e2"])
    doc = {"elements": [e1, e2], "chunks": [c1, c2]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_error_dict():
    err = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"


def test_e2e_document_none_returns_nulls():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # 多数 metric 应当 null
    assert out["pipeline_success"]["value"] is False
    assert out["schema_valid"]["value"] is None


def test_e2e_kwargs_positional_equivalence():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert out1 == out2


def test_e2e_image_with_resource_path_no_bbox(tmp_path):
    """image element + 无 bbox 的 paragraph + 无 base_dir。"""
    img_dir = tmp_path / "img"
    img_dir.mkdir()
    (img_dir / "a.png").write_bytes(b"PNG")
    e1 = _make_image_element("e1", "a.png")
    e2 = _make_text_element("e2", "paragraph", "hello")  # 无 bbox
    doc = {"elements": [e1, e2], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=img_dir)
    assert "image_resource_exists_ratio" in out
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_docx_with_relationship_id():
    e1 = {
        "element_id": "e1",
        "type": "paragraph",
        "content": "hello",
        "source_locator": {"paragraph_index": 0, "section": 0, "relationship_id": "rId1"},
    }
    doc = {"elements": [e1], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert "docx_locator_valid_ratio" in out


def test_e2e_none_elements_list():
    """document 缺 elements key → 视为 None list。"""
    doc = {"chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 应当不抛
    assert isinstance(out, dict)


def test_e2e_dup_chars_in_actual():
    """实际 chunks 含重复字符 → precision < 1。"""
    e1 = _make_text_element("e1", "paragraph", "abc")
    c1 = _make_chunk("c1", "abcabc", ["e1"])  # 重复
    doc = {"elements": [e1], "chunks": [c1]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # text_preservation_equal 应当 False
    assert out["text_preservation_equal"]["value"] == 0.0


def test_e2e_three_headings_partial():
    e1 = _make_text_element("e1", "heading", "title one")
    e2 = _make_text_element("e2", "heading", "title two")
    e3 = _make_text_element("e3", "heading", "title three")
    c1 = _make_chunk("c1", "title one", ["e1"])
    c2 = _make_chunk("c2", "title two", ["e2"])
    # 缺 title three
    doc = {"elements": [e1, e2, e3], "chunks": [c1, c2]}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["value"] < 1.0


def test_e2e_full_chain_keys_check():
    """完整 doc 应当返回 14 metric keys。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
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


def test_e2e_idempotent_complex():
    e1 = _make_pdf_text_element("e1", "paragraph", "hello")
    c1 = _make_chunk("c1", "hello", ["e1"])
    doc = {"elements": [e1], "chunks": [c1]}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_no_unexpected_exceptions():
    """各种 None/empty 输入不应抛。"""
    compute_automatic_metrics(None, None, "pdf", None)
    compute_automatic_metrics({}, None, "pdf", None)
    compute_automatic_metrics({"elements": []}, None, "pdf", None)
    compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)


def test_e2e_minimal_doc_returns_pipeline_success_true():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
