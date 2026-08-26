r"""parser md 缩进围栏退化、html tfoot
DOM 序、无引号属性容错（Round 1834）。

新角度：R1833 锁标记变体——**缩进
2 空格的 ``` 围栏不识别——成普通
paragraph 字面 '``` ... ```' 无
code_block 元数据；thead/tfoot/
tbody 按源码 DOM 序（H/F/B）不重排
tfoot 到末尾；border=1 无引号属性
容错解析**零覆盖：

- **缩进围栏**：paragraph 无 kind
- **tfoot 序**：'| H |'/'| F |'/'| B |'
- **无引号属性**：照常成表
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_indented_fence_degrades(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("- item\n\n  ```\n  code\n  ```\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "```\n  code\n  ```", {})]


def test_tfoot_dom_order(tmp_path):
    doc, errors = _html(
        tmp_path,
        "<table><thead><tr><th>H</th></tr>"
        "</thead><tfoot><tr><td>F</td></tr>"
        "</tfoot><tbody><tr><td>B</td></tr>"
        "</tbody></table>")
    assert errors == []
    t = doc.elements[0]
    assert t.content == "| H |\n| --- |\n| F |\n| B |"
    assert t.metadata["row_count"] == 3


def test_unquoted_attribute_tolerated(tmp_path):
    doc, errors = _html(
        tmp_path,
        '<table border=1><tr><td>x</td></tr>'
        "</table>")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| x |\n| --- |"]
