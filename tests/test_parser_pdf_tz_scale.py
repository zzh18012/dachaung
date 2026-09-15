r"""PDF Tz 横向缩放——宽度缩放不改行聚类、可翻分词（Round 1959，a 优先级）。

Tz 零覆盖（R1958 grep 实证；R1956/R1958 锁字号与 Ts 轴）。
Tz 只缩字宽不改 y → 行聚类与类型判定不变；字宽变化改 x
间隙 → **可翻转 pdfplumber 分词**。探针 R1959 实证：

- **Z1 50 Tz**：'AA BB' 两词不变、AA 宽减半（bbox 至
  258.004——BB@250 宽 ~8）
- **Z2 200 Tz**：'AA BB' 不变、BB 宽 ~32（bbox 至 282.016）
- **Z3 分词翻转**：紧贴对（AA@100、BB@117）控制版 gap~1
  合成**一词 'AABB'**（bbox 至 133.008）；50 Tz 下 AA 宽
  减半 → gap ~9 > 3 → **两词 'AA BB'**（bbox 至 125.004）

判别式：若分词改不考虑 Tz（按字号估宽）则 Z3 两版同形翻
红；若 Tz 误入 y/字号通道则 Z1/Z2 行为变。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_T = "BT /F1 12 Tf {tz} Tz {x} 700 Td ({t}) Tj ET"


def _parse(tmp_path: Path, tz: int, x2: float = 250.0):
    p = tmp_path / "z.pdf"
    p.write_bytes(_pdf([( _T.format(tz=tz, x=100, t="AA") + "\n"
                        + _T.format(tz=tz, x=x2, t="BB")).encode("latin-1")]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_half_scale_keeps_words(tmp_path):
    """Z1：50 Tz → 两词不变、宽度减半。"""
    d = _parse(tmp_path, 50)
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content.split() == ["AA", "BB"]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 258.004, 94.484], abs=0.01)
    assert d.warnings == []


def test_double_scale_widens_bbox(tmp_path):
    """Z2：200 Tz → 两词不变、BB 宽 ~32（bbox 至 282.016）。"""
    d = _parse(tmp_path, 200)
    assert d.elements[0].content.split() == ["AA", "BB"]
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 282.016, 94.484], abs=0.01)
    assert d.warnings == []


def test_tz_flips_word_split(tmp_path):
    """Z3：紧贴对 100 Tz 一词 'AABB'；50 Tz gap 增 → 'AA BB'。"""
    control = _parse(tmp_path, 100, x2=117.0)
    assert control.elements[0].content.split() == ["AABB"]
    assert control.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 133.008, 94.484], abs=0.01)
    squeezed = _parse(tmp_path, 50, x2=117.0)
    assert squeezed.elements[0].content.split() == ["AA", "BB"]
    assert squeezed.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 125.004, 94.484], abs=0.01)
    assert squeezed.warnings == []
