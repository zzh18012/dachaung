"""evaluation/report.py 第二百二十五轮 edges 测试（Round 781）。

补强 edges77-80 未触及的角度（第一百四十五批）。

新角度：
- counts 值 True 参与：sum([True]) == 1、participating 1
  （bool 是 int 子类穿过 None 过滤）
- ratio 值 True → macro_average 1.0 且是 float（sum/len 触发真除）
- get_git_provenance 真实 git 集成（本 worktree）：commit 为
  40 位 hex 或 None、dirty 恒 bool（活体冒烟，不造 git 状态）
- run_timestamp_iso 两次调用单调不减（Windows 时钟粒度下
  相邻两次可能同 tick 相等，锁 >= 而非 !=）
- forbidden tokens 第二百五十一批（subprocess 用 run 计数 2 替代）
"""

from __future__ import annotations

import inspect
import re
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_git_provenance,
)


def _m(**kw):
    d = {"element_count_total": {"value": None, "reason": "x"},
         "pipeline_success": {"value": False, "reason": "x"},
         "schema_valid": {"value": None, "reason": "x"}}
    d.update(kw)
    return {"metrics": d}


# ---------- bool 穿过 None 过滤 ----------

def test_counts_bool_value_sums_to_one_batch54():
    out = aggregate_summary(
        [_m(element_count_total={"value": True, "reason": None})])
    assert out["counts"]["element_count_total"] == {"sum": 1,
                                                    "participating_docs": 1}


def test_ratio_bool_value_macro_float_batch54():
    out = aggregate_summary(
        [_m(schema_valid={"value": True, "reason": None})])
    mac = out["ratio_macro_averages"]["schema_valid"]
    assert mac["macro_average"] == 1.0
    assert type(mac["macro_average"]) is float
    assert mac["participating_docs"] == 1
    assert mac["not_evaluated"] == 0


# ---------- 真实 git 集成 ----------

def test_real_git_provenance_smoke_batch54():
    gp = get_git_provenance(Path(__file__).resolve().parents[1])
    assert gp["git_commit"] is None or \
        re.fullmatch(r"[0-9a-f]{40}", gp["git_commit"])
    assert isinstance(gp["git_dirty"], bool)


# ---------- 时间戳单调 ----------

def test_timestamps_monotonic_nondecreasing_batch54():
    stamps = []
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}), \
            patch.object(report_mod, "get_dependency_versions",
                         lambda: {}):
        for _ in range(2):
            p = build_provenance(Path("."), "fallback", 800, None)
            stamps.append(datetime.fromisoformat(
                p["run_timestamp_iso"]))
    # Windows 时钟粒度下相邻两次可能同 tick；只锁不减
    assert stamps[1] >= stamps[0]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_bool_slip_lines_batch54():
    src = _src()
    assert ".get(\"value\") is not None" in src
    assert ".get(\"value\") is True" in src
    assert "datetime.now().astimezone().isoformat()" in src


# ---------- forbidden tokens 第二百五十一批 ----------

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


def test_source_subprocess_run_count_two_batch54():
    assert _src().count("subprocess.run") == 2


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
