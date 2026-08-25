r"""pipeline 资源继承与重叠/变换文本（Round 1580）。

新角度：R1579 锁渲染状态——**Resources 继承、
重叠重复文本、cm 变换**零覆盖：

- **Resources 挂在 /Pages 节点**（页节点不写）→
  pdfminer 按继承链解析、正常提取
- **同位置重复绘制同文本两次** → pdfminer 字符级
  **交错合并** 'DDUUPP'（单元素）
- **cm 横向 100 倍缩放**（+200 平移）→ 文本 bbox
  变换至 [7400, ...] 深出页外仍提取
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
_RES = "<< /Font << /F1 5 0 R >> >>"


def _objs(c: str,
          res_on_pages: bool = False):
    page_res = "" if res_on_pages \
        else f" /Resources {_RES}"
    pages_res = f" /Resources {_RES}" \
        if res_on_pages else ""
    return {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: (f"<< /Type /Pages"
            f" /Kids [3 0 R]"
            f" /Count 1"
            f"{pages_res} >>"),
        3: (f"<< /Type /Page"
            f" /Parent 2 0 R"
            f" /MediaBox"
            f" [0 0 612 792]"
            f"{page_res}"
            f" /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
    }


def _pdf(tmp_path: Path, name: str,
         c: str,
         res_on_pages=False) -> Path:
    objs = _objs(c, res_on_pages)
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


def test_resources_inherited_from_pages(
        tmp_path):
    p = _pdf(
        tmp_path, "inh.pdf",
        "BT /F1 12 Tf 72 700"
        " Td (INHERITED) Tj ET",
        res_on_pages=True)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "INHERITED"


def test_overlapping_text_interleaved(
        tmp_path):
    c = ("BT /F1 12 Tf 72 700"
         " Td (DUP) Tj ET"
         " BT /F1 12 Tf 72 700"
         " Td (DUP) Tj ET")
    p = _pdf(tmp_path, "dup.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "DDUUPP"
    (c1,) = doc.chunks
    assert c1.text == "DDUUPP"


def test_cm_scaled_text_offpage(
        tmp_path):
    c = ("q 100 0 0 1 200 0 cm"
         " BT /F1 12 Tf 72 700"
         " Td (SHIFTCM) Tj ET Q")
    p = _pdf(tmp_path, "cm.pdf", c)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "SHIFTCM"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [7400.0, 82.48, 12732.8,
             94.48], abs=0.01)
