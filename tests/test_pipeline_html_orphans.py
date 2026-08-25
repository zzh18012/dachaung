r"""pipeline HTML 容错标记与孤儿标签（Round 1627）。

新角度：R1626 锁包装透明——**doctype/注释/未闭合
标签、孤儿 li/td/tr、嵌套表格**零覆盖：

- **宽容标记**：doctype/注释丢弃；未闭合 &lt;p&gt;
  正常提取；p 的属性忽略
- **孤儿 li** → list_item（unordered 缺省）；
  **孤儿 td/tr** → paragraph（无 table 容器则
  不成表格）
- **嵌套表格塌缩**：外层表格消失，产出一个
  '|  |\\n| --- |\\n| in |' 表（空表头 + 内容行）
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


def test_tolerant_markup(tmp_path):
    doc = _run(
        tmp_path,
        "<!DOCTYPE html><!-- note -->"
        '<p class="x" data-y="1">t</p>')
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "t", {})]

    doc2 = _run(
        tmp_path, "<p>unclosed")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "unclosed")]


def test_orphan_tags(tmp_path):
    doc = _run(
        tmp_path,
        "<li>orphan</li><p>ok</p>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "orphan",
         {"ordered": False,
          "marker": "unordered"}),
        ("paragraph", "ok", {})]

    doc2 = _run(
        tmp_path, "<td>cell</td>")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "cell")]

    doc3 = _run(
        tmp_path, "<tr><td>c</td></tr>")
    assert [(e.type, e.content)
            for e in doc3.elements] == [
        ("paragraph", "c")]


def test_nested_table_collapse(tmp_path):
    doc = _run(
        tmp_path,
        "<table><tr><td><table><tr><td>in"
        "</td></tr></table></td></tr>"
        "</table>")
    assert [(e.type, e.content,
             e.metadata)
            for e in doc.elements] == [
        ("table", "|  |\n| --- |\n| in |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]
