r"""PDF 未测压缩编码三形态静默成功锁定（Round 1945，a 优先级）。

edges91 锁 DCTDecode 垃圾（元素照发零告警）；R1582 锁 DCTDecode
真图/CMYK/Decode 反相；R1941 锁退化源（零像素/截断/缺 CS）。
**JPXDecode / CCITTFaxDecode / LZWDecode 零覆盖**（grep 实证，
含 /DecodeParms 形态）。探针 R1945 实证——三形态同归**静默成
功**（pdfium 渲染放置区域、从不解码源数据，R1941 语义跨编码
成立）：

- **J1 JPXDecode 垃圾流**：16 字节 \xdeadbeef×4 + 声明 2x2
  RGB → image 元素、srcsize [2,2]、真 PNG
- **J2 CCITTFaxDecode G4 垃圾**：/DecodeParms /Columns 2
  /Rows 2 /K -1 + 8 字节噪声 → 同上
- **J3 LZWDecode 垃圾**：8 字节递减序列 → 同上

判别式：若任一编码引入源数据解码/校验则对应测试零告警断言
翻红；若渲染改读源像素则 PNG 尺寸断言翻红（放置 100pt@144dpi
= 200x200，与 2x2 源阵不符）。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import tests.test_parser_pdf_image_numbering as numbering
from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_JPX = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
        b"/Filter /JPXDecode /Length 16 >>\nstream\n"
        + b"\xde\xad\xbe\xef" * 4 + b"\nendstream")
_CCITT = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
          b"/ColorSpace /DeviceGray /BitsPerComponent 1 "
          b"/Filter /CCITTFaxDecode /DecodeParms "
          b"<< /Columns 2 /Rows 2 /K -1 >> /Length 8 >>\nstream\n"
          + b"\x00\xff\x55\xaa" * 2 + b"\nendstream")
_LZW = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
        b"/Filter /LZWDecode /Length 8 >>\nstream\n"
        + b"\x80\x40\x20\x10\x08\x04\x02\x01" + b"\nendstream")


def _parse(tmp_path: Path, monkeypatch, img: bytes):
    monkeypatch.setattr(numbering, "_IMG", img)
    p = tmp_path / "c.pdf"
    p.write_bytes(numbering._pdf(
        [b"q 100 0 0 100 450 600 cm /Im1 Do Q"]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    return FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p)), img_dir


def _assert_silent_success(d, img_dir):
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.metadata["srcsize"] == [2, 2]
    assert e.metadata["extracted_to_disk"] is True
    png = next(img_dir.rglob("*.png"))
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert Image.open(png).size == (200, 200)
    assert d.warnings == []


def test_jpxdecode_garbage_succeeds(tmp_path, monkeypatch):
    """J1：JPXDecode 垃圾流 → 元素照发、真 PNG 200x200、零告警。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _JPX)
    _assert_silent_success(d, img_dir)


def test_ccittfax_garbage_succeeds(tmp_path, monkeypatch):
    """J2：CCITTFax G4（/DecodeParms /K -1）垃圾 → 同 J1 静默成功。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _CCITT)
    _assert_silent_success(d, img_dir)


def test_lzwdecode_garbage_succeeds(tmp_path, monkeypatch):
    """J3：LZWDecode 垃圾 → 同 J1 静默成功。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _LZW)
    _assert_silent_success(d, img_dir)
