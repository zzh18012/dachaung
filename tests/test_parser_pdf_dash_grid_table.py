r"""PDF 虚线/点线完整网格照样成表（Round 1952，a 优先级）。

edges104 锁实线完整网格成表；R1584 锁虚线矩形（孤立、无相
交）不成表；R1951 锁单方向/不相交线不成表。探针 R1952 实
证——**dash 图案不影响成表**（pdfminer paint_path 只读路径
几何，不看 dash 状态；三形态全成表且 md 与实线版一致）：

- **D1 虚线网格**：`[5 3] 0 d` 作用于全网格 → '| AA | BB
  |  |'、row 1 / col 3、零告警
- **P1 点线网格**：`[1 1] 0 d`（极端短 dash）→ 同 D1
- **M1 混合**：横线实线、竖线才设 dash → 同 D1（dash 是
  流内状态，只影响后续 stroke）

判别式：结构判据是**相交几何**而非外观——R1951 缺一条相
交线整表消失 vs 本轮 dash 全开表照成。若未来 find_tables
引入实线过滤则三断言齐翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 400.0, 550.0]


def _content(mode: str) -> bytes:
    parts = ["1 w 0 0 0 RG"]
    dash = {"D": "[5 3] 0 d", "P": "[1 1] 0 d"}.get(mode, "")
    if dash:
        parts.append(dash)
    if mode == "M":
        for y in (700.0, 620.0):
            parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
        parts.append("[5 3] 0 d")
        for x in _XS:
            parts.append(f"{x:.1f} 620.0 m {x:.1f} 700.0 l S")
    else:
        for y in (700.0, 620.0):
            parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
        for x in _XS:
            parts.append(f"{x:.1f} 620.0 m {x:.1f} 700.0 l S")
    for x, y, t in [(120.0, 660.0, "AA"), (270.0, 660.0, "BB")]:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({t}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _assert_table(tmp_path: Path, mode: str):
    p = tmp_path / "g.pdf"
    p.write_bytes(_pdf([_content(mode)]))
    d = FallbackParser().parse(p, compute_file_hash(p))
    assert [e.type for e in d.elements] == ["heading", "table"]
    tbl = d.elements[1]
    assert tbl.content == "| AA | BB |  |\n| --- | --- | --- |"
    assert tbl.metadata["row_count"] == 1
    assert tbl.metadata["col_count"] == 3
    assert d.warnings == []


def test_dashed_grid_forms_table(tmp_path):
    """D1：[5 3] 虚线全网格 → 与实线网格同表。"""
    _assert_table(tmp_path, "D")


def test_dotted_grid_forms_table(tmp_path):
    """P1：[1 1] 点线（极端短 dash）→ 同 D1 成表。"""
    _assert_table(tmp_path, "P")


def test_mixed_solid_and_dashed(tmp_path):
    """M1：横实竖虚 → 同 D1（dash 是流内状态只影响后续）。"""
    _assert_table(tmp_path, "M")
