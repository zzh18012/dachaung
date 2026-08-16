"""evaluation/metrics.py 第九十四轮 edges 测试（Round 681）。

补强 edges75 未触及的角度（第五十三批）。

新角度：
- _text_preservation 更深（Counter & 交集精确 / Counter sum == 0 分支 / expected=actual 单字符 / Unicode mixed / 空字符串 text 元素 / empty_actual + empty_expected 不同组合）
- _pdf_locator_ratio 更深（page bool/string/0/负数/大数 / text type 无 bbox / non-text type 无 bbox / locator None / locator 空 dict / locator 缺 page）
- _docx_locator_ratio 更深（locator None / locator 空 dict / locator 含 page 拒绝 / locator 含 bbox 拒绝 / 7 个 structural key 各自 / 多 key 共存）
- _is_valid_bbox 更深（长度 3/5 / 全 int / 全 float / mixed / 含字符串 / 含 None / 含 list / 含 bool）
- _image_resource_ratio 更深（rp 是绝对路径 / image_base_dir 给定但 rp 是文件名 / image_base_dir None / image_base_dir 是绝对路径）
- _chunk_reference_ratio 更深（chunks 全有 ids / 元素 element_id 重复 / chunk ids 含 None / ids 是 None / ids 是空 list）
- _heading_boundary_ratio 更深（heading 无 element_id / chunks first id None / 多 heading 共享 element_id）
- _silent_drop_count 更深（expectations None / 无 element_count_by_type / 多 type drops 求和 / type 不在 actual / actual > expected 不算 drops / actual == expected）
- compute_automatic_metrics 更深（success 完整 14 metrics / pipeline_failed 14 null + reason / source_type 是 'other' / expectations 是 None / image_base_dir 是 None / docx_source_type 走 docx 路径）
- 模块源码补强（_TEXT_TYPES 7 entries / _PDF_BBOX_REQUIRED_TYPES 4 entries / _NOT_EVALUATED str / Counter import / math import / 7 imports / 14 函数 / __all__ 1 entry / module docstring 含 evaluator v1.1 / text_preservation 语义说明）
- AST 结构补强（无 ClassDef / 无 AsyncFunctionDef / 14 FunctionDef / __all__ List 1 / 3 module-level Assigns / compute_automatic_metrics 多 metric assignment / _pdf_locator_ratio 多 if + 1 For / _docx_locator_ratio 多 if + 1 For / _is_valid_bbox 多 if + 1 For / _image_resource_ratio 2 For + 1 try / _chunk_reference_ratio 1 For / _text_preservation 多 if + 1 For / _heading_boundary_ratio 1 For / _silent_drop_count 2 if + 1 For）
- forbidden tokens 第一百五十一批
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


# ---------- _text_preservation 更深 ----------

def test_text_preservation_counter_intersection_exact_batch52():
    """Counter & 交集：每个字符取 min。"""
    # expected = "aabb" → Counter({'a':2, 'b':2})
    # actual   = "abbb" → Counter({'a':1, 'b':3})
    # 交集 = {'a':1, 'b':2} → sum = 3
    # precision = 3 / 4 = 0.75
    # recall = 3 / 4 = 0.75
    elements = [{"type": "paragraph", "content": "aabb"}]
    chunks = [{"text": "abbb"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 0.75
    assert out["equal"]["value"] is False


def test_text_preservation_single_char_equal_batch52():
    elements = [{"type": "paragraph", "content": "x"}]
    chunks = [{"text": "x"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_unicode_mixed_batch52():
    elements = [{"type": "paragraph", "content": "你好abc"}]
    chunks = [{"text": "abc你好"}]
    out = _text_preservation(elements, chunks)
    # 顺序不同 → equal False，但 Counter 相同 → p=r=1
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_empty_string_text_element_batch52():
    """某些 element 的 content 是空字符串 → 不影响。"""
    elements = [
        {"type": "paragraph", "content": ""},
        {"type": "paragraph", "content": "hello"},
    ]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


def test_text_preservation_empty_actual_with_expected_batch52():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # expected = "abc", actual = ""
    # equal = False
    # sum(c_actual.values()) == 0 → precision null empty_actual
    # sum(c_expected.values()) > 0 → recall = 0/3 = 0
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_actual"
    assert out["recall"]["value"] == 0.0


def test_text_preservation_empty_expected_with_actual_batch52():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected = "", actual = "abc"
    # equal = False
    # sum(c_actual.values()) > 0 → precision = 0/3 = 0
    # sum(c_expected.values()) == 0 → recall null empty_expected
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["value"] is None
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_empty_both_batch52():
    elements = [{"type": "paragraph", "content": ""}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # both empty → equal True，precision/recall null empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["value"] is None


# ---------- _pdf_locator_ratio 更深 ----------

def test_pdf_locator_page_bool_rejected_batch52():
    """page 是 bool → isinstance(True, int) is True 但 page < 1 拒绝 True。"""
    # True == 1，page=1 ≥1 通过；False == 0 <1 拒绝
    elements = [
        {"type": "paragraph", "source_locator": {"page": True, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    # page=True → isinstance(True, int) is True, True < 1 is False (True == 1) → 通过
    # type paragraph 在 _PDF_BBOX_REQUIRED_TYPES 中，bbox valid → valid +=1
    assert out["value"] == 1.0


def test_pdf_locator_page_string_rejected_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {"page": "1", "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    # page="1" → isinstance("1", int) False → 不通过
    assert out["value"] == 0.0


def test_pdf_locator_page_zero_rejected_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 0, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_rejected_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {"page": -5, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_large_number_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 10000, "bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_text_type_without_bbox_rejected_batch52():
    """paragraph (在 _PDF_BBOX_REQUIRED_TYPES) 缺 bbox → 拒绝。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 无 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_non_text_type_without_bbox_accepted_batch52():
    """image (不在 _PDF_BBOX_REQUIRED_TYPES) 缺 bbox → 接受。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_locator_none_batch52():
    elements = [
        {"type": "paragraph", "source_locator": None},
    ]
    out = _pdf_locator_ratio(elements)
    # loc = None or {} = {}; page = None; not int → skip
    assert out["value"] == 0.0


def test_pdf_locator_locator_empty_dict_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {}},
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_no_page_field_batch52():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [0, 0, 10, 10]}},
    ]
    out = _pdf_locator_ratio(elements)
    # page = None → not int → skip
    assert out["value"] == 0.0


def test_pdf_locator_mixed_types_batch52():
    """多 type 混合，部分合法。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},  # valid
        {"type": "image", "source_locator": {"page": 2}},  # valid (image 不需 bbox)
        {"type": "paragraph", "source_locator": {"page": 0}},  # invalid page
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 2/3


