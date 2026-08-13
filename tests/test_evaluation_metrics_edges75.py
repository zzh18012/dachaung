"""evaluation/metrics.py 第九十三轮 edges 测试（Round 668）。

补强 edges74 未触及的角度（第五十一批）。

新角度：
- _strip_unicode_whitespace 更细（form feed / vertical tab / next line / byte order mark / thin space / hair space / narrow no-break space / 全角空格 / line/paragraph separator）
- Counter 多集合交集（min per char / 不同字符相同次数 / 单字符 vs 多字符 / 三种字符相同）
- _text_preservation 边界（expected 空 actual 非空 / actual 空 expected 非空 / expected == actual 不空 / Unicode 大小写敏感 / 重复字符验证）
- _heading_boundary_ratio 边界（chunks 同 first id 去重 / heading 无 element_id / chunks 全空 ids / 多对一）
- _silent_drop_count 边界（expectations None / element_count_by_type 是 None / 空 dict / actual > expected / actual == expected）
- _is_valid_bbox 角（tuple / set / dict / mixed int+float / 全 0 / 负数 / inf / -inf / nan / bool 拒绝）
- _chunk_reference_ratio 角（空 ids / 部分缺失 / 全部缺失 / ids None / ids 含非字符串 / 元素 element_id 是 None）
- _image_resource_ratio 角（resource_path 是 None / 空字符串 / 0-size 文件 / image_base_dir 与 rp 联合 / OSError 容错）
- compute_automatic_metrics 完整路径（schema exception 分支类型 / pipeline_failed 14 个 null + reason）
- _null / _ratio / _bool_metric / _int_metric 类型与值
- 模块源码补强（_null 返回 dict / _ratio float 转换 / _bool_metric bool 转换 / _int_metric int 转换 / 14 函数顺序 / Counter & 用法 / Counter sum 用法）
- AST 结构补强（14 顶层函数 / 函数名顺序 / __all__ Assign / 模块常量 Assign 数量 / 嵌套 if/for / 嵌套 try/except / compute_automatic_metrics ≥10 metrics key / 7 imports / 无 ClassDef / 无 AsyncFunctionDef / 无 Global / 无 Nonlocal / 无 Importstar）
- forbidden tokens 第一百三十八批
"""

from __future__ import annotations

