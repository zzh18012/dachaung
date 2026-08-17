"""evaluation/report.py 第三百五十八轮 edges 测试（Round 914）。

补强 edges99 未触及的角度（第二百九十批，probe 实证）。

新角度：
- get_git_provenance 三态：r1 rc0+r2 rc0 dirty → {commit, True}；
  r2 rc1 即便 stdout 非空 → dirty False（returncode 主导）；
  r1 rc0 但 stdout 全空白 → commit None（"or None" 再证）
- get_dependency_versions 双异常路径：PackageNotFoundError 与
  通用 Exception 都归 None，第三包正常返回 9.9
- aggregate_summary：rows 完全缺 element_count_total 键 →
  .get(name, {}).get("value") 链安全过滤，sum 4 / participating 1
- ratio 值 0.0 参与聚合（falsy 陷阱）：macro 0.0、participating 1、
  not_evaluated 3
- silent_drop_total [2, None, 3] → 5（null 行过滤）
- EVALUATOR_VERSION / REPORT_VERSION 常量双双 "1.1"（锁死不变量）
- ratio 聚合键完整 12 项有序
- forbidden tokens 第三百八十四批（subprocess.run 恰 2 次）
"""

from __future__ import annotations

import importlib.metadata
import inspect
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.report import (
    aggregate_summary,
    get_dependency_versions,
    get_git_provenance,
)


def _cp(rc, out):
    return CompletedProcess(args=[], returncode=rc, stdout=out,
                            stderr="")


# ---------- git 三态 ----------

def test_git_commit_and_dirty_true_batch112():
    with patch("subprocess.run",
               side_effect=[_cp(0, "abc123\n"), _cp(0, " M x\n")]):
        out = get_git_provenance(Path("."))
    assert out == {"git_commit": "abc123", "git_dirty": True}


def test_git_r2_rc1_forces_not_dirty_batch112():
    with patch("subprocess.run",
               side_effect=[_cp(0, "abc\n"), _cp(1, " M x\n")]):
        out = get_git_provenance(Path("."))
    assert out == {"git_commit": "abc", "git_dirty": False}


def test_git_whitespace_commit_none_batch112():
    with patch("subprocess.run",
               side_effect=[_cp(0, "   \n"), _cp(0, "")]):
        out = get_git_provenance(Path("."))
    assert out == {"git_commit": None, "git_dirty": False}


# ---------- dependency versions 异常路径 ----------

def test_dependency_versions_exception_paths_batch112():
    def fake_version(pkg):
        if pkg == "pdfplumber":
            raise importlib.metadata.PackageNotFoundError("pdfplumber")
        if pkg == "python-docx":
            raise RuntimeError("boom")
        return "9.9"

    with patch.object(importlib.metadata, "version",
                      side_effect=fake_version):
        out = get_dependency_versions()
    assert out == {"pdfplumber": None, "python-docx": None,
                   "pypdfium2": "9.9"}
    assert list(out) == ["pdfplumber", "python-docx", "pypdfium2"]


# ---------- aggregate：缺键安全 + 零值参与 ----------

_ROWS = [
    {"metrics": {"pipeline_success": {"value": False}}},
    {"metrics": {"element_count_total": {"value": None},
                 "schema_valid": {"value": 0.0}}},
    {"metrics": {"element_count_total": {"value": 4},
                 "schema_valid": {"value": None},
                 "silent_drop_count": {"value": 2}}},
    {"metrics": {"silent_drop_count": {"value": 3}}},
]


def test_aggregate_missing_key_safe_batch112():
    s = aggregate_summary(_ROWS)
    assert s["counts"] == {"element_count_total": {
        "sum": 4, "participating_docs": 1}}


def test_aggregate_zero_value_participates_batch112():
    s = aggregate_summary(_ROWS)
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 3}


def test_aggregate_silent_drop_mixed_batch112():
    s = aggregate_summary(_ROWS)
    assert s["silent_drop_total"] == 5


def test_aggregate_success_zero_of_four_batch112():
    s = aggregate_summary(_ROWS)
    assert s["success_rates"] == {"pipeline_success": {
        "success_count": 0, "total": 4, "rate": 0.0}}


def test_aggregate_ratio_keys_twelve_ordered_batch112():
    s = aggregate_summary(_ROWS)
    assert list(s["ratio_macro_averages"]) == [
        "schema_valid", "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio", "image_resource_exists_ratio",
        "chunk_reference_intact_ratio", "text_preservation_equal",
        "text_char_multiset_precision", "text_char_multiset_recall",
        "heading_boundary_compliance", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_boundary_f1",
    ]


# ---------- 版本常量锁死 ----------

def test_version_constants_locked_batch112():
    assert EVALUATOR_VERSION == "1.1"
    assert REPORT_VERSION == "1.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch112():
    src = _src()
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert "rate = (successes / total) if total else None" in src
    assert ('summary["silent_drop_total"] = sum(silent_vals) '
            "if silent_vals else None") in src
    assert "macro = sum(values) / len(values)" in src


def test_ratio_metrics_tuple_full_order_batch112():
    assert report_mod._RATIO_METRICS == (
        "schema_valid", "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio", "image_resource_exists_ratio",
        "chunk_reference_intact_ratio", "text_preservation_equal",
        "text_char_multiset_precision", "text_char_multiset_recall",
        "heading_boundary_compliance", "chunk_boundary_precision",
        "chunk_boundary_recall", "chunk_boundary_f1",
    )


# ---------- forbidden tokens 第三百八十四批 ----------

def test_source_no_eval_batch112():
    assert "eval(" not in _src()


def test_source_no_exec_batch112():
    assert "exec(" not in _src()


def test_source_no_compile_batch112():
    assert "compile(" not in _src()


def test_source_no_globals_batch112():
    assert "globals(" not in _src()


def test_source_no_locals_batch112():
    assert "locals(" not in _src()


def test_source_no_os_system_batch112():
    assert "os.system" not in _src()


def test_source_no_subprocess_run_count_batch112():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch112():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch112():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch112():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch112():
    assert "socket" not in _src()


def test_source_no_requests_batch112():
    assert "requests" not in _src()


def test_source_no_urllib_batch112():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch112():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch112():
    assert "yield" not in _src()


def test_source_no_async_await_batch112():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch112():
    assert "open(" not in _src()
