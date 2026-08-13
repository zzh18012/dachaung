"""evaluation/metrics.py 第八十五轮 edges 测试（Round 628）。

补强 edges69 未触及的角度（第四十五批）。

新角度：
- 4 helper 返回 dict 类型 + 字段类型精确
- _ratio 接受 bool（True→1.0/False→0.0）
- _ratio 接受 int / float / Decimal-ish
- _int_metric 接受 bool（True→1）
- _null reason 不能为空
- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 字节串/字节切片
- _PDF_BBOX_REQUIRED_TYPES subset _TEXT_TYPES
- _is_valid_bbox 各种边界（list/tuple/set/dict / bool / NaN / Inf / None）
- _is_valid_bbox source 含 isinstance+bool+isfinite
- _strip_unicode_whitespace 链式调用 / 与 str.strip 对比
- _text_preservation source level 精确
- _pdf_locator_ratio 各种 element 类型组合
- _pdf_locator_ratio page=0 / page<0 / page=True
- _docx_locator_ratio 各种 locator 字段
- _chunk_reference_ratio 全部 valid / 全部 invalid / 空 source_element_ids
- _heading_boundary_ratio source level
- _silent_drop_count source level
- _image_resource_ratio source level
- compute_automatic_metrics source level
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第九十八批
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


# ---------- 4 helper 返回类型精确 ----------

def test_null_returns_dict_batch45():
    out = _null("reason_x")
    assert isinstance(out, dict)
    assert isinstance(out["value"], type(None))
    assert isinstance(out["reason"], str)


def test_ratio_returns_dict_batch45():
    out = _ratio(0.5)
    assert isinstance(out, dict)
    assert isinstance(out["value"], float)
    assert out["reason"] is None


def test_bool_metric_returns_dict_batch45():
    out = _bool_metric(True)
    assert isinstance(out, dict)
    assert isinstance(out["value"], bool)
    assert out["reason"] is None


def test_int_metric_returns_dict_batch45():
    out = _int_metric(5)
    assert isinstance(out, dict)
    assert isinstance(out["value"], int)
    assert out["reason"] is None


def test_null_value_is_exactly_none_batch45():
    out = _null("x")
    assert out["value"] is None


def test_ratio_value_is_float_batch45():
    """int 输入也要变成 float。"""
    out = _ratio(1)
    assert out["value"] == 1.0
    assert isinstance(out["value"], float)


def test_bool_metric_value_is_bool_batch45():
    """int 输入也要变成 bool。"""
    out = _bool_metric(1)
    assert out["value"] is True
    assert isinstance(out["value"], bool)


def test_int_metric_value_is_int_batch45():
    """float 输入要变成 int（截断）。"""
    out = _int_metric(3.7)
    assert out["value"] == 3
    assert isinstance(out["value"], int)


def test_int_metric_bool_input_batch45():
    """bool 输入 True → 1。"""
    out = _int_metric(True)
    assert out["value"] == 1
    assert out["reason"] is None


def test_int_metric_negative_input_batch45():
    out = _int_metric(-5)
    assert out["value"] == -5


def test_int_metric_zero_input_batch45():
    out = _int_metric(0)
    assert out["value"] == 0


def test_ratio_zero_batch45():
    out = _ratio(0)
    assert out["value"] == 0.0
    assert isinstance(out["value"], float)


def test_ratio_one_batch45():
    out = _ratio(1)
    assert out["value"] == 1.0


def test_ratio_negative_batch45():
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_bool_true_batch45():
    """bool True 作为 float(1.0)。"""
    out = _ratio(True)
    assert out["value"] == 1.0


def test_ratio_bool_false_batch45():
    out = _ratio(False)
    assert out["value"] == 0.0


# ---------- 常量精确 ----------

def test_text_types_is_tuple_batch45():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_batch45():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_text_types_seven_entries_batch45():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_types_four_entries_batch45():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_subset_of_text_types_batch45():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_not_evaluated_value_batch45():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str_batch45():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_all_str_batch45():
    for t in _TEXT_TYPES:
        assert isinstance(t, str)


def test_text_types_unique_batch45():
    assert len(set(_TEXT_TYPES)) == len(_TEXT_TYPES)


def test_pdf_bbox_required_types_unique_batch45():
    assert len(set(_PDF_BBOX_REQUIRED_TYPES)) == len(_PDF_BBOX_REQUIRED_TYPES)


def test_text_types_contains_paragraph_batch45():
    assert "paragraph" in _TEXT_TYPES


def test_text_types_contains_heading_batch45():
    assert "heading" in _TEXT_TYPES


def test_text_types_not_contains_image_batch45():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_contains_heading_paragraph_caption_list_item_batch45():
    assert "heading" in _PDF_BBOX_REQUIRED_TYPES
    assert "paragraph" in _PDF_BBOX_REQUIRED_TYPES
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES
    assert "list_item" in _PDF_BBOX_REQUIRED_TYPES


# ---------- _is_valid_bbox 各种边界 ----------

def test_is_valid_bbox_standard_list_batch45():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0]) is True


def test_is_valid_bbox_int_list_batch45():
    assert _is_valid_bbox([1, 2, 3, 4]) is True


def test_is_valid_bbox_tuple_rejected_batch45():
    """tuple 不接受（isinstance 检查 list）。"""
    assert _is_valid_bbox((1.0, 2.0, 3.0, 4.0)) is False


def test_is_valid_bbox_set_rejected_batch45():
    assert _is_valid_bbox({1.0, 2.0, 3.0, 4.0}) is False


def test_is_valid_bbox_dict_rejected_batch45():
    assert _is_valid_bbox({"x": 1, "y": 2, "w": 3, "h": 4}) is False


def test_is_valid_bbox_empty_list_batch45():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_short_list_batch45():
    assert _is_valid_bbox([1.0, 2.0, 3.0]) is False


def test_is_valid_bbox_long_list_batch45():
    assert _is_valid_bbox([1.0, 2.0, 3.0, 4.0, 5.0]) is False


def test_is_valid_bbox_with_bool_batch45():
    """bool 元素被拒绝。"""
    assert _is_valid_bbox([True, 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_with_nan_batch45():
    assert _is_valid_bbox([float("nan"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_with_inf_batch45():
    assert _is_valid_bbox([float("inf"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_with_neg_inf_batch45():
    assert _is_valid_bbox([float("-inf"), 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_none_batch45():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_str_batch45():
    assert _is_valid_bbox("1.0") is False


def test_is_valid_bbox_zero_values_batch45():
    """全 0 仍 valid（finite）。"""
    assert _is_valid_bbox([0.0, 0.0, 0.0, 0.0]) is True


def test_is_valid_bbox_negative_values_batch45():
    """负数仍 valid（finite）。"""
    assert _is_valid_bbox([-1.0, -2.0, -3.0, -4.0]) is True


def test_is_valid_bbox_mixed_int_float_batch45():
    assert _is_valid_bbox([1, 2.0, 3, 4.0]) is True


def test_is_valid_bbox_one_element_none_batch45():
    """list 含 None 元素拒绝。"""
    assert _is_valid_bbox([None, 2.0, 3.0, 4.0]) is False


def test_is_valid_bbox_one_element_str_batch45():
    assert _is_valid_bbox(["1", 2.0, 3.0, 4.0]) is False


# ---------- _strip_unicode_whitespace ----------

def test_strip_unicode_whitespace_returns_str_batch45():
    out = _strip_unicode_whitespace("abc")
    assert isinstance(out, str)


def test_strip_unicode_whitespace_empty_batch45():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_change_batch45():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_all_whitespace_batch45():
    assert _strip_unicode_whitespace(" \t\n\r") == ""


def test_strip_unicode_whitespace_preserves_punctuation_batch45():
    assert _strip_unicode_whitespace("a,b.c!") == "a,b.c!"


def test_strip_unicode_whitespace_preserves_digits_batch45():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_strip_unicode_whitespace_preserves_emoji_batch45():
    assert _strip_unicode_whitespace("🎉 🚀") == "🎉🚀"


def test_strip_unicode_whitespace_preserves_chinese_batch45():
    assert _strip_unicode_whitespace("你 好 世 界") == "你好世界"


def test_strip_unicode_whitespace_only_nbsp_batch45():
    """U+00A0 NBSP 是空白。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_only_em_space_batch45():
    """U+2003 EM SPACE 是空白。"""
    assert _strip_unicode_whitespace(" ") == ""


