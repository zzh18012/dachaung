r"""app/parsers_fallback PDF 边角测试 - 第一百零七轮（Round 1537）。

新角度（probe 实证）Tm 矩阵极端 + 字号极端（此前轮次
Tm/Tf 均为规范正交矩阵与常规字号；页面级 /Rotate 已锁
——本轮是**文本级**几何变换）：

- **Tm 90° 旋转 [0 1 -1 0]**：'VERT' → 'TREV'（字符逐个
  竖排、阅读序反转）、bbox 成 12pt 宽竖条 [62.5, 60,
  74.5, 92]
- **Tm 270° [0 -1 1 0]**：'V270' 不反转、竖条上移
- **⚠ Tm 斜切 [1 0.5 0 1]**：'SKEW' → 'W E K S'（剪切
  使各字符基线错位 → 逐字裂词 + 顺序打乱）
- **Tm 零横列 [0 0 0 1]**：零宽 bbox（x1==x2==72）、文
  本仍完整
- **Tm 零纵列 [1 0 0 0]**：零高 bbox 且 'ZV' → 'Z V'
  （字符同行叠点后裂词）
- **非均匀缩放 [2 0 0 0.5]**：内容不变、bbox 高度压至
  6pt
- **Tf 0.001**：'TINY' 完整提取、bbox 退化为一点
  [72, 92, 72, 92]
- **⚠ Tf 1000 + 同页 12pt**：并成一元素 'BIG SMALL'、
  bbox y 达 -701..299（千级行盒吞并常规行且越出页面）
- **竖排 + 横排同页**：仍并成单元素 'TREV HORIZ'
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _els(tmp_path, name, content):
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
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
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
    return [(e.content, e.type,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_tm_rotate90(tmp_path):
    assert _els(
        tmp_path, "rot90.pdf",
        "BT /F1 12 Tf 0 1 -1 0 72 700"
        " Tm (VERT) Tj ET") == [
        ("TREV", "heading",
         [62.5, 60.0, 74.5, 92.0])]


def test_tm_rotate270(tmp_path):
    assert _els(
        tmp_path, "rot270.pdf",
        "BT /F1 12 Tf 0 -1 1 0 72 700"
        " Tm (V270) Tj ET") == [
        ("V270", "heading",
         [69.5, 92.0, 81.5, 120.0])]


def test_tm_skew_scrambles(tmp_path):
    assert _els(
        tmp_path, "skew.pdf",
        "BT /F1 12 Tf 1 0.5 0 1 72 700"
        " Tm (SKEW) Tj ET") == [
        ("W E K S", "heading",
         [72.0, 64.8, 107.3, 94.5])]


def test_tm_zero_horizontal(
        tmp_path):
    assert _els(
        tmp_path, "zeroh.pdf",
        "BT /F1 12 Tf 0 0 0 1 72 700"
        " Tm (ZH) Tj ET") == [
        ("ZH", "heading",
         [72.0, 82.5, 72.0, 94.5])]


def test_tm_zero_vertical(
        tmp_path):
    assert _els(
        tmp_path, "zerov.pdf",
        "BT /F1 12 Tf 1 0 0 0 72 700"
        " Tm (ZV) Tj ET") == [
        ("Z V", "heading",
         [72.0, 92.0, 87.3, 92.0])]


def test_tm_nonuniform(tmp_path):
    assert _els(
        tmp_path, "nonuni.pdf",
        "BT /F1 12 Tf 2 0 0 0.5 72 700"
        " Tm (NU) Tj ET") == [
        ("NU", "heading",
         [72.0, 87.2, 106.7, 93.2])]


def test_tiny_font(tmp_path):
    assert _els(
        tmp_path, "tiny.pdf",
        "BT /F1 0.001 Tf 72 700 Td"
        " (TINY) Tj ET") == [
        ("TINY", "heading",
         [72.0, 92.0, 72.0, 92.0])]


def test_huge_font_swallows(
        tmp_path):
    assert _els(
        tmp_path, "big.pdf",
        "BT /F1 1000 Tf 72 700 Td"
        " (BIG) Tj ET"
        " BT /F1 12 Tf 72 600 Td"
        " (SMALL) Tj ET") == [
        ("BIG SMALL", "heading",
         [72.0, -701.0, 1795.0,
          299.0])]


def test_vertical_plus_horizontal(
        tmp_path):
    assert _els(
        tmp_path, "mix.pdf",
        "BT /F1 12 Tf 0 1 -1 0 300 700"
        " Tm (VERT) Tj ET"
        " BT /F1 12 Tf 72 650 Td"
        " (HORIZ) Tj ET") == [
        ("TREV HORIZ", "heading",
         [72.0, 60.0, 302.5,
          144.5])]
