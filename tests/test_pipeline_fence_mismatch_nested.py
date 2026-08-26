r"""pipeline 围栏闭合类型匹配、md HTML 块
原样与 html 单元格内嵌块（Round 1697）。

新角度：R1696 锁波浪线围栏——**'```' 不能
闭合 '~~~'（内容连反引号一起吞）、md 中
HTML 块原样段落、td 内 h2 拍平、li 内 bq
吞掉 li、td 内嵌套表行并入外层表**零覆盖：

- **'~~~py' 由 '```' "闭合"**：不闭合，
  content 'code\\n```\\nafter' 全吞
- **'~~~' 内嵌 '```'**：内层反引号全是
  内容，'~~~' 才闭合，'tail' 独立段落
- **md '<div>x</div>'**：原样 paragraph
- **td 内 `<h2>`**：拍平成单元格文本 'H'
- **li 内 `<blockquote>`**：list_item 消失
  只剩 blockquote 段落 'q'
- **td 内嵌 `<table>`**：内层行并入外层，
  '|  |\\n| --- |\\n| in |'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_tilde_not_closed_by_backticks(tmp_path):
    doc, errors = _run(
        tmp_path, "~~~py\ncode\n```\nafter\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code\n```\nafter",
         {"kind": "code_block", "language": "py"})]


def test_backticks_inside_tilde_fence(tmp_path):
    doc, errors = _run(
        tmp_path, "~~~\n```\nx\n```\n~~~\ntail\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "```\nx\n```",
         {"kind": "code_block", "language": ""}),
        ("paragraph", "tail", {})]


def test_md_html_block_raw(tmp_path):
    doc, errors = _run(tmp_path, "<div>x</div>\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "<div>x</div>", {})]


def test_h2_in_td_flattens(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><h2>H</h2></td></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_bq_in_li_swallows_li(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li><blockquote>q</blockquote></li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "q", {"kind": "blockquote"})]


def test_nested_table_in_td_merges(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><table><tr><td>in</td>"
        "</tr></table></td></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  |\n| --- |\n| in |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]
