"""evaluation/report.py 第四百四十二轮 edges 测试（Round 998）。

补强 edges111 未触及的角度（第三百七十四批，probe 实证）。

新角度：
- counts [0, None]：0 参与求和（非空列表即真）、None 被滤 →
  sum 0 + participating 1
- ratio [0.0, None]：macro 0.0（非 None）+ participating 1 +
  not_evaluated 1；对照全 None → macro None
- get_dependency_versions 键序固定
  ["pdfplumber", "python-docx", "pypdfium2"]
- get_git_provenance 接受 Path(".")（cwd=str 化后 subprocess
  照常）→ 恰 2 键、git_commit 非 None
- pipeline_success 值为字符串 "true" → is True 不成立 →
  success_count 0 / rate 0.0（强类型不隐式转换）
- forbidden tokens 第四百六十八批（open 0 + subprocess.run
  恰 2）
"""

from __future__ import annotations

import importlib.metadata
import inspect
from pathlib import Path

import evaluation.report as rpt
from evaluation.report import (aggregate_summary,
                               get_dependency_versions,
                               get_git_provenance)


def _doc(v, name):
    return {"metrics": {name: {"value": v, "reason": None}}}


# ---------- counts：0 参与 ----------

def test_counts_zero_participates_batch196():
    s = aggregate_summary([_doc(0, "element_count_total"),
                           _doc(None, "element_count_total")])
    assert s["counts"]["element_count_total"] == {
        "sum": 0, "participating_docs": 1}


# ---------- ratio：0.0 参与 ----------

def test_ratio_zero_participates_batch196():
    s = aggregate_summary(
        [_doc(0.0, "pdf_locator_valid_ratio"),
         _doc(None, "pdf_locator_valid_ratio")])
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 1}


def test_all_none_f1_macro_none_batch196():
    s = aggregate_summary([_doc(None, "chunk_boundary_f1")])
    assert s["ratio_macro_averages"]["chunk_boundary_f1"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


# ---------- 依赖版本键序 ----------

def test_deps_key_order_batch196():
    d = get_dependency_versions()
    assert list(d.keys()) == [
        "pdfplumber", "python-docx", "pypdfium2"]


# ---------- git 源 Path(".") ----------

def test_git_provenance_dot_path_batch196():
    g = get_git_provenance(Path("."))
    assert list(g.keys()) == ["git_commit", "git_dirty"]
    assert g["git_commit"] is not None


# ---------- 字符串 "true" 不算成功 ----------

def test_success_string_true_not_counted_batch196():
    s = aggregate_summary([_doc("true", "pipeline_success")])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch196():
    src = _src()
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert src.count("versions[pkg] = None") == 2


# ---------- forbidden tokens 第四百六十八批 ----------

def test_source_no_eval_batch196():
    assert "eval(" not in _src()


def test_source_no_exec_batch196():
    assert "exec(" not in _src()


def test_source_no_compile_batch196():
    assert "compile(" not in _src()


def test_source_no_globals_batch196():
    assert "globals(" not in _src()


def test_source_no_locals_batch196():
    assert "locals(" not in _src()


def test_source_no_os_system_batch196():
    assert "os.system" not in _src()


def test_source_no_popen_batch196():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch196():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch196():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch196():
    assert "socket" not in _src()


def test_source_no_requests_batch196():
    assert "requests" not in _src()


def test_source_no_urllib_batch196():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch196():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch196():
    assert "yield" not in _src()


def test_source_no_async_await_batch196():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch196():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch196():
    assert _src().count("subprocess.run") == 2
