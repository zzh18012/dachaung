r"""PDF 非规范 cm 矩阵与 /ImageMask 图像锁定（Round 1936，a 优先级）。

R1896 锁零宽（x1==x0）静默跳过；**镜像（负宽）/旋转 cm/
1-bit 模板（/ImageMask）**零覆盖。探针 R1936 实证（pdfplumber
对 cm 矩阵取 min/max 归一 bbox，负宽不产生 x1<x0）：

- **X1 镜像负宽保留**：`-100 0 0 100 550 600 cm` → image 元素
  正常保留、bbox 与轴对齐基线**全等** [450, 92, 550, 192]、渲染
  落盘、零告警——不落入 R1896 退化跳过（宽 0 才跳、负宽归一）
- **X2 旋转 90° 保留**：`0 100 -100 0 550 600 cm` → 同 bbox
  全等保留（旋转不退化）
- **X3 /ImageMask 模板图**：1-bit 模板（无 ColorSpace、带
  /Decode）→ image 元素、srcsize [2,2]、渲染落盘、零告警
  （水印/图章扫描形态）

判别式：若改用矩阵原始跨度判退化（负宽→x1<x0 跳过）则 X1
元素数断言翻红；若 ImageMask 被排除在 image 对象外则 X3 翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_parser_pdf_image_numbering as numbering
from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_MASK_IMG = (b"<< /Type /XObject /Subtype /Image /ImageMask true "
             b"/Width 2 /Height 2 /BitsPerComponent 1 /Length 1 "
             b"/Decode [0 1] >>\nstream\n\xa0\nendstream")


def _parse(tmp_path: Path, content: bytes, patch_img=None):
    if patch_img is not None:
        numbering._IMG = patch_img
    try:
        p = tmp_path / "im.pdf"
        p.write_bytes(numbering._pdf([content]))
        img_dir = tmp_path / "imgs"
        img_dir.mkdir(exist_ok=True)
        return FallbackParser(image_output_dir=str(img_dir)).parse(
            p, compute_file_hash(p))
    finally:
        if patch_img is not None:
            numbering._IMG = _ORIG_IMG


_ORIG_IMG = numbering._IMG


def test_mirrored_negative_width_kept(tmp_path):
    """X1：负宽镜像 cm → image 保留，bbox 与基线全等
    [450, 92, 550, 192]（归一，非 x1<x0 跳过）。"""
    d = _parse(tmp_path, b"q -100 0 0 100 550 600 cm /Im1 Do Q")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.source_locator["bbox"] == [450.0, 92.0, 550.0, 192.0]
    assert e.metadata["extracted_to_disk"] is True
    assert d.warnings == []


def test_rotated_matrix_kept(tmp_path):
    """X2：旋转 90° cm（0 100 -100 0）→ 同 bbox 全等保留、
    渲染落盘、零告警。"""
    d = _parse(tmp_path, b"q 0 100 -100 0 550 600 cm /Im1 Do Q")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.source_locator["bbox"] == [450.0, 92.0, 550.0, 192.0]
    assert e.metadata["extracted_to_disk"] is True
    assert d.warnings == []


def test_image_mask_stencil_extracted(tmp_path):
    """X3：/ImageMask true 1-bit 模板（无 ColorSpace、带 /Decode）
    → image 元素、srcsize [2,2]、渲染落盘、零告警。"""
    d = _parse(tmp_path, b"q 100 0 0 100 450 600 cm /Im1 Do Q",
               patch_img=_MASK_IMG)
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "image"
    assert e.metadata["srcsize"] == [2, 2]
    assert e.metadata["extracted_to_disk"] is True
    assert d.warnings == []
