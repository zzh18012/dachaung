"""evaluation/report.py 第九十三轮 edges 测试（Round 676）。

补强 edges65 未触及的角度（第五十二批）。

新角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 完整性
- get_git_provenance 命令行调用（实际 subprocess.run 2 次：rev-parse HEAD + status --porcelain）
- get_git_provenance 边界（returncode 0 + stdout 空白 / commit 是 "abc123\n" / dirty 是 " M file.txt\n"）
- get_dependency_versions 实际行为（包含已安装的 pdfplumber / python-docx）
- build_provenance 完整字段（git_commit / git_dirty / evaluator_version / report_version / parser_name / parser_version / dependencies / max_chars / run_timestamp_iso）
- build_devset_section 完整字段（status / file_count / content_group_count / pdf_count / docx_count / categories_covered）
- aggregate_summary 多 metric 类型（pipeline_success + schema_valid 同时 / ratio 各项独立计算 / counts vs success_rates vs ratio_macro 不混淆）
- aggregate_summary 边界（all None values / 全部相同 value / mixing True + 1 + "x"）
- 模块源码补强（_RATIO_METRICS 文档注释 / 不混合类型 docstring / 4 模块常量 / 函数顺序）
- AST 结构补强（4 Assigns / aggregate_summary 3 个显式 for / for target 都是 ast.Name + store）
- forbidden tokens 第一百四十六批
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


# ---------- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 完整性 ----------

def test_count_metrics_tuple_immutable_batch52():
    """tuple 不可变。"""
    with pytest.raises(TypeError):
        _COUNT_METRICS[0] = "x"  # type: ignore


def test_success_bool_metrics_tuple_immutable_batch52():
    with pytest.raises(TypeError):
        _SUCCESS_BOOL_METRICS[0] = "x"  # type: ignore


def test_ratio_metrics_tuple_immutable_batch52():
    with pytest.raises(TypeError):
        _RATIO_METRICS[0] = "x"  # type: ignore


def test_count_metrics_unique_per_metric_category_batch52():
    """_COUNT_METRICS / _SUCCESS_BOOL_METRICS / _RATIO_METRICS 不重叠。"""
    all_metrics = set(_COUNT_METRICS) | set(_SUCCESS_BOOL_METRICS) | set(_RATIO_METRICS)
    assert "element_count_total" in all_metrics
    assert "pipeline_success" in all_metrics
    assert "pdf_locator_valid_ratio" in all_metrics


def test_count_and_success_metrics_no_overlap_batch52():
    assert set(_COUNT_METRICS) & set(_SUCCESS_BOOL_METRICS) == set()


def test_count_and_ratio_metrics_no_overlap_batch52():
    assert set(_COUNT_METRICS) & set(_RATIO_METRICS) == set()


def test_success_and_ratio_metrics_no_overlap_batch52():
    """pipeline_success 是 bool，不在 ratio。"""
    assert set(_SUCCESS_BOOL_METRICS) & set(_RATIO_METRICS) == set()


# ---------- get_git_provenance subprocess 调用 ----------

def test_get_git_provenance_calls_2_subprocess_batch52(tmp_path):
    """调用 2 次 subprocess.run：rev-parse HEAD + status --porcelain。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]) as mock_run:
        get_git_provenance(tmp_path)
    assert mock_run.call_count == 2
    # 第 1 次命令
    cmd1 = mock_run.call_args_list[0].args[0]
    assert cmd1 == ["git", "rev-parse", "HEAD"]
    # 第 2 次命令
    cmd2 = mock_run.call_args_list[1].args[0]
    assert cmd2 == ["git", "status", "--porcelain"]


def test_get_git_provenance_cwd_is_project_root_batch52(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]) as mock_run:
        get_git_provenance(tmp_path)
    for call in mock_run.call_args_list:
        assert call.kwargs["cwd"] == str(tmp_path)


