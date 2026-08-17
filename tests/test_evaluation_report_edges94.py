"""evaluation/report.py 第三百一十六轮 edges 测试（Round 872）。

补强 edges93 未触及的角度（第二百四十七批）。

新角度：
- counts 值 False：非 None 即参与（sum 3、participating 2）
- ratio 值为字符串 "0.5"：参与进 values → sum TypeError
  （现状锁定）
- get_dependency_versions：importlib.metadata.version 抛
  PackageNotFoundError → 三包全 None（patch stdlib）
- get_git_provenance：subprocess 抛 TimeoutExpired
  （SubprocessError 子类）→ 异常分支 commit None +
  dirty True
- forbidden tokens 第三百四十二批
"""

from __future__ import annotations

import inspect
import subprocess
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    get_dependency_versions,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


# ---------- counts 值 False ----------

def test_counts_false_value_participates_batch70():
    s = aggregate_summary([
        _pd({"element_count_total": {"value": False}}),
        _pd({"element_count_total": {"value": 3}})])
    assert s["counts"]["element_count_total"] == {
        "sum": 3, "participating_docs": 2}


# ---------- ratio 字符串值 ----------

def test_ratio_string_value_typeerror_batch70():
    try:
        aggregate_summary([
            _pd({"schema_valid": {"value": "0.5"}}),
            _pd({"schema_valid": {"value": 1.0}})])
        raise AssertionError("no error")
    except TypeError:
        pass


# ---------- 依赖缺失 ----------

def test_dependency_versions_not_found_batch70():
    with patch("importlib.metadata.version",
               side_effect=PackageNotFoundError("x")):
        out = get_dependency_versions()
    assert out == {"pdfplumber": None,
                   "python-docx": None,
                   "pypdfium2": None}


# ---------- git 超时 ----------

def test_git_provenance_timeout_batch70(tmp_path):
    with patch.object(report_mod.subprocess, "run",
                      side_effect=subprocess.TimeoutExpired(
                          "git", 10)):
        out = get_git_provenance(tmp_path)
    assert out == {"git_commit": None, "git_dirty": True}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch70():
    src = _src()
    assert "except (OSError, subprocess.SubprocessError):" in src
    assert "except importlib.metadata.PackageNotFoundError:" in src
    assert "counts[name] = {" in src


# ---------- forbidden tokens 第三百四十二批 ----------

def test_source_no_eval_batch70():
    assert "eval(" not in _src()


def test_source_no_exec_batch70():
    assert "exec(" not in _src()


def test_source_no_compile_batch70():
    assert "compile(" not in _src()


def test_source_no_globals_batch70():
    assert "globals(" not in _src()


def test_source_no_locals_batch70():
    assert "locals(" not in _src()


def test_source_no_os_system_batch70():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch70():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch70():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch70():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch70():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch70():
    assert "socket" not in _src()


def test_source_no_requests_batch70():
    assert "requests" not in _src()


def test_source_no_urllib_batch70():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch70():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch70():
    assert "yield" not in _src()


def test_source_no_async_await_batch70():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch70():
    assert "open(" not in _src()
