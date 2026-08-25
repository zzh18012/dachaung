r"""pipeline HTML 完整文档结构与标题内行内
（Round 1638）。

新角度：R1637 锁引用内部——**html/body 属性
透明、head 整体丢弃、标题内行内剥除+实体解码**
零覆盖：

- **标题内行内**：'&lt;h2&gt;&lt;b&gt;B&lt;/b&gt;
  old &amp;amp; new' → heading 'B old & new'
- **html/body 带属性透明**：内容照常提取
- **完整文档**：head（meta/title）整体丢弃，
  body 内容正常
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


def test_inline_in_heading(tmp_path):
    doc = _run(
        tmp_path,
        "<h2><b>B</b> old &amp; new</h2>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "B old & new",
         {"level": 2})]


def test_html_body_attrs_transparent(tmp_path):
    doc = _run(
        tmp_path,
        '<html lang="en"><body><p>deep'
        "</p></body></html>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "deep")]


def test_full_document_head_dropped(tmp_path):
    doc = _run(
        tmp_path,
        "<html><head><meta charset='utf-8'>"
        "<title>T</title></head>"
        "<body><h1>H</h1></body></html>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "H")]
