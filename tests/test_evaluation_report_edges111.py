"""evaluation/report.py 第四百三十五轮 edges 测试（Round 991）。

补强 edges110 未触及的角度（第三百六十七批，probe 实证）。

新角度：
- per_doc 条目缺 "metrics" 键 → r["metrics"] 直取 →
  KeyError 'metrics'（.get 只在 metrics 内部用，外层裸取）
- importlib.metadata.version 抛通用 Exception → 三包全
  None（except Exception 兜底分支，与 PackageNotFoundError
  分支分开）
- 3 文档 1 成功 → rate 精确 0.3333333333333333 == 1/3
- ratio_macro_averages 输出键序 == _RATIO_METRICS 元组序
  （首 schema_valid 尾 chunk_boundary_f1）
- forbidden tokens 第四百六十一批（open 0 + subprocess.run
  恰 2）
"""

from __future__ import annotations

import importlib.metadata
import inspect
from unittest.mock import patch

import pytest

import evaluation.report as rpt
from evaluation.report import aggregate_summary, get_dependency_versions


# ---------- 缺 metrics 键崩溃 ----------

def test_missing_metrics_key_crashes_batch189():
    with pytest.raises(KeyError) as ei:
        aggregate_summary([{"doc_id": "d"}])
    assert ei.value.args[0] == "metrics"


# ---------- 通用异常兜底 ----------

def test_dep_version_generic_exception_none_batch189():
    def boom(pkg):
        raise RuntimeError("nope")

    with patch.object(importlib.metadata, "version", boom):
        d = get_dependency_versions()
    assert d == {"pdfplumber": None, "python-docx": None,
                 "pypdfium2": None}


# ---------- 1/3 成功率 ----------

def test_success_rate_third_batch189():
    doc = lambda v: {"metrics": {"pipeline_success": {
        "value": v, "reason": None}}}  # noqa: E731
    s = aggregate_summary([doc(True), doc(False), doc(False)])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 3,
        "rate": 0.3333333333333333}
    assert s["success_rates"]["pipeline_success"]["rate"] == 1 / 3


# ---------- ratio 键序 ----------

def test_ratio_key_order_matches_tuple_batch189():
    s = aggregate_summary([])
    keys = list(s["ratio_macro_averages"])
    assert keys == list(rpt._RATIO_METRICS)
    assert keys[0] == "schema_valid"
    assert keys[-1] == "chunk_boundary_f1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch189():
    src = _src()
    assert src.count(
        'r["metrics"].get(name, {}).get("value")') == 5
    assert "except importlib.metadata.PackageNotFoundError:" in src
    assert '"rate": rate,' in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


# ---------- forbidden tokens 第四百六十一批 ----------

def test_source_no_eval_batch189():
    assert "eval(" not in _src()


def test_source_no_exec_batch189():
    assert "exec(" not in _src()


def test_source_no_compile_batch189():
    assert "compile(" not in _src()


def test_source_no_globals_batch189():
    assert "globals(" not in _src()


def test_source_no_locals_batch189():
    assert "locals(" not in _src()


def test_source_no_os_system_batch189():
    assert "os.system" not in _src()


def test_source_no_popen_batch189():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch189():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch189():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch189():
    assert "socket" not in _src()


def test_source_no_requests_batch189():
    assert "requests" not in _src()


def test_source_no_urllib_batch189():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch189():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch189():
    assert "yield" not in _src()


def test_source_no_async_await_batch189():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch189():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch189():
    assert _src().count("subprocess.run") == 2
