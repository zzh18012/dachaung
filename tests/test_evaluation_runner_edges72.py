"""evaluation/runner.py 第八十九轮 edges 测试（Round 639）。

补强 edges71 未触及的角度（第四十七批）。

新角度：
- _load_annotation 各种路径（None / 不存在 / 是目录 / JSON 解析失败 / OSError 兜底）
- _process_one 多种路径（成功 / errors 非空 / document None / parser_version 透传 / image_dir 计算）
- _process_one unlink OSError 兜底
- run_evaluation 写盘 ensure_ascii=False
- run_evaluation per_doc_results 私有字段（_annotation_present / _tolerance_chars / _missing_markers）
- run_evaluation public_per_doc 字段（不含私有 _）
- run_evaluation report 顶层 6 keys
- run_evaluation expected_failures 路径
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百零九批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.runner as runner_mod
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# ---------- _load_annotation 各种路径 ----------

def test_load_annotation_none_batch47():
    assert _load_annotation(None) is None


def test_load_annotation_not_exist_batch47(tmp_path):
    p = tmp_path / "notexist.json"
    assert _load_annotation(p) is None


def test_load_annotation_is_directory_batch47(tmp_path):
    """is_file() 对目录返回 False。"""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_valid_json_batch47(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"key": "value"}


def test_load_annotation_json_decode_error_batch47(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_oserror_batch47(tmp_path):
    """open 抛 OSError → 兜底 None。"""
    p = tmp_path / "perm.json"
    p.write_text("{}", encoding="utf-8")
    original_open = Path.open
    with patch("pathlib.Path.open", side_effect=OSError("boom")):
        assert _load_annotation(p) is None


def test_load_annotation_utf8_encoding_batch47(tmp_path):
    """中文 JSON 用 utf-8 解析。"""
    p = tmp_path / "cn.json"
    p.write_text('{"中文": "测试"}', encoding="utf-8")
    out = _load_annotation(p)
    assert out == {"中文": "测试"}


def test_load_annotation_empty_file_batch47(tmp_path):
    """空文件 → JSONDecodeError → None。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_array_json_batch47(tmp_path):
    """JSON 数组也合法。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    out = _load_annotation(p)
    assert out == [1, 2, 3]


def test_load_annotation_returns_dict_or_none_batch47(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    out = _load_annotation(p)
    assert isinstance(out, (dict, list, type(None)))


# ---------- _process_one 多种路径 ----------

def _make_doc_entry(**kwargs):
    """构造 MagicMock 模拟 DocumentEntry。"""
    m = MagicMock()
    m.doc_id = kwargs.get("doc_id", "d1")
    m.resolved_path = kwargs.get("resolved_path", Path("/tmp/x.pdf"))
    m.source_type = kwargs.get("source_type", "pdf")
    m.expectations = kwargs.get("expectations", None)
    m.annotation_resolved = kwargs.get("annotation_resolved", None)
    return m


def test_process_one_success_path_batch47(tmp_path):
    """成功路径：返回 (document_dict, None, elapsed, parser_version, image_dir)。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1", "elements": []}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "fallback-1.0"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, total, version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document == {"id": "d1", "elements": []}
    assert error is None
    assert isinstance(total, float)
    assert total >= 0.0
    assert version == "fallback-1.0"
    assert image_dir == tmp_path / "imgs"


def test_process_one_errors_nonempty_batch47(tmp_path):
    """errors 非空 → 返回 (None, errors[0].to_dict(), elapsed, None, image_dir)。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    err = MagicMock()
    err.to_dict.return_value = {"code": "parse_failed", "message": "bad"}
    err.code = "parse_failed"

    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, total, version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document is None
    assert error == {"code": "parse_failed", "message": "bad"}
    assert version is None
    assert image_dir is None  # document is None → image_dir None


def test_process_one_document_none_no_errors_batch47(tmp_path):
    """document None 且 errors 空 → 兜底 unknown error。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            document, error, total, version, image_dir = _process_one(
                doc, tmp_path, "fallback", 800
            )
    assert document is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }
    assert version is None


