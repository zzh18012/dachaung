"""evaluation/report.py 第三百三十轮 edges 测试（Round 886）。

补强 edges95 未触及的角度（第二百六十批）。

新角度：
- 三组指标名单互不相交（ratio / count / success）
- ratio_macro_averages 键序 == _RATIO_METRICS 序；
  success_rates 键序 == _SUCCESS_BOOL_METRICS 序
  （循环插入序锁定）
- 100 份文档规模聚合 sanity（sum 550、rate 1.0）
- forbidden tokens 第三百五十六批
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    _RATIO_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
)


def _pd(metrics):
    return {"metrics": metrics}


# ---------- 名单互斥 ----------

def test_metric_groups_disjoint_batch84():
    r, c, s = (set(_RATIO_METRICS), set(_COUNT_METRICS),
               set(_SUCCESS_BOOL_METRICS))
    assert not (r & c)
    assert not (r & s)
    assert not (c & s)


# ---------- 键序 ----------

def test_ratio_key_order_matches_tuple_batch84():
    s = aggregate_summary([
        _pd({"schema_valid": {"value": 1.0},
             "chunk_boundary_f1": {"value": 0.5}})])
    assert list(s["ratio_macro_averages"]) == \
        list(_RATIO_METRICS)


def test_success_key_order_matches_tuple_batch84():
    s = aggregate_summary([_pd({"pipeline_success":
                                {"value": True}})])
    assert list(s["success_rates"]) == \
        list(_SUCCESS_BOOL_METRICS)


# ---------- 规模 sanity ----------

def test_hundred_docs_scale_batch84():
    rows = []
    for i in range(100):
        rows.append(_pd({
            "pipeline_success": {"value": True},
            "element_count_total": {"value": i % 10 + 1}}))
    s = aggregate_summary(rows)
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 100, "total": 100, "rate": 1.0}
    # sum = 10 * (1+2+...+10) = 550
    assert s["counts"]["element_count_total"] == {
        "sum": 550, "participating_docs": 100}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch84():
    src = _src()
    assert 'summary["ratio_macro_averages"] = ratio_avgs' in src
    assert 'summary["success_rates"] = success_rates' in src
    assert "summary[\"counts\"] = counts" in src


# ---------- forbidden tokens 第三百五十六批 ----------

def test_source_no_eval_batch84():
    assert "eval(" not in _src()


def test_source_no_exec_batch84():
    assert "exec(" not in _src()


def test_source_no_compile_batch84():
    assert "compile(" not in _src()


def test_source_no_globals_batch84():
    assert "globals(" not in _src()


def test_source_no_locals_batch84():
    assert "locals(" not in _src()


def test_source_no_os_system_batch84():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch84():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch84():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch84():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch84():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch84():
    assert "socket" not in _src()


def test_source_no_requests_batch84():
    assert "requests" not in _src()


def test_source_no_urllib_batch84():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch84():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch84():
    assert "yield" not in _src()


def test_source_no_async_await_batch84():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch84():
    assert "open(" not in _src()
