r"""app/parsers/fallback_parser.py 边角测试 - 第五十三轮（Round 1447）。

新角度（probe 实证）注释层 + 空白页（历史只碰正文内容流，
/Annots /Outlines 与空白页从未考察）：
- /Annots Link 注释（/Contents 'Hidden annotation text'）
  **完全不可见**——正文照常，无告警
- /Outlines 书签（/Title 'Bookmark title text' + PageMode
  UseOutlines）同样不可见
- 空白中间页：干净跳过——elements 页号 1/3、无幽灵元素、
  无告警
- 全空白 PDF：0 元素 + pdf_no_text_extracted
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
    mx = max(objs)
    out += (b"xref\n0 "
            + str(mx + 1).encode()
            + b"\n0000000000 65535 f \n")
    for oid in range(1, mx + 1):
        if oid in offsets:
            out += ("%010d 00000 n \n"
                    % offsets[oid]).encode()
        else:
            out += b"0000000000 65535 f \n"
    out += (b"trailer\n<< /Size "
            + str(mx + 1).encode()
            + b" /Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


_BODY = (b"BT /F1 12 Tf 72 700 Td "
         b"(Annotated body text)"
         b" Tj ET")


def _base_objs():
    return {
        5: (b"<< /Type /Font /Subtype"
            b" /Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R >>"),
        2: (b"<< /Type /Pages "
            b"/Kids [3 0 R] "
            b"/Count 1 >>"),
        3: (b"<< /Type /Page /Parent"
            b" 2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(_BODY)).encode()
            + b" >>\nstream\n" + _BODY
            + b"\nendstream"),
    }


# ---------- /Annots ----------

def _annots_pdf(tmp_path):
    objs = _base_objs()
    objs[3] = (
        objs[3].replace(
            b"/Contents 4 0 R >>",
            b"/Contents 4 0 R"
            b" /Annots [6 0 R] >>"))
    objs[6] = (
        b"<< /Type /Annot /Subtype"
        b" /Link /Rect "
        b"[72 680 200 700] "
        b"/Contents (Hidden "
        b"annotation text) "
        b"/A << /S /URI /URI "
        b"(https://example.com)"
        b" >> >>")
    p = tmp_path / "ann.pdf"
    p.write_bytes(_build(objs))
    return p


def test_annot_invisible(tmp_path):
    p = _annots_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Annotated body text"]
    assert doc.warnings == []


def test_annot_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _annots_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_annot_chunk(tmp_path):
    p = _annots_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Annotated body text"]


# ---------- /Outlines ----------

def _outlines_pdf(tmp_path):
    objs = _base_objs()
    objs[1] = (b"<< /Type /Catalog "
               b"/Pages 2 0 R"
               b" /Outlines 7 0 R"
               b" /PageMode "
               b"/UseOutlines >>")
    objs[7] = (b"<< /Type /Outlines"
               b" /First 8 0 R"
               b" /Last 8 0 R"
               b" /Count 1 >>")
    objs[8] = (b"<< /Type /"
               b"OutlineItem /Title"
               b" (Bookmark title text)"
               b" /Parent 7 0 R >>")
    p = tmp_path / "out.pdf"
    p.write_bytes(_build(objs))
    return p


def test_outline_invisible(
        tmp_path):
    p = _outlines_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Annotated body text"]
    assert doc.warnings == []


def test_outline_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _outlines_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


# ---------- 空白页 ----------

def _build_pages(pages):
    n = len(pages)
    kids = b" ".join(
        b"%d 0 R" % (10 + i)
        for i in range(n))
    objs = {
        5: (b"<< /Type /Font /"
            b"Subtype /Type1 /"
            b"BaseFont /"
            b"Helvetica >>"),
        1: (b"<< /Type /Catalog /"
            b"Pages 2 0 R >>"),
        2: (b"<< /Type /Pages /"
            b"Kids [" + kids
            + b"] /Count "
            + str(n).encode()
            + b" >>"),
    }
    for i, content in enumerate(pages):
        objs[10 + i] = (
            b"<< /Type /Page /Parent"
            b" 2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >>"
            b" /Contents "
            + str(20 + i).encode()
            + b" 0 R >>")
        objs[20 + i] = (
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream")
    return _build(objs)


def test_blank_middle_skipped(
        tmp_path):
    p = tmp_path / "blank.pdf"
    p.write_bytes(_build_pages([
        b"BT /F1 12 Tf 72 700 Td "
        b"(Before blank) Tj ET",
        b"",
        b"BT /F1 12 Tf 72 700 Td "
        b"(After blank) Tj ET"]))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Before blank",
        "After blank"]
    assert [e.source_locator["page"]
            for e in doc.elements] == [
        1, 3]
    assert doc.warnings == []


def test_blank_middle_chunks(
        tmp_path):
    p = tmp_path / "blankc.pdf"
    p.write_bytes(_build_pages([
        b"BT /F1 12 Tf 72 700 Td "
        b"(Before blank) Tj ET",
        b"",
        b"BT /F1 12 Tf 72 700 Td "
        b"(After blank) Tj ET"]))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Before blank",
        "After blank"]


def test_all_blank_warning(
        tmp_path):
    p = tmp_path / "ab.pdf"
    p.write_bytes(_build_pages(
        [b"", b""]))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_all_blank_pipeline(
        tmp_path):
    p = tmp_path / "abp.pdf"
    p.write_bytes(_build_pages(
        [b"", b""]))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


def test_blank_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = tmp_path / "bs.pdf"
    p.write_bytes(_build_pages([
        b"BT /F1 12 Tf 72 700 Td "
        b"(Only page) Tj ET",
        b""]))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
