"""evaluation/report.py 第二百六十轮 edges 测试（Round 816）。

补强 edges85 未触及的角度（第一百八十批）。

新角度：
- get_git_provenance 真跑本 worktree：commit 恒为 40 位小写
  hex、dirty 恒为 bool（值不锁，取决于工作区状态）
- success_rates 1/3：rate 恰等于 1/3（0.333...），success_
  count/total 同步
- build_provenance 锁死 evaluator_version "1.1" /
  report_version "1.1"（自跑线不动版本号的守卫）
- aggregate_summary 每次返回全新 dict：改 s1 不影响 s2
- counts 负值 -5 原样求和（不裁剪到 0）
- 源码锁 _COUNT_METRICS / _SUCCESS_BOOL_METRICS 元组
- forbidden tokens 第二百八十六批
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import aggregate_summary, build_provenance, \
    get_git_provenance


# ---------- 真跑 worktree ----------

def test_git_provenance_real_worktree_batch55():
    out = get_git_provenance(Path("."))
    assert re.fullmatch(r"[0-9a-f]{40}", out["git_commit"])
    assert isinstance(out["git_dirty"], bool)


# ---------- success rate 精确 ----------

def test_success_rate_one_third_batch55():
    s = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": True,
                                          "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False,
                                          "reason": None}}},
        {"metrics": {"pipeline_success": {"value": False,
                                          "reason": None}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 3, "rate": 1 / 3}


# ---------- 版本号锁死 ----------

def test_provenance_versions_frozen_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}):
        prov = build_provenance(Path("."), "fallback", 800,
                                "1.0")
    assert prov["evaluator_version"] == "1.1"
    assert prov["report_version"] == "1.1"


# ---------- 每次全新 dict ----------

def test_aggregate_returns_fresh_dict_batch55():
    s1 = aggregate_summary([])
    s2 = aggregate_summary([])
    assert s1 is not s2
    s1["counts"]["zz"] = 1
    assert "zz" not in s2["counts"]


# ---------- counts 负值 ----------

def test_counts_negative_sum_not_clamped_batch55():
    s = aggregate_summary([
        {"metrics": {"element_count_total": {"value": -5,
                                             "reason": None}}}])
    assert s["counts"]["element_count_total"] == {
        "sum": -5, "participating_docs": 1}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_metric_tuples_batch55():
    src = _src()
    assert '_COUNT_METRICS = ("element_count_total",)' in src
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src
    assert 'r["metrics"].get(name, {}).get("value") is True' in src


# ---------- forbidden tokens 第二百八十六批 ----------

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
