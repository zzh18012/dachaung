r"""app/parsers_fallback PDF 边角测试 - 第一百零八轮（Round 1538）。

新角度（probe 实证）词内混排家族（真实 PDF 常态：粗体
词中切换字体/字号；此前轮次单元素内字体字号恒定）：

- **词中换字体不裂词**：Helvetica(abc)+Courier(def)+
  Helvetica(ghi) → 单词 'abcdefghi'（字体切换不参与分
  词）
- **⚠ 词中换字号裂词且乱序**：12(abc)+24(DEF)+12(ghi)
  → 'DEF abc ghi' 三词且 24pt 段排前
- **词中换渲染模式不裂词**：Tr 0(abc)+3(inv)+0(ghi) →
  'abcinvghi'（隐形段照常并入）
- **整词隐形照常提取**（与既有 Tr 3 结论一致，独立元素）
- **⚠ 同位异字体叠印 → 字符级交错**：'OVER'+'LAY' 同
  位置 → 'OLAVYER'（按 x 坐标逐字穿插，内容损坏且零
  警告）
- **纯空格串 (␣␣␣) → 无元素**（静默丢弃、零警告）
- **空串 () → 无元素**（同上）
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
        " << /F1 5 0 R /F2 6 0 R >>"
        " >> /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}\n"
        f"endstream",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding"
        " /WinAnsiEncoding >>",
        "<< /Type /Font"
        " /Subtype /Type1"
        " /BaseFont /Courier"
        " /Encoding"
        " /WinAnsiEncoding >>",
    ]
    pdf = b"%PDF-1.4\n"
    for i, o in enumerate(objs):
        pdf += (f"{i + 1} 0 obj\n{o}"
                f"\nendobj\n"
                ).encode("latin-1")
    pdf += (b"trailer << /Root 1 0 R"
            b" /Size 7 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    assert doc.warnings == []
    return [(e.content, e.type,
             [round(v, 1) for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


def test_midword_font_change(
        tmp_path):
    assert _els(
        tmp_path, "fontmix.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (abc) Tj /F2 12 Tf"
        " (def) Tj /F1 12 Tf"
        " (ghi) Tj ET") == [
        ("abcdefghi", "heading",
         [72.0, 82.3, 129.0,
          94.5])]


def test_midword_size_change(
        tmp_path):
    assert _els(
        tmp_path, "sizemix.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (abc) Tj /F1 24 Tf"
        " (DEF) Tj /F1 12 Tf"
        " (ghi) Tj ET") == [
        ("DEF abc ghi", "heading",
         [72.0, 73.0, 155.4,
          97.0])]


def test_midword_rendermode(
        tmp_path):
    assert _els(
        tmp_path, "trmix.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (abc) Tj 3 Tr (inv) Tj"
        " 0 Tr (ghi) Tj ET") == [
        ("abcinvghi", "heading",
         [72.0, 82.5, 122.7,
          94.5])]


def test_invisible_word_still_extracted(
        tmp_path):
    assert _els(
        tmp_path, "ghost.pdf",
        "BT /F1 12 Tf 3 Tr 72 700"
        " Td (GHOSTWORD) Tj 0 Tr"
        " ET BT /F1 12 Tf 72 650"
        " Td (REAL) Tj ET") == [
        ("GHOSTWORD", "heading",
         [72.0, 82.5, 152.7,
          94.5]),
        ("REAL", "heading",
         [72.0, 132.5, 103.3,
          144.5])]


def test_overlay_interleaves(
        tmp_path):
    assert _els(
        tmp_path, "overlay.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (OVER) Tj ET"
        " BT /F2 12 Tf 72 700 Td"
        " (LAY) Tj ET") == [
        ("OLAVYER", "heading",
         [72.0, 82.3, 106.0,
          94.5])]


def test_spaces_only_dropped(
        tmp_path):
    assert _els(
        tmp_path, "spaces.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " (   ) Tj ET"
        " BT /F1 12 Tf 72 650 Td"
        " (TEXT) Tj ET") == [
        ("TEXT", "heading",
         [72.0, 132.5, 102.7,
          144.5])]


def test_empty_string_dropped(
        tmp_path):
    assert _els(
        tmp_path, "empty.pdf",
        "BT /F1 12 Tf 72 700 Td"
        " () Tj ET"
        " BT /F1 12 Tf 72 650 Td"
        " (TEXT) Tj ET") == [
        ("TEXT", "heading",
         [72.0, 132.5, 102.7,
          144.5])]
