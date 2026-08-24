r"""evaluation/cli.py 边角测试 - 第一百八十二轮（Round 1395）。

新角度（probe 实证）：富真 PDF（heading×2 页 + 长段 + 题注
+ 画线表 + Image XObject）穿 manifest 评测全链：
- ECT 全五类 {heading 3, paragraph 2, caption 1, table 1,
  image 1}，expectations 对齐 → sdc/sdt 0
- **runner 给 parse 传 image_output_dir** → PDF 图片经
  pypdfium2 真落盘 → irer 1.0（裸 process_single 是
  '(unrendered)'，评测路径不是）
- pdfloc 1.0（双页 bbox 全有效）、hbc/crir/tpe 全绿
- 表内文字双份（'tA1 tB1' heading + table 元素）
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from evaluation.cli import main


def _build_rich_pdf():
    p1_text = ("A long body paragraph "
               "under the first heading "
               "with enough characters "
               "to exercise the sequential "
               "chunk strategy fully "
               "here.")
    p2_text = ("Second body paragraph "
               "on page two also long "
               "enough for its own "
               "treatment in the chunker "
               "pipeline without "
               "trouble.")
    grid = [
        "1 w 0 0 0 RG",
        "100 450 m 400 450 l S",
        "100 400 m 400 400 l S",
        "100 450 m 100 400 l S",
        "250 450 m 250 400 l S",
        "400 450 m 400 400 l S",
    ]

    def text(x, y, t):
        return (f"BT /F1 12 Tf {x} {y} "
                f"Td ({t}) Tj ET")

    c1 = "\n".join(grid + [
        text(72, 700, "Rich Doc Heading"),
        text(72, 640, p1_text),
        text(110, 420, "tA1"),
        text(260, 420, "tB1"),
        text(72, 580,
             "Figure 1: rich caption"),
        "q 80 0 0 80 450 600 cm "
        "/Im1 Do Q"]).encode()
    c2 = "\n".join([
        text(72, 700, "Page Two Heading"),
        text(72, 640, p2_text)]).encode()
    img_data = b"\x00\x00\xff"
    objs = {
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages /Kids "
            b"[3 0 R 7 0 R] "
            b"/Count 2 >>"),
        3: (b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            b"6 0 R >> /XObject << /Im1 "
            b"5 0 R >> >> /Contents "
            b"4 0 R >>"),
        7: (b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 "
            b"6 0 R >> >> /Contents "
            b"8 0 R >>"),
        5: (b"<< /Type /XObject /Subtype "
            b"/Image /Width 1 /Height 1 "
            b"/ColorSpace /DeviceRGB "
            b"/BitsPerComponent 8 "
            b"/Length 3 >>\nstream\n"
            + img_data + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        4: (b"<< /Length "
            + str(len(c1)).encode()
            + b" >>\nstream\n" + c1
            + b"\nendstream"),
        8: (b"<< /Length "
            + str(len(c2)).encode()
            + b" >>\nstream\n" + c2
            + b"\nendstream"),
    }
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n".encode()
                + objs[oid] + b"\nendobj\n")
    xref_pos = len(out)
    out += (b"xref\n0 9\n"
            b"0000000000 65535 f \n")
    for oid in range(1, 9):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 9 "
            b"/Root 1 0 R >>\nstartxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


_ECT = {"heading": 3, "paragraph": 2,
        "caption": 1, "table": 1,
        "image": 1}


def _run(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples"
     / "rich.pdf").write_bytes(
        _build_rich_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "rich",
             "path": "samples/rich.pdf",
             "source_type": "pdf",
             "expectations": {
                 "element_count_by_type":
                     _ECT}}]}),
        encoding="utf-8")
    rep = tmp_path / "r.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["run", "--manifest",
                   str(mf),
                   "--output", str(rep),
                   "--parser", "fallback",
                   "--max-chars", "800"])
    data = json.loads(
        rep.read_text(encoding="utf-8"))
    return rc, data, rep


# ---------- run ----------

def test_run_rc0(tmp_path):
    rc, _, _ = _run(tmp_path)
    assert rc == 0


def test_run_stdout_success(tmp_path):
    (tmp_path / "samples").mkdir()
    (tmp_path / "samples"
     / "rich.pdf").write_bytes(
        _build_rich_pdf())
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "rich",
             "path": "samples/rich.pdf",
             "source_type": "pdf",
             "expectations": {
                 "element_count_by_type":
                     _ECT}}]}),
        encoding="utf-8")
    rep = tmp_path / "r.json"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main(["run", "--manifest", str(mf),
              "--output", str(rep),
              "--parser", "fallback",
              "--max-chars", "800"])
    assert "documents=1（成功 1，失败 0）" \
        in buf.getvalue()


# ---------- per_doc 指标 ----------

def test_ect_full(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "element_count_by_type"] == {
        "value": _ECT, "reason": None}


def test_sdc_zero(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "silent_drop_count"] == {
        "value": 0, "reason": None}


def test_irer_one_rendered(tmp_path):
    """runner 传 image_output_dir → 图片
    真落盘 → 存在率 1.0。"""
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "image_resource_exists_ratio"] == {
        "value": 1.0, "reason": None}


def test_pdfloc_one(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}


def test_hbc_one(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}


def test_crir_one(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "chunk_reference_intact_ratio"] == {
        "value": 1.0, "reason": None}


def test_tpe_true(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["per_doc"][0]["metrics"][
        "text_preservation_equal"] == {
        "value": True, "reason": None}


# ---------- summary ----------

def test_sdt_zero(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["summary"][
        "silent_drop_total"] == 0


def test_counts_eight(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["summary"]["counts"][
        "element_count_total"] == {
        "sum": 8, "participating_docs": 1}


def test_devset_pdf_one(tmp_path):
    _, data, _ = _run(tmp_path)
    assert data["devset"]["pdf_count"] \
        == 1
    assert data["devset"]["docx_count"] \
        == 0


# ---------- validate-report ----------

def test_validate_report_ok(tmp_path):
    _, _, rep = _run(tmp_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(["validate-report", str(rep)])
    assert rc == 0
