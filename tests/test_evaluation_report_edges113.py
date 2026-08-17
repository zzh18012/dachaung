"""evaluation/report.py 第四百四十九轮 edges 测试（Round 1005）。

补强 edges112 未触及的角度（第三百八十一批，probe 实证）。

新角度（聚合风格分歧矩阵 + 版本常量跨模块一致性）：
- 4 文档混合 [None, 0.0, 0.5, 1.0]：macro 0.5（3 值均值）、
  participating 3、not_evaluated 1 —— **键缺失与值 None
  等价**都进 not_evaluated
- silent_drop [None, 0, 2, 缺键] → 2（0 参与、缺键/None
  滤除）
- counts [None, 0, 7, 缺键] → sum 7 + participating 2
- pipeline_success [T,F,F,F] → rate 0.25
- EVALUATOR_VERSION / REPORT_VERSION 在 evaluation.__init__
  与 report 模块同一值 "1.1"；runner 引用的 REPORT_VERSION
  同为 "1.1"（跨模块单一定义点）
- forbidden tokens 第四百七十五批（open 0 + subprocess.run
  恰 2）
"""

from __future__ import annotations

import inspect

import evaluation
import evaluation.report as rpt
import evaluation.runner as runner_mod
from evaluation.report import aggregate_summary


def _m(v, reason=None):
    return {"value": v, "reason": reason}


_DOCS = [
    {"metrics": {
        "pdf_locator_valid_ratio": _m(None, "x"),
        "silent_drop_count": _m(None, "x"),
        "element_count_total": _m(None, "x"),
        "pipeline_success": _m(True)}},
    {"metrics": {
        "pdf_locator_valid_ratio": _m(0.0),
        "silent_drop_count": _m(0),
        "element_count_total": _m(0),
        "pipeline_success": _m(False)}},
    {"metrics": {
        "pdf_locator_valid_ratio": _m(0.5),
        "silent_drop_count": _m(2),
        "element_count_total": _m(7),
        "pipeline_success": _m(False)}},
    {"metrics": {
        "pdf_locator_valid_ratio": _m(1.0),
        "pipeline_success": _m(False)}},
]


# ---------- ratio 分歧矩阵 ----------

def test_ratio_divergence_matrix_batch203():
    s = aggregate_summary(_DOCS)
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 3,
        "not_evaluated": 1}


# ---------- silent 求和 ----------

def test_silent_mixed_missing_key_batch203():
    s = aggregate_summary(_DOCS)
    assert s["silent_drop_total"] == 2


# ---------- counts ----------

def test_counts_mixed_missing_key_batch203():
    s = aggregate_summary(_DOCS)
    assert s["counts"]["element_count_total"] == {
        "sum": 7, "participating_docs": 2}


# ---------- 成功率 1/4 ----------

def test_rate_quarter_batch203():
    s = aggregate_summary(_DOCS)
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 4, "rate": 0.25}


# ---------- 版本常量跨模块一致 ----------

def test_version_constants_identity_batch203():
    assert evaluation.EVALUATOR_VERSION == \
        rpt.EVALUATOR_VERSION == "1.1"
    assert evaluation.REPORT_VERSION == \
        rpt.REPORT_VERSION == \
        runner_mod.REPORT_VERSION == "1.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch203():
    src = _src()
    assert "macro = sum(values) / len(values)" in src
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


# ---------- forbidden tokens 第四百七十五批 ----------

def test_source_no_eval_batch203():
    assert "eval(" not in _src()


def test_source_no_exec_batch203():
    assert "exec(" not in _src()


def test_source_no_compile_batch203():
    assert "compile(" not in _src()


def test_source_no_globals_batch203():
    assert "globals(" not in _src()


def test_source_no_locals_batch203():
    assert "locals(" not in _src()


def test_source_no_os_system_batch203():
    assert "os.system" not in _src()


def test_source_no_popen_batch203():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch203():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch203():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch203():
    assert "socket" not in _src()


def test_source_no_requests_batch203():
    assert "requests" not in _src()


def test_source_no_urllib_batch203():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch203():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch203():
    assert "yield" not in _src()


def test_source_no_async_await_batch203():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch203():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch203():
    assert _src().count("subprocess.run") == 2
