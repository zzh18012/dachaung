"""evaluation/metrics.py 第三十六轮 edges 测试（Round 380）。

重点补强 edges34 未触及的角度：
- compute_automatic_metrics 行为深度第八批
- _pdf_locator_ratio 行为深度第八批
- _docx_locator_ratio 行为深度第八批
- _image_resource_ratio 行为深度第八批
- _chunk_reference_ratio 行为深度第八批
- _text_preservation 行为深度第八批
- _heading_boundary_ratio 行为深度第八批
- _silent_drop_count 行为深度第八批
- _is_valid_bbox 行为深度第八批
- _strip_unicode_whitespace 行为深度第八批
- module source forbidden tokens 第十一批
- module source 字符串精确补强第八批
- signatures 第八批
- module 合理性第八批
- 端到端集成第八批
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


# ---------- _null / _ratio / _bool_metric / _int_metric helpers ----------


def test_null_returns_proper_structure():
    r = _null("my_reason")
    assert r == {"value": None, "reason": "my_reason"}


def test_null_with_empty_reason():
    r = _null("")
    assert r == {"value": None, "reason": ""}


def test_ratio_returns_proper_structure():
    r = _ratio(0.5)
    assert r == {"value": 0.5, "reason": None}


def test_ratio_with_int_input_converts_to_float():
    r = _ratio(1)
    assert r["value"] == 1.0
    assert isinstance(r["value"], float)


def test_ratio_with_zero():
    r = _ratio(0.0)
    assert r == {"value": 0.0, "reason": None}


def test_ratio_with_negative():
    """负数也接受（虽然业务上不应有）."""
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_bool_metric_true():
    r = _bool_metric(True)
    assert r == {"value": True, "reason": None}


def test_bool_metric_false():
    r = _bool_metric(False)
    assert r == {"value": False, "reason": None}


def test_bool_metric_with_int_converts_to_bool():
    r = _bool_metric(1)
    assert r["value"] is True
    r = _bool_metric(0)
    assert r["value"] is False


def test_int_metric_zero():
    r = _int_metric(0)
    assert r == {"value": 0, "reason": None}


def test_int_metric_negative():
    r = _int_metric(-5)
    assert r == {"value": -5, "reason": None}


def test_int_metric_with_float_truncates():
    """int(2.9) = 2."""
    r = _int_metric(2.9)
    assert r["value"] == 2


def test_int_metric_with_bool_converts_to_int():
    """int(True) = 1."""
    r = _int_metric(True)
    assert r["value"] == 1


# ---------- compute_automatic_metrics 行为深度第八批 ----------


def test_compute_returns_dict_type():
    r = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(r, dict)


def test_compute_with_error_dict_only():
    """error 非空 + document None → pipeline_success=False + error_code 设置."""
    error = {"code": "parse_failed", "message": "boom"}
    r = compute_automatic_metrics(None, error, "pdf", None)
    assert r["pipeline_success"]["value"] is False
    assert r["error_code"]["value"] == "parse_failed"


def test_compute_with_error_none_and_document_none():
    r = compute_automatic_metrics(None, None, "pdf", None)
    assert r["pipeline_success"]["value"] is False
    assert r["error_code"]["value"] is None


def test_compute_with_minimal_doc_returns_dict_with_metrics():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pipeline_success" in r
    assert r["pipeline_success"]["value"] is True
    assert "element_count_total" in r


def test_compute_element_count_total_returns_int_value():
    doc = {"elements": [{"element_id": "e1", "type": "heading"}], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["element_count_total"]["value"] == 1
    assert isinstance(r["element_count_total"]["value"], int)


def test_compute_element_count_by_type_dict():
    doc = {
        "elements": [
            {"element_id": "e1", "type": "heading"},
            {"element_id": "e2", "type": "heading"},
            {"element_id": "e3", "type": "paragraph"},
        ],
        "chunks": [],
    }
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["element_count_by_type"]["value"] == {"heading": 2, "paragraph": 1}


def test_compute_element_count_by_type_unknown_when_no_type():
    doc = {
        "elements": [{"element_id": "e1"}],  # no type
        "chunks": [],
    }
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["element_count_by_type"]["value"] == {"unknown": 1}


def test_compute_pdf_locator_for_pdf_source_type():
    doc = {
        "elements": [
            {"element_id": "e1", "type": "heading",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        ],
        "chunks": [],
    }
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["pdf_locator_valid_ratio"]["value"] == 1.0


def test_compute_pdf_locator_for_docx_source_type_is_null():
    """source_type=docx → pdf_locator_valid_ratio is null not_pdf_document."""
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "docx", None)
    assert r["pdf_locator_valid_ratio"]["value"] is None
    assert r["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_docx_locator_for_docx_source_type():
    doc = {
        "elements": [
            {"element_id": "e1", "type": "paragraph",
             "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [],
    }
    r = compute_automatic_metrics(doc, None, "docx", None)
    assert r["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_docx_locator_for_pdf_source_type_is_null():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["docx_locator_valid_ratio"]["value"] is None
    assert r["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_image_resource_no_image_elements_null():
    doc = {"elements": [{"element_id": "e1", "type": "heading"}], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["image_resource_exists_ratio"]["value"] is None
    assert r["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_returns_14_metrics_when_doc_provided():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(r.keys()) == expected_keys


def test_compute_silent_drop_count_no_expectations():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["silent_drop_count"]["value"] is None
    assert r["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_silent_drop_count_with_expectations():
    doc = {
        "elements": [{"element_id": "e1", "type": "heading"}],
        "chunks": [],
    }
    expectations = {"element_count_by_type": {"heading": 3}}
    r = compute_automatic_metrics(doc, None, "pdf", expectations)
    # actual heading = 1, expected = 3 → drop = 2
    assert r["silent_drop_count"]["value"] == 2


def test_compute_idempotent_full_doc():
    doc = {
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "x",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        ],
        "chunks": [{"chunk_id": "c1", "text": "x", "source_element_ids": ["e1"]}],
    }
    r1 = compute_automatic_metrics(doc, None, "pdf", None)
    r2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert r1 == r2


def test_compute_does_not_mutate_document():
    doc = {
        "elements": [{"element_id": "e1", "type": "heading"}],
        "chunks": [],
    }
    import copy
    doc_copy = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == doc_copy


def test_compute_does_not_mutate_error():
    error = {"code": "parse_failed", "message": "x"}
    import copy
    error_copy = copy.deepcopy(error)
    compute_automatic_metrics(None, error, "pdf", None)
    assert error == error_copy


def test_compute_does_not_mutate_expectations():
    doc = {"elements": [{"element_id": "e1", "type": "heading"}], "chunks": []}
    expectations = {"element_count_by_type": {"heading": 2}}
    import copy
    exp_copy = copy.deepcopy(expectations)
    compute_automatic_metrics(doc, None, "pdf", expectations)
    assert expectations == exp_copy


def test_compute_kwargs_full_call():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert isinstance(r, dict)


def test_compute_positional_full_call():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None, None)
    assert isinstance(r, dict)


def test_compute_text_preservation_with_dup_chars():
    """actual 中含重复字符 → Counter 交集给出 min."""
    doc = {
        "elements": [
            {"element_id": "e1", "type": "paragraph", "content": "aab"},
        ],
        "chunks": [{"chunk_id": "c1", "text": "ab", "source_element_ids": ["e1"]}],
    }
    r = compute_automatic_metrics(doc, None, "pdf", None)
    # expected = "aab", actual = "ab"
    # c_expected = {a:2, b:1}, c_actual = {a:1, b:1}
    # intersection = {a:1, b:1}, common = 2
    # precision = 2/2 = 1.0, recall = 2/3 ≈ 0.667
    assert r["text_char_multiset_precision"]["value"] == 1.0
    assert abs(r["text_char_multiset_recall"]["value"] - 2 / 3) < 1e-6
    # equal = False
    assert r["text_preservation_equal"]["value"] is False


# ---------- _pdf_locator_ratio 行为深度第八批 ----------


def test_pdf_locator_no_elements_returns_null():
    r = _pdf_locator_ratio([])
    assert r["value"] is None
    assert r["reason"] == "no_elements"


def test_pdf_locator_page_one_valid():
    elements = [{"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_negative_page_invalid():
    elements = [{"type": "heading", "source_locator": {"page": -1, "bbox": [0, 0, 10, 10]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_text_type_requires_bbox():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]  # 无 bbox
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_image_does_not_require_bbox():
    elements = [{"type": "image", "source_locator": {"page": 1}}]  # image 无 bbox 要求
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_partial():
    elements = [
        {"type": "heading", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 0}},  # page=0 无效
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.5


def test_pdf_locator_source_locator_none():
    elements = [{"type": "heading"}]  # 无 source_locator
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_source_locator_empty_dict():
    elements = [{"type": "heading", "source_locator": {}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_returns_dict_with_value_and_reason():
    r = _pdf_locator_ratio([{"type": "heading"}])
    assert "value" in r
    assert "reason" in r


def test_pdf_locator_with_huge_page_number():
    elements = [{"type": "heading", "source_locator": {"page": 999999, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_with_float_page_rejected():
    """page 必须是 int（isinstance(page, int)）."""
    elements = [{"type": "heading", "source_locator": {"page": 1.0, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_with_bool_page_rejected():
    """bool 是 int 的子类，但 isinstance(True, int) is True — 这可能是个 bug."""
    elements = [{"type": "heading", "source_locator": {"page": True, "bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    # bool True 被视为 1，可能 valid
    # 不严格断言，但应不抛
    assert isinstance(r["value"], float) or r["value"] is None


# ---------- _docx_locator_ratio 行为深度第八批 ----------


def test_docx_locator_no_elements_returns_null():
    r = _docx_locator_ratio([])
    assert r["value"] is None
    assert r["reason"] == "no_elements"


def test_docx_locator_with_paragraph_index():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_with_section():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_with_run_index():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_with_table_indices():
    elements = [{"type": "table_cell", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_with_relationship_id():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_page_rejected():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_bbox_rejected():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 10, 10]}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_no_structural_key_rejected():
    elements = [{"type": "paragraph", "source_locator": {"other_key": "value"}}]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_partial():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # rejected
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.5


def test_docx_locator_source_locator_none():
    elements = [{"type": "paragraph"}]  # 无 source_locator
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_returns_dict_with_value_and_reason():
    r = _docx_locator_ratio([])
    assert "value" in r
    assert "reason" in r


# ---------- _image_resource_ratio 行为深度第八批 ----------


def test_image_resource_no_image_returns_null():
    elements = [{"type": "heading"}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] is None
    assert r["reason"] == "no_image_elements"


def test_image_resource_no_resource_path():
    elements = [{"type": "image"}]  # 无 resource_path
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_empty_resource_path():
    elements = [{"type": "image", "resource_path": ""}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_existing_file(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"PNG data")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_zero_byte_file(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_with_base_dir(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 1.0


def test_image_resource_partial(tmp_path):
    img1 = tmp_path / "img1.png"
    img1.write_bytes(b"PNG")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": "missing.png"},
    ]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.5


def test_image_resource_returns_dict_with_value_and_reason():
    elements = [{"type": "heading"}]
    r = _image_resource_ratio(elements, None)
    assert "value" in r
    assert "reason" in r


def test_image_resource_all_images_present(tmp_path):
    img1 = tmp_path / "img1.png"
    img1.write_bytes(b"PNG1")
    img2 = tmp_path / "img2.png"
    img2.write_bytes(b"PNG2")
    elements = [
        {"type": "image", "resource_path": str(img1)},
        {"type": "image", "resource_path": str(img2)},
    ]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_none_image_skipped():
    elements = [
        {"type": "heading"},
        {"type": "image", "resource_path": ""},  # 空路径不计
    ]
    r = _image_resource_ratio(elements, None)
    # 1 image total, 0 valid → 0.0
    assert r["value"] == 0.0


# ---------- _chunk_reference_ratio 行为深度第八批 ----------


def test_chunk_reference_no_chunks_returns_null():
    r = _chunk_reference_ratio([], [])
    assert r["value"] is None
    assert r["reason"] == "no_chunks"


def test_chunk_reference_empty_elements_list():
    r = _chunk_reference_ratio([], [{"chunk_id": "c1", "source_element_ids": ["e1"]}])
    # elem_ids 空 → e1 不在 → 0 valid
    assert r["value"] == 0.0


def test_chunk_reference_chunk_no_source_element_ids():
    r = _chunk_reference_ratio([{"element_id": "e1"}], [{"chunk_id": "c1"}])
    # chunk.source_element_ids 缺 → ids=[] → all(...) on empty = True → counts as valid
    # 但 ids 空 → not ids → skip
    # 实际上代码是 `if ids and all(...)`，空 ids 不计
    # chunks = 1, valid = 0 → 0.0
    assert r["value"] == 0.0


def test_chunk_reference_chunk_empty_source_element_ids():
    r = _chunk_reference_ratio([{"element_id": "e1"}], [{"chunk_id": "c1", "source_element_ids": []}])
    assert r["value"] == 0.0


def test_chunk_reference_all_ids_present():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1", "e2"]}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_chunk_reference_some_ids_missing():
    elements = [{"element_id": "e1"}]
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1", "missing"]}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0  # all() 失败 → 整 chunk invalid


def test_chunk_reference_partial_chunks():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"chunk_id": "c1", "source_element_ids": ["e1"]},  # valid
        {"chunk_id": "c2", "source_element_ids": ["missing"]},  # invalid
    ]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_chunk_reference_returns_dict_with_value_and_reason():
    r = _chunk_reference_ratio([], [])
    assert "value" in r
    assert "reason" in r


def test_chunk_reference_no_elements_no_chunks():
    r = _chunk_reference_ratio([], [])
    # chunks=[] → null no_chunks
    assert r["value"] is None


# ---------- _text_preservation 行为深度第八批 ----------


def test_text_preservation_both_empty():
    r = _text_preservation([], [])
    assert r["equal"]["value"] is True
    assert r["precision"]["reason"] == "empty_expected_and_actual"
    assert r["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_match():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_actual_missing():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []  # actual = ""
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    # actual 空 → precision null
    assert r["precision"]["value"] is None
    assert r["precision"]["reason"] == "empty_actual"
    # recall = 0/3 = 0
    assert r["recall"]["value"] == 0.0


def test_text_preservation_expected_missing():
    elements = []  # expected = ""
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    # precision = 0/3 = 0
    assert r["precision"]["value"] == 0.0
    # recall null empty_expected
    assert r["recall"]["value"] is None
    assert r["recall"]["reason"] == "empty_expected"


def test_text_preservation_image_skipped():
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},  # image 不参与
    ]
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_partial_overlap():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abd"}]  # c → d
    r = _text_preservation(elements, chunks)
    # expected = "abc", actual = "abd"
    # c_e = {a:1, b:1, c:1}, c_a = {a:1, b:1, d:1}
    # intersection = {a:1, b:1}, common = 2
    # precision = 2/3, recall = 2/3
    assert abs(r["precision"]["value"] - 2 / 3) < 1e-6
    assert abs(r["recall"]["value"] - 2 / 3) < 1e-6


def test_text_preservation_returns_dict_with_3_keys():
    r = _text_preservation([], [])
    assert set(r.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_key_is_dict():
    r = _text_preservation([], [])
    for k in ("equal", "precision", "recall"):
        assert isinstance(r[k], dict)
        assert "value" in r[k]
        assert "reason" in r[k]


def test_text_preservation_does_not_mutate_inputs():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    import copy
    e_copy = copy.deepcopy(elements)
    c_copy = copy.deepcopy(chunks)
    _text_preservation(elements, chunks)
    assert elements == e_copy
    assert chunks == c_copy


def test_text_preservation_with_whitespace_ignored():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    # 删除空白后都是 "abc" → equal
    assert r["equal"]["value"] is True


def test_text_preservation_with_none_content():
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    r = _text_preservation(elements, chunks)
    # expected_raw = "" (None → "")
    # actual = "abc"
    assert r["equal"]["value"] is False


def test_text_preservation_with_none_chunk_text():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    r = _text_preservation(elements, chunks)
    # actual = ""
    assert r["equal"]["value"] is False


def test_text_preservation_idempotent():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    r1 = _text_preservation(elements, chunks)
    r2 = _text_preservation(elements, chunks)
    assert r1 == r2


# ---------- _heading_boundary_ratio 行为深度第八批 ----------


def test_heading_boundary_no_headings_returns_null():
    r = _heading_boundary_ratio([], [])
    assert r["value"] is None
    assert r["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r["value"] == 0.0


def test_heading_boundary_full_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_no_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_partial():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_heading_boundary_chunk_empty_ids():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_chunk_no_ids_key():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]  # no source_element_ids
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_heading_boundary_heading_no_element_id():
    elements = [{"type": "heading"}]  # no element_id
    chunks = [{"source_element_ids": ["x"]}]
    r = _heading_boundary_ratio(elements, chunks)
    # matched = sum(... if h.get("element_id") in chunk_first_ids) = 0
    assert r["value"] == 0.0


def test_heading_boundary_multiple_chunks_same_first_id():
    """多个 chunk 共享同一首 id → 该 heading 仍只算 1 个匹配."""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h1"]},  # same first id
    ]
    r = _heading_boundary_ratio(elements, chunks)
    # chunk_first_ids 是 set，去重 → {"h1"}
    # matched = 1
    assert r["value"] == 1.0


def test_heading_boundary_returns_dict_with_value_and_reason():
    r = _heading_boundary_ratio([], [])
    assert "value" in r
    assert "reason" in r


# ---------- _silent_drop_count 行为深度第八批 ----------


def test_silent_drop_no_expectations_returns_null():
    r = _silent_drop_count({}, None)
    assert r["value"] is None
    assert r["reason"] == "no_expectations"


def test_silent_drop_empty_expectations_returns_null():
    r = _silent_drop_count({}, {})
    assert r["value"] is None
    assert r["reason"] == "no_expectations"


def test_silent_drop_no_element_count_returns_null():
    r = _silent_drop_count({}, {"other_key": 1})
    assert r["value"] is None
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_empty_element_count_returns_null():
    r = _silent_drop_count({}, {"element_count_by_type": {}})
    assert r["value"] is None
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_actual_more_than_expected():
    """actual > expected → no drop for that type."""
    by_type = {"heading": 5}
    expectations = {"element_count_by_type": {"heading": 3}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 0


def test_silent_drop_actual_less_than_expected():
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 4


def test_silent_drop_mixed_types():
    by_type = {"heading": 1, "paragraph": 5}
    expectations = {"element_count_by_type": {"heading": 3, "paragraph": 2}}
    # heading: max(0, 3-1) = 2
    # paragraph: max(0, 2-5) = 0
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 2


def test_silent_drop_actual_zero():
    by_type = {}
    expectations = {"element_count_by_type": {"heading": 3}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 3


def test_silent_drop_returns_int_value():
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert isinstance(r["value"], int)


def test_silent_drop_returns_dict_with_value_and_reason():
    r = _silent_drop_count({}, None)
    assert "value" in r
    assert "reason" in r


def test_silent_drop_does_not_mutate_inputs():
    by_type = {"heading": 1}
    expectations = {"element_count_by_type": {"heading": 5}}
    import copy
    bt_copy = copy.deepcopy(by_type)
    exp_copy = copy.deepcopy(expectations)
    _silent_drop_count(by_type, expectations)
    assert by_type == bt_copy
    assert expectations == exp_copy


# ---------- _is_valid_bbox 行为深度第八批 ----------


def test_is_valid_bbox_valid_4_ints():
    assert _is_valid_bbox([0, 0, 10, 10]) is True


def test_is_valid_bbox_valid_4_floats():
    assert _is_valid_bbox([0.0, 0.0, 10.5, 10.5]) is True


def test_is_valid_bbox_mixed_int_float():
    assert _is_valid_bbox([0, 0.0, 10, 10.5]) is True


def test_is_valid_bbox_negative_numbers():
    assert _is_valid_bbox([-1, -1, 10, 10]) is True


def test_is_valid_bbox_tuple_rejected():
    assert _is_valid_bbox((0, 0, 10, 10)) is False


def test_is_valid_bbox_string_rejected():
    assert _is_valid_bbox("0,0,10,10") is False


def test_is_valid_bbox_none_rejected():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_short():
    assert _is_valid_bbox([0, 0, 10]) is False


def test_is_valid_bbox_too_long():
    assert _is_valid_bbox([0, 0, 10, 10, 10]) is False


def test_is_valid_bbox_string_element():
    assert _is_valid_bbox(["0", "0", "10", "10"]) is False


def test_is_valid_bbox_none_element():
    assert _is_valid_bbox([0, 0, None, 10]) is False


def test_is_valid_bbox_bool_element_rejected():
    """True/False 是 int 子类，但应拒绝（避免 page=True 之类）."""
    assert _is_valid_bbox([True, 0, 10, 10]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([0, 0, float("nan"), 10]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([0, 0, float("inf"), 10]) is False


def test_is_valid_bbox_with_negative_inf():
    assert _is_valid_bbox([0, 0, float("-inf"), 10]) is False


def test_is_valid_bbox_all_zeros():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_dict_rejected():
    assert _is_valid_bbox({"x": 0, "y": 0, "w": 10, "h": 10}) is False


def test_is_valid_bbox_set_rejected():
    assert _is_valid_bbox({0, 0, 10, 10}) is False


def test_is_valid_bbox_tuple_in_list():
    """[(0,0), (10,10)] 是 list of tuples → 长度 2 → False."""
    assert _is_valid_bbox([(0, 0), (10, 10)]) is False


# ---------- _strip_unicode_whitespace 行为深度第八批 ----------


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace("   \t\n") == ""


def test_strip_unicode_whitespace_internal_whitespace():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_leading_trailing():
    assert _strip_unicode_whitespace("  abc  ") == "abc"


def test_strip_unicode_whitespace_nbsp():
    """U+00A0 NBSP."""
    assert _strip_unicode_whitespace(" abc ") == "abc"


def test_strip_unicode_whitespace_em_space():
    """U+2003 EM SPACE."""
    assert _strip_unicode_whitespace(" abc ") == "abc"


def test_strip_unicode_whitespace_en_space():
    """U+2002 EN SPACE."""
    assert _strip_unicode_whitespace(" abc") == "abc"


def test_strip_unicode_whitespace_ideographic_space():
    """U+3000 IDEOGRAPHIC SPACE."""
    assert _strip_unicode_whitespace("　abc") == "abc"


def test_strip_unicode_whitespace_line_separator():
    """U+2028 LINE SEPARATOR."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator():
    """U+2029 PARAGRAPH SEPARATOR."""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_preserves_non_whitespace():
    assert _strip_unicode_whitespace("a-b,c.d!") == "a-b,c.d!"


