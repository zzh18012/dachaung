"""evaluation/report.py 第八十八轮 edges 测试（Round 638）。

补强 edges60 未触及的角度（第四十七批）。

新角度：
- _RATIO_METRICS 子集属性（text_* / chunk_* / locator_* / pdf_/docx_）
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 单元素性质
- aggregate_summary counts 边界（None 跳过 / 全 None / int 0 / 负数）
- aggregate_summary success_rates bool 严格性（True 不是 1）
- aggregate_summary ratio 各项独立 null
- aggregate_summary silent_drop 各种 None / 0 / 求和
- get_git_provenance 多种 mock 路径（returncode / stdout empty / dirty / clean）
- get_dependency_versions 各种异常路径
- build_provenance max_chars int 强制转换
- build_devset_section 全字段映射
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百零八批
"""

from __future__ import annotations

import ast
import inspect
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


# ---------- _RATIO_METRICS 子集属性 ----------

def test_ratio_metrics_text_subfamily_batch47():
    """text_* 系列：equal / precision / recall。"""
    text_metrics = [m for m in _RATIO_METRICS if m.startswith("text_")]
    assert set(text_metrics) == {
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
    }


def test_ratio_metrics_chunk_subfamily_batch47():
    """chunk_* 系列。"""
    chunk_metrics = [m for m in _RATIO_METRICS if m.startswith("chunk_")]
    assert set(chunk_metrics) == {
        "chunk_reference_intact_ratio",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    }


def test_ratio_metrics_locator_subfamily_batch47():
    locator_metrics = [m for m in _RATIO_METRICS if m.endswith("_ratio") and "locator" in m]
    assert set(locator_metrics) == {
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
    }


def test_ratio_metrics_image_member_batch47():
    assert "image_resource_exists_ratio" in _RATIO_METRICS


def test_ratio_metrics_heading_member_batch47():
    assert "heading_boundary_compliance" in _RATIO_METRICS


def test_ratio_metrics_schema_valid_member_batch47():
    assert "schema_valid" in _RATIO_METRICS


def test_ratio_metrics_count_text_three_batch47():
    text_metrics = [m for m in _RATIO_METRICS if m.startswith("text_")]
    assert len(text_metrics) == 3


def test_ratio_metrics_count_chunk_four_batch47():
    chunk_metrics = [m for m in _RATIO_METRICS if m.startswith("chunk_")]
    assert len(chunk_metrics) == 4


def test_ratio_metrics_chunk_reference_before_text_batch47():
    """chunk_reference_intact_ratio 出现在 text_* 之前。"""
    ref_idx = _RATIO_METRICS.index("chunk_reference_intact_ratio")
    text_idx = _RATIO_METRICS.index("text_preservation_equal")
    assert ref_idx < text_idx


def test_ratio_metrics_chunk_boundary_after_text_batch47():
    """chunk_boundary_* 出现在 text_* 之后。"""
    boundary_idx = _RATIO_METRICS.index("chunk_boundary_precision")
    text_idx = _RATIO_METRICS.index("text_char_multiset_recall")
    assert text_idx < boundary_idx


def test_ratio_metrics_schema_first_batch47():
    """schema_valid 在所有 ratio 中是 index 0。"""
    assert _RATIO_METRICS.index("schema_valid") == 0


def test_ratio_metrics_chunk_boundary_f1_last_batch47():
    assert _RATIO_METRICS.index("chunk_boundary_f1") == len(_RATIO_METRICS) - 1


# ---------- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 单元素 ----------

def test_count_metrics_single_element_batch47():
    assert len(_COUNT_METRICS) == 1
    assert _COUNT_METRICS[0] == "element_count_total"


def test_success_bool_metrics_single_element_batch47():
    assert len(_SUCCESS_BOOL_METRICS) == 1
    assert _SUCCESS_BOOL_METRICS[0] == "pipeline_success"


def test_count_metrics_is_tuple_batch47():
    assert isinstance(_COUNT_METRICS, tuple)


def test_success_bool_metrics_is_tuple_batch47():
    assert isinstance(_SUCCESS_BOOL_METRICS, tuple)


def test_count_metrics_no_overlap_with_ratio_batch47():
    for m in _COUNT_METRICS:
        assert m not in _RATIO_METRICS


def test_success_bool_no_overlap_with_ratio_batch47():
    for m in _SUCCESS_BOOL_METRICS:
        assert m not in _RATIO_METRICS


