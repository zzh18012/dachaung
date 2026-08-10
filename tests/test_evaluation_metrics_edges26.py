"""evaluation/metrics.py 第二十七轮 edges 测试（Round 322）。

重点补强 edges25 未触及的角度：
- compute_automatic_metrics 整体行为深度补强（混合 source_type / document + error 同时给 / 各 metric 路径）
- error_code 字段精确补强
- _text_preservation 不变量补强（empty + only image + 多类型混合）
- _silent_drop_count 边界补充（element_count_by_type=None/空/非 dict）
- _pdf/_docx/_image/_strip_unicode source level 补强
- module source 字符串精确补强（含 dict 字面量结构 / for loop 模式）
- module source forbidden tokens 第二批
- signatures 精确（POSITIONAL_OR_KEYWORD / 无 varargs / 5 params）
- 端到端集成补强（DOCX 全元素 / PDF 全元素 / 多 chunk 引用）
- 模块整体合理性（_TEXT_TYPES 7 / _PDF_BBOX 4 / _NOT_EVALUATED）
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


# ---------- compute_automatic_metrics 整体行为深度补强 ----------


def test_compute_metrics_source_type_unknown_both_locators_null():
    """source_type 不是 pdf/docx → 两 locator 都 null 但 reason 不同。"""
    out = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "unknown", None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_metrics_source_type_empty_string_both_null():
    out = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "", None
    )
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_compute_metrics_source_type_pdf_docx_locator_null():
    out = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "pdf", None
    )
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_source_type_docx_pdf_locator_null():
    out = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "docx", None
    )
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"


def test_compute_metrics_document_and_error_both_set_pipeline_success_false():
    """error != None → pipeline_success False（即使 document 非 None）。"""
    doc = {"elements": [], "chunks": []}
    err = {"code": "fail"}
    out = compute_automatic_metrics(doc, err, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    # error_code 取自 error["code"]
    assert out["error_code"]["value"] == "fail"


def test_compute_metrics_document_set_error_none_pipeline_success_true():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["error_code"]["value"] is None


def test_compute_metrics_returns_14_keys_for_normal_doc():
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


def test_compute_metrics_returns_14_keys_for_failed_doc():
    """document=None 也应返回 14 个 key（pipeline_success/error_code/schema_valid + 11 null）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_metrics_error_code_with_no_code_field():
    """error truthy 但缺 code 字段 → KeyError（代码用 error["code"]）。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, {"x": 1}, "pdf", None)


def test_compute_metrics_error_code_with_various_value_types():
    """error["code"] 可以是任意可序列化值。"""
    for code in ("E1", 0, "", "X" * 50):
        out = compute_automatic_metrics(None, {"code": code}, "pdf", None)
        assert out["error_code"]["value"] == code


def test_compute_metrics_element_count_by_type_default_unknown():
    """element 缺 type 字段 → 计入 'unknown'。"""
    doc = {
        "elements": [{"element_id": "e1"}, {"element_id": "e2", "type": "heading"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 1, "heading": 1}


def test_compute_metrics_element_count_total_int():
    doc = {"elements": [{"type": "heading"}, {"type": "paragraph"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2
    assert isinstance(out["element_count_total"]["value"], int)


def test_compute_metrics_schema_valid_value_is_bool_or_none():
    """正常路径 schema_valid value 是 True/False；失败路径是 None。"""
    # 失败路径
    out_fail = compute_automatic_metrics(None, None, "pdf", None)
    assert out_fail["schema_valid"]["value"] is None
    # 正常路径
    out_ok = compute_automatic_metrics(
        {"elements": [], "chunks": []}, None, "pdf", None
    )
    assert isinstance(out_ok["schema_valid"]["value"], bool)


# ---------- _text_preservation 不变量补强 ----------


def test_text_preservation_empty_elements_and_chunks_equal_true():
    """两者都空 → equal True，precision/recall null empty_expected_and_actual。"""
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_only_images_equal_true():
    """elements 全是 image + chunks 空 → expected=actual='' → equal True。"""
    out = _text_preservation(
        [{"type": "image", "content": "x"}, {"type": "image"}], []
    )
    assert out["equal"]["value"] is True


def test_text_preservation_only_images_with_chunks_equal_false():
    """elements 全是 image + chunks 有内容 → expected='' < actual → equal False。"""
    out = _text_preservation(
        [{"type": "image", "content": "x"}], [{"text": "abc"}]
    )
    assert out["equal"]["value"] is False


def test_text_preservation_chunk_with_no_text_field():
    """chunk 没有 text 字段 → c.get('text') or '' → ''。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{}]  # no text field
    out = _text_preservation(elements, chunks)
    # actual = "" → equal False
    assert out["equal"]["value"] is False
    # precision null empty_actual
    assert out["precision"]["reason"] == "empty_actual"
    # recall = 0 / 3 = 0
    assert out["recall"]["value"] == 0.0


