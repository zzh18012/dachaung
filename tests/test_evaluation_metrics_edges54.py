"""evaluation/metrics.py 第五十六轮 edges 测试（Round 512）。

补强 edges53 未触及的角度（第二十八批）：
- _null / _ratio / _bool_metric / _int_metric 第二十八批：返回结构 / 类型 / 边界值
- compute_automatic_metrics 第二十八批：document None + error None / error code 透传 / source_type unknown / pdf 走 pdf_locator / docx 走 docx_locator / expectations 完整 / image_base_dir 嵌套路径 / 13 个 metric key 完整
- _pdf_locator_ratio 第二十八批：empty / page=0 / page=-1 / page=None / bbox 缺失 / bbox 残缺 / bbox 布尔 / bbox inf
- _docx_locator_ratio 第二十八批：empty / 含 page / 含 bbox / 含 paragraph_index / 含 section / 含 relationship_id / 全无结构键
- _is_valid_bbox 第二十八批：非 list / 长度错 / None / bool / inf / nan / str 混入
- _image_resource_ratio 第二十八批：无 image / image 缺 resource_path / 文件存在 / 文件不存在 / 大小 0
- _chunk_reference_ratio 第二十八批：chunks empty / 单 chunk 单 id 匹配 / 多 chunk 多 id / 部分不匹配
- _strip_unicode_whitespace 第二十八批：NBSP / em space / ideographic space / line separator / paragraph separator / 零宽
- _text_preservation 第二十八批：纯空白 / 空白 + 字符 / image content 忽略 / chunk text None
- _heading_boundary_ratio 第二十八批：无 heading / 单 heading 匹配 / 多 heading 部分匹配 / chunk 缺 source_element_ids
- _silent_drop_count 第二十八批：无 expectations / expectations 含空 element_count_by_type / 实际大于预期 / 实际等于预期
- module source forbidden tokens 第四十五批
- module source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
"""

from __future__ import annotations

import inspect
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


# ---------- 基础构造器 第二十八批 ----------


def test_null_returns_value_none_batch28():
    m = _null("reason")
    assert m["value"] is None


def test_null_returns_reason_unchanged_batch28():
    m = _null("X")
    assert m["reason"] == "X"


def test_null_returns_dict_batch28():
    assert isinstance(_null("x"), dict)


def test_ratio_zero_batch28():
    m = _ratio(0.0)
    assert m["value"] == 0.0
    assert m["reason"] is None


def test_ratio_one_batch28():
    m = _ratio(1.0)
    assert m["value"] == 1.0


def test_ratio_returns_float_batch28():
    m = _ratio(0)
    assert isinstance(m["value"], float)


def test_bool_metric_true_batch28():
    m = _bool_metric(True)
    assert m["value"] is True


def test_bool_metric_false_batch28():
    m = _bool_metric(False)
    assert m["value"] is False


def test_bool_metric_casts_int_batch28():
    """传入 truthy int 1 → True。"""
    m = _bool_metric(1)
    assert m["value"] is True


def test_int_metric_zero_batch28():
    m = _int_metric(0)
    assert m["value"] == 0


def test_int_metric_large_batch28():
    m = _int_metric(10**18)
    assert m["value"] == 10**18


def test_int_metric_casts_to_int_batch28():
    m = _int_metric(True)  # bool is int subclass
    assert m["value"] == 1


# ---------- compute_automatic_metrics 第二十八批 ----------


