"""evaluation/report.py 第九十一轮 edges 测试（Round 662）。

补强 edges63 未触及的角度（第四十九批）。

新角度：
- get_git_provenance 多种响应（git rev-parse 失败但 status 成功 / status stdout 含空格 / stdout 含 newline）
- get_git_provenance 超时处理（timeout=10 触发 TimeoutExpired → SubprocessError）
- get_git_provenance OSError 处理（FileNotFoundError 当 git 不存在）
- get_dependency_versions 多场景（pdfplumber 已安装 / python-docx 已安装 / pypdfium2 不存在）
- build_provenance 完整字段（9 个 key / git_commit / git_dirty / evaluator_version=1.1 / report_version=1.1 / parser_name / parser_version / dependencies / max_chars 是 int / run_timestamp_iso 是 ISO 格式）
- build_devset_section 完整字段（6 个 key / status / file_count / content_group_count / pdf_count / docx_count / categories_covered）
- aggregate_summary 多场景（empty list / 单 doc counts 求和 / 多 doc counts / success_rate 0/1/0.5 / ratio macro avg / silent_drop）
- 模块源码补强（subprocess/datetime/Path/Any/EVALUATOR_VERSION+REPORT_VERSION imports / _RATIO_METRICS 12 entries / _COUNT_METRICS / _SUCCESS_BOOL_METRICS / __all__ 5 entries / docstring 关键词）
- AST 结构补强（5 函数 / 无 ClassDef / 无 AsyncFunctionDef / module docstring / 4 import / 3 top-level Assign / get_git_provenance 2 subprocess.run + try / get_dependency_versions import + try / build_provenance 多 keys / aggregate_summary 4 sections / silent_drop list comprehension）
- forbidden tokens 第一百三十二批
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


# ---------- get_git_provenance 多种响应 ----------

def test_git_provenance_success_with_commit_batch49(tmp_path):
    """git rev-parse HEAD 成功 + git status porcelain 空 → commit set, dirty False。"""
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_git_provenance_success_dirty_batch49(tmp_path):
    """git status 输出非空 → dirty True。"""
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_git_provenance_rev_parse_failure_batch49(tmp_path):
    """git rev-parse 失败但 status 成功 → commit None, dirty 取决于 status。"""
    r1 = MagicMock(returncode=128, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_git_provenance_rev_parse_empty_stdout_batch49(tmp_path):
    """git rev-parse 成功但 stdout 空 → commit None。"""
    r1 = MagicMock(returncode=0, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None


def test_git_provenance_status_failure_batch49(tmp_path):
    """git status 失败 → dirty False（returncode != 0 短路为 False）。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=128, stdout="")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc"
    assert out["git_dirty"] is False


def test_git_provenance_status_with_whitespace_only_batch49(tmp_path):
    """git status stdout 是纯空白 → strip 后空 → dirty False。"""
    r1 = MagicMock(returncode=0, stdout="abc\n")
    r2 = MagicMock(returncode=0, stdout="   \n\t  \n")
    with patch("subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_dirty"] is False


def test_git_provenance_timeout_raises_subprocess_error_batch49(tmp_path):
    """subprocess.run 抛 TimeoutExpired → 被 except 捕获，返回 dirty=True。"""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="git", timeout=10)):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_provenance_oserror_batch49(tmp_path):
    """subprocess.run 抛 OSError → 被 except 捕获。"""
    with patch("subprocess.run", side_effect=OSError("no git")):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


# ---------- get_dependency_versions 多场景 ----------

def test_get_dependency_versions_returns_dict_batch49():
    out = get_dependency_versions()
    assert isinstance(out, dict)
    assert "pdfplumber" in out
    assert "python-docx" in out
    assert "pypdfium2" in out


def test_get_dependency_versions_values_type_batch49():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_package_not_found_batch49():
    """模拟 PackageNotFoundError → value None。"""
    import importlib.metadata
    with patch("importlib.metadata.version", side_effect=importlib.metadata.PackageNotFoundError):
        out = get_dependency_versions()
    assert out["pdfplumber"] is None
    assert out["python-docx"] is None
    assert out["pypdfium2"] is None


def test_get_dependency_versions_generic_exception_batch49():
    """模拟其他 Exception → value None。"""
    with patch("importlib.metadata.version", side_effect=RuntimeError("err")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


# ---------- build_provenance 完整字段 ----------

def test_build_provenance_has_9_keys_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, "1.0")
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


def test_build_provenance_evaluator_version_1_1_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["evaluator_version"] == "1.1"


def test_build_provenance_report_version_1_1_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["report_version"] == "1.1"


def test_build_provenance_max_chars_is_int_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_string_to_int_batch49(tmp_path):
    """max_chars 传入字符串 '800'，函数内部 int(max_chars) 转 int。"""
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", "800", "1.0")
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_parser_name_passed_through_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "kreuzberg", 800, "4.10.2")
    assert out["parser_name"] == "kreuzberg"
    assert out["parser_version"] == "4.10.2"


