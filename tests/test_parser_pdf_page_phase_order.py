r"""PDF 页内元素发射顺序锁定（Round 1919，a 优先级）。

探针 R1919 实证（fallback_parser._parse_pdf :260-330 每页三阶段：
words→段落循环先于 find_tables→表格循环先于 images 循环）：

- **相位序压倒几何序**：表格在页首（bbox top≈92）、正文在页底
  （top≈682）→ 元素序 [heading(表内文本), paragraph(正文),
  table]——table 元素**最后**发射，阅读序与几何序倒置；
  表内文本同时双重提取为 heading（R1888 机制）
- **同页双表**：上下两表 + 中部正文 → 全部文本元素先于两个
  table 元素；两 table 之间保持 find_tables 的几何上下序
  （bbox top 小者先）
- **跨页**：页序优先——页 1 的（文本+表格）全部先于页 2 文本，
  页内仍维持相位序

判别式：把 :291 表格循环挪到 :260 段落循环之前，本文件三个测试
全部翻红（现存测试无任何 paragraphs-before-tables 顺序断言，
grep 零覆盖）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.parsers.fallback_parser import _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf

_XS = [100.0, 250.0, 400.0, 550.0]
_LONG = (
    "This body line sits below the table region and is long enough "
    "to classify as a paragraph."
)


def _grid(y_top: float, y_bot: float, cells: list[tuple[float, float, str]]) -> str:
    """2 行带 × 3 列带线框网格（PDF 坐标自下而上）+ 单元格文本。"""
    parts = ["1 w 0 0 0 RG"]
    for y in (y_top, (y_top + y_bot) / 2, y_bot):
        parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    for x in _XS:
        parts.append(f"{x:.1f} {y_bot:.1f} m {x:.1f} {y_top:.1f} l S")
    for x, y, text in cells:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    return "\n".join(parts)


def _text_line(y: float, text: str) -> str:
    return f"BT /F1 12 Tf 72.0 {y:.1f} Td ({text}) Tj ET"


def _parse(contents: list[bytes]):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "doc.pdf"
        p.write_bytes(_build_pdf(contents))
        return _parse_pdf(p, "sha", "doc-x", None)


def test_table_above_text_emits_table_element_last():
    """表在页首、正文在页底 → 类型序 [heading, paragraph, table]：
    table 最后发射，正文段落元素的下标小于 table 元素，且几何
    top 反而更大（阅读序与几何序倒置）。"""
    content = _grid(700.0, 620.0, [
        (120.0, 640.0, "h1"), (270.0, 640.0, "h2"),
        (120.0, 655.0, "a1"), (270.0, 655.0, "a2"),
    ])
    content += "\n" + _text_line(100.0, _LONG)
    elements, warnings = _parse([content.encode("latin-1")])
    assert [e.type for e in elements] == ["heading", "paragraph", "table"]
    assert warnings == []
    body, table = elements[1], elements[2]
    assert body.content is not None and body.content.startswith("This body line")
    assert table.type == "table"
    # 正文在页底（top 大），表格在页首（top 小）——几何倒置
    assert body.source_locator["bbox"][1] > table.source_locator["bbox"][1]
    # 判别式：表格循环若先于段落循环，table 会是第一个元素
    assert elements.index(body) < elements.index(table)


def test_two_tables_all_text_elements_precede_both_tables():
    """上下双表 + 中部正文 → 文本元素（两表表内文本 + 正文）全部
    先于两个 table 元素；两 table 之间保持几何上下序。"""
    content = _grid(700.0, 620.0, [(120.0, 640.0, "A1"), (270.0, 640.0, "A2")])
    content += "\n" + _grid(300.0, 220.0, [(120.0, 240.0, "B1"), (270.0, 240.0, "B2")])
    content += "\n" + _text_line(450.0, _LONG)
    elements, _ = _parse([content.encode("latin-1")])
    types = [e.type for e in elements]
    assert types == ["heading", "paragraph", "heading", "table", "table"]
    first_text = types.index("heading")
    table_a, table_b = elements[3], elements[4]
    # 判别式 1：任一文本元素不得晚于任一 table 元素
    assert all(i < 3 for i, t in enumerate(types) if t != "table")
    # 判别式 2：双表保持几何上下序（上表 top 小）
    assert table_a.source_locator["bbox"][1] < table_b.source_locator["bbox"][1]
    assert "A1" in (table_a.content or "") and "B1" in (table_b.content or "")
    # 中部正文元素也在两表之前
    body_idx = next(i for i, e in enumerate(elements)
                    if e.content and e.content.startswith("This body line"))
    assert body_idx < 3


def test_cross_page_table_before_next_page_text():
    """页 1 表、页 2 正文 → 页序优先：[heading, table, paragraph]，
    页内相位序不变，locator.page 记录各自来源页。"""
    page1 = _grid(700.0, 620.0, [(120.0, 640.0, "C1"), (270.0, 640.0, "C2")])
    page2 = _text_line(700.0, _LONG)
    elements, _ = _parse([page1.encode("latin-1"), page2.encode("latin-1")])
    assert [e.type for e in elements] == ["heading", "table", "paragraph"]
    assert [e.source_locator["page"] for e in elements] == [1, 1, 2]
    body = elements[2]
    assert body.content is not None and body.content.startswith("This body line")
    # 页 2 的正文不得先于页 1 的 table（页序优先）
    assert elements.index(elements[1]) < elements.index(body)