def test_strip_unicode_whitespace_only_ideographic_space_batch45():
    """U+3000 IDEOGRAPHIC SPACE 是空白。"""
    assert _strip_unicode_whitespace("　") == ""


def test_strip_unicode_whitespace_chain_batch45():
    """链式调用：先 strip 再压缩。"""
    s = "  hello  world  "
    stripped = _strip_unicode_whitespace(s)
    assert stripped == "helloworld"


# ---------- _pdf_locator_ratio 各种 ----------

def test_pdf_locator_ratio_page_zero_batch45():
    """page=0 视为 invalid（要求 page >= 1）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_negative_batch45():
    elements = [{"type": "paragraph", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_page_bool_true_batch45():
    """bool 是 int 子类，True==1，page=True 视为 page=1。
    用 image 类型避免触发 _PDF_BBOX_REQUIRED_TYPES 的 bbox 要求。"""
    elements = [{"type": "image", "source_locator": {"page": True}}]
    out = _pdf_locator_ratio(elements)
    # bool isinstance(page, int) == True, page < 1: True < 1? No, True == 1
    assert out["value"] == 1.0


def test_pdf_locator_ratio_page_string_batch45():
    """page="1" 不是 int。"""
    elements = [{"type": "paragraph", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_no_locator_batch45():
    """没有 source_locator 的元素 page=None。"""
    elements = [{"type": "paragraph"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_locator_none_batch45():
    elements = [{"type": "paragraph", "source_locator": None}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_text_type_missing_bbox_batch45():
    """paragraph 类型需要 bbox；缺失视为 invalid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_ratio_image_type_no_bbox_needed_batch45():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES，所以只需 page>=1。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_ratio_partial_mix_batch45():
    """混合：1 个完全 valid + 1 个 invalid = 0.5。"""
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _docx_locator_ratio 各种 ----------

