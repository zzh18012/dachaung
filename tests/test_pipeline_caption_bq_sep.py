r"""pipeline 表 caption 丢弃、figcaption 成段、
blockquote 分段（Round 1646）。

新角度：R1645 锁属性/pre——**caption 元素
丢弃、figcaption 无关联成普通段、'>' 分隔
引用语义**零覆盖：

- **table 内 caption 丢弃**：'Cap' 不进表格
  也不成段；纯 caption 表 → no_extracted_
  elements（html_no_content）
- **figcaption 成普通段**：figure 里 img 照常
  image，figcaption 文本成 paragraph，无
  caption 关联
- **'>' 分隔行在引用内**：'> a\\n>\\n> b' 单
  blockquote 'a\\n\\nb'；空行分隔才是两个
  blockquote
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def _md(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_table_caption_dropped(tmp_path):
    doc, errors = _html(
        tmp_path,
        "<table><caption>Cap</caption>"
        "<tr><td>x</td></tr></table>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| x |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]

    doc2, errors2 = _html(
        tmp_path,
        "<table><caption>Only</caption></table>")
    assert doc2 is None
    assert [e.code for e in errors2] == [
        "no_extracted_elements"]


def test_figcaption_plain_paragraph(tmp_path):
    doc, errors = _html(
        tmp_path,
        "<figure><img src='i.png' alt='A'>"
        "<figcaption>fig text</figcaption>"
        "</figure>")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"}),
        ("paragraph", "fig text", {})]


def test_blockquote_separator(tmp_path):
    doc = _md(tmp_path, "> a\n>\n> b\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a\n\nb",
         {"kind": "blockquote"})]

    doc2 = _md(tmp_path, "> a\n\n> b\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("paragraph", "b", {"kind": "blockquote"})]
