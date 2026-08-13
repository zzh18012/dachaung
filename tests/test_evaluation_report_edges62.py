"""evaluation/report.py 第八十九轮 edges 测试（Round 646）。

补强 edges61 未触及的角度（第四十八批）。

新角度：
- aggregate_summary 多文档混合（counts / success / ratio / silent_drop）
- aggregate_summary 极端边界（单文档 / 100 文档 / 重复 doc_id）
- get_git_provenance stdout 含特殊字符
- get_dependency_versions mock importlib 失败
- build_provenance 字段精确（9 keys 顺序）
- build_devset_section 边界
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十六批
"""

from __future__ import annotations

import ast
import inspect
import subprocess
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


# ---------- aggregate_summary 多文档混合 ----------

def test_aggregate_mixed_full_batch48():
    """完整多文档混合：counts + success + ratio + silent。"""
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 10},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "pdf_locator_valid_ratio": {"value": 0.8},
                "silent_drop_count": {"value": 2},
            }
        },
        {
            "metrics": {
                "element_count_total": {"value": 5},
                "pipeline_success": {"value": False},
                "schema_valid": {"value": 0.5},
                "pdf_locator_valid_ratio": {"value": None},
                "silent_drop_count": {"value": None},
            }
        },
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 15
    assert s["counts"]["element_count_total"]["participating_docs"] == 2
    sr = s["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5
    avgs = s["ratio_macro_averages"]
    assert avgs["schema_valid"]["macro_average"] == 0.75
    assert avgs["schema_valid"]["participating_docs"] == 2
    assert avgs["pdf_locator_valid_ratio"]["macro_average"] == 0.8
    assert avgs["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert s["silent_drop_total"] == 2


def test_aggregate_single_doc_batch48():
    per_doc = [
        {
            "metrics": {
                "element_count_total": {"value": 100},
                "pipeline_success": {"value": True},
                "schema_valid": {"value": 1.0},
                "silent_drop_count": {"value": 5},
            }
        }
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 100
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["silent_drop_total"] == 5


def test_aggregate_100_docs_batch48():
    """100 个文档全成功。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}, "schema_valid": {"value": 1.0}}}
        for _ in range(100)
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 100
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_duplicate_doc_id_batch48():
    """doc_id 重复不影响 aggregate（aggregate 不看 doc_id）。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 2


# ---------- aggregate_summary 极端边界 ----------

def test_aggregate_metrics_empty_dict_batch48():
    """doc 的 metrics 是空 dict → 所有指标 null。"""
    per_doc = [{"metrics": {}}]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}
    assert s["success_rates"]["pipeline_success"] == {"success_count": 0, "total": 1, "rate": 0.0}
    for k, v in s["ratio_macro_averages"].items():
        assert v["macro_average"] is None
        assert v["participating_docs"] == 0
        assert v["not_evaluated"] == 1
    assert s["silent_drop_total"] is None


def test_aggregate_metrics_value_only_no_reason_batch48():
    """metric 只有 value 没 reason → 仍能聚合。"""
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},  # 没 reason
    ]
    s = aggregate_summary(per_doc)
    assert s["counts"]["element_count_total"]["sum"] == 5


def test_aggregate_metrics_with_extra_unknown_key_batch48():
    """metric 含未知 key → 跳过。"""
    per_doc = [
        {"metrics": {"unknown_metric": {"value": 99}}},
    ]
    s = aggregate_summary(per_doc)
    # 未知 key 不应出现在 summary 中
    assert "unknown_metric" not in s["counts"]


