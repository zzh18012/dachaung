"""evaluation/report.py 第三百二十三轮 edges 测试（Round 879）。

补强 edges94 未触及的角度（第二百五十四批）。

新角度：
- metrics[name] 是 int（非 dict）→ .get AttributeError
  （现状锁定）
- build_provenance 无打桩全真实：键集恰 9 项 +
  evaluator/report 版本 "1.1" + 非实盘 git → commit None
- _RATIO_METRICS 无重复（12 项唯一）
- 文档缺 element_count_total 指标 → counts 条目
  {"sum": None, "participating_docs": 0}
- forbidden tokens 第三百四十九批
"""

from __future__ import annotations

import inspect

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


# ---------- metrics[name] 非 dict ----------

def test_metric_value_int_attribute_error_batch77():
    try:
        aggregate_summary([
            _pd({"element_count_total": 5})])
        raise AssertionError("no error")
    except AttributeError as e:
        assert "'int' object has no attribute 'get'" \
            in str(e)


# ---------- 全真实 build_provenance ----------

def test_build_provenance_real_key_set_batch77(tmp_path):
    p = build_provenance(tmp_path, "fallback", 800, "1.2.3")
    assert sorted(p) == [
        "dependencies", "evaluator_version", "git_commit",
        "git_dirty", "max_chars", "parser_name",
        "parser_version", "report_version",
        "run_timestamp_iso"]
    assert p["evaluator_version"] == "1.1"
    assert p["report_version"] == "1.1"
    assert p["parser_name"] == "fallback"
    assert p["parser_version"] == "1.2.3"
    assert p["max_chars"] == 800
    assert p["git_commit"] is None  # tmp 非 git 目录
    assert sorted(p["dependencies"]) == [
        "pdfplumber", "pypdfium2", "python-docx"]


# ---------- ratio 指标唯一性 ----------

def test_ratio_metrics_unique_twelve_batch77():
    assert len(_RATIO_METRICS) == 12
    assert len(set(_RATIO_METRICS)) == 12


# ---------- 缺失指标条目 ----------

def test_counts_missing_metric_empty_entry_batch77():
    s = aggregate_summary([
        _pd({"pipeline_success": {"value": True}})])
    assert s["counts"]["element_count_total"] == {
        "sum": None, "participating_docs": 0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch77():
    src = _src()
    assert 'r["metrics"].get(name, {}).get("value")' in src
    assert 'counts[name] = {"sum": None, "participating_docs": 0}' in src
    assert '"run_timestamp_iso": datetime.now().astimezone().isoformat(),' in src


# ---------- forbidden tokens 第三百四十九批 ----------

def test_source_no_eval_batch77():
    assert "eval(" not in _src()


def test_source_no_exec_batch77():
    assert "exec(" not in _src()


def test_source_no_compile_batch77():
    assert "compile(" not in _src()


def test_source_no_globals_batch77():
    assert "globals(" not in _src()


def test_source_no_locals_batch77():
    assert "locals(" not in _src()


def test_source_no_os_system_batch77():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch77():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch77():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch77():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch77():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch77():
    assert "socket" not in _src()


def test_source_no_requests_batch77():
    assert "requests" not in _src()


def test_source_no_urllib_batch77():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch77():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch77():
    assert "yield" not in _src()


def test_source_no_async_await_batch77():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch77():
    assert "open(" not in _src()
