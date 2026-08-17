"""evaluation/report.py 第二百八十八轮 edges 测试（Round 844）。

补强 edges89 未触及的角度（第二百一十八批）。

新角度：
- ratio 值 False（bool）参与 macro：sum([False])/1 → 0.0
  float（False 非 None 不被过滤）
- figure_caption_* 不在 _RATIO_METRICS（恒 null 不参与聚合）
- counts [-5, 3] → sum -2（负值不截断的混合形态）
- build_provenance max_chars 传 str "800" → int() 接受
- build_devset_section 接真实 load_manifest 产物（集成）
- get_git_provenance 传文件路径（非目录）→ cwd 非法抛
  OSError → 异常分支 dirty=True（docstring 承诺唯一兑现处）
- forbidden tokens 第三百一十四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_git_provenance,
)
from evaluation.manifest import load_manifest


def _r(metrics):
    return {"doc_id": "d", "metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- ratio False ----------

def test_ratio_false_value_macro_zero_batch55():
    s = aggregate_summary([_r(_m("schema_valid", False))])
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.0, "participating_docs": 1,
        "not_evaluated": 0}


# ---------- figure_caption 不参与 ----------

def test_figure_caption_not_ratio_batch55():
    for k in ("figure_caption_precision",
              "figure_caption_recall", "figure_caption_f1"):
        assert k not in _RATIO_METRICS


# ---------- counts 混合负值 ----------

def test_counts_negative_mixed_sum_batch55():
    s = aggregate_summary([
        _r(_m("element_count_total", -5)),
        _r(_m("element_count_total", 3))])
    assert s["counts"]["element_count_total"] == {
        "sum": -2, "participating_docs": 2}


# ---------- max_chars str ----------

def test_max_chars_str_coerced_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": None,
                                 "git_dirty": False}), \
         patch.object(report_mod, "get_dependency_versions",
                      lambda: {}):
        p = build_provenance(Path("root"), "fallback", "800",
                             None)  # type: ignore[arg-type]
    assert p["max_chars"] == 800
    assert isinstance(p["max_chars"], int)


# ---------- 真实 Manifest 集成 ----------

def test_devset_section_real_manifest_batch55(tmp_path):
    root = tmp_path / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    (root / "samples" / "b.pdf").write_bytes(b"x")
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf", "categories": ["x"]},
            {"doc_id": "d2", "path": "samples/b.pdf",
             "source_type": "pdf", "categories": ["y"],
             "paired_with": "d1"},
            {"doc_id": "d1b", "path": "samples/b.pdf",
             "source_type": "pdf", "paired_with": "d2"},
        ]}), encoding="utf-8")
    m = load_manifest(f, root)
    d = build_devset_section(m)
    assert d == {
        "status": "complete", "file_count": 3,
        "content_group_count": 2, "pdf_count": 3,
        "docx_count": 0, "categories_covered": ["x", "y"]}


# ---------- git 文件路径 ----------

def test_git_provenance_file_path_batch55(tmp_path):
    f = tmp_path / "somefile.txt"
    f.write_text("x", encoding="utf-8")
    g = get_git_provenance(f)
    # cwd 指向文件 → NotADirectoryError（OSError）→ 异常分支
    # commit=None 且 dirty=True（docstring 承诺只在异常路径成立）
    assert g == {"git_commit": None, "git_dirty": True}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "not_eval = len(per_doc_results) - len(values)" in src
    assert "dirty = bool(r2.returncode == 0 and r2.stdout.strip())" in src
    assert '"max_chars": int(max_chars),' in src


# ---------- forbidden tokens 第三百一十四批 ----------

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
