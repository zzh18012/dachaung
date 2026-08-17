"""evaluation/report.py 第二百六十七轮 edges 测试（Round 823）。

补强 edges86 未触及的角度（第一百九十四批）。

新角度：
- ratio macro 浮点伪影原样保留：[0.1, 0.2] → 0.15000000000000002
  （sum/len 不做圆整）
- pdf_locator_valid_ratio 单指标 macro [1.0, 0.0] → 0.5
- get_dependency_versions 键序锁定（pdfplumber /
  python-docx / pypdfium2 插入序）
- success_rates **is True 严格性**：value 1（int）不计成功 →
  [True, 1] → success_count 1、rate 0.5
- counts 值 0 参与（`is not None` 过滤，0 非 None）→ sum 0 +
  participating 1
- silent_drop_count [0, 0] → 0（列表真值）；全 None → None
- ratio 0.0 与缺键混排：macro 0.0 + not_evaluated 1
- forbidden tokens 第二百九十三批
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import aggregate_summary, \
    get_dependency_versions


# ---------- 浮点伪影 ----------

def test_ratio_macro_float_artifact_batch55():
    s = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 0.1,
                                      "reason": None}}},
        {"metrics": {"schema_valid": {"value": 0.2,
                                      "reason": None}}}])
    m = s["ratio_macro_averages"]["schema_valid"]
    assert m["macro_average"] == 0.15000000000000002
    assert m["participating_docs"] == 2


# ---------- pdf_locator macro ----------

def test_pdf_locator_macro_half_batch55():
    s = aggregate_summary([
        {"metrics": {"pdf_locator_valid_ratio": {
            "value": 1.0, "reason": None}}},
        {"metrics": {"pdf_locator_valid_ratio": {
            "value": 0.0, "reason": None}}}])
    assert s["ratio_macro_averages"]["pdf_locator_valid_ratio"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- 依赖键序 ----------

def test_dependency_versions_key_order_batch55():
    v = get_dependency_versions()
    assert list(v.keys()) == ["pdfplumber", "python-docx",
                              "pypdfium2"]


# ---------- is True 严格性 ----------

def test_success_strict_is_true_batch55():
    s = aggregate_summary([
        {"metrics": {"pipeline_success": {"value": True,
                                          "reason": None}}},
        {"metrics": {"pipeline_success": {"value": 1,
                                          "reason": None}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


# ---------- counts 零参与 ----------

def test_counts_zero_participates_batch55():
    s = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 0,
                                             "reason": None}}}])
    assert s["counts"]["element_count_total"] == {
        "sum": 0, "participating_docs": 1}


# ---------- silent 0 vs None ----------

def test_silent_zero_sum_not_none_batch55():
    s = aggregate_summary([
        {"metrics": {"silent_drop_count": {"value": 0,
                                           "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 0,
                                           "reason": None}}}])
    assert s["silent_drop_total"] == 0


def test_silent_all_none_is_none_batch55():
    s = aggregate_summary([
        {"metrics": {"silent_drop_count": {"value": None,
                                           "reason": "x"}}}])
    assert s["silent_drop_total"] is None


# ---------- 0.0 与缺键混排 ----------

def test_ratio_zero_missing_mix_batch55():
    s = aggregate_summary([
        {"metrics": {"heading_boundary_compliance": {
            "value": 0.0, "reason": None}}},
        {"metrics": {}}])
    assert s["ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 1}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "if r[\"metrics\"].get(name, {}).get(\"value\") is not None" in src
    assert "macro = sum(values) / len(values)" in src


# ---------- forbidden tokens 第二百九十三批 ----------

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
