r"""pipeline 文本渲染状态：Tm 旋转/极端字号/缺 Tf（Round 1579）。

新角度：R1578 锁页几何——**文本矩阵与字号状态**
零覆盖：

- **竖排 Tm**（[0 1 -1 0]）→ 提取内容**字符倒序**
  'LACITREV'（90° 旋转下视觉行读取方向反转）
- **极端字号共存**（0.5pt + 300pt）→ 巨字形包围
  小字区域、两段文本合并**单元素**且分类 heading、
  bbox 允许负 y
- **缺 Tf**（Tj 前未设字体）→ pdfminer 提取为空 →
  no_extracted_elements + pdf_no_text_extracted 警告
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
         c: str) -> Path:
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R >>"),
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


def test_vertical_tm_reversed(
        tmp_path):
    p = _pdf(
        tmp_path, "vert.pdf",
        "BT /F1 12 Tf"
        " 0 1 -1 0 300 400 Tm"
        " (VERTICAL) Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "LACITREV"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [290.48, 333.32, 302.48,
             392.0], abs=0.01)


def test_extreme_font_sizes_merge(
        tmp_path):
    c = ("BT /F1 0.5 Tf 72 700"
         " Td (TINY) Tj ET"
         " BT /F1 300 Tf 72 600"
         " Td (HUGE) Tj ET")
    p = _pdf(tmp_path, "sizes.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.type == "heading"
    assert el.content == "TINY HUGE"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, -45.9, 938.7, 254.1],
            abs=0.01)
    (ch,) = doc.chunks
    assert ch.text == "TINY HUGE"


def test_missing_tf_no_elements(
        tmp_path):
    p = _pdf(
        tmp_path, "notf.pdf",
        "BT 72 700 Td (NOTF)"
        " Tj ET")
    doc, errors = process_single(
        p, write_json=False)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]
    w = errors[0].details["warnings"]
    assert [x["code"] for x in w] == [
        "pdf_no_text_extracted"]
