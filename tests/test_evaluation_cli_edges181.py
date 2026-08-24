r"""evaluation/cli.py 边角测试 - 第一百八十一轮（Round 1388）。

新角度（probe 实证）：真文件管线里的期望偏差与解析失败共存：
- 好 PDF 期望多算（heading 3 vs 实际 1、paragraph 2 vs
  实际 1）→ silent_drop_count = 3（逐类型缺口求和）
- 坏 PDF 字节 → error_code=pdfplumber_open_failed、
  pipeline_success False、全部指标 null + pipeline_failed
- 聚合层：sdt 只累 participating（3），失败文档不进
  counts；rate 0.5；hbc not_evaluated +1
- validate-report 对含失败文档的报告仍 rc 0
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from evaluation.cli import main


def _build_pdf(pages_lines):
    n_pages = len(pages_lines)
    page_ids = [3 + i * 2
                for i in range(n_pages)]
    content_ids = [4 + i * 2
                   for i in range(n_pages)]
    font_id = 3 + n_pages * 2
    objs = {font_id: b"<< /Type /Font "
                    b"/Subtype /Type1 "
                    b"/BaseFont /Helvetica >>"}
    objs[1] = (b"<< /Type /Catalog "
               b"/Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R"
                    for pid in page_ids)
    objs[2] = (f"<< /Type /Pages /Kids "
               f"[{kids}] /Count "
               f"{n_pages} >>").encode()
    for i, lines in enumerate(pages_lines):
        pid = page_ids[i]
        cid = content_ids[i]
        objs[pid] = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 "
            f"{font_id} 0 R >> >> /Contents "
            f"{cid} 0 R >>").encode()
        blocks = []
        for (y, line) in lines:
            esc = line.replace(
                "\\", r"\\").replace(
                "(", r"\(").replace(
                ")", r"\)")
            blocks.append(
                f"BT /F1 12 Tf 72 {y} Td "
                f"({esc}) Tj ET")
        stream = " ".join(blocks).encode()
        objs[cid] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n" + stream
            + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid] + b"\nendobj\n")
    xref_pos = len(out)
    maxid = max(objs)
    out += (f"xref\n0 {maxid + 1}\n"
            .encode()
            + b"0000000000 65535 f \n")
    for oid in range(1, maxid + 1):
        out += (
            f"{offsets[oid]:010d} 00000 n \n"
            .encode() if oid in offsets
            else b"0000000000 65535 f \n")
    out += (f"trailer\n<< /Size "
            f"{maxid + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF"
            ).encode()
    return bytes(out)


def _run(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples" / "good.pdf").write_bytes(
        _build_pdf([[(700, "Only Heading"),
                     (640, "Body line ends "
                           "here.")]]))
    (tmp_path / "samples" / "bad.pdf").write_bytes(
        b"%PDF-1.4\nbroken\n%%EOF")
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "g",
             "path": "samples/good.pdf",
             "source_type": "pdf",
             "expectations": {
                 "element_count_by_type": {
                     "heading": 3,
                     "paragraph": 2}}},
            {"doc_id": "b",
             "path": "samples/bad.pdf",
             "source_type": "pdf"}]}),
        encoding="utf-8")
    rep = tmp_path / "r.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["run", "--manifest", str(mf),
                   "--output", str(rep),
                   "--parser", "fallback",
                   "--max-chars", "800"])
    data = json.loads(
        rep.read_text(encoding="utf-8"))
    return rc, buf.getvalue(), data, rep


# ---------- run 摘要 ----------

def test_run_rc0(tmp_path):
    rc, _, _, _ = _run(tmp_path)
    assert rc == 0


def test_run_stdout_one_failure(tmp_path):
    _, so, _, _ = _run(tmp_path)
    assert "documents=2（成功 1，失败 1）" \
        in so


def test_run_stdout_pdf2(tmp_path):
    _, so, _, _ = _run(tmp_path)
    assert "pdf=2 docx=0" in so


# ---------- 好 PDF：期望偏差 ----------

def test_good_doc_success(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "pipeline_success"] == {
        "value": True, "reason": None}


def test_good_doc_sdc_three(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "silent_drop_count"] == {
        "value": 3, "reason": None}


def test_good_doc_actual_ect(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "element_count_by_type"] == {
        "value": {"heading": 1,
                  "paragraph": 1},
        "reason": None}


def test_good_doc_error_code_none(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "error_code"] == {
        "value": None, "reason": None}


# ---------- 坏 PDF：结构化失败 ----------

def test_bad_doc_failed(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "pipeline_success"] == {
        "value": False, "reason": None}


def test_bad_doc_error_code(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "error_code"] == {
        "value": "pdfplumber_open_failed",
        "reason": None}


def test_bad_doc_sdc_pipeline_failed(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "silent_drop_count"] == {
        "value": None,
        "reason": "pipeline_failed"}


def test_bad_doc_ect_pipeline_failed(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "element_count_by_type"] == {
        "value": None,
        "reason": "pipeline_failed"}


def test_bad_doc_hbc_pipeline_failed(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "heading_boundary_compliance"] == {
        "value": None,
        "reason": "pipeline_failed"}


def test_bad_doc_locator_pipeline_failed(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["per_doc"][1]["metrics"][
        "pdf_locator_valid_ratio"] == {
        "value": None,
        "reason": "pipeline_failed"}


# ---------- summary 聚合 ----------

def test_summary_sdt_only_participating(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["summary"][
        "silent_drop_total"] == 3


def test_summary_rate_half(tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["summary"][
        "success_rates"][
        "pipeline_success"] == {
        "success_count": 1, "total": 2,
        "rate": 0.5}


def test_summary_counts_one_doc(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["summary"]["counts"][
        "element_count_total"] == {
        "sum": 2, "participating_docs": 1}


def test_summary_hbc_not_evaluated(
        tmp_path):
    _, _, data, _ = _run(tmp_path)
    assert data["summary"][
        "ratio_macro_averages"][
        "heading_boundary_compliance"] == {
        "macro_average": 1.0,
        "participating_docs": 1,
        "not_evaluated": 1}


# ---------- validate-report ----------

def test_validate_report_with_failure(
        tmp_path):
    _, _, _, rep = _run(tmp_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["validate-report", str(rep)])
    assert rc == 0
