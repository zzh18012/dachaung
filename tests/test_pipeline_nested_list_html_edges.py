r"""pipeline html 嵌套列表拍平、标题 inline
剥离、单列表格与 md 括号 marker（Round 1693）。

新角度：R1692 锁 setext——**html 嵌套 ul 拍平
成兄弟项、html 单列表格合法（对比 md ≥2 列
要求）、md '1)' 括号 marker、列表续行成段
落**零覆盖：

- **嵌套 `<ul>` in li**：层级丢失，'a' 与
  'b' 两个平级 list_item
- **`<b>` in h2**：inline 标签剥离，'bold x
  tail' 完整 heading
- **thead+tbody 单列**：col_count 1 照常成
  表，th 出 '| --- |' 头
- **'1) item'**：括号 marker 成 ordered；
  '- item' 后 '  cont' 缩进续行不成项内
  文本，独立 paragraph
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_html_nested_list_flattened(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li>a<ul><li>b</li></ul></li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"})]


def test_html_inline_in_heading(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>bold <b>x</b> tail</h2>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "bold x tail", {"level": 2})]


def test_html_one_col_table(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><thead><tr><th>H</th></tr></thead>"
        "<tbody><tr><td>v</td></tr></tbody></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |\n| v |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_md_paren_marker_and_lazy_cont(tmp_path):
    doc, errors = _run(tmp_path, "1) item\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": True, "marker": "ordered"})]

    doc2, errors2 = _run(
        tmp_path, "- item\n  cont line\n", "d.md")
    assert errors2 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("list_item", "item",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "cont line", {})]
