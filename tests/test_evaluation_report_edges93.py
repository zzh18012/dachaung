"""evaluation/report.py 第三百零九轮 edges 测试（Round 865）。

补强 edges92 未触及的角度（第二百四十批）。

新角度：
- 跟踪文件被修改（非 untracked）→ porcelain " M" → dirty True
- 空清单 → build_devset_section 全零 + 空 categories
- pipeline_success 值 None（pipeline_failed 文档）计入 total
  但不计入 success_count
- counts [3,4] → sum 7、participating 2；ratio [1.0,0.5,0.0]
  → macro 0.5；silent [2,None,3] → 5
- EVALUATOR_VERSION / REPORT_VERSION 锁定 "1.1"
- build_provenance max_chars 传 bool True → int() → 1
- forbidden tokens 第三百三十五批
"""

from __future__ import annotations

import inspect
import subprocess
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


def _mk_repo_with_tracked(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "t.txt"
    tracked.write_text("v1", encoding="utf-8")
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"],
                ["git", "add", "t.txt"],
                ["git", "commit", "-q", "-m", "x"]):
        subprocess.run(cmd, cwd=repo, check=True,
                       capture_output=True)
    return repo, tracked


# ---------- 跟踪文件修改 → dirty ----------

def test_git_modified_tracked_file_dirty_batch63(tmp_path):
    repo, tracked = _mk_repo_with_tracked(tmp_path)
    assert get_git_provenance(repo)["git_dirty"] is False
    tracked.write_text("v2", encoding="utf-8")
    out = get_git_provenance(repo)
    assert out["git_dirty"] is True
    assert out["git_commit"] is not None


# ---------- 空清单 devset ----------

def test_devset_section_empty_manifest_batch63(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    f = tmp_path / "m.json"
    f.write_text('{"manifest_version": "1.0", '
                 '"devset_status": "incomplete", '
                 '"documents": []}', encoding="utf-8")
    m = load_manifest(f, root)
    assert build_devset_section(m) == {
        "status": "incomplete", "file_count": 0,
        "content_group_count": 0, "pdf_count": 0,
        "docx_count": 0, "categories_covered": []}


# ---------- pipeline_failed 文档计入 total ----------

def test_success_none_value_counts_in_total_batch63():
    s = aggregate_summary([
        _pd({"pipeline_success": {"value": True}}),
        _pd({"pipeline_success": {"value": None,
                                   "reason": "pipeline_failed"}})])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 1, "total": 2, "rate": 0.5}


# ---------- 多值聚合 ----------

def test_counts_two_docs_sum_batch63():
    s = aggregate_summary([
        _pd({"element_count_total": {"value": 3}}),
        _pd({"element_count_total": {"value": 4}})])
    assert s["counts"]["element_count_total"] == {
        "sum": 7, "participating_docs": 2}


def test_ratio_three_values_macro_half_batch63():
    s = aggregate_summary([
        _pd({"schema_valid": {"value": 1.0}}),
        _pd({"schema_valid": {"value": 0.5}}),
        _pd({"schema_valid": {"value": 0.0}})])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.5, "participating_docs": 3,
        "not_evaluated": 0}


def test_silent_drop_mixed_values_batch63():
    s = aggregate_summary([
        _pd({"silent_drop_count": {"value": 2}}),
        _pd({"silent_drop_count": {"value": None}}),
        _pd({"silent_drop_count": {"value": 3}})])
    assert s["silent_drop_total"] == 5


# ---------- 版本常量锁定 ----------

def test_versions_locked_one_one_batch63():
    assert report_mod.EVALUATOR_VERSION == "1.1"
    assert report_mod.REPORT_VERSION == "1.1"


# ---------- max_chars bool ----------

def test_build_provenance_max_chars_bool_batch63(tmp_path):
    with patch.object(report_mod, "get_git_provenance",
                      return_value={"git_commit": "c",
                                    "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      return_value={}):
        p = build_provenance(tmp_path, "p", True, "1")
    assert p["max_chars"] == 1
    assert p["parser_version"] == "1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch63():
    src = _src()
    assert "macro = sum(values) / len(values)" in src
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert '"max_chars": int(max_chars)' in src


# ---------- forbidden tokens 第三百三十五批 ----------

def test_source_no_eval_batch63():
    assert "eval(" not in _src()


def test_source_no_exec_batch63():
    assert "exec(" not in _src()


def test_source_no_compile_batch63():
    assert "compile(" not in _src()


def test_source_no_globals_batch63():
    assert "globals(" not in _src()


def test_source_no_locals_batch63():
    assert "locals(" not in _src()


def test_source_no_os_system_batch63():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch63():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch63():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch63():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch63():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch63():
    assert "socket" not in _src()


def test_source_no_requests_batch63():
    assert "requests" not in _src()


def test_source_no_urllib_batch63():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch63():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch63():
    assert "yield" not in _src()


def test_source_no_async_await_batch63():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch63():
    assert "open(" not in _src()
