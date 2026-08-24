r"""app/parsers/fallback_parser.py 边角测试 - 第十三轮（Round 1389）。

新角度（probe 实证）：cp1252/WinAnsi 重音字符穿真实 PDF 字节
（font 声明 /Encoding /WinAnsiEncoding，历史测试从未在真 PDF
里放过非 ASCII）：
- 'Café Münchén naïve résumé' 逐字符无损往返
- 'Überstraße déjà vu' 正文段无损
- 重音不影响分类（短行无句号仍 heading / 长行带句号仍
  paragraph）
- 'Figure 1: café caption' 带 Unicode 仍命中 caption_regex
- schema / 管线 / 指标（tpe、cmp/cmr、hbc）全绿
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _build_pdf(pages_lines):
    n_pages = len(pages_lines)
    page_ids = [3 + i * 2
                for i in range(n_pages)]
    content_ids = [4 + i * 2
                   for i in range(n_pages)]
    font_id = 3 + n_pages * 2
    objs = {font_id: (b"<< /Type /Font "
                      b"/Subtype /Type1 "
                      b"/BaseFont /Helvetica "
                      b"/Encoding "
                      b"/WinAnsiEncoding >>")}
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
            raw = line.encode("cp1252")
            esc = raw.replace(
                b"\\", b"\\\\").replace(
                b"(", b"\\(").replace(
                b")", b"\\)")
            blocks.append(
                b"BT /F1 12 Tf 72 "
                + str(y).encode()
                + b" Td (" + esc
                + b") Tj ET")
        stream = b" ".join(blocks)
        objs[cid] = (
            b"<< /Length "
            + str(len(stream)).encode()
            + b" >>\nstream\n" + stream
            + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(out)
        out += (str(oid).encode()
                + b" 0 obj\n" + objs[oid]
                + b"\nendobj\n")
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


_H = "Café Münchén naïve résumé"
_B = ("Accented body: Überstraße "
      "déjà vu ends here.")


def _parse(tmp_path, pages, name="u.pdf"):
    p = tmp_path / name
    p.write_bytes(_build_pdf(pages))
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 逐字符往返 ----------

def test_heading_unicode_roundtrip(tmp_path):
    doc = _parse(tmp_path, [[(700, _H)]])
    assert doc.elements[0].content == \
        "Café Münchén naïve résumé"


def test_body_unicode_roundtrip(tmp_path):
    doc = _parse(tmp_path,
                 [[(640, _B)]])
    assert doc.elements[0].content == (
        "Accented body: Überstraße "
        "déjà vu ends here.")


def test_all_accent_chars_preserved(
        tmp_path):
    doc = _parse(tmp_path,
                 [[(700, "àâçéèêëîïôù"
                     "ûüßÆœ")]])
    assert doc.elements[0].content == (
        "àâçéèêëîïôùûüßÆœ")


def test_no_mojibake(tmp_path):
    doc = _parse(tmp_path, [[(700, _H)]])
    c = doc.elements[0].content
    assert "Ã" not in c
    assert "Â" not in c
    assert "�" not in c


# ---------- 分类不受重音影响 ----------

def test_unicode_short_no_period_heading(
        tmp_path):
    doc = _parse(tmp_path, [[(700, _H)]])
    assert doc.elements[0].type == \
        "heading"
    assert doc.elements[0].metadata == {
        "level": 0,
        "heuristic": "short_line"}


def test_unicode_long_period_paragraph(
        tmp_path):
    doc = _parse(tmp_path, [[(640, _B)]])
    assert doc.elements[0].type == \
        "paragraph"
    assert doc.elements[0].metadata == {}


def test_unicode_caption(tmp_path):
    doc = _parse(tmp_path,
                 [[(580, "Figure 1: café "
                     "caption über")]])
    assert doc.elements[0].type == \
        "caption"
    assert doc.elements[0].metadata == {
        "heuristic": "caption_regex"}


# ---------- 双行板 ----------

def test_two_unicode_lines(tmp_path):
    doc = _parse(tmp_path,
                 [[(700, _H), (640, _B)]])
    assert [e.content
            for e in doc.elements] == [
        _H, _B]


def test_unicode_tight_merge(tmp_path):
    doc = _parse(tmp_path,
                 [[(700, "café line one"),
                   (686, "café line two")]])
    assert len(doc.elements) == 1
    assert doc.elements[0].content == (
        "café line one café line two")


# ---------- locator / schema ----------

def test_unicode_bbox_numeric(tmp_path):
    doc = _parse(tmp_path, [[(700, _H)]])
    bb = doc.elements[0].source_locator[
        "bbox"]
    assert len(bb) == 4
    assert bb[0] == 72.0


def test_unicode_passes_schema(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 [[(700, _H), (640, _B)]])
    assert is_valid(doc.to_dict())


# ---------- 管线 + 指标 ----------

def test_unicode_pipeline_chunk(tmp_path):
    from app.pipeline import \
        process_single
    p = tmp_path / "p.pdf"
    p.write_bytes(
        _build_pdf([[(700, _H),
                     (640, _B)]]))
    doc, errors = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert "Überstraße" in \
        doc.chunks[0].text
    assert "naïve" in \
        doc.chunks[0].text


def test_unicode_metrics(tmp_path):
    from evaluation.metrics import \
        compute_automatic_metrics
    from app.pipeline import \
        process_single
    p = tmp_path / "m.pdf"
    p.write_bytes(
        _build_pdf([[(700, _H),
                     (640, _B)]]))
    doc, _ = process_single(
        p, None, parser_name="fallback",
        max_chars=800)
    m = compute_automatic_metrics(
        doc.to_dict(), None, "pdf", None)
    assert m["text_preservation_equal"] \
        == {"value": True,
            "reason": None}
    assert m[
        "text_char_multiset_precision"] \
        == {"value": 1.0, "reason": None}
    assert m[
        "text_char_multiset_recall"] == {
        "value": 1.0, "reason": None}
    assert m[
        "heading_boundary_compliance"] == {
        "value": 1.0, "reason": None}
