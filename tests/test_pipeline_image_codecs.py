r"""pipeline 图片编码变体：JPEG/CMYK/Decode 反相（Round 1582）。

新角度：R1562 锁基础 XObject——**压缩与色彩编码**
零覆盖：

- **DCTDecode JPEG**（PIL 生成 2×2）→ 正常提取、
  渲染为合法 PNG
- **DeviceCMYK** → 提取渲染成功
- **/Decode [1 0 1 0 1 0] 反相** → 渲染像素真的
  反转（红 → 青），Decode 数组被渲染器尊重
"""

from __future__ import annotations

import io

from pathlib import Path

from PIL import Image

from app.hash import compute_file_hash
from app.pipeline import process_single

_FONT = ("<< /Type /Font"
         " /Subtype /Type1"
         " /BaseFont /Helvetica"
         " /Encoding"
         " /WinAnsiEncoding >>")
_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _pdf(tmp_path: Path, name: str,
         img_obj: bytes) -> Path:
    c = ("q 100 0 0 100 72 692"
         " cm /Im1 Do Q"
         " BT /F1 12 Tf 72 650"
         " Td (BODY) Tj ET")
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
            " /XObject"
            " << /Im1 8 0 R >> >>"
            " /Contents 4 0 R >>"),
        4: f"<< /Length {len(c)} >>"
           f"\nstream\n{c}\nendstream",
        5: _FONT,
        8: img_obj,
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
    p = tmp_path / name
    p.write_bytes(pdf)
    return p


def _img_obj(spec: str,
             data: bytes) -> bytes:
    return ((f"<< /Type /XObject"
             f" /Subtype /Image"
             f" /Width 2 /Height 2"
             f" /BitsPerComponent 8"
             f"{spec}"
             f" /Length"
             f" {len(data)} >>"
             f"\nstream\n"
             ).encode()
            + data + b"\nendstream")


def _extract(tmp_path, p: Path):
    out = tmp_path / "o.json"
    doc, errors = process_single(
        p, output_path=out)
    assert errors == []
    imgs = [e for e in doc.elements
            if e.type == "image"]
    (im,) = imgs
    assert im.metadata["srcsize"] == [2, 2]
    assert im.metadata[
        "extracted_to_disk"] is True
    assert Path(
        im.resource_path)\
        .read_bytes()[:8] == _PNG_SIG
    return im


def test_dctdecode_jpeg(tmp_path):
    buf = io.BytesIO()
    Image.new("RGB", (2, 2),
              (255, 0, 0))\
        .save(buf, format="JPEG")
    jpeg = buf.getvalue()
    spec = (" /ColorSpace"
            " /DeviceRGB"
            " /Filter /DCTDecode")
    p = _pdf(tmp_path, "j.pdf",
             _img_obj(spec, jpeg))
    im = _extract(tmp_path, p)
    assert im.resource_path.endswith(
        "_p1_00.png")


def test_cmyk_image(tmp_path):
    cmyk = bytes(
        [0, 0, 0, 255] * 4)
    spec = (" /ColorSpace"
            " /DeviceCMYK")
    p = _pdf(tmp_path, "c.pdf",
             _img_obj(spec, cmyk))
    im = _extract(tmp_path, p)
    assert im.resource_path.endswith(
        "_p1_00.png")


def test_decode_array_inverts(
        tmp_path):
    px = bytes([255, 0, 0,
                0, 255, 0,
                0, 0, 255,
                255, 255, 0])
    spec = (" /ColorSpace"
            " /DeviceRGB"
            " /Decode"
            " [1 0 1 0 1 0]")
    p = _pdf(tmp_path, "d.pdf",
             _img_obj(spec, px))
    im = _extract(tmp_path, p)
    got = Image.open(
        im.resource_path)\
        .convert("RGB")
    pixels = list(
        got.getdata())
    assert pixels[0] == (0, 255, 255)
    assert all(
        px == (0, 255, 255)
        for px in pixels[:50])
