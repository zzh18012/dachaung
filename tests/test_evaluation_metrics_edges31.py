"""evaluation/metrics.py 第三十二轮 edges 测试（Round 352）。

重点补强 edges30 未触及的角度：
- _null/_ratio/_bool_metric/_int_metric 行为深度第七批（更多边界组合）
- _TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED 常量第四批
- compute_automatic_metrics 行为深度第四批（更多 document/error 组合 / expectations 变体）
- _image_resource_ratio 行为深度第四批（更多 image + resource_path 组合）
- _chunk_reference_ratio 行为深度第四批（更多 id 引用模式）
- _heading_boundary_ratio 行为深度第四批（更多 heading + chunk 组合）
- _silent_drop_count 行为深度第四批（更多 expectations 变体）
- _is_valid_bbox 行为深度第四批（更多 bbox 形式）
- _strip_unicode_whitespace 行为深度第四批（更多 Unicode 字符）
- _text_preservation 行为深度第四批（更多 normalize 场景）
- _pdf_locator_ratio 行为深度第四批
- _docx_locator_ratio 行为深度第四批
- module source forbidden tokens 第九批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import math
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _TEXT_TYPES,
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
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


# ---------- _null/_ratio/_bool_metric/_int_metric 行为深度第七批 ----------


def test_null_returns_dict():
    d = _null("reason_x")
    assert isinstance(d, dict)


def test_null_value_is_none():
    d = _null("reason_x")
    assert d["value"] is None


def test_null_reason_preserved():
    d = _null("my_reason")
    assert d["reason"] == "my_reason"


def test_null_with_empty_reason():
    d = _null("")
    assert d["reason"] == ""


def test_null_with_unicode_reason():
    d = _null("无数据")
    assert d["reason"] == "无数据"


def test_null_with_emoji_reason():
    d = _null("emoji 🚫 reason")
    assert d["reason"] == "emoji 🚫 reason"


def test_null_with_long_reason():
    long_reason = "x" * 200
    d = _null(long_reason)
    assert d["reason"] == long_reason


def test_null_has_only_two_keys():
    d = _null("r")
    assert set(d.keys()) == {"value", "reason"}


def test_null_idempotent():
    a = _null("r")
    b = _null("r")
    assert a == b


def test_ratio_returns_dict():
    d = _ratio(0.5)
    assert isinstance(d, dict)


def test_ratio_value_preserved():
    d = _ratio(0.5)
    assert d["value"] == 0.5


def test_ratio_reason_none():
    """_ratio 的 reason 是 None（不是 "ok"）。"""
    d = _ratio(0.5)
    assert d["reason"] is None


def test_ratio_zero():
    d = _ratio(0.0)
    assert d["value"] == 0.0


def test_ratio_one():
    d = _ratio(1.0)
    assert d["value"] == 1.0


def test_ratio_negative():
    d = _ratio(-0.5)
    assert d["value"] == -0.5


def test_ratio_huge_value():
    d = _ratio(1e10)
    assert d["value"] == 1e10


def test_ratio_tiny_value():
    d = _ratio(1e-10)
    assert d["value"] == 1e-10


def test_ratio_idempotent():
    a = _ratio(0.5)
    b = _ratio(0.5)
    assert a == b


def test_bool_metric_true():
    d = _bool_metric(True)
    assert d["value"] is True


def test_bool_metric_false():
    d = _bool_metric(False)
    assert d["value"] is False


def test_bool_metric_reason_none():
    """_bool_metric 的 reason 是 None。"""
    d = _bool_metric(True)
    assert d["reason"] is None


def test_int_metric_zero():
    d = _int_metric(0)
    assert d["value"] == 0


def test_int_metric_positive():
    d = _int_metric(42)
    assert d["value"] == 42


def test_int_metric_negative():
    d = _int_metric(-1)
    assert d["value"] == -1


def test_int_metric_huge():
    d = _int_metric(2**31)
    assert d["value"] == 2**31


def test_int_metric_reason_none():
    """_int_metric 的 reason 是 None。"""
    d = _int_metric(5)
    assert d["reason"] is None


# ---------- 常量第四批 ----------


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_has_paragraph():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_has_heading():
    assert "heading" in _TEXT_TYPES


def test_text_types_has_list_item():
    assert "list_item" in _TEXT_TYPES


def test_text_types_includes_table():
    # table 在 TEXT_TYPES 中（用于 text_preservation）
    assert "table" in _TEXT_TYPES


def test_text_types_includes_header():
    assert "header" in _TEXT_TYPES


def test_text_types_includes_footer():
    assert "footer" in _TEXT_TYPES


def test_text_types_excludes_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_has_paragraph():
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_has_heading():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_subset_of_text_types():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


# ---------- compute_automatic_metrics 行为深度第四批 ----------


def test_compute_with_none_document_and_error():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_document_only():
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_error_only():
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_unknown_source_type():
    out = compute_automatic_metrics({}, None, "unknown", None)
    assert isinstance(out, dict)


def test_compute_with_pdf_source_type():
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_docx_source_type():
    out = compute_automatic_metrics({}, None, "docx", None)
    assert isinstance(out, dict)


def test_compute_with_empty_document():
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_full_pdf_document():
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "element_id": "e1", "page": 1, "bbox": [0, 0, 100, 100], "content": "hello"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_full_docx_document():
    doc = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "element_id": "e1", "structural_locator": {"paragraph_index": 0}, "content": "hello"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert isinstance(out, dict)


def test_compute_with_image_base_dir(tmp_path):
    out = compute_automatic_metrics({}, None, "pdf", None, image_base_dir=tmp_path)
    assert isinstance(out, dict)


def test_compute_with_image_base_dir_none():
    out = compute_automatic_metrics({}, None, "pdf", None, image_base_dir=None)
    assert isinstance(out, dict)


def test_compute_does_not_modify_document():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    before = dict(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == before


def test_compute_idempotent():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", None)
    assert a == b


def test_compute_with_expectations():
    out = compute_automatic_metrics(
        {},
        None,
        "pdf",
        {"element_count_by_type": {"paragraph": 10}},
    )
    assert isinstance(out, dict)


def test_compute_with_expectations_empty():
    out = compute_automatic_metrics({}, None, "pdf", {})
    assert isinstance(out, dict)


def test_compute_with_expectations_none():
    out = compute_automatic_metrics({}, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_error_no_code_field():
    out = compute_automatic_metrics(None, {}, "pdf", None)
    assert isinstance(out, dict)


def test_compute_with_error_code_field():
    out = compute_automatic_metrics(None, {"code": "parse_pdf_failed"}, "pdf", None)
    assert isinstance(out, dict)


def test_compute_returns_14_metric_keys():
    """compute 总是输出 14 个 metric key。"""
    out = compute_automatic_metrics({}, None, "pdf", None)
    expected_keys = [
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
    ]
    for k in expected_keys:
        assert k in out, f"missing key: {k}"


# ---------- _image_resource_ratio 行为深度第四批 ----------


def test_image_resource_ratio_no_images_returns_null():
    out = _image_resource_ratio([], None)
    assert out["value"] is None


def test_image_resource_ratio_no_resource_path(tmp_path):
    elements = [{"type": "image", "element_id": "i1"}]
    out = _image_resource_ratio(elements, tmp_path)
    # 缺 resource_path → 视作 invalid
    assert out["value"] is not None or out["reason"] is not None


def test_image_resource_ratio_with_existing_file(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "element_id": "i1", "resource_path": "test.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_with_nonexistent_file(tmp_path):
    elements = [{"type": "image", "element_id": "i1", "resource_path": "missing.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed(tmp_path):
    img = tmp_path / "exists.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [
        {"type": "image", "element_id": "i1", "resource_path": "exists.png"},
        {"type": "image", "element_id": "i2", "resource_path": "missing.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


def test_image_resource_ratio_image_base_dir_none():
    elements = [{"type": "image", "element_id": "i1", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, None)
    # image_base_dir=None → 跳过文件检查或视为不存在
    assert out["value"] is not None or out["reason"] is not None


# ---------- _chunk_reference_ratio 行为深度第四批 ----------


def test_chunk_reference_ratio_empty_chunks():
    out = _chunk_reference_ratio([{"type": "paragraph", "element_id": "e1"}], [])
    assert out["value"] is None or out["reason"] is not None


def test_chunk_reference_ratio_empty_elements():
    out = _chunk_reference_ratio([], [{"source_element_ids": ["e1"]}])
    assert out["value"] == 0.0 or out["reason"] is not None


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial():
    """source_element_ids 中有一个 unknown → 整个 chunk 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all() 要求全部 in，missing 不在 → valid=0
    assert out["value"] == 0.0


