r"""PDF 同基线混排字号——3pt 行容差边界与词序重排（Round 1956，a 优先级）。

`_group_words_to_paragraphs` 行聚类条件 `abs(yc - current_y)
<= 3.0`（fallback_parser.py:129）；字号不参与分类（short_line
纯文本启发式）——**同基线混排字号**广扫（混排字号/Tf.*Tf/
mixed size 各形）实证零覆盖。探针 R1956 实证：

- **M1 12+24 同基线**：y 中心差 ~5.5 > 3 → **拆两行**，大字
  行先（中心更靠上）→ 段内合并后 'BB AA'——**视觉序 'AA
  BB' 被重排**（bbox 含两词并集）
- **M2 12+18 同基线**：差 ~2.8 ≤ 3 → 同行 → x 序 'AA BB'
  （容差内不重排）——与 M1 的判别面恰在字号比
- **M3 drop-cap**：36pt 'D' + 12pt 'rop'/'tail' → 'D rop
  tail'——**词被字号边界劈开**（视觉 'Drop tail'）

判别式：若行容差改基线对齐（同 baseline 即同行）则 M1/M3
翻红；若容差收窄则 M2 翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_T = "BT /F1 {size} Tf {x} 700 Td ({t}) Tj ET"


def _parse(tmp_path: Path, specs: list[tuple[int, float, str]]):
    p = tmp_path / "m.pdf"
    p.write_bytes(_pdf(["\n".join(
        _T.format(size=s, x=x, t=t) for s, x, t in specs
    ).encode("latin-1")]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_12_24_same_baseline_reorders(tmp_path):
    """M1：12+24 同基线 → 拆行重排 'BB AA'（大字行先）。"""
    d = _parse(tmp_path, [(12, 100.0, "AA"), (24, 200.0, "BB")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "BB AA"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 72.968, 232.016, 96.968], abs=0.01)
    assert d.warnings == []


def test_12_18_same_baseline_keeps_x_order(tmp_path):
    """M2：12+18 同基线 → 容差内同行 'AA BB'（x 序保留）。"""
    d = _parse(tmp_path, [(12, 100.0, "AA"), (18, 200.0, "BB")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "AA BB"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 77.726, 224.012, 95.726], abs=0.01)
    assert d.warnings == []


def test_drop_cap_splits_word(tmp_path):
    """M3：36pt 首字母 + 12pt 续文 → 'D rop tail' 词被劈开。"""
    d = _parse(tmp_path, [(36, 100.0, "D"),
                          (12, 130.0, "rop"),
                          (12, 200.0, "tail")])
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "D rop tail"
    assert d.warnings == []
