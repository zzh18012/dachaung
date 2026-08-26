r"""pipeline html 链成员细则：标题拉列表、
pre 入链、表格后不复并、标题断反向链
（Round 1743）。

新角度：R1742 锁 md 相邻表——**html 与 md
链规则完全同构：'<h2>'+ul → 'T a'（2
ids）；p+pre+p → 'aaa line1\\nline2 bbb'
（3 ids）；表格后段落不复并（img 旁路无
济）；bq 之后标题开新链 'q'+'T bbb'**零
覆盖：

- **`<h2>T</h2><ul><li>a</li></ul>`**：
  'T a'（2 ids）
- **`<p>aaa</p><pre>line1\\nline2</pre>`+
  `<p>bbb</p>`**：单 chunk 三源，kind
  'preformatted' 保内部换行
- **表+img+p**：表块 + 'bbb' 两块——
  表格打断后段落独立，img 不恢复合并
- **bq+h2+p**：'q'（1 id）+'T bbb'（2
  ids）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_html_heading_pulls_list(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>T</h2><ul><li>a</li></ul>")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "list_item"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T a", 2)]


def test_html_pre_joins_chain(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<p>aaa</p><pre>line1\nline2</pre><p>bbb</p>")
    assert errors == []
    assert [(e.type, e.metadata.get("kind"))
            for e in doc.elements] == [
        ("paragraph", None),
        ("paragraph", "preformatted"),
        ("paragraph", None)]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa line1\nline2 bbb", 3)]


def test_no_remerge_after_table(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><th>h1</th><th>h2</th></tr>"
        "<tr><td>v1</td><td>v2</td></tr></table>"
        "<img src='i.png'><p>bbb</p>")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "table", "image", "paragraph"]
    assert [len(c.source_element_ids)
            for c in doc.chunks] == [1, 1]
    assert doc.chunks[1].text == "bbb"


def test_html_heading_breaks_backward_chain(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<blockquote><p>q</p></blockquote>"
        "<h2>T</h2><p>bbb</p>")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("q", 1), ("T bbb", 2)]
