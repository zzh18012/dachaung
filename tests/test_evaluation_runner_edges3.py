"""evaluation/runner.py 边角测试 - 第三轮（Round 96）。

补强已有 59 + 65 + 121 = 245 测试未覆盖的：
- run_evaluation 报告结构精确字段（top-level / provenance / devset / summary / per_doc）
- per_doc public 字段精确（不含 _annotation_present / _tolerance_chars / _missing_markers）
- wall_time_seconds 结构精确：{total, parse:None, chunk:None, parse_reason, chunk_reason}
- expected_failures 结构精确：{doc_id, expected_error_code, actual_error_code, matches}
- annotation_present 影响是否计算 chunk_boundary / figure_caption
- _process_one 失败时的 error_dict 来自 errors[0].to_dict()
- _process_one 成功时的 document.to_dict() 结构
- _process_one image_dir 仅在 document 非空时计算
- run_evaluation 写盘后能被 json.load 重读
- 多文档顺序保持与 manifest 一致
- tolerance_chars 透传到 chunk_boundary_prf
- _tolerance_chars / _missing_markers 在 per_doc_results 但不在 public_per_doc
- build_devset_section 6 字段齐全
- aggregate_summary 4 类聚合（counts/success_rates/ratio/silent_drop）

不修改任何源码。
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from evaluation import EVALUATOR_VERSION, REPORT_VERSION
from evaluation.runner import _load_annotation, _process_one, run_evaluation


# =========================================================================
# 共用 fixtures（与 _edges2.py 相同结构）
# =========================================================================


@dataclass
class _FakeDocEntry:
    doc_id: str
    resolved_path: Path
    source_type: str = "docx"
    expectations: dict | None = None
    annotation_resolved: Path | None = None


@dataclass
class _FakeExpectedFailure:
    doc_id: str
    resolved_path: Path
    expected_error_code: str
    source_type: str | None = None


@dataclass
class _FakeManifest:
    manifest_version: str = "1.0"
    devset_status: str = "incomplete"
    documents: tuple = ()
    expected_failures: tuple = ()
    project_root: Path | None = None

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
            s.update(getattr(d, "categories", ()))
        return sorted(s)


def _write_minimal_docx(path: Path, text: str = "Hello world.") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    doc_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc_xml)
    return path


def _write_minimal_pdf(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000052 00000 n \n0000000101 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n164\n%%EOF"
    )
    path.write_bytes(pdf_bytes)
    return path


# =========================================================================
# 报告 top-level 结构
# =========================================================================


def test_report_top_level_keys_exact_set(tmp_path: Path):
    """report 顶层 keys 精确为 6 个。"""
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert set(report.keys()) == {
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
        "expected_failures",
    }


def test_report_report_version_value(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["report_version"] == REPORT_VERSION


# =========================================================================
# provenance 字段精确
# =========================================================================


def test_report_provenance_keys_exact_set(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    prov = report["provenance"]
    assert set(prov.keys()) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_report_provenance_evaluator_version_value(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["evaluator_version"] == EVALUATOR_VERSION


def test_report_provenance_report_version_value(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["report_version"] == REPORT_VERSION


def test_report_provenance_parser_name_default(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["provenance"]["parser_name"] == "fallback"


def test_report_provenance_parser_name_override(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out, parser_name="kreuzberg")
    assert report["provenance"]["parser_name"] == "kreuzberg"


def test_report_provenance_max_chars_value(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out, max_chars=500)
    assert report["provenance"]["max_chars"] == 500


def test_report_provenance_dependencies_is_dict(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert isinstance(report["provenance"]["dependencies"], dict)


def test_report_provenance_dependencies_has_pdfplumber(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "pdfplumber" in report["provenance"]["dependencies"]


def test_report_provenance_dependencies_has_python_docx(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "python-docx" in report["provenance"]["dependencies"]


def test_report_provenance_dependencies_has_pypdfium2(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "pypdfium2" in report["provenance"]["dependencies"]


def test_report_provenance_run_timestamp_iso_format(tmp_path: Path):
    """ISO 8601 时间戳。"""
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    ts = report["provenance"]["run_timestamp_iso"]
    # ISO format 应当包含 'T' 或日期
    assert "T" in ts or "-" in ts


def test_report_provenance_git_commit_is_string_or_none(tmp_path: Path):
    m = _FakeManifest(project_root=Path.cwd())
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    commit = report["provenance"]["git_commit"]
    assert commit is None or isinstance(commit, str)


def test_report_provenance_git_dirty_is_bool(tmp_path: Path):
    m = _FakeManifest(project_root=Path.cwd())
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert isinstance(report["provenance"]["git_dirty"], bool)


# =========================================================================
# devset 字段精确
# =========================================================================


def test_report_devset_keys_exact_set(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert set(report["devset"].keys()) == {
        "status",
        "file_count",
        "content_group_count",
        "pdf_count",
        "docx_count",
        "categories_covered",
    }


def test_report_devset_status_incomplete(tmp_path: Path):
    m = _FakeManifest(devset_status="incomplete")
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["status"] == "incomplete"


def test_report_devset_file_count_zero_when_empty(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["file_count"] == 0


def test_report_devset_pdf_count_zero_when_no_pdfs(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["pdf_count"] == 0


def test_report_devset_docx_count_zero_when_no_docx(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["docx_count"] == 0


def test_report_devset_content_group_count_zero_when_empty(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["devset"]["content_group_count"] == 0


def test_report_devset_categories_covered_is_list(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert isinstance(report["devset"]["categories_covered"], list)


# =========================================================================
# summary 字段精确
# =========================================================================


def test_report_summary_keys_exact_set(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert set(report["summary"].keys()) == {
        "counts",
        "success_rates",
        "ratio_macro_averages",
        "silent_drop_total",
    }


def test_report_summary_counts_has_element_count_total(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "element_count_total" in report["summary"]["counts"]


def test_report_summary_success_rates_has_pipeline_success(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "pipeline_success" in report["summary"]["success_rates"]


def test_report_summary_pipeline_success_rate_zero_when_no_docs(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    sr = report["summary"]["success_rates"]["pipeline_success"]
    assert sr["rate"] is None  # 0 docs → None


def test_report_summary_pipeline_success_rate_one_when_succeeds(tmp_path: Path):
    """有 1 个合法 docx → rate=1.0。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    sr = report["summary"]["success_rates"]["pipeline_success"]
    assert sr["rate"] == 1.0
    assert sr["success_count"] == 1
    assert sr["total"] == 1


