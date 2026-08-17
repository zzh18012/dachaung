"""evaluation/report.py 第五百六十轮 edges 测试（Round 1116）。

补强 edges128 未触及的角度（第四百九十二批，probe 实证）。

新角度（reason 通道聚合全忽略 / metrics-only 条目）：
- **reason 通道聚合全忽略**：value True 带 reason "whatever"
  → success {1, 1, 1.0}；ect 4 带 reason "noise" → counts
  {4, 1}；ratio 0.25 带 reason → macro 0.25——三家族只读
  value，reason 聚合层完全丢弃（True-with-reason 首锁，
  旧锁只测过 reason None 正形）
- **metrics-only 条目**：per_doc 条目只有 metrics 键（无
  doc_id / wall_time_seconds）→ 聚合照常——aggregate 只
  读 r["metrics"]，条目壳不设防（metrics-only 首锁）
- forbidden tokens 第五百八十八批（open 0，报告变体
  15 条 + subprocess.run 计数 2）
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import aggregate_summary


# ---------- reason 通道聚合全忽略 ----------

def test_reason_channel_ignored_batch315():
    s = aggregate_summary([{"doc_id": "a", "metrics": {
        "pipeline_success": {
            "value": True, "reason": "whatever"},
        "element_count_total": {
            "value": 4, "reason": "noise"},
        "docx_locator_valid_ratio": {
            "value": 0.25, "reason": "noise"}}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 1, "rate": 1.0}
    assert s["counts"]["element_count_total"] == {
        "sum": 4, "participating_docs": 1}
    assert s["ratio_macro_averages"][
        "docx_locator_valid_ratio"] == {
        "macro_average": 0.25, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- metrics-only 条目 ----------

def test_metrics_only_entries_batch315():
    s = aggregate_summary([{"metrics": {
        "element_count_total": {
            "value": 4, "reason": None},
        "docx_locator_valid_ratio": {
            "value": 0.25, "reason": None}}}])
    assert s["counts"]["element_count_total"] == {
        "sum": 4, "participating_docs": 1}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 1, "rate": 0.0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch315():
    src = _src()
    assert "聚合所有 per_doc" in src
    assert "# ratio macro averages" in src


# ---------- forbidden tokens 第五百八十八批（报告变体） ----------

def test_source_no_eval_batch315():
    assert "eval(" not in _src()


def test_source_no_exec_batch315():
    assert "exec(" not in _src()


def test_source_no_compile_batch315():
    assert "compile(" not in _src()


def test_source_no_globals_batch315():
    assert "globals(" not in _src()


def test_source_no_locals_batch315():
    assert "locals(" not in _src()


def test_source_no_os_system_batch315():
    assert "os.system" not in _src()


def test_source_no_popen_batch315():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch315():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch315():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch315():
    assert "socket" not in _src()


def test_source_no_requests_batch315():
    assert "requests" not in _src()


def test_source_no_urllib_batch315():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch315():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch315():
    assert "yield" not in _src()


def test_source_no_async_await_batch315():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch315():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch315():
    assert _src().count("subprocess.run") == 2