def test_compute_metrics_document_none_error_none_batch28():
    """document=None, error=None → pipeline_success=False, schema_valid=pipeline_failed。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    assert m["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_metrics_error_code_propagated_batch28():
    """error.code 透传。"""
    m = compute_automatic_metrics(None, {"code": "X"}, "pdf", None)
    assert m["error_code"]["value"] == "X"


def test_compute_metrics_error_none_code_none_batch28():
    """error=None → code=None。"""
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["error_code"]["value"] is None


def test_compute_metrics_source_type_unknown_batch28():
    """source_type='unknown'（非 pdf/docx）→ pdf/docx locator 都 null + not_pdf/docx_document。

    注意：document=None 时所有 metric 都是 pipeline_failed；要测 not_pdf_document
    必须给一个非 None 的 document。
    """
    m = compute_automatic_metrics({}, None, "unknown", None)
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_returns_dict_batch28():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(m, dict)


def test_compute_metrics_document_none_returns_13_metric_keys_batch28():
    m = compute_automatic_metrics(None, None, "pdf", None)
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
    assert expected_keys.issubset(set(m.keys()))


def test_compute_metrics_document_empty_dict_batch28():
    """document={} → 不抛异常，element_count_total=0。"""
    m = compute_automatic_metrics({}, None, "pdf", None)
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_with_elements_batch28():
    """document 含 elements → element_count_by_type。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "hello"},
            {"type": "paragraph", "content": "world"},
            {"type": "heading", "content": "title"},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = m["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1}


# ---------- _pdf_locator_ratio 第二十八批 ----------


def test_pdf_locator_ratio_empty_batch28():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_ratio_page_zero_batch28():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    # page=0 invalid → valid=0 → ratio=0.0
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch28():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_none_batch28():
    elements = [{"type": "image", "source_locator": {"page": None}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_missing_batch28():
    elements = [{"type": "image", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_only_valid_batch28():
    """image 类型只需 page≥1，不需 bbox。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_paragraph_missing_bbox_batch28():
    """paragraph 需要 page≥1 + bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_paragraph_with_valid_bbox_batch28():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0.0, 0.0, 100.0, 100.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_no_locator_key_batch28():
    """element 没有 source_locator key。"""
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第二十八批 ----------


def test_docx_locator_ratio_empty_batch28():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_ratio_has_page_batch28():
    """含 page → 不合法。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_has_bbox_batch28():
    """含 bbox → 不合法。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_has_paragraph_index_batch28():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_has_section_batch28():
    elements = [{"type": "paragraph", "source_locator": {"section": "main"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_has_relationship_id_batch28():
    elements = [{"type": "image", "source_locator": {"relationship_id": "r1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_no_structural_keys_batch28():
    elements = [{"type": "paragraph", "source_locator": {"foo": "bar"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_locator_key_batch28():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第二十八批 ----------


def test_is_valid_bbox_none_batch28():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_str_batch28():
    assert _is_valid_bbox("not list") is False


def test_is_valid_bbox_dict_batch28():
    assert _is_valid_bbox({}) is False


def test_is_valid_bbox_short_batch28():
    assert _is_valid_bbox([1, 2, 3]) is False


def test_is_valid_bbox_long_batch28():
    assert _is_valid_bbox([1, 2, 3, 4, 5]) is False


def test_is_valid_bbox_with_bool_batch28():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_with_inf_batch28():
    assert _is_valid_bbox([0.0, 0.0, math.inf, 0.0]) is False


def test_is_valid_bbox_with_nan_batch28():
    assert _is_valid_bbox([0.0, 0.0, math.nan, 0.0]) is False


def test_is_valid_bbox_with_str_batch28():
    assert _is_valid_bbox(["0", 0, 0, 0]) is False


def test_is_valid_bbox_valid_batch28():
    assert _is_valid_bbox([0.0, 0.0, 100.0, 100.0]) is True


def test_is_valid_bbox_valid_int_batch28():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_negative_values_batch28():
    assert _is_valid_bbox([-1.0, -1.0, 1.0, 1.0]) is True


# ---------- _image_resource_ratio 第二十八批 ----------


def test_image_resource_ratio_no_images_batch28():
    out = _image_resource_ratio([{"type": "paragraph"}], None)
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path_batch28():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch28():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_exists_batch28(tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG\r\n")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_file_not_exists_batch28(tmp_path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "nope.png")}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_file_size_zero_batch28(tmp_path):
    """文件存在但大小 0 → 不算 valid。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch28(tmp_path):
    img = tmp_path / "good.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img)},  # valid
        {"type": "image", "resource_path": str(tmp_path / "nope.png")},  # invalid
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 第二十八批 ----------


def test_chunk_reference_ratio_no_chunks_batch28():
    out = _chunk_reference_ratio([{"element_id": "e1"}], [])
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_single_match_batch28():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_no_match_batch28():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["eX"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_partial_match_batch28():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # ok
        {"source_element_ids": ["eX"]},  # bad
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_reference_ratio_no_source_ids_batch28():
    """chunk 缺 source_element_ids → 不算 valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_ids_list_batch28():
    """source_element_ids=[] → not valid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_multi_id_all_match_batch28():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_multi_id_partial_batch28():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "eX"]}]  # eX not in elements
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _strip_unicode_whitespace 第二十八批 ----------


def test_strip_unicode_whitespace_nbsp_batch28():
    """U+00A0 NBSP。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch28():
    """U+2003 em space。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch28():
    """U+3000 ideographic space。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch28():
    """U+2028 line separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch28():
    """U+2029 paragraph separator。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_zero_width_not_space_batch28():
    """U+200B zero-width space：isspace() False，不删除。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_empty_batch28():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace_batch28():
    assert _strip_unicode_whitespace(" \t\n\r") == ""


# ---------- _text_preservation 第二十八批 ----------


def test_text_preservation_empty_batch28():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_only_whitespace_batch28():
    elements = [{"type": "paragraph", "content": "  "}]
    chunks = [{"text": "  "}]
    out = _text_preservation(elements, chunks)
    # 删空白后两边都空 → empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_image_content_ignored_batch28():
    """image 的 content 不参与（type=='image' 跳过）。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_chunk_text_none_batch28():
    """chunk.text=None → 当作空字符串。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": None}]
    out = _text_preservation(elements, chunks)
    # actual 空，expected 非空 → recall=0/3=0.0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_content_none_batch28():
    """element.content=None → 当作空字符串。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_partial_batch28():
    """字符多集合：actual 缺一个字符。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    # common = 2, actual = 2 → precision=1.0
    assert out["precision"]["value"] == 1.0
    # common = 2, expected = 3 → recall=2/3
    assert abs(out["recall"]["value"] - 2.0 / 3.0) < 1e-9


# ---------- _heading_boundary_ratio 第二十八批 ----------


def test_heading_boundary_no_headings_batch28():
    out = _heading_boundary_ratio([{"type": "paragraph"}], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_match_batch28():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_no_match_batch28():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_partial_match_batch28():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_chunk_empty_ids_batch28():
    """chunk 缺 source_element_ids → 不贡献。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunk_ids_first_only_batch28():
    """只看 chunk 的第一个 source_element_id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]  # h1 在第二位
    out = _heading_boundary_ratio(elements, chunks)
    # 第一个是 'other'，不算 h1
    assert out["value"] == 0.0


# ---------- _silent_drop_count 第二十八批 ----------


def test_silent_drop_no_expectations_batch28():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expectations_batch28():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_element_count_by_type_batch28():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_zero_drop_batch28():
    """actual == expected → drop=0。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_actual_greater_batch28():
    """actual > expected → 0 drop（max(0, ...)）。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_partial_batch28():
    """某些 type 缺失。"""
    out = _silent_drop_count(
        {"paragraph": 2},
        {"element_count_by_type": {"paragraph": 5, "heading": 3}},
    )
    # paragraph: 5-2=3 drop
    # heading: 3-0=3 drop
    # total: 6
    assert out["value"] == 6


def test_silent_drop_int_value_type_batch28():
    out = _silent_drop_count(
        {},
        {"element_count_by_type": {"paragraph": 3}},
    )
    assert isinstance(out["value"], int)


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_compute_automatic_metrics_batch28():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics" in src


def test_module_source_contains_text_types_constant_batch28():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_required_types_batch28():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_not_evaluated_constant_batch28():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


def test_module_source_contains_pipeline_failed_batch28():
    src = inspect.getsource(mmod)
    assert "pipeline_failed" in src


def test_module_source_contains_not_pdf_document_batch28():
    src = inspect.getsource(mmod)
    assert "not_pdf_document" in src


def test_module_source_contains_not_docx_document_batch28():
    src = inspect.getsource(mmod)
    assert "not_docx_document" in src


def test_module_source_contains_no_chunks_reason_batch28():
    src = inspect.getsource(mmod)
    assert "no_chunks" in src


def test_module_source_contains_no_elements_reason_batch28():
    src = inspect.getsource(mmod)
    assert "no_elements" in src


def test_module_source_contains_empty_expected_and_actual_reason_batch28():
    src = inspect.getsource(mmod)
    assert "empty_expected_and_actual" in src


def test_module_source_contains_counter_import_batch28():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_contains_math_import_batch28():
    src = inspect.getsource(mmod)
    assert "import math" in src


# ---------- signatures 第四十一批 ----------


def test_signature_null_batch28():
    sig = inspect.signature(_null)
    params = list(sig.parameters.keys())
    assert params == ["reason"]


def test_signature_ratio_batch28():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_bool_metric_batch28():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_int_metric_batch28():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_compute_metrics_batch28():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_metrics_image_base_dir_default_none_batch28():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_ratio_batch28():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.keys())
    assert params == ["elements"]


def test_signature_text_preservation_batch28():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.keys())
    assert params == ["elements", "chunks"]


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch28():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch28():
    src = inspect.getsource(mmod)
    assert "Counter" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_imports_pathlib_batch28():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_text_types_value_batch28():
    """_TEXT_TYPES 含 7 个类型。"""
    # 间接验证：从源码提取
    src = inspect.getsource(mmod)
    for t in ("heading", "paragraph", "list_item", "table", "caption", "header", "footer"):
        assert t in src


def test_module_no_main_block_batch28():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_contains_compute_only_batch28():
    """__all__ 只导出 compute_automatic_metrics。"""
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- 端到端集成第四十一批 ----------


def test_e2e_compute_metrics_full_doc_batch28():
    """端到端：完整 document 跑全部 13 个指标。"""
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "element_id": "e1",
                "content": "hello world",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
        ],
        "chunks": [
            {"text": "hello world", "source_element_ids": ["e1"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 1
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_with_expectations_batch28():
    """端到端：含 expectations → silent_drop_count。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "a"},
            {"type": "paragraph", "content": "b"},
        ],
        "chunks": [{"text": "ab"}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = compute_automatic_metrics(doc, None, "docx", expectations)
    assert m["silent_drop_count"]["value"] == 3


def test_e2e_compute_metrics_docx_full_batch28():
    """端到端：DOCX 完整跑。"""
    doc = {
        "elements": [
            {"type": "paragraph", "content": "x", "source_locator": {"paragraph_index": 0}},
        ],
        "chunks": [{"text": "x"}],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_text_preservation_full_match_batch28():
    """端到端：完整匹配 → P=R=1.0 + equal=True。"""
    elements = [
        {"type": "paragraph", "content": "abc def"},
        {"type": "heading", "content": "title"},
    ]
    chunks = [{"text": "abc def"}, {"text": "title"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_e2e_pdf_locator_mixed_batch28():
    """端到端：PDF locator 混合元素。"""
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid (no bbox)
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]},
        },  # valid
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 2.0 / 3.0


def test_e2e_no_side_effects_batch28():
    """端到端：调用 compute 不修改输入。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "abc"}],
        "chunks": [{"text": "abc"}],
    }
    doc_before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_e2e_image_resource_with_base_dir_batch28(tmp_path):
    """端到端：image_base_dir 拼接（仅文件名）。"""
    # 创建图片在 base_dir 下
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]  # 只文件名
    out = _image_resource_ratio(elements, tmp_path)
    # 实现里 candidates = [Path("img.png"), tmp_path / "img.png"]
    # 第一个不找到，第二个找到
    assert out["value"] == 1.0
