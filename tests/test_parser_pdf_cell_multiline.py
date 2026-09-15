r"""PDF 网格表多行（换行包裹）cell——md 内嵌 \\n + 词相位跨 cell 交错（Round 1950，a 优先级）。

广扫实证 PDF 表格测试 cell 全部单行文本（edges38/67 的
multiline 是 DOCX sdt/ins 家族；R1949 锁 DOCX 版）。探针
R1950 实证（一行网格 + col1 两/三行文本、col2 单行）：

- **P1 md 内嵌 '\\n'**：col1 两行 'AA1'/'AA2' → 表格
  '| AA1\\nAA2 | BB |  |'（pdfplumber extract() 同 cell 多
  行以 '\\n' 合并；与 R1949 DOCX c.text 形态一致）
- **词相位跨 cell 交错**：双重提取（R1888/R1922 家族）下
  按视觉行排——'AA1 BB AA2'（cell1 行1 + cell2 + cell1
  行2 交错）；行距 30pt、12pt 字 → gap 18 = 1.5×12 恰等值
  不拆段（R1903 严格 >），单 heading 元素
- **P2 三行 cell**：'| A\\nB\\nC | BB |  |'、词相位
  'A BB B C'

判别式：若 extract 改空格合并则 P1/P2 md 全等翻红；若词相
位跳过表区文本则交错 heading 断言翻红。
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser
from tests.test_parser_pdf_image_numbering import _pdf

_XS = [100.0, 250.0, 400.0, 550.0]


def _content(lines_col1: list[tuple[float, str]]) -> bytes:
    parts = ["1 w 0 0 0 RG"]
    for y in (700.0, 620.0):
        parts.append(f"{_XS[0]} {y:.1f} m {_XS[-1]} {y:.1f} l S")
    for x in _XS:
        parts.append(f"{x:.1f} 620.0 m {x:.1f} 700.0 l S")
    for y, text in lines_col1:
        parts.append(f"BT /F1 12 Tf 120.0 {y:.1f} Td ({text}) Tj ET")
    parts.append("BT /F1 12 Tf 270.0 660.0 Td (BB) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _parse(tmp_path: Path, lines_col1):
    p = tmp_path / "w.pdf"
    p.write_bytes(_pdf([_content(lines_col1)]))
    return FallbackParser().parse(p, compute_file_hash(p))


def test_two_line_cell_newline_in_md(tmp_path):
    """P1：col1 两行 → '| AA1\\nAA2 | BB |  |'、row/col 计数。"""
    d = _parse(tmp_path, [(675.0, "AA1"), (645.0, "AA2")])
    tbl = d.elements[1]
    assert tbl.type == "table"
    assert tbl.content == "| AA1\nAA2 | BB |  |\n| --- | --- | --- |"
    assert tbl.metadata["row_count"] == 1
    assert tbl.metadata["col_count"] == 3
    assert d.warnings == []


def test_word_phase_interleaves_cells_by_line(tmp_path):
    """词相位双重提取：视觉行序 'AA1 BB AA2' 单 heading
    （行 gap 18 = 1.5×12 恰等值不拆段）。"""
    d = _parse(tmp_path, [(675.0, "AA1"), (645.0, "AA2")])
    assert [e.type for e in d.elements] == ["heading", "table"]
    assert d.elements[0].content == "AA1 BB AA2"
    assert d.warnings == []


def test_three_line_cell(tmp_path):
    """P2：三行 cell '| A\\nB\\nC | BB |  |'、词相位 'A BB B C'。"""
    d = _parse(tmp_path, [(675.0, "A"), (655.0, "B"), (635.0, "C")])
    tbl = d.elements[1]
    assert tbl.content == "| A\nB\nC | BB |  |\n| --- | --- | --- |"
    assert d.elements[0].content == "A BB B C"
    assert d.warnings == []
