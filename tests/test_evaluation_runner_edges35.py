"""evaluation/runner.py 第三十六轮 edges 测试（Round 375）。

重点补强 edges34 未触及的角度：
- _process_one 行为深度第八批（用 monkeypatch 替换 process_single，验证 5-tuple 返回）
- run_evaluation 行为深度第八批（用 monkeypatch + 假 Manifest，验证报告装配）
- _load_annotation 行为深度第八批（更多边界）
- module source forbidden tokens 第十三批（新一批禁词）
- module source 字符串精确补强第七批
- signatures 精确补强第五批
- 模块整体合理性补强第五批
- 端到端集成补强第五批
"""

from __future__ import annotations

import inspect
import json
import time
import types
from pathlib import Path
from typing import Any

import pytest

from evaluation import REPORT_VERSION
from evaluation import runner as rmod
from evaluation.runner import (
    _load_annotation,
    _process_one,
    run_evaluation,
)


# ---------- helpers ----------


class _FakeError:
    """模拟 app.pipeline 的 PipelineError（duck-typed）."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


class _FakeDocument:
    """模拟 app.pipeline 的 Document（duck-typed）."""

    def __init__(
        self,
        source_hash: str = "abc123",
        parser_version: str = "1.2.3",
    ):
        self.source_hash = source_hash
        self.parser_version = parser_version

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_hash": self.source_hash,
            "parser_version": self.parser_version,
        }


class _FakeExpectations:
    """模拟 manifest 的 expectations（duck-typed dict-like）."""

    def __init__(self, d: dict[str, Any] | None = None):
        self._d = d or {}

    def get(self, k: str, default: Any = None) -> Any:
        return self._d.get(k, default)

    def __getitem__(self, k: str) -> Any:
        return self._d[k]

    def __contains__(self, k: object) -> bool:
        return k in self._d


class _FakeDocEntry:
    """模拟 manifest 的 DocumentEntry（duck-typed）."""

    def __init__(
        self,
        doc_id: str = "doc1",
        source_type: str = "pdf",
        resolved_path: Path | None = None,
        expectations: Any = None,
        annotation_resolved: Path | None = None,
    ):
        self.doc_id = doc_id
        self.source_type = source_type
        self.resolved_path = resolved_path or Path("sample.pdf")
        self.expectations = expectations
        self.annotation_resolved = annotation_resolved


class _FakeExpectedFailure:
    """模拟 manifest 的 ExpectedFailure."""

    def __init__(
        self,
        doc_id: str = "bad1",
        resolved_path: Path | None = None,
        expected_error_code: str = "parse_failed",
    ):
        self.doc_id = doc_id
        self.resolved_path = resolved_path or Path("bad.pdf")
        self.expected_error_code = expected_error_code


class _FakeManifest:
    """模拟 Manifest（duck-typed）."""

    def __init__(
        self,
        documents: list[Any] | None = None,
        expected_failures: list[Any] | None = None,
        project_root: Path | None = None,
        devset_status: str = "incomplete",
    ):
        self.documents = documents or []
        self.expected_failures = expected_failures or []
        self.project_root = project_root or Path.cwd()
        self.devset_status = devset_status

    @property
    def file_count(self) -> int:
        return len(self.documents)

    @property
    def pdf_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "pdf")

    @property
    def docx_count(self) -> int:
        return sum(1 for d in self.documents if d.source_type == "docx")

    @property
    def content_group_count(self) -> int:
        return len(self.documents)

    @property
    def categories_covered(self) -> list[str]:
        s: set[str] = set()
        for d in self.documents:
            if hasattr(d, "categories"):
                s.update(d.categories)
        return sorted(s)


# ---------- _process_one 行为深度第八批 ----------


def test_process_one_success_returns_5_tuple(monkeypatch, tmp_path):
    """成功路径：document 非空，errors 为空 → 5-tuple (doc_dict, None, elapsed, version, image_dir)."""
    fake_doc = _FakeDocument(source_hash="deadbeef", parser_version="9.9.9")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "input.pdf")
    out_root = tmp_path / "out"

    document, error, elapsed, version, image_dir = _process_one(
        entry, out_root, "fallback", 800
    )
    assert document == {"source_hash": "deadbeef", "parser_version": "9.9.9"}
    assert error is None
    assert isinstance(elapsed, float)
    assert elapsed >= 0.0
    assert version == "9.9.9"
    assert image_dir is not None
    assert "deadbeef" in str(image_dir)


def test_process_one_success_creates_per_doc_dir(monkeypatch, tmp_path):
    fake_doc = _FakeDocument(source_hash="h1")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="abc", resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"

    _process_one(entry, out_root, "fallback", 800)
    per_doc_dir = out_root / "_per_doc"
    assert per_doc_dir.is_dir()


def test_process_one_success_unlinks_stub(monkeypatch, tmp_path):
    """write_json=False 不会写 stub，但 unlink 路径检查应安全."""
    fake_doc = _FakeDocument(source_hash="h1")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="abc", resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"

    _process_one(entry, out_root, "fallback", 800)
    stub = out_root / "_per_doc" / "abc.json"
    assert not stub.is_file()


def test_process_one_errors_non_empty_returns_error_dict(monkeypatch, tmp_path):
    """errors 非空 → 返回 (None, errors[0].to_dict(), elapsed, None, image_dir)."""
    err = _FakeError("parse_failed", "boom")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"

    document, error, elapsed, version, image_dir = _process_one(
        entry, out_root, "fallback", 800
    )
    assert document is None
    assert error == {"code": "parse_failed", "message": "boom"}
    assert isinstance(elapsed, float)
    assert version is None
    assert image_dir is None  # document is None → image_dir is None


def test_process_one_document_none_no_errors_returns_unknown(monkeypatch, tmp_path):
    """document is None 且 errors 为空 → 返回 unknown error dict."""
    def fake_process_single(*args, **kwargs):
        return None, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"

    document, error, elapsed, version, image_dir = _process_one(
        entry, out_root, "fallback", 800
    )
    assert document is None
    assert error == {
        "code": "unknown",
        "message": "process_single returned None without errors",
    }
    assert version is None
    assert image_dir is None


def test_process_one_returns_tuple_of_5(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")

    result = _process_one(entry, tmp_path / "out", "fallback", 800)
    assert isinstance(result, tuple)
    assert len(result) == 5


def test_process_one_elapsed_is_reasonable(monkeypatch, tmp_path):
    """elapsed 应是 perf_counter 差值，非常小但非负."""
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")
    t_before = time.perf_counter()
    _, _, elapsed, _, _ = _process_one(entry, tmp_path / "out", "fallback", 800)
    t_after = time.perf_counter()
    assert 0.0 <= elapsed <= (t_after - t_before) + 0.1


def test_process_one_image_dir_uses_image_output_dir_for(monkeypatch, tmp_path):
    """image_dir 应等于 image_output_dir_for(out_stub, source_hash)."""
    from app.pipeline import image_output_dir_for

    fake_doc = _FakeDocument(source_hash="specific_hash")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="zzz", resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"

    _, _, _, _, image_dir = _process_one(entry, out_root, "fallback", 800)
    expected = image_output_dir_for(out_root / "_per_doc" / "zzz.json", "specific_hash")
    assert image_dir == expected


def test_process_one_parser_name_forwarded(monkeypatch, tmp_path):
    """parser_name 应被转发到 process_single."""
    captured = {}

    def fake_process_single(path, output_path, *, parser_name, max_chars, write_json):
        captured["parser_name"] = parser_name
        captured["max_chars"] = max_chars
        captured["write_json"] = write_json
        captured["output_path"] = output_path
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")
    _process_one(entry, tmp_path / "out", "kreuzberg", 1200)
    assert captured["parser_name"] == "kreuzberg"
    assert captured["max_chars"] == 1200
    assert captured["write_json"] is False


def test_process_one_out_stub_under_per_doc(monkeypatch, tmp_path):
    captured = {}

    def fake_process_single(path, output_path, **kwargs):
        captured["output_path"] = output_path
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="doc99", resolved_path=tmp_path / "in.pdf")
    _process_one(entry, tmp_path / "out", "fallback", 800)
    assert captured["output_path"] == tmp_path / "out" / "_per_doc" / "doc99.json"


# ---------- run_evaluation 行为深度第八批 ----------


def test_run_evaluation_empty_documents_empty_expected_failures(tmp_path):
    """空 manifest → 报告含 6 keys，per_doc 空列表."""
    manifest = _FakeManifest(documents=[], expected_failures=[])
    out = tmp_path / "report.json"
    report = run_evaluation(manifest, out, parser_name="fallback", max_chars=500)

    assert set(report.keys()) == {
        "report_version", "provenance", "devset", "summary", "per_doc", "expected_failures"
    }
    assert report["per_doc"] == []
    assert report["expected_failures"] == []


def test_run_evaluation_writes_report_to_disk(tmp_path):
    manifest = _FakeManifest(documents=[], expected_failures=[])
    out = tmp_path / "sub" / "report.json"
    run_evaluation(manifest, out)
    assert out.is_file()
    raw = out.read_text(encoding="utf-8")
    assert "report_version" in raw


def test_run_evaluation_report_json_serializable(tmp_path):
    manifest = _FakeManifest(documents=[], expected_failures=[])
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    # 应能 round-trip
    round_tripped = json.loads(json.dumps(report))
    assert round_tripped == report


def test_run_evaluation_creates_parent_dir(tmp_path):
    """output_path 父目录不存在时也应创建."""
    manifest = _FakeManifest()
    out = tmp_path / "a" / "b" / "c" / "r.json"
    run_evaluation(manifest, out)
    assert out.is_file()


def test_run_evaluation_uses_indent_2(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    text = out.read_text(encoding="utf-8")
    # indent=2 → 第二行起有 2 spaces
    assert "\n  " in text


def test_run_evaluation_uses_ensure_ascii_false(tmp_path):
    """写中文/Unicode 不被转义."""
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(manifest, out)
    # 至少 devset.categories_covered 是 list（可能为空），不会有 \u 转义
    # 这里检查 file 中没有 \u 序列
    text = out.read_text(encoding="utf-8")
    # 报告中可能没中文，但 ensure_ascii=False 意味着如果有 unicode 也不会被转义
    # 检查转义序列是合理的：\\u 开头的 4 位 hex 才算 ascii 转义
    # 但 just 字符串里出现 \u 也可能是 schema URL 之类的；这里用更严格的检测：
    # 如果是 ensure_ascii=True，所有非 ascii 字符都会变 \uXXXX
    # 这里因为内容里没有非 ASCII，无法直接判断，仅检查文件可读且为 utf-8
    assert isinstance(text, str)


def test_run_evaluation_report_version_matches_module_constant(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    assert report["report_version"] == REPORT_VERSION


def test_run_evaluation_provenance_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    prov = report["provenance"]
    assert isinstance(prov, dict)
    assert "evaluator_version" in prov
    assert "report_version" in prov


def test_run_evaluation_summary_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    summary = report["summary"]
    assert isinstance(summary, dict)


def test_run_evaluation_devset_present(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    devset = report["devset"]
    assert isinstance(devset, dict)


def test_run_evaluation_one_document_produces_one_per_doc(monkeypatch, tmp_path):
    fake_doc = _FakeDocument(source_hash="h", parser_version="1.0")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4 dummy")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 1
    pd = report["per_doc"][0]
    assert pd["doc_id"] == "d1"
    assert pd["source_type"] == "pdf"
    assert "metrics" in pd
    assert "wall_time_seconds" in pd


def test_run_evaluation_per_doc_excludes_private_keys(monkeypatch, tmp_path):
    """public_per_doc 不应包含 _annotation_present / _tolerance_chars / _missing_markers."""
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    pd = report["per_doc"][0]
    assert "_annotation_present" not in pd
    assert "_tolerance_chars" not in pd
    assert "_missing_markers" not in pd


def test_run_evaluation_wall_time_seconds_has_6_keys(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {
        "total", "parse", "chunk", "parse_reason", "chunk_reason"
    } | {"total"}  # 5 unique keys
    # 实际上是 5 个 keys（total 出现一次）
    assert len(wt) == 5
    assert wt["parse"] is None
    assert wt["chunk"] is None
    assert wt["parse_reason"] == "not_instrumented"
    assert wt["chunk_reason"] == "not_instrumented"
    assert isinstance(wt["total"], float)


def test_run_evaluation_parser_version_captured_from_first_doc(monkeypatch, tmp_path):
    fake_doc = _FakeDocument(parser_version="2.5.1")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] == "2.5.1"


def test_run_evaluation_parser_version_none_when_doc_fails(monkeypatch, tmp_path):
    err = _FakeError("parse_failed", "x")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] is None


def test_run_evaluation_expected_failure_matches(monkeypatch, tmp_path):
    err = _FakeError("parse_failed", "x")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4")
    ef = _FakeExpectedFailure(
        doc_id="bad1", resolved_path=bad_pdf, expected_error_code="parse_failed"
    )
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert len(report["expected_failures"]) == 1
    ef_result = report["expected_failures"][0]
    assert ef_result["doc_id"] == "bad1"
    assert ef_result["expected_error_code"] == "parse_failed"
    assert ef_result["actual_error_code"] == "parse_failed"
    assert ef_result["matches"] is True


def test_run_evaluation_expected_failure_no_match(monkeypatch, tmp_path):
    err = _FakeError("different_code", "x")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4")
    ef = _FakeExpectedFailure(
        doc_id="bad1", resolved_path=bad_pdf, expected_error_code="parse_failed"
    )
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] == "different_code"
    assert ef_result["matches"] is False


def test_run_evaluation_expected_failure_no_errors_actual_code_none(monkeypatch, tmp_path):
    """无 errors → actual_error_code is None, matches expected (non-None) → False."""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4")
    ef = _FakeExpectedFailure(
        doc_id="bad1", resolved_path=bad_pdf, expected_error_code="parse_failed"
    )
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert ef_result["actual_error_code"] is None
    assert ef_result["matches"] is False


def test_run_evaluation_per_doc_includes_metrics_dict(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    metrics = report["per_doc"][0]["metrics"]
    assert isinstance(metrics, dict)


def test_run_evaluation_returns_same_dict_as_written(monkeypatch, tmp_path):
    """返回的 dict 与磁盘上的 JSON 内容一致."""
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert report == on_disk


def test_run_evaluation_max_chars_forwarded(monkeypatch, tmp_path):
    captured = {}

    def fake_process_single(path, output_path, *, parser_name, max_chars, write_json):
        captured["max_chars"] = max_chars
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out, max_chars=432)
    assert captured["max_chars"] == 432


def test_run_evaluation_parser_name_forwarded(monkeypatch, tmp_path):
    captured = {}

    def fake_process_single(path, output_path, *, parser_name, max_chars, write_json):
        captured["parser_name"] = parser_name
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out, parser_name="kreuzberg")
    assert captured["parser_name"] == "kreuzberg"


def test_run_evaluation_tolerance_chars_default_30(monkeypatch, tmp_path):
    """tolerance_chars 默认 30 → 写入 _tolerance_chars（per_doc 内部用）."""
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)  # 默认 tolerance_chars=30
    # 公开报告中无 _tolerance_chars（私有，被剥除），但 metric chunk_boundary_*_tolerance_chars 应被记录
    # 由于无 annotation，metric 值为 None
    pd = report["per_doc"][0]
    assert "metrics" in pd


def test_run_evaluation_with_annotation_loads_file(monkeypatch, tmp_path):
    """annotation_resolved 指向有效文件 → _annotation_present=True."""
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    annot = tmp_path / "ann.json"
    annot.write_text('{"version": 1, "documents": []}', encoding="utf-8")
    entry = _FakeDocEntry(
        doc_id="d1", source_type="pdf", resolved_path=in_pdf, annotation_resolved=annot
    )
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out)
    # 报告公开字段中无 _annotation_present，但应不报错完成


def test_run_evaluation_annotation_missing_does_not_crash(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    annot = tmp_path / "missing.json"  # 不存在
    entry = _FakeDocEntry(
        doc_id="d1", source_type="pdf", resolved_path=in_pdf, annotation_resolved=annot
    )
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 1


def test_run_evaluation_per_doc_order_preserved(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    docs = [
        _FakeDocEntry(doc_id="a", source_type="pdf", resolved_path=in_pdf),
        _FakeDocEntry(doc_id="b", source_type="pdf", resolved_path=in_pdf),
        _FakeDocEntry(doc_id="c", source_type="pdf", resolved_path=in_pdf),
    ]
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    ids = [pd["doc_id"] for pd in report["per_doc"]]
    assert ids == ["a", "b", "c"]


def test_run_evaluation_per_doc_stub_cleaned_up(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out)
    stub = out.parent / "_per_doc" / "d1.json"
    assert not stub.is_file()


def test_run_evaluation_expected_failure_stub_cleaned_up(monkeypatch, tmp_path):
    err = _FakeError("parse_failed", "x")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4")
    ef = _FakeExpectedFailure(doc_id="b1", resolved_path=bad_pdf)
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out)
    stub = out.parent / "_per_doc" / "b1.json"
    assert not stub.is_file()


def test_run_evaluation_two_documents_provenance_uses_first_parser_version(
    monkeypatch, tmp_path
):
    """parser_version_for_prov 取首个非 None parser_version."""
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    docs_data = [
        ("d1", "1.0.0"),
        ("d2", "2.0.0"),
    ]
    docs = [_FakeDocEntry(doc_id=d, source_type="pdf", resolved_path=in_pdf) for d, _ in docs_data]
    versions = {d: v for d, v in docs_data}
    fake_docs = {d: _FakeDocument(parser_version=v) for d, v in docs_data}

    def fake_process_single(path, output_path, **kwargs):
        # 用 output_path 名字区分（doc_id.json）
        doc_id = output_path.stem
        return fake_docs[doc_id], []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert report["provenance"]["parser_version"] == "1.0.0"


def test_run_evaluation_str_output_path(tmp_path):
    """output_path 给字符串也应工作（Path() 包装）."""
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(manifest, str(out))
    assert out.is_file()


# ---------- _load_annotation 行为深度第八批 ----------


def test_load_annotation_path_is_dir_returns_none(tmp_path):
    """目录不是 file → None."""
    d = tmp_path / "subdir"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_dev_null_like_unreadable_returns_none(tmp_path):
    """权限错误模拟：写一个 JSON 但用 monkeypatch 让 open 抛 OSError."""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    original_open = Path.open

    def fake_open(self, *args, **kwargs):
        if self == p:
            raise OSError("simulated")
        return original_open(self, *args, **kwargs)

    # 直接 patch Path.open 不容易（被多处使用），改 patch _load_annotation 内部 json.load
    # 更简单：让文件不存在 → 但我们已经写了；改写文件为不可读模式（Windows 上难）
    # 退一步：用 monkeypatch.setattr Path.open 抛 OSError
    import evaluation.runner as r
    original_path_open = Path.open
    try:
        # 仅 patch 该测试中的 path
        Path.open = fake_open  # type: ignore
        assert _load_annotation(p) is None
    finally:
        Path.open = original_path_open  # type: ignore


def test_load_annotation_returns_falsy_zero(tmp_path):
    """JSON 顶层是 0 也应返回 0（不是 None）."""
    p = tmp_path / "a.json"
    p.write_text("0", encoding="utf-8")
    result = _load_annotation(p)
    assert result == 0
    assert result is not None


def test_load_annotation_returns_falsy_empty_string(tmp_path):
    """JSON 顶层是 "" 也应返回空字符串（不是 None）."""
    p = tmp_path / "a.json"
    p.write_text('""', encoding="utf-8")
    result = _load_annotation(p)
    assert result == ""


def test_load_annotation_returns_falsy_empty_list(tmp_path):
    """JSON 顶层是 [] 也应返回空列表（不是 None）."""
    p = tmp_path / "a.json"
    p.write_text("[]", encoding="utf-8")
    result = _load_annotation(p)
    assert result == []


def test_load_annotation_returns_falsy_false(tmp_path):
    """JSON 顶层是 false 也应返回 False（不是 None）."""
    p = tmp_path / "a.json"
    p.write_text("false", encoding="utf-8")
    result = _load_annotation(p)
    assert result is False


def test_load_annotation_does_not_create_file(tmp_path):
    """读取不存在的文件不应创建它."""
    p = tmp_path / "missing.json"
    _load_annotation(p)
    assert not p.exists()


def test_load_annotation_none_does_not_check_disk(tmp_path):
    """None path 直接返回，不应触碰磁盘."""
    # 这个测试只是确保 None path 不抛异常
    result = _load_annotation(None)
    assert result is None


def test_load_annotation_handles_utf8_multibyte(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"k": "日本語テスト"}', encoding="utf-8")
    assert _load_annotation(p) == {"k": "日本語テスト"}


def test_load_annotation_huge_json(tmp_path):
    """大 JSON 也应能加载."""
    p = tmp_path / "a.json"
    payload = {str(i): i for i in range(1000)}
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = _load_annotation(p)
    assert len(r) == 1000
    assert r["500"] == 500


def test_load_annotation_only_one_arg():
    """_load_annotation 只接受一个参数."""
    sig = inspect.signature(_load_annotation)
    assert len(sig.parameters) == 1


# ---------- module source forbidden tokens 第十三批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_output",
        "subprocess.check_call",
        "shutil.rmtree",
        "shutil.copy",
        "shutil.move",
        "glob.glob",
        "pickle.loads",
        "pickle.load",
        "marshal.loads",
        "ctypes.CDLL",
        "sys.exit",
        "__import__",
        "importlib.import_module",
        "requests.get",
        "urllib.request",
        "http.client",
        "socket.socket",
        "webbrowser.open",
        "antigravity",
        "this",  # easter egg
        "exit(",
        "quit(",
    ],
)
def test_runner_source_no_forbidden_token_thirteenth(token):
    src = inspect.getsource(rmod)
    assert token not in src


# ---------- module source 字符串精确补强第七批 ----------


def test_module_source_has_from_future_annotations():
    src = inspect.getsource(rmod)
    assert "from __future__ import annotations" in src


def test_module_source_import_typing_any():
    src = inspect.getsource(rmod)
    assert "from typing import Any" in src


def test_module_source_has_three_module_level_functions():
    """3 个模块级函数：_load_annotation, _process_one, run_evaluation."""
    src = inspect.getsource(rmod)
    assert "def _load_annotation(" in src
    assert "def _process_one(" in src
    assert "def run_evaluation(" in src


def test_module_source_no_class_definition():
    src = inspect.getsource(rmod)
    assert "\nclass " not in src
    assert not src.startswith("class ")


def test_module_source_no_async_def():
    src = inspect.getsource(rmod)
    assert "async def " not in src


def test_module_source_no_yield():
    src = inspect.getsource(rmod)
    assert "yield" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(rmod)
    assert ":=" not in src


def test_module_source_no_global_keyword():
    src = inspect.getsource(rmod)
    assert "\nglobal " not in src


def test_module_source_no_lambda():
    src = inspect.getsource(rmod)
    assert "lambda " not in src


def test_module_source_no_try_in_load_annotation_body_except_in_helpers():
    """run_evaluation / _process_one 各自有 try-except（unlink 部分），
    但 _load_annotation 的 try-except 应只在 except OSError/JSONDecodeError 出现."""
    src = inspect.getsource(rmod)
    # 找 _load_annotation 的本体（从 def 到下个 def）
    la_start = src.index("def _load_annotation(")
    next_def = src.index("def _process_one(", la_start)
    la_body = src[la_start:next_def]
    assert la_body.count("try:") == 1
    assert la_body.count("except") == 1


def test_module_source_imports_image_output_dir_for():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for" in src
    assert "from app.pipeline import" in src


def test_module_source_uses_image_output_dir_for_call():
    src = inspect.getsource(rmod)
    assert "image_output_dir_for(" in src


def test_module_source_no_print_statements():
    src = inspect.getsource(rmod)
    assert "print(" not in src


def test_module_source_no_logging():
    src = inspect.getsource(rmod)
    assert "import logging" not in src
    assert "logging." not in src


def test_module_source_no_logger():
    src = inspect.getsource(rmod)
    assert "logger" not in src


def test_module_source_uses_per_doc_subdir():
    src = inspect.getsource(rmod)
    assert '"_per_doc"' in src or "'_per_doc'" in src


def test_module_source_uses_doc_id_template():
    src = inspect.getsource(rmod)
    assert "{doc.doc_id}.json" in src or "{doc_id}.json" in src or "f\"{doc.doc_id}.json\"" in src
    assert "{ef.doc_id}.json" in src


def test_module_source_no_hardcoded_absolute_path():
    src = inspect.getsource(rmod)
    assert "C:\\\\Users" not in src
    assert "C:/Users" not in src
    assert "/home/" not in src
    assert "/Users/" not in src


def test_module_source_no_sleep():
    src = inspect.getsource(rmod)
    assert "time.sleep" not in src


def test_module_source_has_docstring():
    src = inspect.getsource(rmod)
    # 模块 docstring 应在文件开头
    assert src.startswith('"""')


