r"""app/parsers/fallback_parser.py 边角测试 - 第二十轮（Round 1405）。

新角度（probe 实证）两个未锁的真实 PDF 编码事实：
- /Filter /FlateDecode 压缩内容流：zlib 解压后抽取与未压缩
  完全一致（bbox 数值同 y=700→top 82.484 / y=640→142.484）
- /Contents [4 0 R 5 0 R] 数组多流：按数组顺序拼接——
  流 1 的 heading 先于流 2 的 paragraph；同一 page 1
"""

from __future__ import annotations

import tempfile
import zlib
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


def _t(x, y, s):
    return (f"BT /F1 12 Tf {x} {y} "
            f"Td ({s}) Tj ET").encode()


def _flate_pdf():
    raw = b" ".join([
        _t(72, 700,
           "Compressed heading"),
        _t(72, 640,
           "Compressed body text "
           "survives zlib round "
           "trip.")])
    comp = zlib.compress(raw)
    return _xref_pdf({
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
        4: (b"<< /Filter "
            b"/FlateDecode /Length "
            + str(len(comp)).encode()
            + b" >>\nstream\n" + comp
            + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>")})


def _array_pdf():
    s1 = _t(72, 700,
            "Array first heading")
    s2 = _t(72, 640,
            "Array second stream "
            "body text.")
    return _xref_pdf({
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
            b"/Contents [4 0 R "
            b"5 0 R] >>"),
        4: (b"<< /Length "
            + str(len(s1)).encode()
            + b" >>\nstream\n" + s1
            + b"\nendstream"),
        5: (b"<< /Length "
            + str(len(s2)).encode()
            + b" >>\nstream\n" + s2
            + b"\nendstream"),
        6: (b"<< /Type /Font /Subtype "
            b"/Type1 /BaseFont "
            b"/Helvetica >>")})


def _parse(tmp_path, name,
           builder):
    p = tmp_path / name
    p.write_bytes(builder())
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- FlateDecode ----------

def test_flate_elements(tmp_path):
    doc = _parse(tmp_path,
                 "flate.pdf",
                 _flate_pdf)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading",
         "Compressed heading"),
        ("paragraph",
         "Compressed body text "
         "survives zlib round "
         "trip.")]


def test_flate_heading_bbox(tmp_path):
    doc = _parse(tmp_path,
                 "flate.pdf",
                 _flate_pdf)
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 186.04799999999997,
                 94.48400000000004]}


def test_flate_paragraph_bbox(tmp_path):
    doc = _parse(tmp_path,
                 "flate.pdf",
                 _flate_pdf)
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 142.48400000000004,
                 318.084,
                 154.48400000000004]}


def test_flate_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 "flate.pdf",
                 _flate_pdf)
    assert is_valid(doc.to_dict())


def test_flate_no_warnings(tmp_path):
    doc = _parse(tmp_path,
                 "flate.pdf",
                 _flate_pdf)
    assert doc.warnings == []


def test_flate_pipeline_chunk(tmp_path):
    p = tmp_path / "flate.pdf"
    p.write_bytes(_flate_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "Compressed heading "
        "Compressed body text "
        "survives zlib round trip.")
    assert len(doc.chunks[0]
               .source_element_ids) == 2


# ---------- /Contents 数组 ----------

def test_array_elements(tmp_path):
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading",
         "Array first heading"),
        ("paragraph",
         "Array second stream "
         "body text.")]


def test_array_order_preserved(
        tmp_path):
    """流 1 的 heading 元素在流 2
    的 paragraph 之前。"""
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    types = [e.type
             for e in doc.elements]
    assert types == [
        "heading", "paragraph"]
    assert doc.elements[
        0].content.startswith(
        "Array first")


def test_array_bboxes(tmp_path):
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 169.368,
                 94.48400000000004]}
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 142.48400000000004,
                 238.068,
                 154.48400000000004]}


def test_array_both_page_one(tmp_path):
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    assert [e.source_locator["page"]
            for e in doc.elements
            ] == [1, 1]


def test_array_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    assert is_valid(doc.to_dict())


def test_array_no_warnings(tmp_path):
    doc = _parse(tmp_path,
                 "arr.pdf",
                 _array_pdf)
    assert doc.warnings == []


def test_array_pipeline_chunk(tmp_path):
    p = tmp_path / "arr.pdf"
    p.write_bytes(_array_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "Array first heading "
        "Array second stream "
        "body text.")
    assert len(doc.chunks[0]
               .source_element_ids) == 2
