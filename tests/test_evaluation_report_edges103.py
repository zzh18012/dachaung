"""evaluation/report.py 第三百七十九轮 edges 测试（Round 935）。

补强 edges102 未触及的角度（第三百一十一批，probe 实证）。

新角度：
- ratio_macro_averages 键序与 _RATIO_METRICS 元组完全一致
  （12 项，schema_valid 首、chunk_boundary_f1 尾）
- counts 混合 [5, None, 7] → sum 12 / participating 2
  （None 过滤后再求和）；counts 键序即 _COUNT_METRICS
- silent_drop_count 混合 [2, None, 3] → total 5
- build_provenance 九键全序（git_commit → … → run_timestamp_
  iso）+ 值穿透（parser_version "1.2"、max_chars 800、
  evaluator/report 1.1）
- git rev-parse rc 0 但 stdout 空 → `strip() or None` →
  commit None（dirty 由 porcelain 决定 True）
- porcelain stdout 纯空白 → strip 后空 → dirty False
- rev-parse rc 128 + porcelain 干净 → commit None / dirty
  False（两命令独立）
- get_dependency_versions 恰三键序 [pdfplumber,
  python-docx, pypdfium2]，值均 str|None
- run_timestamp_iso 可 fromisoformat 解析且带时区
- forbidden tokens 第四百零五批（subprocess.run 恰 2 次）
"""

from __future__ import annotations

import inspect
from datetime import datetime
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
)


def _cp(rc, out):
    return CompletedProcess(args=[], returncode=rc, stdout=out,
                            stderr="")


# ---------- ratio 键序 ----------

def test_ratio_key_order_matches_tuple_batch133():
    s = aggregate_summary([{"metrics": {}}])
    assert list(s["ratio_macro_averages"]) == list(_RATIO_METRICS)
    assert len(_RATIO_METRICS) == 12
    assert _RATIO_METRICS[0] == "schema_valid"
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


# ---------- counts 混合 ----------

def test_counts_mixed_none_batch133():
    rows = [
        {"metrics": {"element_count_total": {"value": 5}}},
        {"metrics": {"element_count_total": {"value": None}}},
        {"metrics": {"element_count_total": {"value": 7}}},
    ]
    s = aggregate_summary(rows)
    assert s["counts"] == {"element_count_total": {
        "sum": 12, "participating_docs": 2}}
    assert list(s["counts"]) == ["element_count_total"]


# ---------- silent 混合 ----------

def test_silent_drop_mixed_none_batch133():
    rows = [
        {"metrics": {"silent_drop_count": {"value": 2}}},
        {"metrics": {"silent_drop_count": {"value": None}}},
        {"metrics": {"silent_drop_count": {"value": 3}}},
    ]
    assert aggregate_summary(rows)["silent_drop_total"] == 5


# ---------- provenance 九键全序 ----------

def test_provenance_nine_keys_order_batch133():
    with patch("subprocess.run",
               side_effect=[_cp(0, "abc123\n"), _cp(0, "")]):
        p = build_provenance(Path("."), "fallback", 800, "1.2")
    assert list(p) == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso"]
    assert p["git_commit"] == "abc123"
    assert p["git_dirty"] is False
    assert p["evaluator_version"] == "1.1"
    assert p["report_version"] == "1.1"
    assert p["parser_name"] == "fallback"
    assert p["parser_version"] == "1.2"
    assert p["max_chars"] == 800


# ---------- git 边界 ----------

def test_revparse_empty_stdout_commit_none_batch133():
    with patch("subprocess.run",
               side_effect=[_cp(0, ""), _cp(0, "?? f\n")]):
        p = build_provenance(Path("."), "f", 1, None)
    assert p["git_commit"] is None
    assert p["git_dirty"] is True


def test_porcelain_whitespace_only_clean_batch133():
    with patch("subprocess.run",
               side_effect=[_cp(0, "c\n"), _cp(0, "   \n ")]):
        p = build_provenance(Path("."), "f", 1, None)
    assert p["git_dirty"] is False


def test_revparse_failure_independent_of_dirty_batch133():
    with patch("subprocess.run",
               side_effect=[_cp(128, ""), _cp(0, "")]):
        p = build_provenance(Path("."), "f", 1, None)
    assert p["git_commit"] is None
    assert p["git_dirty"] is False


# ---------- 依赖三键 ----------

def test_dependency_three_keys_batch133():
    dv = get_dependency_versions()
    assert list(dv) == ["pdfplumber", "python-docx",
                        "pypdfium2"]
    assert all(isinstance(v, (str, type(None)))
               for v in dv.values())


# ---------- 时间戳 ----------

def test_timestamp_parseable_with_tz_batch133():
    with patch("subprocess.run",
               side_effect=[_cp(0, "c\n"), _cp(0, "")]):
        p = build_provenance(Path("."), "f", 1, None)
    dt = datetime.fromisoformat(p["run_timestamp_iso"])
    assert dt.tzinfo is not None
    assert p["run_timestamp_iso"][-6:].startswith(("+", "-"))


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch133():
    src = _src()
    assert 'commit = r.stdout.strip() or None' in src
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src
    assert "not_eval = len(per_doc_results) - len(values)" in src


# ---------- forbidden tokens 第四百零五批 ----------

def test_source_no_eval_batch133():
    assert "eval(" not in _src()


def test_source_no_exec_batch133():
    assert "exec(" not in _src()


def test_source_no_compile_batch133():
    assert "compile(" not in _src()


def test_source_no_globals_batch133():
    assert "globals(" not in _src()


def test_source_no_locals_batch133():
    assert "locals(" not in _src()


def test_source_no_os_system_batch133():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_two_batch133():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch133():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch133():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch133():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch133():
    assert "socket" not in _src()


def test_source_no_requests_batch133():
    assert "requests" not in _src()


def test_source_no_urllib_batch133():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch133():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch133():
    assert "yield" not in _src()


def test_source_no_async_await_batch133():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch133():
    assert "open(" not in _src()
