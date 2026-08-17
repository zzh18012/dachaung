"""evaluation/report.py 第二百三十九轮 edges 测试（Round 795）。

补强 edges82 未触及的角度（第一百五十九批）。

新角度：
- build_devset_section 接真实 load_manifest 产物：6 键 + 值
  （categories 排序并集来自 manifest）
- build_provenance：max_chars True → int 1（bool 是 int 子类被
  int() 收编）；dependencies 字典原样透传
- counts 浮点和：[1.5, 2.5] → sum 4.0（float 穿过求和）
- ratio 负值参与：[-1.0, 1.0] → macro 0.0（不裁剪、不拒）
- silent_drop 负值求和：[-5, 3] → -2
- 全部文档缺 pipeline_success 键 → success_count 0 / total 2 /
  rate 0.0（`is True` 过滤下缺键等同 False，rate 非 null）
- forbidden tokens 第二百六十五批
"""

from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import evaluation.report as report_mod
from evaluation.manifest import load_manifest
from evaluation.report import (
    aggregate_summary,
    build_devset_section,
    build_provenance,
)


def _manifest_env():
    tmp = Path(tempfile.mkdtemp())
    root = tmp / "proj"
    (root / "samples").mkdir(parents=True)
    (root / "samples" / "a.pdf").write_bytes(b"x")
    mf = tmp / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "samples/a.pdf",
             "source_type": "pdf", "categories": ["c1"]},
            {"doc_id": "d2", "path": "samples/a.pdf",
             "source_type": "pdf", "categories": ["c2"]}]}),
        encoding="utf-8")
    return load_manifest(mf, root)


# ---------- 真实 manifest 的 devset 段 ----------

def test_devset_section_from_real_manifest_batch54():
    d = build_devset_section(_manifest_env())
    assert d == {"status": "incomplete", "file_count": 2,
                 "content_group_count": 2, "pdf_count": 2,
                 "docx_count": 0, "categories_covered": ["c1", "c2"]}


# ---------- max_chars bool 与依赖透传 ----------

def test_provenance_max_chars_bool_and_deps_batch54():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c",
                                 "git_dirty": False}), \
            patch.object(report_mod, "get_dependency_versions",
                         lambda: {"pdfplumber": "9.9"}):
        p = build_provenance(Path("."), "fallback", True, "1.0")
    assert p["max_chars"] == 1
    assert p["dependencies"] == {"pdfplumber": "9.9"}


# ---------- counts 浮点和 ----------

def test_counts_float_sum_batch54():
    out = aggregate_summary([
        {"metrics": {"element_count_total": {"value": 1.5,
                                             "reason": None}}},
        {"metrics": {"element_count_total": {"value": 2.5,
                                             "reason": None}}}])
    assert out["counts"]["element_count_total"] == {"sum": 4.0,
                                                    "participating_docs":
                                                    2}


# ---------- ratio 负值 ----------

def test_ratio_negative_values_macro_zero_batch54():
    out = aggregate_summary([
        {"metrics": {"schema_valid": {"value": -1.0,
                                      "reason": None}}},
        {"metrics": {"schema_valid": {"value": 1.0,
                                      "reason": None}}}])
    assert out["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": 0.0, "participating_docs": 2,
        "not_evaluated": 0}


# ---------- silent_drop 负值 ----------

def test_silent_drop_negative_sum_batch54():
    out = aggregate_summary([
        {"metrics": {"silent_drop_count": {"value": -5,
                                           "reason": None}}},
        {"metrics": {"silent_drop_count": {"value": 3,
                                           "reason": None}}}])
    assert out["silent_drop_total"] == -2


# ---------- 缺 pipeline_success ----------

def test_missing_pipeline_success_rate_zero_batch54():
    out = aggregate_summary([{"metrics": {}}, {"metrics": {}}])
    assert out["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_coercion_lines_batch54():
    src = _src()
    assert '"max_chars": int(max_chars)' in src
    assert "manifest.categories_covered" in src
    assert "manifest.devset_status" in src


# ---------- forbidden tokens 第二百六十五批 ----------

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
