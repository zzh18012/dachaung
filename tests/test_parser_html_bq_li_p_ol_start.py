r"""parser html blockquote kind、li 内 p
剥壳、ol start 属性忽略（Round 1823）。

新角度：R1822 锁 caption 静默丢——**
html <blockquote> → paragraph +
kind='blockquote'（与 md bq 同
taxonomy）；<li><p>x</p></li> →
list_item 'x'（p 壳剥掉）；<ol
start="5"> 编号忽略——内容无数字、
ordered/marker 元数据照发**零覆盖：

- **html bq**：kind blockquote
- **li 内 p**：list_item 'para in li'
- **ol start**：'five'/'six' 无编号
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_html_blockquote_kind(tmp_path):
    doc, errors = _run(
        tmp_path, "<blockquote>quoted text</blockquote>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "quoted text",
         {"kind": "blockquote"})]


def test_li_p_stripped(tmp_path):
    doc, errors = _run(
        tmp_path, "<ul><li><p>para in li</p></li></ul>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "para in li",
         {"ordered": False, "marker": "unordered"})]


def test_ol_start_ignored(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<ol start="5"><li>five</li>'
        "<li>six</li></ol>")
    assert errors == []
    assert [(e.content, e.metadata["ordered"])
            for e in doc.elements] == [
        ("five", True), ("six", True)]
    assert all("5" not in (e.content or "")
               and "6" not in (e.content or "")
               for e in doc.elements)
