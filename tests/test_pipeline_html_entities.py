r"""pipeline HTML 实体全集与 img 属性、行内标签
（Round 1621）。

新角度：R1620 锁 md 引用——**数字实体、命名
实体（nbsp/copy/quot）、img 属性筛选、em/code**
零覆盖（R1602 只锁 &amp;&lt;&gt;）：

- **数字实体解码**：&#65; → 'A'，十六进制
  &#x41; → 'A'
- **命名实体解码**：&nbsp; → '\\xa0'（不间断
  空格）、&copy; → '©'、&quot; → '"'
- **img 只留 alt**：title/width 属性丢弃；
  em/code 行内标签剥除（同 strong）
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


def test_numeric_entities(tmp_path):
    doc = _run(
        tmp_path,
        "<p>&#65;&#66;&#67; and &#x41;</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "ABC and A")]


def test_named_entities(tmp_path):
    doc = _run(
        tmp_path,
        '<p>a&nbsp;b &copy; '
        "&quot;q&quot;</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         'a\xa0b © "q"')]


def test_img_attrs_and_inline(tmp_path):
    doc = _run(
        tmp_path,
        '<img src="x.png" alt="A" '
        'title="T" width="10">'
        "<p>x <em>em</em> "
        "<code>cd</code> y</p>")
    assert [(e.type, e.content,
             e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"}),
        ("paragraph", "x em cd y", {})]
