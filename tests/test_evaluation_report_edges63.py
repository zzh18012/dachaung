"""evaluation/report.py 第九十轮 edges 测试（Round 654）。

补强 edges62 未触及的角度（第四十八批）。

新角度：
- get_git_provenance 路径（commit None / dirty True / 正常 commit / 失败 except / returncode 非 0）
- get_dependency_versions 边界（importlib.metadata.version 找到 / PackageNotFoundError / Exception）
- build_provenance 字段精确（9 字段 / max_chars int 转换 / run_timestamp_iso 格式）
- build_devset_section 字段精确（6 字段 / 从 manifest 提取）
- aggregate_summary 多类型混合（counts / success / ratio / silent / empty docs）
- aggregate_summary ratio null 与 not_evaluated 计数
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 常量
- 模块源码补强（subprocess / datetime / Path / Any / EVALUATOR_VERSION/REPORT_VERSION / 12 RATIO_METRICS / 1 COUNT_METRIC / 1 SUCCESS_BOOL_METRIC）
- AST 结构补强（5 函数 / 无 ClassDef / 无 AsyncFunctionDef / module docstring / get_git_provenance 2 subprocess.run / get_dependency_versions 1 for + ≥1 try / build_provenance 调用 / build_devset_section return / aggregate_summary 多 for + 1 return / 4 top-level Assign）
- forbidden tokens 第一百二十四批
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


# ---------- get_git_provenance 路径 ----------

def test_git_provenance_commit_returncode_nonzero_batch48():
    """rev-parse HEAD returncode 非 0：commit 保持 None。"""
    fake_result = MagicMock()
    fake_result.returncode = 1
    fake_result.stdout = ""
    with patch("evaluation.report.subprocess.run", return_value=fake_result):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] is None


def test_git_provenance_commit_returncode_zero_empty_stdout_batch48():
    """rev-parse returncode=0 但 stdout 为空：commit 仍是 None（因为 `stdout.strip() or None`）。"""
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "   "  # 空白
    with patch("evaluation.report.subprocess.run", return_value=fake_result):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] is None


def test_git_provenance_commit_returncode_zero_with_value_batch48():
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "abc123\n"
    with patch("evaluation.report.subprocess.run", return_value=fake_result):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] == "abc123"


def test_git_provenance_dirty_false_when_clean_batch48():
    """status --porcelain stdout 为空 → dirty=False。"""
    fake_result = MagicMock()
    fake_result.returncode = 0
    fake_result.stdout = "abc123\n"  # 第一次 rev-parse
    fake_result2 = MagicMock()
    fake_result2.returncode = 0
    fake_result2.stdout = ""  # status --porcelain 空
    with patch("evaluation.report.subprocess.run", side_effect=[fake_result, fake_result2]):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_dirty"] is False


def test_git_provenance_oserror_returns_dirty_true_batch48():
    """OSError 时 dirty=True。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_subprocess_error_returns_dirty_true_batch48():
    """subprocess.SubprocessError 时 dirty=True。"""
    with patch(
        "evaluation.report.subprocess.run",
        side_effect=subprocess.SubprocessError("timeout"),
    ):
        out = get_git_provenance(Path("/tmp"))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_returns_two_keys_batch48():
    with patch("evaluation.report.subprocess.run", side_effect=OSError("x")):
        out = get_git_provenance(Path("/tmp"))
    assert set(out.keys()) == {"git_commit", "git_dirty"}


# ---------- get_dependency_versions 边界 ----------

def test_dependency_versions_returns_3_packages_batch48():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_are_str_or_none_batch48():
    out = get_dependency_versions()
    for v in out.values():
        assert v is None or isinstance(v, str)


