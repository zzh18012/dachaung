"""evaluation/report.py 第二百七十四轮 edges 测试（Round 830）。

补强 edges87 未触及的角度（第二百零四批）。

新角度：
- _RATIO_METRICS 元组恰 12 项：首 schema_valid 尾 chunk_boundary_f1
- aggregate_summary([]) 全空形态：counts sum null / success rate
  null / ratio macro null / silent null
- pipeline_success 全 False → rate 0.0（非 null）
- per_doc 缺 "metrics" 键 → KeyError（现状记录）
- build_devset_section 键序恰 6 项 + 值直传
- get_dependency_versions 恰 3 个键，值为 str 或 None
- build_provenance parser_name/version 直传（含 None）
- forbidden tokens 第三百批
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

import evaluation.report as report_mod
from evaluation.report import (
    _RATIO_METRICS,
    aggregate_summary,
    build_devset_section,
    build_provenance,
    get_dependency_versions,
)


def _r(metrics):
    return {"doc_id": "d", "metrics": metrics}


def _m(name, value):
    return {name: {"value": value, "reason": None}}


# ---------- _RATIO_METRICS ----------

def test_ratio_metrics_tuple_batch55():
    assert len(_RATIO_METRICS) == 12
    assert _RATIO_METRICS[0] == "schema_valid"
    assert _RATIO_METRICS[-1] == "chunk_boundary_f1"
    assert "text_char_multiset_precision" in _RATIO_METRICS


# ---------- 空列表 ----------

def test_empty_per_doc_full_shape_batch55():
    s = aggregate_summary([])
    assert list(s.keys()) == ["counts", "success_rates",
                              "ratio_macro_averages",
                              "silent_drop_total"]
    assert s["counts"]["element_count_total"] == {
        "sum": None, "participating_docs": 0}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 0, "rate": None}
    assert s["ratio_macro_averages"]["schema_valid"] == {
        "macro_average": None, "participating_docs": 0,
        "not_evaluated": 0}
    assert s["silent_drop_total"] is None


# ---------- 全 False ----------

def test_all_false_rate_zero_batch55():
    s = aggregate_summary([
        _r(_m("pipeline_success", False)),
        _r(_m("pipeline_success", False))])
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 0, "total": 2, "rate": 0.0}


# ---------- 缺 metrics 键 ----------

def test_missing_metrics_key_error_batch55():
    try:
        aggregate_summary([{"doc_id": "d1"}])
        raise AssertionError("no error")
    except KeyError as e:
        assert e.args[0] == "metrics"


# ---------- devset 段 ----------

def test_devset_section_key_order_batch55():
    m = SimpleNamespace(
        devset_status="incomplete", file_count=3,
        content_group_count=2, pdf_count=1, docx_count=2,
        categories_covered=["a", "b"])
    d = build_devset_section(m)
    assert list(d.keys()) == [
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered"]
    assert d["status"] == "incomplete"
    assert d["content_group_count"] == 2
    assert d["categories_covered"] == ["a", "b"]


# ---------- 依赖版本 ----------

def test_dependency_versions_keys_batch55():
    v = get_dependency_versions()
    assert set(v.keys()) == {"pdfplumber", "python-docx",
                             "pypdfium2"}
    for val in v.values():
        assert val is None or isinstance(val, str)


# ---------- provenance 直传 ----------

def test_build_provenance_passthrough_batch55():
    with patch.object(report_mod, "get_git_provenance",
                      lambda r: {"git_commit": "c1",
                                 "git_dirty": True}), \
         patch.object(report_mod, "get_dependency_versions",
                      lambda: {}):
        p = build_provenance(Path("root"), "kreuzberg", 800, None)
    assert p["parser_name"] == "kreuzberg"
    assert p["parser_version"] is None
    assert p["git_commit"] == "c1"
    assert p["git_dirty"] is True
    assert p["dependencies"] == {}
    assert p["max_chars"] == 800
    assert p["evaluator_version"] == "1.1"
    assert p["report_version"] == "1.1"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(report_mod)


def test_source_key_lines_batch55():
    src = _src()
    assert "rate = (successes / total) if total else None" in src
    assert "macro = sum(values) / len(values)" in src
    assert 'summary["silent_drop_total"] = sum(silent_vals) if silent_vals else None' in src


# ---------- forbidden tokens 第三百批 ----------

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
