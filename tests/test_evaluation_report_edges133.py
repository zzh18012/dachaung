"""evaluation/report.py 第五百六十四轮 edges 测试（Round 1229）。

补强 edges132 未触及的角度（第六百零一批，probe 实证）。

新角度（success 桶独占 / 布尔进 ratio 桶 / 裸值崩）：
- **success 桶独占**——schema_
  valid、text_preservation_
  equal 布尔指标不进 success_
  rates；该桶只收 pipeline_
  success（唯一枚举首锁）
- **布尔进 ratio 桶**——
  schema_valid True+False →
  macro 0.5（布尔按 0/1 平均）
- **零值照计**——ect _v(0) →
  sum 0 / participating 1（0 是
  值非 None）
- **裸值崩**——metrics 直接给
  True 不包 {value} 壳 →
  AttributeError: 'bool' object
  has no attribute 'get'（包装契
  约靠崩强制首锁）
- forbidden tokens 第六百九十七批（open 0，subprocess.run 2）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


def _entry(doc_id, **metrics):
    return {"doc_id": doc_id, "metrics": metrics}


def _v(value, reason=None):
    return {"value": value, "reason": reason}


# ---------- success 桶独占 ----------

def test_success_bucket_exclusive_batch427():
    r = aggregate_summary([
        _entry("s", schema_valid=_v(True),
               text_preservation_equal=_v(False)),
    ])
    assert sorted(r["success_rates"].keys()) == \
        ["pipeline_success"]


# ---------- 布尔进 ratio 桶 ----------

def test_boolean_metrics_macro_average_batch427():
    r = aggregate_summary([
        _entry("s", schema_valid=_v(True)),
        _entry("t", schema_valid=_v(False)),
    ])
    assert r["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


def test_tpe_macro_average_batch427():
    r = aggregate_summary([
        _entry("u", text_preservation_equal=_v(True)),
    ])
    assert r["ratio_macro_averages"][
        "text_preservation_equal"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 零值照计 ----------

def test_zero_value_participates_batch427():
    r = aggregate_summary([
        _entry("z", element_count_total=_v(0)),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": 0, "participating_docs": 1}


# ---------- 裸值崩 ----------

def test_bare_value_crashes_batch427():
    with pytest.raises(AttributeError) as ei:
        aggregate_summary([
            _entry("b", pipeline_success=True)])
    assert "'bool' object has no attribute 'get'" \
        in str(ei.value)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch427():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第六百九十七批 ----------

def test_source_no_eval_batch427():
    assert "eval(" not in _src()


def test_source_no_exec_batch427():
    assert "exec(" not in _src()


def test_source_no_compile_batch427():
    assert "compile(" not in _src()


def test_source_no_globals_batch427():
    assert "globals(" not in _src()


def test_source_no_locals_batch427():
    assert "locals(" not in _src()


def test_source_no_os_system_batch427():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch427():
    assert ".call(" not in _src()


def test_source_no_popen_batch427():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch427():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch427():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch427():
    assert "socket" not in _src()


def test_source_no_requests_batch427():
    assert "requests" not in _src()


def test_source_no_urllib_batch427():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch427():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch427():
    assert "yield" not in _src()


def test_source_no_async_await_batch427():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch427():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch427():
    assert _src().count("subprocess.run") == 2
