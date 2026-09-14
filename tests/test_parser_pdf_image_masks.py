r"""PDF 图像透明蒙版三形态——SMask 渲染兑现、色键抠黑、悬空蒙版忽略（Round 1947，a 优先级）。

grep 实证 /SMask 与 /Mask 零覆盖；R1936 锁 /ImageMask 模板
（图本身即蒙版），**作为基图附属的透明蒙版**零覆盖。探针
R1947 实证（基图 2x2 全黑 + 100pt 放置 @144dpi → 200x200
PNG，四象限采样）：

- **S1 软蒙版兑现后摊平**：/SMask（灰度 1bit \xa5）→ PNG
  恰 TL 象限 (0,0,0)、其余 (255,255,255)——alpha 被 pdfium
  摊平到白底（PNG mode RGB 非 RGBA）；SMask 子图不放置不
  成元素；零告警
- **S2 色键蒙版抠掉黑**：/Mask [0 64]³ + 全黑源 → 四象限全
  白（命中色键的像素全透明）；零告警
- **S3 悬空 SMask 被忽略**：/SMask 99 0 R（对象不存在）→
  照发元素、PNG 四象限全黑（蒙版缺失当无蒙版，对照 R1939
  悬空**放置**是静默跳过——悬空**蒙版**不跳基图）、零告警

判别式：若渲染不兑现蒙版则 S1/S2 象限像素断言翻红；若悬空
蒙版引入校验/告警则 S3 零告警翻红；若 alpha 改保留则 PNG
mode 断言（RGB）翻红。
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_FONT = (b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
         b"/Encoding /WinAnsiEncoding >>")
_SMASK = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
          b"/ColorSpace /DeviceGray /BitsPerComponent 1 /Length 1 >>\n"
          b"stream\n\xa5\nendstream")
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)


def _pdf(extra_img_keys: bytes, smask_obj: bytes | None) -> bytes:
    c = b"q 100 0 0 100 450 600 cm /Im1 Do Q"
    img = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
           b"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
           + extra_img_keys + b" /Length 12 >>\nstream\n"
           + b"\x00" * 12 + b"\nendstream")
    objs: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 6 0 R >> "
            b"/XObject << /Im1 5 0 R >> >> /Contents 4 0 R >>"),
        4: (b"<< /Length " + str(len(c)).encode() + b" >>\nstream\n"
            + c + b"\nendstream"),
        5: img,
        6: _FONT,
    }
    if smask_obj is not None:
        objs[7] = smask_obj
    pdf = b"%PDF-1.4\n"
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(pdf)
        pdf += f"{oid} 0 obj\n".encode() + objs[oid] + b"\nendobj\n"
    xref_pos = len(pdf)
    n = max(objs) + 1
    pdf += f"xref\n0 {n}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for oid in range(1, n):
        if oid in offsets:
            pdf += f"{offsets[oid]:010d} 00000 n \n".encode()
        else:
            pdf += b"0000000000 65535 f \n"
    pdf += (b"trailer\n<< /Size " + str(n).encode()
            + b" /Root 1 0 R >>\nstartxref\n"
            + str(xref_pos).encode() + b"\n%%EOF")
    return pdf


def _parse(tmp_path: Path, extra_keys: bytes, smask_obj: bytes | None):
    p = tmp_path / "m.pdf"
    p.write_bytes(_pdf(extra_keys, smask_obj))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    d = FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p))
    assert len(d.elements) == 1
    assert d.elements[0].type == "image"
    assert d.elements[0].metadata["srcsize"] == [2, 2]
    png = next(img_dir.rglob("*.png"))
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    im = Image.open(io.BytesIO(png.read_bytes()))
    return d, im


def _quads(im):
    return {q: im.getpixel(c) for q, c in
            [("TL", (50, 50)), ("TR", (150, 50)),
             ("BL", (50, 150)), ("BR", (150, 150))]}


def test_soft_mask_honored_flattened(tmp_path):
    """S1：SMask 兑现——TL 黑、其余白（alpha 摊平底色）、PNG
    mode RGB（非 RGBA）、SMask 子图不成元素、零告警。"""
    d, im = _parse(tmp_path, b"/SMask 7 0 R", _SMASK)
    assert im.mode == "RGB"
    q = _quads(im)
    assert q["TL"] == _BLACK
    assert q["TR"] == q["BL"] == q["BR"] == _WHITE
    assert d.warnings == []


def test_colorkey_mask_removes_black(tmp_path):
    """S2：/Mask [0 64]³ 色键 + 全黑源 → 四象限全白、零告警。"""
    d, im = _parse(tmp_path, b"/Mask [0 64 0 64 0 64]", None)
    assert all(v == _WHITE for v in _quads(im).values())
    assert d.warnings == []


def test_dangling_smask_ignored_base_renders(tmp_path):
    """S3：/SMask 99 0 R 悬空 → 蒙版当不存在，四象限全黑、
    元素照发、零告警（对照 R1939 悬空放置静默跳过）。"""
    d, im = _parse(tmp_path, b"/SMask 99 0 R", None)
    assert all(v == _BLACK for v in _quads(im).values())
    assert d.warnings == []
