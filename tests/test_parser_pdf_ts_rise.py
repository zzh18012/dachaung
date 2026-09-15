r"""PDF Ts 文字升起——上标/下标的行聚类归属（Round 1958，a 优先级）。

行聚类容差 `abs(yc - current_y) <= 3.0`（R1956 锁字号轴；
本轮锁 **Ts 升起轴**——上标/下标真实形态，广扫 Ts/Tz/上标/
下标 各形实证零覆盖）。探针 R1958 实证：

- **S1 上标 8pt+6Ts**：中心 ≈ 基线+2 vs 基词中心 ≈ 基线-6
  → 差 >3 → **拆行重排**（上标行先）'nd x'——视觉 'x^nd'
  被重排为前缀
- **S2 下标 8pt-4Ts**：差 ≤3 → 同行 → x 序 'x nd'
- **S3 Ts 跨 Tj 持续**：6 Ts 后两个 Tj 都升起且 pen 连续
  → 'n'+'d' 合成单词 'nd' → 'nd x'（text state 不因 Tj
  重置；同 R1953 B3 连字家族）

判别式：若行聚类改基线对齐则 S1/S3 翻红；容差收窄则 S2
翻红；Ts 改为每 Tj 重置则 S3 变 'n d x' 翻红。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_BASE = "BT /F1 12 Tf 100 700 Td (x) Tj ET"


def _parse(tmp_path: Path, extra: str):
    p = tmp_path / "s.pdf"
    p.write_bytes(_pdf([(_BASE + "\n" + extra).encode("latin-1")]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_superscript_splits_line_reorders(tmp_path):
    """S1：8pt+6Ts 上标 → 拆行重排 'nd x'（上标行先）。"""
    d = _parse(tmp_path, "BT /F1 8 Tf 6 Ts 130 700 Td (nd) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "nd x"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 79.656, 138.896, 94.484], abs=0.01)
    assert d.warnings == []


def test_subscript_joins_line(tmp_path):
    """S2：8pt-4Ts 下标 → 容差内同行 'x nd'（x 序）。"""
    d = _parse(tmp_path, "BT /F1 8 Tf -4 Ts 130 700 Td (nd) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "x nd"
    assert d.elements[0].source_locator["bbox"] == pytest.approx(
        [100.0, 82.484, 138.896, 97.656], abs=0.01)
    assert d.warnings == []


def test_rise_persists_across_tj(tmp_path):
    """S3：6 Ts 后两 Tj 均升起且 pen 连续 → 'nd x' 单词连写。"""
    d = _parse(tmp_path, "BT /F1 8 Tf 6 Ts 130 700 Td (n) Tj (d) Tj ET")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].content == "nd x"
    assert d.warnings == []
