r"""pipeline 多页图片命名与页内元素序（Round 1565）。

新角度：R1551-R1564 图片全部单页——**跨页**（第 2 页
图片 → _p2_00.png）与**页内 text→table→image 全序**
零覆盖：

- **第 2 页图片** → 文件名 `_p2_00.png`（无 p1 文件）
- **页内元素序**：先全部文本、再表格、最后图片；
  页间严格按页号升序
- **图片 bbox 翻转**：cm y=692（页高 792）→ bbox
  y=0..100
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


def _pdf(tmp_path: Path) -> Path:
    grid = " ".join(
        f"{x} {y} 100 30 re S"
        for x in (72, 172)
        for y in (650, 610))
    c1 = (grid
          + " BT /F1 10 Tf 80 655"
          " Td (t1) Tj ET"
          " BT /F1 10 Tf 80 615"
          " Td (t2) Tj ET")
    c2 = ("q 100 0 0 100"
          " 72 692 cm /Im1 Do Q"
          " BT /F1 12 Tf 72 650"
          " Td (BODY2) Tj ET")
    px = bytes([255, 0, 0])
    im = (f"<< /Type /XObject"
          f" /Subtype /Image"
          f" /Width 1 /Height 1"
          f" /ColorSpace /DeviceRGB"
          f" /BitsPerComponent 8"
          f" /Length {len(px)} >>"
          f"\nstream\n"
          ).encode() + px \
        + b"\nendstream"
    objs = {
        1: "<< /Type /Catalog"
           " /Pages 2 0 R >>",
        2: "<< /Type /Pages"
           " /Kids [3 0 R 4 0 R]"
           " /Count 2 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 6 0 R >>"
            " /XObject << /Im1"
            " 8 0 R >> >>"
            " /Contents 5 0 R >>"),
        4: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 6 0 R >>"
            " /XObject << /Im1"
            " 8 0 R >> >>"
            " /Contents 7 0 R >>"),
        5: f"<< /Length {len(c1)} >>"
           f"\nstream\n{c1}\n"
           f"endstream",
        6: _FONT,
        7: f"<< /Length {len(c2)} >>"
           f"\nstream\n{c2}\n"
           f"endstream",
        8: im,
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
            b" /Size 9 >>\n%%EOF")
    p = tmp_path / "x.pdf"
    p.write_bytes(pdf)
    return p


def test_image_page2_filename(
        tmp_path):
    p = _pdf(tmp_path)
    process_single(p, tmp_path / "o.json",
                   write_json=True)
    sha = compute_file_hash(p)[:16]
    idir = tmp_path / f"images-{sha}"
    assert sorted(
        f.name for f in idir.iterdir()
    ) == [f"image_{sha}"
          f"_p2_00.png"]


def test_page_internal_order(
        tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path),
        write_json=False)
    assert errors == []
    got = [(e.type,
            e.source_locator["page"])
           for e in doc.elements]
    assert got == [
        ("heading", 1),
        ("heading", 1),
        ("table", 1),
        ("table", 1),
        ("heading", 2),
        ("image", 2)]


def test_image_bbox_flip(
        tmp_path):
    doc, errors = process_single(
        _pdf(tmp_path),
        write_json=False)
    assert errors == []
    (img,) = [e for e
              in doc.elements
              if e.type == "image"]
    assert img.source_locator[
        "bbox"] == [72.0, 0.0,
                    172.0, 100.0]
