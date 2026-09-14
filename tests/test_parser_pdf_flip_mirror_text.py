r"""PDF 颠倒（180°）/镜像文本矩阵三形态锁定（Round 1944，a 优先级）。

R1900 锁 90°（0 1 -1 0）倒序；edges107 锁 -90°（0 -1 1 0）。
grep 实证 **180°（-1 0 0 -1）与镜像（-1 0 0 1 / 1 0 0 -1）
零覆盖**。探针 R1944 实证（pdfminer 非 upright 家族三形态）：

- **P1 180° 整串倒序**：`(flip vert)` @ (-1 0 0 -1 300 700) →
  **'trev pilf'**（全串逐字符反转）；bbox 右端锚定 300.0、
  向左延展 [261.3, 300]
- **P2 水平镜像逐字散射倒序**：`(mirror)` @ (-1 0 0 1) →
  字符 x 降序排布、相邻间距 > x_tolerance → 逐字成词
  **'r o r r mi'**（窄字 i+m 间距 <3 仍融合）；零告警
- **P4 垂直镜像前向散射**：`(vmirror)` @ (1 0 0 -1) → x 仍
  升序（bbox 自 300 向右 337.3）、**不倒序**但同样散射
  'v m ir r o r'——倒序由 x 方向决定（P2 对照），非 upright
  本身；零告警

判别式：若 180° 被改判 upright 原序提取则 P1 全等断言翻红；
若非 upright 字符宽度/间距计算变化则 P2/P4 散射模式翻红；
若镜像 x 方向语义变化则 P2 倒序 vs P4 前向对照翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "f.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_180deg_text_whole_string_reversed(tmp_path):
    """P1：180° 矩阵 → 全串逐字符反转 'trev pilf'，bbox 右端
    锚定 300.0 向左延展，零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf -1 0 0 -1 300 700 Tm (flip vert) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.content == "trev pilf"
    bbox = e.source_locator["bbox"]
    assert bbox[2] == pytest.approx(300.0)
    assert bbox[0] == pytest.approx(261.324, abs=0.01)
    assert d.warnings == []


def test_hmirror_scatters_reversed_chars(tmp_path):
    """P2：水平镜像 → 字符 x 降序、逐字成词 'r o r r mi'（i+m
    窄字距 <3 融合），零告警。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf -1 0 0 1 300 700 Tm (mirror) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.content == "r o r r mi"
    assert e.content.split() == ["r", "o", "r", "r", "mi"]
    assert d.warnings == []


def test_vmirror_forward_order_scatter(tmp_path):
    """P4：垂直镜像 → x 升序**不倒序** 'v m ir r o r'、bbox 自
    300 向右延展（对照 P2：倒序由 x 方向决定）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 1 0 0 -1 300 700 Tm (vmirror) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.content == "v m ir r o r"
    bbox = e.source_locator["bbox"]
    assert bbox[0] == pytest.approx(300.0)
    assert bbox[2] == pytest.approx(337.32, abs=0.01)
    assert d.warnings == []