def test_dependency_versions_package_not_found_returns_none_batch48():
    with patch("importlib.metadata.version", side_effect=__import__("importlib").metadata.PackageNotFoundError):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_dependency_versions_exception_returns_none_batch48():
    with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_dependency_versions_partial_success_batch48():
    """部分包找到部分抛错。"""
    import importlib.metadata
    def fake_version(pkg):
        if pkg == "pdfplumber":
            return "1.0"
        raise importlib.metadata.PackageNotFoundError(pkg)
    with patch("importlib.metadata.version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out["pdfplumber"] == "1.0"
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


# ---------- build_provenance 字段精确 ----------

def test_build_provenance_returns_9_keys_batch48():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "x", "git_dirty": False}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0")
    assert set(out.keys()) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_max_chars_int_conversion_batch48():
    """max_chars 通过 int() 转换。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", "800", "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_run_timestamp_iso_format_batch48():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0")
    # ISO 格式应当能被 datetime.fromisoformat 解析
    parsed = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(parsed, datetime)


def test_build_provenance_parser_version_none_batch48():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_name_passthrough_batch48():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "kreuzberg", 800, "1.0")
    assert out["parser_name"] == "kreuzberg"


def test_build_provenance_evaluator_version_constant_batch48():
    """evaluator_version 来自 EVALUATOR_VERSION 常量。"""
    from evaluation import EVALUATOR_VERSION
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION


def test_build_provenance_report_version_constant_batch48():
    from evaluation import REPORT_VERSION
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        with patch("evaluation.report.get_dependency_versions", return_value={}):
            out = build_provenance(Path("/tmp"), "fallback", 800, "1.0")
    assert out["report_version"] == REPORT_VERSION


# ---------- build_devset_section 字段精确 ----------

def test_build_devset_section_returns_6_keys_batch48():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 10
    m.content_group_count = 5
    m.pdf_count = 5
    m.docx_count = 5
    m.categories_covered = ["a", "b"]
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_build_devset_section_status_passthrough_batch48():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_counts_passthrough_batch48():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 42
    m.content_group_count = 20
    m.pdf_count = 15
    m.docx_count = 27
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["file_count"] == 42
    assert out["content_group_count"] == 20
    assert out["pdf_count"] == 15
    assert out["docx_count"] == 27


def test_build_devset_section_categories_passthrough_batch48():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["x", "y", "z"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["x", "y", "z"]


# ---------- aggregate_summary 多类型混合 ----------

def test_aggregate_summary_empty_docs_batch48():
    out = aggregate_summary([])
    assert out["counts"] == {"element_count_total": {"sum": None, "participating_docs": 0}}
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["total"] == 0
    assert out["silent_drop_total"] is None


def test_aggregate_summary_all_success_batch48():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_partial_success_batch48():
    per_doc = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_counts_sum_batch48():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_with_null_skipped_batch48():
    per_doc = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_summary_ratio_macro_average_batch48():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_with_null_batch48():
    per_doc = [
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["schema_valid"]["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum_batch48():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_with_null_skipped_batch48():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_silent_drop_all_null_batch48():
    per_doc = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(per_doc)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_returns_4_top_keys_batch48():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_ratio_macro_all_ratios_present_batch48():
    """所有 12 个 ratio metric 都出现在 ratio_macro_averages。"""
    out = aggregate_summary([])
    assert set(out["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_summary_success_only_pipeline_success_batch48():
    """success_rates 只有 pipeline_success。"""
    out = aggregate_summary([])
    assert set(out["success_rates"].keys()) == {"pipeline_success"}


def test_aggregate_summary_counts_only_element_count_total_batch48():
    out = aggregate_summary([])
    assert set(out["counts"].keys()) == {"element_count_total"}


# ---------- 模块常量 ----------

def test_ratio_metrics_count_12_batch48():
    assert len(_RATIO_METRICS) == 12


def test_count_metrics_count_1_batch48():
    assert len(_COUNT_METRICS) == 1


def test_success_bool_metrics_count_1_batch48():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_ratio_metrics_no_overlap_with_count_batch48():
    assert not (set(_RATIO_METRICS) & set(_COUNT_METRICS))


def test_ratio_metrics_no_overlap_with_success_batch48():
    assert not (set(_RATIO_METRICS) & set(_SUCCESS_BOOL_METRICS))


def test_count_metrics_no_overlap_with_success_batch48():
    assert not (set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS))


def test_ratio_metrics_contains_chunk_boundary_batch48():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_ratio_metrics_no_figure_caption_batch48():
    """figure_caption_* 不在 RATIO_METRICS（始终 null）。"""
    assert "figure_caption_precision" not in _RATIO_METRICS


def test_count_metrics_is_element_count_total_batch48():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_is_pipeline_success_batch48():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- 模块源码补强 ----------

def test_source_contains_subprocess_import_batch48():
    src = inspect.getsource(report_mod)
    assert "import subprocess" in src


def test_source_contains_datetime_import_batch48():
    src = inspect.getsource(report_mod)
    assert "from datetime import datetime" in src


def test_source_contains_pathlib_import_batch48():
    src = inspect.getsource(report_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch48():
    src = inspect.getsource(report_mod)
    assert "from typing import Any" in src


def test_source_contains_version_imports_batch48():
    src = inspect.getsource(report_mod)
    assert "EVALUATOR_VERSION" in src
    assert "REPORT_VERSION" in src


def test_source_contains_subprocess_run_call_batch48():
    src = inspect.getsource(report_mod)
    assert "subprocess.run" in src


def test_source_contains_git_rev_parse_batch48():
    src = inspect.getsource(report_mod)
    assert "rev-parse" in src
    assert "HEAD" in src


def test_source_contains_git_status_porcelain_batch48():
    src = inspect.getsource(report_mod)
    assert "status" in src
    assert "porcelain" in src


def test_source_contains_importlib_metadata_batch48():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata" in src


def test_source_contains_package_not_found_error_batch48():
    src = inspect.getsource(report_mod)
    assert "PackageNotFoundError" in src


def test_source_contains_isoformat_batch48():
    src = inspect.getsource(report_mod)
    assert "isoformat" in src or "astimezone" in src


def test_source_contains_no_mixing_rule_batch48():
    """docstring 提到不混合类型。"""
    src = inspect.getsource(report_mod)
    assert "不混合" in src or "macro" in src.lower()


def test_source_contains_silent_drop_rule_batch48():
    src = inspect.getsource(report_mod)
    assert "silent_drop" in src


def test_source_contains_all_list_5_entries_batch48():
    src = inspect.getsource(report_mod)
    for name in ("build_provenance", "build_devset_section", "aggregate_summary", "get_git_provenance", "get_dependency_versions"):
        assert name in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_get_git_provenance_has_subprocess_calls_batch48():
    """get_git_provenance 调用 2 次 subprocess.run（rev-parse + status）。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    sub_calls = [
        c for c in calls
        if isinstance(c.func, ast.Attribute)
        and isinstance(c.func.value, ast.Name)
        and c.func.value.id == "subprocess"
        and c.func.attr == "run"
    ]
    assert len(sub_calls) == 2