def test_text_preservation_element_no_content_field():
    """element 没有 content → e.get('content') or '' → ''。"""
    elements = [{"type": "paragraph"}]  # no content
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected = "" → equal False
    assert out["equal"]["value"] is False
    # precision = 0 / 3
    assert out["precision"]["value"] == 0.0
    # recall null empty_expected
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_dict_with_3_keys():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_precision_when_actual_has_repeats():
    """expected='ab', actual='aabb' → precision = 2/4 = 0.5。"""
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "aabb"}]
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 0.5
    assert out["recall"]["value"] == 1.0


# ---------- _silent_drop_count 边界补充 ----------


def test_silent_drop_count_expectations_with_none_element_count():
    """expectations.element_count_by_type = None → 当 falsy → no_expectations_element_count。"""
    out = _silent_drop_count({"x": 1}, {"element_count_by_type": None})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_with_empty_element_count():
    out = _silent_drop_count({"x": 1}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_expectations_no_element_count_key():
    """expectations 缺 element_count_by_type 字段 → .get returns None → 当 falsy。"""
    out = _silent_drop_count({"x": 1}, {"other_field": 1})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_returns_dict_with_2_keys():
    out = _silent_drop_count({}, {"element_count_by_type": {"x": 1}})
    assert set(out.keys()) == {"value", "reason"}


def test_silent_drop_count_with_many_types_summation():
    by_type = {"heading": 1, "paragraph": 0, "table": 3}
    exp = {
        "element_count_by_type": {
            "heading": 5,  # drop 4
            "paragraph": 5,  # drop 5
            "table": 3,  # drop 0
            "image": 2,  # drop 2 (not in actual)
        }
    }
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 4 + 5 + 2


def test_silent_drop_count_value_zero_is_int():
    by_type = {"x": 5}
    exp = {"element_count_by_type": {"x": 5}}
    out = _silent_drop_count(by_type, exp)
    assert out["value"] == 0
    assert isinstance(out["value"], int)


# ---------- _pdf_locator_ratio source level 补强 ----------


def test_pdf_locator_ratio_source_has_isinstance_int_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src


def test_pdf_locator_ratio_source_has_page_less_than_1_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "page < 1" in src


def test_pdf_locator_ratio_source_has_no_elements_branch():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not elements:" in src
    assert 'return _null("no_elements")' in src


def test_pdf_locator_ratio_source_has_bbox_check_branch():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src
    assert "_is_valid_bbox(bbox)" in src


def test_pdf_locator_ratio_source_has_valid_ratio_return():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "return _ratio(valid / len(elements))" in src


# ---------- _docx_locator_ratio source level 补强 ----------


def test_docx_locator_ratio_source_has_structural_keys_tuple():
    src = inspect.getsource(_docx_locator_ratio)
    assert "structural_keys = (" in src


def test_docx_locator_ratio_source_has_page_in_loc_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"page" in loc' in src
    assert '"bbox" in loc' in src


def test_docx_locator_ratio_source_has_any_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert "if not any(k in loc for k in structural_keys):" in src


def test_docx_locator_ratio_source_has_7_structural_keys_count():
    src = inspect.getsource(_docx_locator_ratio)
    # 计数 7 个 keys
    keys = [
        '"section"',
        '"paragraph_index"',
        '"run_index"',
        '"table_index"',
        '"row_index"',
        '"col_index"',
        '"relationship_id"',
    ]
    for k in keys:
        assert k in src


# ---------- _image_resource_ratio source level 补强 ----------


def test_image_resource_ratio_source_has_try_except_oserror():
    src = inspect.getsource(_image_resource_ratio)
    assert "try:" in src
    assert "except OSError:" in src


def test_image_resource_ratio_source_has_candidates_list():
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates: list[Path]" in src
    assert "candidates.append" in src


def test_image_resource_ratio_source_has_isfile_and_size_check():
    src = inspect.getsource(_image_resource_ratio)
    assert "p.is_file()" in src
    assert "p.stat().st_size > 0" in src


def test_image_resource_ratio_source_has_image_filter():
    src = inspect.getsource(_image_resource_ratio)
    assert 'e.get("type") == "image"' in src


def test_image_resource_ratio_source_has_rp_falsy_skip():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not rp:" in src


# ---------- _strip_unicode_whitespace source level 补强 ----------


def test_strip_unicode_whitespace_source_has_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "ch.isspace()" in src


def test_strip_unicode_whitespace_source_has_join():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert '"".join(' in src


def test_strip_unicode_whitespace_source_has_no_sort():
    """不排序，只过滤。"""
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "sorted" not in src
    assert "sort(" not in src


def test_strip_unicode_whitespace_source_signature():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "def _strip_unicode_whitespace(s: str) -> str:" in src


# ---------- _chunk_reference_ratio source level 补强 ----------


def test_chunk_reference_ratio_source_has_elem_ids_set():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "elem_ids = {e.get(\"element_id\") for e in elements}" in src


def test_chunk_reference_ratio_source_has_no_chunks_branch():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "if not chunks:" in src


def test_chunk_reference_ratio_source_has_ids_and_all_check():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "if ids and all(sid in elem_ids for sid in ids):" in src


# ---------- _heading_boundary_ratio source level 补强 ----------


def test_heading_boundary_ratio_source_has_headings_list():
    src = inspect.getsource(_heading_boundary_ratio)
    assert 'headings = [e for e in elements if e.get("type") == "heading"]' in src


def test_heading_boundary_ratio_source_has_chunk_first_ids_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids = set()" in src
    assert "chunk_first_ids.add(ids[0])" in src


def test_heading_boundary_ratio_source_has_no_headings_branch():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "if not headings:" in src


def test_heading_boundary_ratio_source_has_matched_sum():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "matched = sum(1 for h in headings" in src


# ---------- _silent_drop_count source level 补强 ----------


def test_silent_drop_count_source_has_no_expectations_branch():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expectations:" in src


def test_silent_drop_count_source_has_no_expectations_element_count_branch():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expected_counts:" in src


def test_silent_drop_count_source_has_max_zero_via_comparison():
    """代码用 if actual < exp 计算 drop（隐式 max(0, exp-actual)）。"""
    src = inspect.getsource(_silent_drop_count)
    assert "if actual < exp:" in src
    assert "drops += (exp - actual)" in src


# ---------- _is_valid_bbox source level 补强 ----------


def test_is_valid_bbox_source_has_isinstance_list_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(bbox, list)" in src


def test_is_valid_bbox_source_has_len_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "len(bbox) != 4" in src


def test_is_valid_bbox_source_has_bool_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(v, bool)" in src


def test_is_valid_bbox_source_has_math_isfinite():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite(v)" in src


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import json",
        "import csv",
        "import xml",
        "import configparser",
        "import argparse",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_counter_intersection_pattern():
    """text_preservation 用 Counter 交集。"""
    src = inspect.getsource(m)
    assert "c_expected & c_actual" in src


def test_module_source_has_counter_calls():
    src = inspect.getsource(m)
    assert "c_expected = Counter(expected)" in src
    assert "c_actual = Counter(actual)" in src


def test_module_source_has_for_loop_over_elements():
    src = inspect.getsource(m)
    assert "for e in elements:" in src


def test_module_source_has_for_loop_over_chunks():
    src = inspect.getsource(m)
    assert "for c in chunks:" in src


def test_module_source_has_for_loop_in_silent_drop():
    src = inspect.getsource(m)
    assert "for t, exp in expected_counts.items():" in src


def test_module_source_has_pipeline_success_with_and():
    src = inspect.getsource(m)
    assert "pipeline_success = error is None and document is not None" in src


def test_module_source_has_error_code_ternary():
    src = inspect.getsource(m)
    assert 'error["code"] if error' in src


def test_module_source_has_metrics_init_empty_dict():
    src = inspect.getsource(m)
    assert "metrics: dict[str, Any] = {}" in src


def test_module_source_has_lazy_schema_import():
    src = inspect.getsource(m)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_module_source_has_exception_type_name_in_reason():
    src = inspect.getsource(m)
    assert "schema_check_exception:{type(e).__name__}" in src


def test_module_source_has_text_preservation_section_divider():
    src = inspect.getsource(m)
    assert "---------- 子函数 ----------" in src


def test_module_source_has_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_has_no_global_keyword():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_has_no_async_keyword():
    src = inspect.getsource(m)
    assert "async def" not in src
    assert "await " not in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_has_return_metrics_at_end():
    """compute_automatic_metrics 末尾 return metrics。"""
    src = inspect.getsource(compute_automatic_metrics)
    # 末尾应当有 return metrics
    assert "return metrics" in src


def test_module_source_has_two_return_metrics_in_compute():
    """compute_automatic_metrics 有 2 处 return metrics（document=None + 正常）。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert src.count("return metrics") == 2


def test_module_source_has_elements_chunks_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'elements = document.get("elements", [])' in src
    assert 'chunks = document.get("chunks", [])' in src


def test_module_source_has_text_metrics_unpacking():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'text_metrics = _text_preservation(elements, chunks)' in src
    assert 'metrics["text_preservation_equal"] = text_metrics["equal"]' in src


# ---------- signatures 精确（compute_automatic_metrics） ----------


def test_compute_automatic_metrics_has_5_params():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5
    assert list(sig.parameters) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_no_default_for_first_4():
    sig = inspect.signature(compute_automatic_metrics)
    for name in ("document", "error", "source_type", "expectations"):
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_compute_automatic_metrics_default_for_image_base_dir():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_param_kinds():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_compute_automatic_metrics_no_varargs_varkw():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- signatures 精确（_pdf_locator_ratio 等 helpers） ----------


def test_pdf_locator_ratio_has_1_param():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1
    assert "elements" in sig.parameters


def test_docx_locator_ratio_has_1_param():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1
    assert "elements" in sig.parameters


def test_image_resource_ratio_has_2_params_no_default():
    """_image_resource_ratio 自身无 default（default 在 compute_automatic_metrics 调用处）。"""
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters) == ["elements", "image_base_dir"]
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_chunk_reference_ratio_has_2_params_no_default():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters) == ["elements", "chunks"]
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_heading_boundary_ratio_has_2_params_no_default():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters) == ["elements", "chunks"]


def test_silent_drop_count_has_2_params_no_default():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters) == ["by_type", "expectations"]


def test_text_preservation_has_2_params_no_default():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters) == ["elements", "chunks"]


def test_strip_unicode_whitespace_has_1_param():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters) == ["s"]


def test_is_valid_bbox_has_1_param():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters) == ["bbox"]


def test_null_ratio_bool_int_each_1_param():
    for fn in (_null, _ratio, _bool_metric, _int_metric):
        sig = inspect.signature(fn)
        assert len(sig.parameters) == 1


def test_null_param_name_is_reason():
    sig = inspect.signature(_null)
    assert "reason" in sig.parameters


def test_ratio_param_name_is_value():
    sig = inspect.signature(_ratio)
    assert "value" in sig.parameters


def test_bool_metric_param_name_is_value():
    sig = inspect.signature(_bool_metric)
    assert "value" in sig.parameters


def test_int_metric_param_name_is_value():
    sig = inspect.signature(_int_metric)
    assert "value" in sig.parameters


# ---------- 常量精确补强 ----------


def test_TEXT_TYPES_exact_7_entries():
    assert _TEXT_TYPES == (
        "heading",
        "paragraph",
        "list_item",
        "table",
        "caption",
        "header",
        "footer",
    )


def test_PDF_BBOX_REQUIRED_TYPES_exact_4_entries():
    assert _PDF_BBOX_REQUIRED_TYPES == (
        "heading",
        "paragraph",
        "caption",
        "list_item",
    )


def test_NOT_EVALUATED_exact_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_PDF_BBOX_REQUIRED_TYPES_is_subset_of_TEXT_TYPES():
    """PDF_BBOX 类型必须都在 TEXT_TYPES 里（文本类型才需 bbox）。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_TEXT_TYPES_includes_caption():
    """caption 是文本类型（参与 text_preservation）。"""
    assert "caption" in _TEXT_TYPES


def test_TEXT_TYPES_excludes_image():
    """image 不是文本类型。"""
    assert "image" not in _TEXT_TYPES


def test_constants_are_tuples():
    """_TEXT_TYPES 和 _PDF_BBOX 是 tuple 不是 list。"""
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_NOT_EVALUATED_is_string():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- 模块整体合理性 ----------


def test_module_namespace_is_evaluation_metrics():
    assert m.__name__ == "evaluation.metrics"


def test_module_all_only_compute_automatic_metrics():
    assert m.__all__ == ["compute_automatic_metrics"]


def test_module_has_1_public_function():
    public_fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.metrics"
    ]
    assert public_fns == ["compute_automatic_metrics"]


