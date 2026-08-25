r"""pipeline CropBox 忽略与页级继承（Round 1587）。

新角度：R1580 锁 Resources 继承——**CropBox、
共享内容流、MediaBox 继承**零覆盖：

- **/CropBox [0 0 300 400]**（文本在裁剪区外）→
  裁剪被完全忽略：照常提取、bbox 与无 CropBox
  一致（y 翻转仍用 MediaBox 高 792）
- **两页共享同一内容流对象** → 各自产出元素、
  不去重
- **MediaBox/Resources 全挂 /Pages 节点**（页节点
  仅 /Contents）→ 继承生效、y 翻转用继承高 600
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
_RES = (" /Resources"
        " << /Font"
        " << /F1 50 0 R >> >>")


def _pdf(tmp_path: Path, name: str,
         pages: list,
         page_extra: str = "",
         pages_extra: str = "",
         page_has_own: bool = True
         ) -> Path:
    n = len(pages)
    kids = " ".join(
        f"{3 + 2 * i} 0 R"
        for i in range(n))
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: (f"<< /Type /Pages"
            f" /Kids [{kids}]"
            f" /Count {n}"
            f"{pages_extra} >>"),
        50: _FONT,
    }
    for i, c in enumerate(pages):
        own = (" /MediaBox"
               " [0 0 612 792]"
               if page_has_own else "")
        objs[3 + 2 * i] = (
            f"<< /Type /Page"
            f" /Parent 2 0 R"
            f"{own}{page_extra}"
            f"{'' if not page_has_own else _RES}"
            f" /Contents"
            f" {4 + 2 * i} 0 R >>")
        objs[4 + 2 * i] = (
            f"<< /Length {len(c)} >>"
            f"\nstream\n{c}\nendstream")
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
            b" /Size 51 >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def test_cropbox_ignored(tmp_path):
    c = ("BT /F1 12 Tf 72 700"
         " Td (CROPPED) Tj ET")
    p = _pdf(
        tmp_path, "crop.pdf", [c],
        page_extra=(" /CropBox"
                    " [0 0 300 400]"))
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "CROPPED"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 82.48, 131.34,
             94.48], abs=0.01)


def test_shared_content_stream(
        tmp_path):
    c = ("BT /F1 12 Tf 72 700"
         " Td (CROPPED) Tj ET")
    objs_extra = None
    p = _pdf(tmp_path, "same.pdf",
             [c, c])
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    got = [(e.content,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [("CROPPED", 1),
                   ("CROPPED", 2)]


def test_inherited_mediabox(
        tmp_path):
    c = ("BT /F1 12 Tf 72 500"
         " Td (INHM) Tj ET")
    p = _pdf(
        tmp_path, "inh.pdf", [c],
        pages_extra=(" /MediaBox"
                     " [0 0 612 600]"
                     + _RES),
        page_has_own=False)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (el,) = doc.elements
    assert el.content == "INHM"
    assert el.source_locator["bbox"] \
        == pytest.approx(
            [72.0, 90.48, 102.66,
             102.48], abs=0.01)
