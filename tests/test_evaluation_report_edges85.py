"""evaluation/report.py 第二百五十三轮 edges 测试（Round 809）。

补强 edges84 未触及的角度（第一百七十三批）。

新角度：
- get_git_provenance 真跑非 git 目录：rev-parse 失败 → commit
  None；status --porcelain returncode != 0 → dirty **False**
  （docstring "失败时 dirty=true" 只对 exception 路径成立，
  returncode 路径是 False —— 现状记录）
- summary 顶层 4 键全序：counts / success_rates /
  ratio_macro_averages / silent_drop_total
- 未知指标名：任何 section 都不出现，全部按缺勤计
  （not_evaluated = 1）
- build_provenance 时间戳：astimezone 后带 tz offset，
  datetime.fromisoformat 可回解
- build_provenance max_chars 555.9 → int 555（截断非四舍五入）
- forbidden tokens 第二百七十九批
"""

from __future__ import annotations

import inspect
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import aggregate_summary, build_provenance, \
    get_git_provenance


# ---------- 非 git 目录真跑 ----------

def test_git_provenance_non_git_dir_batch55():
    tmp = Path(tempfile.mkdtemp())
    out = get_git_provenance(tmp)
    assert out == {"git_commit": None, "git_dirty": False}


# ---------- summary 顶层键序 ----------

def test_summary_top_level_key_order_batch55():
    s = aggregate_summary([])
    assert list(s.keys()) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]


# ---------- 未知指标 ----------

def test_unknown_metric_ignored_everywhere_batch55():
    s = aggregate_summary([
        {"metrics": {"unknown_metric": {"value": 5,
                                        "reason": None}}}])
    assert s["counts"] == {
        "element_count_total": {"sum": None, "participating_docs": 0}}
    assert s["silent_drop_total"] is None
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}


# ---------- 时间戳可回解 ----------

def test_provenance_timestamp_tz_aware_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}):
        prov = build_provenance(Path("."), "fallback", 800, "1.0")
    ts = prov["run_timestamp_iso"]
    dt = datetime.fromisoformat(ts)
    assert dt.tzinfo is not None
    assert list(prov.keys()) == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso"]


# ---------- max_chars 截断 ----------

def test_provenance_max_chars_float_truncated_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}):
        prov = build_provenance(Path("."), "fallback", 555.9, None)
    assert prov["max_chars"] == 555
    assert isinstance(prov["max_chars"], int)
    assert prov["parser_version"] is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_dirty_line_batch55():
    src = _src()
    assert ("dirty = bool(r2.returncode == 0 and r2.stdout.strip())"
            in src)
    assert 'datetime.now().astimezone().isoformat()' in src
    assert "int(max_chars)" in src


# ---------- forbidden tokens 第二百七十九批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_two_batch55():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
