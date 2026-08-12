"""evaluation/metrics.py 第五十八轮 edges 测试（Round 526）。

补强 edges55 未触及的角度（第三十批）：
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第三十批：内容精确 / 不重叠 / tuple 类型
- _NOT_EVALUATED 第三十批：是 str / 值精确
- 基础构造器 第三十批：null 与 ratio 不同 / bool 强转 / int 强转
- compute_automatic_metrics 第三十批：返回 14 个 metric / schema_check_exception path / 多 source_type 路径
- _pdf_locator_ratio 第三十批：page=0 / page=负数 / bbox=3 个值 / bbox 含 NaN
- _docx_locator_ratio 第三十批：含 page / 含 bbox / 全无结构键 / 7 个结构键
- _is_valid_bbox 第三十批：bool 元素 / NaN / Inf / 正确 4 个数
- _image_resource_ratio 第三十批：rp 是 None / rp 是空 str / 文件存在但 0 size
- _chunk_reference_ratio 第三十批：chunk 无 source_element_ids key / 空 list
- _strip_unicode_whitespace 第三十批：NBSP / em space / ideographic space / line separator
- _text_preservation 第三十批：partial match / unicode 字符 / Counter 交集
- _heading_boundary_ratio 第三十批：heading 无 element_id / 多个 heading / 多个匹配 chunk
- _silent_drop_count 第三十批：expectations 空 dict / expectations 含 element_count_by_type 空 dict
- module source forbidden tokens 第四十七批
- module source 字符串精确补强第四十三批
- signatures 第四十三批
- module 合理性第四十三批
- 端到端集成第四十三批
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
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


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 第三十批 ----------


def test_text_types_value_batch30():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_pdf_bbox_required_types_value_batch30():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_pdf_bbox_required_is_subset_of_text_types_batch30():
    """所有需要 bbox 的类型都属于 text types。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_excludes_table_header_footer_batch30():
    """table/header/footer 不需要 bbox。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_excludes_image_batch30():
    assert "image" not in _TEXT_TYPES


def test_text_types_is_tuple_batch30():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_is_tuple_batch30():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_not_evaluated_value_batch30():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch30():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- 基础构造器 第三十批 ----------


def test_null_two_keys_batch30():
    m = _null("reason1")
    assert set(m.keys()) == {"value", "reason"}


def test_null_value_is_none_batch30():
    assert _null("x")["value"] is None


def test_ratio_two_keys_batch30():
    m = _ratio(0.5)
    assert set(m.keys()) == {"value", "reason"}


def test_ratio_reason_is_none_batch30():
    assert _ratio(0.5)["reason"] is None


def test_ratio_float_value_batch30():
    assert isinstance(_ratio(0.5)["value"], float)


def test_bool_metric_strong_cast_batch30():
    """bool 强转：1 → True。"""
    assert _bool_metric(1)["value"] is True


def test_bool_metric_zero_batch30():
    assert _bool_metric(0)["value"] is False


def test_int_metric_strong_cast_batch30():
    """int 强转：float → int。"""
    assert _int_metric(3.7)["value"] == 3
    assert isinstance(_int_metric(3.7)["value"], int)


def test_int_metric_str_batch30():
    """int('5')=5。"""
    assert _int_metric(5)["value"] == 5


def test_int_metric_negative_batch30():
    assert _int_metric(-10)["value"] == -10


# ---------- compute_automatic_metrics 第三十批 ----------


def test_compute_automatic_metrics_keys_count_batch30():
    """返回 14 个 metric key。"""
    result = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert len(result) == 14


def test_compute_automatic_metrics_keys_set_batch30():
    result = compute_automatic_metrics(
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
    assert set(result.keys()) == expected_keys


def test_compute_automatic_metrics_pipeline_success_true_batch30():
    result = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert result["pipeline_success"]["value"] is True


def test_compute_automatic_metrics_pipeline_failed_batch30():
    """document=None → pipeline_success=False。"""
    result = compute_automatic_metrics(
        document=None,
        error={"code": "fail", "message": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert result["pipeline_success"]["value"] is False


def test_compute_automatic_metrics_error_code_extracted_batch30():
    result = compute_automatic_metrics(
        document=None,
        error={"code": "mycode", "message": "x"},
        source_type="pdf",
        expectations=None,
    )
    assert result["error_code"]["value"] == "mycode"


def test_compute_automatic_metrics_schema_exception_path_batch30():
    """schema 校验抛异常 → value=False, reason 含 exception type。"""
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=RuntimeError("boom")):
        result = compute_automatic_metrics(
            document={"elements": []},
            error=None,
            source_type="pdf",
            expectations=None,
        )
    assert result["schema_valid"]["value"] is False
    assert "schema_check_exception:RuntimeError" in result["schema_valid"]["reason"]


def test_compute_automatic_metrics_pdf_source_batch30():
    """source_type='pdf' → pdf_locator 计算 / docx_locator null。"""
    result = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert result["pdf_locator_valid_ratio"]["reason"] == "no_elements"
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_automatic_metrics_docx_source_batch30():
    """source_type='docx' → docx_locator 计算 / pdf_locator null。"""
    result = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="docx",
        expectations=None,
    )
    assert result["docx_locator_valid_ratio"]["reason"] == "no_elements"
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_automatic_metrics_unknown_source_batch30():
    """source_type='weird' → pdf 与 docx 都 not_*_document。"""
    result = compute_automatic_metrics(
        document={"elements": [], "chunks": []},
        error=None,
        source_type="weird",
        expectations=None,
    )
    assert result["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert result["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# ---------- _pdf_locator_ratio 第三十批 ----------


def test_pdf_locator_ratio_page_zero_batch30():
    """page=0 → invalid（必须 ≥1）。"""
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch30():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_three_values_batch30():
    """bbox 长度 != 4 → invalid。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [1.0, 2.0, 3.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_nan_batch30():
    """bbox 含 NaN → invalid。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [1.0, math.nan, 3.0, 4.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_bbox_inf_batch30():
    """bbox 含 Inf → invalid。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [1.0, math.inf, 3.0, 4.0]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_locator_batch30():
    """无 source_locator → loc={} → page=None → invalid。"""
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第三十批 ----------


def test_docx_locator_ratio_has_page_batch30():
    """有 page → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "section": "s1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_has_bbox_batch30():
    """有 bbox → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "section": "s1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys_batch30():
    """无任何结构化 key → invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"weird_key": "x"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_all_seven_keys_batch30():
    """7 个结构化 key 全有 → valid。"""
    elements = [
        {
            "type": "paragraph",
            "source_locator": {
                "section": "s",
                "paragraph_index": 1,
                "run_index": 2,
                "table_index": 3,
                "row_index": 4,
                "col_index": 5,
                "relationship_id": "r",
            },
        }
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


# ---------- _is_valid_bbox 第三十批 ----------


def test_is_valid_bbox_bool_element_batch30():
    """bool 元素 → invalid（防止 True 被当作 1）。"""
    assert _is_valid_bbox([True, 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_nan_batch30():
    assert _is_valid_bbox([1.0, math.nan, 3.0, 4.0]) is False


def test_is_valid_bbox_inf_batch30():
    assert _is_valid_bbox([1.0, math.inf, 3.0, 4.0]) is False


def test_is_valid_bbox_negative_inf_batch30():
    assert _is_valid_bbox([1.0, -math.inf, 3.0, 4.0]) is False


def test_is_valid_bbox_correct_batch30():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_all_int_batch30():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_mixed_int_float_batch30():
    assert _is_valid_bbox([1, 2.0, 3, 4.0]) is True


def test_is_valid_bbox_zero_values_batch30():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_negative_values_batch30():
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


# ---------- _image_resource_ratio 第三十批 ----------


def test_image_resource_ratio_no_resource_path_batch30():
    """image 无 resource_path → invalid。"""
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch30():
    """resource_path="" → invalid（falsy）。"""
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_zero_size_file_batch30(tmp_path):
    """文件存在但 size=0 → invalid。"""
    p = tmp_path / "img.png"
    p.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(p)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_nonexistent_batch30():
    elements = [{"type": "image", "resource_path": "/nonexistent/img.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_returns_dict_batch30():
    elements = []
    out = _image_resource_ratio(elements, None)
    assert isinstance(out, dict)


# ---------- _chunk_reference_ratio 第三十批 ----------


def test_chunk_reference_ratio_chunk_missing_key_batch30():
    """chunk 无 source_element_ids key → invalid（ids=[]）。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x"}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_list_batch30():
    """chunk source_element_ids=[] → invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch30():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"text": "x", "source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_partial_valid_batch30():
    elements = [{"element_id": "e1"}]
    chunks = [
        {"text": "x", "source_element_ids": ["e1"]},
        {"text": "y", "source_element_ids": ["e_unknown"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _strip_unicode_whitespace 第三十批 ----------


def test_strip_unicode_whitespace_nbsp_batch30():
    """NBSP (U+00A0)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch30():
    """EM SPACE (U+2003)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_en_space_batch30():
    """EN SPACE (U+2002)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch30():
    """IDEOGRAPHIC SPACE (U+3000)。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_line_separator_batch30():
    """LINE SEPARATOR (U+2028)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_paragraph_separator_batch30():
    """PARAGRAPH SEPARATOR (U+2029)。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_no_whitespace_batch30():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_empty_batch30():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace_batch30():
    assert _strip_unicode_whitespace(" \t\n ") == ""


# ---------- _text_preservation 第三十批 ----------


def test_text_preservation_perfect_match_batch30():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_unicode_batch30():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_partial_match_batch30():
    """部分匹配：Counter 交集。"""
    elements = [{"type": "paragraph", "content": "aabbcc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected="aabbcc" (a:2,b:2,c:2), actual="abc" (a:1,b:1,c:1)
    # common = min(2,1)+min(2,1)+min(2,1) = 3
    # precision = 3/3 = 1.0
    # recall = 3/6 = 0.5
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 0.5) < 1e-9


def test_text_preservation_empty_both_batch30():
    elements = [{"type": "image", "content": ""}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # 无非 image element → expected=""
    # actual=""
    # → precision/recall: empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_returns_three_keys_batch30():
    elements = []
    chunks = []
    out = _text_preservation(elements, chunks)
    assert set(out.keys()) == {"equal", "precision", "recall"}


# ---------- _heading_boundary_ratio 第三十批 ----------


def test_heading_boundary_ratio_heading_no_element_id_batch30():
    """heading 无 element_id → 永远不匹配。"""
    elements = [{"type": "heading"}]
    chunks = [{"text": "x", "source_element_ids": ["e1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_multiple_headings_batch30():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # 1/2 matched
    assert out["value"] == 0.5


def test_heading_boundary_ratio_no_headings_batch30():
    elements = [{"type": "paragraph"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_all_matched_batch30():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"text": "x", "source_element_ids": ["h1"]},
        {"text": "y", "source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _silent_drop_count 第三十批 ----------


def test_silent_drop_count_no_expectations_batch30():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_dict_batch30():
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_element_count_by_type_batch30():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_actual_more_than_expected_batch30():
    """actual > expected → 0 drop。"""
    out = _silent_drop_count(
        {"paragraph": 10},
        {"element_count_by_type": {"paragraph": 5}},
    )
    assert out["value"] == 0


def test_silent_drop_count_sum_across_types_batch30():
    out = _silent_drop_count(
        {"paragraph": 3, "heading": 1},
        {"element_count_by_type": {"paragraph": 5, "heading": 2}},
    )
    # paragraph: max(0, 5-3)=2; heading: max(0, 2-1)=1 → total 3
    assert out["value"] == 3


# ---------- module source forbidden tokens 第四十七批 ----------


def test_module_source_no_subprocess_batch30():
    src = inspect.getsource(mmod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(mmod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(mmod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(mmod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(mmod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(mmod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch30():
    src = inspect.getsource(mmod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(mmod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(mmod)
    assert "requests" not in src


def test_module_source_no_unlink_batch30():
    src = inspect.getsource(mmod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十三批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_text_types_constant_batch30():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ' in src


def test_module_source_contains_pdf_bbox_required_types_batch30():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ' in src


def test_module_source_contains_not_evaluated_batch30():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_null_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _null" in src


def test_module_source_contains_ratio_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _ratio" in src


def test_module_source_contains_bool_metric_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _bool_metric" in src


def test_module_source_contains_int_metric_func_batch30():
    src = inspect.getsource(mmod)
    assert "def _int_metric" in src


def test_module_source_contains_compute_automatic_metrics_batch30():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics" in src


def test_module_source_contains_pdf_locator_ratio_batch30():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio" in src


def test_module_source_contains_docx_locator_ratio_batch30():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio" in src


def test_module_source_contains_is_valid_bbox_batch30():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox" in src


def test_module_source_contains_image_resource_ratio_batch30():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio" in src


def test_module_source_contains_chunk_reference_ratio_batch30():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio" in src


def test_module_source_contains_strip_unicode_whitespace_batch30():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace" in src


def test_module_source_contains_text_preservation_batch30():
    src = inspect.getsource(mmod)
    assert "def _text_preservation" in src


def test_module_source_contains_heading_boundary_ratio_batch30():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio" in src


def test_module_source_contains_silent_drop_count_batch30():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count" in src


# ---------- signatures 第四十三批 ----------


def test_signature_null_batch30():
    sig = inspect.signature(_null)
    assert sig.parameters["reason"].annotation == "str"
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_ratio_batch30():
    sig = inspect.signature(_ratio)
    assert sig.parameters["value"].annotation == "float"
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_bool_metric_batch30():
    sig = inspect.signature(_bool_metric)
    assert sig.parameters["value"].annotation == "bool"


def test_signature_int_metric_batch30():
    sig = inspect.signature(_int_metric)
    assert sig.parameters["value"].annotation == "int"


def test_signature_compute_automatic_metrics_batch30():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_automatic_metrics_image_base_dir_default_batch30():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_automatic_metrics_return_annotation_batch30():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict[str, Any]" in str(sig.return_annotation)


def test_signature_is_valid_bbox_batch30():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.parameters["bbox"].annotation == "Any"
    assert sig.return_annotation == "bool"


def test_signature_strip_unicode_whitespace_batch30():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.parameters["s"].annotation == "str"
    assert sig.return_annotation == "str"


# ---------- module 合理性第四十三批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch30():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch30():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch30():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_no_class_definitions_batch30():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_all_contains_one_entry_batch30():
    src = inspect.getsource(mmod)
    assert '"compute_automatic_metrics"' in src


def test_module_no_main_block_batch30():
    src = inspect.getsource(mmod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十三批 ----------


def test_e2e_compute_automatic_metrics_full_batch30():
    """端到端：完整 metrics 计算。"""
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "e1", "content": "hello"},
        ],
        "chunks": [
            {"text": "hello", "source_element_ids": ["e1"]},
        ],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 1
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_pipeline_failed_batch30():
    """端到端：pipeline 失败。"""
    out = compute_automatic_metrics(
        document=None,
        error={"code": "parse_failed"},
        source_type="pdf",
        expectations=None,
    )
    assert out["pipeline_success"]["value"] is False
    assert out["schema_valid"]["reason"] == "pipeline_failed"
    assert out["element_count_total"]["reason"] == "pipeline_failed"


def test_e2e_text_preservation_with_image_batch30():
    """端到端：image 不参与文本保留。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1", "content": ""},
            {"type": "paragraph", "element_id": "p1", "content": "abc"},
        ],
        "chunks": [{"text": "abc", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
    )
    assert out["text_preservation_equal"]["value"] is True


def test_e2e_silent_drop_count_with_expectations_batch30():
    """端到端：含 expectations 的 silent_drop。"""
    doc = {
        "elements": [{"type": "paragraph"}, {"type": "paragraph"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations={"element_count_by_type": {"paragraph": 5}},
    )
    # actual=2, expected=5 → drop=3
    assert out["silent_drop_count"]["value"] == 3


def test_e2e_idempotent_batch30():
    """端到端：相同输入两次相同输出。"""
    doc = {"elements": [], "chunks": []}
    o1 = compute_automatic_metrics(doc, None, "pdf", None)
    o2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert o1 == o2


def test_e2e_no_input_modification_batch30():
    """端到端：不修改输入。"""
    import copy
    doc = {"elements": [{"type": "paragraph", "element_id": "e1"}], "chunks": []}
    snapshot = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == snapshot


def test_e2e_returns_dict_batch30():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)