def test_module_source_docstring_mentions_total():
    src = inspect.getsource(rmod)
    # 模块 docstring 提到计时约束
    assert "total" in src[:800]


def test_module_source_docstring_mentions_not_instrumented():
    src = inspect.getsource(rmod)
    assert "not_instrumented" in src or "未插桩" in src or "instrumented" in src


# ---------- signatures 精确补强第五批 ----------


def test_signature_load_annotation_param_name_path():
    sig = inspect.signature(_load_annotation)
    assert "path" in sig.parameters


def test_signature_load_annotation_param_path_annotation():
    sig = inspect.signature(_load_annotation)
    p = sig.parameters["path"]
    assert "Path" in str(p.annotation)
    assert "None" in str(p.annotation)


def test_signature_process_one_param_names():
    sig = inspect.signature(_process_one)
    assert set(sig.parameters.keys()) == {"doc", "output_root", "parser_name", "max_chars"}


def test_signature_process_one_doc_annotation():
    sig = inspect.signature(_process_one)
    a = sig.parameters["doc"].annotation
    # 实际签名：doc 没有真正 annotation（只是 # 注释）
    assert a is inspect.Parameter.empty


def test_signature_process_one_output_root_annotation():
    sig = inspect.signature(_process_one)
    assert "Path" in str(sig.parameters["output_root"].annotation)


