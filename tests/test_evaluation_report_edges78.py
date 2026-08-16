"""evaluation/report.py 第二百零六轮 edges 测试（Round 760）。

补强 edges74-77 未触及的角度（第一百二十四批）。

新角度：
- get_dependency_versions 不做类型校正：version() 返回 int 5 → 原样 int；
  两次调用返回相等但不同一的 dict
- build_provenance 强转面：parser_version ""（falsy 但原样记录）；
  max_chars "800"（数字字符串 int() 接受）→ 800；True → 1
- counts 浮点求和 1.5+2.5 → 4.0（不强制 int）
- ratio 聚合键序 == _RATIO_METRICS 序（schema_valid 首位 … f1 末位）
- git commit 多行 stdout "abc\\ndef\\n" → strip 只去两端 → 'abc\\ndef'
  整段保留（含内嵌换行，现状记录）
- 单文档空 metrics：counts sum None、rate 0.0（分母 1）
- metric 键缺失与值 null 同等对待：participating 1 / not_evaluated 2
- forbidden tokens 第二百三十批
"""

from __future__ import annotations

import importlib.metadata as im
import inspect
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


class _R:
    def __init__(self, rc, out):
        self.returncode = rc
        self.stdout = out


# ---------- 依赖版本 ----------

def test_dependency_version_non_str_kept_batch54(monkeypatch):
    real = im.version
    monkeypatch.setattr(
        im, "version",
        lambda pkg: 5 if pkg == "pdfplumber" else real(pkg))
    v = get_dependency_versions()
    assert v["pdfplumber"] == 5
    assert isinstance(v["pdfplumber"], int)


def test_dependency_versions_fresh_dict_batch54():
    a = get_dependency_versions()
    b = get_dependency_versions()
    assert a == b
    assert a is not b


# ---------- provenance 强转 ----------

def test_provenance_empty_parser_version_kept_batch54():
    p = build_provenance(ROOT, "fallback", 800, "")
    assert p["parser_version"] == ""


def test_provenance_numeric_str_max_chars_batch54():
    p = build_provenance(ROOT, "fallback", "800", None)
    assert p["max_chars"] == 800


def test_provenance_bool_max_chars_batch54():
    p = build_provenance(ROOT, "fallback", True, None)
    assert p["max_chars"] == 1


# ---------- counts 浮点 ----------

def test_counts_float_sum_batch54():
    s = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 1.5}}},
        {"metrics": {"element_count_total": {"value": 2.5}}}])
    assert s["counts"]["element_count_total"] == {"sum": 4.0,
                                                  "participating_docs": 2}


# ---------- ratio 键序 ----------

def test_ratio_avgs_key_order_matches_tuple_batch54():
    s = aggregate_summary([])
    assert list(s["ratio_macro_averages"]) == list(report_mod._RATIO_METRICS)
    assert list(s["ratio_macro_averages"])[0] == "schema_valid"
    assert list(s["ratio_macro_averages"])[-1] == "chunk_boundary_f1"


# ---------- git 多行 commit ----------

def test_git_commit_multiline_stdout_kept_batch54(monkeypatch):
    monkeypatch.setattr(
        report_mod.subprocess, "run",
        lambda cmd, **k: (_R(0, "abc\ndef\n")
                          if cmd[1] == "rev-parse" else _R(0, "")))
    assert get_git_provenance(".")["git_commit"] == "abc\ndef"


# ---------- 空与缺键 ----------

def test_single_doc_empty_metrics_batch54():
    s = aggregate_summary([{"metrics": {}}])
    assert s["counts"] == {"element_count_total": {"sum": None,
                                                   "participating_docs": 0}}
    assert s["success_rates"]["pipeline_success"]["rate"] == 0.0


def test_missing_key_same_as_null_batch54():
    s = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 0.5}}},
        {"metrics": {}},
        {"metrics": {"schema_valid": {"value": None}}}])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 1, "not_evaluated": 2}


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_coercion_lines_batch54():
    src = _src()
    assert '"max_chars": int(max_chars)' in src
    assert "r.stdout.strip() or None" in src


# ---------- forbidden tokens 第二百三十批 ----------

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


def test_source_subprocess_run_count_two_batch54():
    assert _src().count("subprocess.run") == 2
