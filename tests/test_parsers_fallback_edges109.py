r"""app/parsers_fallback PDF 边角测试 - 第一百零九轮（Round 1539）。

新角度（probe 实证）/Filter 家族与链序（此前轮次仅单
FlateDecode；真实 PDF 常见 ASCIIHex/ASCII85 包裹的链
式过滤器——零覆盖）：

- **单 /ASCIIHexDecode**：十六进制流 → 正常提取
- **空数组 []** → 无过滤照常
- **⚠ 链序按数组顺序解码（非规范逆序）**：数据 =
  hex(flate(raw))，声明 [/ASCIIHexDecode /FlateDecode]
  （hex 在前）→ **正常**；声明 [/FlateDecode /ASCIIHex
  Decode]（规范序）→ **[] + 仅 pdf_no_text_extracted**
  （对 hex 文本做 unflate 静默失败——规范序反而丢全部
  文本）
- **[/FlateDecode /ASCII85Decode] + a85(flate)** → 同上
  静默丢失
- **重复声明两次 FlateDecode**（数据仅压一次）→ 静默丢
  失
- **明文数据声明 /ASCIIHexDecode** → unhex 出乱码字符
  → [] + word_extract_failed + no_text 双警告
- **未知过滤器 /FooDecode** → 同上双警告
"""

from __future__ import annotations

import base64
import zlib
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_RAW = ("BT /F1 12 Tf 72 700 Td"
        " (HEXBODY) Tj ET")
_FLATE = zlib.compress(
    _RAW.encode("latin-1"))
_HEX = _FLATE.hex().encode() + b">"
_A85 = base64.a85encode(_FLATE) + b"~>"


def _parse(tmp_path, name, data,
           filt_decl):
    o4 = (f"<< /Filter {filt_decl}"
          f" /Length {len(data)} >>"
          f"\nstream\n"
          ).encode("latin-1") \
        + data + b"\nendstream"
    objs = [
        b"<< /Type /Catalog"
        b" /Pages 2 0 R >>",
        b"<< /Type /Pages"
        b" /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page"
        b" /Parent 2 0 R"
        b" /MediaBox [0 0 612 792]"
        b" /Resources << /Font"
        b" << /F1 5 0 R >> >>"
        b" /Contents 4 0 R >>",
        o4,
        b"<< /Type /Font"
        b" /Subtype /Type1"
        b" /BaseFont /Helvetica"
        b" /Encoding"
        b" /WinAnsiEncoding >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n"
                .encode("latin-1")
                + o + b"\nendobj\n")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return FallbackParser().parse(
        p, compute_file_hash(p))


def _ok(tmp_path, name, data, decl):
    doc = _parse(tmp_path, name, data,
                 decl)
    assert [e.content
            for e in doc.elements] == [
        "HEXBODY"]
    assert doc.warnings == []


def _lost(tmp_path, name, data,
          decl, codes):
    doc = _parse(tmp_path, name, data,
                 decl)
    assert doc.elements == []
    assert [w.code for w in
            doc.warnings] == codes


def test_single_asciihex(tmp_path):
    plain_hex = (_RAW.encode("latin-1")
                 .hex().encode() + b">")
    _ok(tmp_path, "hex.pdf", plain_hex,
        "/ASCIIHexDecode")


def test_empty_filter_array(
        tmp_path):
    _ok(tmp_path, "nofilter.pdf",
        _RAW.encode("latin-1"), "[]")


def test_chain_hex_then_flate(
        tmp_path):
    _ok(tmp_path, "chainok.pdf",
        _HEX,
        "[/ASCIIHexDecode"
        " /FlateDecode]")


def test_chain_flate_then_hex(
        tmp_path):
    _lost(tmp_path, "chainrev.pdf",
          _HEX,
          "[/FlateDecode"
          " /ASCIIHexDecode]",
          ["pdf_no_text_extracted"])


def test_chain_a85_wrong_order(
        tmp_path):
    _lost(tmp_path, "a85.pdf", _A85,
          "[/FlateDecode"
          " /ASCII85Decode]",
          ["pdf_no_text_extracted"])


def test_double_flate(tmp_path):
    _lost(tmp_path, "dfl.pdf",
          _FLATE,
          "[/FlateDecode"
          " /FlateDecode]",
          ["pdf_no_text_extracted"])


def test_plain_as_hex(tmp_path):
    _lost(tmp_path, "hexplain.pdf",
          _RAW.encode("latin-1"),
          "/ASCIIHexDecode",
          ["pdfplumber_word_extract"
           "_failed",
           "pdf_no_text_extracted"])


def test_unknown_filter(tmp_path):
    _lost(tmp_path, "foo.pdf",
          _RAW.encode("latin-1"),
          "/FooDecode",
          ["pdfplumber_word_extract"
           "_failed",
           "pdf_no_text_extracted"])
