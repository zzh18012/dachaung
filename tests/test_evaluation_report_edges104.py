"""evaluation/report.py 第三百八十六轮 edges 测试（Round 942）。

补强 edges103 未触及的角度（第三百一十八批，probe 实证）。

新角度：
- 空 metrics 行语义：缺 pipeline_success 键 → .get 链兜底
  不计成功但仍进分母 → {success_count: 0, total: 1,
  rate: 0.0}；counts {None, 0}；每个 ratio
  {None, 0, not_evaluated: 1}；silent None
- 未知指标键被忽略：custom_metric 不进 ratio_macro_
  averages（只迭代固定元组）
- ratio 值用 int [1, 0] → macro 0.5（不强制 float 输入）
- aggregate_summary 不改动入参行（纯读）
- _COUNT_METRICS / _SUCCESS_BOOL_METRICS 恰各 1 项
- 真实仓库 get_git_provenance：git_commit 40 位十六
  制 str、git_dirty bool、返回恰 2 键
- forbidden tokens 第四百一十二批（subprocess.run 恰 2）
"""

from __future__ import annotations

import inspect
from pathlib import Path

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    get_git_provenance,
)


# ---------- 空 metrics 行语义 ----------

def test_empty_metrics_row_semantics_batch140():
    s = aggregate_summary([{"metrics": {}}])
    # 缺 pipeline_success 键：不计成功但仍占分母
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}
    assert s["counts"] == {"element_count_total": {
        "sum": None, "participating_docs": 0}}
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 1}
    assert s["silent_drop_total"] is None


# ---------- 未知指标忽略 ----------

def test_unknown_metric_ignored_batch140():
    s = aggregate_summary([
        {"metrics": {"custom_metric": {"value": 1.0},
                     "schema_valid": {"value": 1.0}}}])
    assert "custom_metric" not in s["ratio_macro_averages"]
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 1.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- int 值入算 ----------

def test_int_ratio_values_batch140():
    s = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 1}}},
        {"metrics": {"schema_valid": {"value": 0}}}])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- 不改动入参 ----------

def test_input_rows_not_mutated_batch140():
    rows = [{"metrics": {"element_count_total": {"value": 3},
                         "schema_valid": {"value": 1.0}}}]
    before = repr(rows)
    aggregate_summary(rows)
    assert repr(rows) == before


# ---------- 元组尺寸 ----------

def test_metric_tuple_sizes_batch140():
    assert _COUNT_METRICS == ("element_count_total",)
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)
    assert len(_COUNT_METRICS) == 1
    assert len(_SUCCESS_BOOL_METRICS) == 1


# ---------- 真实仓库 ----------

def test_real_repo_git_provenance_batch140():
    g = get_git_provenance(Path("."))
    assert list(g) == ["git_commit", "git_dirty"]
    assert isinstance(g["git_commit"], str)
    assert len(g["git_commit"]) == 40
    int(g["git_commit"], 16)  # 合法十六进制
    assert isinstance(g["git_dirty"], bool)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch140():
    src = _src()
    assert 'r["metrics"].get(name, {}).get("value")' in src
    assert "if r[\"metrics\"].get(name, {}).get(\"value\") is True" in src
    assert "rate = (successes / total) if total else None" in src
    assert "not_eval = len(per_doc_results) - len(values)" in src


# ---------- forbidden tokens 第四百一十二批 ----------

def test_source_no_eval_batch140():
    assert "eval(" not in _src()


def test_source_no_exec_batch140():
    assert "exec(" not in _src()


def test_source_no_compile_batch140():
    assert "compile(" not in _src()


def test_source_no_globals_batch140():
    assert "globals(" not in _src()


def test_source_no_locals_batch140():
    assert "locals(" not in _src()


def test_source_no_os_system_batch140():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_two_batch140():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch140():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch140():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch140():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch140():
    assert "socket" not in _src()


def test_source_no_requests_batch140():
    assert "requests" not in _src()


def test_source_no_urllib_batch140():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch140():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch140():
    assert "yield" not in _src()


def test_source_no_async_await_batch140():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch140():
    assert "open(" not in _src()
