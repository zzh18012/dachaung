"""PDF pdfplumber 分词 x/y_tolerance=3 精确边界（Round 2012，a 优先级）。

utils/text.py _is_new_word 实读：新词判据
`(cx < ax) or (cx > bx + x) or abs(cy - ay) > y`，x/y 默认 3
（DEFAULT_X_TOLERANCE=3，utils/text.py:27）。intra 行距从**前一
字符 x1 到当前 x0** 量，严格 >（==3.0 仍同词）。flip_mirror 只
定性说过 "间距 > x_tolerance → 逐字成词"，精确边界与字符级
inter 行破词零覆盖（grep 实证）。fallback _lines_to_para 词间/
行间都用单空格 join。探针 R2012 实证（单内容流两 BT 块）：

- **T1 gap 恰 3.0**（B x0=111.004 = A x1+3.0）→ 同词 'AB'
  bbox [100,82.484,119.008,94.484]（浮点 111.004-108.004
  实算 ≤3）
- **T2 gap 3.1** → 裂词 'A B' 单元素，bbox 拓宽 x1=119.108
- **T3 gap 2.9** → 同词 'AB' x1=118.908
- **T4 同列 top 差 3.5** → 字符级破词 + 行聚类裂行 → 单元素
  **'B A'（高位 B 在前**——行按 y_center 升序，与 R1920
  页内自下而上同向）；bbox top=B 的 78.984、bottom=A 的
  94.484（跨 14.5 高）
- **T5 同列 top 差 2.5** → 同词 'AB'（|Δtop|≤3 容忍），
  bbox 高 14.5 [79.984, 94.484]

判别式：T1/T3 若 'A B' 翻；T2 若 'AB' 翻；T4 若 'AB' 或
'A B' 顺序翻；T5 若裂词翻。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def _parse(second: bytes):
    content = b"BT /F1 12 Tf 100 700 Td (A) Tj ET\n" + second
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.pdf"
        p.write_bytes(_pdf([content]))
        return FallbackParser().parse(p, compute_file_hash(p))


def _one(d, text: str):
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == text
    assert d.warnings == []
    return d.elements[0].source_locator["bbox"]


def test_gap_exactly_3_joins():
    """T1：gap 恰 3.0 → 同词 'AB'。"""
    bbox = _one(_parse(b"BT /F1 12 Tf 111.004 700 Td (B) Tj ET"), "AB")
    assert bbox == pytest.approx([100.0, 82.484, 119.008, 94.484], abs=0.01)


def test_gap_3_1_splits():
    """T2：gap 3.1 → 裂词 'A B' 单元素、bbox 拓宽。"""
    bbox = _one(_parse(b"BT /F1 12 Tf 111.104 700 Td (B) Tj ET"), "A B")
    assert bbox == pytest.approx([100.0, 82.484, 119.108, 94.484], abs=0.01)


def test_gap_2_9_joins():
    """T3：gap 2.9 → 同词 'AB'。"""
    bbox = _one(_parse(b"BT /F1 12 Tf 110.904 700 Td (B) Tj ET"), "AB")
    assert bbox == pytest.approx([100.0, 82.484, 118.908, 94.484], abs=0.01)


def test_topdiff_3_5_breaks_and_reorders():
    """T4：top 差 3.5 → 破词破行，高位 B 在前 'B A'。"""
    bbox = _one(_parse(b"BT /F1 12 Tf 100 703.5 Td (B) Tj ET"), "B A")
    assert bbox == pytest.approx([100.0, 78.984, 108.004, 94.484], abs=0.01)


def test_topdiff_2_5_same_word():
    """T5：top 差 2.5 → 同词 'AB'，跨 14.5 高 bbox。"""
    bbox = _one(_parse(b"BT /F1 12 Tf 100 702.5 Td (B) Tj ET"), "AB")
    assert bbox == pytest.approx([100.0, 79.984, 108.004, 94.484], abs=0.01)