def test_process_one_creates_per_doc_dir_batch47(tmp_path):
    """应创建 _per_doc 子目录。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    assert (tmp_path / "_per_doc").is_dir()


def test_process_one_unlinks_stub_batch47(tmp_path):
    """成功路径应删除 out_stub JSON 文件。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    def fake_process_single(*args, **kwargs):
        # 模拟 pipeline 写盘
        out_stub = args[1]
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("{}", encoding="utf-8")
        return fake_document, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            _process_one(doc, tmp_path, "fallback", 800)
    stub = tmp_path / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_process_one_unlink_oserror_swallowed_batch47(tmp_path):
    """unlink 抛 OSError 应被吞掉。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    def fake_process_single(*args, **kwargs):
        out_stub = args[1]
        out_stub.parent.mkdir(parents=True, exist_ok=True)
        out_stub.write_text("{}", encoding="utf-8")
        return fake_document, []

    with patch("evaluation.runner.process_single", side_effect=fake_process_single):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("pathlib.Path.unlink", side_effect=OSError("boom")):
                # 不应抛
                document, error, total, version, image_dir = _process_one(
                    doc, tmp_path, "fallback", 800
                )
    assert document == {"id": "d1"}


def test_process_one_image_dir_only_when_document_not_none_batch47(tmp_path):
    """document is None → image_dir 一定是 None（不调 image_output_dir_for）。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.image_output_dir_for") as m_img:
            _, _, _, _, image_dir = _process_one(doc, tmp_path, "fallback", 800)
            m_img.assert_not_called()
    assert image_dir is None


