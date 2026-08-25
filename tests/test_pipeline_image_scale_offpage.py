r"""pipeline 图片规模与页外放置（Round 1564）。

新角度：R1563 锁了同一 XObject 两次绘制——**规模
（50 次）与页外坐标**零覆盖：

- **同图 50 次绘制** → 50 个 image 元素 + 50 个文件
  _p1_00.._p1_49（线性、不去重）
- **页外绘制**（cm 平移 x=5000）→ 元素**保留**（bbox
  [5000,0,5100,100]）但**不渲染**：extracted_to_disk=
  False、resource_path='(unrendered)' 哨兵、零错误、
  chunks 不受影响
"""

from __future__ import annotations

import json
from pathlib import Path

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path,
         content: str) -> Path:
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
           " /Kids [3 0 R]"
           " /Count 1 >>",
        3: ("<< /Type /Page"
            " /Parent 2 0 R"
            " /MediaBox"
            " [0 0 612 792]"
            " /Resources << /Font"
            " << /F1 5 0 R >>"
            " /XObject << /Im1"
            " 7 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(content)} >>"
           f"\nstream\n{content}\n"
           f"endstream",
        5: _FONT,
        7: im,
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
            b" /Size 8 >>\n%%EOF")
    p = tmp_path / "x.pdf"
    p.write_bytes(pdf)
    return p


def test_fifty_draws_fifty_files(
        tmp_path):
    draws = " ".join(
        f"q 10 0 0 10"
        f" {20 + (i % 10) * 55}"
        f" {40 + (i // 10) * 70}"
        f" cm /Im1 Do Q"
        for i in range(50))
    content = (draws
               + " BT /F1 12 Tf"
               " 72 730 Td"
               " (BODY) Tj ET")
    p = _pdf(tmp_path, content)
    doc, errors = process_single(
        p, tmp_path / "o.json",
        write_json=True)
    assert errors == []
    imgs = [e for e in doc.elements
            if e.type == "image"]
    assert len(imgs) == 50
    sha = compute_file_hash(p)[:16]
    d = tmp_path / f"images-{sha}"
    names = sorted(
        f.name for f in d.iterdir())
    assert names == [
        f"image_{sha}"
        f"_p1_{i:02d}.png"
        for i in range(50)]
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]


def test_off_page_kept_unrendered(
        tmp_path):
    content = ("q 100 0 0 100"
               " 5000 692 cm"
               " /Im1 Do Q"
               " BT /F1 12 Tf"
               " 72 650 Td"
               " (BODY) Tj ET")
    p = _pdf(tmp_path, content)
    doc, errors = process_single(
        p, write_json=False)
    assert errors == []
    (img,) = [e for e
              in doc.elements
              if e.type == "image"]
    assert img.source_locator[
        "bbox"] == [5000.0, 0.0,
                    5100.0, 100.0]
    assert img.metadata[
        "extracted_to_disk"] is False
    assert img.resource_path \
        == "(unrendered)"
    assert [c.text
            for c in doc.chunks] == [
        "BODY"]


def test_off_page_in_json(
        tmp_path):
    content = ("q 100 0 0 100"
               " 5000 692 cm"
               " /Im1 Do Q"
               " BT /F1 12 Tf"
               " 72 650 Td"
               " (BODY) Tj ET")
    p = _pdf(tmp_path, content)
    out = tmp_path / "o.json"
    process_single(p, out,
                   write_json=True)
    data = json.loads(
        out.read_text(encoding="utf-8"))
    (el,) = [el for el
             in data["elements"]
             if el["type"] == "image"]
    assert el["content"] is None
    assert el[
        "resource_path"] \
        == "(unrendered)"
    assert el["metadata"][
        "extracted_to_disk"] is False
