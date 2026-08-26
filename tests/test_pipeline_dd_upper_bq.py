r"""pipeline 孤 dd、大写标签、带空格引用标记
（Round 1664）。

新角度：R1663 锁孤 dt——**dd 无 dt、大写
HTML 标签、'&gt; &gt;' 带空格双层引用**零
覆盖：

- **孤 dd**：'<dd>def</dd>' 无 dt → 普通
  paragraph（与孤 dt 对称）
- **大写标签照常**：'&lt;P&gt;UPPER&lt;/P&gt;'
  成段、'&lt;H1&gt;TOP&lt;/H1&gt;' 成
  level 1 标题（标签大小写不敏感）
- **'&gt; &gt;' 带空格**：剥一层 '&gt; '
  剩 '&gt; deep'（与 '>>' 无空格版一致）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, payload, parser, suffix):
    p = tmp_path / ("d" + suffix)
    p.write_text(payload, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_orphan_dd_paragraph(tmp_path):
    doc = _run(tmp_path, "<dl><dd>def</dd></dl>",
               "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "def", {})]


def test_uppercase_tags(tmp_path):
    doc = _run(tmp_path, "<P>UPPER</P>",
               "html", ".html")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "UPPER")]

    doc2 = _run(tmp_path, "<H1>TOP</H1>",
                "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("heading", "TOP", {"level": 1})]


def test_spaced_bq_marker(tmp_path):
    doc = _run(tmp_path, "> > deep\n",
               "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "> deep",
         {"kind": "blockquote"})]
