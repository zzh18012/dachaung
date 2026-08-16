"""evaluation/report.py 第二百零二轮 edges 测试（Round 732）。

补强 edges72/edges73 未触及的角度（第九十七批）。

新角度：
- rev-parse rc!=0 + porcelain rc==0 空 组合 → (None, False)
- subprocess.run 抛 OSError → except 分支 (None, True)
- 依赖版本异常分支：monkeypatch PackageNotFoundError / 通用 Exception → 全 None
- _RATIO_METRICS 精确 12 项 + schema_valid 在列 + figure_caption 不在列
- figure_caption_* 有值也不进 ratio_macro_averages（行为级）
- counts 值 0 保留 {sum:0, participating:1}
- success 混合 1/2 → rate 0.5
- 键在但值 None → not_evaluated 1（与缺键区分）
- 全 null silent_drop（有文档）→ None
- build_provenance：max_chars 800.7→800 / "800"→800 / parser_version 透传 /
  9 键精确 / 时间戳 fromisoformat 往返
- 真仓库：commit/dirty 与 subprocess 实测一致
- 源码补强（timeout=10×2 / errors="replace"×2 / porcelain）
- AST（get_git_provenance Try1·BoolOp2 / deps ExceptHandler2 / aggregate For3·Dict15）
- forbidden tokens 第二百零二批
"""

from __future__ import annotations

import ast
import collections
import importlib.metadata as im
import inspect
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


def _doc(metrics):
    return {"metrics": metrics}


def _m(v):
    return {"value": v}


def _git_fake(rc1=0, out1="abc123\n", rc2=0, out2=""):
    def fake(cmd, **kwargs):
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, rc1, stdout=out1, stderr="")
        return subprocess.CompletedProcess(cmd, rc2, stdout=out2, stderr="")
    return fake


# ---------- git 组合分支 ----------

def test_git_revparse_fail_porcelain_clean_combo_batch54(monkeypatch):
    monkeypatch.setattr(report_mod.subprocess, "run",
                        _git_fake(rc1=128, out1="", rc2=0, out2=""))
    assert get_git_provenance(ROOT) == {"git_commit": None, "git_dirty": False}


def test_git_oserror_exception_branch_batch54(monkeypatch):
    def boom(cmd, **kwargs):
        raise OSError("no git")
    monkeypatch.setattr(report_mod.subprocess, "run", boom)
    assert get_git_provenance(ROOT) == {"git_commit": None, "git_dirty": True}


# ---------- 依赖异常分支 ----------

def test_dependency_package_not_found_batch54(monkeypatch):
    def raise_pnf(pkg):
        raise im.PackageNotFoundError(pkg)
    monkeypatch.setattr(im, "version", raise_pnf)
    assert get_dependency_versions() == {
        "pdfplumber": None, "python-docx": None, "pypdfium2": None}


def test_dependency_generic_exception_batch54(monkeypatch):
    def boom(pkg):
        raise RuntimeError("boom")
    monkeypatch.setattr(im, "version", boom)
    assert get_dependency_versions() == {
        "pdfplumber": None, "python-docx": None, "pypdfium2": None}


# ---------- 指标集合精确性 ----------

def test_ratio_metrics_tuple_exact_batch54():
    assert len(_RATIO_METRICS) == 12
    assert "schema_valid" in _RATIO_METRICS
    assert not any(n.startswith("figure_caption") for n in _RATIO_METRICS)
    assert _COUNT_METRICS == ("element_count_total",)
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


def test_figure_caption_excluded_behavior_level_batch54():
    s = aggregate_summary([_doc({"figure_caption_precision": _m(0.9),
                                 "figure_caption_f1": _m(1.0)})])
    assert "figure_caption_precision" not in s["ratio_macro_averages"]
    assert "figure_caption_f1" not in s["ratio_macro_averages"]


# ---------- 聚合补角 ----------

def test_counts_zero_value_kept_batch54():
    s = aggregate_summary([_doc({"element_count_total": _m(0)})])
    assert s["counts"]["element_count_total"] == {"sum": 0,
                                                  "participating_docs": 1}


def test_success_mixed_half_rate_batch54():
    s = aggregate_summary([_doc({"pipeline_success": _m(True)}),
                           _doc({"pipeline_success": _m(False)})])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