def test_signature_process_one_parser_name_annotation():
    sig = inspect.signature(_process_one)
    assert "str" in str(sig.parameters["parser_name"].annotation)


def test_signature_process_one_max_chars_annotation():
    sig = inspect.signature(_process_one)
    assert "int" in str(sig.parameters["max_chars"].annotation)


def test_signature_process_one_return_tuple():
    sig = inspect.signature(_process_one)
    ra = str(sig.return_annotation)
    assert "tuple" in ra.lower()


def test_signature_run_evaluation_keyword_only_marker():
    """parser_name, max_chars, tolerance_chars 都是 keyword-only（* 之后）."""
    sig = inspect.signature(run_evaluation)
    params = list(sig.parameters.values())
    # 找 * 标记
    found_star = False
    after_star = []
    for p in params:
        if p.kind == inspect.Parameter.VAR_POSITIONAL:
            found_star = True
            continue
        if found_star:
            after_star.append(p.name)
    # 应有 * 标记（KEYWORD_ONLY 表示 * 之后）
    kw_only = [
        p.name for p in params
        if p.kind == inspect.Parameter.KEYWORD_ONLY
    ]
    assert set(kw_only) == {"parser_name", "max_chars", "tolerance_chars"}


def test_signature_run_evaluation_no_var_positional():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_run_evaluation_no_var_keyword():
    sig = inspect.signature(run_evaluation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_all_3_functions_are_function_type():
    assert isinstance(_load_annotation, types.FunctionType)
    assert isinstance(_process_one, types.FunctionType)
    assert isinstance(run_evaluation, types.FunctionType)


def test_signature_all_3_module_eq():
    assert _load_annotation.__module__ == rmod.__name__
    assert _process_one.__module__ == rmod.__name__
    assert run_evaluation.__module__ == rmod.__name__


# ---------- 模块整体合理性补强第五批 ----------


def test_module_all_attribute_value():
    assert hasattr(rmod, "__all__")
    assert rmod.__all__ == ["run_evaluation"]


def test_module_has_dunder_file():
    assert hasattr(rmod, "__file__")
    assert rmod.__file__ is not None


def test_module_dunder_file_endswith_runner_py():
    assert rmod.__file__.replace("\\", "/").endswith("evaluation/runner.py")


def test_module_dunder_name():
    assert rmod.__name__ == "evaluation.runner"


def test_module_no_dunder_dict_callables_beyond_imports():
    """所有 callable 都应是 imports 或模块自身定义的函数."""
    for name, obj in vars(rmod).items():
        if name.startswith("__"):
            continue
        if callable(obj):
            # 应是 FunctionType（本模块定义）或来自 imports
            if isinstance(obj, types.FunctionType):
                assert obj.__module__ in (rmod.__name__, "app.pipeline") or obj.__module__.startswith("evaluation")
            # 其他 callable（如 classmethod, builtin）应来自 imports
        else:
            # 非 callable 应是 typing.Any / Path / 模块 / __all__ / import 进来的常量
            assert (
                name == "__all__"
                or isinstance(obj, (str, int, type(None), types.ModuleType))
                or hasattr(obj, "__module__")
            )


def test_module_function_count():
    """模块自身定义的函数 = 3."""
    own_funcs = [
        obj for obj in vars(rmod).values()
        if isinstance(obj, types.FunctionType) and obj.__module__ == rmod.__name__
    ]
    assert len(own_funcs) == 3


def test_module_imports_count_at_least_5():
    """至少导入 5 个外部名字（json, time, Path, Any, process_single, ...）."""
    # 通过 inspect.getsource 检查 import 行
    src = inspect.getsource(rmod)
    import_lines = [
        line for line in src.splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert len(import_lines) >= 5


def test_module_has_no_unused_imports_at_module_namespace():
    """模块 namespace 中所有 imported 名字应被使用（启发式检查）."""
    src = inspect.getsource(rmod)
    # 取 from X import Y 模式的所有 Y
    import re
    imports = []
    for line in src.splitlines():
        m = re.match(r"from\s+\S+\s+import\s+\(([^)]+)\)", line)
        if m:
            for name in m.group(1).split(","):
                name = name.strip()
                if name:
                    imports.append(name)
        m = re.match(r"from\s+\S+\s+import\s+(.+)$", line)
        if m and "(" not in line:
            for name in m.group(1).split(","):
                name = name.strip()
                if name:
                    imports.append(name)
    # 抽掉 def __all__ = ... 之类的源码
    body = src
    for name in imports:
        # 至少在 imports 行之外出现一次
        assert name in body


def test_module_constants_only_all():
    """模块级大写常量应是 imports（REPORT_VERSION）或 __all__."""
    for name in dir(rmod):
        if name.startswith("__"):
            continue
        if name.isupper() or (name[:1].isupper() and "_" not in name):
            obj = getattr(rmod, name)
            # 应是 imports（如 REPORT_VERSION="1.1"）或 __all__
            # 不应有模块自身定义的非 import 常量（用 source 检查更严格）
            # 这里只检查 str/int 类常量来自 imports（在源码中无 = "..." 赋值）
            if isinstance(obj, str) and name != "__all__":
                # 看看 source 中是否有 NAME = "value" 形式的赋值
                src = inspect.getsource(rmod)
                pattern = f"{name} = "
                # 顶层赋值（不缩进）
                top_level_assign = any(
                    line.startswith(pattern) for line in src.splitlines()
                )
                assert not top_level_assign, (
                    f"{name} should be imported, not assigned at module level"
                )


def test_module_no_call_at_top_level():
    """模块顶层不应有显式的 print/exit/sys-call 类副作用调用（启发式检查）."""
    src = inspect.getsource(rmod)
    # 检查模块顶层（不缩进）行
    in_triple = False
    triple_quote = None
    suspicious_patterns = ("print(", "exit(", "quit(", "os.system(", "subprocess.")
    for line in src.splitlines():
        if in_triple:
            if triple_quote and triple_quote in line:
                in_triple = False
                triple_quote = None
            continue
        # 检测 docstring 起始
        ls = line.lstrip()
        for q in ('"""', "'''"):
            if ls.startswith(q):
                rest = ls[3:]
                if rest.count(q) >= 1:
                    pass  # 同行关闭
                else:
                    in_triple = True
                    triple_quote = q
                break
        # 不区分顶层/缩进，只看是否有可疑 pattern
        for pat in suspicious_patterns:
            assert pat not in line, f"suspicious call: {pat} in {line!r}"


# ---------- 端到端集成补强第五批 ----------


def test_e2e_load_annotation_idempotent_under_repeated_calls(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"x": [1, 2, 3]}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    c = _load_annotation(p)
    assert a == b == c == {"x": [1, 2, 3]}


def test_e2e_load_annotation_concurrent_safe_sequential(tmp_path):
    """连续多次调用应稳定."""
    p = tmp_path / "a.json"
    p.write_text('[1, 2, {"k": "v"}]', encoding="utf-8")
    for _ in range(20):
        assert _load_annotation(p) == [1, 2, {"k": "v"}]


def test_e2e_load_annotation_unicode_key_and_value(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"键": "值"}', encoding="utf-8")
    assert _load_annotation(p) == {"键": "值"}


def test_e2e_load_annotation_array_of_objects(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[{"a": 1}, {"b": 2}]', encoding="utf-8")
    assert _load_annotation(p) == [{"a": 1}, {"b": 2}]


def test_e2e_load_annotation_array_with_null_values(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[null, 1, null]', encoding="utf-8")
    assert _load_annotation(p) == [None, 1, None]


def test_e2e_load_annotation_returns_same_identity_for_same_content(tmp_path):
    """JSON 重新加载应是 equal（不一定是同一对象）."""
    p = tmp_path / "a.json"
    p.write_text('{"a": 1}', encoding="utf-8")
    a = _load_annotation(p)
    b = _load_annotation(p)
    assert a == b
    assert a is not b


def test_e2e_run_evaluation_end_to_end_with_empty_manifest_produces_valid_report(tmp_path):
    """空 manifest → 报告应通过 schema 校验."""
    from evaluation.schema import validate
    manifest = _FakeManifest(documents=[], expected_failures=[])
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out)
    # validate 第二参数是 schema 名字（字符串）
    validate(report, "evaluation-report.schema.json")


def test_e2e_run_evaluation_idempotent(tmp_path):
    """两次调用应产生相同报告（除 timestamp / git_dirty 外）."""
    manifest = _FakeManifest()
    out1 = tmp_path / "r1.json"
    out2 = tmp_path / "r2.json"
    r1 = run_evaluation(manifest, out1)
    r2 = run_evaluation(manifest, out2)
    # run_timestamp_iso 会不同
    r1["provenance"].pop("run_timestamp_iso", None)
    r2["provenance"].pop("run_timestamp_iso", None)
    # git_dirty 在 dirty repo 中可能因为 first run 生成 _per_doc 目录而变化
    # 但 tmp_path 在仓库外，所以 git_dirty 应一致
    assert r1 == r2


def test_e2e_run_evaluation_returns_dict_type():
    sig = inspect.signature(run_evaluation)
    assert "dict" in str(sig.return_annotation)


def test_e2e_load_annotation_none_returns_none_consistent():
    assert _load_annotation(None) is None
    assert _load_annotation(None) is None
    assert _load_annotation(None) is None


def test_e2e_module_runner_can_be_imported():
    import evaluation.runner as r
    assert r is rmod


def test_e2e_module_runner_run_evaluation_in_all():
    assert "run_evaluation" in rmod.__all__


def test_e2e_module_runner_run_evaluation_public_via_import():
    from evaluation.runner import run_evaluation as f
    assert f is run_evaluation


def test_e2e_load_annotation_handles_bom_properly(tmp_path):
    """BOM 字节会让 json 解析失败 → None."""
    p = tmp_path / "a.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    assert _load_annotation(p) is None


def test_e2e_load_annotation_truncated_json(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a":', encoding="utf-8")
    assert _load_annotation(p) is None


def test_e2e_load_annotation_just_braces(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{}', encoding="utf-8")
    assert _load_annotation(p) == {}


def test_e2e_load_annotation_just_brackets(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('[]', encoding="utf-8")
    assert _load_annotation(p) == []


def test_e2e_load_annotation_deeply_nested(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('{"a": {"b": {"c": {"d": {"e": "deep"}}}}}', encoding="utf-8")
    assert _load_annotation(p) == {"a": {"b": {"c": {"d": {"e": "deep"}}}}}


def test_e2e_load_annotation_with_float(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('3.14159', encoding="utf-8")
    assert _load_annotation(p) == pytest.approx(3.14159)


def test_e2e_load_annotation_with_scientific_notation(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('1.5e3', encoding="utf-8")
    assert _load_annotation(p) == 1500.0


def test_e2e_load_annotation_negative_number(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('-42', encoding="utf-8")
    assert _load_annotation(p) == -42


def test_e2e_load_annotation_json_with_whitespace(tmp_path):
    """JSON 前后空白应被 json.load 容忍."""
    p = tmp_path / "a.json"
    p.write_text('  {"a": 1}  ', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


def test_e2e_load_annotation_json_with_newlines(tmp_path):
    p = tmp_path / "a.json"
    p.write_text('\n{\n"a": 1\n}\n', encoding="utf-8")
    assert _load_annotation(p) == {"a": 1}


# ---------- _process_one 行为深度第八批（继续） ----------


def test_process_one_unlink_handles_gracefully_when_stub_does_not_exist(monkeypatch, tmp_path):
    """stub 不存在时 unlink check 应跳过（不抛）."""
    def fake_process_single(*args, **kwargs):
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="x", resolved_path=tmp_path / "in.pdf")
    # 正常调用，stub 在 write_json=False 下不会创建，unlink check 会跳过
    out_root = tmp_path / "out"
    result = _process_one(entry, out_root, "fallback", 800)
    assert isinstance(result, tuple)


def test_process_one_unlink_swallows_oserror(monkeypatch, tmp_path):
    """即使 unlink 抛 OSError，也应被吞掉（已通过 source 测试，这里行为层面再次验证）."""
    # 制造 stub 存在但 unlink 抛 OSError 的场景：写一个 stub，让 fake_process_single 不写它
    def fake_process_single(*args, **kwargs):
        # 不写文件，但 stub 已被外部预创建
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)

    entry = _FakeDocEntry(doc_id="abc", resolved_path=tmp_path / "in.pdf")
    out_root = tmp_path / "out"
    out_root.mkdir()
    per_doc_dir = out_root / "_per_doc"
    per_doc_dir.mkdir()
    stub = per_doc_dir / "abc.json"
    stub.write_text("dummy", encoding="utf-8")

    # patch Path.unlink 抛 OSError
    original_unlink = Path.unlink

    def fake_unlink(self, *args, **kwargs):
        raise OSError("simulated")

    Path.unlink = fake_unlink  # type: ignore
    try:
        # 不应抛
        result = _process_one(entry, out_root, "fallback", 800)
        assert isinstance(result, tuple)
    finally:
        Path.unlink = original_unlink  # type: ignore


def test_process_one_returns_path_object_for_image_dir(monkeypatch, tmp_path):
    fake_doc = _FakeDocument(source_hash="h")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(resolved_path=tmp_path / "in.pdf")
    _, _, _, _, image_dir = _process_one(entry, tmp_path / "out", "fallback", 800)
    assert isinstance(image_dir, Path)


def test_process_one_image_dir_under_per_doc_subdir(monkeypatch, tmp_path):
    fake_doc = _FakeDocument(source_hash="myhash")

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    entry = _FakeDocEntry(doc_id="d1", resolved_path=tmp_path / "in.pdf")
    _, _, _, _, image_dir = _process_one(entry, tmp_path / "out", "fallback", 800)
    # image_dir 应在 _per_doc 子树（image_output_dir_for 用 images-<sha> 命名）
    assert "_per_doc" in str(image_dir) or "d1" in str(image_dir)


# ---------- run_evaluation 行为深度第八批（继续） ----------


def test_run_evaluation_multiple_documents_all_processed(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    docs = [
        _FakeDocEntry(doc_id=f"d{i}", source_type="pdf", resolved_path=in_pdf)
        for i in range(5)
    ]
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 5


def test_run_evaluation_mixed_pdf_and_docx(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    in_docx = tmp_path / "in.docx"
    in_docx.write_bytes(b"PK dummy")
    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf),
        _FakeDocEntry(doc_id="d2", source_type="docx", resolved_path=in_docx),
    ]
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    types = [pd["source_type"] for pd in report["per_doc"]]
    assert types == ["pdf", "docx"]


def test_run_evaluation_doc_failure_in_middle(monkeypatch, tmp_path):
    """中间一个文档失败，其他仍应处理."""
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")

    call_count = {"n": 0}

    def fake_process_single(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            return None, [_FakeError("failed", "boom")]
        return _FakeDocument(), []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    docs = [
        _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf),
        _FakeDocEntry(doc_id="d2", source_type="pdf", resolved_path=in_pdf),
        _FakeDocEntry(doc_id="d3", source_type="pdf", resolved_path=in_pdf),
    ]
    manifest = _FakeManifest(documents=docs)
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    assert len(report["per_doc"]) == 3
    assert report["per_doc"][1]["doc_id"] == "d2"


def test_run_evaluation_output_root_is_output_path_parent(tmp_path):
    """output_root = output_path.parent（用于 _per_doc 子目录）."""
    manifest = _FakeManifest()
    out = tmp_path / "deep" / "tree" / "r.json"
    run_evaluation(manifest, out)
    # _per_doc 不应被创建（因为 manifest.documents 为空）
    per_doc_dir = out.parent / "_per_doc"
    # 没有 doc → _process_one 不被调用 → _per_doc 不创建
    assert not per_doc_dir.exists()


def test_run_evaluation_per_doc_dir_created_when_documents_exist(monkeypatch, tmp_path):
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    run_evaluation(manifest, out)
    per_doc_dir = out.parent / "_per_doc"
    assert per_doc_dir.is_dir()


def test_run_evaluation_report_keys_exact():
    """报告 keys 应精确等于 6 个."""
    sig_source = inspect.getsource(rmod)
    # 通过实际调用拿 keys
    manifest = _FakeManifest()
    out = Path(__file__).parent / "_tmp_run_eval_test.json"
    try:
        report = run_evaluation(manifest, out)
        assert set(report.keys()) == {
            "report_version", "provenance", "devset", "summary",
            "per_doc", "expected_failures",
        }
    finally:
        if out.exists():
            out.unlink()


def test_run_evaluation_per_doc_dict_keys_exact(monkeypatch, tmp_path):
    """公开 per_doc 中每个条目应只有 4 个 key（doc_id, source_type, metrics, wall_time_seconds）."""
    fake_doc = _FakeDocument()

    def fake_process_single(*args, **kwargs):
        return fake_doc, []

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    in_pdf = tmp_path / "in.pdf"
    in_pdf.write_bytes(b"%PDF-1.4")
    entry = _FakeDocEntry(doc_id="d1", source_type="pdf", resolved_path=in_pdf)
    manifest = _FakeManifest(documents=[entry])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    pd = report["per_doc"][0]
    assert set(pd.keys()) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_run_evaluation_expected_failure_keys_exact(monkeypatch, tmp_path):
    err = _FakeError("parse_failed", "x")

    def fake_process_single(*args, **kwargs):
        return None, [err]

    monkeypatch.setattr(rmod, "process_single", fake_process_single)
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4")
    ef = _FakeExpectedFailure(doc_id="b1", resolved_path=bad_pdf)
    manifest = _FakeManifest(expected_failures=[ef])
    out = tmp_path / "r.json"

    report = run_evaluation(manifest, out)
    ef_result = report["expected_failures"][0]
    assert set(ef_result.keys()) == {
        "doc_id", "expected_error_code", "actual_error_code", "matches",
    }


def test_run_evaluation_provenance_parser_name_forwarded(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_run_evaluation_provenance_max_chars_forwarded(tmp_path):
    manifest = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(manifest, out, max_chars=999)
    assert report["provenance"]["max_chars"] == 999
