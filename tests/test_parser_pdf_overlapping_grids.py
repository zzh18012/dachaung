r"""PDF 重叠网格的表检测——错位合并 vs 嵌套分立（Round 1955，a 优先级）。

edges104 锁单网格成表；R1951/1952 锁半边框不成表/dash 照
成表。**两个网格交叠**（分层表单/坏转换常见）广扫（overlap/
交叠/重叠 grid 各形）实证零覆盖。探针 R1955 实证：

- **O1 x 错位 30 合并**：两网格同 y、x 平移 → 竖线并集入同
  一 edge 池 → **一张 5 列怪表**；文本 'AA' 跨 100/130 竖
  线被**劈成 A|A 两 cell**（bbox 并集 [100,92,430,172]）
- **O2 x+y 十字交叠合并**：一张 3 行 × 4 列表，'AA' 完整落
  (1,1)（bbox y 并集 92-202）
- **O3 嵌套分立**：小网格整个在大网格单 cell 内 → **两张
  独立表**（外 1×3 含 AA、内 1×2 空），元素序 heading、
  外表、内表

判别式：词相位 heading 三形态均完整 'AA'（双重提取不劈字，
与 O1 表内 A|A 成对照）；若 find_tables 引入重叠分离/去重
则 O1/O2 列数与 O3 表数翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf


def grid(x0: float, x1: float, y0: float, y1: float,
         nx: int = 2) -> list[str]:
    parts = []
    xs = [x0 + (x1 - x0) * i / nx for i in range(nx + 1)]
    for y in (y1, y0):
        parts.append(f"{x0:.1f} {y:.1f} m {x1:.1f} {y:.1f} l S")
    for x in xs:
        parts.append(f"{x:.1f} {y0:.1f} m {x:.1f} {y1:.1f} l S")
    return parts


def _parse(tmp_path: Path, parts: list[str]):
    p = tmp_path / "o.pdf"
    p.write_bytes(_pdf(["\n".join(
        ["1 w 0 0 0 RG"] + parts
        + ["BT /F1 12 Tf 120 660 Td (AA) Tj ET"]).encode("latin-1")]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_x_shift_grids_merge_one_table(tmp_path):
    """O1：x 平移 30 交叠 → 一张 5 列表、'AA' 劈成 A|A。"""
    d = _parse(tmp_path, grid(100.0, 400.0, 620.0, 700.0)
               + grid(130.0, 430.0, 620.0, 700.0))
    assert [e.type for e in d.elements] == ["heading", "table"]
    assert d.elements[0].content == "AA"
    tbl = d.elements[1]
    assert tbl.content == "| A | A |  |  |  |\n| --- | --- | --- | --- | --- |"
    assert tbl.metadata["row_count"] == 1
    assert tbl.metadata["col_count"] == 5
    assert tbl.source_locator["bbox"] == [100.0, 92.0, 430.0, 172.0]
    assert d.warnings == []


def test_crosshatch_grids_merge(tmp_path):
    """O2：x+y 双错位十字交叠 → 一张 3×4 表、AA 完整在 (1,1)。"""
    d = _parse(tmp_path, grid(100.0, 400.0, 620.0, 700.0)
               + grid(160.0, 460.0, 590.0, 670.0))
    assert [e.type for e in d.elements] == ["heading", "table"]
    tbl = d.elements[1]
    assert tbl.content == ("| AA |  |  |  |\n| --- | --- | --- | --- |\n"
                           "|  |  |  |  |\n|  |  |  |  |")
    assert tbl.metadata["row_count"] == 3
    assert tbl.metadata["col_count"] == 4
    assert tbl.source_locator["bbox"] == [100.0, 92.0, 400.0, 202.0]
    assert d.warnings == []


def test_nested_grids_two_tables(tmp_path):
    """O3：小网格在大网格 cell 内 → 两张独立表（外 1×3、内 1×2）。"""
    d = _parse(tmp_path, grid(100.0, 550.0, 620.0, 700.0, nx=3)
               + grid(150.0, 250.0, 640.0, 680.0))
    assert [e.type for e in d.elements] == ["heading", "table", "table"]
    outer, inner = d.elements[1], d.elements[2]
    assert outer.content == "| AA |  |  |\n| --- | --- | --- |"
    assert outer.source_locator["bbox"] == [100.0, 92.0, 550.0, 172.0]
    assert inner.content == "|  |  |\n| --- | --- |"
    assert inner.metadata["row_count"] == 1
    assert inner.metadata["col_count"] == 2
    assert inner.source_locator["bbox"] == [150.0, 112.0, 250.0, 152.0]
    assert d.warnings == []