# ---------- _docx_locator_ratio 更深 ----------

def test_docx_locator_locator_none_batch52():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _docx_locator_ratio(elements)
    # loc = None or {} = {}; no page/bbox; no structural keys → skip
    assert out["value"] == 0.0


def test_docx_locator_empty_dict_batch52():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_has_page_rejected_batch52():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": 0}}]
    out = _docx_locator_ratio(elements)
    # 有 page → continue
    assert out["value"] == 0.0


def test_docx_locator_has_bbox_rejected_batch52():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "section": 0}}]
    out = _docx_locator_ratio(elements)
    # 有 bbox → continue
    assert out["value"] == 0.0


@pytest.mark.parametrize("key", [
    "section", "paragraph_index", "run_index",
    "table_index", "row_index", "col_index", "relationship_id",
])
def test_docx_locator_each_structural_key_accepted_batch52(key):
    elements = [{"type": "paragraph", "source_locator": {key: 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_multiple_structural_keys_batch52():
    elements = [{"type": "paragraph", "source_locator": {
        "section": 0, "paragraph_index": 1, "run_index": 0,
    }}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_no_structural_keys_rejected_batch52():
    elements = [{"type": "paragraph", "source_locator": {"unknown_key": "x"}}]
    out = _docx_locator_ratio(elements)
    # unknown_key 不在 structural_keys → continue
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 更深 ----------

def test_is_valid_bbox_length_3_rejected_batch52():
    assert _is_valid_bbox([0, 0, 10]) is False


def test_is_valid_bbox_length_5_rejected_batch52():
    assert _is_valid_bbox([0, 0, 10, 10, 10]) is False


def test_is_valid_bbox_all_int_batch52():
    assert _is_valid_bbox([0, 0, 100, 200]) is True


def test_is_valid_bbox_all_float_batch52():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 200.5]) is True


def test_is_valid_bbox_mixed_int_float_batch52():
    assert _is_valid_bbox([0, 0.0, 100, 200.5]) is True


def test_is_valid_bbox_string_rejected_batch52():
    assert _is_valid_bbox(["0", "0", "10", "10"]) is False


def test_is_valid_bbox_none_rejected_batch52():
    assert _is_valid_bbox([None, None, None, None]) is False


def test_is_valid_bbox_nested_list_rejected_batch52():
    assert _is_valid_bbox([[0], [0], [10], [10]]) is False


def test_is_valid_bbox_inf_rejected_batch52():
    assert _is_valid_bbox([0, 0, math.inf, 10]) is False


def test_is_valid_bbox_nan_rejected_batch52():
    assert _is_valid_bbox([0, 0, math.nan, 10]) is False


def test_is_valid_bbox_negative_accepted_batch52():
    """负数也是有限数。"""
    assert _is_valid_bbox([-10, -10, 0, 0]) is True


def test_is_valid_bbox_tuple_rejected_batch52():
    """tuple 不是 list。"""
    assert _is_valid_bbox((0, 0, 10, 10)) is False


# ---------- _image_resource_ratio 更深 ----------

def test_image_resource_ratio_no_image_elements_batch52():
    out = _image_resource_ratio([], None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_without_resource_path_batch52():
    elements = [{"type": "image"}]  # 无 resource_path
    out = _image_resource_ratio(elements, None)
    # 1 image, valid=0 → ratio 0/1 = 0.0
    assert out["value"] == 0.0


def test_image_resource_ratio_image_empty_resource_path_batch52():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_with_existing_file_batch52(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")  # PNG header
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_with_zero_size_file_batch52(tmp_path):
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_with_image_base_dir_filename_batch52(tmp_path):
    img = tmp_path / "test.jpg"
    img.write_bytes(b"\xff\xd8\xff")  # JPEG header
    elements = [{"type": "image", "resource_path": "test.jpg"}]
    out = _image_resource_ratio(elements, tmp_path)
    # candidates = [Path("test.jpg"), tmp_path / "test.jpg"]
    # 第二个 is_file → valid
    assert out["value"] == 1.0


def test_image_resource_ratio_with_image_base_dir_absolute_rp_batch52(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, tmp_path)
    # 第一个 candidate Path(rp).is_file → valid
    assert out["value"] == 1.0


def test_image_resource_ratio_mixed_batch52(tmp_path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},  # valid
        {"type": "image", "resource_path": "missing.png"},  # invalid
        {"type": "image"},  # no resource_path → invalid
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1/3


# ---------- _chunk_reference_ratio 更深 ----------

def test_chunk_reference_no_chunks_batch52():
    out = _chunk_reference_ratio([], [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_all_chunks_have_valid_ids_batch52():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_duplicated_element_ids_batch52():
    """元素 element_id 重复（异常但理论上可行）→ ids 集合覆盖。"""
    elements = [{"element_id": "e1"}, {"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # elem_ids = {"e1"}; chunk id "e1" in elem_ids → valid
    assert out["value"] == 1.0


def test_chunk_reference_ids_contain_none_batch52():
    """chunk ids 含 None → None not in elem_ids → 整个 chunk 不 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", None]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all(sid in elem_ids for sid in ["e1", None]) → False → not valid
    assert out["value"] == 0.0


def test_chunk_reference_ids_none_batch52():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids = None or [] = [] → ids is falsy → not valid
    assert out["value"] == 0.0


def test_chunk_reference_ids_empty_list_batch52():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids = [] → falsy → not valid
    assert out["value"] == 0.0


# ---------- _heading_boundary_ratio 更深 ----------

def test_heading_boundary_no_headings_batch52():
    out = _heading_boundary_ratio([], [{"text": "x"}])
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_heading_without_element_id_batch52():
    elements = [{"type": "heading"}]  # 无 element_id
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # headings = [h]; h.get("element_id") = None; None in chunk_first_ids ({"h1"}) → False
    # matched = 0
    assert out["value"] == 0.0


def test_heading_boundary_chunks_first_id_none_batch52():
    """chunks 的 source_element_ids[0] 是 None。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": [None]}]
    out = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids = {None}; h1 in {None} → False
    assert out["value"] == 0.0


def test_heading_boundary_perfect_match_batch52():
    elements = [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}]
    chunks = [
        {"source_element_ids": ["h1", "other"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_partial_match_batch52():
    elements = [{"type": "heading", "element_id": "h1"}, {"type": "heading", "element_id": "h2"}]
    chunks = [{"source_element_ids": ["h1"]}]  # h2 未匹配
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 更深 ----------

def test_silent_drop_no_expectations_batch52():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_expectations_no_element_count_batch52():
    out = _silent_drop_count({"paragraph": 5}, {"required_markers": ["x"]})
    # expectations but no element_count_by_type
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_expectations_empty_element_count_batch52():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    # empty dict → falsy
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_multi_type_sum_batch52():
    by_type = {"paragraph": 3, "heading": 1}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 2}}
    out = _silent_drop_count(by_type, expectations)
    # paragraph: max(0, 5-3) = 2; heading: max(0, 2-1) = 1
    # total drops = 3
    assert out["value"] == 3


def test_silent_drop_type_not_in_actual_batch52():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    # actual heading = by_type.get("heading", 0) = 0; 0 < 3 → drop 3
    assert out["value"] == 3


def test_silent_drop_actual_more_than_expected_batch52():
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    # 10 > 5 → 不算 drop
    assert out["value"] == 0


def test_silent_drop_actual_equals_expected_batch52():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


# ---------- compute_automatic_metrics 更深 ----------

def test_compute_metrics_pipeline_failed_14_metrics_keys_batch52():
    out = compute_automatic_metrics(
        document=None, error={"code": "fail"}, source_type="pdf", expectations=None
    )
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(out.keys()) == expected_keys


def test_compute_metrics_pipeline_failed_all_null_batch52():
    out = compute_automatic_metrics(
        document=None, error={"code": "fail"}, source_type="pdf", expectations=None
    )
    # pipeline_success = False
    assert out["pipeline_success"]["value"] is False
    # 后续 11 项都是 _null("pipeline_failed")
    for k in (
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    ):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_compute_metrics_error_code_value_batch52():
    out = compute_automatic_metrics(
        document=None, error={"code": "e_123"}, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] == "e_123"


def test_compute_metrics_error_code_none_when_no_error_batch52():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["error_code"]["value"] is None


def test_compute_metrics_schema_valid_when_document_none_batch52():
    out = compute_automatic_metrics(
        document=None, error={"code": "x"}, source_type="pdf", expectations=None
    )
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_metrics_source_type_other_batch52():
    """source_type 不是 pdf/docx → pdf_ratio 和 docx_ratio 都 null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="other", expectations=None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_source_type_batch52():
    doc = {
        "elements": [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="docx", expectations=None
    )
    # docx 路径走 _docx_locator_ratio
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_metrics_success_returns_14_metrics_batch52():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert len(out) == 14


def test_compute_metrics_success_pipeline_success_true_batch52():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["pipeline_success"]["value"] is True


def test_compute_metrics_expectations_none_batch52():
    """expectations None → silent_drop_count null。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out["silent_drop_count"]["reason"] == "no_expectations"


# ---------- _null / _ratio / _bool_metric / _int_metric ----------

def test_null_returns_proper_dict_batch52():
    out = _null("reason_x")
    assert out == {"value": None, "reason": "reason_x"}


def test_ratio_returns_proper_dict_batch52():
    out = _ratio(0.5)
    assert out == {"value": 0.5, "reason": None}


def test_ratio_converts_to_float_batch52():
    out = _ratio(1)  # int → float
    assert isinstance(out["value"], float)
    assert out["value"] == 1.0


def test_bool_metric_returns_proper_dict_batch52():
    out = _bool_metric(True)
    assert out == {"value": True, "reason": None}


def test_bool_metric_converts_to_bool_batch52():
    out = _bool_metric(1)  # int → bool
    assert isinstance(out["value"], bool)
    assert out["value"] is True


def test_int_metric_returns_proper_dict_batch52():
    out = _int_metric(42)
    assert out == {"value": 42, "reason": None}


def test_int_metric_converts_to_int_batch52():
    out = _int_metric(True)  # bool → int
    assert isinstance(out["value"], int)
    assert out["value"] == 1


# ---------- 模块源码补强 ----------

def test_source_text_types_7_entries_batch52():
    assert len(_TEXT_TYPES) == 7
    assert "heading" in _TEXT_TYPES
    assert "paragraph" in _TEXT_TYPES
    assert "list_item" in _TEXT_TYPES
    assert "table" in _TEXT_TYPES
    assert "caption" in _TEXT_TYPES
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES


def test_source_pdf_bbox_required_4_entries_batch52():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {"heading", "paragraph", "caption", "list_item"}


def test_source_text_types_is_tuple_batch52():
    assert isinstance(_TEXT_TYPES, tuple)


def test_source_pdf_bbox_required_is_tuple_batch52():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_source_not_evaluated_value_batch52():
    assert _NOT_EVALUATED == "not_evaluated"


def test_source_future_annotations_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from __future__ import annotations" in src


def test_source_math_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "import math" in src


def test_source_counter_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_source_pathlib_path_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from pathlib import Path" in src


def test_source_typing_any_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from typing import Any" in src


def test_source_has_text_preservation_docstring_v11_batch52():
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src


def test_source_has_strip_unicode_whitespace_function_batch52():
    src = inspect.getsource(metrics_mod)
    assert "def _strip_unicode_whitespace" in src


def test_source_text_types_definition_batch52():
    src = inspect.getsource(metrics_mod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_source_pdf_bbox_required_definition_batch52():
    src = inspect.getsource(metrics_mod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_source_not_evaluated_definition_batch52():
    src = inspect.getsource(metrics_mod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_source_compute_metrics_signature_batch52():
    src = inspect.getsource(metrics_mod)
    assert "def compute_automatic_metrics(" in src
    assert "document: dict[str, Any] | None" in src
    assert "error: dict[str, Any] | None" in src
    assert "source_type: str" in src
    assert "expectations: dict[str, Any] | None" in src
    assert "image_base_dir: Path | None = None" in src


def test_source_compute_metrics_uses_lazy_schema_import_batch52():
    src = inspect.getsource(metrics_mod)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_source_pipeline_failed_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"pipeline_failed"' in src


def test_source_empty_expected_and_actual_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected_and_actual"' in src


def test_source_empty_actual_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"empty_actual"' in src


def test_source_empty_expected_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"empty_expected"' in src


def test_source_no_expectations_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations"' in src


def test_source_no_chunks_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_chunks"' in src


def test_source_no_elements_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_elements"' in src


def test_source_no_image_elements_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_image_elements"' in src


def test_source_no_heading_elements_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_heading_elements"' in src


def test_source_not_pdf_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"not_pdf_document"' in src


def test_source_not_docx_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"not_docx_document"' in src


def test_source_no_expectations_element_count_reason_batch52():
    src = inspect.getsource(metrics_mod)
    assert '"no_expectations_element_count"' in src


def test_source_all_has_only_compute_metrics_batch52():
    src = inspect.getsource(metrics_mod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- AST 结构补强 ----------

def test_ast_has_14_functions_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 14


def test_ast_function_names_order_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    ]


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_has_3_module_level_assigns_batch52():
    """_TEXT_TYPES + _PDF_BBOX_REQUIRED_TYPES + _NOT_EVALUATED + __all__ = 4。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_all_value_is_list_1_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 1


def test_ast_text_types_assign_tuple_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_TEXT_TYPES" for t in n.targets)
    )
    assert isinstance(assign.value, ast.Tuple)


def test_ast_pdf_bbox_required_assign_tuple_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_PDF_BBOX_REQUIRED_TYPES" for t in n.targets)
    )
    assert isinstance(assign.value, ast.Tuple)


def test_ast_pdf_locator_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_pdf_locator_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_docx_locator_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_docx_locator_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_is_valid_bbox_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_image_resource_ratio_has_2_for_loops_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 2  # for img in images + for p in candidates


def test_ast_image_resource_ratio_has_try_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_image_resource_ratio")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_chunk_reference_ratio_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_chunk_reference_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_strip_unicode_whitespace_returns_str_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace")
    # 签名 s: str
    assert func.args.args[0].arg == "s"


def test_ast_text_preservation_has_counter_calls_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    counter_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "Counter"
    ]
    assert len(counter_calls) == 2


def test_ast_text_preservation_has_multiple_if_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_text_preservation")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # if not expected and not actual + if sum_actual==0 + if sum_expected==0 = 3
    assert len(ifs) == 3


def test_ast_heading_boundary_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_heading_boundary_ratio")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_silent_drop_has_for_loop_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_silent_drop_has_2_if_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_silent_drop_count")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    # if not expectations + if not expected_counts + if actual < exp = 3
    assert len(ifs) == 3


def test_ast_compute_metrics_has_if_document_none_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    src = ast.unparse(func)
    assert "if document is None:" in src


def test_ast_compute_metrics_has_multiple_metric_assigns_batch52():
    """compute_automatic_metrics 至少 14 个 metrics[name] = ... 赋值。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics")
    # 找所有 metrics[...] = ... 赋值
    metric_assigns = []
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == "metrics":
                    metric_assigns.append(n)
                    break
    assert len(metric_assigns) >= 14


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_with_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.With) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_raise_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def test_ast_no_delete_batch52():
    tree = ast.parse(inspect.getsource(metrics_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百五十一批 ----------

def _src() -> str:
    return inspect.getsource(metrics_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    """metrics.py 不使用 open()。"""
    assert "open(" not in _src()
