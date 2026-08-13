"""evaluation/metrics.py 第八十四轮 edges 测试（Round 620）。

补强 edges68 未触及的角度（第四十四批）。

新角度：
- _null / _ratio / _bool_metric / _int_metric 边界
- _strip_unicode_whitespace 各种 Unicode 空白
- _text_preservation equal=True/False
- _text_preservation precision/recall 计算
- _text_preservation empty_expected_and_actual
- _text_preservation empty_actual / empty_expected
- _heading_boundary_ratio no_heading_elements
- _heading_boundary_ratio mixed match
- _silent_drop_count no_expectations / no_expectations_element_count
- _silent_drop_count 实际比期望多（不算 drop）
- compute_automatic_metrics pipeline_failed 路径
- compute_automatic_metrics error_code 透传
- compute_automatic_metrics schema_valid 失败路径
- compute_automatic_metrics 各种 source_type 分支
- module source 字符串精确
- AST 结构
- forbidden tokens 第九十批
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


# ---------- _null / _ratio / _bool_metric / _int_metric ----------

def test_null_returns_dict_batch44():
    out = _null("why")
    assert isinstance(out, dict)


def test_null_keys_batch44():
    out = _null("why")
    assert set(out.keys()) == {"value", "reason"}


def test_null_value_is_none_batch44():
    assert _null("x")["value"] is None


def test_null_reason_passthrough_batch44():
    assert _null("my-reason")["reason"] == "my-reason"


def test_ratio_value_is_float_batch44():
    out = _ratio(0.5)
    assert isinstance(out["value"], float)


def test_ratio_value_exact_batch44():
    assert _ratio(0.5)["value"] == 0.5


def test_ratio_int_to_float_batch44():
    out = _ratio(1)
    assert isinstance(out["value"], float)
    assert out["value"] == 1.0


def test_ratio_reason_is_none_batch44():
    assert _ratio(0.5)["reason"] is None


def test_bool_metric_value_is_bool_batch44():
    assert isinstance(_bool_metric(True)["value"], bool)
    assert isinstance(_bool_metric(False)["value"], bool)


def test_bool_metric_value_exact_batch44():
    assert _bool_metric(True)["value"] is True
    assert _bool_metric(False)["value"] is False


def test_bool_metric_truthy_value_batch44():
    """传 truthy 非布尔值 → bool(True)。"""
    assert _bool_metric(1)["value"] is True
    assert _bool_metric("x")["value"] is True


def test_bool_metric_falsy_value_batch44():
    assert _bool_metric(0)["value"] is False
    assert _bool_metric("")["value"] is False


def test_int_metric_value_is_int_batch44():
    assert isinstance(_int_metric(5)["value"], int)


def test_int_metric_value_exact_batch44():
    assert _int_metric(5)["value"] == 5


def test_int_metric_float_truncates_batch44():
    """int(3.9) → 3。"""
    assert _int_metric(3.9)["value"] == 3


def test_int_metric_raises_on_string_batch44():
    with pytest.raises(ValueError):
        _int_metric("not a number")


# ---------- 常量 ----------

def test_text_types_value_batch44():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_pdf_bbox_required_types_value_batch44():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_text_types_is_tuple_batch44():
    assert isinstance(_TEXT_TYPES, tuple)


def test_pdf_bbox_required_types_is_tuple_batch44():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_is_subset_of_text_types_batch44():
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_text_types_count_7_batch44():
    assert len(_TEXT_TYPES) == 7


def test_pdf_bbox_required_count_4_batch44():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_not_evaluated_value_batch44():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_type_batch44():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- _strip_unicode_whitespace ----------

def test_strip_unicode_whitespace_empty_batch44():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_no_ws_batch44():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_whitespace_ascii_space_batch44():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_whitespace_tab_batch44():
    assert _strip_unicode_whitespace("a\tb") == "ab"


def test_strip_unicode_whitespace_newline_batch44():
    assert _strip_unicode_whitespace("a\nb") == "ab"


def test_strip_unicode_whitespace_nbsp_batch44():
    """NBSP \\u00a0 是 isspace() 空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space_batch44():
    """em space \\u2003 是 isspace() 空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space_batch44():
    """全角空格 \\u3000 是 isspace() 空白。"""
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_zero_width_not_stripped_batch44():
    """U+200B 零宽空格不是 isspace()，不删除。"""
    assert _strip_unicode_whitespace("a​b") == "a​b"


def test_strip_unicode_whitespace_preserves_order_batch44():
    assert _strip_unicode_whitespace("  c  b  a  ") == "cba"


def test_strip_unicode_whitespace_only_ws_batch44():
    assert _strip_unicode_whitespace("   \t\n  ") == ""


def test_strip_unicode_whitespace_preserves_punctuation_batch44():
    assert _strip_unicode_whitespace("a, b. c!") == "a,b.c!"


# ---------- _text_preservation ----------

def test_text_preservation_empty_empty_equal_true_batch44():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True


def test_text_preservation_empty_empty_precision_null_batch44():
    out = _text_preservation([], [])
    assert out["precision"]["value"] is None
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_null_batch44():
    """expected 有内容，actual 空 → equal=False, recall=null。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    out = _text_preservation(elements, [])
    assert out["equal"]["value"] is False
    # actual 空 → precision=null
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_empty_expected_null_batch44():
    """expected 空，actual 有内容 → recall=null。"""
    chunks = [{"text": "abc"}]
    out = _text_preservation([], chunks)
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_equal_true_batch44():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_equal_false_batch44():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "world", "source_element_ids": ["e1"]}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False


