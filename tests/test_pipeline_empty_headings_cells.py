r"""pipeline 空标题丢弃与空单元格保留
（Round 1684）。

新角度：R1683 锁围栏闭合/引号——**空与
纯空白 h2 丢弃、td 空值保留为空格格**零
覆盖：

- **'&lt;h2&gt;&lt;/h2&gt;'**：空标题丢
  弃，后续段落照常
- **'&lt;h2&gt;   &lt;/h2&gt;'**：纯空白
  同样丢弃
- **空 td**：'|  | x |' 空格占位，
  col_count 2
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_empty_heading_dropped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h2></h2><p>x</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]


def test_ws_heading_dropped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h2>   </h2><p>x</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "x")]


def test_empty_cell_placeholder(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td></td><td>x</td></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  | x |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "html_table"})]
