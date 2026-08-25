r"""pipeline HTML 列表/表格/行内家族（Round 1607）。

新角度：R1606 锁空输入——**html 的 ol 属性、嵌套
列表、thead/tbody、colspan、链接、dl** 零覆盖：

- **&lt;ol&gt;** → {'ordered': True, 'marker':
  'ordered'}（同 markdown 分类学）；**start 属性
  忽略**；**嵌套列表拉平**（outer/inner 均平级
  list_item，保文档序）
- **thead/tbody 无缝合并**；metadata 带
  source:'html_table'（区别于 markdown 管道表的
  'markdown_pipe_table'）；**colspan 折叠**
  （单格 → col_count 1）
- **链接丢 href 留锚文本**（区别于 markdown
  raw 保留）；strong 剥除；**&lt;dl&gt; 的 dt+dd
  无分隔符拼接**（'termdef'）
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


def test_html_list_family(tmp_path):
    doc = _run(
        tmp_path,
        "<ol><li>first</li><li>second</li></ol>"
        "<ul><li>outer<ul><li>inner</li>"
        "</ul></li></ul>"
        '<ol start="5"><li>jumps</li></ol>')
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "first",
         {"ordered": True,
          "marker": "ordered"}),
        ("list_item", "second",
         {"ordered": True,
          "marker": "ordered"}),
        ("list_item", "outer",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "inner",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "jumps",
         {"ordered": True,
          "marker": "ordered"})]
    (c,) = doc.chunks
    assert c.text == (
        "first second outer inner jumps")
    assert c.metadata["strategy"] == "sequential"


def test_html_table_variants(tmp_path):
    doc = _run(
        tmp_path,
        "<table><thead><tr><th>H1</th>"
        "<th>H2</th></tr></thead>"
        "<tbody><tr><td>a</td><td>b</td>"
        "</tr></tbody></table>"
        '<table><tr><td colspan="2">wide'
        "</td></tr></table>")
    t1, t2 = doc.elements
    assert t1.content == (
        "| H1 | H2 |\n| --- | --- |\n| a | b |")
    assert t1.metadata == {
        "row_count": 2, "col_count": 2,
        "source": "html_table"}
    assert t2.content == (
        "| wide |\n| --- |")
    assert t2.metadata == {
        "row_count": 1, "col_count": 1,
        "source": "html_table"}
    strategies = [c.metadata["strategy"]
                  for c in doc.chunks]
    assert strategies == ["isolated_table",
                          "isolated_table"]


def test_html_inline_and_dl(tmp_path):
    doc = _run(
        tmp_path,
        '<p>See <a href="u.html">link</a> and '
        "<strong>bold</strong>.</p>"
        "<dl><dt>term</dt><dd>def</dd></dl>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "See link and bold.", {}),
        ("paragraph", "termdef", {})]
