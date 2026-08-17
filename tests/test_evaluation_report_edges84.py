"""evaluation/report.py 第二百四十六轮 edges 测试（Round 802）。

补强 edges83 未触及的角度（第一百六十六批）。

新角度：
- chunk_boundary_f1 真实进 ratio macro：[1.0, 0.5] → 0.75
  （_RATIO_METRICS 元组的行为面验证，非仅定义）
- counts 仅 null 值 → {"sum": None, "participating_docs": 0}
  （与空输入同一形态）
- 1e308 双值求和 → sum inf（float 溢出不抛，聚合层不设防，
  现状记录）
- bool+int 混合 ratio：True + 0 → macro 0.5（bool 按 1 参与）
- forbidden tokens 第二百七十二批
"""

from __future__ import annotations

import inspect
import math

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


# ---------- chunk_boundary_f1 macro ----------

def test_chunk_boundary_f1_macro_average_batch54():
    out = aggregate_summary([
        {"metrics": {"chunk_boundary_f1": {"value": 1.0,
                                           "reason": None}}},
        {"metrics": {"chunk_boundary_f1": {"value": 0.5,
                                           "reason": None}}}])
    assert out["ratio_macro_averages"]["chunk_boundary_f1"] == {
        "macro_average": 0.75, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- counts 仅 null ----------

def test_counts_all_null_shape_batch54():
    out = aggregate_summary([
        {"metrics": {"element_count_total": {"value": None,
                                             "reason": "x"}}}])
    assert out["counts"]["element_count_total"] == {
        "sum": None, "participating_docs": 0}


# ---------- float 溢出 ----------

def test_counts_overflow_to_inf_batch54():
    out = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 1e308,
                                             "reason": None}}},
        {"metrics": {"element_count_total": {"value": 1e308,
                                             "reason": None}}}])
    assert math.isinf(
        out["counts"]["element_count_total"]["sum"])


# ---------- bool+int 混合 ----------

def test_ratio_bool_int_mix_macro_half_batch54():
    out = aggregate_summary([
        {"metrics": {"schema_valid": {"value": True,
                                      "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0,
                                      "reason": None}}}])
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_sum_lines_batch54():
    src = _src()
    assert '"sum": sum(values),' in src
    assert "macro = sum(values) / len(values)" in src
    assert '"sum": None, "participating_docs": 0' in src


# ---------- forbidden tokens 第二百七十二批 ----------

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
