"""evaluation/report.py 第九十六轮 edges 测试（Round 690）。

补强 edges67 未触及的角度（第五十六批）。

新角度：
- get_dependency_versions mock 矩阵（version 正常返回 / PackageNotFoundError → None / 泛型 Exception → None / 三包不同结局混合 / 调用次数 3 / 函数级 import）
- get_git_provenance 更细（commit strip 尾换行 / dirty bool 语义矩阵 / cwd=str(project_root) / capture_output+text+encoding+errors kwargs / 第二次 run 抛 OSError 仍走 except）
- aggregate_summary 混合独立（单 doc 四类指标并存互不干扰 / success value=1(int) 不算成功 is True 严格 / ratio value int 参与 / not_evaluated = total - participating 精确 / 12 ratio 名单顺序）
- build_provenance 细节（git_dirty True 透传 / 40 字符 commit 透传 / max_chars 字符串转 int / dependencies 来自 mock）
- 源码补强（is True 字面 / rate 条件表达式 / macro 表达式 / silent_drop_total 条件 / except PackageNotFoundError + Exception 双层 / build_devset_section type: ignore）
- AST 补强（_RATIO_METRICS 首尾元素 / get_dependency_versions 1 函数级 Import + 2 except handlers / aggregate_summary 4 个 summary[...] 赋值顺序 / get_git_provenance except Tuple 2 元素）
- forbidden tokens 第一百六十批
"""

from __future__ import annotations

import ast
import importlib.metadata
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


# ---------- get_dependency_versions mock 矩阵 ----------

def test_dependency_versions_normal_return_batch52():
    with patch("importlib.metadata.version", return_value="1.2.3") as v:
        out = get_dependency_versions()
    assert v.call_count == 3
    assert out == {"pdfplumber": "1.2.3", "python-docx": "1.2.3", "pypdfium2": "1.2.3"}


def test_dependency_versions_package_not_found_batch52():
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError("x"),
    ):
        out = get_dependency_versions()
    assert out == {"pdfplumber": None, "python-docx": None, "pypdfium2": None}


def test_dependency_versions_generic_exception_batch52():
    with patch("importlib.metadata.version", side_effect=RuntimeError("boom")):
        out = get_dependency_versions()
    assert all(v is None for v in out.values())


def test_dependency_versions_mixed_outcomes_batch52():
    def fake_version(pkg):
        if pkg == "pdfplumber":
            return "0.11.0"
        if pkg == "python-docx":
            raise importlib.metadata.PackageNotFoundError(pkg)
        raise ValueError(pkg)
    with patch("importlib.metadata.version", side_effect=fake_version):
        out = get_dependency_versions()
    assert out == {"pdfplumber": "0.11.0", "python-docx": None, "pypdfium2": None}


def test_dependency_versions_pkg_order_batch52():
    with patch("importlib.metadata.version", return_value="v") as v:
        get_dependency_versions()
    called = [c.args[0] for c in v.call_args_list]
    assert called == ["pdfplumber", "python-docx", "pypdfium2"]


def test_dependency_versions_returns_new_dict_batch52():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b
    assert a is not b


# ---------- get_git_provenance 更细 ----------

def _run(returncode=0, stdout=""):
    m = MagicMock()
    m.returncode = returncode
    m.stdout = stdout
    return m


def test_git_commit_trailing_newline_stripped_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="abc123\n"), _run(stdout="")]
        out = get_git_provenance(Path("."))
    assert out["git_commit"] == "abc123"


def test_git_dirty_true_when_porcelain_output_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="c"), _run(returncode=0, stdout="M f\n")]
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is True


def test_git_dirty_false_when_clean_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="c"), _run(returncode=0, stdout="")]
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False


def test_git_cwd_kwarg_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="c"), _run()]
        get_git_provenance(Path("myroot"))
    for call in run.call_args_list:
        assert call.kwargs.get("cwd") == "myroot"


def test_git_run_kwargs_batch52():
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="c"), _run()]
        get_git_provenance(Path("."))
    for call in run.call_args_list:
        assert call.kwargs.get("capture_output") is True
        assert call.kwargs.get("text") is True
        assert call.kwargs.get("encoding") == "utf-8"
        assert call.kwargs.get("errors") == "replace"


