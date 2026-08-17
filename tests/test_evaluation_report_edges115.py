"""evaluation/report.py 第四百六十三轮 edges 测试（Round 1019）。

补强 edges114 未触及的角度（第三百九十五批，probe 实证）。

新角度（12 指标分歧矩阵回合）：
- 三文档 [None, 0.0, 1.0] 铺满全部 12 个 ratio 指标 →
  每项 macro_average 0.5、participating_docs 2、
  not_evaluated 1（一次性锁 12 项同构聚合）
- figure_caption_* 不进 ratio_macro_averages（键集精确 ==
  _RATIO_METRICS 12 项）
- counts sum 5/participating 2、success 2/3 rate 2/3、
  silent_drop_total 2 三类不混
- 整份分歧报告照过 evaluation-report.schema.json
- forbidden tokens 第四百八十九批（open 0 + subprocess.run
  恰 2；subprocess 是本模块合法依赖不列禁词）
"""

from __future__ import annotations

import inspect
from pathlib import Path

import evaluation.report as rpt
from evaluation.report import (aggregate_summary,
                               build_devset_section,
                               build_provenance)
from evaluation.schema import validate

_RATIOS = (
    "schema_valid", "pdf_locator_valid_ratio",
    "docx_locator_valid_ratio",
    "image_resource_exists_ratio",
    "chunk_reference_intact_ratio",
    "text_preservation_equal",
    "text_char_multiset_precision",
    "text_char_multiset_recall",
    "heading_boundary_compliance",
    "chunk_boundary_precision", "chunk_boundary_recall",
    "chunk_boundary_f1")


class _StubManifest:
    devset_status = "incomplete"
    file_count = 3
    content_group_count = 3
    pdf_count = 3
    docx_count = 0
    categories_covered = ["z"]


def _matrix_per_doc():
    per_doc = []
    for i, v in enumerate([None, 0.0, 1.0]):
        metrics = {n: {"value": v,
                       "reason": None if v is not None else "r"}
                   for n in _RATIOS}
        metrics["element_count_total"] = {
            "value": [0, 5, None][i], "reason": None}
        metrics["silent_drop_count"] = {
            "value": [None, 2, None][i], "reason": None}
        metrics["pipeline_success"] = {
            "value": [True, False, True][i], "reason": None}
        per_doc.append({
            "doc_id": f"d{i}", "source_type": "pdf",
            "metrics": metrics,
            "wall_time_seconds": {
                "total": 0.1, "parse": None, "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented"}})
    return per_doc


# ---------- 三类不混 ----------

def test_divergence_matrix_summary_batch217():
    s = aggregate_summary(_matrix_per_doc())
    assert s["counts"] == {"element_count_total": {
        "sum": 5, "participating_docs": 2}}
    assert s["success_rates"]["pipeline_success"] == {
        "success_count": 2, "total": 3,
        "rate": 2 / 3}
    assert s["silent_drop_total"] == 2


# ---------- 12 项 ratio 同构 ----------

def test_twelve_ratio_macros_batch217():
    s = aggregate_summary(_matrix_per_doc())
    rmas = s["ratio_macro_averages"]
    assert set(rmas) == set(_RATIOS)
    assert len(rmas) == 12
    assert all(v["macro_average"] == 0.5
               for v in rmas.values())
    assert all(v["participating_docs"] == 2
               for v in rmas.values())
    assert all(v["not_evaluated"] == 1
               for v in rmas.values())
    assert "figure_caption_precision" not in rmas


# ---------- 整份报告过 RS ----------

def test_divergence_report_rs_valid_batch217(tmp_path):
    per_doc = _matrix_per_doc()
    report = {
        "report_version": "1.1",
        "provenance": build_provenance(Path(tmp_path),
                                       "fallback", 800, None),
        "devset": build_devset_section(_StubManifest()),
        "summary": aggregate_summary(per_doc),
        "per_doc": per_doc,
        "expected_failures": []}
    validate(report, "evaluation-report.schema.json")


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch217():
    src = _src()
    assert "_RATIO_METRICS = (" in src
    assert 'summary["ratio_macro_averages"] = ratio_avgs' in src
    assert "rate = (successes / total) if total else None" in src


# ---------- forbidden tokens 第四百八十九批 ----------

def test_source_no_eval_batch217():
    assert "eval(" not in _src()


def test_source_no_exec_batch217():
    assert "exec(" not in _src()


def test_source_no_compile_batch217():
    assert "compile(" not in _src()


def test_source_no_globals_batch217():
    assert "globals(" not in _src()


def test_source_no_locals_batch217():
    assert "locals(" not in _src()


def test_source_no_os_system_batch217():
    assert "os.system" not in _src()


def test_source_no_popen_batch217():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch217():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch217():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch217():
    assert "socket" not in _src()


def test_source_no_requests_batch217():
    assert "requests" not in _src()


def test_source_no_urllib_batch217():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch217():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch217():
    assert "yield" not in _src()


def test_source_no_async_await_batch217():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch217():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch217():
    assert _src().count("subprocess.run") == 2
