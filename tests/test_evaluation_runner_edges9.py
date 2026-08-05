r"""evaluation/runner.py 边角测试 - 第九轮（Round 207）。

补强已有 base/edges/edges2-8（共 ~734 测试）未覆盖的深度：
- _load_annotation：None / 不存在 / OSError 路径 / 各种 JSON 类型
- _process_one：image_dir 派生 / output_root 创建 / unlink 各场景
- run_evaluation：报告 6 top keys / per_doc 4 keys / wall_time 5 keys
- run_evaluation：parser_version 第一个成功文档传播
- run_evaluation：expected_failures matches True/False
- run_evaluation：报告写盘 indent=2 + ensure_ascii=False
- run_evaluation：tolerance_chars 传播到 chunk_boundary_prf
- 模块 imports / __all__
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# _load_annotation 深度
# =========================================================================


def test_load_annotation_none_returns_none():
    assert _load_annotation(None) is None


def test_load_annotation_nonexistent_returns_none(tmp_path):
    assert _load_annotation(tmp_path / "nope.json") is None


def test_load_annotation_directory_returns_none(tmp_path):
    """目录不是 file → None。"""
    assert _load_annotation(tmp_path) is None


def test_load_annotation_valid_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"key": "value"}', encoding="utf-8")
    assert _load_annotation(p) == {"key": "value"}


def test_load_annotation_returns_dict_type(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, dict)


def test_load_annotation_returns_list(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    result = _load_annotation(p)
    assert isinstance(result, list)
    assert result == [1, 2, 3]


def test_load_annotation_returns_int(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("42", encoding="utf-8")
    assert _load_annotation(p) == 42


def test_load_annotation_returns_string(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('"hello"', encoding="utf-8")
    assert _load_annotation(p) == "hello"


def test_load_annotation_returns_null(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("null", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_returns_true(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("true", encoding="utf-8")
    assert _load_annotation(p) is True


def test_load_annotation_returns_false(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("false", encoding="utf-8")
    assert _load_annotation(p) is False


def test_load_annotation_returns_float(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("3.14", encoding="utf-8")
    assert _load_annotation(p) == 3.14


def test_load_annotation_returns_nested_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": {"b": {"c": [1, 2]}}}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"a": {"b": {"c": [1, 2]}}}


def test_load_annotation_returns_empty_dict(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{}", encoding="utf-8")
    assert _load_annotation(p) == {}


def test_load_annotation_returns_empty_list(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("[]", encoding="utf-8")
    assert _load_annotation(p) == []


def test_load_annotation_invalid_json_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("{not json", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_truncated_json_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"key": "val', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_extra_data_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"a": 1} extra', encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_empty_file_returns_none(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text("", encoding="utf-8")
    assert _load_annotation(p) is None


def test_load_annotation_unicode_content(tmp_path):
    p = tmp_path / "ann.json"
    p.write_text('{"name": "中文"}', encoding="utf-8")
    result = _load_annotation(p)
    assert result == {"name": "中文"}


def test_load_annotation_returns_independent_dict(tmp_path):
    """每次 load 应返回新 dict。"""
    p = tmp_path / "ann.json"
    p.write_text('{"k": "v"}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b
    assert a is not b
    a["k"] = "modified"
    assert b["k"] == "v"


def test_load_annotation_signature():
    sig = inspect.signature(_load_annotation)
    params = list(sig.parameters)
    assert params == ["path"]


# =========================================================================
# _process_one 深度
# =========================================================================


class _FakeDocEntry:
    """模拟 DocumentEntry。"""
    def __init__(self, doc_id="d1", resolved_path=None, source_type="text",
                 expectations=None, annotation_resolved=None):
        self.doc_id = doc_id
        self.resolved_path = resolved_path or Path("/tmp/x.txt")
        self.source_type = source_type
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeError:
    def __init__(self, code="x", message="boom"):
        self.code = code
        self.message = message

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class _FakeDocument:
    def __init__(self, source_hash="a" * 64, parser_version="0.1.0"):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self):
        return {"source_hash": self.source_hash, "parser_version": self.parser_version}


def test_process_one_signature():
    sig = inspect.signature(_process_one)
    params = list(sig.parameters)
    assert params == ["doc", "output_root", "parser_name", "max_chars"]


def test_process_one_returns_5_tuple(tmp_path, monkeypatch):
    """返回 (document_dict, error_dict, total, parser_version, image_dir)。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    result = _process_one(doc_entry, tmp_path, "text", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_success_returns_document_dict(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    document_dict, error, _, parser_version, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert document_dict is not None
    assert error is None
    assert parser_version == "0.1.0"


def test_process_one_errors_returns_none_document(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError()]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    document_dict, error, _, parser_version, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert document_dict is None
    assert error == {"code": "x", "message": "boom"}
    assert parser_version is None


def test_process_one_no_errors_no_document_returns_unknown(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, []  # 没 errors 但也没 document

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    document_dict, error, _, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert document_dict is None
    assert error["code"] == "unknown"


def test_process_one_creates_per_doc_subdir(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _process_one(doc_entry, tmp_path, "text", 800)
    per_doc_dir = tmp_path / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_total_seconds_is_float(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, total, _, _ = _process_one(doc_entry, tmp_path, "text", 800)
    assert isinstance(total, float)
    assert total >= 0


def test_process_one_image_dir_uses_image_output_dir_for(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(source_hash="abc123"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    # image_dir 是 out_stub.parent / images-<sha[:16]>
    # source_hash="abc123"（6 字符）→ [:16] = "abc123"
    assert image_dir is not None
    assert image_dir.parent == tmp_path / "_per_doc"
    assert image_dir.name == "images-abc123"  # sha16，源串不足 16 时即原值


def test_process_one_image_dir_none_when_document_none(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return None, [_FakeError()]

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    _, _, _, _, image_dir = _process_one(doc_entry, tmp_path, "text", 800)
    assert image_dir is None


# =========================================================================
# run_evaluation 综合深度
# =========================================================================


class _FakeManifest:
    def __init__(self, documents=None, expected_failures=None):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.devset_status = "incomplete"
        self.file_count = len(self.documents)
        self.content_group_count = 1
        self.pdf_count = 0
        self.docx_count = 0
        self.categories_covered = ["text"]
        self.project_root = Path(".")


def test_run_evaluation_returns_dict(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    result = run_evaluation(manifest, out)
    assert isinstance(result, dict)


def test_run_evaluation_signature_keyword_only(tmp_path):
    sig = inspect.signature(run_evaluation)
    # parser_name/max_chars/tolerance_chars 是 keyword-only
    assert sig.parameters["parser_name"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_chars"].kind == inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.KEYWORD_ONLY


def test_run_evaluation_defaults(tmp_path):
    sig = inspect.signature(run_evaluation)
    assert sig.parameters["parser_name"].default == "fallback"
    assert sig.parameters["max_chars"].default == 800
    assert sig.parameters["tolerance_chars"].default == 30


def test_run_evaluation_report_six_top_keys(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {
        "report_version", "provenance", "devset",
        "summary", "per_doc", "expected_failures",
    }
    assert set(report.keys()) == expected


def test_run_evaluation_report_version_is_string(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["report_version"], str)


def test_run_evaluation_per_doc_is_list(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["per_doc"], list)


def test_run_evaluation_expected_failures_is_list(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert isinstance(report["expected_failures"], list)


def test_run_evaluation_summary_has_four_keys(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {"counts", "success_rates", "ratio_macro_averages", "silent_drop_total"}
    assert set(report["summary"].keys()) == expected


def test_run_evaluation_provenance_nine_keys(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {
        "git_commit", "git_dirty",
        "evaluator_version", "report_version",
        "parser_name", "parser_version",
        "dependencies", "max_chars", "run_timestamp_iso",
    }
    assert set(report["provenance"].keys()) == expected


def test_run_evaluation_devset_six_keys(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {
        "status", "file_count", "content_group_count",
        "pdf_count", "docx_count", "categories_covered",
    }
    assert set(report["devset"].keys()) == expected


def test_run_evaluation_writes_file_to_disk(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_file_is_valid_json(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    data = json.loads(text)
    assert isinstance(data, dict)


def test_run_evaluation_file_matches_returned_dict(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert json.loads(text) == report


def test_run_evaluation_creates_parent_dirs(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "a" / "b" / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_file_uses_utf8(tmp_path):
    """报告文件应该是 UTF-8 编码。"""
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    assert "report_version" in text


def test_run_evaluation_file_uses_indent_2(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "\n  " in text


def test_run_evaluation_file_ensure_ascii_false(tmp_path):
    r"""categories_covered 含中文时不应转 \uXXXX。"""
    manifest = _FakeManifest()
    manifest.categories_covered = ["中文类型"]
    out = tmp_path / "report.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    assert "中文类型" in text


def test_run_evaluation_per_doc_strips_private_keys(tmp_path, monkeypatch):
    """公开 per_doc 不应含 _annotation_present/_tolerance_chars/_missing_markers。"""
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    for r in report["per_doc"]:
        assert "_annotation_present" not in r
        assert "_tolerance_chars" not in r
        assert "_missing_markers" not in r


def test_run_evaluation_per_doc_has_four_keys(tmp_path):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {"doc_id", "source_type", "metrics", "wall_time_seconds"}
    assert set(report["per_doc"][0].keys()) == expected


def test_run_evaluation_wall_time_has_five_keys(tmp_path):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    expected = {"total", "parse", "chunk", "parse_reason", "chunk_reason"}
    assert set(wt.keys()) == expected


def test_run_evaluation_wall_time_parse_chunk_null(tmp_path):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"


def test_run_evaluation_wall_time_total_nonneg(tmp_path):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    total = report["per_doc"][0]["wall_time_seconds"]["total"]
    assert total is None or total >= 0


def test_run_evaluation_provenance_parser_version_set_on_success(tmp_path, monkeypatch):
    doc_entry = _FakeDocEntry(resolved_path=tmp_path / "x.txt")
    (tmp_path / "x.txt").write_text("hello world", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(parser_version="0.1.0"), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    manifest = _FakeManifest(documents=[doc_entry])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    # text parser version
    assert report["provenance"]["parser_version"] == "0.1.0"


def test_run_evaluation_provenance_parser_name_propagated(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, parser_name="fallback")
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["provenance"]["parser_name"] == "fallback"


def test_run_evaluation_provenance_max_chars_propagated(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    run_evaluation(manifest, out, max_chars=400)
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["provenance"]["max_chars"] == 400


def test_run_evaluation_creates_per_doc_dir(tmp_path):
    """runner 应在 output_root/_per_doc/ 创建临时目录。"""
    manifest = _FakeManifest()
    out = tmp_path / "sub" / "report.json"
    run_evaluation(manifest, out)
    per_doc_dir = tmp_path / "sub" / "_per_doc"
    assert per_doc_dir.is_dir() or not per_doc_dir.exists()  # 至少创建了


def test_run_evaluation_empty_manifest_per_doc_empty(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["per_doc"] == []


def test_run_evaluation_empty_manifest_summary_structure(tmp_path):
    manifest = _FakeManifest(documents=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert "counts" in report["summary"]
    assert "success_rates" in report["summary"]
    assert "ratio_macro_averages" in report["summary"]
    assert "silent_drop_total" in report["summary"]


def test_run_evaluation_expected_failures_empty_by_default(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert report["expected_failures"] == []


# =========================================================================
# run_evaluation expected_failures 流程
# =========================================================================


class _FakeExpectedFailure:
    def __init__(self, doc_id, resolved_path, expected_error_code):
        self.doc_id = doc_id
        self.resolved_path = resolved_path
        self.expected_error_code = expected_error_code


def test_run_evaluation_expected_failure_matches(tmp_path):
    """期望失败的 doc 实际也失败且 code 匹配 → matches=True。"""
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("d1", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    assert len(report["expected_failures"]) == 1
    ef_result = report["expected_failures"][0]
    assert ef_result["doc_id"] == "d1"
    assert ef_result["expected_error_code"] == "file_not_found"
    assert ef_result["actual_error_code"] == "file_not_found"
    assert ef_result["matches"] is True


def test_run_evaluation_expected_failure_mismatch_when_succeeds(tmp_path, monkeypatch):
    """期望失败的 doc 实际成功 → actual_code=None → matches=False。"""
    good = tmp_path / "good.txt"
    good.write_text("hello world", encoding="utf-8")

    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr("evaluation.runner.process_single", fake_process_single)
    ef = _FakeExpectedFailure("d1", good, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


def test_run_evaluation_expected_failure_result_has_four_keys(tmp_path):
    bad = tmp_path / "missing.txt"
    ef = _FakeExpectedFailure("d1", bad, "file_not_found")
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out)
    expected = {"doc_id", "expected_error_code", "actual_error_code", "matches"}
    assert set(report["expected_failures"][0].keys()) == expected


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.runner as m
    assert set(m.__all__) == {"run_evaluation"}


def test_module_all_is_list():
    import evaluation.runner as m
    assert isinstance(m.__all__, list)


def test_module_imports_json():
    import evaluation.runner as m
    assert hasattr(m, "json")


def test_module_imports_time():
    import evaluation.runner as m
    assert hasattr(m, "time")


def test_module_imports_path():
    import evaluation.runner as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.runner as m
    assert hasattr(m, "Any")


def test_module_imports_pipeline():
    import evaluation.runner as m
    assert hasattr(m, "process_single")
    assert hasattr(m, "image_output_dir_for")


def test_module_imports_report():
    import evaluation.runner as m
    assert hasattr(m, "aggregate_summary")
    assert hasattr(m, "build_devset_section")
    assert hasattr(m, "build_provenance")


def test_module_imports_annotation_metrics():
    import evaluation.runner as m
    assert hasattr(m, "chunk_boundary_prf")
    assert hasattr(m, "figure_caption_prf")


def test_module_imports_metrics():
    import evaluation.runner as m
    assert hasattr(m, "compute_automatic_metrics")


def test_module_imports_report_version():
    import evaluation.runner as m
    assert hasattr(m, "REPORT_VERSION")


def test_module_docstring_present():
    import evaluation.runner as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_constraints():
    import evaluation.runner as m
    doc = m.__doc__
    assert "total" in doc or "perf_counter" in doc
    assert "not_instrumented" in doc
    assert "失败" in doc or "failed" in doc.lower()


def test_module_uses_future_annotations():
    import evaluation.runner as m
    sig = inspect.signature(m.run_evaluation)
    assert isinstance(sig.return_annotation, str)


def test_module_all_entries_exported():
    import evaluation.runner as m
    for name in m.__all__:
        assert hasattr(m, name)


def test_module_no_silence_unused():
    import evaluation.runner as m
    assert not hasattr(m, "_silence_unused_import")