def test_git_second_run_oserror_batch52():
    """第一次成功、第二次抛 OSError → except 兜底 commit=None。"""
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(stdout="c"), OSError("gone")]
        out = get_git_provenance(Path("."))
    assert out["git_commit"] is None
    assert out["git_dirty"] is True


def test_git_dirty_default_true_before_run_batch52():
    """初始 dirty=True：第一条命令 returncode≠0 且第二条也失败时保持 True。"""
    with patch("evaluation.report.subprocess.run") as run:
        run.side_effect = [_run(returncode=1), _run(returncode=1, stdout="M")]
        out = get_git_provenance(Path("."))
    assert out["git_dirty"] is False  # returncode≠0 → bool(0==0 and ...) = False


# ---------- aggregate_summary 混合独立 ----------

def _doc_full() -> dict[str, Any]:
    return {"metrics": {
        "pipeline_success": {"value": True},
        "element_count_total": {"value": 7},
        "schema_valid": {"value": True},
        "chunk_boundary_f1": {"value": 0.5},
        "silent_drop_count": {"value": 2},
    }}


def test_aggregate_mixed_types_independent_batch52():
    s = aggregate_summary([_doc_full()])
    assert s["counts"]["element_count_total"]["sum"] == 7
    assert s["success_rates"]["pipeline_success"]["rate"] == 1.0
    assert s["ratio_macro_averages"]["schema_valid"]["macro_average"] == 1.0
    assert s["ratio_macro_averages"]["chunk_boundary_f1"]["macro_average"] == 0.5
    assert s["silent_drop_total"] == 2


def test_aggregate_success_int_one_not_counted_batch52():
    """value=1（int）不是 is True → 不算成功。"""
    results = [{"metrics": {"pipeline_success": {"value": 1}}}]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0


def test_aggregate_success_truthy_string_not_counted_batch52():
    results = [{"metrics": {"pipeline_success": {"value": "yes"}}}]
    s = aggregate_summary(results)
    assert s["success_rates"]["pipeline_success"]["success_count"] == 0
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_aggregate_ratio_int_value_participates_batch52():
    results = [{"metrics": {"chunk_boundary_f1": {"value": 1}}}]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["participating_docs"] == 1
    assert r["macro_average"] == 1


def test_aggregate_not_evaluated_exact_batch52():
    results = [
        {"metrics": {"chunk_boundary_f1": {"value": 0.5}}},
        {"metrics": {"chunk_boundary_f1": {"value": None}}},
        {"metrics": {"metrics_absent": {"value": 1}}},
    ]
    s = aggregate_summary(results)
    r = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert r["participating_docs"] == 1
    assert r["not_evaluated"] == 2


def test_ratio_metrics_order_batch52():
    assert _RATIO_METRICS == (
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
    )


def test_aggregate_empty_ratio_macro_none_all_12_batch52():
    s = aggregate_summary([])
    for name in _RATIO_METRICS:
        assert s["ratio_macro_averages"][name] == {
            "macro_average": None, "participating_docs": 0, "not_evaluated": 0,
        }


def test_aggregate_counts_key_set_batch52():
    s = aggregate_summary([])
    assert set(s["counts"].keys()) == set(_COUNT_METRICS)
    assert set(s["success_rates"].keys()) == set(_SUCCESS_BOOL_METRICS)


# ---------- build_provenance 细节 ----------

def test_build_provenance_git_dirty_true_passthrough_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": "c", "git_dirty": True}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, None)
    assert out["git_dirty"] is True


def test_build_provenance_commit_40_chars_batch52():
    c = "a" * 40
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": c, "git_dirty": False}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", 800, None)
    assert out["git_commit"] == c


def test_build_provenance_max_chars_str_converted_batch52():
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}), \
         patch("evaluation.report.get_dependency_versions", return_value={}):
        out = build_provenance(Path("."), "fallback", "800", None)
    assert out["max_chars"] == 800
    assert isinstance(out["max_chars"], int)