def test_module_has_13_private_functions():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    expected = {
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
    }
    assert set(private_fns) == expected
    assert len(private_fns) == 13


def test_module_has_3_private_constants():
    private_consts = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and not callable(getattr(m, n))
    ]
    assert set(private_consts) == {
        "_TEXT_TYPES",
        "_PDF_BBOX_REQUIRED_TYPES",
        "_NOT_EVALUATED",
    }


# ---------- 端到端集成补强 ----------


def test_e2e_docx_full_doc_with_all_text_types():
    """DOCX：5 个文本类型 + image，chunks 全部 intact。"""
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "para",
             "source_locator": {"paragraph_index": 1}},
            {"type": "list_item", "element_id": "l1", "content": "item",
             "source_locator": {"paragraph_index": 2}},
            {"type": "table", "element_id": "t1", "content": "cell",
             "source_locator": {"table_index": 0}},
            {"type": "caption", "element_id": "c1", "content": "cap",
             "source_locator": {"table_index": 0}},
            {"type": "image", "element_id": "i1", "resource_path": "x.png",
             "source_locator": {"relationship_id": "r1"}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "para", "source_element_ids": ["p1"]},
            {"text": "item", "source_element_ids": ["l1"]},
            {"text": "cell", "source_element_ids": ["t1"]},
            {"text": "cap", "source_element_ids": ["c1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["element_count_total"]["value"] == 6
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["image_resource_exists_ratio"]["value"] == 0.0  # 文件不存在


def test_e2e_pdf_full_doc_with_bboxes():
    """PDF：所有元素都有 page+bbox。"""
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
            {"type": "paragraph", "element_id": "p1", "content": "para",
             "source_locator": {"page": 1, "bbox": [0, 30, 100, 50]}},
            {"type": "caption", "element_id": "c1", "content": "cap",
             "source_locator": {"page": 2, "bbox": [0, 0, 100, 20]}},
            {"type": "list_item", "element_id": "l1", "content": "li",
             "source_locator": {"page": 2, "bbox": [0, 30, 100, 50]}},
        ],
        "chunks": [
            {"text": "title", "source_element_ids": ["h1"]},
            {"text": "paracapli", "source_element_ids": ["p1", "c1", "l1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_chunk_referencing_heading_first_match():
    """chunk source_element_ids 第一个是 heading → match。"""
    doc = {
        "elements": [
            {"type": "heading", "element_id": "h1", "content": "title",
             "source_locator": {"paragraph_index": 0}},
            {"type": "paragraph", "element_id": "p1", "content": "body",
             "source_locator": {"paragraph_index": 1}},
            {"type": "paragraph", "element_id": "p2", "content": "more",
             "source_locator": {"paragraph_index": 2}},
        ],
        "chunks": [
            {"text": "titlebody", "source_element_ids": ["h1", "p1"]},
            {"text": "more", "source_element_ids": ["p2"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["heading_boundary_compliance"]["value"] == 1.0


def test_e2e_pipeline_failed_returns_correct_metrics_dict():
    """document=None 时所有 11 个 metric 都 null pipeline_failed。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    expected_null_keys = [
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
    for k in expected_null_keys:
        assert out[k]["value"] is None, f"{k} should be None"
        assert out[k]["reason"] == "pipeline_failed", f"{k} should have pipeline_failed reason"


def test_e2e_pdf_with_invalid_page_in_some_elements():
    """混合 page valid/invalid。"""
    doc = {
        "elements": [
            {"type": "table", "source_locator": {"page": 1}},  # valid
            {"type": "table", "source_locator": {"page": 0}},  # invalid (page<1)
            {"type": "table", "source_locator": {}},  # invalid (no page)
            {"type": "table"},  # invalid (no locator)
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # 1 valid / 4 total = 0.25
    assert out["pdf_locator_valid_ratio"]["value"] == 0.25


def test_e2e_docx_with_image_existing_file(tmp_path):
    """DOCX 也可以有 image，image_resource_exists_ratio 同样适用。"""
    img = tmp_path / "img.png"
    img.write_bytes(b"data")
    doc = {
        "elements": [
            {"type": "paragraph", "element_id": "p1", "content": "hi",
             "source_locator": {"paragraph_index": 0}},
            {"type": "image", "element_id": "i1", "resource_path": str(img)},
        ],
        "chunks": [{"text": "hi", "source_element_ids": ["p1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None, image_base_dir=tmp_path)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_with_expectations_image_only():
    """expectations 只 cover image → image 不在 by_type（image 没 type）。"""
    # 注：image element 通常 type="image"，但 by_type 里 "image" 也会被计入
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1"},
            {"type": "paragraph", "element_id": "p1"},
        ],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"image": 1, "paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_text_preservation_with_whitespace_only_chunks():
    """chunks 全是空白 → actual stripped = "" → expected 也需空。"""
    doc = {
        "elements": [{"type": "paragraph", "content": "  "}],
        "chunks": [{"text": "   \n\t  "}],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # expected = "" (空白被 strip), actual = ""
    assert out["text_preservation_equal"]["value"] is True
    assert out["text_char_multiset_precision"]["reason"] == "empty_expected_and_actual"
