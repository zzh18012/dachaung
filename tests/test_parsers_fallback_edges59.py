r"""app/parsers/fallback_parser.py 边角测试 - 第五十九轮（Round 1453）。

新角度（probe 实证）内容流结构变体（历史全单流 + 完整
BT/ET + 默认编码 + 默认 Tz，从未变过）：
- /Contents 数组 [4 0 R 8 0 R]：两流**拼接**成一段——
  'First stream Second stream' bbox 跨两行
- 缺 ET：流在 Tj 后直接结束 → 文本照出，无告警
- Tz 水平缩放：50 → 宽度**减半**（30.672）；200 → **翻倍**
  （100.032）；bbox 高度不变 12
- WinAnsiEncoding 高位字节 <9550> → '•P'（真实映射）；
  同字节默认 StandardEncoding → '(cid:149)P' 占位符
- Tr 3 隐形文本：**照常提取**（无渲染模式过滤）——
  扫描件 OCR 隐形层可用的行为锚点
- 双栏同排：y 排序阅读序**跨栏交错** 'L one R one L two
  R two'，bbox 横跨两栏 [72.0, ..., 332.016, ...]
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


def _build(objs, contents_ref=b"4 0 R"):
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


_FONT = (b"<< /Type /Font /Subtype"
         b" /Type1 /BaseFont "
         b"/Helvetica >>")


def _pdf(tmp_path, name, content4,
         contents_ref=b"4 0 R",
         font5=_FONT,
         extra_stream=None):
    objs = {
        5: font5,
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
            b" /Contents "
            + contents_ref + b" >>"),
        4: _stream(content4),
    }
    if extra_stream is not None:
        objs[8] = _stream(extra_stream)
    p = tmp_path / name
    p.write_bytes(_build(objs, contents_ref))
    return p


# ---------- /Contents 数组 ----------

def test_contents_array_concat(
        tmp_path):
    p = _pdf(
        tmp_path, "ca.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (First stream) Tj ET",
        contents_ref=b"[4 0 R 8 0 R]",
        extra_stream=(
            b"BT /F1 12 Tf 72 680 Td"
            b" (Second stream) Tj ET"))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "First stream Second stream"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        152.70000000000002,
        114.48400000000004]
    assert doc.warnings == []


def test_contents_array_chunk(
        tmp_path):
    p = _pdf(
        tmp_path, "cac.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (First stream) Tj ET",
        contents_ref=b"[4 0 R 8 0 R]",
        extra_stream=(
            b"BT /F1 12 Tf 72 680 Td"
            b" (Second stream) Tj ET"))
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[0].text == \
        "First stream Second stream"


# ---------- 缺 ET ----------

def test_missing_et(tmp_path):
    p = _pdf(
        tmp_path, "net.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" (No ET text) Tj")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "No ET text"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        128.68800000000002,
        94.48400000000004]
    assert doc.warnings == []


# ---------- Tz 水平缩放 ----------

def test_tz_50_narrow(tmp_path):
    p = _pdf(
        tmp_path, "tz5.pdf",
        b"BT /F1 12 Tf 50 Tz"
        b" 72 700 Td"
        b" (Narrow text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Narrow text"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        72.0, 82.48400000000004,
        102.672, 94.48400000000004]


def test_tz_200_wide(tmp_path):
    p = _pdf(
        tmp_path, "tz2.pdf",
        b"BT /F1 12 Tf 200 Tz"
        b" 72 700 Td"
        b" (Wide text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Wide text"
    bbox = doc.elements[
        0].source_locator["bbox"]
    assert bbox == [
        72.0, 82.48400000000004,
        172.032, 94.48400000000004]
    assert (bbox[3] - bbox[1]) == 12.0


# ---------- 编码变体 ----------

def test_winansi_bullet(tmp_path):
    p = _pdf(
        tmp_path, "wa.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" <9550> Tj ET",
        font5=(b"<< /Type /Font"
               b" /Subtype /Type1"
               b" /BaseFont"
               b" /Helvetica"
               b" /Encoding"
               b" /WinAnsiEncoding >>"))
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "•P"
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        84.20400000000001,
        94.48400000000004]


def test_standard_cid_149(tmp_path):
    p = _pdf(
        tmp_path, "sc.pdf",
        b"BT /F1 12 Tf 72 700 Td"
        b" <9550> Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "(cid:149)P"


# ---------- Tr 3 隐形 ----------

def test_tr3_invisible_extracted(
        tmp_path):
    p = _pdf(
        tmp_path, "tr3.pdf",
        b"BT /F1 12 Tf 3 Tr"
        b" 72 700 Td"
        b" (Invisible text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "Invisible text"
    assert doc.warnings == []


def test_tr3_schema(tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "tr3s.pdf",
        b"BT /F1 12 Tf 3 Tr"
        b" 72 700 Td"
        b" (Invisible text) Tj ET")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


# ---------- 双栏交错 ----------

def test_two_column_interleave(
        tmp_path):
    col = (b"BT /F1 12 Tf 72 700 Td"
           b" (L one) Tj ET"
           b" BT /F1 12 Tf 300 700 Td"
           b" (R one) Tj ET"
           b" BT /F1 12 Tf 72 670 Td"
           b" (L two) Tj ET"
           b" BT /F1 12 Tf 300 670 Td"
           b" (R two) Tj ET")
    p = _pdf(
        tmp_path, "2col.pdf", col)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "L one R one L two R two"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        332.016, 124.48400000000004]


def test_two_column_split_by_gap(
        tmp_path):
    col = (b"BT /F1 12 Tf 72 700 Td"
           b" (Left col) Tj ET"
           b" BT /F1 12 Tf 300 700 Td"
           b" (Right col) Tj ET")
    p = _pdf(
        tmp_path, "2cs.pdf", col)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Left col Right col"
