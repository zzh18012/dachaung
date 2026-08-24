r"""app/parsers/fallback_parser.py 边角测试 - 第三十四轮（Round 1424）。

新角度（probe 实证）畸形内容流三态（历史内容流全部配对良
好）：
- 裸 Tj（无 BT/ET 包裹）：静默丢弃——只有 BT 内文本成元
  素、无告警
- q 无 Q：cm 变换**泄漏**到后续所有文本——第二段 Td
  (72,100) 也被缩到 (144,200)、字号 24（对照 R1413 配对
  版 Q 后还原）
- ET 缺失：pdfminer 容忍——两段文本照常各自成元素
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


def _bare_pdf(tmp_path):
    p = tmp_path / "bare.pdf"
    p.write_bytes(_build(
        b"(Bare outside text) Tj\n"
        b"BT /F1 12 Tf 72 700 Td "
        b"(Inside BT text) Tj ET"))
    return p


def _qleak_pdf(tmp_path):
    p = tmp_path / "qleak.pdf"
    p.write_bytes(_build(
        b"q 2 0 0 2 0 0 cm "
        b"BT /F1 12 Tf 72 350 Td "
        b"(First scaled text) Tj ET "
        b"BT /F1 12 Tf 72 100 Td "
        b"(Leaked scale text) "
        b"Tj ET"))
    return p


def _noet_pdf(tmp_path):
    p = tmp_path / "noet.pdf"
    p.write_bytes(_build(
        b"BT /F1 12 Tf 72 700 Td "
        b"(No ET first) Tj "
        b"BT /F1 12 Tf 72 600 Td "
        b"(Second block) Tj ET"))
    return p


# ---------- 裸 Tj ----------

def test_bare_tj_dropped(tmp_path):
    p = _bare_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Inside BT text"]


def test_bare_tj_no_warnings(
        tmp_path):
    p = _bare_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_bare_tj_pipeline(
        tmp_path):
    p = _bare_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Inside BT text"]


# ---------- q 泄漏 ----------

def test_qleak_first_scaled(
        tmp_path):
    p = _qleak_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        144.0, 72.96799999999996,
        312.048, 96.96799999999996]


def test_qleak_second_scaled(
        tmp_path):
    """第二段无 Q 保护也被缩放：
    Td(72,100) → (144,200)、
    高 24（对照 R1413 配对版）。"""
    p = _qleak_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    b = doc.elements[
        1].source_locator["bbox"]
    assert b == [144.0, 572.968,
                 330.76800000000003,
                 596.968]
    assert (b[3] - b[1]) == 24.0


def test_qleak_contents(
        tmp_path):
    p = _qleak_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "First scaled text",
        "Leaked scale text"]


def test_qleak_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _qleak_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
    assert doc.warnings == []


def test_qleak_chunks(tmp_path):
    p = _qleak_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "First scaled text",
        "Leaked scale text"]


# ---------- 缺 ET ----------

def test_noet_both_extracted(
        tmp_path):
    p = _noet_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "No ET first",
        "Second block"]


def test_noet_two_headings(
        tmp_path):
    p = _noet_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.type
            for e in doc.elements] == [
        "heading", "heading"]


def test_noet_no_warnings(
        tmp_path):
    p = _noet_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_noet_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _noet_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())
