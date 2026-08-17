"""evaluation/report.py 第二百八十一轮 edges 测试（Round 837）。

补强 edges88 未触及的角度（第二百一十一批）。

新角度：
- 临时 git 仓库直测 get_git_provenance：clean → 40 位
  commit + dirty False；untracked 文件 → dirty True
- get_dependency_versions 真实安装版本（pdfplumber 以数字开头）
- success rate 2/2 → 1.0；ratio 单值 0.25 直传
- silent_drop 混合 [None, 3] → 3
- _COUNT_METRICS 恰为单元素元组
- build_provenance max_chars 负 float 向零截断
- forbidden tokens 第三百零七批
"""

from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    _COUNT_METRICS,
    aggregate_summary,
    build_provenance,
    get_dependency_versions,
    get_git_provenance,
)


def _r(metrics):
    return {"doc_id": "d", "metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- 临时 git 仓库 ----------

def _mk_repo(tmp_path, dirty):
    repo = tmp_path / "repo"
    repo.mkdir()
    for cmd in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"],
        ["git", "commit", "-q", "--allow-empty", "-m", "x"],
    ):
        subprocess.run(cmd, cwd=repo, check=True,
                       capture_output=True)
    if dirty:
        (repo / "new.txt").write_text("x", encoding="utf-8")
    return repo


def test_git_clean_repo_batch55(tmp_path):
    g = get_git_provenance(_mk_repo(tmp_path, dirty=False))
    assert re.fullmatch(r"[0-9a-f]{40}",
                        g["git_commit"] or "")
    assert g["git_dirty"] is False


def test_git_dirty_repo_batch55(tmp_path):
    g = get_git_provenance(_mk_repo(tmp_path, dirty=True))
    assert re.fullmatch(r"[0-9a-f]{40}",
                        g["git_commit"] or "")
    assert g["git_dirty"] is True


# ---------- 依赖版本 ----------

def test_dependency_pdfplumber_version_batch55():
    v = get_dependency_versions()
    assert v["pdfplumber"] is not None
    assert re.match(r"^\d", v["pdfplumber"])


# ---------- 聚合 ----------

def test_success_rate_full_batch55():
    s = aggregate_summary([
        _r(_m("pipeline_success", True)),
        _r(_m("pipeline_success", True))])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 2, "rate": 1.0}


def test_ratio_single_value_batch55():
    s = aggregate_summary([_r(_m("schema_valid", 0.25))])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.25, "participating_docs": 1,
        "not_evaluated": 0}


def test_silent_drop_mixed_null_value_batch55():
    s = aggregate_summary([
        _r(_m("silent_drop_count", None)),
        _r(_m("silent_drop_count", 3))])
    assert s["silent_drop_total"] == 3


def test_count_metrics_tuple_batch55():
    assert _COUNT_METRICS == ("element_count_total",)


# ---------- max_chars 截断 ----------

def test_max_chars_negative_float_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      lambda: {}):
        p = build_provenance(Path("root"), "fallback", -2.5,
                             "1.0")
    assert p["max_chars"] == -2


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert 'for pkg in ("pdfplumber", "python-docx", "pypdfium2"):' in src
    assert "summary[\"counts\"] = counts" in src
    assert "datetime.now().astimezone().isoformat()" in src


# ---------- forbidden tokens 第三百零七批 ----------

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
