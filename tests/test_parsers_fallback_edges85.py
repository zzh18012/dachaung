r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十五轮（Round 1515）。

新角度（probe 实证）字体编码重映射家族（此前轮次全部
固定 WinAnsiEncoding Helvetica）：

- **/Differences 字形名重映射生效**：[65 /Beta /euro] →
  'ABC' 提取为 'Β€C'（字形名查 Unicode 表，未映射的 C
  不变）
- **高位码 /Differences**：[97 /alpha /beta /gamma] →
  'abcd' → 'αβγd'
- **Symbol 字体直通**：/BaseFont /Symbol 无 Encoding →
  'ab' 原样提取（pdfminer 未应用 Symbol 希腊映射）
- **ZapfDingbats 字体直通**：同上 'ab' 原样
- **/MacRomanEncoding 生效**：bytes \\x80\\x81 → 'ÄÅ'
  （MacRoman 0x80=Ä、0x81=Å，正确按编码表映射）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, font, content):
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\nendstream",
        font,
    ]
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += ("trailer << /Root 1 0 R"
            " /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _content(tmp_path, name, font,
             text):
    content = ("BT /F1 12 Tf 72 700 Td"
               f" ({text}) Tj ET")
    p = _pdf(tmp_path, name, font,
             content)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [e.content
            for e in doc.elements], \
        [w.code for w in doc.warnings]


def test_differences_glyph_remap(
        tmp_path):
    got, warns = _content(
        tmp_path, "diff.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " << /BaseEncoding"
        " /WinAnsiEncoding"
        " /Differences"
        " [65 /Beta /euro] >> >>",
        "ABC")
    assert got == ["Β€C"]
    assert warns == []


def test_differences_high_codes(
        tmp_path):
    got, _ = _content(
        tmp_path, "diffhi.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " << /BaseEncoding"
        " /WinAnsiEncoding"
        " /Differences"
        " [97 /alpha /beta"
        " /gamma] >> >>",
        "abcd")
    assert got == ["αβγd"]


def test_symbol_font_literal(
        tmp_path):
    got, _ = _content(
        tmp_path, "symbol.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Symbol >>",
        "ab")
    assert got == ["ab"]


def test_zapfdingbats_literal(
        tmp_path):
    got, _ = _content(
        tmp_path, "zapf.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont"
        " /ZapfDingbats >>",
        "ab")
    assert got == ["ab"]


def test_macroman_encoding(
        tmp_path):
    content = ("BT /F1 12 Tf 72 700 Td"
               " (\x80\x81) Tj ET")
    p = _pdf(
        tmp_path, "macrom.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /MacRomanEncoding >>",
        content)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert [e.content
            for e in doc.elements] == [
        "ÄÅ"]
