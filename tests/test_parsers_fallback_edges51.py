r"""app/parsers/fallback_parser.py 边角测试 - 第五十一轮（Round 1445）。

新角度（probe 实证）内容流 /Filter（历史手写 PDF 全是裸流，
压缩流——真实 PDF 的常态——从未碰过）：
- FlateDecode：zlib 压缩流透明解压，'Flate compressed
  text' + 正常 bbox
- ASCIIHexDecode：hex 编码 + '>' 终止符照常解码
- ASCII85Decode：base85 + '~>' 照常解码
- 未知过滤器 /UnknownDecode：**双告警**
  [pdfplumber_word_extract_failed, pdf_no_text_extracted]
  ——pdfplumber_word_extract_failed 首次现身
- 过滤器数组链 [/FlateDecode /ASCIIHexDecode] 两种组合序
  都失败（hex(zlib) → pdf_no_text_extracted；zlib(hex) →
  双告警），链式 /Contents 不可用
- Flate 流配错误 /Length（截 20 字节）→ 整流静默丢失
  （与 R1428 裸流同款）
"""

from __future__ import annotations

import tempfile
import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser
from app.pipeline import process_single

import base64


def _build(content, filt=b""):
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
            + filt
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


def _pdf(tmp_path, name, content,
         filt=b""):
    p = tmp_path / name
    p.write_bytes(_build(content, filt))
    return p


_RAW = (b"BT /F1 12 Tf 72 700 Td "
        b"(Flate compressed text)"
        b" Tj ET")
_RAW2 = (b"BT /F1 12 Tf 72 700 Td "
         b"(Chain filtered text)"
         b" Tj ET")


# ---------- FlateDecode ----------

def test_flate_decoded(tmp_path):
    p = _pdf(
        tmp_path, "f.pdf",
        zlib.compress(_RAW),
        b" /Filter /FlateDecode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Flate compressed text"]
    assert doc.elements[
        0].source_locator["bbox"] == [
        72.0, 82.48400000000004,
        190.04399999999998,
        94.48400000000004]
    assert doc.warnings == []


def test_flate_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _pdf(
        tmp_path, "fs.pdf",
        zlib.compress(_RAW),
        b" /Filter /FlateDecode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert is_valid(doc.to_dict())


def test_flate_chunk(tmp_path):
    p = _pdf(
        tmp_path, "fc.pdf",
        zlib.compress(_RAW),
        b" /Filter /FlateDecode")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == \
        "Flate compressed text"


# ---------- ASCIIHex ----------

def test_asciihex_decoded(
        tmp_path):
    p = _pdf(
        tmp_path, "hx.pdf",
        _RAW.hex().encode() + b">",
        b" /Filter /ASCIIHexDecode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Flate compressed text"]
    assert doc.warnings == []


# ---------- ASCII85 ----------

def test_ascii85_decoded(
        tmp_path):
    p = _pdf(
        tmp_path, "a85.pdf",
        base64.a85encode(_RAW2)
        + b"~>",
        b" /Filter /ASCII85Decode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "Chain filtered text"]
    assert doc.warnings == []


# ---------- 未知过滤器 ----------

def test_unknown_filter_warns(
        tmp_path):
    p = _pdf(
        tmp_path, "bad.pdf",
        _RAW,
        b" /Filter /UnknownDecode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdfplumber_word_extract_"
        "failed",
        "pdf_no_text_extracted"]


def test_unknown_filter_pipeline(
        tmp_path):
    p = _pdf(
        tmp_path, "badp.pdf",
        _RAW,
        b" /Filter /UnknownDecode")
    doc, errors = process_single(
        p, None,
        parser_name="fallback",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]


# ---------- 过滤器链 ----------

def test_chain_flate_hex_fails(
        tmp_path):
    p = _pdf(
        tmp_path, "ch1.pdf",
        zlib.compress(_RAW2)
        .hex().encode() + b">",
        b" /Filter [/FlateDecode"
        b" /ASCIIHexDecode]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]


def test_chain_hex_flate_fails(
        tmp_path):
    p = _pdf(
        tmp_path, "ch2.pdf",
        zlib.compress(
            _RAW2.hex().encode()
            + b">"),
        b" /Filter [/ASCIIHexDecode"
        b" /FlateDecode]")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdfplumber_word_extract_"
        "failed",
        "pdf_no_text_extracted"]


# ---------- Flate + 错误 Length ----------

def test_flate_wrong_length(
        tmp_path):
    p = _pdf(
        tmp_path, "fw.pdf",
        zlib.compress(_RAW)[:20],
        b" /Filter /FlateDecode")
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "pdf_no_text_extracted"]
