"""evaluation/report.py 第四百二十一轮 edges 测试（Round 977）。

补强 edges108 未触及的角度（第三百五十三批，probe 实证）。

新角度：
- build_provenance 9 键精确有序（第一次整表锁定）；非 git 目录
  commit=None 且 dirty=False（bool(rc==0 and …) 构造缺陷复现）
- 真 git 仓库行为对：干净仓库 commit 40 位 hex + dirty=False；
  新增未跟踪文件 → porcelain 非空 → dirty=True
- silent_drop_count [0, None] → 求和保持 0（int 而非 None）
- aggregate_summary 顶层恰 4 键有序
- schema_valid 分歧：在 _RATIO_METRICS（macro average）但不在
  _SUCCESS_BOOL_METRICS → success_rates 只含 pipeline_success
- forbidden tokens 第四百四十七批（open 0 + subprocess.run 恰 2）
"""

from __future__ import annotations

import inspect
import re
import subprocess
import tempfile
from pathlib import Path

import evaluation.report as rpt
from evaluation.report import aggregate_summary, build_provenance


# ---------- provenance 键序与非 git 怪癖 ----------

def test_provenance_nine_keys_order_batch175():
    tmp = Path(tempfile.mkdtemp())
    p = build_provenance(tmp, "fallback", 800, "1.2.3")
    assert list(p) == [
        "git_commit", "git_dirty", "evaluator_version",
        "report_version", "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso"]
    assert p["git_commit"] is None
    assert p["git_dirty"] is False
    assert p["max_chars"] == 800
    assert isinstance(p["max_chars"], int)


# ---------- 真 git 仓库行为对 ----------

def _mk_repo():
    repo = Path(tempfile.mkdtemp())

    def git(*a):
        return subprocess.run(["git", *a], cwd=str(repo),
                              capture_output=True, text=True)

    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (repo / "f.txt").write_text("x", encoding="utf-8")
    git("add", "f.txt")
    git("commit", "-q", "-m", "init")
    return repo


def test_git_clean_repo_commit_and_not_dirty_batch175():
    repo = _mk_repo()
    p = build_provenance(repo, "fallback", 800, None)
    assert p["git_commit"] is not None
    assert re.fullmatch(r"[0-9a-f]{40}", p["git_commit"])
    assert p["git_dirty"] is False


def test_git_untracked_file_flips_dirty_batch175():
    repo = _mk_repo()
    (repo / "untracked.txt").write_text("y", encoding="utf-8")
    p = build_provenance(repo, "fallback", 800, None)
    assert p["git_commit"] is not None
    assert p["git_dirty"] is True


# ---------- silent_drop 0 保持 0 ----------

def test_silent_drop_zero_values_stay_zero_batch175():
    s = aggregate_summary([
        {"metrics": {"silent_drop_count": {
            "value": 0, "reason": None}}},
        {"metrics": {"silent_drop_count": {
            "value": None, "reason": "no_expectations"}}}])
    assert s["silent_drop_total"] == 0
    assert isinstance(s["silent_drop_total"], int)


# ---------- summary 顶层键序 ----------

def test_summary_top_keys_order_batch175():
    s = aggregate_summary([])
    assert list(s) == ["counts", "success_rates",
                       "ratio_macro_averages",
                       "silent_drop_total"]


# ---------- schema_valid 分歧 ----------

def test_schema_valid_macro_only_not_success_rates_batch175():
    s = aggregate_summary([{"metrics": {
        "pipeline_success": {"value": True, "reason": None},
        "schema_valid": {"value": True, "reason": None}}}])
    assert list(s["success_rates"]) == ["pipeline_success"]
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch175():
    src = _src()
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert "versions[pkg] = importlib.metadata.version(pkg)" in src
    assert '"max_chars": int(max_chars),' in src
    assert "rate = (successes / total) if total else None" in src


# ---------- forbidden tokens 第四百四十七批 ----------

def test_source_no_eval_batch175():
    assert "eval(" not in _src()


def test_source_no_exec_batch175():
    assert "exec(" not in _src()


def test_source_no_compile_batch175():
    assert "compile(" not in _src()


def test_source_no_globals_batch175():
    assert "globals(" not in _src()


def test_source_no_locals_batch175():
    assert "locals(" not in _src()


def test_source_no_os_system_batch175():
    assert "os.system" not in _src()


def test_source_no_popen_batch175():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch175():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch175():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch175():
    assert "socket" not in _src()


def test_source_no_requests_batch175():
    assert "requests" not in _src()


def test_source_no_urllib_batch175():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch175():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch175():
    assert "yield" not in _src()


def test_source_no_async_await_batch175():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch175():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch175():
    assert _src().count("subprocess.run") == 2
