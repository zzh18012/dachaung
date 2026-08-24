r"""app/parsers/fallback_parser.py 边角测试 - 第二十一轮（Round 1406）。

新角度（probe 实证）两个未锁的 PDF 文本运算符几何：
- TJ 数组带字距调整（[(K) -120 (er) 40 (ned ...)]）：文本
  正确拼回（'Kerned text line'），调整只进 x1 不进字符
- 字号 24 / 6：bbox 高度精确等于字号（24.0 / 6.0），
  top 随字号偏移（24pt y=700 → 72.968；6pt y=640 →
  147.242）；heading 判定与字号无关（有无句号）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _xref_pdf(content):
    objs = {
        6: (b"<< /Type /Font /Subtype "
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
            b"<< /F1 6 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n" + content
            + b"\nendstream"),
    }
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
            ).encode() \
        + b"0000000000 65535 f \n"
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


def _tj_pdf():
    return _xref_pdf(
        b"BT /F1 12 Tf 72 700 Td "
        b"[(K) -120 (er) 40 (ned "
        b"tex) 20 (t li) -30 (ne)] "
        b"TJ ET "
        b"BT /F1 12 Tf 72 640 Td "
        b"[(A) -250 (V second) 15 "
        b"( kerned words)] TJ ET")


def _font_pdf():
    return _xref_pdf(
        b"BT /F1 24 Tf 72 700 Td "
        b"(Big Font Heading) Tj ET "
        b"BT /F1 6 Tf 72 640 Td "
        b"(Tiny six point footnote "
        b"text.) Tj ET")


def _parse(tmp_path, name,
           builder):
    p = tmp_path / name
    p.write_bytes(builder())
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- TJ 字距数组 ----------

def test_tj_texts(tmp_path):
    doc = _parse(tmp_path, "tj.pdf",
                 _tj_pdf)
    assert [e.content
            for e in doc.elements] == [
        "Kerned text line",
        "AV second kerned words"]


def test_tj_types(tmp_path):
    doc = _parse(tmp_path, "tj.pdf",
                 _tj_pdf)
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading"]


def test_tj_bboxes(tmp_path):
    doc = _parse(tmp_path, "tj.pdf",
                 _tj_pdf)
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        156.456, 94.48400000000004]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 142.48400000000004,
        208.212, 154.48400000000004]


def test_tj_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path, "tj.pdf",
                 _tj_pdf)
    assert is_valid(doc.to_dict())


def test_tj_pipeline_chunk(tmp_path):
    p = tmp_path / "tj.pdf"
    p.write_bytes(_tj_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 2
    assert [c.text
            for c in doc.chunks] == [
        "Kerned text line",
        "AV second kerned words"]


# ---------- 字号几何 ----------

def test_font24_bbox(tmp_path):
    doc = _parse(tmp_path, "fs.pdf",
                 _font_pdf)
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 72.96799999999996,
                 257.424,
                 96.96799999999996]}


def test_font6_bbox(tmp_path):
    doc = _parse(tmp_path, "fs.pdf",
                 _font_pdf)
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 147.24199999999996,
                 143.37,
                 153.24199999999996]}


def test_bbox_height_equals_fontsize(
        tmp_path):
    doc = _parse(tmp_path, "fs.pdf",
                 _font_pdf)
    b24 = doc.elements[
        0].source_locator["bbox"]
    b6 = doc.elements[
        1].source_locator["bbox"]
    assert (b24[3] - b24[1]) == 24.0
    assert (b6[3] - b6[1]) == 6.0


def test_font_types(tmp_path):
    """heading 判定与字号无关：
    大字无句号 → heading，小字句号 →
    paragraph。"""
    doc = _parse(tmp_path, "fs.pdf",
                 _font_pdf)
    assert [e.type
            for e in doc.elements] == [
        "heading", "paragraph"]


def test_font_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path, "fs.pdf",
                 _font_pdf)
    assert is_valid(doc.to_dict())


def test_font_pipeline_chunk(tmp_path):
    p = tmp_path / "fs.pdf"
    p.write_bytes(_font_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "Big Font Heading Tiny six "
        "point footnote text.")
