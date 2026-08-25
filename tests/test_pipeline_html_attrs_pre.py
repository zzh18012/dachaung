r"""pipeline HTML 属性透明与 pre 首尾 strip
（Round 1645）。

新角度：R1644 锁标题空格——**元素属性全丢、
pre 内部空白保留但首尾 strip**零覆盖：

- **h2/ul/li 带属性**：id/class/data-\* 全部
  丢弃，只留文本
- **pre 首行缩进剥除**：'  indented' →
  'indented'；中间行 '    more' 缩进保留；
  尾部空格剥除
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


def test_heading_attrs_dropped(tmp_path):
    doc = _run(
        tmp_path, '<h2 id="x" class="c">T</h2>')
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 2})]


def test_list_attrs_dropped(tmp_path):
    doc = _run(
        tmp_path,
        '<ul class="l"><li data-x="1">item</li>'
        "</ul>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": False, "marker": "unordered"})]


def test_pre_strips_ends_keeps_interior(tmp_path):
    doc = _run(
        tmp_path,
        "<pre>  indented\n    more  </pre>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "indented\n    more",
         {"kind": "preformatted"})]
