r"""pipeline 图片 XObject 声明变体（Round 1562）。

新角度：R1551/1552 锁标准 1×1 RGB 图；**退化/变体
声明**（0×0、灰度、ImageMask、截断像素、声明十万级
尺寸）经 pipeline 全链路零覆盖：

- 全部变体 → 零错误、srcsize 照抄声明、
  extracted_to_disk=True、PNG 真实落盘
- **100000×100000 声明尺寸**不炸（区域渲染按页面
  放置矩形，不按原生分辨率分配位图）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")


def _pdf(tmp_path: Path, dic: str,
         px: bytes) -> Path:
    c = ("q 100 0 0 100 72 692 cm"
         " /Im1 Do Q"
         " BT /F1 12 Tf 72 650 Td"
         " (BODY) Tj ET")
    im = (dic.format(n=len(px))
          .encode() + b"\nstream\n"
          + px + b"\nendstream")
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
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
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


def _one(tmp_path: Path, dic: str,
         px: bytes, srcsize):
    p = _pdf(tmp_path, dic, px)
    doc, errors = process_single(
        p, tmp_path / "o.json",
        write_json=True)
    assert errors == []
    imgs = [e for e in doc.elements
            if e.type == "image"]
    (e,) = imgs
    assert e.metadata["srcsize"] \
        == srcsize
    assert e.metadata[
        "extracted_to_disk"] is True
    d = [x for x
         in tmp_path.iterdir()
         if x.is_dir()]
    (idir,) = d
    files = list(idir.iterdir())
    assert [f.name[-10:]
            for f in files] == [
        "_p1_00.png"]
    assert files[0].stat().st_size \
        > 0


_RGB = ("<< /Type /XObject"
        " /Subtype /Image /Width 1"
        " /Height 1 /ColorSpace"
        " /DeviceRGB"
        " /BitsPerComponent 8"
        " /Length {n} >>")


def test_zero_dims(tmp_path):
    dic = ("<< /Type /XObject"
           " /Subtype /Image"
           " /Width 0 /Height 0"
           " /ColorSpace /DeviceRGB"
           " /BitsPerComponent 8"
           " /Length {n} >>")
    _one(tmp_path, dic,
         bytes([255, 0, 0]), [0, 0])


def test_gray_2x2(tmp_path):
    dic = ("<< /Type /XObject"
           " /Subtype /Image"
           " /Width 2 /Height 2"
           " /ColorSpace /DeviceGray"
           " /BitsPerComponent 8"
           " /Length {n} >>")
    _one(tmp_path, dic,
         bytes([0, 128, 200, 255]),
         [2, 2])


def test_image_mask(tmp_path):
    dic = ("<< /Type /XObject"
           " /Subtype /Image"
           " /Width 1 /Height 1"
           " /ImageMask true"
           " /BitsPerComponent 1"
           " /Length {n} >>")
    _one(tmp_path, dic, bytes([0]),
         [1, 1])


def test_truncated_pixel_data(
        tmp_path):
    _one(tmp_path, _RGB,
         bytes([255]), [1, 1])


def test_huge_declared_dims(
        tmp_path):
    dic = ("<< /Type /XObject"
           " /Subtype /Image"
           " /Width 100000"
           " /Height 100000"
           " /ColorSpace /DeviceRGB"
           " /BitsPerComponent 8"
           " /Length {n} >>")
    _one(tmp_path, dic,
         bytes([255, 0, 0]),
         [100000, 100000])