def test_text_preservation_precision_recall_with_partial_overlap_batch44():
    elements = [{"type": "paragraph", "content": "aabc"}]
    chunks = [{"text": "abcc"}]
    out = _text_preservation(elements, chunks)
    # expected = "aabc" (a*2, b*1, c*1)
    # actual = "abcc" (a*1, b*1, c*2)
    # common = min(a:2,1) + min(b:1,1) + min(c:1,2) = 1+1+1 = 3
    # precision = 3 / 4 = 0.75
    # recall = 3 / 4 = 0.75
    assert out["precision"]["value"] == 0.75
    assert out["recall"]["value"] == 0.75


def test_text_preservation_ignores_image_content_batch44():
    """image element 的 content 不参与 expected_sequence。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "xyz"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_strips_whitespace_batch44():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_returns_3_keys_batch44():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


# ---------- _heading_boundary_ratio ----------

def test_heading_boundary_no_heading_elements_batch44():
    elements = [{"type": "paragraph", "element_id": "e1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"
    assert out["value"] is None


def test_heading_boundary_no_chunks_batch44():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_perfect_match_batch44():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_partial_match_batch44():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"text": "x", "source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_no_match_batch44():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunk_no_ids_batch44():
    """chunk source_element_ids 空 → 不算 first id。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "x", "source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _silent_drop_count ----------

def test_silent_drop_no_expectations_batch44():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"
    assert out["value"] is None


