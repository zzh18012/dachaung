r"""app/parsers/fallback_parser.py 边角测试 - 第五十四轮（Round 1448）。

新角度（probe 实证）Form XObject（历史内容流全直接画在页流
里，/XObject + Do 复用机制从未碰过——真实 PDF 常态）：
- /X1 Do 引用 Form XObject：内嵌文本透明提取，cm 平移
  正确施加——bbox [72.0, 82.484, 139.356, 94.484]（同
  直接 Td 到 (72,700) 完全一致）
- 页面直接文本 + Form 文本并存：30pt 行距 ≤30 合并阈值
  → 单元素 'Direct page text XO form text'，bbox 跨两行
- 未定义资源 /X9 Do：整页静默失败 → 0 元素 +
  pdf_no_text_extracted
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


_FORM = (b"BT /F1 12 Tf 0 0 Td "
         b"(XO form text) Tj ET")


def _objs(content4):
    return {
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
        4: _stream(content4),
        6: _stream(
            _FORM,
            b" /Type /XObject /"
            b"Subtype /Form "
            b"/BBox [0 0 200 20] "
            b"/Resources << /Font "
            b"<< /F1 5 0 R >> >>"),
    }


def _pdf(tmp_path, name, content4):
    p = tmp_path / name
    p.write_bytes(_build(_objs(content4)))
    return p


# ---------- 单 Form ----------

def test_form_extracted(tmp_path):
    p = _pdf(
        tmp_path, "x1.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X1 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "XO form text"]
    assert doc.warnings == []


def test_form_bbox_translated(
        tmp_path):
    p = _pdf(
        tmp_path, "x2.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X1 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        139.356, 94.48400000000004]


def test_form_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "x3.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X1 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_form_chunk(tmp_path):
    p = _pdf(
        tmp_path, "x4.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X1 Do Q")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == "XO form text"


# ---------- 直接 + Form 并存 ----------

def test_direct_and_form_merge(
        tmp_path):
    p = _pdf(
        tmp_path, "d1.pdf",
        b"BT /F1 12 Tf 72 720 Td"
        b" (Direct page text) Tj"
        b" ET q 1 0 0 1 72 690 cm"
        b" /X1 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Direct page text"
        " XO form text"]


def test_direct_and_form_bbox(
        tmp_path):
    p = _pdf(
        tmp_path, "d2.pdf",
        b"BT /F1 12 Tf 72 720 Td"
        b" (Direct page text) Tj"
        b" ET q 1 0 0 1 72 690 cm"
        b" /X1 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 62.48400000000004,
        156.036, 104.48400000000004]


# ---------- 未定义资源 ----------

def test_missing_xobj_dead(
        tmp_path):
    p = _pdf(
        tmp_path, "m1.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X9 Do Q")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_missing_xobj_pipeline(
        tmp_path):
    p = _pdf(
        tmp_path, "m2.pdf",
        b"q 1 0 0 1 72 700 cm"
        b" /X9 Do Q")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


# ---------- 通用 ----------

def test_form_no_q_wrap(tmp_path):
    p = _pdf(
        tmp_path, "nq.pdf",
        b"1 0 0 1 72 700 cm"
        b" /X1 Do")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "XO form text"]