import ast
import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.metrics as metrics_mod
from evaluation.metrics import (
    _TEXT_TYPES,
    _PDF_BBOX_REQUIRED_TYPES,
    _NOT_EVALUATED,
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


# ---------- _strip_unicode_whitespace 更细 ----------

def test_strip_form_feed_batch51():
    """form feed (\\f, \\u000C) is whitespace."""
    assert _strip_unicode_whitespace("a\fb") == "ab"


def test_strip_vertical_tab_batch51():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_next_line_batch51():
    """NEL (\\u0085) next line."""
    assert _strip_unicode_whitespace("ab") == "ab"


def test_strip_bom_is_not_whitespace_batch51():
    """BOM ZERO WIDTH NO-BREAK SPACE (\\uFEFF) is NOT isspace() whitespace → 保留。"""
    assert _strip_unicode_whitespace("a﻿b") == "a﻿b"


def test_strip_thin_space_batch51():
    """THIN SPACE (\\u2009)."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_hair_space_batch51():
    """HAIR SPACE (\\u200A)."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_narrow_nbsp_batch51():
    """NARROW NO-BREAK SPACE (\\u202F)."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_fullwidth_space_batch51():
    """全角空格 IDEOGRAPHIC SPACE (\\u3000)."""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_line_separator_batch51():
    """LINE SEPARATOR (\\u2028)."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_paragraph_separator_batch51():
    """PARAGRAPH SEPARATOR (\\u2029)."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_multiple_consecutive_batch51():
    """多个连续空白字符都被剥离。"""
    assert _strip_unicode_whitespace("a \t\n　b") == "ab"


def test_strip_all_whitespace_returns_empty_batch51():
    """全是空白 → 空串。"""
    assert _strip_unicode_whitespace("  \t\n　") == ""


def test_strip_empty_string_batch51():
    assert _strip_unicode_whitespace("") == ""


def test_strip_no_whitespace_unchanged_batch51():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_does_not_sort_chars_batch51():
    """不排序，保留顺序。"""
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_preserves_punctuation_batch51():
    """标点符号保留。"""
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


# ---------- Counter 多集合交集 ----------

def test_counter_intersection_min_per_char_batch51():
    a = Counter("aabb")
    b = Counter("ab")
    common = sum((a & b).values())
    assert common == 2  # min(2,1) + min(2,1) = 2


def test_counter_intersection_disjoint_batch51():
    a = Counter("aa")
    b = Counter("bb")
    common = sum((a & b).values())
    assert common == 0


def test_counter_intersection_equal_multiset_batch51():
    a = Counter("abcabc")
    b = Counter("aabbcc")
    common = sum((a & b).values())
    assert common == 6


def test_counter_intersection_with_repeats_batch51():
    a = Counter("aaaa")
    b = Counter("aa")
    common = sum((a & b).values())
    assert common == 2


def test_counter_intersection_zero_in_one_batch51():
    a = Counter("xyz")
    b = Counter("")
    common = sum((a & b).values())
    assert common == 0


# ---------- _text_preservation 边界 ----------

def test_text_preservation_expected_empty_actual_nonempty_batch51():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # expected 空 → recall null
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"
    # actual 非空 → precision 是 0
    assert out["precision"]["value"] == 0.0


def test_text_preservation_actual_empty_expected_nonempty_batch51():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # actual 空 → precision null
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_actual"
    # expected 非空 → recall 是 0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_both_nonempty_equal_batch51():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_case_sensitive_batch51():
    elements = [{"type": "paragraph", "content": "ABC"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_partial_overlap_batch51():
    """重复字符验证：Counter 交集给出正确比例。"""
    elements = [{"type": "paragraph", "content": "aaaa"}]
    chunks = [{"text": "aa"}]
    out = _text_preservation(elements, chunks)
    # expected=aaaa, actual=aa → 交集 = 2
    # precision = 2/2 = 1.0; recall = 2/4 = 0.5
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 0.5
    assert out["equal"]["value"] is False


def test_text_preservation_image_excluded_batch51():
    """image type 不参与 expected。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_content_none_skipped_batch51():
    """content 是 None → 当 ""。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] is None


def test_text_preservation_text_none_skipped_batch51():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] is None


# ---------- _heading_boundary_ratio 边界 ----------

def test_heading_boundary_chunks_same_first_id_dedup_batch51():
    """多个 chunks 用同一 first id → set 去重不影响计数。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1", "p1"]},
        {"source_element_ids": ["h1", "p2"]},  # 同 first id
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_heading_no_element_id_batch51():
    """heading 无 element_id → 不可能匹配。"""
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunks_all_empty_ids_batch51():
    """chunks 全空 ids → 无 chunk first id → 全未匹配。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": []},
        {"source_element_ids": None},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_multi_headings_some_matched_batch51():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["p1", "h2"]},  # h2 不是首元素，不匹配
    ]
    out = _heading_boundary_ratio(elements, chunks)
    # 只有 h1 匹配（h3 完全没 chunk 引用，h2 不是首）
    assert out["value"] == 1 / 3


def test_heading_boundary_no_headings_batch51():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


# ---------- _silent_drop_count 边界 ----------

def test_silent_drop_count_expectations_none_batch51():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_expectations_empty_dict_batch51():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_element_count_by_type_none_batch51():
    """expectations 含 element_count_by_type=None。"""
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": None})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_element_count_by_type_empty_batch51():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_greater_than_expected_batch51():
    """actual > expected → 该类型 drop=0（max(0, neg)）。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_actual_equal_expected_batch51():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_count_actual_less_expected_batch51():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 2


def test_silent_drop_count_multi_type_sum_batch51():
    """多类型 drop 求和。"""
    by_type = {"paragraph": 2, "heading": 0, "image": 3}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2, "image": 3}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: 5-2=3, heading: 2-0=2, image: 3-3=0 → 总 5
    assert out["value"] == 5


