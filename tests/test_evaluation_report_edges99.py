"""evaluation/report.py 第三百五十一轮 edges 测试（Round 907）。

补强 edges98 未触及的角度（第二百八十三批，probe 实证）。

新角度：
- get_git_provenance 的 cwd 不存在 → subprocess 抛 OSError
  （FileNotFoundError 子类）被捕获 → {None, True}
- build_devset_section 接真实 load_manifest 产物：status /
- categories_covered（真实 list 而非 fake 类）
- _RATIO_METRICS 尾三项顺序
- 全 False success → rate 0.0（分母非 0 不为 None）
- aggregate_summary 不改动传入行
- forbidden tokens 第三百七十七批（report 变体：subprocess.run 计 2）
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    get_git_provenance,
)


def _pd(metrics):
    return {"metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- cwd 不存在 ----------

def test_git_provenance_missing_cwd_oserror_batch105(tmp_path):
    out = get_git_provenance(tmp_path / "nope")
    assert out == {"git_commit": None, "git_dirty": True}


# ---------- 真实 Manifest 集成 ----------

def test_devset_section_real_manifest_batch105(tmp_path):
    from evaluation.manifest import load_manifest

    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf", "categories": ["c1", "c2"]}]}),
        encoding="utf-8")
    m = load_manifest(f, root)
    d = build_devset_section(m)
    assert d["status"] == "complete"
    assert d["file_count"] == 1
    assert d["pdf_count"] == 1
    assert d["docx_count"] == 0
    assert d["content_group_count"] == 1
    assert d["categories_covered"] == ["c1", "c2"]
    assert isinstance(d["categories_covered"], list)


# ---------- 尾三项顺序 ----------

def test_ratio_tail_order_batch105():
    assert _RATIO_METRICS[-3:] == (
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1")


# ---------- 全 False ----------

def test_success_all_false_rate_zero_batch105():
    s = aggregate_summary([
        _pd(_m("pipeline_success", False)),
        _pd(_m("pipeline_success", False)),
    ])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


# ---------- 输入不可变 ----------

def test_aggregate_does_not_mutate_rows_batch105():
    rows = [
        {"doc_id": "d1",
         "metrics": {"pipeline_success": {"value": True,
                                          "reason": None}},
         "_internal": "keep"},
    ]
    aggregate_summary(rows)
    assert rows[0]["_internal"] == "keep"
    assert list(rows[0]) == ["doc_id", "metrics", "_internal"]


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch105():
    src = _src()
    assert "except (OSError, subprocess.SubprocessError):" in src
    assert 'summary["counts"] = counts' in src
    assert '"categories_covered": manifest.categories_covered,' in src


# ---------- forbidden tokens 第三百七十七批（report 变体）----------

def test_source_no_eval_batch105():
    assert "eval(" not in _src()


def test_source_no_exec_batch105():
    assert "exec(" not in _src()


def test_source_no_compile_batch105():
    assert "compile(" not in _src()


def test_source_no_globals_batch105():
    assert "globals(" not in _src()


def test_source_no_locals_batch105():
    assert "locals(" not in _src()


def test_source_no_os_system_batch105():
    assert "os.system" not in _src()


def test_source_subprocess_run_count_is_2_batch105():
    assert _src().count("subprocess.run") == 2


def test_source_no_popen_batch105():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch105():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch105():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch105():
    assert "socket" not in _src()


def test_source_no_requests_batch105():
    assert "requests" not in _src()


def test_source_no_urllib_batch105():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch105():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch105():
    assert "yield" not in _src()


def test_source_no_async_await_batch105():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch105():
    assert "open(" not in _src()