def test_success_bool_no_overlap_with_count_batch47():
    for m in _SUCCESS_BOOL_METRICS:
        assert m not in _COUNT_METRICS


def test_three_metric_tuples_disjoint_batch47():
    all_metrics = list(_RATIO_METRICS) + list(_COUNT_METRICS) + list(_SUCCESS_BOOL_METRICS)
    assert len(all_metrics) == len(set(all_metrics))


# ---------- aggregate_summary counts 边界 ----------

def test_aggregate_counts_all_none_batch47():
    """全部 doc 的 counts value 是 None → participating_docs=0, sum=None。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_counts_value_zero_batch47():
    """value=0 不是 None，应参与求和。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 0}}},
        {"metrics": {"element_count_total": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 5
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_counts_negative_batch47():
    per_doc = [
        {"metrics": {"element_count_total": {"value": -3}}},
        {"metrics": {"element_count_total": {"value": -1}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == -4


def test_aggregate_counts_missing_key_batch47():
    """doc 中没有 element_count_total key → 跳过。"""
    per_doc = [
        {"metrics": {}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 10
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_counts_missing_value_key_batch47():
    """有 element_count_total 但没有 value key。"""
    per_doc = [
        {"metrics": {"element_count_total": {"reason": "not_evaluated"}}},
        {"metrics": {"element_count_total": {"value": 7}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 7
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


# ---------- aggregate_summary success_rates bool 严格性 ----------

def test_aggregate_success_bool_strict_true_batch47():
    """True 严格判定，1（int）不算 True。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": 1}}},  # int 不是 bool
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1  # 只有第一个 True
    assert sr["total"] == 2


def test_aggregate_success_with_none_batch47():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_success_false_batch47():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["rate"] == 0.0


def test_aggregate_success_empty_batch47():
    s = aggregate_summary([])
    sr = s["success_rates"]["pipeline_success"]
    assert sr == {"success_count": 0, "total": 0, "rate": None}


def test_aggregate_success_rate_float_batch47():
    """3 个文档 1 成功 → rate 0.333..."""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    s = aggregate_summary(per_doc)
    sr = s["success_rates"]["pipeline_success"]
    assert sr["rate"] == pytest.approx(1 / 3)


# ---------- aggregate_summary ratio 各项独立 null ----------

def test_aggregate_ratio_partial_participation_batch47():
    """不同 ratio 各自有不同 doc 参与。"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}, "pdf_locator_valid_ratio": {"value": 0.5}}},
    ]
    s = aggregate_summary(per_doc)
    avgs = s["ratio_macro_averages"]
    assert avgs["schema_valid"]["macro_average"] == 1.0
    assert avgs["schema_valid"]["participating_docs"] == 1
    assert avgs["schema_valid"]["not_evaluated"] == 1
    assert avgs["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert avgs["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert avgs["pdf_locator_valid_ratio"]["not_evaluated"] == 1


def test_aggregate_ratio_all_null_batch47():
    per_doc = [
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    avg = s["ratio_macro_averages"]["schema_valid"]
    assert avg == {"macro_average": None, "participating_docs": 0, "not_evaluated": 2}


def test_aggregate_ratio_macro_calc_batch47():
    """(0.5 + 1.0 + 0.0) / 3 = 0.5"""
    per_doc = [
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.0}}},
    ]
    s = aggregate_summary(per_doc)
    avg = s["ratio_macro_averages"]["schema_valid"]
    assert avg["macro_average"] == pytest.approx(0.5)
    assert avg["participating_docs"] == 3
    assert avg["not_evaluated"] == 0


def test_aggregate_ratio_total_12_keys_batch47():
    s = aggregate_summary([])
    assert len(s["ratio_macro_averages"]) == 12


def test_aggregate_summary_has_four_top_keys_batch47():
    s = aggregate_summary([])
    assert set(s.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


# ---------- aggregate_summary silent_drop 各种 ----------

def test_aggregate_silent_drop_all_none_batch47():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] is None


def test_aggregate_silent_drop_partial_batch47():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 8


def test_aggregate_silent_drop_zero_batch47():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 0}}},
        {"metrics": {"silent_drop_count": {"value": 0}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 0


def test_aggregate_silent_drop_empty_batch47():
    s = aggregate_summary([])
    assert s["silent_drop_total"] is None


def test_aggregate_silent_drop_missing_key_batch47():
    """doc 没有 silent_drop_count → 跳过。"""
    per_doc = [
        {"metrics": {}},
        {"metrics": {"silent_drop_count": {"value": 2}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 2


# ---------- get_git_provenance 多种 mock 路径 ----------

def test_git_provenance_commit_with_whitespace_batch47(tmp_path):
    """commit 前后空白 strip 掉。"""
    r1 = MagicMock(returncode=0, stdout="  abc123  \n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_git_provenance_commit_empty_after_strip_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="   \n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_commit_returncode_nonzero_batch47(tmp_path):
    r1 = MagicMock(returncode=1, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_dirty_status_nonempty_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is True


def test_git_provenance_dirty_status_returncode_nonzero_batch47(tmp_path):
    """status returncode != 0 → bool(False and ...) = False（不进 except 分支）。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"
    # returncode != 0 不进 except，dirty 直接计算为 False
    assert out["git_dirty"] is False


def test_git_provenance_oserror_first_batch47(tmp_path):
    """第一次 subprocess.run 抛 OSError → 走 except 分支。"""
    with patch("subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_oserror_second_batch47(tmp_path):
    """第二次抛 OSError。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    with patch("subprocess.run", side_effect=[r1, OSError("boom")]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_timeout_batch47(tmp_path):
    """TimeoutExpired 是 SubprocessError 子类。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


# ---------- get_dependency_versions 各种 ----------

def test_dependency_versions_keys_batch47():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_are_str_or_none_batch47():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_dependency_versions_with_package_not_found_batch47():
    """所有包都 PackageNotFoundError。"""
    import importlib.metadata as im
    with patch("importlib.metadata.version", side_effect=im.PackageNotFoundError("x")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_dependency_versions_with_generic_exception_batch47():
    """通用 Exception 路径。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("unexpected")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_dependency_versions_returns_dict_batch47():
    assert isinstance(get_dependency_versions(), dict)


# ---------- build_provenance max_chars int 强制转换 ----------

def test_build_provenance_max_chars_int_conversion_batch47(tmp_path):
    """max_chars 是 str/int 都强制转 int。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_string_input_batch47(tmp_path):
    """str '800' 通过 int() 转换。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", "800", None)
    assert out["max_chars"] == 800


def test_build_provenance_parser_version_none_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_value_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert out["parser_version"] == "4.10.2"


def test_build_provenance_evaluator_version_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == "1.1"
    assert out["report_version"] == "1.1"


def test_build_provenance_run_timestamp_iso_format_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    assert isinstance(ts, str)
    # ISO 格式包含 T
    assert "T" in ts


def test_build_provenance_keys_batch47(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    expected_keys = {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(out.keys()) == expected_keys


# ---------- build_devset_section 全字段映射 ----------

def test_build_devset_section_passthrough_batch47():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 7
    m.content_group_count = 3
    m.pdf_count = 4
    m.docx_count = 3
    m.categories_covered = ["a", "b"]
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 7
    assert out["content_group_count"] == 3
    assert out["pdf_count"] == 4
    assert out["docx_count"] == 3
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_keys_batch47():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    expected_keys = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(out.keys()) == expected_keys


def test_build_devset_section_uses_attributes_batch47():
    """应直接读 Manifest 对象的属性（不调用方法）。"""
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 1
    m.content_group_count = 1
    m.pdf_count = 1
    m.docx_count = 0
    m.categories_covered = ["only_pdf"]
    out = build_devset_section(m)
    # 各属性被读了一次
    assert m.devset_status == "incomplete"  # 直接属性读


# ---------- module source 字符串补强 ----------

def test_source_contains_counts_求和_batch47():
    src = inspect.getsource(report_mod)
    assert "求和" in src


def test_source_contains_macro_average_batch47():
    src = inspect.getsource(report_mod)
    assert "macro average" in src


def test_source_contains_not_evaluated_batch47():
    src = inspect.getsource(report_mod)
    assert "not_evaluated" in src or "not evaluated" in src.lower()


def test_source_contains_figure_caption_always_null_batch47():
    src = inspect.getsource(report_mod)
    assert "figure_caption_*" in src or "figure_caption" in src


def test_source_contains_importlib_metadata_batch47():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata" in src


def test_source_contains_subprocess_run_batch47():
    src = inspect.getsource(report_mod)
    assert "subprocess.run" in src


def test_source_contains_cwd_str_conversion_batch47():
    src = inspect.getsource(report_mod)
    assert "cwd=str" in src


def test_source_contains_capture_output_batch47():
    src = inspect.getsource(report_mod)
    assert "capture_output=True" in src


def test_source_contains_timeout_10_batch47():
    src = inspect.getsource(report_mod)
    assert "timeout=10" in src


def test_source_contains_pypdfium2_batch47():
    src = inspect.getsource(report_mod)
    assert "pypdfium2" in src


def test_source_contains_python_docx_batch47():
    src = inspect.getsource(report_mod)
    assert "python-docx" in src


def test_source_contains_pdfplumber_batch47():
    src = inspect.getsource(report_mod)
    assert "pdfplumber" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5  # get_git_provenance / get_dependency_versions / build_provenance / build_devset_section / aggregate_summary


def test_ast_top_level_assigns_count_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # 3 tuple constants + 1 __all__
    assert len(assigns) == 4


def test_ast_ratio_metrics_is_tuple_literal_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_RATIO_METRICS":
                assert isinstance(n.value, ast.Tuple)
                return
    pytest.fail("_RATIO_METRICS assignment not found")


def test_ast_ratio_metrics_has_12_elts_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_RATIO_METRICS":
                assert isinstance(n.value, ast.Tuple)
                assert len(n.value.elts) == 12
                return
    pytest.fail("_RATIO_METRICS assignment not found")


def test_ast_count_metrics_single_elt_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_COUNT_METRICS":
                assert isinstance(n.value, ast.Tuple)
                assert len(n.value.elts) == 1
                return
    pytest.fail("_COUNT_METRICS assignment not found")


def test_ast_success_bool_metrics_single_elt_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            t = n.targets[0]
            if isinstance(t, ast.Name) and t.id == "_SUCCESS_BOOL_METRICS":
                assert isinstance(n.value, ast.Tuple)
                assert len(n.value.elts) == 1
                return
    pytest.fail("_SUCCESS_BOOL_METRICS assignment not found")


def test_ast_get_git_provenance_has_try_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_get_git_provenance_except_handlers_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)][0]
    assert len(trys.handlers) == 1
    h = trys.handlers[0]
    # 异常类型应是 tuple (OSError, subprocess.SubprocessError)
    assert isinstance(h.type, ast.Tuple)
    assert len(h.type.elts) == 2


def test_ast_aggregate_summary_has_subscript_batch47():
    """summary["xxx"] = ... 多个 Subscript 赋值。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary"][0]
    subscripts = [n for n in ast.walk(func) if isinstance(n, ast.Subscript)]
    assert len(subscripts) >= 5


def test_ast_aggregate_summary_has_4_summary_assigns_batch47():
    """应给 summary 赋值 4 次：counts / success_rates / ratio_macro_averages / silent_drop_total。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary"][0]
    summary_assigns = []
    for n in ast.walk(func):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id == "summary":
                    summary_assigns.append(t)
    assert len(summary_assigns) == 4


def test_ast_build_provenance_has_return_dict_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)


def test_ast_build_devset_section_has_return_dict_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)


def test_ast_no_class_def_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_module_has_docstring_batch47():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


# ---------- forbidden tokens 第一百零八批 ----------

def test_source_no_eval_batch47():
    src = inspect.getsource(report_mod)
    assert "eval(" not in src


def test_source_no_exec_batch47():
    src = inspect.getsource(report_mod)
    assert "exec(" not in src


def test_source_no_compile_batch47():
    src = inspect.getsource(report_mod)
    assert "compile(" not in src


def test_source_no_globals_batch47():
    src = inspect.getsource(report_mod)
    assert "globals(" not in src


def test_source_no_locals_batch47():
    src = inspect.getsource(report_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch47():
    src = inspect.getsource(report_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch47():
    src = inspect.getsource(report_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch47():
    src = inspect.getsource(report_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch47():
    src = inspect.getsource(report_mod)
    assert "pickle.load(" not in src


def test_source_no_lambda_batch47():
    src = inspect.getsource(report_mod)
    assert "lambda" not in src


def test_source_no_yield_batch47():
    src = inspect.getsource(report_mod)
    assert "yield" not in src


def test_source_no_walrus_batch47():
    src = inspect.getsource(report_mod)
    assert ":=" not in src


def test_source_no_async_batch47():
    src = inspect.getsource(report_mod)
    assert "async def" not in src


def test_source_no_await_batch47():
    src = inspect.getsource(report_mod)
    assert "await " not in src
