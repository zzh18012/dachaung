"""evaluation/report.py 第三百七十二轮 edges 测试（Round 928）。

补强 edges101 未触及的角度（第三百零四批，probe 实证）。

新角度：
- git 命令 TimeoutExpired → except (OSError, SubprocessError)
  → {None, True}（dirty 保持起始默认 True）
- aggregate_summary 遇缺 "metrics" 键的行 → KeyError 直接
  冒出（不做 .get 兜底）
- ratio 混合 [0.0, 1.0, None, 0.5] → macro 0.5、
  participating 3、not_evaluated 1
- summary 顶层四键序 [counts, success_rates,
  ratio_macro_averages, silent_drop_total]
- build_provenance 的 dependencies 透传（get_dependency_
  versions 返回什么就放什么）
- __all__ 五项有序
- 分组成员互斥：schema_valid 仅在 _RATIO_METRICS、
  pipeline_success 仅在 _SUCCESS_BOOL_METRICS
- forbidden tokens 第三百九十八批（subprocess.run 恰 2 次）
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

import pytest

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_git_provenance,
)


def _cp(rc, out):
    return CompletedProcess(args=[], returncode=rc, stdout=out,
                            stderr="")


# ---------- git 超时 ----------

def test_git_timeout_defaults_batch126():
    with patch("subprocess.run",
               side_effect=TimeoutExpired("git", 10)):
        out = get_git_provenance(Path("."))
    assert out == {"git_commit": None, "git_dirty": True}


# ---------- 缺 metrics 键 ----------

def test_missing_metrics_key_raises_batch126():
    with pytest.raises(KeyError) as ei:
        aggregate_summary([{"doc_id": "x"}])
    assert ei.value.args[0] == "metrics"


# ---------- ratio 混合 ----------

def test_ratio_mixed_macro_batch126():
    s = aggregate_summary([
        {"metrics": {"schema_valid": {"value": 0.0}}},
        {"metrics": {"schema_valid": {"value": 1.0}}},
        {"metrics": {"schema_valid": {"value": None}}},
        {"metrics": {"schema_valid": {"value": 0.5}}},
    ])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 3,
        "not_evaluated": 1}


def test_summary_top_key_order_batch126():
    s = aggregate_summary([])
    assert list(s) == ["counts", "success_rates",
                       "ratio_macro_averages",
                       "silent_drop_total"]


# ---------- dependencies 透传 ----------

def test_provenance_dependencies_passthrough_batch126():
    with patch("subprocess.run",
               side_effect=[_cp(0, "c\n"), _cp(0, "")]), \
         patch("evaluation.report.get_dependency_versions",
               return_value={"k": "v"}):
        p = build_provenance(Path("."), "fallback", 800, "1.0")
    assert p["dependencies"] == {"k": "v"}


# ---------- __all__ 与分组互斥 ----------

def test_all_five_ordered_batch126():
    assert report_mod.__all__ == [
        "build_provenance", "build_devset_section",
        "aggregate_summary", "get_git_provenance",
        "get_dependency_versions",
    ]


def test_metric_group_membership_exclusive_batch126():
    assert "schema_valid" in report_mod._RATIO_METRICS
    assert "schema_valid" not in report_mod._SUCCESS_BOOL_METRICS
    assert "pipeline_success" in report_mod._SUCCESS_BOOL_METRICS
    assert "pipeline_success" not in report_mod._RATIO_METRICS
    assert report_mod._RATIO_METRICS[0] == "schema_valid"
    assert report_mod._COUNT_METRICS == ("element_count_total",)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch126():
    src = _src()
    assert "except (OSError, subprocess.SubprocessError):" in src
    assert "import subprocess" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) ' \
        "if silent_vals else None" in src


# ---------- forbidden tokens 第三百九十八批 ----------

def test_source_no_eval_batch126():
    assert "eval(" not in _src()


def test_source_no_exec_batch126():
    assert "exec(" not in _src()


def test_source_no_compile_batch126():
    assert "compile(" not in _src()


def test_source_no_globals_batch126():
    assert "globals(" not in _src()


def test_source_no_locals_batch126():
    assert "locals(" not in _src()


def test_source_no_os_system_batch126():
    assert "os.system" not in _src()


def test_source_no_subprocess_run_count_batch126():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch126():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch126():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch126():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch126():
    assert "socket" not in _src()


def test_source_no_requests_batch126():
    assert "requests" not in _src()


def test_source_no_urllib_batch126():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch126():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch126():
    assert "yield" not in _src()


def test_source_no_async_await_batch126():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch126():
    assert "open(" not in _src()
