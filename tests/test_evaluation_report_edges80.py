"""evaluation/report.py 第二百一十八轮 edges 测试（Round 774）。

补强 edges77-79 未触及的角度（第一百三十八批）。

新角度：
- git 双命令 rc!=0（进程成功、git 失败）：dirty = bool(rc==0 and
  stdout) → False —— 与 docstring "失败时 dirty=true" 不符，
  该语义只覆盖异常路径；两命令都 rc 128 → {commit None, dirty False}
- rev-parse rc0 出 commit + porcelain rc128 → commit 保留、
  dirty False
- subprocess.TimeoutExpired（SubprocessError 子类）→ 异常路径
  全默认 {None, True}
- summary 外层键序 4 键固定 [counts, success_rates,
  ratio_macro_averages, silent_drop_total]
- aggregate_summary 接受 tuple 输入（len/迭代不挑类型）
- build_provenance 键序 9 键固定
- get_dependency_versions 的兜底 except Exception → 三包全 None
  （patch importlib.metadata.version 抛 RuntimeError）
- EVALUATOR_VERSION == REPORT_VERSION == "1.1"（锁定不动）
- counts 值 "5"（非 None 非数字）参与 values → sum TypeError
  （未守卫，现状记录）
- forbidden tokens 第二百四十四批（subprocess 用 run 计数 2 替代）
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


class _FakeR:
    def __init__(self, rc, out=""):
        self.returncode = rc
        self.stdout = out


# ---------- git rc 路径 ----------

def test_both_git_commands_fail_dirty_false_batch54():
    with patch.object(report_mod.subprocess, "run",
                      side_effect=[_FakeR(128), _FakeR(128)]):
        assert get_git_provenance(Path(".")) == {
            "git_commit": None, "git_dirty": False}


def test_commit_kept_porcelain_fail_batch54():
    with patch.object(report_mod.subprocess, "run",
                      side_effect=[_FakeR(0, "abc\n"), _FakeR(128)]):
        assert get_git_provenance(Path(".")) == {
            "git_commit": "abc", "git_dirty": False}


def test_timeout_expired_defaults_batch54():
    with patch.object(report_mod.subprocess, "run",
                      side_effect=subprocess.TimeoutExpired("git", 10)):
        assert get_git_provenance(Path(".")) == {
            "git_commit": None, "git_dirty": True}


# ---------- 聚合形态 ----------

def test_summary_outer_key_order_batch54():
    assert list(aggregate_summary([])) == [
        "counts", "success_rates", "ratio_macro_averages",
        "silent_drop_total"]


def test_aggregate_accepts_tuple_input_batch54():
    out = aggregate_summary(({"metrics": {
        "pipeline_success": {"value": True, "reason": None}}},))
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 1, "rate": 1.0}


# ---------- provenance 形态 ----------

def test_build_provenance_key_order_batch54():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}), \
            patch.object(report_mod, "get_dependency_versions",
                         lambda: {}):
        p = build_provenance(Path("."), "fallback", 800, None)
    assert list(p) == ["git_commit", "git_dirty", "evaluator_version",
                       "report_version", "parser_name", "parser_version",
                       "dependencies", "max_chars",
                       "run_timestamp_iso"]


def test_dependency_versions_generic_exception_batch54():
    import importlib.metadata as imd
    with patch.object(imd, "version",
                      side_effect=RuntimeError("boom")):
        dv = get_dependency_versions()
    assert list(dv) == ["pdfplumber", "python-docx", "pypdfium2"]
    assert all(v is None for v in dv.values())


def test_version_constants_locked_batch54():
    assert report_mod.EVALUATOR_VERSION == "1.1"
    assert report_mod.REPORT_VERSION == "1.1"


# ---------- 未守卫 TypeError ----------

def test_counts_string_value_typeerror_batch54():
    with pytest.raises(TypeError):
        aggregate_summary([{"metrics": {
            "element_count_total": {"value": "5", "reason": None}}}])


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_dirty_and_guard_lines_batch54():
    src = _src()
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert "except (OSError, subprocess.SubprocessError):" in src
    assert "except Exception:" in src


# ---------- forbidden tokens 第二百四十四批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_two_batch54():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
