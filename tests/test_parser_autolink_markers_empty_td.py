r"""parser md 自动链接字面、列表 *
/+ 标记识别、html 空单元格（Round
1833）。

新角度：R1832 锁 hr 星号变体——**
'<http://x.com>' 尖括号自动链接整串
字面；'* s1' 与 '+ s2' 均识别为
list_item（marker 元数据只存
'ordered'/'unordered' 不存原字符）；
'<td></td>' 空单元保留空格 '|  | x
|'**零覆盖：

- **自动链接**：原文保留
- **标记变体**：'s1'/'s2' 均 unordered
- **空单元**：'|  | x |' 列数 2
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_md_autolink_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("see <http://x.com> end\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "see <http://x.com> end"]


def test_list_marker_variants(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("* s1\n+ s2\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "s1",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "s2",
         {"ordered": False, "marker": "unordered"})]


def test_html_empty_td_cell(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td></td><td>x</td></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    t = doc.elements[0]
    assert t.content == "|  | x |\n| --- | --- |"
    assert t.metadata == {
        "row_count": 1, "col_count": 2,
        "source": "html_table"}
