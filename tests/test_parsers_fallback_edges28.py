r"""app/parsers/fallback_parser.py 边角测试 - 第二十八轮（Round 1416）。

新角度（probe 实证）三个未锁的非正文 PDF 结构可见性：
- /Annots 文本注解（含 Contents 与 T 作者）：完全不可见、
  无告警——只有正文流进 element
- 无 /Contents 键的页：静默跳过，页码保留（页 1/页 3 出
  元素、页 2 无）；跨空页 chunk 照常合并
- /Outlines 书签（Outline/Title/Dest）：不可见
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _xref_pdf(objs):
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


def _annot_pdf(tmp_path):
    c = (b"BT /F1 12 Tf 72 700 Td "
         b"(Annotated body text "
         b"here.) Tj ET")
    p = tmp_path / "ann.pdf"
    p.write_bytes(_xref_pdf({
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
            b"/Annots [7 0 R] "
            b"/Resources << /Font "
            b"<< /F1 6 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(c)).encode()
            + b" >>\nstream\n" + c
            + b"\nendstream"),
        7: (b"<< /Type /Annot "
            b"/Subtype /Text "
            b"/Rect [100 690 120 710] "
            b"/Contents (Hidden "
            b"annotation note text) "
            b"/T (Reviewer) >>")}))
    return p


def _nocontents_pdf(tmp_path):
    c1 = (b"BT /F1 12 Tf 72 700 Td "
          b"(First page before "
          b"empty.) Tj ET")
    c3 = (b"BT /F1 12 Tf 72 700 Td "
          b"(Third page after "
          b"empty.) Tj ET")
    p = tmp_path / "nocontents.pdf"
    p.write_bytes(_xref_pdf({
        8: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>"),
        1: (b"<< /Type /Catalog "
            b"/Pages 2 0 R "
            b"/Outlines 9 0 R >>"),
        2: (b"<< /Type /Pages /Kids "
            b"[3 0 R 5 0 R 6 0 R] "
            b"/Count 3 >>"),
        3: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 8 0 R >> >> "
            b"/Contents 4 0 R >>"),
        4: (b"<< /Length "
            + str(len(c1)).encode()
            + b" >>\nstream\n" + c1
            + b"\nendstream"),
        5: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 8 0 R >> >> >>"),
        6: (b"<< /Type /Page /Parent "
            b"2 0 R /MediaBox "
            b"[0 0 612 792] "
            b"/Resources << /Font "
            b"<< /F1 8 0 R >> >> "
            b"/Contents 7 0 R >>"),
        7: (b"<< /Length "
            + str(len(c3)).encode()
            + b" >>\nstream\n" + c3
            + b"\nendstream"),
        9: (b"<< /Type /Outlines "
            b"/First 10 0 R "
            b"/Count 1 >>"),
        10: (b"<< /Type /Outline "
             b"/Title (Bookmark "
             b"title unseen) "
             b"/Dest [3 0 R /XYZ "
             b"0 792 0] >>")}))
    return p


# ---------- /Annots ----------

def test_annot_invisible(tmp_path):
    doc = FallbackParser().parse(
        _annot_pdf(tmp_path),
        compute_file_hash(
            _annot_pdf(tmp_path)))
    assert [e.content
            for e in doc.elements] == [
        "Annotated body text "
        "here."]
    assert len(doc.elements) == 1


def test_annot_no_warnings(tmp_path):
    doc = FallbackParser().parse(
        _annot_pdf(tmp_path),
        compute_file_hash(
            _annot_pdf(tmp_path)))
    assert doc.warnings == []


def test_annot_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = FallbackParser().parse(
        _annot_pdf(tmp_path),
        compute_file_hash(
            _annot_pdf(tmp_path)))
    assert is_valid(doc.to_dict())


# ---------- 无 /Contents 页 + /Outlines ----------

def test_nocontents_two_elements(
        tmp_path):
    doc = FallbackParser().parse(
        _nocontents_pdf(tmp_path),
        compute_file_hash(
            _nocontents_pdf(
                tmp_path)))
    assert [e.content
            for e in doc.elements] == [
        "First page before empty.",
        "Third page after empty."]


def test_nocontents_page_numbers(
        tmp_path):
    doc = FallbackParser().parse(
        _nocontents_pdf(tmp_path),
        compute_file_hash(
            _nocontents_pdf(
                tmp_path)))
    assert [e.source_locator["page"]
            for e in doc.elements
            ] == [1, 3]


def test_outlines_invisible(tmp_path):
    doc = FallbackParser().parse(
        _nocontents_pdf(tmp_path),
        compute_file_hash(
            _nocontents_pdf(
                tmp_path)))
    for e in doc.elements:
        assert "Bookmark" not in \
            e.content


def test_nocontents_no_warnings(
        tmp_path):
    doc = FallbackParser().parse(
        _nocontents_pdf(tmp_path),
        compute_file_hash(
            _nocontents_pdf(
                tmp_path)))
    assert doc.warnings == []


def test_nocontents_schema_valid(
        tmp_path):
    from app.schema import is_valid
    doc = FallbackParser().parse(
        _nocontents_pdf(tmp_path),
        compute_file_hash(
            _nocontents_pdf(
                tmp_path)))
    assert is_valid(doc.to_dict())


def test_nocontents_pipeline_chunk(
        tmp_path):
    p = _nocontents_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "First page before empty. "
        "Third page after empty.")
    assert len(doc.chunks[0]
               .source_element_ids) == 2


def test_nocontents_pdfloc_green(
        tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    p = _nocontents_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf",
        None)
    assert m[
        "pdf_locator_valid_ratio"] == {
        "value": 1.0, "reason": None}