def test_null_value_key_counts_not_evaluated_batch54():
    # 键存在但值 None（区别于缺键）：同样进 not_evaluated
    s = aggregate_summary([_doc({"text_preservation_equal": _m(None)}),
                           _doc({"text_preservation_equal": _m(True)})])
    assert s["ratio_macro_averages"]["text_preservation_equal"] == {
        "macro_average": 1.0, "participating_docs": 1, "not_evaluated": 1}


def test_silent_all_null_with_docs_none_batch54():
    s = aggregate_summary([_doc({"silent_drop_count": _m(None)}), _doc({})])
    assert s["silent_drop_total"] is None


def test_aggregate_top_keys_exact_batch54():
    assert sorted(aggregate_summary([]).keys()) == [
        "counts", "ratio_macro_averages", "silent_drop_total",
        "success_rates"]


# ---------- build_provenance ----------

def test_provenance_max_chars_coercion_batch54(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    p1 = build_provenance(ROOT, "fallback", 800.7, None)
    p2 = build_provenance(ROOT, "fallback", "800", "v9")
    assert p1["max_chars"] == 800 and isinstance(p1["max_chars"], int)
    assert p2["max_chars"] == 800
    assert p1["parser_version"] is None
    assert p2["parser_version"] == "v9"
    assert p1["parser_name"] == "fallback"


def test_provenance_keys_exact_nine_batch54(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": "c" * 40, "git_dirty": False})
    p = build_provenance(ROOT, "fallback", 800, None)
    assert sorted(p.keys()) == [
        "dependencies", "evaluator_version", "git_commit", "git_dirty",
        "max_chars", "parser_name", "parser_version", "report_version",
        "run_timestamp_iso"]
    assert p["git_commit"] == "c" * 40


def test_provenance_timestamp_fromisoformat_roundtrip_batch54(monkeypatch):
    monkeypatch.setattr(report_mod, "get_git_provenance",
                        lambda r: {"git_commit": None, "git_dirty": False})
    ts = build_provenance(ROOT, "fallback", 800, None)["run_timestamp_iso"]
    assert datetime.fromisoformat(ts).isoformat() == ts


# ---------- 真仓库 ----------

def test_real_repo_commit_and_dirty_match_batch54():
    out = get_git_provenance(ROOT)
    r = subprocess.run(["git", "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    assert out["git_commit"] == r.stdout.strip()
    r2 = subprocess.run(["git", "status", "--porcelain"],
                        capture_output=True, text=True)
    assert out["git_dirty"] == bool(r2.stdout.strip())


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_git_invocation_params_batch54():
    src = _src()
    assert src.count("timeout=10") == 2
    assert src.count('errors="replace"') == 2
    assert "porcelain" in src


def test_source_docstring_aggregation_rules_batch54():
    src = _src()
    assert "不混合类型" in src
    assert "无 expectations 的文档不参与" in src


def test_all_export_list_exact_batch54():
    assert report_mod.__all__ == [
        "build_provenance", "build_devset_section", "aggregate_summary",
        "get_git_provenance", "get_dependency_versions"]


# ---------- AST ----------

def _func(name: str) -> ast.FunctionDef:
    tree = ast.parse(inspect.getsource(report_mod))
    return next(n for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def _counts(func) -> collections.Counter:
    return collections.Counter(type(n).__name__ for n in ast.walk(func))


def test_ast_git_provenance_structure_batch54():
    c = _counts(_func("get_git_provenance"))
    assert (c["Try"], c["ExceptHandler"], c["If"], c["BoolOp"],
            c["Compare"]) == (1, 1, 1, 2, 2)


def test_ast_dependency_versions_structure_batch54():
    c = _counts(_func("get_dependency_versions"))
    assert (c["Try"], c["ExceptHandler"], c["For"], c["Import"]) == (1, 2, 1, 1)


def test_ast_aggregate_summary_structure_batch54():
    c = _counts(_func("aggregate_summary"))
    assert (c["For"], c["If"], c["IfExp"], c["ListComp"], c["Dict"],
            c["GeneratorExp"]) == (3, 2, 2, 3, 15, 1)


# ---------- forbidden tokens 第二百零二批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
