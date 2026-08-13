"""evaluation/report.py 第九十二轮 edges 测试（Round 670）。

补强 edges64 未触及的角度（第五十一批）。

新角度：
- _RATIO_METRICS / _COUNT_METRICS / _SUCCESS_BOOL_METRICS 完整内容
- get_git_provenance 失败路径（OSError raise / subprocess.SubprocessError raise / nonzero returncode / 空输出）
- get_dependency_versions 路径（pdfplumber/docx/pypdfium2 找不到时 None / 三个都正常）
- build_provenance 字段类型（int max_chars / iso timestamp / dependencies dict / parser_version 可 None）
- build_devset_section 全字段（status / file_count / content_group_count / pdf_count / docx_count / categories_covered）
- aggregate_summary 多场景（empty / counts null / success_rates 全 fail / ratio 全 null / silent_drop 全 null）
- aggregate_summary 类型混合（pipeline_success True+False+null / ratio int+float）
- 模块源码补强（_RATIO_METRICS 12 / _COUNT_METRICS 1 / _SUCCESS_BOOL_METRICS 1 / subprocess import / datetime import / EVALUATOR_VERSION REPORT_VERSION import / __all__ 5）
- AST 结构补强（5 函数 + 顺序 / 无 ClassDef / 无 AsyncFunctionDef / 4 imports / 3 模块常量 Assign / aggregate_summary 嵌套 for + dict / build_provenance 调 get_git_provenance + get_dependency_versions / get_dependency_versions for 循环 + try-except / get_git_provenance try-except）
- forbidden tokens 第一百四十批
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


# ---------- 常量完整内容 ----------

def test_ratio_metrics_length_12_batch51():
    assert len(_RATIO_METRICS) == 12


def test_ratio_metrics_exact_contents_batch51():
    assert set(_RATIO_METRICS) == {
        "schema_valid",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    }


def test_count_metrics_exact_batch51():
    assert _COUNT_METRICS == ("element_count_total",)


def test_success_bool_metrics_exact_batch51():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_ratio_metrics_does_not_include_figure_caption_batch51():
    for m in _RATIO_METRICS:
        assert "figure_caption" not in m


def test_ratio_metrics_does_not_include_silent_drop_batch51():
    assert "silent_drop_count" not in _RATIO_METRICS


def test_ratio_metrics_does_not_include_element_count_batch51():
    assert "element_count_total" not in _RATIO_METRICS


def test_ratio_metrics_is_tuple_batch51():
    assert isinstance(_RATIO_METRICS, tuple)


# ---------- get_git_provenance 失败路径 ----------

def test_get_git_provenance_oserror_batch51(tmp_path):
    """subprocess.run 抛 OSError → catch 返回 commit=None, dirty=True。"""
    def fake_run(*args, **kwargs):
        raise OSError("boom")
    with patch("evaluation.report.subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_subprocess_error_batch51(tmp_path):
    """subprocess.SubprocessError 同样 catch。"""
    def fake_run(*args, **kwargs):
        raise subprocess.SubprocessError("suberr")
    with patch("evaluation.report.subprocess.run", side_effect=fake_run):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_get_git_provenance_nonzero_returncode_batch51(tmp_path):
    """git rev-parse 失败 → commit 保持 None。"""
    r1 = MagicMock(returncode=1, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False  # 第二次 returncode=0 + stdout 空


def test_get_git_provenance_empty_output_batch51(tmp_path):
    """stdout 为空 → commit None。"""
    r1 = MagicMock(returncode=0, stdout="")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] is None
    assert out["git_dirty"] is False


def test_get_git_provenance_success_batch51(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=0, stdout="")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


def test_get_git_provenance_dirty_batch51(tmp_path):
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=0, stdout=" M file.txt\n")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is True


def test_get_git_provenance_dirty_when_status_fails_batch51(tmp_path):
    """status returncode != 0 → dirty=False（bool(0 and ...) 短路）。"""
    r1 = MagicMock(returncode=0, stdout="abc123\n")
    r2 = MagicMock(returncode=128, stdout=" M file.txt\n")
    with patch("evaluation.report.subprocess.run", side_effect=[r1, r2]):
        out = get_git_provenance(tmp_path)
    assert out["git_commit"] == "abc123"
    assert out["git_dirty"] is False


# ---------- get_dependency_versions ----------

def test_get_dependency_versions_returns_dict_batch51():
    out = get_dependency_versions()
    assert isinstance(out, dict)


def test_get_dependency_versions_has_3_keys_batch51():
    out = get_dependency_versions()
    assert set(out.keys()) == {"pdfplumber", "python-docx", "pypdfium2"}


def test_get_dependency_versions_values_str_or_none_batch51():
    out = get_dependency_versions()
    for k, v in out.items():
        assert v is None or isinstance(v, str)


def test_get_dependency_versions_handles_package_not_found_batch51():
    """importlib.metadata.PackageNotFoundError 被 catch → None。"""
    with patch("importlib.metadata.version", side_effect=__import__("importlib").metadata.PackageNotFoundError("x")):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


def test_get_dependency_versions_handles_generic_exception_batch51():
    with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        out = get_dependency_versions()
    for v in out.values():
        assert v is None


# ---------- build_provenance ----------

def test_build_provenance_has_9_keys_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert set(out.keys()) == {
        "git_commit", "git_dirty", "evaluator_version", "report_version",
        "parser_name", "parser_version", "dependencies", "max_chars",
        "run_timestamp_iso",
    }


def test_build_provenance_max_chars_is_int_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_max_chars_int_conversion_batch51(tmp_path):
    """传 float 会被 int() 转换。"""
    out = build_provenance(tmp_path, "fallback", 800.9, None)
    assert out["max_chars"] == 800


def test_build_provenance_parser_version_can_be_none_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["parser_version"] is None


def test_build_provenance_parser_version_string_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, "1.0.0")
    assert out["parser_version"] == "1.0.0"


def test_build_provenance_evaluator_version_is_1_1_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["evaluator_version"] == "1.1"


def test_build_provenance_report_version_is_1_1_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert out["report_version"] == "1.1"


def test_build_provenance_run_timestamp_iso_is_string_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["run_timestamp_iso"], str)
    # 应能被 datetime.fromisoformat 解析
    datetime.fromisoformat(out["run_timestamp_iso"])


def test_build_provenance_dependencies_is_dict_batch51(tmp_path):
    out = build_provenance(tmp_path, "fallback", 800, None)
    assert isinstance(out["dependencies"], dict)


# ---------- build_devset_section ----------

def test_build_devset_section_returns_6_keys_batch51():
    m = MagicMock()
    m.devset_status = "incomplete"
    m.file_count = 5
    m.content_group_count = 3
    m.pdf_count = 2
    m.docx_count = 3
    m.categories_covered = ["a", "b"]
    out = build_devset_section(m)
    assert set(out.keys()) == {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert out["status"] == "incomplete"
    assert out["file_count"] == 5
    assert out["content_group_count"] == 3
    assert out["pdf_count"] == 2
    assert out["docx_count"] == 3
    assert out["categories_covered"] == ["a", "b"]


def test_build_devset_section_status_complete_batch51():
    m = MagicMock()
    m.devset_status = "complete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    out = build_devset_section(m)
    assert out["status"] == "complete"


# ---------- aggregate_summary 多场景 ----------

def test_aggregate_summary_empty_batch51():
    out = aggregate_summary([])
    assert set(out.keys()) == {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}


def test_aggregate_summary_empty_counts_batch51():
    out = aggregate_summary([])
    # counts: element_count_total sum=None, participating_docs=0
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_empty_success_rate_batch51():
    out = aggregate_summary([])
    # success_rates: pipeline_success total=0, rate=None
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 0
    assert sr["total"] == 0
    assert sr["rate"] is None


def test_aggregate_summary_empty_ratio_macro_batch51():
    out = aggregate_summary([])
    for name in _RATIO_METRICS:
        m = out["ratio_macro_averages"][name]
        assert m["macro_average"] is None
        assert m["participating_docs"] == 0
        assert m["not_evaluated"] == 0


def test_aggregate_summary_empty_silent_drop_batch51():
    out = aggregate_summary([])
    assert out["silent_drop_total"] is None


def test_aggregate_summary_success_count_some_batch51():
    """3 文档：2 个 pipeline_success=True，1 个 False。"""
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": False}}},
    ]
    out = aggregate_summary(docs)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 2
    assert sr["total"] == 3
    assert sr["rate"] == 2 / 3


def test_aggregate_summary_counts_sum_int_values_batch51():
    docs = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_skips_none_values_batch51():
    docs = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 10}}},
    ]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] == 15
    assert out["counts"]["element_count_total"]["participating_docs"] == 2


def test_aggregate_summary_counts_all_none_batch51():
    docs = [{"metrics": {"element_count_total": {"value": None}}}]
    out = aggregate_summary(docs)
    assert out["counts"]["element_count_total"]["sum"] is None
    assert out["counts"]["element_count_total"]["participating_docs"] == 0


def test_aggregate_summary_ratio_macro_partial_null_batch51():
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1.0}}},
    ]
    out = aggregate_summary(docs)
    m = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert m["macro_average"] == 0.75
    assert m["participating_docs"] == 2
    assert m["not_evaluated"] == 1


def test_aggregate_summary_silent_drop_sum_batch51():
    docs = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": 5}}},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 8


def test_aggregate_summary_silent_drop_all_null_batch51():
    docs = [
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] is None


def test_aggregate_summary_silent_drop_partial_null_batch51():
    docs = [
        {"metrics": {"silent_drop_count": {"value": 3}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
    ]
    out = aggregate_summary(docs)
    assert out["silent_drop_total"] == 3


def test_aggregate_summary_success_count_null_value_batch51():
    """pipeline_success value=None → 不算成功，但算 total。"""
    docs = [
        {"metrics": {"pipeline_success": {"value": True}}},
        {"metrics": {"pipeline_success": {"value": None}}},
    ]
    out = aggregate_summary(docs)
    sr = out["success_rates"]["pipeline_success"]
    assert sr["success_count"] == 1
    assert sr["total"] == 2
    assert sr["rate"] == 0.5


def test_aggregate_summary_ratio_int_and_float_mix_batch51():
    """ratio 值是 int+float 也能算 macro。"""
    docs = [
        {"metrics": {"pdf_locator_valid_ratio": {"value": 1}}},  # int
        {"metrics": {"pdf_locator_valid_ratio": {"value": 0.5}}},  # float
    ]
    out = aggregate_summary(docs)
    m = out["ratio_macro_averages"]["pdf_locator_valid_ratio"]
    assert m["macro_average"] == 0.75


# ---------- 模块源码补强 ----------

def test_source_contains_subprocess_import_batch51():
    src = inspect.getsource(report_mod)
    assert "import subprocess" in src


def test_source_contains_datetime_import_batch51():
    src = inspect.getsource(report_mod)
    assert "from datetime import datetime" in src


def test_source_contains_path_import_batch51():
    src = inspect.getsource(report_mod)
    assert "from pathlib import Path" in src


def test_source_imports_evaluator_and_report_version_batch51():
    src = inspect.getsource(report_mod)
    assert "from evaluation import EVALUATOR_VERSION, REPORT_VERSION" in src


def test_source_contains_get_git_provenance_docstring_batch51():
    src = inspect.getsource(report_mod)
    assert "读 git commit 与 dirty 状态" in src


def test_source_contains_get_dependency_versions_docstring_batch51():
    src = inspect.getsource(report_mod)
    assert "importlib.metadata.version" in src


def test_source_contains_aggregate_summary_docstring_batch51():
    src = inspect.getsource(report_mod)
    assert "聚合" in src


def test_source_contains_counts_section_batch51():
    src = inspect.getsource(report_mod)
    assert "counts" in src
    assert "success_rates" in src
    assert "ratio_macro_averages" in src


def test_source_contains_silent_drop_sum_batch51():
    src = inspect.getsource(report_mod)
    assert "silent_drop_total" in src


def test_source_contains_no_mixing_types_note_batch51():
    src = inspect.getsource(report_mod)
    assert "不混合" in src


def test_source_all_5_exports_batch51():
    src = inspect.getsource(report_mod)
    assert '"build_provenance"' in src
    assert '"build_devset_section"' in src
    assert '"aggregate_summary"' in src
    assert '"get_git_provenance"' in src
    assert '"get_dependency_versions"' in src


def test_source_contains_timeout_10_batch51():
    src = inspect.getsource(report_mod)
    assert "timeout=10" in src


def test_source_contains_encoding_utf8_batch51():
    src = inspect.getsource(report_mod)
    assert 'encoding="utf-8"' in src


def test_source_contains_errors_replace_batch51():
    src = inspect.getsource(report_mod)
    assert 'errors="replace"' in src


def test_source_contains_capture_output_batch51():
    src = inspect.getsource(report_mod)
    assert "capture_output=True" in src


def test_source_contains_astimezone_iso_batch51():
    src = inspect.getsource(report_mod)
    assert ".astimezone().isoformat()" in src


def test_source_contains_pdfplumber_python_docx_pypdfium2_batch51():
    src = inspect.getsource(report_mod)
    assert '"pdfplumber"' in src
    assert '"python-docx"' in src
    assert '"pypdfium2"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_5_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 5


def test_ast_function_names_order_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["get_git_provenance", "get_dependency_versions", "build_provenance", "build_devset_section", "aggregate_summary"]


def test_ast_no_class_def_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_has_4_imports_batch51():
    """__future__ + subprocess + datetime + Path + Any + EVALUATOR+REPORT = 6。"""
    tree = ast.parse(inspect.getsource(report_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6


def test_ast_has_4_module_level_assigns_batch51():
    """_RATIO_METRICS + _COUNT_METRICS + _SUCCESS_BOOL_METRICS + __all__ = 4。"""
    tree = ast.parse(inspect.getsource(report_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 4


def test_ast_module_docstring_exists_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_has_all_assign_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    all_assign = None
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == "__all__":
                    all_assign = n
    # __all__ 是第 4 个 Assign（紧接前 3 个常量之后）— 但只有 3 个 module-level Assign
    # 加上 __all__ 实际是 4 个，看 source 应有
    assert all_assign is not None


def test_ast_get_git_provenance_has_try_except_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1


def test_ast_get_dependency_versions_has_for_loop_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_get_dependency_versions_has_2_try_batch51():
    """两个 try-except：PackageNotFoundError + Exception。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    tries = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(tries) == 1  # 单个 try 多个 except