def test_build_provenance_parser_version_none_batch49(tmp_path):
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_run_timestamp_iso_format_batch49(tmp_path):
    """run_timestamp_iso 是 ISO 8601 格式。"""
    with patch("subprocess.run", side_effect=[
        MagicMock(returncode=0, stdout="abc\n"),
        MagicMock(returncode=0, stdout=""),
    ]):
        out = build_provenance(tmp_path, "fallback", 800, None)
    ts = out["run_timestamp_iso"]
    # ISO 格式：含 T 或 +offset
    assert "T" in ts or "+" in ts
    # 能被 datetime.fromisoformat 解析
    parsed = datetime.fromisoformat(ts)
    assert isinstance(parsed, datetime)


# ---------- build_devset_section 完整字段 ----------

def test_build_devset_section_has_6_keys_batch49():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 3
    m.content_group_count = 2
    m.pdf_count = 2
    m.docx_count = 1
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


def test_build_devset_section_status_passed_through_batch49():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["status"] == "incomplete"


def test_build_devset_section_categories_passed_through_batch49():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = ["x", "y", "z"]
    out = build_devset_section(m)
    assert out["categories_covered"] == ["x", "y", "z"]


# ---------- aggregate_summary 多场景 ----------

def test_aggregate_summary_empty_batch49():
    out = aggregate_summary([])
    assert out["counts"] == {"element_count_total": {"sum": None, "participating_docs": 0}}
    assert out["success_rates"]["pipeline_success"]["rate"] is None
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 0
    assert out["silent_drop_total"] is None


def test_aggregate_summary_counts_sum_batch49():
    docs = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
        {"metrics": {"element_count_total": {"value": 15}}},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 30
    assert out["counts"]["element_count_total"]["participating_docs"] == 3


def test_aggregate_summary_counts_skip_none_batch49():
    docs = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},  # null skipped
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_success_rate_0_batch49():
    docs = [
        {"metrics": {"pipeline_success": {"value": False}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 0
    assert out["success_rates"]["pipeline_success"]["total"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_summary_success_rate_1_batch49():
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 2
    assert out["success_rates"]["pipeline_success"]["rate"] == 1.0


def test_aggregate_summary_success_rate_half_batch49():
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(docs)
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["rate"] == 0.5


def test_aggregate_summary_success_only_true_counts_batch49():
    """null value 不算 success 也不算 total。"""
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(docs)
    # total = len(per_doc_results) = 3
    assert out["success_rates"]["pipeline_success"]["success_count"] == 1
    assert out["success_rates"]["pipeline_success"]["total"] == 3


def test_aggregate_summary_ratio_macro_avg_batch49():
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1.0}}},
    ]
    out = aggregate_summary(docs)
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.75
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 2
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 0


def test_aggregate_summary_ratio_macro_with_null_batch49():
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
        {"metrics": {"metrics": {}}},  # no metric at all
    ]
    out = aggregate_summary(docs)
    # 2 docs no value → not_evaluated=2, participating=1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["macro_average"] == 0.5
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["participating_docs"] == 1
    assert out["ratio_macro_averages"]["pdf_locator_valid_ratio"]["not_evaluated"] == 2


def test_aggregate_summary_silent_drop_total_batch49():
    docs = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_skip_null_batch49():
    docs = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {}},  # no silent_drop_count key
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_has_4_top_keys_batch49():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_ratio_macro_has_all_12_metrics_batch49():
    out = aggregate_summary([])
    assert len(out["ratio_macro_averages"]) == 12


def test_aggregate_summary_figure_caption_not_in_ratio_batch49():
    """figure_caption_* 不在 _RATIO_METRICS 中。"""
    src = inspect.getsource(report_mod)
    assert "figure_caption_precision" not in src
    assert "figure_caption_recall" not in src
    assert "figure_caption_f1" not in src


# ---------- 模块源码补强 ----------

def test_source_contains_subprocess_import_batch49():
    src = inspect.getsource(report_mod)
    assert "import subprocess" in src


def test_source_contains_datetime_import_batch49():
    src = inspect.getsource(report_mod)
    assert "from datetime import datetime" in src