def test_aggregate_success_with_falsey_values_batch48():
    """0 / 0.0 / "" 都不算 True。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": 0}}},
        {"metrics": {"pipeline_success": {"value": 0.0}}},
        {"metrics": {"pipeline_success": {"value": ""}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_success_only_true_strict_batch48():
    """只有 True（bool）算成功，"True" 字符串不算。"""
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": "True"}}},  # str
    ]
    s = aggregate_summary(per_doc)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 1


# ---------- get_git_provenance stdout 含特殊字符 ----------

def test_git_provenance_stdout_with_newline_batch48(tmp_path):
    """stdout 含换行 → strip 后取一行。"""
    r1 = MagicMock(returncode=0, stdout="abc\ndef\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    # strip 只去首尾，中间换行仍保留
    assert "abc" in out["git_commit"]


def test_git_provenance_stdout_only_newlines_batch48(tmp_path):
    r1 = MagicMock(returncode=0, stdout="\n\n\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    # strip 后是空 → None
    assert out["git_commit"] is None


def test_git_provenance_status_with_only_whitespace_batch48(tmp_path):
    """status 输出只有空白 → strip 后空 → dirty False。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="   \n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_git_provenance_status_with_tab_batch48(tmp_path):
    """status 含 tab → strip 后非空 → dirty True。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="\t M file\n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


# ---------- get_dependency_versions mock importlib 失败 ----------

def test_dependency_versions_mixed_batch48():
    """部分包找到部分找不到。"""
    import importlib.metadata as im
    call_count = [0]

    def side(pkg):
        call_count[0] += 1
        if pkg == "pdfplumber":
            return "0.10.0"
        raise im.PackageNotFoundError(pkg)

    with patch("importlib.metadata.version", side_effect=side):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "0.10.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None
    assert call_count[0] == 3


def test_dependency_versions_specific_exception_batch48():
    """特定包抛特定异常 → 仍返回 None。"""
    def side(pkg):
        if pkg == "pdfplumber":
            return "1.0"
        if pkg == "python-docx":
            raise ValueError("specific")
        raise RuntimeError("generic")

    with patch("importlib.metadata.version", side_effect=side):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_dependency_versions_returns_correct_keys_batch48():
    out = get_dependency_versions()
    assert "pdfplumber" in out
    assert "python-docx" in out
    assert "pypdfium2" in out


# ---------- build_provenance 字段精确 ----------

def test_build_provenance_field_order_batch48(tmp_path):
    """9 个字段都存在且值正确。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, "v1")
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False
    assert out["evaluator_version"] == "1.1"
    assert out["report_version"] == "1.1"
    assert out["parser_name"] == "fallback"
    assert out["parser_version"] == "v1"
    assert isinstance(out["dependencies"], dict)
    assert out["max_chars"] == 800
    assert isinstance(out["run_timestamp_iso"], str)


def test_build_provenance_field_count_batch48(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert len(out) == 9


def test_build_provenance_max_chars_passed_through_batch48(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 1500, None)
    assert out["max_chars"] == 1500


def test_build_provenance_parser_name_kreuzberg_batch48(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"
    assert out["parser_version"] == "4.10.2"


def test_build_provenance_dependencies_subkeys_batch48(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    deps = out["dependencies"]
    assert set(deps.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


# ---------- build_devset_section 边界 ----------

def test_build_devset_section_complete_status_batch48():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 4
    m.docx_count = 6
    m.categories_covered = ["cat1"]
    out = build_devset_section(m)
    assert out["status"] == "complete"
    assert out["file_count"] == 10


def test_build_devset_section_empty_documents_batch48():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["file_count"] == 0
    assert out["categories_covered"] == []


def test_build_devset_section_many_categories_batch48():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 2
    m.pdf_count = 3
    m.docx_count = 2
    m.categories_covered = ["a", "b", "c", "d", "e"]
    out = build_devset_section(m)
    assert len(out["categories_covered"]) == 5


# ---------- aggregate_summary silent_drop 与 counts 区别 ----------

def test_aggregate_silent_drop_not_in_counts_batch48():
    """silent_drop_count 不在 _COUNT_METRICS 里（独立聚合）。"""
    assert "silent_drop_count" not in _COUNT_METRICS


def test_aggregate_silent_drop_not_in_success_batch48():
    assert "silent_drop_count" not in _SUCCESS_BOOL_METRICS


def test_aggregate_silent_drop_not_in_ratio_batch48():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_aggregate_silent_drop_special_handling_batch48():
    """silent_drop_count 单独走 summary["silent_drop_total"]。"""
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 7}}},
    ]
    s = aggregate_summary(per_doc)
    assert s["silent_drop_total"] == 10


# ---------- aggregate_summary counts 只对 element_count_total ----------

def test_aggregate_counts_only_element_count_total_batch48():
    """counts 只包含 element_count_total。"""
    s = aggregate_summary([])
    assert set(s["counts"].keys()) == {"element_count_total"}


def test_aggregate_success_only_pipeline_success_batch48():
    """success_rates 只包含 pipeline_success。"""
    s = aggregate_summary([])
    assert set(s["success_rates"].keys()) == {"pipeline_success"}


# ---------- module source 字符串补强 ----------