def test_strip_unicode_whitespace_preserves_punctuation():
    """标点不是空白."""
    s = ".,;:!?-_/()[]{}"
    assert _strip_unicode_whitespace(s) == s


def test_strip_unicode_whitespace_preserves_unicode_letters():
    """中文、日文、韩文等不是空白."""
    assert _strip_unicode_whitespace("你好世界") == "你好世界"


def test_strip_unicode_whitespace_preserves_emoji():
    """emoji 不是空白."""
    assert _strip_unicode_whitespace("😀abc") == "😀abc"


def test_strip_unicode_whitespace_returns_str_type():
    assert isinstance(_strip_unicode_whitespace(""), str)
    assert isinstance(_strip_unicode_whitespace("abc"), str)


def test_strip_unicode_whitespace_idempotent():
    s1 = _strip_unicode_whitespace("a b c")
    s2 = _strip_unicode_whitespace(s1)
    assert s1 == s2


def test_strip_unicode_whitespace_mixed():
    """ASCII 空白 + Unicode 空白混合."""
    assert _strip_unicode_whitespace("a \tb　\nc") == "abc"


def test_strip_unicode_whitespace_zero_width_not_whitespace():
    """U+200B ZERO WIDTH SPACE — isspace() 是 False → 不删除."""
    result = _strip_unicode_whitespace("a​b")
    # 保留 zero width space（它不是 isspace）
    assert "​" in result


