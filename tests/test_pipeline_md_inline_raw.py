r"""pipeline Markdown 内联标记全 raw（Round 1641）。

新角度：R1640 锁 br/th——**段落里的 link/
code span/强调/行内 HTML 全部原样保留**零覆盖：

- **内联 link**：'[text](http://x.com) tail'
  方括号括号原样
- **code span 与强调**：反引号 / ** / * 不剥
- **HTML 行原样**：'<div class="x">hello</div>'
  整行不解析不剥属性；'start <b>bold</b> end'
  混排同样保留
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_inline_link_raw(tmp_path):
    doc = _run(
        tmp_path, "[text](http://x.com) tail\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "[text](http://x.com) tail", {})]


def test_code_span_emphasis_raw(tmp_path):
    doc = _run(
        tmp_path, "before `code span` after\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "before `code span` after")]

    doc2 = _run(
        tmp_path, "some **bold** and *ital* here\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "some **bold** and *ital* here")]


def test_html_verbatim(tmp_path):
    doc = _run(
        tmp_path,
        '<div class="x">hello</div>\n')
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         '<div class="x">hello</div>', {})]

    doc2 = _run(
        tmp_path, "start <b>bold</b> end\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "start <b>bold</b> end")]
