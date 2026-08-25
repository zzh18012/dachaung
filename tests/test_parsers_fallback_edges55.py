r"""app/parsers/fallback_parser.py 边角测试 - 第五十五轮（Round 1449）。

新角度（probe 实证）退化字号 + 嵌套 Form（Tf 只考察过正常
正值；Form 只考察过单层）：
- Tf 0：文本照出 'Zero size text' 但 bbox 塌成**点**
  [72.0, 92.0, 72.0, 92.0]（宽高全 0）
- Tf -12：负字号镜像——字符序**倒序** 'txet ezis
  evitateN'，bbox 反向延伸 [-22.704, ..., 72.0, ...]
  （右端钉在原点 72）
- Tf 12.5：小数字号正常，bbox [72.0, 82.0875, 152.575,
  94.5875]
- 嵌套 Form X1→X2：最深文本照常提取，平移**累加**——
  72+30=102，bbox [102.0, 52.484, 192.708, 64.484]
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _stream(data, extra=b""):
    return (b"<< /Length "
            + str(len(data)).encode()
            + extra
            + b" >>\nstream\n" + data
            + b"\nendstream")


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


def _page_pdf(tmp_path, name, text_cmd,
              size_cmd):
    objs = {
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
            b"<< /F1 5 0 R >> >>"
            b" /Contents 4 0 R >>"),
        4: _stream(
            b"BT /F1 " + size_cmd
            + b" Tf 72 700 Td ("
            + text_cmd + b") Tj ET"),
    }
    p = tmp_path / name
    p.write_bytes(_build(objs))
    return p


# ---------- Tf 0 ----------

def test_zero_size_point_bbox(
        tmp_path):
    p = _page_pdf(
        tmp_path, "f0.pdf",
        b"Zero size text", b"0")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Zero size text"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 92.0, 72.0, 92.0]
    assert doc.warnings == []


def test_zero_size_schema(
        tmp_path):
    from app.schema import is_valid
    p = _page_pdf(
        tmp_path, "f0s.pdf",
        b"Zero size text", b"0")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


# ---------- Tf 负 ----------

def test_negative_reversed(
        tmp_path):
    p = _page_pdf(
        tmp_path, "fn.pdf",
        b"Negative size text",
        b"-12")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "txet ezis evitageN"


def test_negative_bbox(
        tmp_path):
    p = _page_pdf(
        tmp_path, "fnb.pdf",
        b"Negative size text",
        b"-12")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        -22.703999999999994,
        89.51599999999996,
        72.0, 101.51599999999996]


def test_negative_chunk(
        tmp_path):
    p = _page_pdf(
        tmp_path, "fnc.pdf",
        b"Negative size text",
        b"-12")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == \
        "txet ezis evitageN"


# ---------- Tf 小数 ----------

def test_fractional_bbox(
        tmp_path):
    p = _page_pdf(
        tmp_path, "ff.pdf",
        b"Fractional size",
        b"12.5")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Fractional size"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.08749999999998,
        152.575, 94.58749999999998]


# ---------- 嵌套 Form ----------

def _nested_pdf(tmp_path, name):
    objs = {
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
            b"<< /F1 5 0 R >> "
            b"/XObject << /X1 6 0 R"
            b" >> >> /Contents "
            b"4 0 R >>"),
        4: _stream(
            b"q 1 0 0 1 72 700 cm"
            b" /X1 Do Q"),
        6: _stream(
            b"q 1 0 0 1 30 30 cm"
            b" /X2 Do Q",
            b" /Type /XObject /"
            b"Subtype /Form "
            b"/BBox [0 0 200 60] "
            b"/Resources << /Font"
            b" << /F1 5 0 R >> "
            b"/XObject << /X2 "
            b"7 0 R >> >>"),
        7: _stream(
            b"BT /F1 12 Tf 0 0 Td"
            b" (Nested inner text)"
            b" Tj ET",
            b" /Type /XObject /"
            b"Subtype /Form "
            b"/BBox [0 0 200 20] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >>"),
    }
    p = tmp_path / name
    p.write_bytes(_build(objs))
    return p


def test_nested_form_extracted(
        tmp_path):
    p = _nested_pdf(tmp_path,
                    "nf.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Nested inner text"]
    assert doc.warnings == []


def test_nested_form_translation(
        tmp_path):
    p = _nested_pdf(tmp_path,
                    "nfb.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        102.0, 52.48400000000004,
        192.708, 64.48400000000004]


def test_nested_form_schema(
        tmp_path):
    from app.schema import is_valid
    p = _nested_pdf(tmp_path,
                    "nfs.pdf")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_nested_form_chunk(
        tmp_path):
    p = _nested_pdf(tmp_path,
                    "nfc.pdf")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "Nested inner text"
