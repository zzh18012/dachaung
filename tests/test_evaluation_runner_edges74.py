"""evaluation/runner.py 第九十一轮 edges 测试（Round 655）。

补强 edges73 未触及的角度（第四十八批）。

新角度：
- _load_annotation 更多错误路径（OSError → None / 目录而非文件 → None）
- _process_one errors 路径（errors 非空时返回 errors[0].to_dict()）
- _process_one document None 路径（返回 unknown error dict）
- _process_one 成功路径（document.to_dict + parser_version）
- _process_one image_dir 推导（document None 时 None / document 非空时 Path）
- _process_one out_stub unlink 失败时不抛（OSError 不会传到调用方）
- run_evaluation expected_failures 完整流程
- run_evaluation report JSON 写盘内容
- run_evaluation wall_time_seconds 完整结构（total / parse null / chunk null / parse_reason / chunk_reason）
- run_evaluation per_doc 完整字段（含 _ 私有键）
- run_evaluation public_per_doc 不含 _ 私有键
- 模块源码补强
- AST 结构补强
- forbidden tokens 第一百二十五批
"""

from __future__ import annotations

import ast
import inspect
import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 更多错误路径 ----------

def test_load_annotation_directory_not_file_batch48(tmp_path):
    """路径是目录 → 返回 None。"""
    d = tmp_path / "subdir"
    d.mkdir()
    out = _load_annotation(d)
    assert out is None


def test_load_annotation_oserror_returns_none_batch48(tmp_path):
    """open 抛 OSError → 返回 None。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        out = _load_annotation(p)
    assert out is None


def test_load_annotation_returns_dict_on_success_batch48(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"k": "v"}


# ---------- _process_one errors 路径 ----------

def _make_doc(**kw):
    m = MagicMock()
    m.doc_id = kw.get("doc_id", "d1")
    m.resolved_path = kw.get("resolved_path", Path("/tmp/x.pdf"))
    m.source_type = kw.get("source_type", "pdf")
    m.annotation_resolved = kw.get("annotation_resolved", None)
    m.expectations = kw.get("expectations", None)
    return m


def test_process_one_errors_returns_error_dict_batch48(tmp_path):
    """errors 非空 → 返回 (None, errors[0].to_dict(), elapsed, None, image_dir)。
    errors 路径无论 document 是否非空，都返回 document=None。"""
    doc = _make_doc()
    fake_err = MagicMock()
    fake_err.to_dict.return_value = {"code": "E_PARSE"}
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [fake_err])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, elapsed, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None  # errors 路径强制返回 None
    assert error == {"code": "E_PARSE"}
    assert pv is None  # errors 路径不返回 parser_version


def test_process_one_errors_empty_document_none_batch48(tmp_path):
    """errors 非空 + document None → 走 errors 路径。"""
    doc = _make_doc()
    fake_err = MagicMock()
    fake_err.to_dict.return_value = {"code": "E_PARSE"}
    with patch("evaluation.runner.process_single", return_value=(None, [fake_err])):
        document, error, elapsed, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error == {"code": "E_PARSE"}
    assert pv is None
    assert image_dir is None  # document None → image_dir None


def test_process_one_no_errors_no_document_returns_unknown_batch48(tmp_path):
    """无 errors 但 document 是 None → 返回 unknown error。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        document, error, elapsed, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document is None
    assert error["code"] == "unknown"
    assert "process_single returned None" in error["message"]


def test_process_one_success_returns_document_dict_batch48(tmp_path):
    """成功路径：返回 document.to_dict + parser_version。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, elapsed, pv, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert document == {"id": "d1"}
    assert error is None
    assert pv == "1.0"


def test_process_one_elapsed_positive_batch48(tmp_path):
    """elapsed 是正数。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _, _, elapsed, _, _ = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(elapsed, float)
    assert elapsed >= 0.0


