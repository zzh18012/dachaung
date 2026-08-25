r"""pipeline HTML 块嵌套异常容器（Round 1636）。

新角度：R1635 锁围栏变体——**td 内 h2、li 内
p、非法 p 嵌套 p**零覆盖：

- **td 内 h2 拍平**：标题不成 heading，作为
  单元格文本进表 '| H |\\n| --- |'
- **li 内 p 折叠**：块级子元素并入 li 文本成
  单个 list_item；行内混排同段拼接
- **p 嵌套 p（非法 HTML）**：内层透明，
  'outerinner' 无分隔拼接
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def test_heading_in_cell_flattened(tmp_path):
    doc = _run(
        tmp_path,
        "<table><tr><td><h2>H</h2>"
        "</td></tr></table>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_li_block_children_collapsed(tmp_path):
    doc = _run(
        tmp_path,
        "<ul><li><p>para in li</p></li>"
        "</ul>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "para in li",
         {"ordered": False,
          "marker": "unordered"})]

    doc2 = _run(
        tmp_path,
        "<li>text <b>bold</b> tail</li>")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("list_item", "text bold tail")]


def test_p_in_p_transparent(tmp_path):
    doc = _run(
        tmp_path,
        "<p>outer<p>inner</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "outerinner")]