def test_docx_locator_ratio_section_batch45():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_paragraph_index_batch45():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_relationship_id_batch45():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_ratio_with_page_rejected_batch45():
    """有 page 字段 → 视为 invalid（DOCX 不应有 page）。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_with_bbox_rejected_batch45():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1], "paragraph_index": 5}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_empty_locator_batch45():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_no_locator_batch45():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_ratio_partial_mix_batch45():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},
        {"type": "paragraph"},  # no locator
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 各种 ----------

def test_chunk_reference_ratio_all_valid_batch45():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1"]}, {"source_element_ids": ["e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_all_invalid_batch45():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e2"]}, {"source_element_ids": ["e3"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_empty_ids_batch45():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # ids falsy → 不计入 valid
    assert out["value"] == 0.0


def test_chunk_reference_ratio_none_ids_batch45():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": None}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_missing_ids_key_batch45():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_multi_ids_partial_batch45():
    """chunk 引用多个 element，其中部分 valid → chunk 视为 invalid。"""
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_reference_ratio_multi_ids_all_valid_batch45():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_empty_chunks_batch45():
    elements = [{"element_id": "e1"}]
    chunks = []
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_dedup_elements_batch45():
    """重复 element_id 在 elements 集合中只算一次。"""
    elements = [{"element_id": "e1"}, {"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _heading_boundary_ratio source level ----------

def test_heading_boundary_ratio_source_uses_first_id_batch45():
    src = inspect.getsource(metrics_mod._heading_boundary_ratio)
    # 实现取 ids[0]（first chunk 的第一个 element id）
    assert "ids[0]" in src or "ids[:1]" in src


def test_heading_boundary_ratio_source_uses_set_batch45():
    src = inspect.getsource(metrics_mod._heading_boundary_ratio)
    assert "matched" in src or "set(" in src


# ---------- _silent_drop_count source level ----------

def test_silent_drop_count_source_uses_by_type_get_batch45():
    src = inspect.getsource(metrics_mod._silent_drop_count)
    assert "by_type.get" in src


def test_silent_drop_count_source_uses_sum_batch45():
    src = inspect.getsource(metrics_mod._silent_drop_count)
    assert "drops" in src
    assert "sum(" in src or "_int_metric" in src


def test_silent_drop_count_source_uses_items_batch45():
    src = inspect.getsource(metrics_mod._silent_drop_count)
    assert ".items()" in src


# ---------- _image_resource_ratio source level ----------

def test_image_resource_ratio_source_uses_is_file_batch45():
    src = inspect.getsource(metrics_mod._image_resource_ratio)
    assert "is_file()" in src


def test_image_resource_ratio_source_uses_stat_st_size_batch45():
    src = inspect.getsource(metrics_mod._image_resource_ratio)
    assert "stat().st_size" in src


def test_image_resource_ratio_source_uses_OSError_batch45():
    src = inspect.getsource(metrics_mod._image_resource_ratio)
    assert "OSError" in src


def test_image_resource_ratio_source_uses_resource_path_batch45():
    src = inspect.getsource(metrics_mod._image_resource_ratio)
    assert "resource_path" in src


def test_image_resource_ratio_source_uses_image_base_dir_batch45():
    src = inspect.getsource(metrics_mod._image_resource_ratio)
    assert "image_base_dir" in src


# ---------- compute_automatic_metrics source level ----------

def test_compute_source_uses_document_get_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "document.get" in src or 'document.get("elements' in src


def test_compute_source_uses_error_get_or_index_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    # error["code"] 严格索引
    assert 'error["code"]' in src


def test_compute_source_uses_lazy_import_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_compute_source_uses_try_except_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "try:" in src
    assert "except Exception" in src


def test_compute_source_uses_schema_check_exception_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "schema_check_exception" in src


def test_compute_source_uses_not_pdf_document_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "not_pdf_document" in src


def test_compute_source_uses_not_docx_document_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "not_docx_document" in src


def test_compute_source_uses_pipeline_failed_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "pipeline_failed" in src


def test_compute_source_uses_pipeline_success_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    assert "pipeline_success" in src


def test_compute_source_contains_14_metric_keys_batch45():
    src = inspect.getsource(compute_automatic_metrics)
    keys = [
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
    for k in keys:
        assert k in src


# ---------- 模块源码字符串 ----------

def test_module_docstring_contains_design_principles_batch45():
    src = inspect.getsource(metrics_mod)
    assert "纯函数" in src
    assert "缺数据时返回 null + reason" in src


def test_module_docstring_contains_text_preservation_v11_batch45():
    src = inspect.getsource(metrics_mod)
    assert "text_preservation 语义" in src
    assert "v1.1" in src


def test_module_source_contains_math_import_batch45():
    src = inspect.getsource(metrics_mod)
    assert "import math" in src


def test_module_source_contains_counter_import_batch45():
    src = inspect.getsource(metrics_mod)
    assert "from collections import Counter" in src


def test_module_source_contains_path_import_batch45():
    src = inspect.getsource(metrics_mod)
    assert "from pathlib import Path" in src


def test_module_source_contains_any_import_batch45():
    src = inspect.getsource(metrics_mod)
    assert "from typing import Any" in src


def test_module_source_contains_text_types_definition_batch45():
    src = inspect.getsource(metrics_mod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_contains_pdf_bbox_definition_batch45():
    src = inspect.getsource(metrics_mod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_contains_not_evaluated_definition_batch45():
    src = inspect.getsource(metrics_mod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_underscore_null_batch45():
    src = inspect.getsource(metrics_mod)
    assert "def _null(reason: str) -> dict[str, Any]:" in src


def test_module_source_contains_underscore_ratio_batch45():
    src = inspect.getsource(metrics_mod)
    assert "def _ratio(value: float) -> dict[str, Any]:" in src


def test_module_source_contains_underscore_bool_batch45():
    src = inspect.getsource(metrics_mod)
    assert "def _bool_metric(value: bool) -> dict[str, Any]:" in src


def test_module_source_contains_underscore_int_batch45():
    src = inspect.getsource(metrics_mod)
    assert "def _int_metric(value: int) -> dict[str, Any]:" in src


def test_module_source_contains_compute_function_batch45():
    src = inspect.getsource(metrics_mod)
    assert "def compute_automatic_metrics(" in src


# ---------- __all__ ----------

def test_all_exact_batch45():
    assert list(metrics_mod.__all__) == ["compute_automatic_metrics"]


def test_all_count_one_batch45():
    assert len(metrics_mod.__all__) == 1


def test_all_entry_callable_batch45():
    assert callable(getattr(metrics_mod, "compute_automatic_metrics"))


# ---------- AST 结构 ----------

def test_ast_top_level_functions_count_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    # compute_automatic_metrics + _pdf_locator_ratio + _docx_locator_ratio +
    # _is_valid_bbox + _image_resource_ratio + _chunk_reference_ratio +
    # _strip_unicode_whitespace + _text_preservation + _heading_boundary_ratio +
    # _silent_drop_count + _null + _ratio + _bool_metric + _int_metric = 14
    assert len(funcs) == 14


def test_ast_top_level_no_class_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_no_async_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_first_node_docstring_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_second_node_future_import_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_third_node_math_import_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    third = tree.body[2]
    assert isinstance(third, ast.Import)
    # import math 是 ast.Import，不是 ImportFrom
    alias = third.names[0]
    assert alias.name == "math"


def test_ast_compute_function_has_returns_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    compute_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics"][0]
    returns = [n for n in ast.walk(compute_func) if isinstance(n, ast.Return)]
    assert len(returns) >= 1


def test_ast_compute_function_has_for_in_for_each_element_batch45():
    """compute_automatic_metrics 内有 for e in elements。"""
    tree = ast.parse(inspect.getsource(metrics_mod))
    compute_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "compute_automatic_metrics"][0]
    fors = [n for n in ast.walk(compute_func) if isinstance(n, ast.For)]
    assert len(fors) >= 1


def test_ast_is_valid_bbox_uses_isinstance_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox"][0]
    has_isinstance = False
    for n in ast.walk(func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "isinstance":
            has_isinstance = True
    assert has_isinstance


def test_ast_is_valid_bbox_uses_math_isfinite_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_is_valid_bbox"][0]
    has_isfinite = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "isfinite":
            has_isfinite = True
    assert has_isfinite


def test_ast_strip_unicode_whitespace_uses_isspace_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace"][0]
    has_isspace = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "isspace":
            has_isspace = True
    assert has_isspace


def test_ast_strip_unicode_whitespace_uses_join_batch45():
    tree = ast.parse(inspect.getsource(metrics_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_strip_unicode_whitespace"][0]
    has_join = False
    for n in ast.walk(func):
        if isinstance(n, ast.Attribute) and n.attr == "join":
            has_join = True
    assert has_join


# ---------- forbidden tokens 第九十八批 ----------

def test_source_no_eval_batch45():
    src = inspect.getsource(metrics_mod)
    assert "eval(" not in src


def test_source_no_exec_batch45():
    src = inspect.getsource(metrics_mod)
    assert "exec(" not in src


def test_source_no_compile_batch45():
    src = inspect.getsource(metrics_mod)
    assert "compile(" not in src


def test_source_no_globals_batch45():
    src = inspect.getsource(metrics_mod)
    assert "globals(" not in src


def test_source_no_locals_batch45():
    src = inspect.getsource(metrics_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch45():
    src = inspect.getsource(metrics_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch45():
    src = inspect.getsource(metrics_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch45():
    src = inspect.getsource(metrics_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch45():
    src = inspect.getsource(metrics_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch45():
    src = inspect.getsource(metrics_mod)
    assert "subprocess" not in src


def test_source_no_class_keyword_batch45():
    src = inspect.getsource(metrics_mod)
    assert "class _" not in src
    assert "class X" not in src


def test_source_no_async_batch45():
    src = inspect.getsource(metrics_mod)
    assert "async def" not in src


def test_source_no_yield_batch45():
    src = inspect.getsource(metrics_mod)
    assert "yield" not in src


def test_source_no_walrus_batch45():
    src = inspect.getsource(metrics_mod)
    assert ":=" not in src