def test_process_one_image_dir_when_document_none_batch48(tmp_path):
    """document None 时 image_dir None。"""
    doc = _make_doc()
    with patch("evaluation.runner.process_single", return_value=(None, [])):
        _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir is None


def test_process_one_image_dir_when_document_exists_batch48(tmp_path):
    """document 非空时 image_dir 是 Path（来自 image_output_dir_for）。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    expected = tmp_path / "imgs"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=expected) as mock_call:
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
    assert image_dir == expected
    mock_call.assert_called_once()


def test_process_one_unlink_failure_silent_batch48(tmp_path):
    """out_stub.unlink 抛 OSError 不应传到调用方。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("pathlib.Path.unlink", side_effect=OSError("perm")):
                # 不抛
                _process_one(doc, tmp_path, "fallback", 800)


# ---------- run_evaluation expected_failures 完整流程 ----------

def _make_manifest(docs=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = docs or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path("/tmp")
    return m


def test_run_evaluation_expected_failures_path_batch48(tmp_path):
    """expected_failures 跑 process_single 并记录 actual_code。"""
    ef = MagicMock()
    ef.doc_id = "f1"
    ef.resolved_path = tmp_path / "fail.pdf"
    ef.expected_error_code = "E_PARSE"

    fake_err = MagicMock()
    fake_err.code = "E_PARSE"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(None, [fake_err])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                with patch("evaluation.runner.aggregate_summary", return_value={}):
                    report = run_evaluation(manifest, out)
    assert report["expected_failures"] == [
        {
            "doc_id": "f1",
            "expected_error_code": "E_PARSE",
            "actual_error_code": "E_PARSE",
            "matches": True,
        }
    ]


def test_run_evaluation_expected_failures_mismatch_batch48(tmp_path):
    ef = MagicMock()
    ef.doc_id = "f1"
    ef.resolved_path = tmp_path / "fail.pdf"
    ef.expected_error_code = "E_PARSE"

    fake_err = MagicMock()
    fake_err.code = "E_OCR"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(None, [fake_err])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                with patch("evaluation.runner.aggregate_summary", return_value={}):
                    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] == "E_OCR"
    assert ef_result["matches"] is False


def test_run_evaluation_expected_failures_no_errors_batch48(tmp_path):
    """expected_failure 没产生 errors → actual_code=None。"""
    ef = MagicMock()
    ef.doc_id = "f1"
    ef.resolved_path = tmp_path / "fail.pdf"
    ef.expected_error_code = "E_PARSE"

    fake_document = MagicMock()
    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                with patch("evaluation.runner.aggregate_summary", return_value={}):
                    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


# ---------- run_evaluation report JSON 写盘内容 ----------

def test_run_evaluation_writes_json_to_disk_batch48(tmp_path):
    """报告应写入 output_path。"""
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.build_provenance", return_value={"k": "v"}):
        with patch("evaluation.runner.build_devset_section", return_value={"status": "complete"}):
            with patch("evaluation.runner.aggregate_summary", return_value={"silent_drop_total": 0}):
                report = run_evaluation(manifest, out)
    assert out.is_file()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == report


