r"""pipeline 内联图片与重复绘制（Round 1563）。

新角度：R1551-R1562 全部用 XObject 图片——两个相邻
形态零覆盖：

- **内联图片 BI/ID/EI**（无 XObject 资源）→ 同样被
  提取为 image 元素并落盘
- **同一 XObject 一页绘制两次** → 两个 image 元素、
  两个文件 _p1_00/_p1_01（按绘制次数提取，不按内容
  去重）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_TEXT = ("BT /F1 12 Tf 72 650 Td"
         " (BODY) Tj ET")


def _pdf(tmp_path: Path,
         content: bytes,
         with_xobj: bool) -> Path:
    res = "/Font << /F1 5 0 R >>"
    if with_xobj:
        res += (" /XObject"
                " << /Im1 7 0 R >>")
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
            f" /Resources << {res} >>"
            " /Contents 4 0 R >>"),
    }
    objs[4] = (b"<< /Length "
               + str(len(content))
               .encode()
               + b" >>\nstream\n"
               + content
               + b"\nendstream")
    objs[5] = _FONT
    if with_xobj:
        px = bytes([255, 0, 0])
        objs[7] = (
            f"<< /Type /XObject"
            f" /Subtype /Image"
            f" /Width 1 /Height 1"
            f" /ColorSpace /DeviceRGB"
            f" /BitsPerComponent 8"
            f" /Length {len(px)} >>"
            f"\nstream\n"
            ).encode() + px \
            + b"\nendstream"
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
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / "x.pdf"
    p.write_bytes(pdf)
    return p


def _imgs(doc):
    return [e for e in doc.elements
            if e.type == "image"]


def test_inline_image(tmp_path):
    px = bytes([0, 255, 0])
    content = (
        b"q 100 0 0 100 72 692 cm"
        b" BI /W 1 /H 1 /CS /RGB"
        b" /BPC 8 ID " + px
        + b" EI Q " + _TEXT.encode())
    p = _pdf(tmp_path, content,
             with_xobj=False)
    doc, errors = process_single(
        p, tmp_path / "o.json",
        write_json=True)
    assert errors == []
    (e,) = _imgs(doc)
    assert e.metadata["srcsize"] \
        == [1, 1]
    assert e.metadata[
        "extracted_to_disk"] is True
    sha = compute_file_hash(p)[:16]
    d = tmp_path / f"images-{sha}"
    assert (d / f"image_{sha}"
            f"_p1_00.png").is_file()
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]


def test_same_xobject_twice(
        tmp_path):
    content = (
        "q 100 0 0 100 72 692 cm"
        " /Im1 Do Q"
        " q 100 0 0 100 200 692 cm"
        " /Im1 Do Q "
        + _TEXT).encode()
    p = _pdf(tmp_path, content,
             with_xobj=True)
    doc, errors = process_single(
        p, tmp_path / "o.json",
        write_json=True)
    assert errors == []
    imgs = _imgs(doc)
    assert len(imgs) == 2
    assert all(
        e.metadata[
            "extracted_to_disk"]
        is True for e in imgs)
    sha = compute_file_hash(p)[:16]
    d = tmp_path / f"images-{sha}"
    assert sorted(
        f.name for f in d.iterdir()
    ) == [f"image_{sha}"
          f"_p1_00.png",
          f"image_{sha}"
          f"_p1_01.png"]
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]