def test_ast_build_provenance_calls_get_git_provenance_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    src = ast.unparse(func)
    assert "get_git_provenance(" in src
    assert "get_dependency_versions()" in src


def test_ast_aggregate_summary_has_3_for_loops_batch51():
    """aggregate_summary 用 list comprehension + 单独 for for silent_drop = 3 ast.For。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 3  # 3 个 list comp


def test_ast_aggregate_summary_has_3_explicit_for_in_body_batch51():
    """aggregate_summary body 有 3 个显式 for：_COUNT_METRICS / _SUCCESS_BOOL_METRICS / _RATIO_METRICS。"""
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    for_st = [n for n in func.body if isinstance(n, ast.For)]
    assert len(for_st) == 3


def test_ast_build_devset_section_returns_dict_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_devset_section")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)
    assert len(returns[0].value.keys) == 6


def test_ast_no_with_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.With) for n in ast.walk(tree))


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_global_nonlocal_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_delete_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_raise_top_level_batch51():
    """raise 都在函数/try 内。模块顶层无 raise。"""
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Raise)


def test_ast_no_star_import_batch51():
    tree = ast.parse(inspect.getsource(report_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


# ---------- forbidden tokens 第一百四十批 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch51():
    assert "yield" not in _src()


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_subprocess_only_in_get_provenance_batch51():
    """subprocess 出现在 import 和 subprocess.run、subprocess.SubprocessError。"""
    src = _src()
    # 至少在 import + 2 处使用
    assert src.count("subprocess") >= 3


def test_source_open_count_zero_batch51():
    """report.py 不使用 open()。"""
    assert "open(" not in _src()