def test_silent_drop_expectations_empty_dict_batch44():
    out = _silent_drop_count({"paragraph": 5}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_expectations_no_element_count_key_batch44():
    out = _silent_drop_count({"paragraph": 5}, {"other_key": "x"})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_expectations_empty_count_batch44():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_zero_when_actual_equals_expected_batch44():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_positive_when_actual_less_batch44():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 2


def test_silent_drop_zero_when_actual_more_batch44():
    """actual > expected 不算 drop。"""
    out = _silent_drop_count({"paragraph": 7}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_sums_across_types_batch44():
    out = _silent_drop_count(
        {"paragraph": 3, "heading": 1},
        {"element_count_by_type": {"paragraph": 5, "heading": 2}},
    )
    # (5-3) + (2-1) = 2 + 1 = 3
    assert out["value"] == 3


def test_silent_drop_missing_type_in_actual_batch44():
    """expected 中的类型 actual 没有 → 算 drop。"""
    out = _silent_drop_count({}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5


def test_silent_drop_extra_type_in_actual_batch44():
    """actual 有 expected 中没有的类型 → 不算 drop。"""
    out = _silent_drop_count({"image": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 5  # paragraph: 5-0=5, image: 不在 expected


# ---------- compute_automatic_metrics: pipeline_failed ----------

def test_compute_pipeline_failed_returns_14_metrics_batch44():
    out = compute_automatic_metrics(None, None, "pdf", None)
    # pipeline_success + error_code + schema_valid + 11 个后续 null 指标 = 14
    assert len(out) == 14


def test_compute_pipeline_failed_pipeline_success_false_batch44():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_pipeline_failed_error_code_none_batch44():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_pipeline_failed_schema_valid_batch44():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["schema_valid"]["reason"] == "pipeline_failed"


def test_compute_pipeline_failed_all_other_metrics_null_batch44():
    out = compute_automatic_metrics(None, None, "pdf", None)
    for name in (
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
    ):
        assert out[name]["value"] is None
        assert out[name]["reason"] == "pipeline_failed"


# ---------- compute_automatic_metrics: error_code ----------

def test_compute_with_error_code_batch44():
    err = {"code": "parse_failed", "message": "boom"}
    out = compute_automatic_metrics(None, err, "pdf", None)
    assert out["error_code"]["value"] == "parse_failed"
    assert out["pipeline_success"]["value"] is False


def test_compute_with_no_error_code_batch44():
    """error dict 但 code 字段缺失 → KeyError（实现严格访问 error['code']）。"""
    err = {"message": "no code"}
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, err, "pdf", None)


# ---------- compute_automatic_metrics: schema_valid ----------

def test_compute_schema_valid_passes_batch44():
    """document 通过 schema → schema_valid=True。"""
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["schema_valid"]["value"] is True


def test_compute_schema_valid_fails_batch44():
    """document 不过 schema → schema_valid=False。"""
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=False):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["schema_valid"]["value"] is False


def test_compute_schema_check_exception_batch44():
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", side_effect=ValueError("boom")):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["schema_valid"]["value"] is False
    assert "schema_check_exception:ValueError" in out["schema_valid"]["reason"]


# ---------- compute_automatic_metrics: source_type ----------

def test_compute_pdf_source_type_batch44():
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "pdf", None)
    # pdf_locator 是 _null (no_elements)，docx_locator 是 not_docx_document
    assert out["pdf_locator_valid_ratio"]["reason"] == "no_elements"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_docx_source_type_batch44():
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "no_elements"
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_unknown_source_type_batch44():
    """source_type 既非 pdf 也非 docx → 两个 locator 都 not_*。"""
    document = {"elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "html", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


# ---------- compute_automatic_metrics: element_count_total ----------

def test_compute_element_count_total_batch44():
    document = {"elements": [{"type": "paragraph"}, {"type": "heading"}], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2


def test_compute_element_count_by_type_batch44():
    document = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"paragraph": 2, "heading": 1}


def test_compute_element_count_by_type_unknown_type_batch44():
    """element 缺 type 字段 → 'unknown'。"""
    document = {"elements": [{}, {}], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        out = compute_automatic_metrics(document, None, "pdf", None)
    assert out["element_count_by_type"]["value"] == {"unknown": 2}


# ---------- __all__ ----------

def test_all_exact_batch44():
    assert set(metrics_mod.__all__) == {"compute_automatic_metrics"}


def test_all_count_1_batch44():
    assert len(metrics_mod.__all__) == 1


# ---------- module source ----------

def test_module_source_contains_design_principles_batch44():
    src = inspect.getsource(metrics_mod)
    assert "设计原则" in src


def test_module_source_contains_pure_function_batch44():
    src = inspect.getsource(metrics_mod)
    assert "纯函数" in src


def test_module_source_contains_text_preservation_batch44():
    src = inspect.getsource(metrics_mod)
    assert "text_preservation" in src


def test_module_source_contains_counter_batch44():
    src = inspect.getsource(metrics_mod)
    assert "Counter" in src


def test_module_source_contains_no_modify_batch44():
    src = inspect.getsource(metrics_mod)
    assert "不修改" in src


def test_module_source_contains_v11_batch44():
    src = inspect.getsource(metrics_mod)
    assert "v1.1" in src


def test_module_source_contains_v10_batch44():
    src = inspect.getsource(metrics_mod)
    assert "v1.0" in src


def test_module_source_contains_text_types_definition_batch44():
    src = inspect.getsource(metrics_mod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_definition_batch44():
    src = inspect.getsource(metrics_mod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_function_names_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "compute_automatic_metrics" in funcs
    assert "_pdf_locator_ratio" in funcs
    assert "_docx_locator_ratio" in funcs
    assert "_text_preservation" in funcs
    assert "_heading_boundary_ratio" in funcs
    assert "_silent_drop_count" in funcs
    assert "_is_valid_bbox" in funcs


def test_ast_top_level_no_try_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_top_level_no_for_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_top_level_no_while_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_top_level_no_async_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_from_future_first_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_imports_batch44():
    tree = ast.parse(inspect.getsource(metrics_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 3


# ---------- forbidden tokens 第九十批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(metrics_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(metrics_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(metrics_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(metrics_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(metrics_mod)
    assert "locals(" not in src


def test_source_no_open_batch44():
    src = inspect.getsource(metrics_mod)
    assert "open(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(metrics_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(metrics_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(metrics_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(metrics_mod)
    assert "pickle.load(" not in src
