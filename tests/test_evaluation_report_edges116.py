"""evaluation/report.py 第四百七十轮 edges 测试（Round 1026）。

补强 edges115 未触及的角度（第四百零二批，probe 实证）。

新角度（结构与序）：
- summary 顶层四键插入序精确 [counts, success_rates,
  ratio_macro_averages, silent_drop_total]；12 个 ratio
  键按 _RATIO_METRICS 元组序排列（此前只锁过 set 相等）
- 空输入全量深快照：12 项 ratio 全 {macro None,
  participating 0, not_evaluated 0}、counts 双 None/0、
  success 0/0/None、silent None——一次 dict == 全锁
- forbidden tokens 第四百九十六批（open 0 + subprocess.run
  恰 2；subprocess 是本模块合法依赖不列禁词）
"""

from __future__ import annotations

import inspect
from pathlib import Path

import evaluation.report as rpt
from evaluation.report import aggregate_summary

_RATIO_ORDER = (
    "schema_valid", "pdf_locator_valid_ratio",
    "docx_locator_valid_ratio",
    "image_resource_exists_ratio",
    "chunk_reference_intact_ratio",
    "text_preservation_equal",
    "text_char_multiset_precision",
    "text_char_multiset_recall",
    "heading_boundary_compliance",
    "chunk_boundary_precision", "chunk_boundary_recall",
    "chunk_boundary_f1")


# ---------- 插入序 ----------

def test_summary_key_insertion_order_batch224():
    s = aggregate_summary([])
    assert list(s.keys()) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]
    assert list(s["ratio_macro_averages"].keys()) == \
        list(_RATIO_ORDER)


# ---------- 空输入全量深快照 ----------

def test_empty_aggregate_full_snapshot_batch224():
    s = aggregate_summary([])
    assert s == {
        "counts": {"element_count_total": {
            "sum": None, "participating_docs": 0}},
        "success_rates": {"pipeline_success": {
            "success_count": 0, "total": 0, "rate": None}},
        "ratio_macro_averages": {
            n: {"macro_average": None,
                "participating_docs": 0,
                "not_evaluated": 0}
            for n in _RATIO_ORDER},
        "silent_drop_total": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch224():
    src = _src()
    assert 'summary["counts"] = counts' in src
    assert 'summary["success_rates"] = success_rates' in src
    assert ("summary[\"silent_drop_total\"] ="
            " sum(silent_vals) if silent_vals else None") in src


# ---------- forbidden tokens 第四百九十六批 ----------

def test_source_no_eval_batch224():
    assert "eval(" not in _src()


def test_source_no_exec_batch224():
    assert "exec(" not in _src()


def test_source_no_compile_batch224():
    assert "compile(" not in _src()


def test_source_no_globals_batch224():
    assert "globals(" not in _src()


def test_source_no_locals_batch224():
    assert "locals(" not in _src()


def test_source_no_os_system_batch224():
    assert "os.system" not in _src()


def test_source_no_popen_batch224():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch224():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch224():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch224():
    assert "socket" not in _src()


def test_source_no_requests_batch224():
    assert "requests" not in _src()


def test_source_no_urllib_batch224():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch224():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch224():
    assert "yield" not in _src()


def test_source_no_async_await_batch224():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch224():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch224():
    assert _src().count("subprocess.run") == 2