def test_run_evaluation_report_has_6_top_keys_batch48(tmp_path):
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                report = run_evaluation(manifest, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_run_evaluation_report_version_matches_constant_batch48(tmp_path):
    from evaluation import REPORT_VERSION
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_creates_output_root_batch48(tmp_path):
    """output_root 不存在时自动创建。"""
    out = tmp_path / "deep" / "nested" / "r.json"
    manifest = _make_manifest(project_root=tmp_path)
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            with patch("evaluation.runner.aggregate_summary", return_value={}):
                run_evaluation(manifest, out)
    assert out.is_file()


# ---------- run_evaluation wall_time_seconds 完整结构 ----------

def test_run_evaluation_wall_time_seconds_structure_batch48(tmp_path):
    """per_doc 的 wall_time_seconds 应有 5 keys。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", return_value={}):
                                    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)


# ---------- run_evaluation per_doc 完整字段（含 _ 私有键） ----------

def test_run_evaluation_per_doc_internal_has_private_keys_batch48(tmp_path):
    """per_doc_results 内部有 _ 私有键（不出现在最终 report）。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"

    captured = {}

    def fake_aggregate(per_doc):
        captured["first"] = per_doc[0] if per_doc else None
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                                    run_evaluation(manifest, out)
    internal = captured["first"]
    assert "_annotation_present" in internal
    assert "_tolerance_chars" in internal
    assert "_missing_markers" in internal


def test_run_evaluation_public_per_doc_no_private_keys_batch48(tmp_path):
    """public_per_doc 不应有 _ 私有键。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", return_value={}):
                                    report = run_evaluation(manifest, out)
    public = report["per_doc"][0]
    assert set(public.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert not any(k.startswith("_") for k in public.keys())


def test_run_evaluation_annotation_present_false_when_none_batch48(tmp_path):
    """annotation_resolved None 时 _annotation_present=False。"""
    doc = _make_doc()
    doc.annotation_resolved = None
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    captured = {}

    def fake_aggregate(per_doc):
        captured["first"] = per_doc[0]
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                                    run_evaluation(manifest, out)
    assert captured["first"]["_annotation_present"] is False


def test_run_evaluation_tolerance_chars_default_30_batch48(tmp_path):
    """chunk_boundary_prf 默认 tolerance_chars=30。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tol"] = tolerance_chars
        return {"_tolerance_chars": {"value": tolerance_chars, "reason": None}}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", return_value={}):
                                    run_evaluation(manifest, out)
    assert captured["tol"] == 30


def test_run_evaluation_tolerance_chars_custom_batch48(tmp_path):
    """run_evaluation(tolerance_chars=99) 传到 chunk_boundary_prf。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    captured = {}

    def fake_chunk_b(document, annotation, tolerance_chars=30):
        captured["tol"] = tolerance_chars
        return {"_tolerance_chars": {"value": tolerance_chars, "reason": None}}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", side_effect=fake_chunk_b):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", return_value={}):
                                    run_evaluation(manifest, out, tolerance_chars=99)
    assert captured["tol"] == 99


def test_run_evaluation_missing_markers_default_empty_list_batch48(tmp_path):
    """chunk_b 无 _missing_markers → per_doc 默认 []。"""
    doc = _make_doc()
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "1.0"
    captured = {}

    def fake_aggregate(per_doc):
        captured["first"] = per_doc[0]
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={"_tolerance_chars": {"value": 30, "reason": None}}):
                        with patch("evaluation.runner.build_provenance", return_value={}):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                                    run_evaluation(manifest, out)
    assert captured["first"]["_missing_markers"] == []


def test_run_evaluation_parser_version_first_doc_batch48(tmp_path):
    """parser_version 取第一个成功的 document。"""
    doc1 = _make_doc(doc_id="d1")
    doc2 = _make_doc(doc_id="d2")
    fake1 = MagicMock()
    fake1.to_dict.return_value = {"id": "d1"}
    fake1.source_hash = "h1"
    fake1.parser_version = "v1"
    fake2 = MagicMock()
    fake2.to_dict.return_value = {"id": "d2"}
    fake2.source_hash = "h2"
    fake2.parser_version = "v2"
    captured = {}

    def fake_build_prov(project_root, parser_name, max_chars, parser_version):
        captured["pv"] = parser_version
        return {}

    manifest = _make_manifest(docs=[doc1, doc2], project_root=tmp_path)
    out = tmp_path / "r.json"
    with patch("evaluation.runner.process_single", side_effect=[(fake1, []), (fake2, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.compute_automatic_metrics", return_value={}):
                with patch("evaluation.runner.figure_caption_prf", return_value={}):
                    with patch("evaluation.runner.chunk_boundary_prf", return_value={}):
                        with patch("evaluation.runner.build_provenance", side_effect=fake_build_prov):
                            with patch("evaluation.runner.build_devset_section", return_value={}):
                                with patch("evaluation.runner.aggregate_summary", return_value={}):
                                    run_evaluation(manifest, out)
    # 第一个成功 document 的 parser_version 是 "v1"
    assert captured["pv"] == "v1"


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "import json" in src


def test_source_contains_time_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "import time" in src


def test_source_contains_pathlib_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "from typing import Any" in src


def test_source_contains_pipeline_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "from app.pipeline import" in src


def test_source_contains_process_single_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "process_single" in src


def test_source_contains_image_output_dir_for_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for" in src


def test_source_contains_report_version_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "REPORT_VERSION" in src


def test_source_contains_chunk_boundary_prf_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "chunk_boundary_prf" in src


def test_source_contains_figure_caption_prf_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "figure_caption_prf" in src


def test_source_contains_compute_automatic_metrics_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "compute_automatic_metrics" in src


def test_source_contains_aggregate_summary_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "aggregate_summary" in src


def test_source_contains_build_provenance_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "build_provenance" in src


def test_source_contains_build_devset_section_import_batch48():
    src = inspect.getsource(runner_mod)
    assert "build_devset_section" in src


def test_source_contains_perf_counter_call_batch48():
    src = inspect.getsource(runner_mod)
    assert "perf_counter" in src


def test_source_contains_not_instrumented_batch48():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_source_contains_pipeline_failed_batch48():
    """docstring 提到 pipeline_failed。"""
    src = inspect.getsource(runner_mod)
    assert "pipeline_failed" in src


def test_source_contains_unknown_error_code_batch48():
    """document None 无 errors 时返回 'unknown' 错误码。"""
    src = inspect.getsource(runner_mod)
    assert '"unknown"' in src


def test_source_contains_write_json_false_batch48():
    """调用 process_single 时 write_json=False。"""
    src = inspect.getsource(runner_mod)
    assert "write_json=False" in src


def test_source_contains_ensure_ascii_false_batch48():
    """JSON 写盘用 ensure_ascii=False（中文不转义）。"""
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_source_contains_all_list_run_evaluation_batch48():
    src = inspect.getsource(runner_mod)
    assert "__all__" in src
    assert '"run_evaluation"' in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3  # _load_annotation, _process_one, run_evaluation


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_load_annotation_has_try_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_load_annotation_has_open_call_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_open = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "open" for c in calls
    )
    assert has_open


def test_ast_process_one_has_perf_counter_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_perf = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "perf_counter" for c in calls
    )
    assert has_perf


def test_ast_process_one_multiple_returns_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 3


def test_ast_process_one_has_try_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_run_evaluation_has_multiple_for_batch48():
    """run_evaluation 至少 3 个 top-level for（documents / expected_failures / public_per_doc）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) >= 3


def test_ast_run_evaluation_has_with_open_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    withs = [n for n in func.body if isinstance(n, ast.With)]
    assert len(withs) >= 1


def test_ast_run_evaluation_has_json_dump_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_dump = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "dump" for c in calls
    )
    assert has_dump


def test_ast_run_evaluation_returns_dict_batch48():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Name)
    assert returns[0].value.id == "report"


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：__future__ / json / time / Path / Any / app.pipeline / REPORT_VERSION / annotation_metrics / metrics / report = 10。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 10


def test_ast_module_top_level_assign_count_batch48():
    """模块顶部 Assign：__all__ = 1。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 1


# ---------- forbidden tokens 第一百二十五批 ----------

def _src() -> str:
    return inspect.getsource(runner_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_popen_batch48():
    assert ".popen(" not in _src()
    assert "Popen(" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()


def test_source_no_async_def_batch48():
    assert "async def" not in _src()


def test_source_no_await_batch48():
    assert "await " not in _src()