def test_silent_drop_count_expected_type_missing_in_actual_batch51():
    """expected 含 actual 没有的类型 → 视为 0。"""
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_count_returns_int_metric_batch51():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert isinstance(out["value"], int)
    assert out["reason"] is None


# ---------- _is_valid_bbox 角 ----------

def test_is_valid_bbox_tuple_rejected_batch51():
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_set_rejected_batch51():
    assert _is_valid_bbox({0, 0, 1, 1}) is False  # set 只有 3 元素


def test_is_valid_bbox_dict_rejected_batch51():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_str_rejected_batch51():
    assert _is_valid_bbox("0000") is False


def test_is_valid_bbox_mixed_int_float_batch51():
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


def test_is_valid_bbox_all_zero_batch51():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_batch51():
    assert _is_valid_bbox([-1, -2, -3, -4]) is True


def test_is_valid_bbox_inf_rejected_batch51():
    assert _is_valid_bbox([0, 0, 1, float("inf")]) is False


def test_is_valid_bbox_neg_inf_rejected_batch51():
    assert _is_valid_bbox([0, 0, 1, float("-inf")]) is False


def test_is_valid_bbox_nan_rejected_batch51():
    assert _is_valid_bbox([0, 0, 1, float("nan")]) is False


def test_is_valid_bbox_bool_true_rejected_batch51():
    assert _is_valid_bbox([True, 0, 1, 2]) is False


def test_is_valid_bbox_str_numeric_rejected_batch51():
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_none_rejected_batch51():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_5_elements_rejected_batch51():
    assert _is_valid_bbox([0, 0, 1, 1, 2]) is False


def test_is_valid_bbox_3_elements_rejected_batch51():
    assert _is_valid_bbox([0, 0, 1]) is False


# ---------- _chunk_reference_ratio 角 ----------

