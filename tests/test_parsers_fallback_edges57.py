r"""app/parsers/fallback_parser.py 边角测试 - 第五十七轮（Round 1451）。

新角度（probe 实证）页面几何（历史全部 MediaBox [0 0 612 792]
无旋转，/Rotate 与非零原点从未碰过）：
- /Rotate 90：pdfplumber 施加旋转变换——页面转横 792x612，
  bbox [697.516, 72.0, 709.516, 136.704]
- /Rotate 180/270：字符序**倒序** 'txet detatoR'（同负字号
  现象），bbox 分别 [475.296, 697.516, 540.0, 709.516] /
  [82.484, 475.296, 94.484, 540.0]
- /Rotate 45 非直角：**静默忽略** → 与 rot0 完全一致，无告警
- MediaBox 非零原点 [100 50 712 842]：原点 x 被**丢弃**——
  bbox 与零原点完全相同
- MediaBox 偏移 + /Rotate 90：交互产生**负 y** bbox
  [697.516, -128.0, 709.516, -63.296]
- /CropBox（单独/与偏移 MediaBox 并存）：坐标**不受影响**
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _stream(data):
    return (b"<< /Length "
            + str(len(data)).encode()
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


def _pdf(tmp_path, name,
         mediabox=b"[0 0 612 792]",
         extra_page=b""):
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
            + mediabox
            + b" /Resources << /Font"
            b" << /F1 5 0 R >> >>"
            b" /Contents 4 0 R"
            + extra_page + b" >>"),
        4: _stream(
            b"BT /F1 12 Tf 72 700 Td"
            b" (Rotated text) Tj ET"),
    }
    p = tmp_path / name
    p.write_bytes(_build(objs))
    return p


# ---------- /Rotate ----------

def test_rot0_baseline(tmp_path):
    p = _pdf(
        tmp_path, "r0.pdf",
        extra_page=b" /Rotate 0")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        136.704, 94.48400000000004]


def test_rot90_transformed(tmp_path):
    p = _pdf(
        tmp_path, "r90.pdf",
        extra_page=b" /Rotate 90")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        697.516, 72.0,
        709.516, 136.704]
    assert doc.warnings == []


def test_rot180_reversed(tmp_path):
    p = _pdf(
        tmp_path, "r180.pdf",
        extra_page=b" /Rotate 180")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "txet detatoR"
    assert doc.elements[
        0].source_locator["bbox"] == [
        475.296, 697.516,
        540.0, 709.516]


def test_rot270_reversed(tmp_path):
    p = _pdf(
        tmp_path, "r270.pdf",
        extra_page=b" /Rotate 270")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "txet detatoR"
    assert doc.elements[
        0].source_locator["bbox"] == [
        82.484, 475.296,
        94.484, 540.0]


def test_rot45_ignored(tmp_path):
    p = _pdf(
        tmp_path, "r45.pdf",
        extra_page=b" /Rotate 45")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        136.704, 94.48400000000004]
    assert doc.warnings == []


# ---------- MediaBox 原点 ----------

def test_mediabox_origin_dropped(
        tmp_path):
    p = _pdf(
        tmp_path, "mb.pdf",
        mediabox=b"[100 50 712 842]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        136.704, 94.48400000000004]


def test_mediabox_offset_rot90_negative(
        tmp_path):
    p = _pdf(
        tmp_path, "mb90.pdf",
        mediabox=b"[100 50 712 842]",
        extra_page=b" /Rotate 90")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        697.516, -128.0,
        709.516, -63.29600000000005]
    assert bbox[1] < 0
    assert doc.warnings == []


# ---------- /CropBox ----------

def test_cropbox_ignored(tmp_path):
    p = _pdf(
        tmp_path, "cb.pdf",
        extra_page=b" /CropBox"
                   b" [72 72 540 720]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        136.704, 94.48400000000004]


def test_cropbox_offset_mediabox(
        tmp_path):
    p = _pdf(
        tmp_path, "cbo.pdf",
        mediabox=b"[100 50 712 842]",
        extra_page=b" /CropBox"
                   b" [150 100 600 700]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Rotated text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        136.704, 94.48400000000004]


# ---------- 通用 ----------

def test_rot90_schema(tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "r90s.pdf",
        extra_page=b" /Rotate 90")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_rot180_chunk(tmp_path):
    p = _pdf(
        tmp_path, "r180c.pdf",
        extra_page=b" /Rotate 180")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "txet detatoR"


def test_rot90_single_page_only(
        tmp_path):
    objs = {
        5: (b"<< /Type /Font /Subtype"
            b" /Type1 /BaseFont"
            b" /Helvetica >>"),
        1: (b"<< /Type /Catalog"
            b" /Pages 2 0 R >>"),
        2: (b"<< /Type /Pages"
            b" /Kids [3 0 R 6 0 R]"
            b" /Count 2 >>"),
        3: (b"<< /Type /Page /Parent"
            b" 2 0 R /MediaBox"
            b" [0 0 612 792]"
            b" /Rotate 90"
            b" /Resources << /Font"
            b" << /F1 5 0 R >> >>"
            b" /Contents 4 0 R >>"),
        4: _stream(
            b"BT /F1 12 Tf 72 700 Td"
            b" (Rotated text) Tj"
            b" ET"),
        6: (b"<< /Type /Page /Parent"
            b" 2 0 R /MediaBox"
            b" [0 0 612 792]"
            b" /Resources << /Font"
            b" << /F1 5 0 R >> >>"
            b" /Contents 7 0 R >>"),
        7: _stream(
            b"BT /F1 12 Tf 72 700 Td"
            b" (Normal text) Tj"
            b" ET"),
    }
    p = tmp_path / "mix.pdf"
    p.write_bytes(_build(objs))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Rotated text", "Normal text"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        697.516, 72.0,
        709.516, 136.704]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        133.344, 94.48400000000004]
    assert doc.warnings == []