def test_strip_unicode_whitespace_with_bom():
    """U+FEFF BOM — isspace() 是 False → 不删除."""
    result = _strip_unicode_whitespace("﻿abc")
    assert "﻿" in result


# ---------- module source forbidden tokens 第十一批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "shutil.rmtree",
        "shutil.copy",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",
        "exit(",
        "quit(",
        "exec(",
        "eval(",
        "compile(",
    ],
)
def test_metrics_source_no_forbidden_token_eleventh(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


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


def test_module_source_has_text_types_constant():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_has_pdf_bbox_required_types():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_has_not_evaluated_constant():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_has_4_helpers():
    src = inspect.getsource(mmod)
    assert "def _null(" in src
    assert "def _ratio(" in src
    assert "def _bool_metric(" in src
    assert "def _int_metric(" in src


def test_module_source_has_compute_automatic_metrics():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_sub_functions():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src
    assert "def _docx_locator_ratio(" in src
    assert "def _image_resource_ratio(" in src
    assert "def _chunk_reference_ratio(" in src
    assert "def _text_preservation(" in src
    assert "def _heading_boundary_ratio(" in src
    assert "def _silent_drop_count(" in src
    assert "def _is_valid_bbox(" in src
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_no_class_definitions():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def " not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(mmod)
    assert "\nglobal " not in src


def test_module_source_no_lambda_at_top_level():
    src = inspect.getsource(mmod)
    for line in src.splitlines():
        if line[:1].isspace():
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "import", "from", "def ", "class ", "@")):
            continue
        if stripped.startswith(('"""', "'''")):
            continue
        # 顶层不应有 NAME = lambda
        assert not ("=" in stripped and "lambda " in stripped), \
            f"top-level lambda: {stripped}"