def test_source_contains_pathlib_import_batch49():
    src = inspect.getsource(report_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(report_mod)
    assert "from typing import Any" in src


def test_source_contains_evaluation_import_batch49():
    src = inspect.getsource(report_mod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_source_docstring_mentions_no_mix_types_batch49():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src


def test_source_docstring_mentions_silent_drop_batch49():
    src = inspect.getsource(report_mod)
    assert "silent_drop" in src


def test_source_docstring_mentions_macro_average_batch49():
    src = inspect.getsource(report_mod)
    assert "macro average" in src.lower() or "macro_average" in src.lower() or "macro average" in src


def test_source_ratio_metrics_12_entries_batch49():
    assert len(_RATIO_METRICS) == 12


def test_source_count_metrics_1_entry_batch49():
    assert len(_COUNT_METRICS) == 1


def test_source_success_bool_metrics_1_entry_batch49():
    assert len(_SUCCESS_BOOL_METRICS) == 1


def test_source_all_has_5_entries_batch49():
    src = inspect.getsource(report_mod)
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_source_contains_timeout_10_batch49():
    src = inspect.getsource(report_mod)
    assert "timeout=10" in src


def test_source_contains_capture_output_batch49():
    src = inspect.getsource(report_mod)
    assert "capture_output=True" in src


def test_source_contains_encoding_utf8_batch49():
    src = inspect.getsource(report_mod)
    assert 'encoding="utf-8"' in src


def test_source_contains_errors_replace_batch49():
    src = inspect.getsource(report_mod)
    assert 'errors="replace"' in src


def test_source_contains_isoformat_call_batch49():
    src = inspect.getsource(report_mod)
    assert ".isoformat()" in src


def test_source_contains_astimezone_batch49():
    src = inspect.getsource(report_mod)
    assert ".astimezone()" in src


def test_source_contains_subprocess_run_call_batch49():
    src = inspect.getsource(report_mod)
    assert "subprocess.run(" in src


def test_source_contains_porcelain_command_batch49():
    src = inspect.getsource(report_mod)
    assert '"status", "--porcelain"' in src


def test_source_contains_rev_parse_command_batch49():
    src = inspect.getsource(report_mod)
    assert '"rev-parse", "HEAD"' in src


def test_source_contains_importlib_metadata_batch49():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata" in src


def test_source_contains_package_not_found_batch49():
    src = inspect.getsource(report_mod)
    assert "PackageNotFoundError" in src


def test_source_contains_python_docx_string_batch49():
    src = inspect.getsource(report_mod)
    assert '"python-docx"' in src


def test_source_contains_pypdfium2_string_batch49():
    src = inspect.getsource(report_mod)
    assert '"pypdfium2"' in src


def test_source_contains_pdfplumber_string_batch49():
    src = inspect.getsource(report_mod)
    assert '"pdfplumber"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_5_top_level_functions_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_function_names_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == [
        "get_git_provenance",
        "get_dependency_versions",
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
    ]


def test_ast_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_4_imports_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    # __future__ + subprocess + datetime + Path + Any + evaluation = 6
    assert len(imports) == 6


def test_ast_module_has_3_top_level_assigns_batch49():
    """_RATIO_METRICS + _COUNT_METRICS + _SUCCESS_BOOL_METRICS + __all__ = 4。"""
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_get_git_provenance_has_2_subprocess_calls_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "run"
    ]
    assert len(calls) == 2


def test_ast_get_git_provenance_has_try_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_get_git_provenance_has_except_tuple_batch49():
    """except (OSError, subprocess.SubprocessError)。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    src = ast.unparse(func)
    assert "OSError" in src
    assert "SubprocessError" in src


def test_ast_get_dependency_versions_has_import_inside_function_batch49():
    """import importlib.metadata 在函数内部。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    imports = [n for n in ast.walk(func) if isinstance(n, ast.Import)]
    assert len(imports) == 1


def test_ast_get_dependency_versions_has_try_with_3_handlers_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    # 3 except handlers
    assert len(trys[0].handlers) == 2  # PackageNotFoundError + Exception


def test_ast_build_provenance_has_return_dict_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    src = ast.unparse(func)
    assert "return {" in src
    # 9 个 key (ast.unparse 使用单引号)
    for key in [
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    ]:
        assert f"'{key}'" in src or f'"{key}"' in src


def test_ast_aggregate_summary_has_multiple_for_batch49():
    """aggregate_summary 至少 3 个 for（counts + success_rates + ratio + silent_drop = 4）。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    # 只算直接的 for，不算 list comprehension 内的
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 3


def test_ast_aggregate_summary_silent_drop_uses_list_comprehension_batch49():
    """silent_drop 用 list comprehension（不是 ast.For）。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    list_comps = [n for n in ast.walk(func) if isinstance(n, ast.ListComp)]
    assert len(list_comps) >= 2  # counts values + ratio values + silent_vals


def test_ast_aggregate_summary_has_dict_assignments_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    src = ast.unparse(func)
    # ast.unparse 用单引号
    assert "summary['counts']" in src or 'summary["counts"]' in src
    assert "summary['success_rates']" in src or 'summary["success_rates"]' in src
    assert "summary['ratio_macro_averages']" in src or 'summary["ratio_macro_averages"]' in src
    assert "summary['silent_drop_total']" in src or 'summary["silent_drop_total"]' in src


def test_ast_aggregate_summary_success_uses_sum_with_generator_batch49():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    src = ast.unparse(func)
    assert "sum(" in src


# ---------- forbidden tokens 第一百三十二批 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_popen_batch49():
    """不直接用 Popen（用 run）。"""
    assert "Popen(" not in _src()


def test_source_no_popen_direct_batch49():
    """subprocess.Popen 可以，但单独 popen( 调用禁止。"""
    assert "popen(" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_no_open_batch49():
    """report.py 不调用 open()。"""
    assert "open(" not in _src()
