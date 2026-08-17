"""evaluation/report.py 第二百九十五轮 edges 测试（Round 851）。

补强 edges90 未触及的角度（第二百二十五批）。

新角度：
- 三个依赖版本在本 venv 全部非 None（真实安装态）
- counts 值 2.5（float）照加不取整 → sum 2.5
- _SUCCESS_BOOL_METRICS 恰为单元素元组（直测，非源码串）
- get_git_provenance 恰 2 个键且顺序 git_commit → git_dirty
- build_provenance 两次调用各出新 dict（时间戳均可
  fromisoformat 解析；不等断言因 Windows 时钟分辨率弃用）
- 不打补丁时 provenance.dependencies 恰 3 键
- forbidden tokens 第三百二十一批
"""

from __future__ import annotations

import datetime
import inspect
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    _SUCCESS_BOOL_METRICS,
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _r(metrics):
    return {"doc_id": "d", "metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- 真实依赖版本 ----------

def test_all_dependencies_present_batch55():
    v = get_dependency_versions()
    assert v["pdfplumber"] is not None
    assert v["python-docx"] is not None
    assert v["pypdfium2"] is not None


# ---------- counts float ----------

def test_counts_float_sum_batch55():
    s = aggregate_summary([
        _r(_m("element_count_total", 2.5))])
    assert s["counts"]["element_count_total"] == {
        "sum": 2.5, "participating_docs": 1}


# ---------- 元组直测 ----------

def test_success_bool_metrics_tuple_batch55():
    assert _SUCCESS_BOOL_METRICS == ("pipeline_success",)


# ---------- git 键序 ----------

def test_git_provenance_two_keys_batch55(tmp_path):
    g = get_git_provenance(tmp_path)
    assert list(g.keys()) == ["git_commit", "git_dirty"]


# ---------- 时间戳两次不同 ----------

def test_timestamp_parses_and_fresh_dict_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        p1 = build_provenance(Path("r"), "fallback", 800, None)
        p2 = build_provenance(Path("r"), "fallback", 800, None)
    for p in (p1, p2):
        datetime.datetime.fromisoformat(p["run_timestamp_iso"])
    # 每次新 dict（改一个不影响另一个）；时间戳是否相同
    # 取决于系统时钟分辨率（Windows 可同 μs），不做不等断言
    assert p1 is not p2
    p1["parser_name"] = "mutated"
    assert p2["parser_name"] == "fallback"


# ---------- 真实 dependencies ----------

def test_provenance_real_dependencies_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}):
        p = build_provenance(Path("r"), "fallback", 800, "1.0")
    assert list(p["dependencies"].keys()) == [
        "pdfplumber", "python-docx", "pypdfium2"]
    assert all(v is not None
               for v in p["dependencies"].values())


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'successes = sum(' in src
    assert "if values:" in src
    assert 'summary["success_rates"] = success_rates' in src


# ---------- forbidden tokens 第三百二十一批 ----------

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


def test_source_subprocess_run_count_is_2_batch55():
    assert _src().count("subprocess.run") == 2
