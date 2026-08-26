r"""pipeline 标题-表-标题流与 li 内表格成兄弟
（Round 1667）。

新角度：R1666 锁紧贴块——**三明治分块流、
li 内表格抽出为兄弟元素（list_item 保留）**
零覆盖：

- **'# A' 表 '# B'**：三 chunk 各自独立
  （sequential / isolated_table /
  sequential）
- **li 内 table**：list_item 保留文本，
  table 作为兄弟元素就地展开（与 R1647
  img-in-li 破坏 list_item 不同型）
- **元素顺序**：前后 list_item 不受影响，
  table 落在原位置
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_heading_table_heading_flow(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "# A\n| a | b |\n| --- | --- |\n# B\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("A", 1, "sequential"),
        ("| a | b |\n| --- | --- |", 1,
         "isolated_table"),
        ("B", 1, "sequential")]


def test_table_in_li_sibling(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<ul><li>text<table><tr><td>x</td></tr>"
        "</table></li></ul>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "text",
         {"ordered": False, "marker": "unordered"}),
        ("table", "| x |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_table_in_li_order_preserved(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<ul><li>one</li><li>two<table>"
        "<tr><td>x</td></tr></table></li>"
        "<li>three</li></ul>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "one"),
        ("list_item", "two"),
        ("table", "| x |\n| --- |"),
        ("list_item", "three")]