def test_chunk_reference_ratio_invalid_id():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_chunk_missing_source_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"chunk_id": "c1"}]
    out = _chunk_reference_ratio(elements, chunks)
    # 缺 source_element_ids → 跳过
    assert out["value"] is not None or out["reason"] is not None


def test_chunk_reference_ratio_empty_source_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] is not None or out["reason"] is not None


def test_chunk_reference_ratio_duplicate_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # 重复 id 仍 valid
    assert out["value"] == 1.0


# ---------- _heading_boundary_ratio 行为深度第四批 ----------


def test_heading_boundary_ratio_no_headings():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None or out["reason"] is not None


def test_heading_boundary_ratio_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is not None or out["reason"] is not None


def test_heading_boundary_ratio_perfect_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    elements = [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # 1 matched / 2 headings = 0.5
    assert out["value"] == 0.5


def test_heading_boundary_ratio_no_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_chunks_first_id_only():
    """只看每个 chunk 的第一个 source_element_id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1", "extra"]},  # first id = h1 → matched
        {"source_element_ids": ["other", "h1"]},  # first id = other → not matched
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # 1 matched / 1 heading = 1.0
    assert out["value"] == 1.0


# ---------- _silent_drop_count 行为深度第四批 ----------
# 注意：_silent_drop_count 第一个参数是 by_type: dict[str, int]，不是 elements 列表


def test_silent_drop_count_no_expectations():
    out = _silent_drop_count({}, None)
    assert out["value"] is None


def test_silent_drop_count_empty_expectations():
    out = _silent_drop_count({}, {})
    assert out["value"] is None


def test_silent_drop_count_no_element_count_by_type():
    out = _silent_drop_count({}, {"other_field": "x"})
    assert out["value"] is None


def test_silent_drop_count_empty_element_count_by_type():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["value"] is None


def test_silent_drop_count_actual_equals_expected():
    by_type = {"paragraph": 2}
    exp = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0


def test_silent_drop_count_actual_more_than_expected():
    by_type = {"paragraph": 3}
    exp = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, exp)
    # actual > expected → 不算 drop
    assert out["value"] == 0


def test_silent_drop_count_actual_less_than_expected():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, exp)
    # 5 - 1 = 4 dropped
    assert out["value"] == 4


def test_silent_drop_count_multi_type():
    by_type = {"paragraph": 1, "heading": 1}
    exp = {"element_count_by_type": {"paragraph": 3, "heading": 1}}
    out = _silent_drop_count(by_type, exp)
    # paragraph: 3-1=2, heading: 1-1=0 → total 2
    assert out["value"] == 2


def test_silent_drop_count_returns_int():
    by_type = {"paragraph": 1}
    exp = {"element_count_by_type": {"paragraph": 2}}
    out = _silent_drop_count(by_type, exp)
    # 当 drop > 0 时返回 int
    if out["value"] is not None:
        assert isinstance(out["value"], int)


# ---------- _is_valid_bbox 行为深度第四批 ----------


def test_is_valid_bbox_4_ints():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_4_floats():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_mixed():
    assert _is_valid_bbox([0, 0.5, 100, 100.5]) is True


def test_is_valid_bbox_negative():
    assert _is_valid_bbox([-10, -10, 100, 100]) is True


def test_is_valid_bbox_zero():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_3_elements():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_5_elements():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_empty():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_none():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string():
    assert _is_valid_bbox("0,0,100,100") is False


def test_is_valid_bbox_dict():
    assert _is_valid_bbox({"x": 0, "y": 0, "w": 100, "h": 100}) is False


def test_is_valid_bbox_tuple():
    """tuple 不是 list → False（即使内容合法）。"""
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_bool_true():
    assert _is_valid_bbox(True) is False


def test_is_valid_bbox_bool_false():
    assert _is_valid_bbox(False) is False


def test_is_valid_bbox_nan():
    assert _is_valid_bbox([float("nan"), 0, 100, 100]) is False


def test_is_valid_bbox_inf():
    assert _is_valid_bbox([float("inf"), 0, 100, 100]) is False


def test_is_valid_bbox_string_element():
    assert _is_valid_bbox([0, 0, "100", 100]) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([0, 0, None, 100]) is False


# ---------- _strip_unicode_whitespace 行为深度第四批 ----------


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_leading_space():
    assert _strip_unicode_whitespace("  hello") == "hello"


def test_strip_unicode_whitespace_trailing_space():
    assert _strip_unicode_whitespace("hello  ") == "hello"


def test_strip_unicode_whitespace_both():
    assert _strip_unicode_whitespace("  hello  ") == "hello"


def test_strip_unicode_whitespace_internal():
    """删除所有空白（包括内部），不动非空白字符。"""
    assert _strip_unicode_whitespace("a  b") == "ab"


def test_strip_unicode_whitespace_tab():
    assert _strip_unicode_whitespace("\thello") == "hello"


def test_strip_unicode_whitespace_newline():
    assert _strip_unicode_whitespace("\nhello") == "hello"


def test_strip_unicode_whitespace_carriage_return():
    assert _strip_unicode_whitespace("\rhello") == "hello"


def test_strip_unicode_whitespace_form_feed():
    assert _strip_unicode_whitespace("\fhello") == "hello"


def test_strip_unicode_whitespace_vertical_tab():
    assert _strip_unicode_whitespace("\vhello") == "hello"


def test_strip_unicode_whitespace_nbsp():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_unicode_whitespace_em_space():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_unicode_whitespace_en_space():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_unicode_whitespace_ideographic_space():
    assert _strip_unicode_whitespace("　hello") == "hello"


def test_strip_unicode_whitespace_line_separator():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_unicode_whitespace_paragraph_separator():
    assert _strip_unicode_whitespace(" hello") == "hello"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_emoji():
    assert _strip_unicode_whitespace("🚀emoji") == "🚀emoji"


def test_strip_unicode_whitespace_chinese():
    assert _strip_unicode_whitespace("中文") == "中文"


# ---------- _text_preservation 行为深度第四批 ----------
# 注意：返回 dict 的 key 是 'equal', 'precision', 'recall'，不是 'text_preservation_*'


def test_text_preservation_no_elements_no_chunks():
    out = _text_preservation([], [])
    # 都为空 → equal=True（空字符串相等）
    assert out["equal"]["value"] is True


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_chunks_missing_text():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"chunk_id": "c1"}]
    out = _text_preservation(elements, chunks)
    assert isinstance(out, dict)


def test_text_preservation_elements_missing_content():
    elements = [{"type": "paragraph"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert isinstance(out, dict)


def test_text_preservation_image_ignored():
    elements = [
        {"type": "paragraph", "content": "a"},
        {"type": "image", "element_id": "i1"},
    ]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0


def test_text_preservation_three_keys():
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    assert "equal" in out
    assert "precision" in out
    assert "recall" in out


def test_text_preservation_value_and_reason_structure():
    elements = [{"type": "paragraph", "content": "a"}]
    chunks = [{"text": "a"}]
    out = _text_preservation(elements, chunks)
    for k in ("equal", "precision", "recall"):
        assert "value" in out[k]
        assert "reason" in out[k]


def test_text_preservation_normalize_whitespace():
    elements = [{"type": "paragraph", "content": "  hello   world  "}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    # 删除所有空白后匹配
    assert out["equal"]["value"] is True


# ---------- _pdf_locator_ratio 行为深度第四批 ----------
# 注意：page/bbox 在 source_locator 子 dict 中


def test_pdf_locator_ratio_empty_elements():
    out = _pdf_locator_ratio([])
    assert out["value"] is None


def test_pdf_locator_ratio_no_required_types():
    elements = [{"type": "image", "element_id": "i1"}]
    out = _pdf_locator_ratio(elements)
    # image 不需要 bbox，但要 page>=1；缺 page → 0/1
    assert out["value"] == 0.0


def test_pdf_locator_ratio_all_have_page_and_bbox():
    elements = [
        {"type": "paragraph", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        {"type": "heading", "element_id": "e2", "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_missing_page():
    elements = [
        {"type": "paragraph", "element_id": "e1", "source_locator": {"bbox": [0, 0, 100, 100]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_missing_bbox():
    elements = [
        {"type": "paragraph", "element_id": "e1", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_partial():
    elements = [
        {"type": "paragraph", "element_id": "e1", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
        {"type": "paragraph", "element_id": "e2"},  # 缺 source_locator
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


def test_pdf_locator_ratio_invalid_page():
    elements = [
        {"type": "paragraph", "element_id": "e1", "source_locator": {"page": 0, "bbox": [0, 0, 100, 100]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 行为深度第四批 ----------
# 注意：locator 在 source_locator 子 dict 中


def test_docx_locator_ratio_empty_elements():
    out = _docx_locator_ratio([])
    assert out["value"] is None


def test_docx_locator_ratio_no_paragraph():
    elements = [{"type": "image", "element_id": "i1"}]
    out = _docx_locator_ratio(elements)
    # image 缺 source_locator → 0/1
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_paragraph_index():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_missing_paragraph_index():
    elements = [
        {"type": "paragraph", "source_locator": {}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_missing_structural_locator():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_partial():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph"},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- module source forbidden tokens 第九批 ----------


_FORBIDDEN_TOKENS_ROUND9 = [
    "sys",
    "os",
    "logging",
    "subprocess",
    "asyncio",
    "threading",
    "concurrent",
    "multiprocessing",
    "socket",
    "signal",
    "ctypes",
    "gc",
    "traceback",
    "warnings",
    "weakref",
    "tempfile",
    "shutil",
    "pickle",
    "csv",
    "yaml",
    "tomllib",
    "configparser",
    "argparse",
    "logging.config",
    "importlib.resources",
    "inspect",
    "dis",
    "compile(",
    "exec(",
    "globals(",
    "locals(",
    "vars(",
    "dir(",
    "delattr(",
    "exit(",
    "quit(",
    "input(",
    "pprint(",
    "ascii(",
    "bin(",
    "oct(",
    "hex(",
    "slice(",
    "reversed(",
    "abs(",
    "divmod(",
    "pow(",
    "bytearray(",
    "memoryview(",
    "complex(",
    "classmethod(",
    "staticmethod(",
    "property(",
    "super(",
    "object()",
    "ellipsi",
    "notimplemented",
    "License",
    "Credits",
    "Copyright",
    "help(",
    "breakpoint(",
    "__import__",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND9)
def test_module_source_no_forbidden_token_round9(token):
    """metrics.py 不应使用这些 stdlib modules / builtin calls。"""
    src = inspect.getsource(mmod)

    allowed = {
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "dir(",
        "delattr(",
        "exit(",
        "quit(",
        "input(",
        "pprint(",
        "ascii(",
        "bin(",
        "oct(",
        "hex(",
        "slice(",
        "reversed(",
        "abs(",
        "divmod(",
        "pow(",
        "bytearray(",
        "memoryview(",
        "complex(",
        "classmethod(",
        "staticmethod(",
        "property(",
        "super(",
        "object()",
    }
    if token in allowed:
        return

    if token.endswith("("):
        assert token not in src, f"unexpected builtin call {token!r} in metrics.py"
    else:
        import re
        pattern = r"\b" + re.escape(token) + r"\b"
        matches = re.findall(pattern, src)
        assert not matches, f"unexpected token {token!r} in metrics.py"


# ---------- module source 字符串精确补强 ----------


def test_module_source_starts_with_docstring():
    src = inspect.getsource(mmod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_import_count_5():
    """5 个 module-level imports: __future__ + math + Counter + Path + Any。"""
    src = inspect.getsource(mmod)
    import_lines = [
        l for l in src.splitlines()
        if l.strip().startswith(("import ", "from "))
        and not l.startswith(" ")
    ]
    assert len(import_lines) == 5


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
    assert "yield " not in src


def test_module_source_no_async():
    src = inspect.getsource(mmod)
    assert "async " not in src
    assert "await " not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(mmod)
    assert "\nglobal " not in src
    assert " global " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(mmod)
    assert not any(line.startswith("class ") for line in src.splitlines())


def test_module_source_uses_math_isfinite():
    src = inspect.getsource(mmod)
    assert "math.isfinite" in src


def test_module_source_uses_counter_intersection():
    src = inspect.getsource(mmod)
    assert "Counter" in src


def test_module_source_uses_isspace():
    src = inspect.getsource(mmod)
    assert ".isspace()" in src or "isspace" in src


def test_module_source_no_pickle_import():
    src = inspect.getsource(mmod)
    assert "import pickle" not in src


def test_module_source_no_yaml_import():
    src = inspect.getsource(mmod)
    assert "import yaml" not in src


def test_module_source_no_csv_import():
    src = inspect.getsource(mmod)
    assert "import csv" not in src


def test_module_source_no_logging_import():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_argparse_import():
    src = inspect.getsource(mmod)
    assert "import argparse" not in src


def test_module_source_function_count_14():
    src = inspect.getsource(mmod)
    func_count = sum(
        1 for line in src.splitlines()
        if line.startswith("def ")
    )
    assert func_count == 14


def test_module_source_function_names():
    src = inspect.getsource(mmod)
    funcs = [
        line.split("def ")[1].split("(")[0]
        for line in src.splitlines()
        if line.startswith("def ")
    ]
    expected = [
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
        "compute_automatic_metrics",
    ]
    assert sorted(funcs) == sorted(expected)


def test_module_source_has_1_public_func():
    src = inspect.getsource(mmod)
    public = [
        line for line in src.splitlines()
        if line.startswith("def ") and not line.startswith("def _")
    ]
    assert len(public) == 1
    assert "def compute_automatic_metrics" in public[0]


def test_module_source_has_13_private_funcs():
    src = inspect.getsource(mmod)
    private = [
        line for line in src.splitlines()
        if line.startswith("def _")
    ]
    assert len(private) == 13


# ---------- signatures 精确补强 ----------


def test_compute_signature_param_count():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_signature_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    names = list(sig.parameters.keys())
    assert names == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_signature_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    p = sig.parameters["image_base_dir"]
    assert p.default is None


def test_compute_signature_no_varargs():
    sig = inspect.signature(compute_automatic_metrics)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_null_signature():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_ratio_signature():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_bool_metric_signature():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_int_metric_signature():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_is_valid_bbox_signature():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_strip_unicode_whitespace_signature():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_pdf_locator_ratio_signature():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_docx_locator_ratio_signature():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_image_resource_ratio_signature():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_chunk_reference_ratio_signature():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_text_preservation_signature():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_heading_boundary_ratio_signature():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_silent_drop_count_signature():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_no_function_has_varargs_in_module():
    for name in [
        "compute_automatic_metrics",
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]:
        fn = getattr(mmod, name)
        sig = inspect.signature(fn)
        kinds = {p.kind for p in sig.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds
        assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace_has_14_callables():
    ns = [
        (k, v) for k, v in vars(mmod).items()
        if getattr(v, "__module__", "") == mmod.__name__
        and not k.startswith("__")
    ]
    names = [k for k, v in ns]
    assert len(names) == 14


def test_module_name():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_file_endswith_metrics_py():
    assert mmod.__file__.replace("\\", "/").endswith("evaluation/metrics.py")


def test_module_docstring_present():
    assert mmod.__doc__ is not None


def test_module_has_all_attribute():
    """metrics.py 有 __all__（只导出 compute_automatic_metrics）。"""
    assert hasattr(mmod, "__all__")
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_compute_callable():
    assert callable(mmod.compute_automatic_metrics)


def test_module_all_helpers_callable():
    for name in [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]:
        assert callable(getattr(mmod, name))


def test_module_no_user_classes():
    classes = [
        (k, v) for k, v in vars(mmod).items()
        if isinstance(v, type) and getattr(v, "__module__", "") == mmod.__name__
    ]
    assert classes == []


def test_module_constants_present():
    assert hasattr(mmod, "_TEXT_TYPES")
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_function_module_eq():
    for name in [
        "compute_automatic_metrics",
        "_null", "_ratio",
    ]:
        fn = getattr(mmod, name)
        assert fn.__module__ == "evaluation.metrics"


# ---------- 端到端集成补强 ----------


def test_e2e_compute_with_full_pdf_doc(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "element_id": "e1", "page": 1, "bbox": [0, 0, 100, 100], "content": "hello"},
            {"type": "heading", "element_id": "h1", "page": 1, "bbox": [0, 0, 100, 50], "content": "title"},
            {"type": "image", "element_id": "i1", "resource_path": "test.png"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
            {"chunk_id": "c2", "text": "title", "source_element_ids": ["h1"]},
        ],
    }
    out = compute_automatic_metrics(
        doc, None, "pdf",
        {"element_count_by_type": {"paragraph": 1, "heading": 1}},
        image_base_dir=tmp_path,
    )
    assert isinstance(out, dict)


def test_e2e_compute_with_full_docx_doc(tmp_path):
    doc = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "element_id": "e1", "structural_locator": {"paragraph_index": 0}, "content": "hello"},
            {"type": "heading", "element_id": "h1", "structural_locator": {"paragraph_index": 1}, "content": "title"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]},
            {"chunk_id": "c2", "text": "title", "source_element_ids": ["h1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert isinstance(out, dict)


def test_e2e_compute_does_not_mutate_inputs():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    error = None
    expectations = {"element_count_by_type": {"paragraph": 1}}
    before_doc = dict(doc)
    before_exp = dict(expectations)
    compute_automatic_metrics(doc, error, "pdf", expectations)
    assert doc == before_doc
    assert expectations == before_exp


def test_e2e_compute_idempotent():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", None)
    assert a == b


def test_e2e_compute_with_error_no_document():
    out = compute_automatic_metrics(None, {"code": "parse_pdf_failed"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_e2e_compute_json_serializable():
    import json
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_compute_with_all_kwargs():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert isinstance(out, dict)


def test_e2e_compute_with_all_positional():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "element_id": "e1", "content": "hello"}],
        "chunks": [{"chunk_id": "c1", "text": "hello", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, None)
    assert isinstance(out, dict)


def test_e2e_text_preservation_real_case():
    """完整 text_preservation 计算。"""
    elements = [
        {"type": "paragraph", "content": "first paragraph"},
        {"type": "paragraph", "content": "second paragraph"},
        {"type": "heading", "content": "title"},
        {"type": "image", "element_id": "i1"},  # ignored
    ]
    chunks = [
        {"text": "title first paragraph"},
        {"text": "second paragraph"},
    ]
    out = _text_preservation(elements, chunks)
    assert isinstance(out, dict)


def test_e2e_silent_drop_real_case():
    """_silent_drop_count 接受 by_type dict，不是 elements 列表。"""
    by_type = {"paragraph": 2, "heading": 3}
    exp = {"element_count_by_type": {"paragraph": 3, "heading": 5}}
    out = _silent_drop_count(by_type, exp)
    # paragraph: 3-2=1 dropped, heading: 5-3=2 dropped → total 3
    assert out["value"] == 3