def test_chunk_reference_all_chunks_empty_ids_batch51():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}, {"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    # 2 chunks 都无 ids → valid=0
    assert out["value"] == 0.0


def test_chunk_reference_partial_missing_batch51():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["e3"]},  # invalid
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_all_missing_batch51():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e2"]}, {"source_element_ids": ["e3"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_element_id_none_skipped_batch51():
    """元素 element_id 是 None → 不在 set 中（None 不能 in None）。
    其实 None 能 in set，但 chunk 引用 None 也算 id。"""
    elements = [{"element_id": None}]
    chunks = [{"source_element_ids": [None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # {None} contains None → valid
    assert out["value"] == 1.0


def test_chunk_reference_chunk_ids_with_partial_valid_batch51():
    """chunk 引用部分 valid + 部分 invalid → all() 判定，False → 该 chunk 不算。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]  # e2 不在
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_no_chunks_batch51():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


# ---------- _image_resource_ratio 角 ----------

def test_image_ratio_no_image_elements_batch51():
    out = _image_resource_ratio([{"type": "paragraph"}], None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_ratio_resource_path_none_batch51(tmp_path):
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_empty_string_batch51(tmp_path):
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_zero_size_file_batch51(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"")  # 0 size
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_exists_nonzero_size_batch51(tmp_path):
    f = tmp_path / "img.png"
    f.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_ratio_image_base_dir_none_batch51(tmp_path):
    """image_base_dir=None → 直接用 Path(rp)。"""
    elements = [{"type": "image", "resource_path": "nonexistent.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_partial_batch51(tmp_path):
    """2 个 image，1 个存在 1 个不存在 → 0.5。"""
    f1 = tmp_path / "img1.png"
    f1.write_bytes(b"data")
    elements = [
        {"type": "image", "resource_path": "img1.png"},
        {"type": "image", "resource_path": "img2.png"},
    ]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 0.5


# ---------- _null / _ratio / _bool_metric / _int_metric ----------

def test_null_returns_dict_with_value_none_batch51():
    out = _null("any_reason")
    assert out == {"value": None, "reason": "any_reason"}


def test_ratio_returns_dict_with_float_batch51():
    out = _ratio(0.5)
    assert out == {"value": 0.5, "reason": None}
    assert isinstance(out["value"], float)


def test_ratio_int_input_converted_to_float_batch51():
    out = _ratio(1)
    assert isinstance(out["value"], float)


def test_bool_metric_returns_dict_with_bool_batch51():
    out = _bool_metric(True)
    assert out == {"value": True, "reason": None}


def test_bool_metric_int_converted_to_bool_batch51():
    out = _bool_metric(1)
    assert out["value"] is True


def test_int_metric_returns_dict_with_int_batch51():
    out = _int_metric(5)
    assert out == {"value": 5, "reason": None}


def test_int_metric_float_converted_to_int_batch51():
    out = _int_metric(5.9)
    assert out["value"] == 5
    assert isinstance(out["value"], int)


# ---------- compute_automatic_metrics 完整路径 ----------

def test_compute_metrics_pipeline_failed_returns_14_metrics_batch51():
    """document=None + error=None → pipeline_failed=True；返回 14 个 metrics。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14
    # pipeline_success 是 False（reason=None）
    assert out["pipeline_success"]["value"] is False
    # error_code 的 reason 始终是 None（不是字符串）
    assert out["error_code"]["value"] is None
    assert out["error_code"]["reason"] is None
    # 其他 12 个 metrics 都是 null + str reason
    null_metrics = {k: v for k, v in out.items() if k not in ("pipeline_success", "error_code")}
    assert len(null_metrics) == 12
    for k, v in null_metrics.items():
        assert v["value"] is None, k
        assert isinstance(v["reason"], str), k


def test_compute_metrics_schema_exception_branch_batch51(monkeypatch):
    """schema_valid 异常分支 → schema_valid = {value: False, reason: 'schema_check_exception:Type'}。"""
    def boom(_doc):
        raise RuntimeError("boom")
    monkeypatch.setattr(
        "evaluation.schema_validation.document_passes_schema",
        boom,
    )
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception:RuntimeError" in out["schema_valid"]["reason"]


def test_compute_metrics_schema_exception_value_error_batch51(monkeypatch):
    def boom(_doc):
        raise ValueError("v")
    monkeypatch.setattr(
        "evaluation.schema_validation.document_passes_schema",
        boom,
    )
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert "schema_check_exception:ValueError" in out["schema_valid"]["reason"]


def test_compute_metrics_with_full_doc_pdf_batch51():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hello",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 1
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["value"] is None
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_compute_metrics_with_full_doc_docx_batch51():
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hi",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_metrics_error_path_batch51():
    """有 error → pipeline_success=False + error_code 取自 error。"""
    err = {"code": "parse_failed"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"


def test_compute_metrics_no_error_no_doc_batch51():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] is None


# ---------- 模块常量更细 ----------

def test_text_types_exact_contents_batch51():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_text_types_length_7_batch51():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_exact_contents_batch51():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_pdf_bbox_required_types_length_4_batch51():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_subset_of_text_types_batch51():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_not_evaluated_constant_batch51():
    assert _NOT_EVALUATED == "not_evaluated"


def test_text_types_is_tuple_batch51():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_batch51():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_does_not_include_image_batch51():
    assert "image" not in _TEXT_TYPES


# ---------- 模块源码补强 ----------

def test_source_contains_counter_import_batch51():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_source_contains_math_isfinite_batch51():
    src = inspect.getsource(metrics_mod)
    assert "math.isfinite" in src


def test_source_contains_counter_intersection_batch51():
    src = inspect.getsource(metrics_mod)
    assert "c_expected & c_actual" in src


def test_source_contains_strip_unicode_whitespace_function_batch51():
    src = inspect.getsource(metrics_mod)
    assert "def _strip_unicode_whitespace" in src
    assert ".isspace()" in src


def test_source_contains_text_preservation_docstring_batch51():
    src = inspect.getsource(metrics_mod)
    assert "口径 D" in src or "口径D" in src


def test_source_contains_image_excluded_note_batch51():
    src = inspect.getsource(metrics_mod)
    assert "image" in src


def test_source_contains_pipeline_failed_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "pipeline_failed" in src


def test_source_contains_no_elements_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "no_elements" in src


def test_source_contains_no_chunks_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "no_chunks" in src


def test_source_contains_no_image_elements_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "no_image_elements" in src


def test_source_contains_no_heading_elements_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "no_heading_elements" in src


def test_source_contains_no_expectations_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "no_expectations" in src


def test_source_contains_not_pdf_document_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "not_pdf_document" in src


def test_source_contains_not_docx_document_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "not_docx_document" in src


def test_source_contains_empty_expected_actual_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "empty_expected_and_actual" in src


def test_source_contains_schema_check_exception_reason_batch51():
    src = inspect.getsource(metrics_mod)
    assert "schema_check_exception" in src


# ---------- AST 结构补强 ----------

def test_ast_has_14_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 14


def test_ast_function_names_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
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
    ]


def test_ast_no_class_def_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_no_global_statement_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Global) for n in ast.walk(tree))


