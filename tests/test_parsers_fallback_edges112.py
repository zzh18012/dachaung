r"""app/parsers_fallback PDF 边角测试 - 第一百一十二轮（Round 1542）。

新角度（probe 实证）字体声明变体（此前轮次字体为
Type1/Type0/CIDFontType0/Type3 完整声明；真实 PDF 常见
TrueType 非嵌入、残缺声明——零覆盖）：

- **/Subtype /TrueType 非嵌入 + WinAnsi** → 同 Type1 行
  为（'BODY'、bbox 一致）
- **CIDFontType2 + Identity-H 无 ToUnicode** → 双字节
  CID 占位符 '(cid:16975)(cid:17497)'（BODY 的 16 位
  码）、DW 600 决定字宽
- **缺失 /Subtype** → 照常
- **仅 /Type+/Subtype+/BaseFont（无 /Encoding）** → 照
  常（默认编码回退）
- **缺失 /Type** → 照常
- **未知 /Encoding /BogusEncoding** → 静默回退照常
- **/Encoding 悬空间接引用**（指向不存在的 7 0 R）→ 容
  忍、回退编码
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser

_C = "BT /F1 12 Tf 72 700 Td (BODY) Tj ET"


def _els(tmp_path, name, font_obj):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages"
        " /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page"
        " /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(_C)} >>"
        f"\nstream\n{_C}\nendstream",
        font_obj,
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [(e.content,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_truetype_nonembedded(
        tmp_path):
    assert _els(
        tmp_path, "tt.pdf",
        "<< /Type /Font"
        " /Subtype /TrueType"
        " /BaseFont /Arial"
        " /Encoding"
        " /WinAnsiEncoding >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_cidfonttype2_placeholders(
        tmp_path):
    assert _els(
        tmp_path, "cidt2.pdf",
        "<< /Type /Font"
        " /Subtype /Type0"
        " /BaseFont /Test"
        " /Encoding /Identity-H"
        " /DescendantFonts"
        " [<< /Type /Font"
        " /Subtype /CIDFontType2"
        " /BaseFont /Test"
        " /CIDSystemInfo"
        " << /Registry (Adobe)"
        " /Ordering (Identity)"
        " /Supplement 0 >>"
        " /DW 600 >>] >>") == [
        ("(cid:16975)(cid:17497)",
         [72.0, 80.0, 86.4, 92.0])]


def test_missing_subtype(tmp_path):
    assert _els(
        tmp_path, "nosub.pdf",
        "<< /Type /Font"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_minimal_font(tmp_path):
    assert _els(
        tmp_path, "minfont.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont"
        " /Helvetica >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_missing_type(tmp_path):
    assert _els(
        tmp_path, "notype.pdf",
        "<< /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_unknown_encoding(tmp_path):
    assert _els(
        tmp_path, "bogusenc.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /BogusEncoding >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]


def test_dangling_encoding_ref(
        tmp_path):
    assert _els(
        tmp_path, "refenc.pdf",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding 7 0 R >>") == [
        ("BODY", [72.0, 82.5, 106.0,
                  94.5])]
