"""evaluation/report.py 第五百六十二轮 edges 测试（Round 1216）。

补强 edges130 未触及的角度（第五百八十八批，probe 实证）。

新角度（布尔求和 / 字符串崩 / 裸 None / 严格 True）：
- **布尔求和**——ect True + True →
  sum 2 / 2 篇（bool 是 int 子类照
  加首锁）
- **字符串崩**——ect "7" →
  TypeError: unsupported operand
  type(s) for +: 'int' and 'str'
  （counts 无类型设防，非数值直接
  崩不静默首锁）
- **裸 None 不评**——ratio _v(None)
  无 reason + 另一篇 0.5 → macro
  0.5 / participating 1 /
  not_evaluated 1（value 为 None
  即路由 not_evaluated，与 reason
  有无无关首锁）
- **严格 True**——pipeline_success
  _v(1) 与 _v("yes")（皆 truthy）→
  success 0/2 / rate 0.0（仅字面
  True 计成功首锁）
- forbidden tokens 第六百八十六批（open 0，subprocess.run 2）
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


# ---------- 布尔求和 ----------

def test_boolean_counts_sum_batch414():
    r = aggregate_summary([
        _entry("b1", element_count_total=_v(True)),
        _entry("b2", element_count_total=_v(True)),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": 2, "participating_docs": 2}


# ---------- 字符串崩 ----------

def test_string_counts_crash_batch414():
    with pytest.raises(TypeError) as ei:
        aggregate_summary([
            _entry("s1", element_count_total=_v("7"))])
    assert "unsupported operand type(s) for +: " \
           "'int' and 'str'" in str(ei.value)


# ---------- 裸 None 不评 ----------

def test_bare_none_routes_not_evaluated_batch414():
    r = aggregate_summary([
        _entry("n1", pdf_locator_valid_ratio=_v(None)),
        _entry("n2", pdf_locator_valid_ratio=_v(0.5)),
    ])
    assert r["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 1}


def test_bare_none_silent_drop_total_batch414():
    r = aggregate_summary([
        _entry("d1", silent_drop_count=_v(None)),
        _entry("d2", silent_drop_count=_v(5)),
    ])
    assert r["silent_drop_total"] == 5


# ---------- 严格 True ----------

def test_truthy_non_bool_is_failure_batch414():
    r = aggregate_summary([
        _entry("t1", pipeline_success=_v(1)),
        _entry("t2", pipeline_success=_v("yes")),
    ])
    assert r["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


def test_only_literal_true_succeeds_batch414():
    r = aggregate_summary([
        _entry("t1", pipeline_success=_v(True)),
        _entry("t2", pipeline_success=_v(1.0)),
    ])
    assert r["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch414():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第六百八十六批 ----------

def test_source_no_eval_batch414():
    assert "eval(" not in _src()


def test_source_no_exec_batch414():
    assert "exec(" not in _src()


def test_source_no_compile_batch414():
    assert "compile(" not in _src()


def test_source_no_globals_batch414():
    assert "globals(" not in _src()


def test_source_no_locals_batch414():
    assert "locals(" not in _src()


def test_source_no_os_system_batch414():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch414():
    assert ".call(" not in _src()


def test_source_no_popen_batch414():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch414():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch414():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch414():
    assert "socket" not in _src()


def test_source_no_requests_batch414():
    assert "requests" not in _src()


def test_source_no_urllib_batch414():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch414():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch414():
    assert "yield" not in _src()


def test_source_no_async_await_batch414():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch414():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch414():
    assert _src().count("subprocess.run") == 2
