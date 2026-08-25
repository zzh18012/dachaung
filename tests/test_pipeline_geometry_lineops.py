r"""pipeline 页几何与换行操作符（Round 1578）。

新角度：R1574 锁页缘文本——**MediaBox 平移/矮页
与 T*/' 换行操作符**零覆盖：

- **MediaBox 原点平移**（[100 100 712 892]，文本
  x=72 落在盒外）→ 报告 bbox 与未平移**完全一致**
  （x 原样、y 只按盒高翻转，原点坐标被忽略），
  盒外文本照常提取
- **矮页**（高 600）→ y 翻转用盒高 600 而非默认
  792（y=500 → bbox y0=90.484）
- **T* 换行**（TL=14，三行）→ 单元素合并
- **' 操作符**（先 TL 再两撇）→ 'Q1 Q2' 合并单元素
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, name: str,
         c: str,
         media: str = "[0 0 612 792]"
         ) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: (f"<< /Type /Page"
            f" /Parent 2 0 R"
            f" /MediaBox {media}"
            f" /Resources << /Font"
            f" << /F1 5 0 R >> >>"
            f" /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }
    pdf = b"%PDF-1.4\n"
    for oid in sorted(objs):
        o = objs[oid]
        if isinstance(o, str):
            o = o.encode("latin-1")
        pdf += (f"{oid} 0 obj\n"
                ).encode() + o \
            + b"\nendobj\n"
    pdf += (b"trailer"
            b" << /Root 1 0 R"
            b" /Size 6 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_mediabox_origin_ignored(
        tmp_path):
    p = _pdf(
        tmp_path, "origin.pdf",
        "BT /F1 12 Tf 72 700"
        " Td (SHIFTED) Tj ET",
        media="[100 100 712 892]")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "SHIFTED"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 82.484, 123.336,
             94.484], abs=1e-6)


def test_short_page_flip_uses_height(
        tmp_path):
    p = _pdf(
        tmp_path, "short.pdf",
        "BT /F1 12 Tf 72 500"
        " Td (SHORTPG) Tj ET",
        media="[0 0 612 600]")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 90.484, 131.34,
             102.484], abs=1e-6)


def test_tstar_leading_merge(
        tmp_path):
    c = ("BT /F1 12 Tf 14 TL"
         " 72 700 Td (LINEA) Tj"
         " T* (LINEB) Tj"
         " T* (LINEC) Tj ET")
    p = _pdf(tmp_path, "tstar.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == (
        "LINEA LINEB LINEC")
    (c,) = doc.chunks
    assert c.text == el.content


def test_quote_operator_lines(
        tmp_path):
    c = ("BT /F1 12 Tf 20 TL"
         " 72 700 Td"
         " (Q1)' (Q2)' ET")
    p = _pdf(tmp_path, "quote.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "Q1 Q2"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 102.484, 88.008,
             134.484], abs=1e-6)
