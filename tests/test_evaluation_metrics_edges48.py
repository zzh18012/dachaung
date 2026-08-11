"""evaluation/metrics.py 第五十轮 edges 测试（Round 470）。

补强 edges47 未触及的角度：
- _null / _ratio / _bool_metric / _int_metric 构造子第二十二批（更多边界）
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十二批
- _strip_unicode_whitespace 第二十二批
- compute_automatic_metrics 第二十二批（更多 corner case）
- _pdf_locator_ratio 第二十二批
- _docx_locator_ratio 第二十二批
- _is_valid_bbox 第二十二批
- _image_resource_ratio 第二十二批
- _chunk_reference_ratio 第二十二批
- _text_preservation 第二十二批
- _heading_boundary_ratio 第二十二批
- _silent_drop_count 第二十二批
- module source forbidden tokens 第三十七批
- module source 字符串精确补强第三十三批
- signatures 第三十三批
- module 合理性第三十三批
- 端到端集成第三十三批
"""

from __future__ import annotations

import inspect
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.metrics import (
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
from evaluation import metrics as mmod


# ---------- 构造子第二十二批 ----------


def test_null_with_unicode_reason_batch22():
    err = _null("失败原因")
    assert err == {"value": None, "reason": "失败原因"}


def test_null_with_empty_reason_batch22():
    err = _null("")
    assert err == {"value": None, "reason": ""}


def test_null_with_long_reason_batch22():
    long = "x" * 1000
    err = _null(long)
    assert err["reason"] == long


def test_ratio_negative_value_preserved_batch22():
    """_ratio 不做范围校验（用户责任）。"""
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_ratio_large_value_preserved_batch22():
    r = _ratio(100.0)
    assert r["value"] == 100.0


def test_ratio_int_input_converted_to_float_batch22():
    r = _ratio(1)
    assert r["value"] == 1.0
    assert isinstance(r["value"], float)


def test_ratio_inf_input_batch22():
    """inf 不被拒（float() 接受 inf）。"""
    import math
    r = _ratio(math.inf)
    assert math.isinf(r["value"])


def test_ratio_nan_input_batch22():
    import math
    r = _ratio(math.nan)
    assert math.isnan(r["value"])


def test_bool_metric_with_int_input_batch22():
    """int 输入被 bool()。"""
    b = _bool_metric(0)
    assert b["value"] is False
    b2 = _bool_metric(1)
    assert b2["value"] is True


def test_bool_metric_with_string_input_batch22():
    """非空 str → True。"""
    b = _bool_metric("yes")
    assert b["value"] is True
    b2 = _bool_metric("")
    assert b2["value"] is False


def test_int_metric_with_negative_batch22():
    i = _int_metric(-5)
    assert i["value"] == -5


def test_int_metric_with_float_input_batch22():
    """float 输入被 int()（截断）。"""
    i = _int_metric(3.99)
    assert i["value"] == 3


def test_int_metric_with_string_digits_batch22():
    i = _int_metric("0")  # type: ignore
    assert i["value"] == 0


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第二十二批 ----------


def test_text_types_is_tuple_batch22():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_contains_paragraph_batch22():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_contains_heading_batch22():
    assert "heading" in _TEXT_TYPES


def test_text_types_excludes_image_batch22():
    assert "image" not in _TEXT_TYPES


def test_text_types_count_batch22():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_is_tuple_batch22():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_count_4_batch22():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_subset_of_text_types_batch22():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_excludes_table_batch22():
    """table 在 _TEXT_TYPES 但不在 _PDF_BBOX_REQUIRED_TYPES。"""
    assert "table" in _TEXT_TYPES
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


# ---------- _strip_unicode_whitespace 第二十二批 ----------


def test_strip_unicode_whitespace_pure_string_batch22():
    """纯字符串无变化。"""
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_single_char_batch22():
    assert _strip_unicode_whitespace("a") == "a"


def test_strip_unicode_whitespace_digit_batch22():
    assert _strip_unicode_whitespace("5") == "5"


def test_strip_unicode_whitespace_only_whitespace_batch22():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_whitespace_mixed_batch22():
    assert _strip_unicode_whitespace("  a  b  c  ") == "abc"


def test_strip_unicode_whitespace_unicode_chars_batch22():
    """中文字符保留。"""
    assert _strip_unicode_whitespace("  你好  世界  ") == "你好世界"


def test_strip_unicode_whitespace_newline_tab_batch22():
    assert _strip_unicode_whitespace("\ta\nb\nc") == "abc"


# ---------- compute_automatic_metrics 第二十二批 ----------


def test_compute_metrics_no_document_returns_pipeline_failed_for_all_batch22():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "PARSE_FAIL", "message": "broken"},
        source_type="pdf",
        expectations=None,
    )
    # pipeline_success = False
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "PARSE_FAIL"
    # 其他 metric 应是 null + pipeline_failed
    for k in ("element_count_total", "schema_valid"):
        assert out[k]["reason"] in ("pipeline_failed", None)