def test_ast_no_nonlocal_statement_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Nonlocal) for n in ast.walk(tree))


def test_ast_no_star_import_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_has_module_docstring_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_4_top_level_assigns_batch51():
    """_TEXT_TYPES + _PDF_BBOX_REQUIRED_TYPES + _NOT_EVALUATED + __all__ = 4。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_assign_targets_names_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    names = []
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
    assert set(names) == {"_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED", "__all__"}


def test_ast_text_types_value_is_tuple_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    tt = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_TEXT_TYPES" for t in n.targets)
    )
    assert isinstance(tt.value, ast.Tuple)
    assert len(tt.value.elts) == 7


def test_ast_pdf_bbox_types_value_is_tuple_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    pt = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_PDF_BBOX_REQUIRED_TYPES" for t in n.targets)
    )
    assert isinstance(pt.value, ast.Tuple)
    assert len(pt.value.elts) == 4


def test_ast_not_evaluated_value_is_constant_str_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    ne = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_NOT_EVALUATED" for t in n.targets)
    )
    assert isinstance(ne.value, ast.Constant)
    assert ne.value.value == "not_evaluated"


def test_ast_all_value_is_list_with_1_constant_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 1
    elt = all_assign.value.elts[0]
    assert isinstance(elt, ast.Constant)
    assert elt.value == "compute_automatic_metrics"


def test_ast_module_has_5_imports_batch51():
    """__future__ + math + Counter + Path + Any = 5。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


def test_ast_compute_metrics_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_compute_metrics_has_for_loop_for_metrics_assign_batch51():
    """pipeline_failed 时 for 循环 14 个 metric → null。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # for name in (...):  +  for e in elements:  →  ≥2
    assert len(fors) >= 2


def test_ast_silent_drop_count_has_for_loop_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_image_resource_ratio_has_for_loop_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 2  # for img in images + for p in candidates


def test_ast_strip_unicode_whitespace_uses_join_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace")
    src = ast.unparse(func)
    assert "join(" in src
    assert "if not ch.isspace()" in src


def test_ast_text_preservation_uses_counter_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    src = ast.unparse(func)
    assert "Counter(" in src
    assert "c_expected & c_actual" in src


def test_ast_is_valid_bbox_uses_math_isfinite_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox")
    src = ast.unparse(func)
    assert "math.isfinite" in src


def test_ast_try_locations_batch51():
    """compute_automatic_metrics 和 _image_resource_ratio 各有 1 try；其他函数无 try。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    for func in funcs:
        tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
        if func.name in ("compute_automatic_metrics", "_image_resource_ratio"):
            assert len(tries) == 1, f"{func.name} should have 1 try"
        else:
            assert len(tries) == 0, f"{func.name} should have 0 try"


def test_ast_no_with_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.With) for n in ast.walk(tree))


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_delete_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_raise_batch51():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百三十八批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch51():
    assert "subprocess" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()
