"""evaluation/report.py 第五百六十三轮 edges 测试（Round 1223）。

补强 edges131 未触及的角度（第五百九十五批，probe 实证）。

新角度（值在场优先 / None 带因跳过）：
- **count None 带因跳过**——ect
  _v(3) + _v(None, "pipeline_
  failed") → sum 3 / participating 1
  （None 值不进分母首锁）
- **ratio 值在场优先**——_v(0.5,
  "partial") 带 reason 仍计数 →
  macro 0.5 / not_evaluated 0（值
  非 None 即参评，reason 只是注记
  不路由首锁）
- **silent 全 None**——两篇全
  _v(None, reason) → total None
- forbidden tokens 第六百九十二批（open 0，subprocess.run 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


def _entry(doc_id, **metrics):
    return {"doc_id": doc_id, "metrics": metrics}


def _v(value, reason=None):
    return {"value": value, "reason": reason}


# ---------- count None 带因跳过 ----------

def test_count_none_with_reason_skipped_batch421():
    r = aggregate_summary([
        _entry("a", element_count_total=_v(3)),
        _entry("b", element_count_total=_v(
            None, "pipeline_failed")),
    ])
    assert r["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 1}


# ---------- ratio 值在场优先 ----------

def test_ratio_value_beats_reason_batch421():
    r = aggregate_summary([
        _entry("a", pdf_locator_valid_ratio=_v(0.5,
                                               "partial")),
    ])
    assert r["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 0}


def test_ratio_value_beats_reason_mixed_batch421():
    r = aggregate_summary([
        _entry("a", pdf_locator_valid_ratio=_v(0.5,
                                               "partial")),
        _entry("b", pdf_locator_valid_ratio=_v(
            None, "no_elements")),
    ])
    assert r["ratio_macro_averages"][
        "pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 1,
        "not_evaluated": 1}


# ---------- silent 全 None ----------

def test_silent_all_none_total_none_batch421():
    r = aggregate_summary([
        _entry("a", silent_drop_count=_v(None, "x")),
        _entry("b", silent_drop_count=_v(None, "y")),
    ])
    assert r["silent_drop_total"] is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch421():
    src = _src()
    assert "def aggregate_summary(" in src
    assert "_RATIO_METRICS" in src


# ---------- forbidden tokens 第六百九十二批 ----------

def test_source_no_eval_batch421():
    assert "eval(" not in _src()


def test_source_no_exec_batch421():
    assert "exec(" not in _src()


def test_source_no_compile_batch421():
    assert "compile(" not in _src()


def test_source_no_globals_batch421():
    assert "globals(" not in _src()


def test_source_no_locals_batch421():
    assert "locals(" not in _src()


def test_source_no_os_system_batch421():
    assert "os.system" not in _src()


def test_source_no_subprocess_call_batch421():
    assert ".call(" not in _src()


def test_source_no_popen_batch421():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch421():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch421():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch421():
    assert "socket" not in _src()


def test_source_no_requests_batch421():
    assert "requests" not in _src()


def test_source_no_urllib_batch421():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch421():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch421():
    assert "yield" not in _src()


def test_source_no_async_await_batch421():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch421():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch421():
    assert _src().count("subprocess.run") == 2
