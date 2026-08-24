r"""app/parsers/fallback_parser.py 边角测试 - 第三十五轮（Round 1425）。

新角度（probe 实证）十六进制字符串 + 未注册字体（历史文本
串全是括号字面量、字体全在 Resources 里）：
- <48656C6C6F...> Tj 十六进制串照常解码（'Hello hex
  world'），bbox 正常；奇偶长度无异常
- /F9 未在 Resources 注册：文本**仍被抽取**，但 bbox 退化
  成零宽框 [72.0, 80.0, 72.0, 92.0]（宽 0、高恰 12、top
  无 2.484 基线偏移）；schema 仍绿、无告警
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


def _hex_pdf(tmp_path):
    p = tmp_path / "hex.pdf"
    p.write_bytes(_build(
        b"BT /F1 12 Tf 72 700 Td "
        b"<48656C6C6F2068657820"
        b"776F726C64> Tj ET "
        b"BT /F1 12 Tf 72 640 Td "
        b"<416263> Tj ET"))
    return p


def _uf_pdf(tmp_path):
    p = tmp_path / "uf.pdf"
    p.write_bytes(_build(
        b"BT /F9 12 Tf 72 700 Td "
        b"(Unknown font text) "
        b"Tj ET"))
    return p


# ---------- 十六进制串 ----------

def test_hex_decoded(tmp_path):
    p = _hex_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Hello hex world", "Abc"]


def test_hex_bboxes(tmp_path):
    p = _hex_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        154.02, 94.48400000000004]
    assert doc.elements[
        1].source_locator["bbox"] == [
        72.0, 142.48400000000004,
        92.676, 154.48400000000004]


def test_hex_no_warnings(tmp_path):
    p = _hex_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_hex_schema_valid(tmp_path):
    from app.schema import is_valid
    p = _hex_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_hex_chunks(tmp_path):
    p = _hex_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Hello hex world", "Abc"]


# ---------- 未注册字体 ----------

def test_uf_text_extracted(
        tmp_path):
    p = _uf_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].content == \
        "Unknown font text"


def test_uf_zero_width_bbox(
        tmp_path):
    p = _uf_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements[
        0].source_locator == {
        "page": 1,
        "bbox": [72.0, 80.0,
                 72.0, 92.0]}


def test_uf_box_geometry(
        tmp_path):
    b = _parse_uf_bbox(tmp_path)
    assert (b[2] - b[0]) == 0.0
    assert (b[3] - b[1]) == 12.0


def _parse_uf_bbox(tmp_path):
    p = _uf_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return doc.elements[
        0].source_locator["bbox"]


def test_uf_no_warnings(tmp_path):
    p = _uf_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []


def test_uf_schema_valid(tmp_path):
    from app.schema import is_valid
    p = _uf_pdf(tmp_path)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_uf_pipeline_chunk(
        tmp_path):
    p = _uf_pdf(tmp_path)
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert [c.text
            for c in doc.chunks] == [
        "Unknown font text"]
    assert len(doc.chunks[0]
               .source_element_ids) == 1
