"""evaluation/report.py 第二百零三轮 edges 测试（Round 739）。

补强 edges73/edges74 未触及的角度（第一百零四批）。

新角度：
- TimeoutExpired（SubprocessError 子类）→ except 分支 (None, True)
- rev-parse rc=0 但 stdout 空 → commit None（"strip() or None"）
- porcelain rc!=0 且 rev-parse 成功 → dirty False（现状记录：
  git status 失败不视为脏）
- _RATIO_METRICS[0] 是 schema_valid
- counts 多文档求和 {sum:7, participating:2}
- ratio 不做 [0,1] 截断：1.5 原样进 macro、负值参与平均
- 文档存在但缺 metric → rate 0.0（不是 None —— 与零文档 rate None 对照）
- build_devset_section 配对组：a↔b 双向 + c 未配对 → groups 2、
  categories 排序、pdf/docx 分开数
- forbidden tokens 第二百零九批
"""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path

import pytest

import evaluation.report as report_mod
from evaluation.manifest import DocumentEntry, Manifest
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    get_git_provenance,
)

ROOT = Path(__file__).resolve().parents[1]


def _git_fake(rc1=0, out1="abc\n", rc2=0, out2=""):
    def fake(cmd, **kwargs):
        if cmd[1] == "rev-parse":
            return subprocess.CompletedProcess(cmd, rc1, stdout=out1,
                                               stderr="")
        return subprocess.CompletedProcess(cmd, rc2, stdout=out2, stderr="")
    return fake


# ---------- git 补角 ----------

def test_git_timeout_expired_branch_batch54(monkeypatch):
    def boom(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 10)
    monkeypatch.setattr(report_mod.subprocess, "run", boom)
    assert get_git_provenance(ROOT) == {"git_commit": None,
                                        "git_dirty": True}


def test_git_revparse_empty_stdout_commit_none_batch54(monkeypatch):
    monkeypatch.setattr(report_mod.subprocess, "run",
                        _git_fake(rc1=0, out1=""))
    assert get_git_provenance(ROOT)["git_commit"] is None


def test_git_porcelain_nonzero_rc_dirty_false_batch54(monkeypatch):
    # 现状记录：git status 失败（rc!=0）不进 except，dirty 判 False
    monkeypatch.setattr(report_mod.subprocess, "run",
                        _git_fake(rc1=0, out1="c\n", rc2=1, out2=""))
    assert get_git_provenance(ROOT) == {"git_commit": "c",
                                        "git_dirty": False}


# ---------- 指标集合 ----------

def test_ratio_metrics_first_element_schema_valid_batch54():
    assert _RATIO_METRICS[0] == "schema_valid"
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"


# ---------- 聚合补角 ----------

def test_counts_multi_doc_sum_batch54():
    s = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 3}}},
        {"metrics": {"element_count_total": {"value": 4}}},
    ])
    assert s["counts"]["element_count_total"] == {"sum": 7,
                                                  "participating_docs": 2}


def test_ratio_no_clamping_above_one_batch54():
    s = aggregate_summary(
        [{"metrics": {"heading_boundary_compliance": {"value": 1.5}}}])
    assert s["ratio_macro_averages"]["heading_boundary_compliance"] == {
        "macro_average": 1.5, "participating_docs": 1, "not_evaluated": 0}


def test_ratio_negative_values_average_batch54():
    s = aggregate_summary([
        {"metrics": {"heading_boundary_compliance": {"value": -0.5}}},
        {"metrics": {"heading_boundary_compliance": {"value": 0.5}}},
    ])
    assert s["ratio_macro_averages"]["heading_boundary_compliance"] == {
        "macro_average": 0.0, "participating_docs": 2, "not_evaluated": 0}


def test_success_missing_metric_rate_zero_not_none_batch54():
    s = aggregate_summary([{"metrics": {}}, {"metrics": {}}])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


# ---------- devset 配对 ----------

def test_devset_section_paired_groups_batch54():
    def entry(i, pw=None, st="pdf"):
        return DocumentEntry(
            doc_id=i, path_str=f"{i}.pdf", resolved_path=ROOT / f"{i}.pdf",
            source_type=st, sha256=None, categories=(i,), paired_with=pw,
            annotation_file_str=None, annotation_resolved=None,
            expectations=None)

    man = Manifest("1.0", "incomplete",
                   (entry("a", "b"), entry("b", "a", "docx"), entry("c")),
                   (), ROOT)
    assert build_devset_section(man) == {
        "status": "incomplete", "file_count": 3,
        "content_group_count": 2, "pdf_count": 2, "docx_count": 1,
        "categories_covered": ["a", "b", "c"],
    }


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(report_mod)


def test_source_dirty_expression_batch54():
    src = _src()
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert "commit = r.stdout.strip() or None" in src


def test_source_subprocess_error_in_except_batch54():
    assert "except (OSError, subprocess.SubprocessError):" in _src()


# ---------- forbidden tokens 第二百零九批 ----------

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
