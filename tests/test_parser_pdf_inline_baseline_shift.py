r"""PDF 行内基线偏移——上标/同基线混号锁定（Round 1937，a 优先级）。

edges44 只锁**整块** Ts 8 的 bbox 平移；**行内混排**（部分
字符升起/缩号）与行聚类容差（:129 abs(y_center 差) <= 3.0）
的交互零覆盖。探针 R1937 实证：

- **B1 行内上标拆行同段融合**："word." 后接 Ts 8 升起的 "1" →
  y_center 差 ~8 > 3 → 拆两行；行距 8 < 1.5×行高 → 同段 →
  单元素 content 恰 **'1 word.'**——上标**先于**宿主词（高行
  在前的阅读序伪影，真实学术 PDF 提取常态）；bbox top 抬升
  82.484 → 74.484
- **B2 8pt 行内同基线融合**：12pt "Big" + 8pt "lit" 同基线 →
  单行融合 'Big lit'（pdfminer bbox 锚定基线，y_center 收敛
  于容差内），x 序保留
- **B3 4pt 行内同基线融合**：12pt + 4pt 同基线 → 同样融合
  'Big tiny'——字号差 3 倍仍不裂行

判别式：若上标行被并入宿主行（容差放宽）则 B1 '1 word.'
全等断言翻红；若同基线混号按字号裂行则 B2/B3 翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "bl.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_inline_superscript_splits_line_same_para(tmp_path):
    """B1：Ts 8 升起的 "1" → 拆行同段 → 单元素 '1 word.'
    （上标先于宿主词），bbox top 抬升至 74.484。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (word.) Tj 8 Ts 30 0 Td (1) Tj ET")
    assert len(d.elements) == 1
    e = d.elements[0]
    assert e.type == "paragraph"
    assert e.content == "1 word."
    assert e.source_locator["bbox"] == pytest.approx(
        [72.0, 74.484, 108.672, 94.484])
    assert d.warnings == []


def test_8pt_inline_same_baseline_fused(tmp_path):
    """B2：12pt "Big" + 8pt "lit" 同基线（Tm 绝对定位）→ 单行
    融合 'Big lit'，x 序保留。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (Big) Tj "
               b"1 0 0 1 102 700 Tm /F1 8 Tf (lit) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "Big lit"
    assert d.warnings == []


def test_4pt_inline_same_baseline_fused(tmp_path):
    """B3：12pt + 4pt（字号差 3 倍）同基线 → 仍单行融合
    'Big tiny'（bbox 锚定基线、中心收敛于容差内）。"""
    d = _parse(tmp_path,
               b"BT /F1 12 Tf 72 700 Td (Big) Tj "
               b"1 0 0 1 102 700 Tm /F1 4 Tf (tiny) Tj ET")
    assert len(d.elements) == 1
    assert d.elements[0].content == "Big tiny"
    assert d.warnings == []
