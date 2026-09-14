r"""html 容器级 loose 文本不对称：列表放行成段、表格吞噬（Round 1850）。

新角度（probe 实证，grep 核实零覆盖——edges14 孤儿 li 是无容器裸
li，edges12 caption 被吞是 `<caption>` 标签；**容器内裸文本**无覆盖）：
- **列表容器放行**：`<ul>stray<li>a</li></ul>` → loose 'stray' 成
  paragraph + list_item 'a'（ol 同规，ordered 标记不受影响）
- **表格容器吞噬**：`<table>loose<tr>…` 行前 loose 与
  `<td>a</td>gap<td>b</td>` 单元格间 loose 均**静默消失**——无
  paragraph、无 warning，单元格照常合并成行
- **无 li 的列表容器**：`<ul>stray</ul>` → 仅一个 paragraph，零
  list 元素（容器本身不产出）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.html_parser import HtmlParser


def _parse(tmp_path: Path, text: str):
    p = tmp_path / "a.html"
    p.write_text(text, encoding="utf-8", newline="")
    return HtmlParser().parse(p, compute_file_hash(p))


def test_loose_text_in_list_becomes_paragraph(tmp_path: Path):
    doc = _parse(tmp_path, "<ul>stray<li>a</li></ul>")
    assert len(doc.elements) == 2
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == "stray"
    item = doc.elements[1]
    assert item.type == "list_item"
    assert item.content == "a"
    assert item.metadata == {"ordered": False, "marker": "unordered"}

    ol = _parse(tmp_path, "<ol>stray<li>a</li></ol>")
    assert [e.type for e in ol.elements] == ["paragraph", "list_item"]
    assert ol.elements[1].metadata == {"ordered": True, "marker": "ordered"}


def test_loose_text_in_table_swallowed(tmp_path: Path):
    before = _parse(tmp_path, "<table>loose text<tr><td>x</td></tr></table>")
    assert len(before.elements) == 1
    assert before.elements[0].type == "table"
    assert before.elements[0].content == "| x |\n| --- |"
    assert before.elements[0].metadata == {
        "row_count": 1, "col_count": 1, "source": "html_table"}
    assert before.warnings == []

    between = _parse(tmp_path,
                     "<table><tr><td>a</td>gap<td>b</td></tr></table>")
    assert len(between.elements) == 1
    assert between.elements[0].content == "| a | b |\n| --- | --- |"
    assert between.elements[0].metadata["col_count"] == 2
    assert between.warnings == []


def test_stray_only_list_container(tmp_path: Path):
    doc = _parse(tmp_path, "<ul>stray</ul><p>after</p>")
    assert [e.type for e in doc.elements] == ["paragraph", "paragraph"]
    assert doc.elements[0].content == "stray"
    assert doc.elements[1].content == "after"
