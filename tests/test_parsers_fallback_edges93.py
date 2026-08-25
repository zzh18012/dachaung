r"""app/parsers/fallback_parser.py PDF 边角测试 - 第九十三轮（Round 1523）。

新角度（probe 实证）Type3 字体（最后一种未测字体类型；
R1515 测过 Type1 编码重映射、R1517 测过 Type0/CID）：

- **Type3 无 ToUnicode 原样提取**：/CharProcs 空 glyph
  流 + /Differences [97 /ga 98 /gb] → 'ab'、bbox 宽由
  /Widths×/FontMatrix×字号精确驱动（(600+700)×0.012×
  12=187.2 → x1=259.2）
- **Type3 + 单字节 ToUnicode 映射**：bfchar <61>→A →
  'AB'
- **超出 /LastChar 的码零宽**：'(abc)' 的 c（99 > 98）
  → 内容仍含 'c' 但 bbox 与 'ab' 完全相同（默认宽 0，
  字符叠加）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


_TU = ("/CIDInit /ProcSet findresource"
       " begin\n12 dict begin\nbegincmap\n"
       "/CIDSystemInfo << /Registry"
       " (Adobe) /Ordering (UCS)"
       " /Supplement 0 >> def\n"
       "/CMapName /Adobe-Identity-UCS"
       " def\n/CMapType 2 def\n"
       "1 begincodespacerange\n<00>"
       " <FF>\nendcodespacerange\n"
       "2 beginbfchar\n<61> <0041>\n"
       "<62> <0042>\nendbfchar\n"
       "endcmap\nCMapName currentdict"
       " /CMap defineresource pop\n"
       "end\nend")


def _pdf(tmp_path, name, content,
         tounicode=None):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(content)} >>"
        f"\nstream\n{content}"
        f"\nendstream",
        "<< /Type /Font /Subtype"
        " /Type3 /FontBBox"
        " [0 0 1000 1000]"
        " /FontMatrix"
        " [0.012 0 0 0.012 0 0]"
        " /CharProcs << /ga 7 0 R"
        " /gb 8 0 R >>"
        " /Encoding << /Type"
        " /Encoding /Differences"
        " [97 /ga 98 /gb] >>"
        " /FirstChar 97 /LastChar 98"
        " /Widths [600 700]"
        + (" /ToUnicode 9 0 R"
           if tounicode else "")
        + " >>",
        "<< /Length 0 >>\nstream\n"
        "\nendstream",
        "<< /Length 0 >>\nstream\n"
        "\nendstream",
        "<< /Length 0 >>\nstream\n"
        "\nendstream",
    ]
    if tounicode:
        objs.append(
            f"<< /Length"
            f" {len(tounicode)} >>"
            f"\nstream\n{tounicode}"
            f"\nendstream")
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += (f"trailer << /Root 1 0 R"
            f" /Size {len(objs) + 1} >>"
            f"\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _els(tmp_path, name, text,
         tounicode=None):
    content = ("BT /F1 12 Tf 72 700 Td"
               f" ({text}) Tj ET")
    p = _pdf(tmp_path, name, content,
             tounicode)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements], \
        doc.warnings


def test_type3_plain(tmp_path):
    got, warns = _els(
        tmp_path, "t3.pdf", "ab")
    assert got == [
        ("ab",
         [72.0, 80.0, 259.2, 92.0])]
    assert warns == []


def test_type3_tounicode(tmp_path):
    got, _ = _els(
        tmp_path, "t3tu.pdf", "ab",
        _TU)
    assert got == [
        ("AB",
         [72.0, 80.0, 259.2, 92.0])]


def test_type3_beyond_lastchar(
        tmp_path):
    got, _ = _els(
        tmp_path, "t3out.pdf", "abc")
    assert got == [
        ("abc",
         [72.0, 80.0, 259.2, 92.0])]
