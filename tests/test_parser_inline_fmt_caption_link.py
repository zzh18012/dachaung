r"""parser html 内联格式标签剥壳保文、
caption 静默丢弃、md 内联链接字面
（Round 1822）。

新角度：R1821 锁 th 内图片空单元——
**b/i/strong/em/code 全部剥壳只留文本
'bold it st em cd'；<caption> 不进表
格也不发射元素（静默丢）；md '[text]
(url)' 整串字面保留（raw 哲学含链接
语法本身）**零覆盖：

- **内联格式**：五标签一串纯文本
- **caption**：表格只剩 '| a |'
- **md 链接**：'[text](http://x.com)'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_html_inline_formatting_stripped(tmp_path):
    doc, errors = _html(
        tmp_path,
        '<p><b>bold</b> <i>it</i> '
        '<strong>st</strong> <em>em</em> '
        '<code>cd</code></p>')
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "bold it st em cd")]


def test_html_caption_dropped(tmp_path):
    doc, errors = _html(
        tmp_path,
        '<table><caption>Cap</caption>'
        '<tr><th>a</th></tr></table>')
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| a |\n| --- |"]
    assert all("Cap" not in (e.content or "")
               for e in doc.elements)


def test_md_inline_link_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "see [text](http://x.com) end\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "see [text](http://x.com) end"]
