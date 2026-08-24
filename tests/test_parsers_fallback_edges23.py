r"""app/parsers/fallback_parser.py 边角测试 - 第二十三轮（Round 1408）。

新角度（probe 实证）PDF 文本状态运算符三连：
- 3 Tr（不可见渲染模式，OCR 层标准）：照常抽取，
  bbox 与可见文本无异
- 150 Tz + 5 Tc（放大 + 字距）：字间空隙超过分词阈值
  → 每个字母成为独立 word，拼回时空格分隔
  （'W i d e s p a c e d h e a d l i n e'）
- 裸字符串无 Tj（流内孤儿对象）：不渲染不抽取；
  T* 仍对下一个 Tj 应用 leading（y-14 → top 156.484）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single


def _xref_pdf(content):
    objs = {
        6: (b"<< /Type /Font /Subtype "
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
            b"<< /F1 6 0 R >> >> "
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


def _tr3_pdf():
    return _xref_pdf(
        b"BT /F1 12 Tf 3 Tr 72 700 "
        b"Td (Invisible OCR layer "
        b"text) Tj ET "
        b"BT /F1 12 Tf 0 Tr 72 640 "
        b"Td (Visible normal text "
        b"body here.) Tj ET")


def _ops_pdf():
    return _xref_pdf(
        b"BT /F1 12 Tf 150 Tz 5 Tc "
        b"72 700 Td (Wide spaced "
        b"headline) Tj ET "
        b"BT /F1 12 Tf 14 TL 72 640 "
        b"Td (First leaded line) T* "
        b"(Second leaded line "
        b"follows here.) Tj ET")


def _parse(tmp_path, name,
           builder):
    p = tmp_path / name
    p.write_bytes(builder())
    return FallbackParser().parse(
        p, compute_file_hash(p))


# ---------- Tr 3 不可见文本 ----------

def test_tr3_invisible_extracted(
        tmp_path):
    doc = _parse(tmp_path,
                 "tr3.pdf", _tr3_pdf)
    assert [e.content
            for e in doc.elements] == [
        "Invisible OCR layer text",
        "Visible normal text body "
        "here."]


def test_tr3_types(tmp_path):
    doc = _parse(tmp_path,
                 "tr3.pdf", _tr3_pdf)
    assert [e.type
            for e in doc.elements] == [
        "heading", "paragraph"]


def test_tr3_bbox_same_geometry(
        tmp_path):
    """不可见文本 bbox 与可见文本
    同几何（y=700 → top 82.484）。"""
    doc = _parse(tmp_path,
                 "tr3.pdf", _tr3_pdf)
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        197.364, 94.48400000000004]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 142.48400000000004,
        230.064, 154.48400000000004]


def test_tr3_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 "tr3.pdf", _tr3_pdf)
    assert is_valid(doc.to_dict())


def test_tr3_pipeline(tmp_path):
    p = tmp_path / "tr3.pdf"
    p.write_bytes(_tr3_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "Invisible OCR layer text "
        "Visible normal text body "
        "here.")


# ---------- Tz/Tc 字距分词 ----------

def test_ops_letter_spaced_words(
        tmp_path):
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert doc.elements[
        0].content == (
        "W i d e s p a c e d "
        "h e a d l i n e")


def test_ops_lone_string_dropped(
        tmp_path):
    """无 Tj 的裸字符串 '(First
    leaded line)' 不渲染不抽取。"""
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    for e in doc.elements:
        assert "First" not in e.content
    assert len(doc.elements) == 2


def test_ops_tstar_leading_applied(
        tmp_path):
    """T* 把下一个 Tj 下移 14：
    y=640-14 → top 156.484。"""
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert doc.elements[
        1].source_locator["bbox"][1] \
        == 156.48400000000004


def test_ops_types(tmp_path):
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert [e.type
            for e in doc.elements] == [
        "heading", "paragraph"]


def test_ops_wide_bbox(tmp_path):
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert doc.elements[
        0].source_locator["bbox"][2] \
        == 391.58399999999995


def test_ops_schema_valid(tmp_path):
    from app.schema import is_valid
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert is_valid(doc.to_dict())


def test_ops_no_warnings(tmp_path):
    doc = _parse(tmp_path,
                 "ops.pdf", _ops_pdf)
    assert doc.warnings == []


def test_ops_pipeline_chunk(tmp_path):
    p = tmp_path / "ops.pdf"
    p.write_bytes(_ops_pdf())
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == (
        "W i d e s p a c e d "
        "h e a d l i n e "
        "S e c o n d l e a d e d "
        "l i n e f o l l o w s "
        "h e r e .")
