"""evaluation/report.py 第九十四轮 edges 测试（Round 683）。

补强 edges66 未触及的角度（第五十三批）。

新角度：
- get_git_provenance 更深（rev-parse returncode 非 0 → commit None / porcelain returncode 非 0 → dirty False / stdout 只有空白 → commit None / stdout 只有空白 → dirty False）
- get_dependency_versions 更深（返回 3 个 key / value 是 str 或 None / pypdfium2 可能 None / 返回 dict 类型）
- build_provenance 更深（max_chars int 转换 / parser_version None 保留 / dependencies 调用 / run_timestamp_iso 含时区 / evaluator_version/report_version 来自 evaluation 包）
- aggregate_summary counts 更深（value 0 是有效值参与 / 多 doc 不同值 sum / participating_docs 计数 / None 不参与）
- aggregate_summary success_rates 更深（空列表 rate None / 全失败 rate 0.0 / 全成功 rate 1.0 / total 等于 doc 数）
- aggregate_summary ratio macro 更深（部分 null not_evaluated 计数 / 全 null macro None / macro 平均计算精确 / participating + not_evaluated == total）
- aggregate_summary silent_drop_total 更深（全 None → None / 部分 None 求和非 None / 空列表 → None）
- build_devset_section 更深（6 keys 固定 / 值来自 manifest 属性）
- 模块源码补强（subprocess import / datetime import / EVALUATOR_VERSION REPORT_VERSION import / _RATIO_METRICS 12 / _COUNT_METRICS 1 / _SUCCESS_BOOL_METRICS 1 / get_git_provenance 命令行 / timeout=10 / build_provenance int(max_chars) / astimezone().isoformat()）
- AST 结构补强（5 函数 + 顺序 / 4 module-level Assigns / _RATIO_METRICS Tuple 12 / aggregate_summary 3 显式 For / get_git_provenance 1 Try + 2 subprocess.run / build_provenance 1 return Dict 9 / build_devset_section 1 return Dict 6 / 无 ClassDef / 无 AsyncFunctionDef）
- forbidden tokens 第一百五十三批
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
from evaluation import EVALUATOR_VERSION, REPORT_VERSION
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


# ---------- get_git_provenance 更深 ----------

def _run_result(returncode=0, stdout=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_git_provenance_revparse_fail_commit_none_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(returncode=1), _run_result(stdout="")]
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_git_provenance_porcelain_fail_dirty_false_batch52():
    """porcelain returncode 非 0 → bool(0==0 and ...) short-circuit → dirty=False。"""
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [
            _run_result(stdout="abc123\n"),
            _run_result(returncode=128, stdout="M file\n"),
        ]
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_git_provenance_commit_stdout_whitespace_only_batch52():
    """rev-parse stdout 只有换行 → strip 后空 → None。"""
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(stdout="\n  \n"), _run_result(stdout="")]
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None


def test_git_provenance_porcelain_stdout_whitespace_only_batch52():
    """porcelain stdout 只有空白 → strip 后空 → dirty=False。"""
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(stdout="abc"), _run_result(stdout="   \n")]
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_git_provenance_oserror_fallback_batch52():
    with patch("evaluation.report.subprocess.run", side_effect=OSError("no git")):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_timeout_fallback_batch52():
    with patch("evaluation.report.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 10)):
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_returns_2_keys_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(stdout="c1\n"), _run_result(stdout="M f\n")]
        out = get_git_provenance(Path("."))
    assert set(out.keys()) == {"git_commit", "git_dirty"}


def test_git_provenance_two_subprocess_calls_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(stdout="c\n"), _run_result(stdout="")]
        get_git_provenance(Path("."))
    assert run.call_count == 2
    # 第一次 rev-parse HEAD
    assert run.call_args_list[0].args[0] == ["git", "rev-parse", "HEAD"]
    # 第二次 status --porcelain
    assert run.call_args_list[1].args[0] == ["git", "status", "--porcelain"]


def test_git_provenance_timeout_kwarg_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run_result(stdout="c\n"), _run_result(stdout="")]
        get_git_provenance(Path("."))
    for call in run.call_args_list:
        assert call.kwargs.get("timeout") == 10


# ---------- get_dependency_versions 更深 ----------

def test_dependency_versions_3_keys_batch52():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_dependency_versions_values_type_batch52():
    v = get_dependency_versions()
    for k, val in v.items():
        assert val is None or isinstance(val, str)


def test_dependency_versions_pdfplumber_installed_batch52():
    v = get_dependency_versions()
    # fallback parser 用 pdfplumber，应已安装
    assert v["pdfplumber"] is not None


def test_dependency_versions_python_docx_installed_batch52():
    v = get_dependency_versions()
    assert v["python-docx"] is not None


def test_dependency_versions_returns_dict_batch52():
    assert isinstance(get_dependency_versions(), dict)


# ---------- build_provenance 更深 ----------

def test_build_provenance_max_chars_int_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={"pdfplumber": "1.0"}):
        out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_version_none_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_9_keys_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert set(out.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_versions_from_package_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, "1.0")
    assert out["evaluator_version"] == EVALUATOR_VERSION
    assert out["report_version"] == REPORT_VERSION


def test_build_provenance_timestamp_has_timezone_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = out["run_timestamp_iso"]
    # isoformat with tz contains + or Z
    assert ("+" in ts) or ts.endswith("Z")


def test_build_provenance_timestamp_parseable_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = datetime.fromisoformat(out["run_timestamp_iso"])
    assert isinstance(ts, datetime)


def test_build_provenance_parser_name_recorded_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"
    assert out["parser_version"] == "4.10.2"


# ---------- aggregate_summary counts 更深 ----------

def _doc(metrics):
    return {"metrics": metrics}


def test_aggregate_counts_zero_is_valid_batch52():
    """value=0 不是 None → 参与 sum。"""
    results = [
        _doc({"element_count_total": {"value": 0}}),
        _doc({"element_count_total": {"value": 5}}),
    ]
    s = aggregate_summary(results)
    assert s["counts"]["element_count_total"]["sum"] == 5
    assert s["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_counts_none_not_participating_batch52():
    results = [
        _doc({"element_count_total": {"value": None, "reason": "pipeline_failed"}}),
        _doc({"element_count_total": {"value": 3}}),
    ]
    s = aggregate_summary(results)
    assert s["counts"]["element_count_total"]["sum"] == 3
    assert s["counts"]["element_count_total"]["participating_docs"] == 1


def test_aggregate_counts_all_none_batch52():
    results = [_doc({"element_count_total": {"value": None}})]
    s = aggregate_summary(results)
    assert s["counts"]["element_count_total"]["sum"] is None
    assert s["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_counts_empty_results_batch52():
    s = aggregate_summary([])
    assert s["counts"]["element_count_total"] == {"sum": None, "participating_docs": 0}


def test_aggregate_counts_missing_metric_batch52():
    """metrics 里根本没有该 key → get(name, {}) → value None → 不参与。"""
    results = [_doc({"other": {"value": 1}})]
    s = aggregate_summary(results)
    assert s["counts"]["element_count_total"]["sum"] is None


# ---------- aggregate_summary success_rates 更深 ----------

def test_aggregate_success_empty_rate_none_batch52():
    s = aggregate_summary([])
    assert s["success_rates"]["pipeline_success"]["rate"] is None
    assert s["success_rates"]["pipeline_success"]["total"] == 0
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_success_all_fail_batch52():
    results = [
        _doc({"pipeline_success": {"value": False}}),
        _doc({"pipeline_success": {"value": False}}),
    ]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_success_all_pass_batch52():
    results = [
        _doc({"pipeline_success": {"value": True}}),
        _doc({"pipeline_success": {"value": True}}),
    ]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_success_half_batch52():
    results = [
        _doc({"pipeline_success": {"value": True}}),
        _doc({"pipeline_success": {"value": False}}),
        _doc({"pipeline_success": {"value": True}}),
        _doc({"pipeline_success": {"value": False}}),
    ]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.5
    assert s["success_rates"]["pipeline_success"]["total"] == 4


def test_aggregate_success_null_counts_as_fail_batch52():
    """pipeline_success value=None 不算成功。"""
    results = [
        _doc({"pipeline_success": {"value": None}}),
    ]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


# ---------- aggregate_summary ratio macro 更深 ----------

def test_aggregate_ratio_partial_null_batch52():
    results = [
        _doc({"chunk_boundary_f1": {"value": 1.0}}),
        _doc({"chunk_boundary_f1": {"value": None, "reason": "no_annotation"}}),
    ]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["macro_average"] == 1.0
    assert r["participating_docs"] == 1
    assert r["not_evaluated"] == 1


def test_aggregate_ratio_all_null_batch52():
    results = [_doc({"chunk_boundary_f1": {"value": None}})]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["macro_average"] is None
    assert r["participating_docs"] == 0
    assert r["not_evaluated"] == 1


def test_aggregate_ratio_macro_exact_batch52():
    results = [
        _doc({"chunk_boundary_f1": {"value": 0.5}}),
        _doc({"chunk_boundary_f1": {"value": 1.0}}),
    ]
    s = aggregate_summary(results)
    assert s["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] == 0.75


def test_aggregate_ratio_participating_plus_not_evaluated_batch52():
    results = [
        _doc({"chunk_boundary_f1": {"value": 0.5}}),
        _doc({"chunk_boundary_f1": {"value": 0.25}}),
        _doc({"chunk_boundary_f1": {"value": None}}),
        _doc({"chunk_boundary_f1": {"value": None}}),
    ]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["participating_docs"] + r["not_evaluated"] == 4


def test_aggregate_ratio_all_12_metrics_present_batch52():
    s = aggregate_summary([])
    assert set(s["ratio_macro_averages"].keys()) == set(_RATIO_METRICS)


def test_aggregate_ratio_zero_value_participates_batch52():
    results = [_doc({"chunk_boundary_f1": {"value": 0.0}})]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["participating_docs"] == 1
    assert r["macro_average"] == 0.0


# ---------- aggregate_summary silent_drop_total 更深 ----------

def test_aggregate_silent_drop_all_none_batch52():
    results = [
        _doc({"silent_drop_count": {"value": None, "reason": "no_expectations"}}),
    ]
    s = aggregate_summary(results)
    assert s["silent_drop_total"] is None


def test_aggregate_silent_drop_partial_batch52():
    results = [
        _doc({"silent_drop_count": {"value": 2}}),
        _doc({"silent_drop_count": {"value": None}}),
        _doc({"silent_drop_count": {"value": 3}}),
    ]
    s = aggregate_summary(results)
    assert s["silent_drop_total"] == 5


def test_aggregate_silent_drop_empty_batch52():
    s = aggregate_summary([])
    assert s["silent_drop_total"] is None


def test_aggregate_silent_drop_zero_batch52():
    results = [_doc({"silent_drop_count": {"value": 0}})]
    s = aggregate_summary(results)
    assert s["silent_drop_total"] == 0


# ---------- build_devset_section 更深 ----------

def _make_manifest(status="incomplete", docs=None):
    m = MagicMock()
    m.devset_status = status
    m.file_count = len(docs) if docs is not None else 0
    m.content_group_count = 0
    m.pdf_count = sum(1 for d in (docs or []) if d.get("source_type") == "pdf")
    m.docx_count = sum(1 for d in (docs or []) if d.get("source_type") == "docx")
    m.categories_covered = []
    return m


def test_devset_section_6_keys_batch52():
    m = _make_manifest()
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }


def test_devset_section_status_from_manifest_batch52():
    m = _make_manifest(status="complete")
    out = build_devset_section(m)
    assert out["status"] == "complete"


def test_devset_section_counts_batch52():
    docs = [{"source_type": "pdf"}, {"source_type": "pdf"}, {"source_type": "docx"}]
    m = _make_manifest(docs=docs)
    out = build_devset_section(m)
    assert out["file_count"] == 3
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 1


def test_devset_section_categories_pass_through_batch52():
    """build_devset_section 只透传 categories_covered（排序在 Manifest property 内完成）。"""
    m = _make_manifest()
    m.categories_covered = ["zebra", "apple", "mango"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["zebra", "apple", "mango"]


# ---------- 模块源码补强 ----------

def test_source_subprocess_import_batch52():
    src = inspect.getsource(report_mod)
    assert "import subprocess" in src


def test_source_datetime_import_batch52():
    src = inspect.getsource(report_mod)
    assert "from datetime import datetime" in src


def test_source_path_import_batch52():
    src = inspect.getsource(report_mod)
    assert "from pathlib import Path" in src


def test_source_any_import_batch52():
    src = inspect.getsource(report_mod)
    assert "from typing import Any" in src


def test_source_versions_import_batch52():
    src = inspect.getsource(report_mod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_source_ratio_metrics_12_entries_batch52():
    assert len(_RATIO_METRICS) == 12


def test_source_count_metrics_1_entry_batch52():
    assert _COUNT_METRICS == ("element_count_total",)


def test_source_success_bool_metrics_1_entry_batch52():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_source_ratio_metrics_excludes_figure_caption_batch52():
    for name in _RATIO_METRICS:
        assert not name.startswith("figure_caption")


def test_source_ratio_metrics_includes_chunk_boundary_batch52():
    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_source_git_provenance_commands_batch52():
    src = inspect.getsource(report_mod)
    assert '"git", "rev-parse", "HEAD"' in src
    assert '"git", "status", "--porcelain"' in src


def test_source_git_provenance_timeout_batch52():
    src = inspect.getsource(report_mod)
    assert src.count("timeout=10") == 2


def test_source_build_provenance_int_conversion_batch52():
    src = inspect.getsource(report_mod)
    assert "int(max_chars)" in src


def test_source_build_provenance_astimezone_batch52():
    src = inspect.getsource(report_mod)
    assert "datetime.now().astimezone().isoformat()" in src


def test_source_get_dependency_versions_packages_batch52():
    src = inspect.getsource(report_mod)
    assert '"pdfplumber", "python-docx", "pypdfium2"' in src


def test_source_dependency_importlib_note_batch52():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata" in src


def test_source_aggregate_docstring_no_mixing_batch52():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src


def test_source_all_5_entries_batch52():
    src = inspect.getsource(report_mod)
    for name in ("build_provenance", "build_devset_section", "aggregate_summary", "get_git_provenance", "get_dependency_versions"):
        assert f'"{name}"' in src


# ---------- AST 结构补强 ----------

def test_ast_5_functions_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_function_names_order_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
        "get_git_provenance", "get_dependency_versions",
        "build_provenance", "build_devset_section", "aggregate_summary",
    ]


def test_ast_4_module_level_assigns_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4  # 3 常量 + __all__


def test_ast_ratio_metrics_tuple_12_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_RATIO_METRICS" for t in n.targets)
    )
    assert isinstance(assign.value, ast.Tuple)
    assert len(assign.value.elts) == 12


def test_ast_count_metrics_tuple_1_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_COUNT_METRICS" for t in n.targets)
    )
    assert isinstance(assign.value, ast.Tuple)
    assert len(assign.value.elts) == 1


def test_ast_success_bool_metrics_tuple_1_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_SUCCESS_BOOL_METRICS" for t in n.targets)
    )
    assert isinstance(assign.value, ast.Tuple)
    assert len(assign.value.elts) == 1


def test_ast_git_provenance_1_try_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    # except (OSError, subprocess.SubprocessError)
    handlers = trys[0].handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0].type, ast.Tuple)


def test_ast_git_provenance_2_subprocess_runs_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    runs = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
    ]
    assert len(runs) == 2


def test_ast_build_provenance_returns_dict_9_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)
    assert len(returns[0].value.keys) == 9


def test_ast_build_devset_section_returns_dict_6_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)
    assert len(returns[0].value.keys) == 6


def test_ast_aggregate_summary_3_explicit_for_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 3  # counts + success + ratio


def test_ast_aggregate_summary_4_summary_keys_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    src = ast.unparse(func)
    assert "summary['counts']" in src or 'summary["counts"]' in src
    assert "summary['success_rates']" in src or 'summary["success_rates"]' in src
    assert "summary['ratio_macro_averages']" in src or 'summary["ratio_macro_averages"]' in src
    assert "summary['silent_drop_total']" in src or 'summary["silent_drop_total"]' in src


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_raise_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_all_value_is_list_5_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 5


# ---------- forbidden tokens 第一百五十三批 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_popen_batch52():
    """subprocess.run 允许，subprocess.Popen 不允许。"""
    assert "Popen" not in _src()


def test_source_no_popen_batch52():
    assert "popen(" not in _src().replace("Popen", "")


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    """report.py 不使用 open()。"""
    assert "open(" not in _src()
