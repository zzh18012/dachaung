"""evaluation/metrics.py 第二十八轮 edges 测试（Round 328）。

重点补强 edges26 未触及的角度：
- compute_automatic_metrics 边界组合补强
- _text_preservation 数学精确（Counter 多集合语义深度）
- _pdf_locator_ratio 边界组合补强
- _docx_locator_ratio 边界组合补强
- _image_resource_ratio 边界组合补强
- _chunk_reference_ratio 边界组合补强
- _heading_boundary_ratio 边界组合补强
- _silent_drop_count 边界组合补强
- module source 字符串精确补强（math/Counter source level）
- module source forbidden tokens 第三批
- signatures 精确补强（return annotations）
- 端到端集成补强
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import math
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest

import evaluation.metrics as m
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


# ---------- compute_automatic_metrics 边界组合补强 ----------


def test_compute_metrics_with_image_in_elements_and_chunks():
    """image 不参与 text_preservation（仅文本类型参与）。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1"},
            {"type": "paragraph", "element_id": "p1", "content": "abc"},
        ],
        "chunks": [{"text": "abc"}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # image 没有 resource_path → image_resource_exists_ratio null no_image... wait
    # 实际：image elements 存在但没 resource_path → valid=0, ratio=0.0
    assert out["image_resource_exists_ratio"]["value"] == 0.0
    # text_preservation: expected = "abc" (only non-image), actual = "abc" → equal True
    assert out["text_preservation_equal"]["value"] is True


def test_compute_metrics_pipeline_success_with_error_dict_only():
    """document=None + error={} → pipeline_success=False（error falsy 但 document None）。"""
    out = compute_automatic_metrics(None, {}, "pdf", None)
    # pipeline_success = error is None and document is not None
    # error = {} is falsy but not None → still pipeline_success False
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_pipeline_success_truthy_error():
    out = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_metrics_no_schema_validation_inside_metrics():
    """compute_automatic_metrics 不做 schema 校验（schema_valid 在 runner 计算）；
    若 elements 不是 list of dict 会抛 AttributeError（异常由上游处理）。"""
    with pytest.raises(AttributeError):
        compute_automatic_metrics({"elements": "not list"}, None, "pdf", None)


def test_compute_metrics_output_includes_schema_valid():
    """schema_valid 在 compute_automatic_metrics 的输出 metrics 中（由 schema_validation 计算）。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "schema_valid" in out
    assert out["schema_valid"]["value"] in (True, False)
    assert out["schema_valid"]["reason"] is None or \
           isinstance(out["schema_valid"]["reason"], str)


def test_compute_metrics_returns_consistent_metrics_for_same_input():
    """相同输入两次调用 → 结果一致。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_compute_metrics_does_not_mutate_input():
    """compute_automatic_metrics 不修改输入 dict。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x"}],
    }
    import json as _json
    doc_copy = _json.loads(_json.dumps(doc))
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == doc_copy


def test_compute_metrics_with_unknown_source_type_text_preservation():
    """source_type 任意值都不影响 text_preservation 计算。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc"}],
    }
    out = compute_automatic_metrics(doc, None, "weird_type", None)
    assert out["text_preservation_equal"]["value"] is True


# ---------- _text_preservation 数学精确（Counter 多集合语义深度） ----------


def test_text_preservation_common_minus_actual():
    """common = Σ min(count) → common <= min(|expected|, |actual|)。"""
    # expected = "aabb" (a:2, b:2), actual = "ab" (a:1, b:1)
    # common = min(2,1)+min(2,1) = 2
    # precision = 2 / 2 = 1, recall = 2 / 4 = 0.5
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5