def test_ast_get_git_provenance_has_try_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_get_git_provenance_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_get_dependency_versions_has_for_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_get_dependency_versions_has_try_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_build_provenance_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)


def test_ast_build_provenance_calls_get_git_provenance_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_call = any(
        isinstance(c.func, ast.Name) and c.func.id == "get_git_provenance" for c in calls
    )
    assert has_call


def test_ast_build_provenance_calls_get_dependency_versions_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_call = any(
        isinstance(c.func, ast.Name) and c.func.id == "get_dependency_versions" for c in calls
    )
    assert has_call


def test_ast_aggregate_summary_has_multiple_for_batch48():
    """aggregate_summary 至少 3 个 for（counts / success / ratio，silent 用 list comprehension 不是 for）。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 3


def test_ast_aggregate_summary_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Name)
    assert returns[0].value.id == "summary"


def test_ast_module_top_level_assign_count_batch48():
    """模块顶部 Assign：_RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS / __all__ = 4。"""
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：__future__ / subprocess / datetime / Path / Any / EVALUATOR+REPORT_VERSION = 6。"""
    tree = ast.parse(inspect.getsource(report_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6


def test_ast_build_devset_section_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)


# ---------- forbidden tokens 第一百二十四批 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_locals_batch48():
    assert "locals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_popen_batch48():
    # subprocess.Popen 是大写，popen 是小写（shell=True 的危险形式）
    # report.py 用 subprocess.run，没有 popen
    assert ".popen(" not in _src()
    assert "Popen(" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()


def test_source_no_async_def_batch48():
    assert "async def" not in _src()
