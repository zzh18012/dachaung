r"""DOCX 表行 gridBefore/gridAfter 列偏移（Round 1967，a 优先级）。

既有表格测试全整齐行/gridSpan/vMerge（广扫 gridBefore/
gridAfter 零匹配）；真实 Word 允许行首/行尾跳过网格列。
探针 R1967 实证（python-docx row.cells 只看 gridSpan，
gridBefore/gridAfter **全忽略**；_rows_to_markdown 右补
齐）：

- **G1 gridBefore=1（2 格）在 3 列表**→ '| A | B |  |'——
  **行左移**（A 落 H1 列而非 H2），行尾由右补齐凑 3 列
- **G2 gridAfter=1（2 格）**→ 与 G1 渲染**逐字相同**——尾
  跳列恰被右补齐复原（巧合正确），首跳列信息静默丢失
- **G3 gridBefore=1 + gridSpan=2（单格跨 2）**→ row.cells
  span 复制 → '| SPAN | SPAN |  |'（既有 span 复制行为
  与左移叠加）

判别式：若 python-docx/解析器尊重 gridBefore 则 G1 变
'|  | A | B |' 翻红；G1/G2 恒等锁"首尾偏移不可分辨"。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser

_N = nsdecls("w")


def _tc(text: str, span: int = 1) -> str:
    tcpr = '<w:tcPr><w:tcW w:w="2000" w:type="dxa"/>'
    if span > 1:
        tcpr += f'<w:gridSpan w:val="{span}"/>'
    tcpr += "</w:tcPr>"
    return (f"<w:tc {_N}>{tcpr}<w:p {_N}><w:r><w:t>{text}"
            f"</w:t></w:r></w:p></w:tc>")


def _tr(cells: str, before: int = 0, after: int = 0) -> str:
    trpr = "<w:trPr>"
    if before:
        trpr += f'<w:gridBefore w:val="{before}"/>'
    if after:
        trpr += f'<w:gridAfter w:val="{after}"/>'
    trpr += "</w:trPr>"
    return f"<w:tr {_N}>{trpr}{cells}</w:tr>"


def _parse(rows_xml: list[str]):
    d = Document()
    t = d.add_table(rows=1, cols=3)
    for i, h in enumerate(("H1", "H2", "H3")):
        t.rows[0].cells[i].text = h
    for r in rows_xml:
        t._tbl.append(parse_xml(r))
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "g.docx"
        d.save(p)
        return FallbackParser().parse(p, compute_file_hash(p))


def test_grid_before_row_left_shifted():
    """G1：gridBefore=1（A|B 两格）→ '| A | B |  |'——A 落
    H1 列、行尾右补齐、零告警。"""
    d = _parse([_tr(_tc("A") + _tc("B"), before=1)])
    assert [e.type for e in d.elements] == ["table"]
    assert d.elements[0].content == "| H1 | H2 | H3 |\n| --- | --- | --- |\n| A | B |  |"
    assert d.elements[0].metadata == {
        "row_count": 2, "col_count": 3, "source": "python-docx"}
    assert d.warnings == []


def test_grid_after_row_renders_identical_to_before():
    """G2：gridAfter=1 → 与 G1 渲染逐字相同——尾跳列被右补
    齐复原（巧合正确）、首跳列丢失。"""
    d1 = _parse([_tr(_tc("A") + _tc("B"), before=1)])
    d2 = _parse([_tr(_tc("A") + _tc("B"), after=1)])
    assert d1.elements[0].content == d2.elements[0].content
    assert d2.elements[0].content.endswith("| A | B |  |")
    assert d2.warnings == []


def test_grid_before_with_span_duplicates_and_shifts():
    """G3：gridBefore=1 + gridSpan=2 单格 → span 复制 + 左移
    → '| SPAN | SPAN |  |'。"""
    d = _parse([_tr(_tc("SPAN", span=2), before=1)])
    assert d.elements[0].content == (
        "| H1 | H2 | H3 |\n| --- | --- | --- |\n| SPAN | SPAN |  |")
    assert d.warnings == []