def test_build_provenance_dependencies_from_helper_batch52():
    deps = {"pdfplumber": "0.11.0", "python-docx": "1.1.2", "pypdfium2": None}
    with patch("evaluation.report.get_git_provenance", return_value={"git_commit": None, "git_dirty": True}), \
         patch("evaluation.report.get_dependency_versions", return_value=deps) as gdv:
        out = build_provenance(Path("."), "fallback", 800, None)
    assert out["dependencies"] == deps
    gdv.assert_called_once_with()


# ---------- 源码补强 ----------

def test_source_success_is_true_literal_batch52():
    src = inspect.getsource(report_mod)
    assert ".get(\"value\") is True" in src


def test_source_rate_conditional_batch52():
    src = inspect.getsource(report_mod)
    assert "(successes / total) if total else None" in src


def test_source_macro_expression_batch52():
    src = inspect.getsource(report_mod)
    assert "macro = sum(values) / len(values)" in src


def test_source_silent_drop_conditional_batch52():
    src = inspect.getsource(report_mod)
    assert "sum(silent_vals) if silent_vals else None" in src


def test_source_except_two_layers_batch52():
    src = inspect.getsource(report_mod)
    assert "except importlib.metadata.PackageNotFoundError:" in src
    assert src.count("versions[pkg] = None") == 2


def test_source_build_devset_type_ignore_batch52():
    src = inspect.getsource(report_mod)
    assert "# type: ignore[no-untyped-def]" in src


def test_source_git_commit_or_none_batch52():
    src = inspect.getsource(report_mod)
    assert "r.stdout.strip() or None" in src


def test_source_git_dirty_bool_expression_batch52():
    src = inspect.getsource(report_mod)
    assert "bool(r2.returncode == 0 and r2.stdout.strip())" in src


def test_source_docstring_no_composite_score_batch52():
    src = inspect.getsource(report_mod)
    assert "不混合类型" in src
    assert "macro average" in src


# ---------- AST 补强 ----------

def test_ast_ratio_metrics_first_last_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "_RATIO_METRICS" for t in n.targets)
    )
    elts = [e.value for e in assign.value.elts]
    assert elts[0] == "schema_valid"
    assert elts[-1] == "chunk_boundary_f1"


def test_ast_dependency_versions_function_import_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    imports = [n for n in func.body if isinstance(n, ast.Import)]
    assert len(imports) == 1
    assert imports[0].names[0].name == "importlib.metadata"


def test_ast_dependency_versions_2_except_handlers_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_dependency_versions")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1
    assert len(trys[0].handlers) == 2


def test_ast_aggregate_summary_assign_order_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    keys = [
        t.slice.value for n in func.body if isinstance(n, ast.Assign)
        for t in n.targets if isinstance(t, ast.Subscript)
        and isinstance(t.value, ast.Name) and t.value.id == "summary"
        and isinstance(t.slice, ast.Constant)
    ]
    assert keys == ["counts", "success_rates", "ratio_macro_averages", "silent_drop_total"]


def test_ast_git_provenance_except_tuple_2_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_git_provenance")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    handler_type = trys[0].handlers[0].type
    assert isinstance(handler_type, ast.Tuple)
    names = [ast.unparse(e) for e in handler_type.elts]
    assert sorted(names) == ["OSError", "subprocess.SubprocessError"]


def test_ast_aggregate_summary_3_for_targets_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "aggregate_summary")
    iters = [
        n.iter.id for n in func.body if isinstance(n, ast.For)
        and isinstance(n.iter, ast.Name)
    ]
    assert iters == ["_COUNT_METRICS", "_SUCCESS_BOOL_METRICS", "_RATIO_METRICS"]


def test_ast_build_provenance_calls_helpers_in_order_batch52():
    tree = ast.parse(inspect.getsource(report_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build_provenance")
    calls = [
        n.func.id for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    ]
    assert calls[0] == "get_git_provenance"
    assert "get_dependency_versions" in calls


# ---------- forbidden tokens 第一百六十批 ----------

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
    assert "Popen" not in _src()
    assert "popen(" not in _src()


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
    assert "open(" not in _src()
