r"""pipeline HTML 结构家族：pre/br/实体/无 src 图（Round 1602）。

新角度：R1597 锁 html 元素家族——**结构细节**
零覆盖：

- **&lt;br&gt;** → 转空格；**&lt;pre&gt;** →
  paragraph {'kind': 'preformatted'}（换行保留）
- **HTML 实体解码**（&amp;&lt;&gt; → &<>）——
  区别于 markdown 的 raw 保留
- **无 src 的 &lt;img&gt;** → 完全丢弃（无元素）
- **h2/h3** → heading level 2/3
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="html")
    assert errors == []
    return doc


def test_pre_br_entities(tmp_path):
    doc = _run(
        tmp_path,
        '<p>a<br>b</p>'
        '<pre>code()\n'
        '  indent</pre>'
        '<p>&amp;&lt;&gt;</p>')
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("paragraph", "a b", {}),
        ("paragraph",
         "code()\n  indent",
         {"kind": "preformatted"}),
        ("paragraph", "&<>", {})]


def test_img_no_src_dropped(
        tmp_path):
    doc = _run(
        tmp_path,
        '<img alt="no-src">'
        '<img>'
        '<h2 class="x">H2</h2>'
        '<h3>H3</h3>')
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("heading", "H2",
         {"level": 2}),
        ("heading", "H3",
         {"level": 3})]
