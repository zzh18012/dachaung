"""evaluation/metrics.py 第四十五轮 edges 测试（Round 436）。

补强 edges42 未触及的角度：
- _null / _ratio / _bool_metric / _int_metric 边界第十六批（None / True / 1.0 / 负数 / 浮点截断 / 零长 reason / 大整数）
- compute_automatic_metrics 第十六批（error empty dict / source_type=txt/other / chunks 空 / elements 空 / schema 异常 / 不修改 document 字段顺序 / image_base_dir 真实路径 / 各 reason 字符串值）
- _strip_unicode_whitespace 第十六批（empty / all WS / all non-WS / NUL / ZWSP 非空白）
- _is_valid_bbox 第十六批（inf / nan / mixed / True bool / 字符串数字）
- _pdf_locator_ratio 第十六批（all valid / all invalid / locator None / heading 无 bbox / image 不要求 bbox）
- _docx_locator_ratio 第十六批（relationship_id / section 多键 / locator None / 空 dict / 含 page+bbox+section → invalid）
- _image_resource_ratio 第十六批（tmp file 真实路径 / 空文件 / 不存在 / image_base_dir 拼接）
- _chunk_reference_ratio 第十六批（chunks None ids / 重复 id / extra ids / 空元素集）
- _text_preservation 第十六批（reversed / subset / Counter 交集 / chunks 空 / elements 全 image）
- _heading_boundary_ratio 第十六批（chunk 多 ids / heading 无 element_id / 多 heading 同 chunk）
- _silent_drop_count 第十六批（actual > expected / 多类型 / expectations=None / 空 dict / element_count_by_type=None）
- module source forbidden tokens 第三十一批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from evaluation import metrics as mmod
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


# ---------- _null / _ratio / _bool_metric / _int_metric 边界第十六批 ----------


def test_null_returns_value_none_batch16():
    r = _null("reason")
    assert r["value"] is None
    assert r["reason"] == "reason"


def test_null_empty_reason_batch16():
    r = _null("")
    assert r["value"] is None
    assert r["reason"] == ""


def test_null_long_reason_batch16():
    r = _null("a" * 200)
    assert len(r["reason"]) == 200


def test_ratio_value_zero_batch16():
    r = _ratio(0)
    assert r["value"] == 0.0
    assert r["reason"] is None


def test_ratio_value_one_batch16():
    r = _ratio(1)
    assert r["value"] == 1.0


def test_ratio_negative_batch16():
    """ratio 不做范围检查；负数也接受。"""
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_ratio_float_truncate_not_rounded_batch16():
    """ratio 用 float()，不做 round。"""
    r = _ratio(1 / 3)
    assert abs(r["value"] - 0.3333333333333333) < 1e-9


def test_ratio_int_to_float_batch16():
    r = _ratio(2)
    assert isinstance(r["value"], float)
    assert r["value"] == 2.0


def test_bool_metric_none_batch16():
    """bool(None) → False。"""
    r = _bool_metric(None)
    assert r["value"] is False


def test_bool_metric_zero_batch16():
    r = _bool_metric(0)
    assert r["value"] is False


def test_bool_metric_empty_string_batch16():
    r = _bool_metric("")
    assert r["value"] is False


def test_bool_metric_true_batch16():
    r = _bool_metric(True)
    assert r["value"] is True


def test_int_metric_negative_batch16():
    r = _int_metric(-3)
    assert r["value"] == -3


def test_int_metric_truncates_float_batch16():
    """int(3.7) → 3（截断，不四舍五入）。"""
    r = _int_metric(3.7)
    assert r["value"] == 3


def test_int_metric_true_is_one_batch16():
    r = _int_metric(True)
    assert r["value"] == 1


def test_int_metric_big_batch16():
    r = _int_metric(10**18)
    assert r["value"] == 10**18


# ---------- compute_automatic_metrics 第十六批 ----------


def test_compute_metrics_error_empty_dict_batch16():
    """error 是空 dict → pipeline_success False（用 `is None` 判断，不是 truthy）。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, {}, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    # 但 error_code value=None（因为 error["code"] if error → falsy → None）
    assert m["error_code"]["value"] is None


