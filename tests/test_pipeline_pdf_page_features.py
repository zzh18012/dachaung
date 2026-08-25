r"""pipeline PDF 页级特性家族（Round 1566）。

新角度：此前 60+ 轮 PDF 边角全部聚焦**内容流**——
页 dict/catalog 级特性零覆盖：

- **/Annots（Link 注释）**、**/AcroForm（表单字段
  /V 值）**、**/Outlines（书签）** → 全部中性：仅
  BODY 元素、零错误（表单值不进 elements）
- **/Rotate 90 / 270** → 文本 bbox 被旋转变换（probe
  实证精确值：rot90 [697.516,72,709.516,106.008]、
  rot270 [82.484,505.992,94.484,540]）；**⚠ rot270
  字符序反转 'YDOB'**（与 R1531 cm 旋转镜像一致）
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
         page_extra: str = "",
         catalog_extra: str = "",
         extra_objs=None) -> Path:
    content = ("BT /F1 12 Tf"
               " 72 700 Td"
               " (BODY) Tj ET")
    objs = {
        1: (f"<< /Type /Catalog"
            f" /Pages 2 0 R"
            f"{catalog_extra} >>"),
        2: "<< /Type /Pages"
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >> >>"
            " /Contents 4 0 R"
            f"{page_extra} >>"),
        4: f"<< /Length {len(content)} >>"
           f"\nstream\n{content}\n"
           f"endstream",
        5: _FONT,
    }
    if extra_objs:
        objs.update(extra_objs)
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
            b" /Size "
            + str(len(objs) + 1).encode()
            + b" >>\n%%EOF")
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _body_only(tmp_path, name, **kw):
    p = _pdf(tmp_path, name, **kw)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "BODY")]
    assert doc.chunks
    return doc


def test_annots_neutral(tmp_path):
    _body_only(
        tmp_path, "a.pdf",
        page_extra=" /Annots [6 0 R]",
        extra_objs={
            6: ("<< /Type /Annot"
                " /Subtype /Link"
                " /Rect"
                " [72 700 200 720]"
                " /Border [0 0 0]"
                " >>")})


def test_acroform_value_ignored(
        tmp_path):
    _body_only(
        tmp_path, "f.pdf",
        catalog_extra=" /AcroForm 6 0 R",
        extra_objs={
            6: "<< /Fields [7 0 R] >>",
            7: ("<< /T (name1)"
                " /FT /Tx"
                " /V (Form Value)"
                " /Rect"
                " [72 600 300 620]"
                " >>")})


def test_outlines_neutral(tmp_path):
    _body_only(
        tmp_path, "o.pdf",
        catalog_extra=" /Outlines 6 0 R",
        extra_objs={
            6: ("<< /Type /Outlines"
                " /First 7 0 R"
                " /Last 7 0 R"
                " /Count 1 >>"),
            7: ("<< /Title"
                " (Bookmark One)"
                " /Parent 6 0 R"
                " /Dest [3 0 R /XYZ"
                " null null null]"
                " >>")})


def test_rotate_90_bbox(tmp_path):
    doc = _body_only(
        tmp_path, "r90.pdf",
        page_extra=" /Rotate 90")
    assert doc.elements[0]\
        .source_locator["bbox"] \
        == pytest.approx([
            697.516, 72.0,
            709.516, 106.008],
            abs=1e-6)


def test_rotate_270_bbox(tmp_path):
    p = _pdf(tmp_path, "r270.pdf",
             page_extra=" /Rotate 270")
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    e = doc.elements[0]
    assert e.content == "YDOB"
    assert e.source_locator["bbox"] \
        == pytest.approx([
            82.484, 505.992,
            94.484, 540.0],
            abs=1e-6)