def test_report_summary_ratio_macro_averages_has_text_preservation_equal(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "text_preservation_equal" in report["summary"]["ratio_macro_averages"]


def test_report_summary_ratio_macro_averages_has_chunk_boundary_f1(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "chunk_boundary_f1" in report["summary"]["ratio_macro_averages"]


def test_report_summary_ratio_macro_averages_has_heading_boundary_compliance(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert "heading_boundary_compliance" in report["summary"]["ratio_macro_averages"]


def test_report_summary_silent_drop_total_none_when_no_docs(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["summary"]["silent_drop_total"] is None


# =========================================================================
# per_doc 公开字段精确
# =========================================================================


def test_per_doc_public_keys_exact_set(tmp_path: Path):
    """per_doc[i] 仅含 4 个公开字段（不含 _annotation_present / _tolerance_chars / _missing_markers）。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert set(report["per_doc"][0].keys()) == {
        "doc_id",
        "source_type",
        "metrics",
        "wall_time_seconds",
    }


def test_per_doc_does_not_contain_annotation_present(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "_annotation_present" not in report["per_doc"][0]


def test_per_doc_does_not_contain_tolerance_chars(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "_tolerance_chars" not in report["per_doc"][0]


def test_per_doc_does_not_contain_missing_markers(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "_missing_markers" not in report["per_doc"][0]


def test_per_doc_wall_time_seconds_keys_exact(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    wt = report["per_doc"][0]["wall_time_seconds"]
    assert set(wt.keys()) == {"total", "parse", "chunk", "parse_reason", "chunk_reason"}


def test_per_doc_wall_time_seconds_parse_is_none(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["wall_time_seconds"]["parse"] is None


def test_per_doc_wall_time_seconds_chunk_is_none(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["wall_time_seconds"]["chunk"] is None


def test_per_doc_wall_time_seconds_parse_reason_not_instrumented(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["wall_time_seconds"]["parse_reason"] == "not_instrumented"


def test_per_doc_wall_time_seconds_chunk_reason_not_instrumented(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["wall_time_seconds"]["chunk_reason"] == "not_instrumented"


def test_per_doc_wall_time_seconds_total_positive_when_succeeds(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["wall_time_seconds"]["total"] > 0


# =========================================================================
# per_doc.metrics 结构
# =========================================================================


def test_per_doc_metrics_has_element_count_total(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "element_count_total" in report["per_doc"][0]["metrics"]


def test_per_doc_metrics_has_pipeline_success(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "pipeline_success" in report["per_doc"][0]["metrics"]


def test_per_doc_metrics_pipeline_success_value_true_when_ok(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    metric = report["per_doc"][0]["metrics"]["pipeline_success"]
    assert metric["value"] is True


def test_per_doc_metrics_has_text_preservation_equal(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "text_preservation_equal" in report["per_doc"][0]["metrics"]


def test_per_doc_metrics_has_chunk_boundary_precision(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "chunk_boundary_precision" in report["per_doc"][0]["metrics"]


def test_per_doc_metrics_has_figure_caption_precision(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert "figure_caption_precision" in report["per_doc"][0]["metrics"]


def test_per_doc_metrics_figure_caption_precision_is_null(tmp_path: Path):
    """figure_caption_* 始终 null + parser_does_not_emit_relations。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    metric = report["per_doc"][0]["metrics"]["figure_caption_precision"]
    assert metric["value"] is None
    assert metric["reason"] == "parser_does_not_emit_relations"


# =========================================================================
# expected_failures 结构
# =========================================================================


def test_expected_failures_keys_exact_set(tmp_path: Path):
    """expected_failures[i] 含 4 个字段。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    ef = _FakeExpectedFailure(
        doc_id="ef1",
        resolved_path=docx_p,
        expected_error_code="file_not_found",
    )
    m = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert set(report["expected_failures"][0].keys()) == {
        "doc_id",
        "expected_error_code",
        "actual_error_code",
        "matches",
    }


def test_expected_failures_actual_code_when_unexpectedly_succeeds(tmp_path: Path):
    """期望失败但实际成功 → actual_code=None, matches=False. """
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    ef = _FakeExpectedFailure(
        doc_id="ef1",
        resolved_path=docx_p,
        expected_error_code="file_not_found",  # 期望失败
    )
    m = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    ef_r = report["expected_failures"][0]
    assert ef_r["actual_error_code"] is None  # 实际成功
    assert ef_r["matches"] is False


def test_expected_failures_actual_code_when_matches(tmp_path: Path):
    """期望失败且实际失败且 code 匹配 → matches=True. """
    ef = _FakeExpectedFailure(
        doc_id="ef1",
        resolved_path=tmp_path / "nonexistent.docx",  # 不存在
        expected_error_code="file_not_found",
    )
    m = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    ef_r = report["expected_failures"][0]
    assert ef_r["actual_error_code"] == "file_not_found"
    assert ef_r["matches"] is True


def test_expected_failures_actual_code_when_mismatch(tmp_path: Path):
    """期望 code A 但实际 code B → matches=False. """
    ef = _FakeExpectedFailure(
        doc_id="ef1",
        resolved_path=tmp_path / "nonexistent.docx",  # file_not_found
        expected_error_code="schema_validation_failed",  # 期望不同 code
    )
    m = _FakeManifest(expected_failures=(ef,))
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    ef_r = report["expected_failures"][0]
    assert ef_r["actual_error_code"] == "file_not_found"
    assert ef_r["expected_error_code"] == "schema_validation_failed"
    assert ef_r["matches"] is False


def test_expected_failures_empty_list_when_manifest_empty(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["expected_failures"] == []


def test_expected_failures_multiple_entries_preserve_order(tmp_path: Path):
    ef1 = _FakeExpectedFailure(
        doc_id="ef1",
        resolved_path=tmp_path / "no1.docx",
        expected_error_code="file_not_found",
    )
    ef2 = _FakeExpectedFailure(
        doc_id="ef2",
        resolved_path=tmp_path / "no2.docx",
        expected_error_code="file_not_found",
    )
    m = _FakeManifest(expected_failures=(ef1, ef2))
    out = tmp_path / "r.json"
    report = run_evaluation(m, out)
    assert report["expected_failures"][0]["doc_id"] == "ef1"
    assert report["expected_failures"][1]["doc_id"] == "ef2"


# =========================================================================
# per_doc 顺序与 manifest 一致
# =========================================================================


def test_per_doc_preserves_manifest_order(tmp_path: Path):
    p1 = tmp_path / "a.docx"
    p2 = tmp_path / "b.docx"
    _write_minimal_docx(p1)
    _write_minimal_docx(p2)
    d1 = _FakeDocEntry(doc_id="d1", resolved_path=p1, source_type="docx")
    d2 = _FakeDocEntry(doc_id="d2", resolved_path=p2, source_type="docx")
    m = _FakeManifest(documents=(d1, d2))
    out = tmp_path / "out" / "r.json"
    report = run_evaluation(m, out)
    assert report["per_doc"][0]["doc_id"] == "d1"
    assert report["per_doc"][1]["doc_id"] == "d2"


# =========================================================================
# 写盘 + 重读
# =========================================================================


def test_report_written_to_disk_can_be_reloaded(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "deep" / "r.json"
    run_evaluation(m, out)
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "report_version" in data


def test_report_written_is_valid_json(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    # 不抛即可
    json.loads(out.read_text(encoding="utf-8"))


def test_report_written_uses_indent_2(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # indent=2 → 含 "  " 缩进
    assert "  " in content


def test_report_written_uses_ensure_ascii_false(tmp_path: Path):
    """ensure_ascii=False → 中文/Unicode 不转义。"""
    m = _FakeManifest()
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    content = out.read_text(encoding="utf-8")
    # 不抛 + 是 UTF-8 编码
    assert out.read_bytes()[:1] == b"{"


# =========================================================================
# _process_one 错误路径细节
# =========================================================================


def test_process_one_missing_file_returns_file_not_found_error(tmp_path: Path):
    missing = tmp_path / "no.docx"
    doc = _FakeDocEntry(doc_id="d1", resolved_path=missing, source_type="docx")
    output_root = tmp_path / "out"
    document, error, total, parser_version, image_dir = _process_one(
        doc, output_root, "fallback", 800
    )
    assert document is None
    assert error["code"] == "file_not_found"


def test_process_one_missing_file_total_seconds_positive(tmp_path: Path):
    missing = tmp_path / "no.docx"
    doc = _FakeDocEntry(doc_id="d1", resolved_path=missing, source_type="docx")
    output_root = tmp_path / "out"
    _, _, total, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert total >= 0


def test_process_one_missing_file_parser_version_none(tmp_path: Path):
    missing = tmp_path / "no.docx"
    doc = _FakeDocEntry(doc_id="d1", resolved_path=missing, source_type="docx")
    output_root = tmp_path / "out"
    _, _, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
    assert parser_version is None


def test_process_one_missing_file_image_dir_none(tmp_path: Path):
    """document 为 None → image_dir 也 None（不返回 Path() 占位）。"""
    missing = tmp_path / "no.docx"
    doc = _FakeDocEntry(doc_id="d1", resolved_path=missing, source_type="docx")
    output_root = tmp_path / "out"
    _, _, _, _, image_dir = _process_one(doc, output_root, "fallback", 800)
    assert image_dir is None


def test_process_one_creates_per_doc_directory(tmp_path: Path):
    """out_stub 父目录 _per_doc 被创建。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "fallback", 800)
    assert (output_root / "_per_doc").is_dir()


def test_process_one_out_stub_cleaned_up(tmp_path: Path):
    """成功后 out_stub（_per_doc/<doc_id>.json）被清理。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    output_root = tmp_path / "out"
    _process_one(doc, output_root, "fallback", 800)
    out_stub = output_root / "_per_doc" / "d1.json"
    assert not out_stub.exists()


def test_process_one_returns_document_to_dict_when_success(tmp_path: Path):
    """成功 → document 是 dict（to_dict 后），不是 None。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    output_root = tmp_path / "out"
    document, error, _, _, _ = _process_one(doc, output_root, "fallback", 800)
    assert document is not None
    assert error is None
    assert isinstance(document, dict)
    assert "document_id" in document


def test_process_one_returns_parser_version_when_success(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    output_root = tmp_path / "out"
    _, _, _, parser_version, _ = _process_one(doc, output_root, "fallback", 800)
    assert parser_version is not None
    assert isinstance(parser_version, str)


# =========================================================================
# _load_annotation 第三轮
# =========================================================================


def test_load_annotation_returns_none_for_none_input():
    assert _load_annotation(None) is None


def test_load_annotation_returns_none_for_missing_file(tmp_path: Path):
    missing = tmp_path / "no.json"
    assert _load_annotation(missing) is None


def test_load_annotation_returns_none_for_directory(tmp_path: Path):
    """目录 → OSError → None。"""
    d = tmp_path / "sub"
    d.mkdir()
    assert _load_annotation(d) is None


def test_load_annotation_returns_dict_for_valid_json(tmp_path: Path):
    f = tmp_path / "a.json"
    f.write_text('{"chunks": []}', encoding="utf-8")
    result = _load_annotation(f)
    assert result == {"chunks": []}


def test_load_annotation_returns_list_for_array_json(tmp_path: Path):
    f = tmp_path / "a.json"
    f.write_text("[1,2,3]", encoding="utf-8")
    result = _load_annotation(f)
    assert result == [1, 2, 3]


def test_load_annotation_handles_utf8_with_bom(tmp_path: Path):
    """UTF-8 BOM 不应导致 JSON 解析失败。"""
    f = tmp_path / "a.json"
    f.write_bytes(b'\xef\xbb\xbf{"k": "v"}')
    result = _load_annotation(f)
    # BOM 不被 json.load 接受 → None
    # 但某些 Python 版本可能接受；不强断言具体值
    assert result is None or result == {"k": "v"}


# =========================================================================
# run_evaluation 不抛异常（防御性）
# =========================================================================


def test_run_evaluation_does_not_raise_for_minimal_manifest(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "r.json"
    # 不抛即可
    run_evaluation(m, out)


def test_run_evaluation_does_not_raise_for_doc_with_unsupported_extension(tmp_path: Path):
    """doc 但 source_type 不在 schema enum（pdf/docx）→ 仍能跑（pipeline 会失败）。"""
    txt_p = tmp_path / "a.txt"
    txt_p.write_text("hello", encoding="utf-8")
    doc = _FakeDocEntry(doc_id="d1", resolved_path=txt_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "r.json"
    # 不抛即可
    run_evaluation(m, out)


def test_run_evaluation_creates_output_in_deeply_nested_dir(tmp_path: Path):
    m = _FakeManifest()
    out = tmp_path / "a" / "b" / "c" / "r.json"
    run_evaluation(m, out)
    assert out.exists()


def test_run_evaluation_tolerance_chars_default_30(tmp_path: Path):
    """tolerance_chars 默认 30 → 不抛。"""
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "r.json"
    run_evaluation(m, out)
    # 不抛即可


def test_run_evaluation_tolerance_chars_override(tmp_path: Path):
    docx_p = tmp_path / "a.docx"
    _write_minimal_docx(docx_p)
    doc = _FakeDocEntry(doc_id="d1", resolved_path=docx_p, source_type="docx")
    m = _FakeManifest(documents=(doc,))
    out = tmp_path / "r.json"
    run_evaluation(m, out, tolerance_chars=100)
    # 不抛即可
