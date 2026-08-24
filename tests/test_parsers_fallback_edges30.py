r"""app/parsers/fallback_parser.py 边角测试 - 第三十轮（Round 1419）。

新角度（probe 实证）内容流字符串转义 + 单 BT 多 Td 相对
定位（历史 Td 全是单 BT 单 Td 绝对定位）：
- 八进制 \351 → 'Ø'（StandardEncoding 0xE9 位是 Ø 不是 é）
- \( \) 括号转义正常还原；两字符 \n 转义 → LF 进字符串 →
  渲染成 (cid:10) 字面文本；\ 加真实换行是规范续行符 →
  无字符产生（'cont1cont2'）
- () Tj 空串无幽灵元素
- 同 BT 第二个 Td 相对前一文本行起点 → 落到页面外
  （x 翻倍 144、top -557.5），且按 top 排序后**先于**正文
  元素出现；schema 容忍负 bbox
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


def _esc_pdf(tmp_path):
    c = (b"BT /F1 12 Tf 72 700 Td "
         rb"(caf\351 au lait) Tj ET "
         b"BT /F1 12 Tf 72 660 Td "
         rb"(a\(b\)c parens) Tj ET "
         b"BT /F1 12 Tf 72 620 Td "
         b"(line1\\nline2 cont) "
         b"Tj ET "
         b"BT /F1 12 Tf 72 580 Td "
         b"(cont1\\" + b"\n" +
         b"cont2) Tj ET "
         b"BT /F1 12 Tf 72 540 Td "
         b"() Tj ET "
         b"BT /F1 12 Tf 72 500 Td "
         b"(real after empty) "
         b"Tj ET")
    p = tmp_path / "esc.pdf"
    p.write_bytes(_build(c))
    return p


def _td_pdf(tmp_path):
    c = (b"BT /F1 12 Tf 72 700 Td "
         b"(First Td line) Tj "
         b"72 640 Td "
         b"(Second Td line) Tj ET")
    p = tmp_path / "td.pdf"
    p.write_bytes(_build(c))
    return p


# ---------- 转义 ----------

def test_octal_escape_std_enc(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == "cafØ au lait"


def test_parens_escape(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        1].content == "a(b)c parens"


def test_backslash_n_escape_cid(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        2].content == \
        "line1(cid:10)line2 cont"


def test_line_continuation_dropped(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        3].content == \
        "cont1cont2"


def test_empty_tj_no_ghost(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert len(doc.elements) == 5
    assert doc.elements[
        4].content == \
        "real after empty"


def test_escape_all_heading(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading"] * 5


def test_escape_locators(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    tops = [e.source_locator["bbox"][1]
            for e in doc.elements]
    assert tops == [82.48400000000004,
                    122.48400000000004,
                    162.48400000000004,
                    202.48400000000004,
                    282.484]
    assert all(
        e.source_locator["page"] == 1
        for e in doc.elements)


def test_escape_no_warnings(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_escape_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _esc_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_escape_chunks(
        tmp_path):
    p = _esc_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "cafØ au lait",
        "a(b)c parens",
        "line1(cid:10)line2 cont",
        "cont1cont2",
        "real after empty"]
    assert [len(c.source_element_ids)
            for c in doc.chunks] == [
        1, 1, 1, 1, 1]


# ---------- 单 BT 双 Td ----------

def test_td_relative_offpage(
        tmp_path):
    p = _td_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [144.0,
                 -557.5160000000001,
                 224.04,
                 -545.5160000000001]}


def test_td_order_by_top(
        tmp_path):
    p = _td_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Second Td line",
        "First Td line"]


def test_td_first_bbox(
        tmp_path):
    p = _td_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        134.67600000000002,
        94.48400000000004]


def test_td_schema_negative_bbox(
        tmp_path):
    from app.schema import is_valid
    p = _td_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
    assert doc.warnings == []


def test_td_chunks_order(
        tmp_path):
    p = _td_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Second Td line",
        "First Td line"]
