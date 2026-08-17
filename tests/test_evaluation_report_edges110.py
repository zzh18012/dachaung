"""evaluation/report.py 第四百二十八轮 edges 测试（Round 984）。

补强 edges109 未触及的角度（第三百六十批，probe 实证）。

新角度：
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 精确元组（与 R970
  的 _RATIO_METRICS 12 项合成三表全锁定）
- pipeline_success value=1（int，truthy 但非 True）→
  `is True` 身份检查不计 → success_count 0 / rate 0.0
- element_count_total value=True → bool 进 sum 算 1
  （同一 bool 家族在两处行为相反）
- get_git_provenance 非 git 目录返回恰 2 键
  {git_commit: None, git_dirty: False}
- schema_valid False 参与 macro → 0.0 / participating 1
- forbidden tokens 第四百五十四批（open 0 + subprocess.run 恰 2）
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import evaluation.report as rpt
from evaluation.report import aggregate_summary, get_git_provenance


# ---------- 内部元组 ----------

def test_count_and_success_tuples_batch182():
    assert rpt._COUNT_METRICS == ("element_count_total",)
    assert rpt._SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- int 1 不算成功 ----------

def test_int_one_pipeline_success_not_counted_batch182():
    s = aggregate_summary([{"metrics": {
        "pipeline_success": {"value": 1, "reason": None}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


# ---------- bool True 求和算 1 ----------

def test_bool_true_element_count_sums_one_batch182():
    s = aggregate_summary([{"metrics": {
        "element_count_total": {"value": True,
                                "reason": None}}}])
    assert s["counts"]["element_count_total"] == {
        "sum": 1, "participating_docs": 1}


# ---------- 非 git provenance ----------

def test_git_provenance_two_keys_batch182():
    g = get_git_provenance(Path(tempfile.mkdtemp()))
    assert list(g) == ["git_commit", "git_dirty"]
    assert g == {"git_commit": None, "git_dirty": False}


# ---------- schema_valid False macro ----------

def test_schema_valid_false_macro_zero_batch182():
    s = aggregate_summary([{"metrics": {
        "schema_valid": {"value": False, "reason": None}}}])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.0,
        "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch182():
    src = _src()
    assert '_COUNT_METRICS = ("element_count_total",)' in src
    assert '_SUCCESS_BOOL_METRICS = ("pipeline_success",)' in src
    assert 'if r["metrics"].get(name, {}).get("value") is True' in src
    assert "macro = sum(values) / len(values)" in src


# ---------- forbidden tokens 第四百五十四批 ----------

def test_source_no_eval_batch182():
    assert "eval(" not in _src()


def test_source_no_exec_batch182():
    assert "exec(" not in _src()


def test_source_no_compile_batch182():
    assert "compile(" not in _src()


def test_source_no_globals_batch182():
    assert "globals(" not in _src()


def test_source_no_locals_batch182():
    assert "locals(" not in _src()


def test_source_no_os_system_batch182():
    assert "os.system" not in _src()


def test_source_no_popen_batch182():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch182():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch182():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch182():
    assert "socket" not in _src()


def test_source_no_requests_batch182():
    assert "requests" not in _src()


def test_source_no_urllib_batch182():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch182():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch182():
    assert "yield" not in _src()


def test_source_no_async_await_batch182():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch182():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch182():
    assert _src().count("subprocess.run") == 2