def test_compute_metrics_error_with_code_batch16():
    err = {"code": "parse_failed"}
    m = compute_automatic_metrics(None, err, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "parse_failed"


def test_compute_metrics_source_type_txt_batch16():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "txt", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_other_batch16():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "other", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_chunks_empty_batch16():
    doc = {"elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["chunk_reference_intact_ratio"]["reason"] == "no_chunks"
    assert m["text_preservation_equal"]["value"] is False


def test_compute_metrics_elements_empty_batch16():
    doc = {"elements": [], "chunks": [{"text": "x", "source_element_ids": []}]}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_does_not_modify_document_keys_batch16():
    doc = {"elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
           "chunks": [{"text": "a", "source_element_ids": ["e1"]}]}
    before = list(doc.keys())
    compute_automatic_metrics(doc, None, "pdf", None)
    assert list(doc.keys()) == before


def test_compute_metrics_does_not_modify_document_values_batch16():
    doc = {"elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
           "chunks": [{"text": "a", "source_element_ids": ["e1"]}]}
    elem_before = dict(doc["elements"][0])
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc["elements"][0] == elem_before


def test_compute_metrics_schema_check_exception_batch16():
    """document_passes_schema 抛异常 → schema_valid value=False + reason 含 schema_check_exception。"""
    doc = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["schema_valid"]["value"] is False
    assert "schema_check_exception" in m["schema_valid"]["reason"]
    assert "RuntimeError" in m["schema_valid"]["reason"]


def test_compute_metrics_image_base_dir_none_uses_path_str_batch16(tmp_path):
    """image_base_dir=None 时直接用 resource_path 字符串。"""
    img_path = tmp_path / "x.png"
    img_path.write_bytes(b"\x89PNG\r\n")
    doc = {"elements": [{"type": "image", "resource_path": str(img_path)}], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_metrics_returns_dict_type_batch16():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert isinstance(m, dict)


def test_compute_metrics_pipeline_success_when_both_none_batch16():
    """document=None + error=None → pipeline_success False（document is None）。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] is None


def test_compute_metrics_error_code_value_is_none_when_no_error_batch16():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["error_code"]["value"] is None
    assert m["error_code"]["reason"] is None


# ---------- _strip_unicode_whitespace 第十六批 ----------


def test_strip_unicode_whitespace_empty_batch16():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_ws_batch16():
    assert _strip_unicode_whitespace("  \t\n\r") == ""


def test_strip_unicode_whitespace_no_ws_batch16():
    assert _strip_unicode_whitespace("abcXYZ") == "abcXYZ"


def test_strip_unicode_whitespace_nul_not_ws_batch16():
    """NUL 字符 \x00 不是空白。"""
    assert _strip_unicode_whitespace("a\x00b") == "a\x00b"


def test_strip_unicode_whitespace_zwsp_not_ws_batch16():
    """ZWSP (U+200B) 不是空白（isspace() 返回 False）。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_preserves_order_batch16():
    assert _strip_unicode_whitespace("c b a") == "cba"


def test_strip_unicode_whitespace_preserves_duplicates_batch16():
    assert _strip_unicode_whitespace("aa bb aa") == "aabbaa"


def test_strip_unicode_whitespace_mixed_batch16():
    """多种空白混合。"""
    s = "a\tb\nc\rd e　f"
    assert _strip_unicode_whitespace(s) == "abcdef"


# ---------- _is_valid_bbox 第十六批 ----------


def test_is_valid_bbox_inf_batch16():
    assert _is_valid_bbox([0, math.inf, 1, 1]) is False


def test_is_valid_bbox_neg_inf_batch16():
    assert _is_valid_bbox([0, -math.inf, 1, 1]) is False


def test_is_valid_bbox_nan_batch16():
    assert _is_valid_bbox([0, math.nan, 1, 1]) is False


def test_is_valid_bbox_with_true_batch16():
    """True 是 int 的子类但被显式拒绝。"""
    assert _is_valid_bbox([True, 0, 1, 1]) is False


def test_is_valid_bbox_with_false_batch16():
    assert _is_valid_bbox([0, False, 1, 1]) is False


def test_is_valid_bbox_string_digits_batch16():
    """字符串 '1' 不是数字。"""
    assert _is_valid_bbox(["0", "0", "1", "1"]) is False


def test_is_valid_bbox_mixed_valid_batch16():
    assert _is_valid_bbox([0.5, 1, 1.5, 2]) is True


def test_is_valid_bbox_tuple_batch16():
    """tuple 不是 list → False。"""
    assert _is_valid_bbox((0, 0, 1, 1)) is False


def test_is_valid_bbox_negative_values_batch16():
    """负数是有限数 → True。"""
    assert _is_valid_bbox([-1, -1, 0, 0]) is True


# ---------- _pdf_locator_ratio 第十六批 ----------


def test_pdf_locator_ratio_all_valid_batch16():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {"page": 2, "bbox": [0, 0, 1, 1]}},
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_all_invalid_batch16():
    elements = [
        {"type": "paragraph", "source_locator": {}},
        {"type": "paragraph", "source_locator": {"page": 0}},
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch16():
    """locator 是 None → `loc = None or {}` → {} → page=None → 跳过。"""
    elements = [{"type": "paragraph", "source_locator": None}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_image_no_bbox_required_batch16():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES → 只要有 page 就算 valid。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_heading_requires_bbox_batch16():
    """heading 在 _PDF_BBOX_REQUIRED_TYPES → 缺 bbox 算 invalid。"""
    elements = [{"type": "heading", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_caption_requires_bbox_batch16():
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_list_item_requires_bbox_batch16():
    elements = [{"type": "list_item", "source_locator": {"page": 1}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_no_locator_key_batch16():
    """element 没有 source_locator 键 → 用 .get() 返回 None → {} → invalid。"""
    elements = [{"type": "paragraph"}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_mixed_half_batch16():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        {"type": "paragraph", "source_locator": {}},
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.5


# ---------- _docx_locator_ratio 第十六批 ----------


def test_docx_locator_ratio_relationship_id_only_batch16():
    elements = [{"type": "paragraph", "source_locator": {"relationship_id": "rId1"}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_section_paragraph_batch16():
    elements = [{"type": "paragraph", "source_locator": {"section": 0, "paragraph_index": 1}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_locator_none_batch16():
    elements = [{"type": "paragraph", "source_locator": None}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_empty_dict_batch16():
    elements = [{"type": "paragraph", "source_locator": {}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_page_present_invalidates_batch16():
    """含 page → 整个 element invalid（即使有 paragraph_index）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_bbox_present_invalidates_batch16():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_no_locator_key_batch16():
    elements = [{"type": "paragraph"}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_all_structural_keys_batch16():
    loc = {"section": 0, "paragraph_index": 0, "run_index": 0,
           "table_index": 0, "row_index": 0, "col_index": 0, "relationship_id": "x"}
    elements = [{"type": "paragraph", "source_locator": loc}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


# ---------- _image_resource_ratio 第十六批 ----------


def test_image_resource_ratio_real_file_batch16(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_ratio_empty_file_batch16(tmp_path):
    """空文件（size=0）→ invalid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_nonexistent_file_batch16():
    elements = [{"type": "image", "resource_path": "/no/such/file.png"}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_image_base_dir_prepended_batch16(tmp_path):
    """resource_path 只是文件名，image_base_dir 拼接后能找到。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 1.0


def test_image_resource_ratio_mixed_batch16(tmp_path):
    img1 = tmp_path / "a.png"
    img1.write_bytes(b"\x89PNG")
    img2 = tmp_path / "b.png"
    img2.write_bytes(b"")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": str(img2)},
    ]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.5


def test_image_resource_ratio_resource_path_empty_batch16():
    elements = [{"type": "image", "resource_path": ""}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_resource_path_none_batch16():
    elements = [{"type": "image", "resource_path": None}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_no_resource_path_key_batch16():
    elements = [{"type": "image"}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


# ---------- _chunk_reference_ratio 第十六批 ----------


def test_chunk_reference_ratio_source_ids_none_batch16():
    """source_element_ids 是 None → falsy → 不算 valid。"""
    chunks = [{"text": "x", "source_element_ids": None}]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_duplicate_ids_batch16():
    """重复 element_id 在同一 chunk → 仍算 valid（all 检查通过）。"""
    chunks = [{"text": "x", "source_element_ids": ["e1", "e1"]}]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_extra_ids_batch16():
    """包含不存在的 id → invalid。"""
    chunks = [{"text": "x", "source_element_ids": ["e1", "e2"]}]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_empty_elements_batch16():
    """elements 空 → elem_ids 空 → 所有 chunk ids 都 not in → 0。"""
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    r = _chunk_reference_ratio([], chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_partial_valid_batch16():
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},
        {"text": "y", "source_element_ids": ["e2"]},  # e2 not in elements
    ]
    r = _chunk_reference_ratio([{"element_id": "e1"}], chunks)
    assert r["value"] == 0.5


# ---------- _text_preservation 第十六批 ----------


def test_text_preservation_reversed_text_batch16():
    """reversed → equal=False, but precision/recall=1.0（同字符集）。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "cba", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_subset_batch16():
    """actual 是 expected 的子集。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["value"] == 1.0
    assert abs(r["recall"]["value"] - 2 / 3) < 1e-9


def test_text_preservation_chunks_empty_batch16():
    """chunks 空 → actual=空 → equal=False, precision=null, recall=0。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    r = _text_preservation(elements, [])
    assert r["equal"]["value"] is False
    assert r["precision"]["reason"] == "empty_actual"
    assert r["recall"]["value"] == 0.0


def test_text_preservation_elements_all_image_batch16():
    """elements 全是 image → expected=空（image 跳过）。"""
    elements = [{"type": "image"}]
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["recall"]["reason"] == "empty_expected"
    assert r["precision"]["value"] == 0.0  # common=0 / 3


def test_text_preservation_counter_intersect_batch16():
    """Counter 交集：min count。"""
    elements = [{"type": "paragraph", "content": "aabbcc"}]
    chunks = [{"text": "abc", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    # common = a+b+c = 3, |actual|=3, |expected|=6
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 0.5


def test_text_preservation_both_empty_batch16():
    """expected 和 actual 都空 → precision/recall 都是 empty_expected_and_actual。"""
    elements = [{"type": "image"}]
    chunks = []
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True
    assert r["precision"]["reason"] == "empty_expected_and_actual"
    assert r["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_image_content_ignored_batch16():
    """image element 即使有 content 也不参与。"""
    elements = [{"type": "image", "content": "abc"}]
    chunks = [{"text": "abc", "source_element_ids": ["e1"]}]
    r = _text_preservation(elements, chunks)
    # expected=空（只有 image，content 被忽略）
    assert r["equal"]["value"] is False
    assert r["recall"]["reason"] == "empty_expected"


# ---------- _heading_boundary_ratio 第十六批 ----------


def test_heading_boundary_chunk_multiple_ids_batch16():
    """chunk source_element_ids 第一个不是 heading → 不算 matched（即使 heading 在 ids 列表里）。"""
    elements = [
        {"type": "paragraph", "element_id": "p1"},
        {"type": "heading", "element_id": "h1"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["p1", "h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_no_element_id_batch16():
    """heading 没有 element_id → h.get("element_id") None → 不在 set → unmatched。"""
    elements = [{"type": "heading"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_multiple_headings_same_chunk_batch16():
    """两个 heading 都指向同一 chunk 的第一个 id → 都算 matched。"""
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h1"},  # 同 id（不正常但 schema 没限）
    ]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_empty_chunks_batch16():
    """chunks 空 → no chunk starts → 0 matched。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r["value"] == 0.0


def test_heading_boundary_chunk_first_id_empty_list_batch16():
    """chunk source_element_ids 是空 list → 不算作 first id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


# ---------- _silent_drop_count 第十六批 ----------


def test_silent_drop_actual_greater_than_expected_batch16():
    """actual > expected → 不计入 drops（max(0, exp-act)=0）。"""
    by_type = {"paragraph": 5}
    exp = {"element_count_by_type": {"paragraph": 3}}
    r = _silent_drop_count(by_type, exp)
    assert r["value"] == 0


def test_silent_drop_multiple_types_batch16():
    by_type = {"paragraph": 3, "heading": 0, "table": 2}
    exp = {"element_count_by_type": {"paragraph": 5, "heading": 2, "table": 2}}
    r = _silent_drop_count(by_type, exp)
    # paragraph: 5-3=2, heading: 2-0=2, table: 2-2=0 → 4
    assert r["value"] == 4


def test_silent_drop_no_expectations_batch16():
    r = _silent_drop_count({"paragraph": 5}, None)
    assert r["reason"] == "no_expectations"
    assert r["value"] is None


def test_silent_drop_empty_dict_batch16():
    r = _silent_drop_count({"paragraph": 5}, {})
    assert r["reason"] == "no_expectations"


def test_silent_drop_element_count_by_type_none_batch16():
    """expectations 有但 element_count_by_type 是 None → no_expectations_element_count。"""
    r = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": None})
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_element_count_by_type_empty_batch16():
    r = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_extra_type_in_expectations_batch16():
    """expectations 含 actual 中没有的 type → 算全部 expected 为 drop。"""
    by_type = {}
    exp = {"element_count_by_type": {"paragraph": 3}}
    r = _silent_drop_count(by_type, exp)
    assert r["value"] == 3


# ---------- module source forbidden tokens 第三十一批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch16():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src


def test_module_source_no_network_calls_batch16():
    """不调用 urllib / requests / http.client。"""
    src = inspect.getsource(mmod)
    assert "urllib.request" not in src
    assert "import requests" not in src
    assert "http.client" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(mmod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(mmod)
    assert "自动指标：13 项" in src


def test_module_source_has_text_types_constant_batch16():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES = " in src


def test_module_source_has_pdf_bbox_constant_batch16():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = " in src


def test_module_source_has_counter_import_batch16():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_math_import_batch16():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_typing_any_import_batch16():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_pathlib_import_batch16():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_compute_function_batch16():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_null_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_has_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_has_bool_metric_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_has_int_metric_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_has_strip_unicode_whitespace_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_has_is_valid_bbox_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_has_pdf_locator_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_has_docx_locator_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_has_image_resource_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_has_chunk_reference_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_has_text_preservation_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_has_heading_boundary_ratio_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_has_silent_drop_count_function_batch16():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第二十八批 ----------


def test_signature_null_batch16():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_ratio_batch16():
    sig = inspect.signature(_ratio)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_batch16():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_int_metric_batch16():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_compute_metrics_batch16():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_pdf_locator_ratio_batch16():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_ratio_batch16():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_image_resource_ratio_batch16():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_ratio_batch16():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_text_preservation_batch16():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_ratio_batch16():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_silent_drop_count_batch16():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


def test_signature_strip_unicode_whitespace_batch16():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_signature_is_valid_bbox_batch16():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(mmod, "__all__")
    assert isinstance(mmod.__all__, list)


def test_module_all_items_in_namespace_batch16():
    for name in mmod.__all__:
        assert hasattr(mmod, name)


def test_module_all_count_1_batch16():
    assert len(mmod.__all__) == 1


def test_module_compute_callable_batch16():
    assert callable(compute_automatic_metrics)


def test_module_null_callable_batch16():
    assert callable(_null)


def test_module_ratio_callable_batch16():
    assert callable(_ratio)


def test_module_bool_metric_callable_batch16():
    assert callable(_bool_metric)


def test_module_int_metric_callable_batch16():
    assert callable(_int_metric)


def test_module_text_types_is_tuple_batch16():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_pdf_bbox_required_types_is_tuple_batch16():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


# ---------- 端到端集成第二十八批 ----------


def test_e2e_pdf_full_pipeline_batch16():
    """完整 PDF 路径：元素 + chunks + 期望。"""
    doc = {
        "elements": [
            {"type": "heading", "content": "标题", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "content": "正文", "element_id": "p1",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "标题正文", "source_element_ids": ["h1", "p1"]},
        ],
    }
    exp = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", exp)
    assert m["element_count_total"]["value"] == 2
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["text_preservation_equal"]["value"] is True
    assert m["silent_drop_count"]["value"] == 0


def test_e2e_docx_full_pipeline_batch16():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "正文", "element_id": "p1",
             "source_locator": {"paragraph_index": 0, "section": 0}},
        ],
        "chunks": [
            {"text": "正文", "source_element_ids": ["p1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_pipeline_failed_returns_all_null_batch16():
    m = compute_automatic_metrics(None, {"code": "x"}, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "x"
    assert m["schema_valid"]["reason"] == "pipeline_failed"
    assert m["element_count_total"]["reason"] == "pipeline_failed"
    assert m["silent_drop_count"]["reason"] == "pipeline_failed"


def test_e2e_metrics_dict_size_is_14_batch16():
    """compute_automatic_metrics 必须返回 14 个 key。"""
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(m) == 14


def test_e2e_metric_keys_correct_batch16():
    doc = {"elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid", "element_count_total",
        "element_count_by_type", "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio", "text_preservation_equal",
        "text_char_multiset_precision", "text_char_multiset_recall",
        "heading_boundary_compliance", "silent_drop_count",
    }
    assert set(m.keys()) == expected_keys


def test_e2e_locator_ratio_pdf_no_elements_batch16():
    r = _pdf_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_e2e_locator_ratio_docx_no_elements_batch16():
    r = _docx_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_e2e_image_ratio_no_images_batch16():
    r = _image_resource_ratio([{"type": "paragraph"}], None)
    assert r["reason"] == "no_image_elements"


def test_e2e_chunk_reference_no_chunks_batch16():
    r = _chunk_reference_ratio([], [])
    assert r["reason"] == "no_chunks"


def test_e2e_heading_boundary_no_headings_batch16():
    r = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert r["reason"] == "no_heading_elements"
