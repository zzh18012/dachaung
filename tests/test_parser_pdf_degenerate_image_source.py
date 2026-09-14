r"""PDF 退化图像源三形态静默成功锁定（Round 1941，a 优先级）。

R1896 锁零宽**放置**（cm 矩阵退化 → 静默跳过）；R1936 锁
/ImageMask/镜像/旋转矩阵。**退化源图**（零像素 / 数据截断 /
缺 /ColorSpace）零覆盖。探针 R1941 实证——三形态同归**静默
成功**（与退化放置相反：元素照发、PNG 照渲染落盘、零告警）：

- **Z1 零像素源**：/Width 0 /Height 0 + 正常 cm 放置 →
  image 元素、srcsize [0,0]、真 PNG 渲染落盘
- **Z2 截断数据**：声明 2x2 RGB（需 12 字节）但 /Length 1 →
  照发元素、srcsize [2,2]（pdfium 渲染放置区域、从不解码
  源数据）
- **Z3 缺 /ColorSpace**：非模板图缺 CS（R1936 X3 的模板合法
  缺 CS 形态之外）→ 照发元素、PNG 真渲染

判别式：若零像素源被跳过或告警则 Z1 元素数/零告警断言翻红；
若数据长度校验加严则 Z2 翻红；若缺 CS 致崩溃/告警则 Z3 翻红；
PNG 头断言区分真渲染与 "(unrendered)" 占位。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_parser_pdf_image_numbering as numbering
from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_ZERO = (b"<< /Type /XObject /Subtype /Image /Width 0 /Height 0 "
         b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 0 >>\n"
         b"stream\n\nendstream")
_TRUNC = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
          b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 1 >>\n"
          b"stream\n\xff\nendstream")
_NOCS = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
         b"/BitsPerComponent 8 /Length 12 >>\nstream\n"
         + b"\x00" * 12 + b"\nendstream")


def _parse(tmp_path: Path, monkeypatch, img: bytes):
    monkeypatch.setattr(numbering, "_IMG", img)
    p = tmp_path / "z.pdf"
    p.write_bytes(numbering._pdf(
        [b"q 100 0 0 100 450 600 cm /Im1 Do Q"]))
    img_dir = tmp_path / "imgs"
    img_dir.mkdir()
    return FallbackParser(image_output_dir=str(img_dir)).parse(
        p, compute_file_hash(p)), img_dir


def test_zero_pixel_source_succeeds(tmp_path, monkeypatch):
    """Z1：/Width 0 /Height 0 → 元素照发、srcsize [0,0]、
    真 PNG 渲染、零告警。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _ZERO)
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.metadata["srcsize"] == [0, 0]
    assert e.metadata["extracted_to_disk"] is True
    png = next(img_dir.rglob("*.png"))
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert d.warnings == []


def test_truncated_stream_data_succeeds(tmp_path, monkeypatch):
    """Z2：声明 2x2 RGB 但数据仅 1 字节 → 照发元素、srcsize
    [2,2]、零告警（渲染从不解码源数据）。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _TRUNC)
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.metadata["srcsize"] == [2, 2]
    assert e.metadata["extracted_to_disk"] is True
    assert next(img_dir.rglob("*.png")).read_bytes()[:4] == b"\x89PNG"
    assert d.warnings == []


def test_missing_colorspace_succeeds(tmp_path, monkeypatch):
    """Z3：非模板图缺 /ColorSpace → 照发元素、真 PNG、
    零告警（对照 R1936 X3 模板合法缺 CS）。"""
    d, img_dir = _parse(tmp_path, monkeypatch, _NOCS)
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.metadata["srcsize"] == [2, 2]
    assert e.metadata["extracted_to_disk"] is True
    assert next(img_dir.rglob("*.png")).read_bytes()[:4] == b"\x89PNG"
    assert d.warnings == []
