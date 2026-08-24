r"""app/parsers/fallback_parser.py 边角测试 - 第三十一轮（Round 1420）。

新角度（probe 实证）Tm 文本矩阵三态（历史定位全走 Td / q-cm，
从未碰过 Tm）：
- 恒等 '1 0 0 1 72 700 Tm' ≡ Td(72,700)：bbox 与 Td 版逐位
  一致 [72.0, 82.484, 153.36, 94.484]
- 缩放 '2 0 0 2 72 400 Tm'：字形高翻倍（24.0）、宽近 2 倍
  （158.712 vs 81.36，字符宽独立取整），但平移 (e,f) 不缩
  放——x0 仍 72.0（与 R1413 的 q-cm 缩放不同：cm 连平移一
  起缩到 144）
- 旋转 '0 1 -1 0 72 200 Tm'：字符序**倒序**（'enil mT
  detatoR'）、bbox 竖成 12 宽 × 84.7 高；schema 仍绿
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


def _tm_pdf(tmp_path):
    c = (b"BT /F1 12 Tf "
         b"1 0 0 1 72 700 Tm "
         b"(Identity Tm line) Tj ET "
         b"BT /F1 12 Tf "
         b"2 0 0 2 72 400 Tm "
         b"(Scaled Tm line) Tj ET "
         b"BT /F1 12 Tf "
         b"0 1 -1 0 72 200 Tm "
         b"(Rotated Tm line) Tj ET")
    p = tmp_path / "tm.pdf"
    p.write_bytes(_build(c))
    return p


def _parse(tmp_path):
    p = _tm_pdf(tmp_path)
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- 恒等 Tm ----------

def test_identity_tm_bbox(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0,
                 82.48400000000004,
                 153.35999999999999,
                 94.48400000000004]}


def test_identity_tm_content(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        0].type == "heading"
    assert doc.elements[
        0].content == \
        "Identity Tm line"


# ---------- 缩放 Tm ----------

def test_scaled_tm_bbox(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        1].source_locator == {
        "page": 1,
        "bbox": [72.0, 372.968,
                 230.712, 396.968]}


def test_scaled_tm_height_doubled(
        tmp_path):
    doc = _parse(tmp_path)
    b = doc.elements[
        1].source_locator["bbox"]
    assert (b[3] - b[1]) == 24.0


def test_scaled_tm_translation_raw(
        tmp_path):
    """(e,f)=(72,400) 不随 a=d=2 缩放：
    x0 仍 72.0（对照 R1413 cm 版 x0=144）。"""
    doc = _parse(tmp_path)
    assert doc.elements[
        1].source_locator["bbox"][0] \
        == 72.0


def test_scaled_tm_widths(
        tmp_path):
    """宽 158.712 vs 恒等版 81.36——
    近 2 倍但非精确（字符宽按各自
    字号独立取整）。"""
    doc = _parse(tmp_path)
    w_id = (doc.elements[0]
            .source_locator["bbox"][2]
            - doc.elements[0]
            .source_locator["bbox"][0])
    w_sc = (doc.elements[1]
            .source_locator["bbox"][2]
            - doc.elements[1]
            .source_locator["bbox"][0])
    assert w_id == \
        81.35999999999999
    assert w_sc == 158.712
    assert w_sc > 1.95 * w_id


# ---------- 旋转 Tm ----------

def test_rotated_tm_reversed(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        2].content == \
        "enil mT detatoR"


def test_rotated_tm_vertical_bbox(
        tmp_path):
    doc = _parse(tmp_path)
    assert doc.elements[
        2].source_locator == {
        "page": 1,
        "bbox": [62.484, 507.304,
                 74.484, 592.0]}


def test_rotated_tm_box_is_tall(
        tmp_path):
    b = _parse(
        tmp_path).elements[
        2].source_locator["bbox"]
    assert round(b[2] - b[0], 3) \
        == 12.0
    assert round(b[3] - b[1], 3) \
        == 84.696


# ---------- 整体 ----------

def test_three_headings(tmp_path):
    doc = _parse(tmp_path)
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading",
        "heading"]


def test_no_warnings(tmp_path):
    doc = _parse(tmp_path)
    assert doc.warnings == []


def test_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path)
    assert is_valid(doc.to_dict())


def test_pipeline_chunks(tmp_path):
    p = _tm_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Identity Tm line",
        "Scaled Tm line",
        "enil mT detatoR"]
    assert [len(c.source_element_ids)
            for c in doc.chunks] == [
        1, 1, 1]