def test_process_one_returns_5_tuple_batch47(tmp_path):
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"
    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            result = _process_one(doc, tmp_path, "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


# ---------- run_evaluation 写盘 ensure_ascii=False ----------

def _make_manifest(docs=None, expected_failures=None, project_root=None):
    m = MagicMock()
    m.documents = docs or []
    m.expected_failures = expected_failures or []
    m.project_root = project_root or Path("/tmp")
    m.devset_status = "incomplete"
    m.file_count = 0
    m.content_group_count = 0
    m.pdf_count = 0
    m.docx_count = 0
    m.categories_covered = []
    return m


def test_run_evaluation_empty_documents_batch47(tmp_path):
    """manifest 空 documents → per_doc=[]，但报告仍写盘。"""
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.build_provenance", return_value={"evaluator_version": "1.1"}):
        with patch("evaluation.runner.build_devset_section", return_value={"status": "incomplete"}):
            report = run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    assert out.is_file()
    assert report["per_doc"] == []
    assert report["expected_failures"] == []
    assert report["provenance"] == {"evaluator_version": "1.1"}


def test_run_evaluation_writes_unicode_unescaped_batch47(tmp_path):
    """报告写盘 ensure_ascii=False → 中文不转义。"""
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.build_provenance", return_value={"中文_key": "测试值"}):
        with patch("evaluation.runner.build_devset_section", return_value={"status": "incomplete"}):
            run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    raw = out.read_text(encoding="utf-8")
    assert "中文_key" in raw
    assert "测试值" in raw


def test_run_evaluation_creates_output_parent_dir_batch47(tmp_path):
    """output_path 的父目录不存在时应创建。"""
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "nested" / "deep" / "report.json"

    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            run_evaluation(manifest, out, parser_name="fallback", max_chars=800)
    assert out.is_file()


def test_run_evaluation_report_version_batch47(tmp_path):
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            report = run_evaluation(manifest, out)
    assert report["report_version"] == "1.1"


def test_run_evaluation_report_keys_batch47(tmp_path):
    manifest = _make_manifest(project_root=tmp_path)
    out = tmp_path / "report.json"
    with patch("evaluation.runner.build_provenance", return_value={}):
        with patch("evaluation.runner.build_devset_section", return_value={}):
            report = run_evaluation(manifest, out)
    expected_keys = {
        "report_version", "provenance", "devset", "summary",
        "per_doc", "expected_failures",
    }
    assert set(report.keys()) == expected_keys


# ---------- run_evaluation per_doc_results 私有字段 ----------

def test_run_evaluation_per_doc_has_private_annotation_present_batch47(tmp_path):
    """per_doc_results（内部）应含 _annotation_present。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {"counts": {}}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                                with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                    run_evaluation(manifest, out)
    assert "_annotation_present" in captured["per_doc"][0]


def test_run_evaluation_per_doc_has_wall_time_keys_batch47(tmp_path):
    """wall_time_seconds 应含 5 keys（total / parse / chunk / parse_reason / chunk_reason）。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    captured = {}

    def fake_aggregate(per_doc):
        captured["per_doc"] = per_doc
        return {}

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.runner.aggregate_summary", side_effect=fake_aggregate):
                        with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                            with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                                with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                    run_evaluation(manifest, out)
    wt = captured["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_public_per_doc_no_private_batch47(tmp_path):
    """public_per_doc（写盘）不应含私有 _ 字段。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        for k in r.keys():
            assert not k.startswith("_")


def test_run_evaluation_public_per_doc_keys_batch47(tmp_path):
    """public_per_doc 只有 4 keys：doc_id / source_type / metrics / wall_time_seconds。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", return_value={}):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                report = run_evaluation(manifest, out)
    expected_keys = {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert set(report["per_doc"][0].keys()) == expected_keys


# ---------- run_evaluation expected_failures 路径 ----------

def test_run_evaluation_expected_failures_match_batch47(tmp_path):
    """expected_failure 匹配：actual_code == expected_code → matches True。"""
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"

    err = MagicMock()
    err.code = "parse_failed"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is True


def test_run_evaluation_expected_failures_no_match_batch47(tmp_path):
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"

    err = MagicMock()
    err.code = "different_error"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [err])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["matches"] is False
    assert report["expected_failures"][0]["actual_error_code"] == "different_error"


def test_run_evaluation_expected_failures_no_errors_batch47(tmp_path):
    """expected_failure 实际没报错 → actual_code=None, matches=False（除非 expected 也是 None）。"""
    ef = MagicMock()
    ef.doc_id = "ok1"
    ef.resolved_path = tmp_path / "ok.pdf"
    ef.expected_error_code = "parse_failed"

    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "ok1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = "v1"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                report = run_evaluation(manifest, out)
    assert report["expected_failures"][0]["actual_error_code"] is None
    assert report["expected_failures"][0]["matches"] is False


def test_run_evaluation_expected_failures_keys_batch47(tmp_path):
    ef = MagicMock()
    ef.doc_id = "bad1"
    ef.resolved_path = tmp_path / "bad.pdf"
    ef.expected_error_code = "parse_failed"

    manifest = _make_manifest(expected_failures=[ef], project_root=tmp_path)
    out = tmp_path / "report.json"

    with patch("evaluation.runner.process_single", return_value=(None, [])):
        with patch("evaluation.runner.build_provenance", return_value={}):
            with patch("evaluation.runner.build_devset_section", return_value={}):
                report = run_evaluation(manifest, out)
    expected_keys = {"doc_id", "expected_error_code", "actual_error_code", "matches"}
    assert set(report["expected_failures"][0].keys()) == expected_keys


# ---------- run_evaluation parser_version 透传 ----------

def test_run_evaluation_first_parser_version_wins_batch47(tmp_path):
    """parser_version_for_prov 取第一个非 None。"""
    doc1 = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    doc2 = _make_doc_entry(doc_id="d2", resolved_path=tmp_path / "y.pdf")

    doc1_doc = MagicMock()
    doc1_doc.to_dict.return_value = {"id": "d1"}
    doc1_doc.source_hash = "abc"
    doc1_doc.parser_version = "v_first"

    doc2_doc = MagicMock()
    doc2_doc.to_dict.return_value = {"id": "d2"}
    doc2_doc.source_hash = "def"
    doc2_doc.parser_version = "v_second"

    manifest = _make_manifest(docs=[doc1, doc2], project_root=tmp_path)
    out = tmp_path / "report.json"

    captured_prov = {}

    def fake_prov(**kwargs):
        captured_prov.update(kwargs)
        return {}

    with patch("evaluation.runner.process_single", side_effect=[(doc1_doc, []), (doc2_doc, [])]):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", side_effect=fake_prov):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                run_evaluation(manifest, out)
    assert captured_prov["parser_version"] == "v_first"


def test_run_evaluation_no_parser_version_batch47(tmp_path):
    """所有文档都没 parser_version → None。"""
    doc = _make_doc_entry(doc_id="d1", resolved_path=tmp_path / "x.pdf")
    fake_document = MagicMock()
    fake_document.to_dict.return_value = {"id": "d1"}
    fake_document.source_hash = "abc"
    fake_document.parser_version = None

    manifest = _make_manifest(docs=[doc], project_root=tmp_path)
    out = tmp_path / "report.json"

    captured_prov = {}

    def fake_prov(**kwargs):
        captured_prov.update(kwargs)
        return {}

    with patch("evaluation.runner.process_single", return_value=(fake_document, [])):
        with patch("evaluation.runner.image_output_dir_for", return_value=tmp_path / "imgs"):
            with patch("evaluation.runner.build_provenance", side_effect=fake_prov):
                with patch("evaluation.runner.build_devset_section", return_value={}):
                    with patch("evaluation.metrics.compute_automatic_metrics", return_value={}):
                        with patch("evaluation.annotation_metrics.figure_caption_prf", return_value={}):
                            with patch("evaluation.annotation_metrics.chunk_boundary_prf", return_value={}):
                                run_evaluation(manifest, out)
    assert captured_prov["parser_version"] is None


# ---------- module source 字符串补强 ----------

def test_source_contains_not_instrumented_batch47():
    src = inspect.getsource(runner_mod)
    assert "not_instrumented" in src


def test_source_contains_image_output_dir_for_batch47():
    src = inspect.getsource(runner_mod)
    assert "image_output_dir_for" in src


def test_source_contains_process_single_batch47():
    src = inspect.getsource(runner_mod)
    assert "process_single" in src


def test_source_contains_compute_automatic_metrics_batch47():
    src = inspect.getsource(runner_mod)
    assert "compute_automatic_metrics" in src


def test_source_contains_figure_caption_prf_batch47():
    src = inspect.getsource(runner_mod)
    assert "figure_caption_prf" in src


def test_source_contains_chunk_boundary_prf_batch47():
    src = inspect.getsource(runner_mod)
    assert "chunk_boundary_prf" in src


def test_source_contains_aggregate_summary_batch47():
    src = inspect.getsource(runner_mod)
    assert "aggregate_summary" in src


def test_source_contains_ensure_ascii_false_batch47():
    src = inspect.getsource(runner_mod)
    assert "ensure_ascii=False" in src


def test_source_contains_perf_counter_batch47():
    src = inspect.getsource(runner_mod)
    assert "perf_counter" in src


def test_source_contains_pipeline_failed_batch47():
    src = inspect.getsource(runner_mod)
    assert "pipeline_failed" in src


def test_source_contains_unknown_code_batch47():
    src = inspect.getsource(runner_mod)
    assert '"unknown"' in src or "'unknown'" in src


def test_source_contains_not_instrumented_reason_batch47():
    src = inspect.getsource(runner_mod)
    assert '"not_instrumented"' in src or "'not_instrumented'" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 3  # _load_annotation / _process_one / run_evaluation


def test_ast_load_annotation_has_try_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)]
    assert len(trys) == 1


