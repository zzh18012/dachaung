"""evaluation/report.py 第四百五十六轮 edges 测试（Round 1012）。

补强 edges113 未触及的角度（第三百八十八批，probe 实证）。

新角度（生产者 → Schema 端到端回合）：
- 空文档集：build_provenance + build_devset_section +
  aggregate_summary([]) 组装的报告通过
  evaluation-report.schema.json（真实生产者产物合法）
- 全指标管线：compute_automatic_metrics + figure_caption_prf
  + chunk_boundary_prf（_tolerance_chars pop 后）共 20 键
  metrics + wall_time 5 键 → 整份报告照过 RS
- 20 键 = 14 自动 + 3 figure_caption + 3 chunk_boundary
  （_tolerance_chars 已剥离，RS per_doc closed 放行）
- forbidden tokens 第四百八十二批（open 0 + subprocess.run
  恰 2）
"""

from __future__ import annotations

import inspect
from pathlib import Path

import evaluation.report as rpt
from evaluation.annotation_metrics import (chunk_boundary_prf,
                                           figure_caption_prf)
from evaluation.metrics import compute_automatic_metrics
from evaluation.report import (aggregate_summary,
                               build_devset_section,
                               build_provenance)
from evaluation.schema import validate


class _StubManifest:
    devset_status = "incomplete"
    file_count = 1
    content_group_count = 1
    pdf_count = 1
    docx_count = 0
    categories_covered = ["x"]


def _full_metrics(tmp_path):
    (tmp_path / "img.png").write_bytes(b"x")
    doc = {
        "schema_version": "0.1.0", "document_id": "d",
        "source_path": "a.pdf", "source_type": "pdf",
        "source_hash": "a" * 64, "parser_name": "fallback",
        "parser_version": "1",
        "elements": [
            {"element_id": "e1", "type": "paragraph",
             "content": "hello", "parent_id": None,
             "confidence": 0.9, "metadata": {},
             "source_locator": {"page": 1, "bbox": [1, 2, 3, 4]}},
            {"element_id": "i1", "type": "image",
             "resource_path": "img.png", "parent_id": None,
             "confidence": 0.9, "metadata": {},
             "source_locator": {"page": 1,
                                "bbox": [1, 2, 3, 4]}}],
        "chunks": [{"chunk_id": "c1", "text": "hello",
                    "source_element_ids": ["e1"],
                    "char_count": 5}],
        "relations": [], "warnings": [], "errors": [],
        "metadata": {}}
    metrics = compute_automatic_metrics(doc, None, "pdf", None,
                                        tmp_path)
    metrics.update(figure_caption_prf(doc, None))
    cb = chunk_boundary_prf(doc, None, tolerance_chars=30)
    cb.pop("_tolerance_chars", None)
    metrics.update(cb)
    return metrics


# ---------- 空文档集回合 ----------

def test_empty_producers_report_valid_batch210(tmp_path):
    report = {
        "report_version": "1.1",
        "provenance": build_provenance(tmp_path, "fallback", 800,
                                       None),
        "devset": build_devset_section(_StubManifest()),
        "summary": aggregate_summary([]),
        "per_doc": [],
        "expected_failures": [],
    }
    validate(report, "evaluation-report.schema.json")


# ---------- 全指标管线回合 ----------

def test_full_metrics_report_valid_batch210(tmp_path):
    metrics = _full_metrics(tmp_path)
    report = {
        "report_version": "1.1",
        "provenance": build_provenance(tmp_path, "fallback", 800,
                                       None),
        "devset": build_devset_section(_StubManifest()),
        "summary": aggregate_summary([{"metrics": metrics}]),
        "per_doc": [{
            "doc_id": "d1", "source_type": "pdf",
            "metrics": metrics,
            "wall_time_seconds": {
                "total": 0.1, "parse": None, "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented"}}],
        "expected_failures": [],
    }
    validate(report, "evaluation-report.schema.json")


# ---------- 20 键构成 ----------

def test_metrics_key_count_20_batch210(tmp_path):
    metrics = _full_metrics(tmp_path)
    assert len(metrics) == 20
    assert "_tolerance_chars" not in metrics
    fig = [k for k in metrics if k.startswith("figure_caption_")]
    bnd = [k for k in metrics if k.startswith("chunk_boundary_")]
    assert len(fig) == 3 and len(bnd) == 3


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(rpt)


def test_source_key_lines_batch210():
    src = _src()
    assert "def build_provenance(" in src
    assert '"categories_covered": manifest.categories_covered,' in src
    assert "total = len(per_doc_results)" in src


# ---------- forbidden tokens 第四百八十二批 ----------

def test_source_no_eval_batch210():
    assert "eval(" not in _src()


def test_source_no_exec_batch210():
    assert "exec(" not in _src()


def test_source_no_compile_batch210():
    assert "compile(" not in _src()


def test_source_no_globals_batch210():
    assert "globals(" not in _src()


def test_source_no_locals_batch210():
    assert "locals(" not in _src()


def test_source_no_os_system_batch210():
    assert "os.system" not in _src()


def test_source_no_popen_batch210():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch210():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch210():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch210():
    assert "socket" not in _src()


def test_source_no_requests_batch210():
    assert "requests" not in _src()


def test_source_no_urllib_batch210():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch210():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch210():
    assert "yield" not in _src()


def test_source_no_async_await_batch210():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch210():
    assert "open(" not in _src()


def test_source_subprocess_run_count_is_2_batch210():
    assert _src().count("subprocess.run") == 2
