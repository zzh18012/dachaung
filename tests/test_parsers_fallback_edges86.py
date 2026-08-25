r"""app/parsers/fallback_parser.py PDF 边角测试 - 第八十六轮（Round 1516）。

新角度（probe 实证）嵌套 Form XObject 与 Form /Matrix
（R1511 只测了单层 Form；真实 PDF 常见多层表单嵌套）：

- **双层嵌套变换精确复合**：page cm(100,500) → outer
  内 cm(50,60) → inner 文本 (10,20) → INNER 设备 bbox
  [160,202.5,197.3,214.5]（三级平移全部相加）
- **Form /Matrix 参与复合**：外层 Form 带 /Matrix
  [1 0 0 1 20 30] → 文本 (10,20) → 设备 x=100+20+10=
  130（Matrix 先于内容应用）
- **嵌套深度不破坏阅读序**：页底文本 PAGE 仍排最后、
  表单文本按页面位置自上而下
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import \
    FallbackParser


def _pdf(tmp_path, name, page, inner,
         outer, outer_extra="",
         outer_res=
         " << /Font << /F1 5 0 R >>"
         " /XObject"
         " << /Fm2 7 0 R >> >>"):
    objs = [
        "<< /Type /Catalog"
        " /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R]"
        " /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R"
        " /MediaBox [0 0 612 792]"
        " /Resources << /Font"
        " << /F1 5 0 R >> /XObject"
        " << /Fm1 6 0 R >> >>"
        " /Contents 4 0 R >>",
        f"<< /Length {len(page)} >>"
        f"\nstream\n{page}\nendstream",
        "<< /Type /Font /Subtype /Type1"
        " /BaseFont /Helvetica"
        " /Encoding /WinAnsiEncoding >>",
        f"<< /Type /XObject"
        f" /Subtype /Form /BBox"
        f" [0 0 300 200]{outer_extra}"
        f" /Resources{outer_res}"
        f" /Length {len(outer)} >>"
        f"\nstream\n{outer}\nendstream",
        f"<< /Type /XObject"
        f" /Subtype /Form /BBox"
        f" [0 0 100 50] /Resources"
        f" << /Font << /F1 5 0 R >> >>"
        f" /Length {len(inner)} >>"
        f"\nstream\n{inner}\nendstream",
    ]
    pdf = "%PDF-1.4\n" + "".join(
        f"{i + 1} 0 obj\n{o}\nendobj\n"
        for i, o in enumerate(objs))
    pdf += ("trailer << /Root 1 0 R"
            " /Size 8 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf.encode("latin-1"))
    return p


def _els(tmp_path, name, **kw):
    p = _pdf(tmp_path, name, **kw)
    doc = FallbackParser().parse(
        p, compute_file_hash(p))
    return [(e.content,
             [round(v, 1)
              for v in
              e.source_locator["bbox"]])
            for e in doc.elements]


_INNER = ("BT /F1 12 Tf 10 20 Td"
          " (INNER) Tj ET")
_OUTER = ("q 1 0 0 1 50 60 cm /Fm2 Do Q"
          " BT /F1 12 Tf 10 120 Td"
          " (OUTER) Tj ET")


def test_nested_form_composes(
        tmp_path):
    got = _els(
        tmp_path, "nest.pdf",
        page="q 1 0 0 1 100 500 cm"
             " /Fm1 Do Q",
        inner=_INNER, outer=_OUTER)
    assert got == [
        ("OUTER",
         [110.0, 162.5, 152.0, 174.5]),
        ("INNER",
         [160.0, 202.5, 197.3, 214.5]),
    ]


def test_form_matrix_composes(
        tmp_path):
    got = _els(
        tmp_path, "fmat.pdf",
        page="q 1 0 0 1 100 500 cm"
             " /Fm1 Do Q",
        inner="BT /F1 12 Tf 0 0 Td"
              " (ONLY) Tj ET",
        outer="BT /F1 12 Tf 10 20 Td"
              " (X) Tj ET",
        outer_extra=
        " /Matrix [1 0 0 1 20 30]",
        outer_res=
        " << /Font << /F1 5 0 R"
        " >> >>")
    assert got == [
        ("X", [130.0, 232.5,
               138.0, 244.5])]


def test_deep_reading_order(
        tmp_path):
    got = _els(
        tmp_path, "deep3.pdf",
        page="BT /F1 12 Tf 72 100 Td"
             " (PAGE) Tj ET"
             " q 1 0 0 1 100 500 cm"
             " /Fm1 Do Q",
        inner=_INNER, outer=_OUTER)
    assert [c for c, _ in got] == [
        "OUTER", "INNER", "PAGE"]
    assert doc_last(got) == [
        72.0, 682.5, 105.3, 694.5]


def doc_last(got):
    return got[-1][1]
