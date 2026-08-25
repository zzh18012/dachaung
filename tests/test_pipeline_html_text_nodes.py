r"""pipeline HTML 文本节点拼接与空元素（Round 1633）。

新角度：R1632 锁空白保留——**行内标签拼接
不加空格、空/纯空白元素整体丢弃、body 级 br**
零覆盖：

- **文本节点原样拼接**：'one<b>two</b>three'
  → 'onetwothree'（无插入空格）；源内空格
  照保留；span 透明
- **空元素丢弃**：&lt;p&gt;&lt;/p&gt;、
  纯空白 &lt;p&gt;、空 &lt;li&gt; 不产生元素
- **body 级 &lt;br&gt; 丢弃**（不产生空段落）
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


def test_text_node_concatenation(tmp_path):
    doc = _run(
        tmp_path,
        "<p>one<b>two</b>three</p>")
    assert [e.content
            for e in doc.elements] == [
        "onetwothree"]

    doc2 = _run(
        tmp_path,
        "<p>one <b>two</b> three</p>")
    assert [e.content
            for e in doc2.elements] == [
        "one two three"]

    doc3 = _run(
        tmp_path,
        "<div>alpha <span>beta</span>"
        " gamma</div>")
    assert [e.content
            for e in doc3.elements] == [
        "alpha beta gamma"]


def test_empty_elements_dropped(tmp_path):
    doc = _run(
        tmp_path,
        "<p></p><p>   </p><p>real</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "real")]

    doc2 = _run(
        tmp_path,
        "<ul><li></li><li>x</li></ul>")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("list_item", "x")]


def test_body_br_dropped(tmp_path):
    doc = _run(
        tmp_path,
        "<p>a</p><br><p>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a"),
        ("paragraph", "b")]
