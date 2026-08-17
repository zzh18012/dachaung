"""evaluation/report.py 第三百零二轮 edges 测试（Round 858）。

补强 edges91 未触及的角度（第二百三十三批）。

新角度：
- counts 值为 0 仍参与（values 列表非空即建条目，
  sum=0 + participating_docs=1，0 不是 None）
- success_count 用 `is True` 严格比较：int 1 不算成功
- ratio 值 0.0 参与 macro（participating=1，
  无值文档计入 not_evaluated）
- silent_drop 值 0 → 总和 0；全 None → None
- get_git_provenance 收 str 路径（str(project_root) 包装）
- __all__ 恰 5 项且有序
- forbidden tokens 第三百二十八批（report 变体：
  subprocess.run 计数 == 2 替代 no_subprocess）
"""

from __future__ import annotations

import inspect
import re
import subprocess
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    aggregate_summary,
    build_provenance,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


# ---------- counts 0 值参与 ----------

def test_counts_zero_value_participates_batch56():
    s = aggregate_summary([_pd({"element_count_total":
                                {"value": 0}})])
    assert s["counts"]["element_count_total"] == {
        "sum": 0, "participating_docs": 1}


# ---------- success 严格 True ----------

def test_success_strict_true_int_one_not_counted_batch56():
    s = aggregate_summary([
        _pd({"pipeline_success": {"value": 1}}),
        _pd({"pipeline_success": {"value": True}})])
    sr = s["success_rates"]["pipeline_success"]
    assert sr == {"success_count": 1, "total": 2, "rate": 0.5}


# ---------- ratio 0.0 参与 ----------

def test_ratio_zero_participates_not_evaluated_batch56():
    s = aggregate_summary([
        _pd({"schema_valid": {"value": 0.0}}),
        _pd({})])
    r = s["ratio_macro_averages"]["schema_valid"]
    assert r == {"macro_average": 0.0,
                 "participating_docs": 1,
                 "not_evaluated": 1}


# ---------- silent_drop ----------

def test_silent_drop_zero_value_sums_zero_batch56():
    s = aggregate_summary([_pd({"silent_drop_count":
                                {"value": 0}})])
    assert s["silent_drop_total"] == 0


def test_silent_drop_all_none_is_none_batch56():
    s = aggregate_summary([
        _pd({"silent_drop_count": {"value": None}}),
        _pd({"silent_drop_count": {"reason": "no_exp"}})])
    assert s["silent_drop_total"] is None


# ---------- build_provenance 边界 ----------

def test_build_provenance_none_pv_zero_max_chars_batch56(tmp_path):
    with patch.object(report_mod, "get_git_provenance",
                      return_value={"git_commit": None,
                                    "git_dirty": True}), \
         patch.object(report_mod, "get_dependency_versions",
                      return_value={}):
        p = build_provenance(tmp_path, "fallback", 0, None)
    assert p["parser_version"] is None
    assert p["parser_name"] == "fallback"
    assert p["max_chars"] == 0
    assert p["git_commit"] is None
    assert p["git_dirty"] is True


# ---------- str git root ----------

def test_git_provenance_str_root_batch56(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (["git", "init", "-q"],
                ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"],
                ["git", "commit", "-q", "--allow-empty",
                 "-m", "x"]):
        subprocess.run(cmd, cwd=repo, check=True,
                       capture_output=True)
    out = get_git_provenance(str(repo))
    assert re.fullmatch(r"[0-9a-f]{40}",
                        out["git_commit"])
    assert out["git_dirty"] is False


# ---------- 缺失指标计入 not_evaluated ----------

def test_partial_metrics_not_evaluated_batch56():
    s = aggregate_summary([
        _pd({"schema_valid": {"value": True}}),
        _pd({"schema_valid": {"value": False},
             "chunk_boundary_f1": {"value": 0.5}})])
    sv = s["ratio_macro_averages"]["schema_valid"]
    assert sv["participating_docs"] == 2
    assert sv["macro_average"] == 0.5
    cb = s["ratio_macro_averages"]["chunk_boundary_f1"]
    assert cb == {"macro_average": 0.5,
                  "participating_docs": 1,
                  "not_evaluated": 1}


# ---------- __all__ ----------

def test_all_exports_five_ordered_batch56():
    assert report_mod.__all__ == [
        "build_provenance",
        "build_devset_section",
        "aggregate_summary",
        "get_git_provenance",
        "get_dependency_versions"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch56():
    src = _src()
    assert "rate = (successes / total) if total else None" in src
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


# ---------- forbidden tokens 第三百二十八批 ----------

def test_source_no_eval_batch56():
    assert "eval(" not in _src()


def test_source_no_exec_batch56():
    assert "exec(" not in _src()


def test_source_no_compile_batch56():
    assert "compile(" not in _src()


def test_source_no_globals_batch56():
    assert "globals(" not in _src()


def test_source_no_locals_batch56():
    assert "locals(" not in _src()


def test_source_no_os_system_batch56():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch56():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch56():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch56():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch56():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch56():
    assert "socket" not in _src()


def test_source_no_requests_batch56():
    assert "requests" not in _src()


def test_source_no_urllib_batch56():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch56():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch56():
    assert "yield" not in _src()


def test_source_no_async_await_batch56():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch56():
    assert "open(" not in _src()
