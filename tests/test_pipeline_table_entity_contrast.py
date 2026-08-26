r"""pipeline 表格实体对比：md raw 保留与
html 解码、img 属性解码（Round 1760）。

新角度：R1759 锁 alt 变体——**同一表格语
义两家实体策略相反：md 重建管道文本原样
保留 '&amp;'/'&#65;'；html 解码成
'&'/'A'；html img 的 src 与 alt 实体均
解码（'a&b.png'/'x <y>'）**零覆盖：

- **md 表**：'| a &amp; b | c |' 整块
  原样
- **html 表**：'| a & b | c |' 已解码
- **`<img src="a&amp;b.png" alt="x
  &lt;y&gt;">`**：两属性都解码
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


MD_TABLE = "| a &amp; b | c |\n| --- | --- |\n| &#65; | d |"


def test_md_table_entities_raw(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(MD_TABLE + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("table", MD_TABLE)]


def test_html_table_entities_decoded(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th>a &amp; b</th><th>c</th></tr>"
        "<tr><td>&#65;</td><td>d</td></tr></table>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("table", "| a & b | c |\n| --- | --- |\n| A | d |")]


def test_img_attr_entities_decoded(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        '<img src="a&amp;b.png" alt="x &lt;y&gt;">',
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    e = doc.elements[0]
    assert e.type == "image"
    assert e.resource_path == "a&b.png"
    assert e.metadata == {"alt": "x <y>"}