def test_source_contains_不混合类型_batch48():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src or "不混合" in src


def test_source_contains_success_rates_batch48():
    src = inspect.getsource(report_mod)
    assert "success_rates" in src


def test_source_contains_ratio_macro_averages_batch48():
    src = inspect.getsource(report_mod)
    assert "ratio_macro_averages" in src


def test_source_contains_silent_drop_total_batch48():
    src = inspect.getsource(report_mod)
    assert "silent_drop_total" in src


def test_source_contains_participating_docs_batch48():
    src = inspect.getsource(report_mod)
    assert "participating_docs" in src


def test_source_contains_no_expectations_phrase_batch48():
    src = inspect.getsource(report_mod)
    assert "无 expectations" in src or "无expectations" in src


def test_source_contains_ParseError_batch48():
    """应有 pdfplumber/python-docx/pypdfium2 名字。"""
    src = inspect.getsource(report_mod)
    assert "pypdfium2 模块本身没有 __version__" in src


def test_source_contains_importlib_metadata_version_batch48():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata.version" in src


def test_source_contains_PackageNotFoundError_batch48():
    src = inspect.getsource(report_mod)
    assert "PackageNotFoundError" in src


def test_source_contains_run_timestamp_iso_batch48():
    src = inspect.getsource(report_mod)
    assert "run_timestamp_iso" in src


def test_source_contains_iso_format_batch48():
    src = inspect.getsource(report_mod)
    assert "isoformat" in src or "astimezone" in src


# ---------- AST 结构补强 ----------

def test_ast_aggregate_summary_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Name)
    assert returns[0].value.id == "summary"


def test_ast_aggregate_summary_has_three_inner_for_batch48():
    """3 个内层 for：counts / success_rates / ratio_macro_averages。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary"][0]
    top_fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(top_fors) == 3


def test_ast_get_git_provenance_has_two_subprocess_calls_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance"][0]
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
    ]
    assert len(calls) == 2


def test_ast_get_dependency_versions_has_for_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions"][0]
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_get_dependency_versions_has_try_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_build_provenance_has_call_to_get_git_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance"][0]
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    # 至少调用 get_git_provenance 和 get_dependency_versions
    func_names = []
    for c in calls:
        if isinstance(c.func, ast.Name):
            func_names.append(c.func.id)
    assert "get_git_provenance" in func_names
    assert "get_dependency_versions" in func_names


def test_ast_build_devset_section_has_return_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_module_has_no_class_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_module_has_docstring_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)


def test_ast_constants_use_tuple_literal_batch48():
    """3 个常量都是 tuple literal。"""
    tree = ast.parse(inspect.getsource(report_mod))
    tuple_assigns = 0
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1:
            if isinstance(n.value, ast.Tuple):
                tuple_assigns += 1
    assert tuple_assigns == 3


def test_ast_no_async_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in ast.walk(tree):
        assert not isinstance(n, ast.AsyncFunctionDef)


# ---------- forbidden tokens 第一百一十六批 ----------

def test_source_no_eval_batch48():
    src = inspect.getsource(report_mod)
    assert "eval(" not in src


def test_source_no_exec_batch48():
    src = inspect.getsource(report_mod)
    assert "exec(" not in src


def test_source_no_compile_batch48():
    src = inspect.getsource(report_mod)
    assert "compile(" not in src


def test_source_no_globals_batch48():
    src = inspect.getsource(report_mod)
    assert "globals(" not in src


def test_source_no_locals_batch48():
    src = inspect.getsource(report_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch48():
    src = inspect.getsource(report_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch48():
    src = inspect.getsource(report_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch48():
    src = inspect.getsource(report_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch48():
    src = inspect.getsource(report_mod)
    assert "pickle.load(" not in src


def test_source_no_lambda_batch48():
    src = inspect.getsource(report_mod)
    assert "lambda" not in src


def test_source_no_yield_batch48():
    src = inspect.getsource(report_mod)
    assert "yield" not in src


def test_source_no_walrus_batch48():
    src = inspect.getsource(report_mod)
    assert ":=" not in src


def test_source_no_async_batch48():
    src = inspect.getsource(report_mod)
    assert "async def" not in src


def test_source_no_await_batch48():
    src = inspect.getsource(report_mod)
    assert "await " not in src


def test_source_no_raise_batch48():
    src = inspect.getsource(report_mod)
    assert "raise " not in src