def test_compute_metrics_error_none_document_some_returns_pipeline_failed_batch22():
    out = compute_automatic_metrics(
        document=None,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_metrics_minimal_doc_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 0


def test_compute_metrics_returns_dict_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert isinstance(out, dict)


def test_compute_metrics_pdf_source_type_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    # pdf_locator_valid_ratio 不应是 not_pdf_document
    assert out["pdf_locator_valid_ratio"]["reason"] != "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_docx_source_type_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] != "not_docx_document"


def test_compute_metrics_element_count_total_with_elements_batch22():
    out = compute_automatic_metrics(
        document={"elements": [{"type": "paragraph"}, {"type": "heading"}], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_total"]["value"] == 2


def test_compute_metrics_element_count_by_type_batch22():
    out = compute_automatic_metrics(
        document={"elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


def test_compute_metrics_element_count_by_type_with_unknown_type_batch22():
    out = compute_automatic_metrics(
        document={"elements": [{"type": "weird"}], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_by_type"]["value"] == {"weird": 1}


def test_compute_metrics_element_count_by_type_empty_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_by_type"]["value"] == {}


def test_compute_metrics_element_count_by_type_no_type_key_batch22():
    """element 缺 type 字段 → 计入 'unknown'。"""
    out = compute_automatic_metrics(
        document={"elements": [{}], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert "unknown" in out["element_count_by_type"]["value"]


# ---------- _pdf_locator_ratio 第二十二批 ----------


def test_pdf_locator_ratio_no_elements_batch22():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_all_valid_page_batch22():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_zero_invalid_batch22():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_negative_page_invalid_batch22():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_page_key_batch22():
    elements = [{"type": "image", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_locator_key_batch22():
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_needs_bbox_batch22():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]  # 无 bbox
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_bbox_batch22():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _docx_locator_ratio 第二十二批 ----------


def test_docx_locator_ratio_no_elements_batch22():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_with_paragraph_index_batch22():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_invalid_batch22():
    """DOCX locator 不能有 page。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_invalid_batch22():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 10, 10]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_locator_invalid_batch22():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_locator_invalid_batch22():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_section_batch22():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_mixed_batch22():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 0}},
        {"type": "image", "source_locator": {"page": 1}},  # invalid for docx
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _is_valid_bbox 第二十二批 ----------


def test_is_valid_bbox_four_int_batch22():
    assert _is_valid_bbox([0, 0, 100, 200]) is True


def test_is_valid_bbox_four_float_batch22():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 200.5]) is True


def test_is_valid_bbox_three_items_batch22():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_five_items_batch22():
    assert _is_valid_bbox([0, 0, 100, 200, 0]) is False


def test_is_valid_bbox_empty_list_batch22():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_none_batch22():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_string_batch22():
    assert _is_valid_bbox("0,0,10,10") is False


def test_is_valid_bbox_tuple_batch22():
    """tuple 输入被拒绝（_is_valid_bbox 仅接受 list）。"""
    assert _is_valid_bbox((0, 0, 100, 200)) is False


def test_is_valid_bbox_dict_batch22():
    assert _is_valid_bbox({"x": 0}) is False


def test_is_valid_bbox_inf_values_batch22():
    import math
    assert _is_valid_bbox([0, 0, math.inf, 100]) is False


# ---------- _image_resource_ratio 第二十二批 ----------


def test_image_resource_ratio_no_elements_batch22():
    out = _image_resource_ratio([], None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_images_batch22():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_image_with_resource_path_batch22(tmp_path):
    img = tmp_path / "img1.png"
    img.write_bytes(b"x")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_image_without_resource_path_batch22():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_image_nonexistent_path_batch22():
    elements = [{"type": "image", "resource_path": "/nonexistent.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch22(tmp_path):
    img = tmp_path / "exists.png"
    img.write_bytes(b"x")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": "/missing.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_no_images_only_paragraphs_batch22():
    elements = [{"type": "paragraph"}, {"type": "heading"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


# ---------- _chunk_reference_ratio 第二十二批 ----------


def test_chunk_reference_ratio_no_chunks_batch22():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_no_elements_batch22():
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio([], chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_intact_batch22():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_missing_id_batch22():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_missing_batch22():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["x", "y"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_ids_batch22():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # 0 ids → 0 valid (但 ratio 是 0/1 = 0.0)
    p = out["value"]
    assert p == 0.0


# ---------- _text_preservation 第二十二批 ----------


def test_text_preservation_empty_elements_empty_chunks_batch22():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    # precision/recall 分母为 0 时是 None
    assert out["precision"]["value"] is None
    assert out["recall"]["value"] is None


def test_text_preservation_image_excluded_batch22():
    """image 不参与文本比对。"""
    elements = [{"type": "image", "content": "image_data"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_paragraph_included_batch22():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_heading_included_batch22():
    elements = [{"type": "heading", "content": "title"}]
    chunks = [{"text": "title"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_table_included_batch22():
    elements = [{"type": "table", "content": "tabular"}]
    chunks = [{"text": "tabular"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_caption_included_batch22():
    elements = [{"type": "caption", "content": "cap"}]
    chunks = [{"text": "cap"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_mismatch_batch22():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "xyz"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_extra_whitespace_ignored_batch22():
    elements = [{"type": "paragraph", "content": "a b"}]
    chunks = [{"text": "a  b"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


# ---------- _heading_boundary_ratio 第二十二批 ----------


def test_heading_boundary_ratio_no_headings_batch22():
    out = _heading_boundary_ratio([], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks_batch22():
    """有 heading 元素但无 chunks → 0% 合规（reason=None, value=0.0）。"""
    elements = [{"type": "heading", "element_id": "h1", "content": "title"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_ratio_perfect_batch22():
    elements = [{"type": "heading", "element_id": "h1", "content": "title"}]
    chunks = [{"text": "title", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_no_match_batch22():
    elements = [{"type": "heading", "element_id": "h1", "content": "title"}]
    chunks = [{"text": "title", "source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_two_headings_one_match_batch22():
    elements = [
        {"type": "heading", "element_id": "h1", "content": "a"},
        {"type": "heading", "element_id": "h2", "content": "b"},
    ]
    chunks = [
        {"text": "a", "source_element_ids": ["h1"]},
        {"text": "b", "source_element_ids": ["x"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 第二十二批 ----------


def test_silent_drop_count_no_expectations_batch22():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_key_batch22():
    out = _silent_drop_count({}, {"other": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_perfect_match_batch22():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_more_batch22():
    """actual > expected → 不算 silent drop。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_actual_less_batch22():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_count_unknown_type_ignored_batch22():
    """expectations 中没有的 type 不算 silent drop。"""
    by_type = {"weird_type": 0}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 5  # paragraph silent dropped


def test_silent_drop_count_empty_by_type_batch22():
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_count_negative_clamped_batch22():
    """actual > expected → 0（不被负数）。"""
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] >= 0


# ---------- module source forbidden tokens 第三十七批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch22(forbidden):
    src = inspect.getsource(mmod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch22():
    src = inspect.getsource(mmod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch22():
    src = inspect.getsource(mmod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch22():
    src = inspect.getsource(mmod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch22():
    src = inspect.getsource(mmod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch22():
    src = inspect.getsource(mmod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch22():
    src = inspect.getsource(mmod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch22():
    src = inspect.getsource(mmod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch22():
    src = inspect.getsource(mmod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch22():
    src = inspect.getsource(mmod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch22():
    src = inspect.getsource(mmod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch22():
    src = inspect.getsource(mmod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch22():
    src = inspect.getsource(mmod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch22():
    src = inspect.getsource(mmod)
    assert "import datetime" not in src


def test_module_source_no_pandas_import_batch22():
    src = inspect.getsource(mmod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch22():
    src = inspect.getsource(mmod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十三批 ----------


def test_module_source_has_future_annotations_batch22():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_has_math_import_batch22():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_has_collections_counter_import_batch22():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_has_pathlib_path_import_batch22():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import_batch22():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_has_text_types_constant_batch22():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_has_pdf_bbox_required_types_batch22():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_has_null_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_has_ratio_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_has_compute_automatic_metrics_function_batch22():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_has_docstring_batch22():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_has_text_preservation_docstring_batch22():
    src = inspect.getsource(mmod)
    assert "text_preservation" in src


def test_module_source_has_silent_drop_count_function_batch22():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_has_strip_unicode_whitespace_function_batch22():
    src = inspect.getsource(mmod)
    assert "_strip_unicode_whitespace" in src


# ---------- signatures 第三十三批 ----------


def test_signature_null_batch22():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["reason"]


def test_signature_ratio_batch22():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_bool_metric_batch22():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_int_metric_batch22():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["value"]


def test_signature_compute_metrics_batch22():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_image_base_dir_default_none_batch22():
    sig = inspect.signature(compute_automatic_metrics)
    params = {p.name: p for p in sig.parameters.values()}
    assert params["image_base_dir"].default is None


# ---------- module 合理性第三十三批 ----------


def test_module_does_not_import_app_pipeline_batch22():
    src = inspect.getsource(mmod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_evaluation_runner_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_does_not_import_evaluation_manifest_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_evaluation_report_batch22():
    src = inspect.getsource(mmod)
    assert "from evaluation.report" not in src
    assert "from evaluation import report" not in src


def test_module_no_main_block_batch22():
    src = inspect.getsource(mmod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_null_callable_batch22():
    assert callable(mmod._null)


def test_module_ratio_callable_batch22():
    assert callable(mmod._ratio)


def test_module_bool_metric_callable_batch22():
    assert callable(mmod._bool_metric)


def test_module_int_metric_callable_batch22():
    assert callable(mmod._int_metric)


def test_module_compute_automatic_metrics_callable_batch22():
    assert callable(mmod.compute_automatic_metrics)


def test_module_text_types_constant_batch22():
    assert hasattr(mmod, "_TEXT_TYPES")


# ---------- 端到端集成第三十三批 ----------


def test_e2e_compute_metrics_minimal_doc_batch22():
    out = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert "pipeline_success" in out
    assert "schema_valid" in out
    assert "element_count_total" in out
    assert "element_count_by_type" in out
    assert "pdf_locator_valid_ratio" in out
    assert "docx_locator_valid_ratio" in out
    assert "image_resource_exists_ratio" in out
    assert "chunk_reference_intact_ratio" in out
    assert "text_preservation_equal" in out
    assert "text_char_multiset_precision" in out
    assert "text_char_multiset_recall" in out
    assert "heading_boundary_compliance" in out
    assert "silent_drop_count" in out


def test_e2e_compute_metrics_full_pdf_doc_batch22():
    """完整 PDF doc。"""
    out = compute_automatic_metrics(
        document={
            "elements": [
                {"type": "paragraph", "id": "e1", "content": "hello", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
            ],
            "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
        },
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["element_count_total"]["value"] == 1
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_full_docx_doc_batch22():
    out = compute_automatic_metrics(
        document={
            "elements": [
                {"type": "paragraph", "id": "e1", "content": "hello", "source_locator": {"paragraph_index": 0}},
            ],
            "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
        },
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert out["element_count_total"]["value"] == 1
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_with_silent_drop_batch22():
    out = compute_automatic_metrics(
        document={"elements": [{"type": "paragraph"}], "chunks": []},
        error=None,
        source_type="pdf",
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    assert out["silent_drop_count"]["value"] == 4


def test_e2e_compute_metrics_pipeline_failed_batch22():
    out = compute_automatic_metrics(
        document=None,
        error={"code": "E_PARSE"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False
    assert out["element_count_total"]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_idempotent_batch22():
    doc = {"elements": [{"type": "paragraph", "content": "x"}], "chunks": [{"text": "x"}]}
    o1 = compute_automatic_metrics(doc, None, "pdf", None)
    o2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert o1 == o2


def test_e2e_compute_metrics_no_image_elements_batch22():
    """无 image elements 时 image_resource_exists_ratio 应是 no_image_elements。"""
    out = compute_automatic_metrics(
        document={"elements": [{"type": "paragraph"}], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_e2e_compute_metrics_does_not_mutate_input_batch22():
    doc = {"elements": [{"type": "paragraph", "content": "x"}], "chunks": [{"text": "x"}]}
    import copy
    snapshot = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == snapshot
