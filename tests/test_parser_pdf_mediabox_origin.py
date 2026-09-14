r"""PDF MediaBox 非零原点——翻转基准取高度差、无平移无裁剪（Round 1943）。

grep 实证 tests/ 全部 277 处 MediaBox 字面量均零原点
（[0 0 ...]）；R1587 锁 CropBox 忽略 / MediaBox 继承也全
零原点。**非零原点**（印刷裁切常见形态 [36 36 612 792]）零
覆盖。探针 R1943 实证：

- **N1 翻转基准 = 高度差**：同一文本 (100,700) 在
  [36 36 612 792] 下 bbox top=46.484 = 756-709.516
  （零原点对照 82.484 = 792-709.516）——pdfplumber 以
  page.height=y1-y0 翻转、**不用 y1=792、不平移原点**
- **N2 低于原点不裁剪**：文本 y=10 < 原点 36 → 照常提
  取、bbox top=736.484（在 [0,756] 顶缘外无影响）、零告警
- **N3 左于原点不裁剪**：文本 x=10 < 36 → bbox x0=10.0
  原样、零告警

判别式：若翻转基准改用 y1 或做原点平移则 N1 bbox 数值断言
翻红；若引入 MediaBox 裁剪则 N2/N3 元素数断言翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_BOX = b"[36 36 612 792]"


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "o.pdf"
    raw = _pdf([content])
    assert b"[0 0 612 792]" in raw
    p.write_bytes(raw.replace(b"[0 0 612 792]", _BOX))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_flip_base_is_height_not_y1(tmp_path):
    """N1：bbox top=46.484=756-709.516（高度差基准），恰比
    零原点对照低 36——非 y1 基准、无原点平移。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 100 700 Td (origin box) Tj ET")
    e = d.elements[0]
    assert e.type == "heading"
    assert e.content == "origin box"
    assert e.source_locator["bbox"] == pytest.approx(
        [100.0, 46.484, 152.02, 58.484])
    assert d.warnings == []


def test_below_origin_text_retained(tmp_path):
    """N2：y=10 < 原点 36 → 照常提取、bbox top≈736.5、零告警
    （无 MediaBox 几何裁剪）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 100 10 Td (below origin) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.content == "below origin"
    top = e.source_locator["bbox"][1]
    assert top == pytest.approx(736.484)
    assert top > 720
    assert d.warnings == []


def test_left_of_origin_text_retained(tmp_path):
    """N3：x=10 < 原点 36 → bbox x0=10.0 原样保留、零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 10 700 Td (left of origin) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.content == "left of origin"
    assert e.source_locator["bbox"][0] == pytest.approx(10.0)
    assert e.source_locator["bbox"][0] < 36
    assert d.warnings == []