def test_get_git_provenance_default_dirty_true_batch52(tmp_path):
    """默认 dirty=True（异常时也 True）。"""
    with patch("evaluation.report.subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is True


def test_get_git_provenance_default_commit_none_batch52(tmp_path):
    with patch("evaluation.report.subprocess.run", side_effect=OSError("boom")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_get_git_provenance_kwargs_passed_batch52(tmp_path):
    """subprocess.run 收到 capture_output=True, text=True, encoding, errors, timeout。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]) as mock_run:
        get_git_provenance(tmp_path)
    for call in mock_run.call_args_list:
        assert call.kwargs["capture_output"] is True
        assert call.kwargs["text"] is True
        assert call.kwargs["encoding"] == "utf-8"
        assert call.kwargs["errors"] == "replace"
        assert call.kwargs["timeout"] == 10


def test_get_git_provenance_returns_dict_with_2_keys_batch52(tmp_path):
    with patch("evaluation.report.subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = get_git_provenance(tmp_path)
    assert set(out.keys()) == {"git_commit", "git_dirty"}


# ---------- get_dependency_versions 实际行为 ----------

def test_get_dependency_versions_pdfplumber_value_batch52():
    """pdfplumber 已安装 → 返回真实版本号。"""
    out = get_dependency_versions()
    # pdfplumber 是 fallback parser 主依赖，应该已安装
    if out["pdfplumber"] is not None:
        # 形如 '0.x.y'
        assert "." in out["pdfplumber"]


def test_get_dependency_versions_python_docx_value_batch52():
    out = get_dependency_versions()
    # python-docx 包名带 '-'，但 import 时是 'docx'
    if out["python-docx"] is not None:
        assert "." in out["python-docx"]


def test_get_dependency_versions_no_extra_keys_batch52():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


# ---------- build_provenance 完整字段 ----------

def test_build_provenance_git_commit_from_helper_batch52(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "abc", "git_dirty": False}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_build_provenance_dependencies_dict_batch52(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)
    assert set(out["dependencies"].keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_build_provenance_max_chars_negative_batch52(tmp_path):
    """负数 max_chars 也能被 int() 转换。"""
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", -100, None)
    assert out["max_chars"] == -100


def test_build_provenance_parser_name_recorded_batch52(tmp_path):
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "kreuzberg", 800, "2.0")
    assert out["parser_name"] == "kreuzberg"
    assert out["parser_version"] == "2.0"


def test_build_provenance_timestamp_recent_batch52(tmp_path):
    """timestamp 应该接近当前时间。"""
    t_before = datetime.now().astimezone()
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}):
        out = build_provenance(tmp_path, "fallback", 800, None)
    t_after = datetime.now().astimezone()
    ts = datetime.fromisoformat(out["run_timestamp_iso"])
    assert t_before <= ts <= t_after


# ---------- build_devset_section 完整字段 ----------

def test_build_devset_section_uses_manifest_attributes_batch52():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 3
    m.content_group_count = 2
    m.pdf_count = 1
    m.docx_count = 2
    m.categories_covered = ["a", "b", "c"]
    out = build_devset_section(m)
    assert out["status"] == "incomplete"
    assert out["file_count"] == 3
    assert out["content_group_count"] == 2
    assert out["pdf_count"] == 1
    assert out["docx_count"] == 2
    assert out["categories_covered"] == ["a", "b", "c"]


def test_build_devset_section_returns_6_keys_batch52():
    m = MagicMock()
    m.devset_status = "x"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert len(out) == 6


# ---------- aggregate_summary 多 metric 类型 ----------

def test_aggregate_summary_success_and_schema_valid_independent_batch52():
    """schema_valid 是 ratio，pipeline_success 是 success_bool；各自计算不混淆。"""
    docs = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "schema_valid": {"value": True},
        }},
        {"metrics": {
            "pipeline_success": {"value": False},
            "schema_valid": {"value": True},
        }},
    ]
    out = aggregate_summary(docs)
    # success_rates: pipeline_success 1/2 = 0.5
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5
    # ratio_macro: schema_valid 1.0
    assert out["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0


def test_aggregate_summary_counts_vs_success_not_mixed_batch52():
    """element_count_total 是 count，pipeline_success 是 success_bool；不混淆。"""
    docs = [
        {"metrics": {
            "pipeline_success": {"value": True},
            "element_count_total": {"value": 5},
        }},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 5
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1


def test_aggregate_summary_all_none_values_batch52():
    """所有 metric value 是 None。"""
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
    ]
    out = aggregate_summary(docs)
    m = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert m["macro_average"] is None
    assert m["participating_docs"] == 0
    assert m["not_evaluated"] == 2


def test_aggregate_summary_all_same_value_batch52():
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
    ]
    out = aggregate_summary(docs)
    m = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert m["macro_average"] == 0.5


def test_aggregate_summary_rate_all_fail_batch52():
    docs = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(docs)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 2
    assert sr["rate"] == 0.0


def test_aggregate_summary_rate_all_success_batch52():
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_missing_metric_treated_as_none_batch52():
    """per_doc 缺某 metric → 视为 None 不参与。"""
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {}},  # 缺 metric
    ]
    out = aggregate_summary(docs)
    m = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    # 1 个 doc 有值
    assert m["participating_docs"] == 1
    assert m["macro_average"] == 0.5
    assert m["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_one_doc_only_batch52():
    """silent_drop 只 1 个 doc 有值。"""
    docs = [
        {"metrics": {"silent_drop_count": {"value": 5}}},
        {"metrics": {}},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 5


def test_aggregate_summary_returns_4_keys_batch52():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_counts_with_0_int_batch52():
    """element_count_total = 0 也参与求和。"""
    docs = [
        {"metrics": {"element_count_total": {"value": 0}}},
    ]
    out = aggregate_summary(docs)
    # 0 is not None, so it's included
    assert out["counts"]["element_count_total"]["sum"] == 0
    assert out["counts"]["element_count_total"]["participating_docs"] == 1


# ---------- 模块源码补强 ----------

def test_source_ratio_metrics_doc_comment_batch52():
    src = inspect.getsource(report_mod)
    assert "ratio（参与 macro average）" in src or "macro average" in src


def test_source_figure_caption_note_batch52():
    src = inspect.getsource(report_mod)
    assert "figure_caption_*" in src
    assert "始终 null" in src


def test_source_no_mixed_types_docstring_batch52():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src


def test_source_counts_doc_comment_batch52():
    src = inspect.getsource(report_mod)
    assert "counts" in src
    assert "求和" in src


def test_source_success_rates_doc_comment_batch52():
    src = inspect.getsource(report_mod)
    assert "success_rates" in src


def test_source_silent_drop_doc_comment_batch52():
    src = inspect.getsource(report_mod)
    assert "silent_drop_count" in src
    assert "求和" in src


def test_source_function_order_batch52():
    src = inspect.getsource(report_mod)
    # 5 函数顺序：get_git_provenance → get_dependency_versions → build_provenance → build_devset_section → aggregate_summary
    pos = {
        "get_git_provenance": src.find("def get_git_provenance"),
        "get_dependency_versions": src.find("def get_dependency_versions"),
        "build_provenance": src.find("def build_provenance"),
        "build_devset_section": src.find("def build_devset_section"),
        "aggregate_summary": src.find("def aggregate_summary"),
    }
    sorted_pos = sorted(pos.values())
    assert sorted_pos == [pos["get_git_provenance"], pos["get_dependency_versions"], pos["build_provenance"], pos["build_devset_section"], pos["aggregate_summary"]]


# ---------- AST 结构补强 ----------

def test_ast_has_4_module_level_assigns_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_assign_target_ids_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    names = []
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    names.append(t.id)
    assert set(names) == {"_RATIO_METRICS", "_COUNT_METRICS", "_SUCCESS_BOOL_METRICS", "__all__"}


def test_ast_count_metrics_value_is_tuple_1_elt_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    cm = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_COUNT_METRICS" for t in n.targets)
    )
    assert isinstance(cm.value, ast.Tuple)
    assert len(cm.value.elts) == 1


def test_ast_success_bool_metrics_value_is_tuple_1_elt_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    sm = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_SUCCESS_BOOL_METRICS" for t in n.targets)
    )
    assert isinstance(sm.value, ast.Tuple)
    assert len(sm.value.elts) == 1


def test_ast_aggregate_summary_3_for_loops_in_body_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 3


def test_ast_aggregate_summary_for_target_is_name_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    for f in [n for n in func.body if isinstance(n, ast.For)]:
        assert isinstance(f.target, ast.Name)


def test_ast_build_provenance_returns_dict_9_keys_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)
    assert len(returns[0].value.keys) == 9


def test_ast_build_devset_section_returns_dict_6_keys_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)
    assert len(returns[0].value.keys) == 6


def test_ast_get_git_provenance_has_try_except_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_get_git_provenance_except_catches_oserror_subprocess_error_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    try_n = next(n for n in ast.walk(func) if isinstance(n, ast.Try))
    assert len(try_n.handlers) == 1
    handler = try_n.handlers[0]
    # tuple of names
    assert isinstance(handler.type, ast.Tuple)
    type_names = [t.id for t in handler.type.elts if isinstance(t, ast.Name)]
    assert "OSError" in type_names
    # subprocess.SubprocessError 是 ast.Attribute
    attr_types = [t for t in handler.type.elts if isinstance(t, ast.Attribute)]
    assert any(a.attr == "SubprocessError" for a in attr_types)


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_module_has_docstring_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


# ---------- forbidden tokens 第一百四十六批 ----------

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


def test_source_no_popen_batch52():
    assert "popen" not in _src()


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


def test_source_subprocess_count_at_least_3_batch52():
    """subprocess 出现在 import + 2 处使用 = 至少 3 次。"""
    assert _src().count("subprocess") >= 3
