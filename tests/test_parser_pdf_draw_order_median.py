r"""PDF upright 字符绘制流序 vs 位置序 + 段距阈值上中位数（Round 2005，a 优先级）。

两块零覆盖（grep 实证：R1944 锁矩阵反转倒序——镜像/180°；
R1920 锁图片元素流序；R1887 单元级锁跨栏融合但全 12pt 等高；
phase3_order 锁三相位序不涉词内字符序与高度中位数）。
探针 R2005 实证：

- **T1 词内字符序 = 位置序**：同词簇（间距 <3pt）三字符按
  T@120→C@100→A@110 乱序绘制 → 'CAT'（pdfplumber 按位置
  排序组词，流序不参与）
- **T2 词序 = 位置序**：同行 B@200 先画、A@100 后画 → 'A B'
- **T3 行序自上而下**：底行（y=100）先画 → 元素仍 ['upper
  line','lower line']（fallback 按 y_center 重排）
- **T4/T5 上中位数阈值**：fallback_parser.py:139-149
  `1.5*sorted(heights)[len//2]` 偶数个取**大者**非平均——
  12pt+24pt 词 median=24 → 阈值 36（真中位数 18→27）：
  gap=30 合段 'AA BB'，gap=37 拆两段
- **T6/T7 严格 > 边界**：等高 gap 恰 1.5*12=18 → 合段；
  gap=19 → 拆段

判别式：T1 若 'TCA' 翻；T4 若拆段翻（上中位数失效）；T6 若
拆段翻（>= 误植）；T2/T3 流序若胜出翻。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(tmp_path: Path, content: bytes):
    p = tmp_path / "o.pdf"
    p.write_bytes(_pdf([content]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_word_char_order_positional(tmp_path):
    """T1：乱序绘制 T@120,C@100,A@110 → 'CAT'（位置序组词非流序）。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 120 700 Td (T) Tj ET\n"
        b"BT /F1 12 Tf 100 700 Td (C) Tj ET\n"
        b"BT /F1 12 Tf 110 700 Td (A) Tj ET"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "CAT"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 127.332, 94.484], abs=0.01)
    assert d.warnings == []


def test_word_order_positional_despite_draw_order(tmp_path):
    """T2：B@200 先画、A@100 后画 → 'A B'（x0 排序压倒绘制流序）。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 200 700 Td (B) Tj ET\n"
        b"BT /F1 12 Tf 100 700 Td (A) Tj ET"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "A B"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 208.004, 94.484], abs=0.01)
    assert d.warnings == []


def test_line_order_topdown_despite_draw_order(tmp_path):
    """T3：底行（y=100）先画 → 元素仍 ['upper line','lower line']。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 100 100 Td (lower line) Tj ET\n"
        b"BT /F1 12 Tf 100 700 Td (upper line) Tj ET"))
    assert [(e.type, e.content) for e in d.elements] == [
        ("heading", "upper line"), ("heading", "lower line")]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 152.692, 94.484], abs=0.01)
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [100.0, 682.484, 150.676, 694.484], abs=0.01)
    assert d.warnings == []


def test_upper_median_threshold_merges_at_30(tmp_path):
    """T4：12pt+24pt 词上中位数=24 → 阈值 36 → gap=30 合段 'AA BB'。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 100 700 Td (AA) Tj ET\n"
        b"BT /F1 24 Tf 100 648.484 Td (BB) Tj ET"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AA BB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 132.016, 148.484], abs=0.01)
    assert d.warnings == []


def test_upper_median_threshold_splits_at_37(tmp_path):
    """T5：gap=37 > 36（上中位数阈值）→ 拆两段（真中位数 27 早已拆）。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 100 700 Td (AA) Tj ET\n"
        b"BT /F1 24 Tf 100 641.484 Td (BB) Tj ET"))
    assert [(e.type, e.content) for e in d.elements] == [
        ("heading", "AA"), ("heading", "BB")]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 116.008, 94.484], abs=0.01)
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [100.0, 131.484, 132.016, 155.484], abs=0.01)
    assert d.warnings == []


def test_exact_threshold_gap_18_merges(tmp_path):
    """T6：等高 gap 恰 1.5*12=18 → 严格 > 不满足 → 合段 'aa bb'。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 100 700 Td (aa) Tj ET\n"
        b"BT /F1 12 Tf 100 670 Td (bb) Tj ET"))
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "aa bb"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 113.344, 124.484], abs=0.01)
    assert d.warnings == []


def test_gap_19_splits(tmp_path):
    """T7：gap=19 > 18 → 拆两段（与 T6 构成边界两侧）。"""
    d = _parse(tmp_path, (
        b"BT /F1 12 Tf 100 700 Td (aa) Tj ET\n"
        b"BT /F1 12 Tf 100 669 Td (bb) Tj ET"))
    assert [(e.type, e.content) for e in d.elements] == [
        ("heading", "aa"), ("heading", "bb")]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 113.344, 94.484], abs=0.01)
    assert d.elements[1].source_locator["bbox"] == pytest.approx(
        [100.0, 113.484, 113.344, 125.484], abs=0.01)
    assert d.warnings == []
