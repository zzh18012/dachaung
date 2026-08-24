r"""app/parsers/fallback_parser.py 边角测试 - 第四十轮（Round 1431）。

新角度（probe 实证）双栏同行文本（历史同行文本无横向间
隔考察）：
- 任意不重叠横向间隔（x=200/300/400）都不分栏——两段合
  成单元素、空格连接（'Left column text Right column
  text'），bbox 横跨两栏 [72.0, ..., 492.7, ...]
- 重叠（x=150，右栏起点落在左栏文本内部）：字符级**交错**
  ——'Left column texRtight column text'（R 按 x 序插进
  'text' 中间），bbox 到 242.7
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _build(content):
    objs = {
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
    out += b"xref\n0 6\n" \
        b"0000000000 65535 f \n"
    for oid in range(1, 6):
        out += ("%010d 00000 n \n"
                % offsets[oid]).encode()
    out += (b"trailer\n<< /Size 6 "
            b"/Root 1 0 R >>\n"
            b"startxref\n"
            + str(xref_pos).encode()
            + b"\n%%EOF")
    return bytes(out)


def _col_pdf(tmp_path, x2):
    c = (b"BT /F1 12 Tf 72 700 Td "
         b"(Left column text) Tj ET "
         b"BT /F1 12 Tf "
         + str(x2).encode()
         + b" 700 Td "
         b"(Right column text) Tj ET")
    p = tmp_path / f"col{x2}.pdf"
    p.write_bytes(_build(c))
    return p


# ---------- 不重叠间隔 ----------

def test_gap400_single_element(
        tmp_path):
    p = _col_pdf(tmp_path, 400)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Left column text "
        "Right column text"]


def test_gap300_single_element(
        tmp_path):
    p = _col_pdf(tmp_path, 300)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert len(doc.elements) == 1


def test_gap200_single_element(
        tmp_path):
    p = _col_pdf(tmp_path, 200)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert len(doc.elements) == 1


def test_gap400_bbox_spans(
        tmp_path):
    p = _col_pdf(tmp_path, 400)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 492.7,
                 94.48400000000004]}


def test_gap_type_heading(
        tmp_path):
    p = _col_pdf(tmp_path, 400)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].type == "heading"


# ---------- 重叠交错 ----------

def test_overlap_interleaved(
        tmp_path):
    p = _col_pdf(tmp_path, 150)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Left column texRtight " \
        "column text"


def test_overlap_bbox(tmp_path):
    p = _col_pdf(tmp_path, 150)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 242.7,
                 94.48400000000004]}


# ---------- 通用 ----------

def test_no_warnings(tmp_path):
    for x2 in (150, 400):
        p = _col_pdf(tmp_path, x2)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert doc.warnings == []


def test_schema_valid(tmp_path):
    from app.schema import is_valid
    for x2 in (150, 400):
        p = _col_pdf(tmp_path, x2)
        doc = FallbackParser().parse(
            p, compute_file_hash(p))
        assert is_valid(doc.to_dict())


def test_chunks(tmp_path):
    p = _col_pdf(tmp_path, 400)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Left column text "
        "Right column text"]
    assert len(doc.chunks[0]
               .source_element_ids) == 1


def test_overlap_chunk(tmp_path):
    p = _col_pdf(tmp_path, 150)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == (
        "Left column texRtight "
        "column text")
