r"""pipeline html hr 丢弃、li 内链接 raw、
body 内 title 丢弃（Round 1653）。

新角度：R1652 锁 pre>code——**hr 元素、列
表项内联链接、head 外 title**零覆盖：

- **html '&lt;hr&gt;' 整体丢弃**：前后段落
  照常（与 md 分隔线一致）
- **li 内链接 raw**：'- [x](http://u) tail'
  剥 '- ' 后链接原样
- **body 内 '&lt;title&gt;' 也丢**：title 不
  只在 head 中被剥，出现在 body 同样不产
  出元素
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


def test_html_hr_dropped(tmp_path):
    doc = _run(tmp_path, "<p>a</p><hr><p>b</p>",
               "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {}),
        ("paragraph", "b", {})]


def test_li_inline_link_raw(tmp_path):
    doc = _run(
        tmp_path, "- [x](http://u) tail\n",
        "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "[x](http://u) tail",
         {"ordered": False, "marker": "unordered"})]


def test_title_in_body_dropped(tmp_path):
    doc = _run(
        tmp_path,
        "<body><title>T</title><p>x</p></body>",
        "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]