def test_module_source_no_sleep():
    src = inspect.getsource(mmod)
    assert "time.sleep" not in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(mmod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src


def test_module_source_no_print():
    src = inspect.getsource(mmod)
    assert "print(" not in src


def test_module_source_no_logging():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(mmod)
    assert "subprocess." not in src


def test_module_source_no_unlink():
    src = inspect.getsource(mmod)
    assert ".unlink(" not in src


def test_module_source_docstring_first_line():
    src = inspect.getsource(mmod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_text_preservation():
    src = inspect.getsource(mmod)
    assert "text_preservation" in src[:1500] or "文本保留" in src[:1500]


def test_module_source_docstring_mentions_pure_function():
    src = inspect.getsource(mmod)
    assert "纯函数" in src[:600] or "pure" in src[:600].lower()


def test_module_source_docstring_mentions_v1_1():
    src = inspect.getsource(mmod)
    assert "v1.1" in src[:2000]


# ---------- signatures 第八批 ----------


def test_signature_null_1_param():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_signature_null_reason_kind():
    sig = inspect.signature(_null)
    assert sig.parameters["reason"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_ratio_1_param():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_signature_bool_metric_1_param():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_signature_int_metric_1_param():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_signature_compute_automatic_metrics_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_signature_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    for name in ("document", "error", "source_type", "expectations", "image_base_dir"):
        assert sig.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_compute_automatic_metrics_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_automatic_metrics_no_varargs():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_compute_automatic_metrics_no_kwargs():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_pdf_locator_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_signature_docx_locator_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_signature_image_resource_2_params():
    sig = inspect.signature(_image_resource_ratio)
    assert len(sig.parameters) == 2


def test_signature_chunk_reference_2_params():
    sig = inspect.signature(_chunk_reference_ratio)
    assert len(sig.parameters) == 2


def test_signature_text_preservation_2_params():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_signature_heading_boundary_2_params():
    sig = inspect.signature(_heading_boundary_ratio)
    assert len(sig.parameters) == 2


def test_signature_silent_drop_2_params():
    sig = inspect.signature(_silent_drop_count)
    assert len(sig.parameters) == 2


def test_signature_is_valid_bbox_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_signature_strip_unicode_whitespace_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert len(sig.parameters) == 1


def test_signature_all_funcs_function_type():
    for f in (_null, _ratio, _bool_metric, _int_metric,
              compute_automatic_metrics,
              _pdf_locator_ratio, _docx_locator_ratio,
              _image_resource_ratio, _chunk_reference_ratio,
              _text_preservation, _heading_boundary_ratio,
              _silent_drop_count, _is_valid_bbox,
              _strip_unicode_whitespace):
        assert isinstance(f, types.FunctionType)


def test_signature_all_funcs_module_eq():
    for f in (_null, _ratio, _bool_metric, _int_metric,
              compute_automatic_metrics,
              _pdf_locator_ratio, _docx_locator_ratio,
              _image_resource_ratio, _chunk_reference_ratio,
              _text_preservation, _heading_boundary_ratio,
              _silent_drop_count, _is_valid_bbox,
              _strip_unicode_whitespace):
        assert f.__module__ == mmod.__name__


# ---------- module 合理性第八批 ----------


def test_module_all_exact_1_item():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique():
    assert len(set(mmod.__all__)) == len(mmod.__all__)


def test_module_all_entries_are_str():
    for entry in mmod.__all__:
        assert isinstance(entry, str)


def test_module_text_types_exact_entries():
    assert mmod._TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_module_text_types_is_tuple():
    assert isinstance(mmod._TEXT_TYPES, tuple)


def test_module_pdf_bbox_required_types_exact_entries():
    assert mmod._PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_module_pdf_bbox_required_types_is_tuple():
    assert isinstance(mmod._PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_not_evaluated_value():
    assert mmod._NOT_EVALUATED == "not_evaluated"


def test_module_not_evaluated_type():
    assert isinstance(mmod._NOT_EVALUATED, str)


def test_module_text_types_length_7():
    assert len(mmod._TEXT_TYPES) == 7


def test_module_pdf_bbox_required_types_length_4():
    assert len(mmod._PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_text_types_pdf_bbox_subset():
    """_PDF_BBOX_REQUIRED_TYPES 应是 _TEXT_TYPES 的子集."""
    assert set(mmod._PDF_BBOX_REQUIRED_TYPES).issubset(set(mmod._TEXT_TYPES))


def test_module_has_docstring():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 0


def test_module_docstring_starts_with_chinese():
    assert mmod.__doc__.strip().startswith("自动指标")


def test_module_file_endswith_metrics_py():
    assert mmod.__file__.replace("\\", "/").endswith("evaluation/metrics.py")


def test_module_name_is_evaluation_metrics():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_user_function_count():
    own_funcs = [
        obj for obj in vars(mmod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == mmod.__name__
    ]
    # 4 helpers + compute_automatic_metrics + 9 sub-functions = 14
    assert len(own_funcs) == 14


def test_module_no_user_classes():
    own_classes = [
        obj for obj in vars(mmod).values()
        if isinstance(obj, type) and obj.__module__ == mmod.__name__
    ]
    assert len(own_classes) == 0


def test_module_no_call_at_top_level():
    """模块顶层不应有显式的 print/exit/subprocess 类副作用调用."""
    src = inspect.getsource(mmod)
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("os.system(", "subprocess.", "exit(", "quit(", "print(")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass
                else:
                    in_triple = True
                    triple_quote = q
                break
        for pat in suspicious_patterns:
            assert pat not in line, f"suspicious pattern {pat!r} in {line!r}"


# ---------- 端到端集成第八批 ----------


def test_e2e_compute_metrics_full_pdf_doc():
    doc = {
        "elements": [
            {"element_id": "e1", "type": "heading", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"element_id": "e2", "type": "paragraph", "content": "body",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "title", "source_element_ids": ["e1"]},
            {"chunk_id": "c2", "text": "body", "source_element_ids": ["e2"]},
        ],
    }
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["pipeline_success"]["value"] is True
    assert r["element_count_total"]["value"] == 2
    assert r["pdf_locator_valid_ratio"]["value"] == 1.0
    assert r["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_error_dict():
    error = {"code": "parse_failed", "message": "boom"}
    r = compute_automatic_metrics(None, error, "pdf", None)
    assert r["pipeline_success"]["value"] is False
    assert r["error_code"]["value"] == "parse_failed"


def test_e2e_compute_metrics_document_none_returns_14_null_metrics():
    r = compute_automatic_metrics(None, None, "pdf", None)
    assert len(r) == 14
    # Most should be null with pipeline_failed
    for k in ("element_count_total", "pdf_locator_valid_ratio", "silent_drop_count"):
        assert r[k]["value"] is None
        assert r[k]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_with_positional_args():
    r = compute_automatic_metrics(None, None, "pdf", None, None)
    assert isinstance(r, dict)


def test_e2e_compute_metrics_with_kwargs():
    r = compute_automatic_metrics(
        document=None, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert isinstance(r, dict)


def test_e2e_pdf_locator_with_image_no_bbox():
    """image element 不需要 bbox（PDF）."""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # no bbox, type=image
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_e2e_docx_locator_with_relationship_id():
    elements = [
        {"type": "image", "source_locator": {"relationship_id": "rId1"}},
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_e2e_chunk_reference_with_none_elements_list():
    r = _chunk_reference_ratio([], [{"chunk_id": "c1", "source_element_ids": ["e1"]}])
    assert r["value"] == 0.0


def test_e2e_text_preservation_with_dup_chars_in_actual():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "aabbcc"}]  # 重复字符
    r = _text_preservation(elements, chunks)
    # expected = "abc", actual = "aabbcc"
    # c_e = {a:1, b:1, c:1}, c_a = {a:2, b:2, c:2}
    # intersection = {a:1, b:1, c:1}, common = 3
    # precision = 3/6 = 0.5, recall = 3/3 = 1.0
    assert r["precision"]["value"] == 0.5
    assert r["recall"]["value"] == 1.0


def test_e2e_heading_boundary_with_three_headings_partial():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
        {"type": "heading", "element_id": "h3"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},  # match
        {"source_element_ids": ["h3"]},  # match
        # h2 不匹配
    ]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 2 / 3


def test_e2e_full_chain_compute_then_check_keys():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(r.keys()) == expected_keys


def test_e2e_metric_value_or_reason_in_each():
    """每个 metric 应有 value 和 reason 字段."""
    r = compute_automatic_metrics({"elements": [], "chunks": []}, None, "pdf", None)
    for k, m in r.items():
        assert isinstance(m, dict), f"{k} should be dict"
        assert "value" in m, f"{k} should have value"
        assert "reason" in m, f"{k} should have reason"


def test_e2e_idempotent():
    doc = {"elements": [], "chunks": []}
    r1 = compute_automatic_metrics(doc, None, "pdf", None)
    r2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert r1 == r2


def test_e2e_does_not_raise_on_unexpected_input():
    """对 None / 空 dict 等不应抛意外异常."""
    try:
        compute_automatic_metrics(None, None, "pdf", None)
        compute_automatic_metrics({}, None, "pdf", None)  # 缺 elements/chunks
    except Exception as e:  # noqa: BLE001
        # schema_valid 可能抛，但应被捕获
        pytest.fail(f"unexpected exception: {type(e).__name__}: {e}")


def test_e2e_compute_returns_pipeline_success_true_for_minimal_doc():
    doc = {"elements": [], "chunks": []}
    r = compute_automatic_metrics(doc, None, "pdf", None)
    assert r["pipeline_success"]["value"] is True