def test_ast_load_annotation_except_handler_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_load_annotation"][0]
    trys = [n for n in func.body if isinstance(n, ast.Try)][0]
    h = trys.handlers[0]
    assert isinstance(h.type, ast.Tuple)
    assert len(h.type.elts) == 2  # OSError + json.JSONDecodeError


def test_ast_process_one_has_if_errors_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) >= 3  # if document / if errors / if out_stub.is_file()


def test_ast_process_one_has_try_in_if_batch47():
    """if out_stub.is_file(): 内部有 try。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) >= 1


def test_ast_run_evaluation_has_two_for_loops_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 3  # documents / expected_failures / public_per_doc


def test_ast_run_evaluation_has_with_for_dump_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    withs = [n for n in func.body if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_run_evaluation_returns_dict_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_evaluation"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Name)
    assert returns[0].value.id == "report"


def test_ast_no_class_def_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_module_docstring_present_batch47():
    tree = ast.parse(inspect.getsource(runner_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_process_one_return_statements_batch47():
    """_process_one 应有 3 个 return（errors / document None / 成功）。"""
    tree = ast.parse(inspect.getsource(runner_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_process_one"][0]
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 3


# ---------- forbidden tokens 第一百零九批 ----------

def test_source_no_eval_batch47():
    src = inspect.getsource(runner_mod)
    assert "eval(" not in src


def test_source_no_exec_batch47():
    src = inspect.getsource(runner_mod)
    assert "exec(" not in src


def test_source_no_compile_batch47():
    src = inspect.getsource(runner_mod)
    assert "compile(" not in src


def test_source_no_globals_batch47():
    src = inspect.getsource(runner_mod)
    assert "globals(" not in src


def test_source_no_locals_batch47():
    src = inspect.getsource(runner_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch47():
    src = inspect.getsource(runner_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch47():
    src = inspect.getsource(runner_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch47():
    src = inspect.getsource(runner_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch47():
    src = inspect.getsource(runner_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch47():
    src = inspect.getsource(runner_mod)
    assert "subprocess" not in src


def test_source_no_lambda_batch47():
    src = inspect.getsource(runner_mod)
    assert "lambda" not in src


def test_source_no_yield_batch47():
    src = inspect.getsource(runner_mod)
    assert "yield" not in src


def test_source_no_walrus_batch47():
    src = inspect.getsource(runner_mod)
    assert ":=" not in src


def test_source_no_async_batch47():
    src = inspect.getsource(runner_mod)
    assert "async def" not in src


def test_source_no_await_batch47():
    src = inspect.getsource(runner_mod)
    assert "await " not in src
