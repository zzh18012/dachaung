r"""app/parsers/fallback_parser.py 边角测试 - 第三十六轮（Round 1427）。

新角度（probe 实证）MediaBox 继承 + 空 /Contents（历史
MediaBox 全挂在页对象上）：
- /Pages 树上 /MediaBox [0 0 612 792]、页省略：正常继承，
  bbox 与页级版逐位一致
- 继承 [50 50 562 742] 非零原点：top 按继承 box 高 692
  计 → **负 top**（-17.516）
- /Contents []（空数组）：0 元素 + pdf_no_text_extracted
  告警；parse 层 schema 仍绿、管线层 no_extracted_elements
  结构化错误（doc None）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(objs):
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (f"{oid} 0 obj\n"
                .encode()
                + objs[oid]
                + b"\nendobj\n")
    xref_pos = len(out)
    maxid = max(objs)
    out += (f"xref\n0 {maxid + 1}\n"
            .encode()
            + b"0000000000 65535 f \n")
    for oid in range(1, maxid + 1):
        out += (
            f"{offsets[oid]:010d} "
            f"00000 n \n".encode()
            if oid in offsets
            else b"0000000000 65535 f \n")
    out += (f"trailer\n<< /Size "
            f"{maxid + 1} /Root 1 0 R "
            f">>\nstartxref\n{xref_pos}"
            f"\n%%EOF").encode()
    return bytes(out)


def _inh_pdf(tmp_path, box):
    c = (b"BT /F1 12 Tf 72 700 Td "
         b"(Inherited box text) "
         b"Tj ET")
    p = tmp_path / "inh.pdf"
    p.write_bytes(_build({
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 /MediaBox "
            + box + b" >>"),
        3: (b"<< /Type /Page /Parent "
            b"2 0 R /Resources "
            b"<< /Font << /F1 5 0 R "
            b">> >> /Contents "
            b"4 0 R >>"),
        4: (b"<< /Length "
            + str(len(c)).encode()
            + b" >>\nstream\n" + c
            + b"\nendstream")}))
    return p


def _eca_pdf(tmp_path):
    p = tmp_path / "eca.pdf"
    p.write_bytes(_build({
        5: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >> "
            b"/Contents [] >>")}))
    return p


# ---------- MediaBox 继承 ----------

def test_inherited_zero_origin(
        tmp_path):
    p = _inh_pdf(
        tmp_path, b"[0 0 612 792]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 164.052,
                 94.48400000000004]}
    assert doc.elements[
        0].content == \
        "Inherited box text"


def test_inherited_nonzero_origin(
        tmp_path):
    """继承 [50 50 562 742]：top 按
    box 高 692 计 → 负 top。"""
    p = _inh_pdf(
        tmp_path, b"[50 50 562 742]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, -17.515999999999963,
        164.05199999999996,
        -5.515999999999963]


def test_inherited_no_warnings(
        tmp_path):
    p = _inh_pdf(
        tmp_path, b"[50 50 562 742]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_inherited_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _inh_pdf(
        tmp_path, b"[0 0 612 792]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_inherited_chunks(tmp_path):
    p = _inh_pdf(
        tmp_path, b"[0 0 612 792]")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Inherited box text"]


# ---------- 空 /Contents 数组 ----------

def test_eca_zero_elements(
        tmp_path):
    p = _eca_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert doc.chunks == []


def test_eca_warning(tmp_path):
    p = _eca_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [(w.code, w.reason)
            for w in doc.warnings] == [
        ("pdf_no_text_extracted",
         "pdfplumber 未提取到任何文本"
         "/表格/图片（可能为扫描件，"
         "本阶段不支持 OCR）")]


def test_eca_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _eca_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_eca_pipeline_error(
        tmp_path):
    p = _eca_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]
    details = errors[0].details
    assert details[
        "source_type"] == "pdf"
    assert details["warnings"][0][
        "code"] == \
        "pdf_no_text_extracted"