def test_text_preservation_actual_subset_of_expected():
    """actual 是 expected 的字符子集。"""
    # expected = "hello worlds", actual = "world"
    # expected stripped = "helloworlds" → 11 chars
    # common = w+o+r+l+d = 5
    # precision = 5/5 = 1, recall = 5/11 ≈ 0.4545
    elements = [{"type": "paragraph", "content": "hello worlds"}]
    chunks = [{"text": "world"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 5/11) < 1e-9


def test_text_preservation_disjoint_chars():
    """expected 和 actual 完全不重叠。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "xyz"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] == 0.0
    # equal 也是 False
    assert out["equal"]["value"] is False


def test_text_preservation_actual_superset():
    """actual 包含 expected 全部 + 多余。"""
    # expected = "ab", actual = "abcd"
    # common = 2, precision = 2/4, recall = 2/2 = 1
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abcd"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 1.0


def test_text_preservation_with_image_in_elements_excluded():
    """image 不参与 expected sequence。"""
    elements = [
        {"type": "image", "content": "this_should_be_excluded"},
        {"type": "paragraph", "content": "abc"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_with_chunk_text_int_zero():
    """chunk text 是 int 0 → falsy → ""。"""
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": 0}]
    out = _text_preservation(elements, chunks)
    # expected = "", actual = "" → equal True
    assert out["equal"]["value"] is True


def test_text_preservation_counter_takes_min_correctly_with_3_repeats():
    """3 个相同字符。"""
    # expected = "aaa", actual = "aa"
    # common = min(3, 2) = 2
    # precision = 2/2 = 1, recall = 2/3
    elements = [{"type": "paragraph", "content": "aaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2/3) < 1e-9


def test_text_preservation_with_whitespace_only_in_elements_and_chunks():
    """都是空白 → strip 后都 "" → equal True + null empty_expected_and_actual。"""
    elements = [{"type": "paragraph", "content": "   \n\t  "}]
    chunks = [{"text": "  \n  "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


# ---------- _pdf_locator_ratio 边界组合补强 ----------


def test_pdf_locator_with_all_invalid_pages():
    elements = [
        {"type": "table", "source_locator": {"page": 0}},
        {"type": "table", "source_locator": {"page": -1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_with_mixed_types_some_required_bbox():
    """混合 types：paragraph 需要 bbox，table 不需要。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
        {"type": "table", "source_locator": {"page": 1}},  # valid
        {"type": "table", "source_locator": {"page": 0}},  # invalid (page<1)
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5  # 2 valid / 4 total


def test_pdf_locator_with_bbox_invalid_for_paragraph():
    """paragraph + bbox 缺一元素 → invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, "x"]}},  # str
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_with_no_locator_field():
    elements = [{"type": "table"}, {"type": "table"}]  # no source_locator
    out = _pdf_locator_ratio(elements)
    # loc = e.get("source_locator") or {} = {}
    # page = None → invalid
    assert out["value"] == 0.0


def test_pdf_locator_page_is_float():
    """page 是 float（不是 int）→ invalid。"""
    elements = [{"type": "table", "source_locator": {"page": 1.0}}]
    out = _pdf_locator_ratio(elements)
    # isinstance(1.0, int) is False
    assert out["value"] == 0.0


def test_pdf_locator_page_is_string():
    """page 是 string '1' → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_returns_ratio_with_correct_value_type():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert isinstance(out["value"], float)


# ---------- _docx_locator_ratio 边界组合补强 ----------


def test_docx_locator_with_no_locator_field():
    elements = [{"type": "paragraph"}, {"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_multiple_structural_keys_in_one_element():
    """一个 element 含多个 structural_keys → valid。"""
    elements = [
        {"type": "paragraph", "source_locator": {
            "section": 1, "paragraph_index": 0, "run_index": 0,
        }},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_page_and_structural_key_still_invalid():
    """locator 含 page → 即使有 structural_key 也 invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {
            "page": 1, "paragraph_index": 0,
        }},
    ]
    out = _docx_locator_ratio(elements)
    # 代码：if "page" in loc or "bbox" in loc: continue → invalid
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_and_structural_key_still_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {
            "bbox": [0, 0, 1, 1], "paragraph_index": 0,
        }},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_unknown_keys_only():
    """locator 仅含非 structural_key → invalid。"""
    elements = [
        {"type": "paragraph", "source_locator": {"unknown_key": 0}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _image_resource_ratio 边界组合补强 ----------


def test_image_resource_with_none_image_base_dir(tmp_path):
    """image_base_dir=None → 仅用 resource_path 原值。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_with_absolute_path_no_image_base_dir(tmp_path):
    img = tmp_path / "abs.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_with_relative_path_and_image_base_dir(tmp_path):
    """resource_path 是相对路径 + image_base_dir → 拼接 Path(rp).name 找。"""
    img = tmp_path / "rel.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "rel.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    # candidates: [Path("rel.png"), tmp_path / "rel.png"]
    # 第二个存在 → valid
    assert out["value"] == 1.0


def test_image_resource_with_zero_size_file(tmp_path):
    """文件存在但 size=0 → invalid。"""
    img = tmp_path / "zero.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_resource_with_nonexistent_relative_no_base_dir():
    """resource_path 是相对路径但 image_base_dir=None → 仅用相对路径。"""
    elements = [{"type": "image", "resource_path": "nonexistent.png"}]
    out = _image_resource_ratio(elements, None)
    # Path("nonexistent.png").is_file() 在 cwd 找 → 通常不存在
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 边界组合补强 ----------


def test_chunk_reference_with_chunk_referencing_unknown_id():
    """chunk source_element_ids 含 element 中没有的 id → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_with_chunk_referencing_only_known_ids():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]  # 都在
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_with_chunks_referencing_same_id():
    """两个 chunk 都引用同一 id → 都 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e1"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_with_element_id_none():
    """element 缺 element_id → set 含 None。"""
    elements = [{"type": "paragraph"}]  # no element_id
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # elem_ids = {None}, sid=None in {None} → True → valid
    assert out["value"] == 1.0


def test_chunk_reference_with_chunk_no_source_element_ids_key():
    """chunk 缺 source_element_ids 字段。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "abc"}]  # no source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    # ids = c.get("source_element_ids") or [] = []
    # if ids and ... → falsy → not valid
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 边界组合补强 ----------


def test_heading_boundary_with_chunk_referencing_non_heading_id_at_first():
    """chunk first id 是 paragraph 而非 heading → 仍按 id 匹配。"""
    # 实际算法不检查 source_element 的 type，只检查 chunk 第一个 id 是否匹配 heading element_id
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "paragraph", "element_id": "p1"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # first id = h1，匹配
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_with_chunk_first_id_not_in_headings():
    """chunk first id 不是任何 heading 的 id → not match。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["p1"]}]  # first id = p1，不是 heading id
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_with_chunk_referencing_heading_at_position_2():
    """heading id 在 chunk 第 2 个位置 → 不算 match（只看 first）。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 在第 2 位
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_with_multiple_chunks_each_first_heading():
    """多 chunk 每个 first 都是不同 heading → 全部 match。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
        {"source_element_ids": ["h3"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_with_chunks_first_id_empty_string():
    """chunk first id 是空字符串 → 仍按 id 匹配（空字符串也是 string）。"""
    elements = [{"type": "heading", "element_id": ""}]
    chunks = [{"source_element_ids": [""]}]
    out = _heading_boundary_ratio(elements, chunks)
    # heading_id = "" in chunk_first_ids = {""} → True → match
    assert out["value"] == 1.0


# ---------- _silent_drop_count 边界组合补强 ----------


def test_silent_drop_with_many_types_some_drops():
    by_type = {"a": 1, "b": 5, "c": 0}
    exp = {"element_count_by_type": {"a": 5, "b": 5, "c": 0, "d": 3}}
    # a: drop 4, b: drop 0, c: drop 0, d: drop 3 (not in actual)
    # total = 4 + 3 = 7
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 7


def test_silent_drop_with_zero_expected_value():
    """expected type 值为 0 → 不算 drop（即使 actual 也 0）。"""
    by_type = {"x": 0}
    exp = {"element_count_by_type": {"x": 0}}
    out = _silent_drop_count(by_type, exp)
    # actual(0) < exp(0)? No → no drop
    assert out["value"] == 0


def test_silent_drop_with_negative_actual_increases_drop():
    """actual 负数（不可能但理论上）→ max(0, exp - actual) 增加 drop。"""
    by_type = {"x": -5}  # 不可能但测试
    exp = {"element_count_by_type": {"x": 0}}
    out = _silent_drop_count(by_type, exp)
    # max(0, 0 - (-5)) = max(0, 5) = 5
    assert out["value"] == 5


def test_silent_drop_with_expected_count_zero_for_some_types():
    by_type = {"x": 5, "y": 3}
    exp = {"element_count_by_type": {"x": 5, "y": 0}}  # y 期望 0
    out = _silent_drop_count(by_type, exp)
    # x: 5 not < 5 → no drop
    # y: 3 not < 0 → no drop
    assert out["value"] == 0


# ---------- _strip_unicode_whitespace 数学边界 ----------


def test_strip_unicode_whitespace_with_only_unicode_spaces():
    """各种 Unicode 空白字符全 stripped。"""
    assert _strip_unicode_whitespace("    ") == ""
    assert _strip_unicode_whitespace("    ") == ""
    assert _strip_unicode_whitespace("　") == ""


def test_strip_unicode_whitespace_preserves_emoji():
    assert _strip_unicode_whitespace("😀😁😂") == "😀😁😂"


def test_strip_unicode_whitespace_preserves_chinese_punctuation():
    """中文标点（，。、）不是空白 → 保留。"""
    assert _strip_unicode_whitespace("你好，世界。") == "你好，世界。"


def test_strip_unicode_whitespace_preserves_digits():
    assert _strip_unicode_whitespace("12345") == "12345"


def test_strip_unicode_whitespace_preserves_letters():
    assert _strip_unicode_whitespace("abcXYZ") == "abcXYZ"


def test_strip_unicode_whitespace_long_string():
    """长字符串保留所有非空白。"""
    s = "a" * 1000 + " " * 100 + "b" * 1000
    assert _strip_unicode_whitespace(s) == "a" * 1000 + "b" * 1000


def test_strip_unicode_whitespace_empty_string():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_single_char():
    assert _strip_unicode_whitespace("x") == "x"


# ---------- _is_valid_bbox 数学边界补强 ----------


def test_is_valid_bbox_with_inf():
    """inf 不是 finite → False。"""
    assert _is_valid_bbox([0, 0, math.inf, 1]) is False


def test_is_valid_bbox_with_nan():
    """nan 不是 finite → False。"""
    assert _is_valid_bbox([0, 0, math.nan, 1]) is False


def test_is_valid_bbox_with_negative_inf():
    assert _is_valid_bbox([0, 0, -math.inf, 1]) is False


def test_is_valid_bbox_with_4_valid_negatives():
    """4 个负数也 valid（finite）。"""
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_with_4_zeros():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_with_4_floats():
    assert _is_valid_bbox([0.5, 1.5, 2.5, 3.5]) is True


def test_is_valid_bbox_with_4_huge_floats():
    assert _is_valid_bbox([1e308, 1e308, 1e308, 1e308]) is True


def test_is_valid_bbox_with_3_elements():
    assert _is_valid_bbox([0, 0, 1]) is False


def test_is_valid_bbox_with_5_elements():
    assert _is_valid_bbox([0, 0, 1, 1, 1]) is False


# ---------- _ratio 数学边界补强 ----------


def test_ratio_with_very_small_negative():
    r = _ratio(-1e-300)
    assert r["value"] == -1e-300


def test_ratio_with_negative_zero():
    r = _ratio(-0.0)
    # -0.0 转 float 仍是 -0.0
    assert math.copysign(1.0, r["value"]) == -1.0


def test_ratio_with_int_input():
    """int 输入被 float() 转。"""
    r = _ratio(1)  # int
    assert r["value"] == 1.0
    assert isinstance(r["value"], float)


def test_ratio_with_bool_input():
    """bool 是 int 子类，float(True) = 1.0。"""
    r = _ratio(True)
    assert r["value"] == 1.0


def test_ratio_dict_always_2_keys():
    r = _ratio(0.5)
    assert set(r.keys()) == {"value", "reason"}


# ---------- _null 行为深度补强 ----------


def test_null_returns_dict_with_2_keys():
    r = _null("x")
    assert set(r.keys()) == {"value", "reason"}


def test_null_value_is_none_type():
    r = _null("x")
    assert r["value"] is None


def test_null_reason_string_type():
    r = _null("hello")
    assert isinstance(r["reason"], str)


# ---------- _bool_metric 数学补强 ----------


def test_bool_metric_with_int_zero():
    r = _bool_metric(0)
    assert r["value"] is False


def test_bool_metric_with_int_one():
    r = _bool_metric(1)
    assert r["value"] is True


def test_bool_metric_with_string_truthy():
    """非空字符串 truthy。"""
    r = _bool_metric("x")
    assert r["value"] is True


def test_bool_metric_with_string_falsy():
    r = _bool_metric("")
    assert r["value"] is False


def test_bool_metric_with_negative_int():
    r = _bool_metric(-1)
    assert r["value"] is True  # -1 is truthy


def test_bool_metric_value_is_bool_not_int():
    """bool 是 int 子类，但 bool() 强制转换。"""
    r = _bool_metric(1)
    assert isinstance(r["value"], bool)
    # type() 严格是 bool
    assert type(r["value"]) is bool


# ---------- _int_metric 数学补强 ----------


def test_int_metric_with_zero():
    r = _int_metric(0)
    assert r["value"] == 0


def test_int_metric_with_negative():
    r = _int_metric(-5)
    assert r["value"] == -5


def test_int_metric_with_huge_int():
    r = _int_metric(10**18)
    assert r["value"] == 10**18


def test_int_metric_with_bool_true():
    r = _int_metric(True)
    assert r["value"] == 1


def test_int_metric_value_is_int_type():
    r = _int_metric(5)
    assert type(r["value"]) is int


# ---------- module source 字符串精确补强（math/Counter source level） ----------


def test_module_source_has_import_math():
    src = inspect.getsource(m)
    assert "import math" in src


def test_module_source_has_from_collections_import_counter():
    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_has_math_isfinite_in_is_valid_bbox():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite(v)" in src


def test_module_source_has_counter_intersection_in_text_preservation():
    src = inspect.getsource(_text_preservation)
    assert "c_expected & c_actual" in src


def test_module_source_has_sum_for_common():
    src = inspect.getsource(_text_preservation)
    assert "common = sum((c_expected & c_actual).values())" in src


def test_module_source_has_sum_for_actual():
    src = inspect.getsource(_text_preservation)
    assert "if sum(c_actual.values()) == 0:" in src


def test_module_source_has_sum_for_expected():
    src = inspect.getsource(_text_preservation)
    assert "if sum(c_expected.values()) == 0:" in src


def test_module_source_has_f1_calc_pattern():
    src = inspect.getsource(_text_preservation)
    # _text_preservation 不算 f1，但 _ratio 用于 precision/recall
    # 这个断言验证 source 用 _ratio
    assert "_ratio(common" in src


def test_module_source_pdf_locator_uses_isinstance():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src


def test_module_source_docx_locator_uses_any_for_structural_keys():
    src = inspect.getsource(_docx_locator_ratio)
    assert "any(k in loc for k in structural_keys)" in src


def test_module_source_image_resource_uses_is_file_and_stat():
    src = inspect.getsource(_image_resource_ratio)
    assert "p.is_file()" in src
    assert "p.stat().st_size" in src


def test_module_source_chunk_reference_uses_set_comprehension():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "{e.get(\"element_id\") for e in elements}" in src


def test_module_source_heading_boundary_uses_add_to_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids.add(ids[0])" in src


def test_module_source_silent_drop_uses_items_iteration():
    src = inspect.getsource(_silent_drop_count)
    assert "for t, exp in expected_counts.items():" in src


# ---------- module source forbidden tokens 第三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import base64",
        "import binascii",
        "import bisect",
        "import calendar",
        "import concurrent",
        "import contextlib",
        "import copyreg",
        "import cProfile",
        "import ctypes",
        "import fnmatch",
        "import functools",
        "import getopt",
        "import getpass",
        "import gettext",
        "import heapq",
        "import imaplib",
        "import imap",
        "import imghdr",
        "import imp",
        "import importlib",
        "import ipaddress",
        "import locale",
        "import logging",
        "import lzma",
        "import mailbox",
        "import mimetypes",
        "import mmap",
        "import multiprocessing",
        "import netrc",
        "import ntpath",
        "import numbers",
        "import operator",
        "import optparse",
        "import pathlib",
        "import platform",
        "import poplib",
        "import posixpath",
        "import profile",
        "import pstats",
        "import py_compile",
        "import quopri",
        "import reprlib",
        "import runpy",
        "import sched",
        "import select",
        "import shelve",
        "import shlex",
        "import signal",
        "import site",
        "import smtplib",
        "import sndhdr",
        "import socketserver",
        "import sqlite3",
        "import ssl",
        "import subprocess",
        "import sunau",
        "import symtable",
        "import tabnanny",
        "import telnetlib",
        "import termios",
        "import timeit",
        "import tkinter",
        "import token",
        "import tokenize",
        "import trace",
        "import tty",
        "import turtle",
        "import typing",
        "import unittest",
        "import urllib",
        "import uu",
        "import webbrowser",
        "import xdrlib",
        "import zipapp",
        "import zipfile",
        "import zipimport",
    ],
)
def test_module_source_forbidden_tokens_third_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- signatures 精确补强（return annotations） ----------


def test_compute_automatic_metrics_return_annotation():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.return_annotation == "dict[str, Any]"


def test_pdf_locator_ratio_return_annotation():
    sig = inspect.signature(_pdf_locator_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_docx_locator_ratio_return_annotation():
    sig = inspect.signature(_docx_locator_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_image_resource_ratio_return_annotation():
    sig = inspect.signature(_image_resource_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_chunk_reference_ratio_return_annotation():
    sig = inspect.signature(_chunk_reference_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_text_preservation_return_annotation():
    sig = inspect.signature(_text_preservation)
    assert sig.return_annotation == "dict[str, Any]"


def test_heading_boundary_ratio_return_annotation():
    sig = inspect.signature(_heading_boundary_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_silent_drop_count_return_annotation():
    sig = inspect.signature(_silent_drop_count)
    assert sig.return_annotation == "dict[str, Any]"


def test_strip_unicode_whitespace_return_annotation():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.return_annotation == "str"


def test_is_valid_bbox_return_annotation():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_null_return_annotation():
    sig = inspect.signature(_null)
    assert sig.return_annotation == "dict[str, Any]"


def test_ratio_return_annotation():
    sig = inspect.signature(_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_bool_metric_return_annotation():
    sig = inspect.signature(_bool_metric)
    assert sig.return_annotation == "dict[str, Any]"


def test_int_metric_return_annotation():
    sig = inspect.signature(_int_metric)
    assert sig.return_annotation == "dict[str, Any]"


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert m.__name__ == "evaluation.metrics"


def test_module_all_only_compute_automatic_metrics():
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_has_1_public_function():
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.metrics"
    ]
    assert public == ["compute_automatic_metrics"]


def test_module_has_13_private_functions():
    private = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert len(private) == 13


def test_module_has_3_private_constants():
    consts = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and not callable(getattr(m, n))
    ]
    assert set(consts) == {
        "_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED",
    }


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


def test_module_no_decorators():
    src = inspect.getsource(m)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            pytest.fail(f"Found decorator: {stripped}")


# ---------- 端到端集成补强 ----------


def test_e2e_complete_pdf_pipeline():
    """完整 PDF pipeline：text + image + heading。"""
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "element_id": "p1", "content": "body",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
            {"type": "image", "element_id": "i1", "resource_path": "x.png"},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "body", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    # i1 没 source_locator → invalid → 2/3 ≈ 0.667
    assert abs(out["pdf_locator_valid_ratio"]["value"] - 2/3) < 1e-9
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_complete_docx_pipeline():
    """完整 DOCX pipeline。"""
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "body",
             "source_locator": {"paragraph_index": 1}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "body", "source_element_ids": ["p1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_pipeline_failed_returns_correct_metrics():
    """document=None → 11 metrics null pipeline_failed。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    null_keys = [
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ]
    for k in null_keys:
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_with_expectations_full_match():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "heading"},
            {"type": "table"},
        ],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"paragraph": 1, "heading": 1, "table": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_with_expectations_no_drop_with_image_in_actual():
    """image 在 by_type 计入。"""
    doc = {
        "elements": [
            {"type": "image"},
            {"type": "paragraph"},
        ],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"image": 1, "paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_with_unicode_content():
    """含中文 content 的完整 pipeline。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "你好世界",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "你好世界", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["value"] == 1.0
    assert out["text_char_multiset_recall"]["value"] == 1.0


def test_e2e_with_empty_content_chunks():
    """chunks 全空 content。"""
    doc = {
        "elements": [{"type": "paragraph", "content": ""}],
        "chunks": [{"text": ""}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # expected = "", actual = "" → equal True
    assert out["text_preservation_equal"]["value"] is True
    # precision/recall null empty_expected_and_actual
    assert out["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"


def test_e2e_consistent_results_across_runs():
    """两次调用结果一致。"""
    doc = {
        "elements": [{"type": "paragraph", "element_id": "p1", "content": "x"}],
        "chunks": [{"text": "x", "source_element_ids": ["p1"]}],
    }
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2
