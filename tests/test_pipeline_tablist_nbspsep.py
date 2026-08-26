r"""pipeline tab 缩进断列表、NBSP 作标题
分隔、td 内引用拍平（Round 1728）。

新角度：R1727 锁引用惰性——**'\\t- b' tab
缩进断列表成段落、'#\\xa0T' NBSP 可作标题
分隔符、td 内 bq 拍平、text 内 NBSP 保留**
零覆盖：

- **'- a\\n\\t- b'**：list_item 'a' +
  paragraph '- b'（tab 同空格断列表）
- **'#\\xa0T'**：heading 'T'（NBSP 等效
  分隔，对比 1 空格也断）
- **td 内 `<blockquote>q</blockquote>`**：
  拍平单元格 'q'
- **text 'a\\xa0b'**：NBSP 原样保留
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


def test_tab_indent_breaks_list(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\t- b\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "- b", {})]


def test_nbsp_heading_separator(tmp_path):
    doc, errors = _run(tmp_path, "#\xa0T\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 1})]


def test_bq_in_td_flattens(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><blockquote>q</blockquote>"
        "</td></tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| q |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_text_nbsp_preserved(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes("a\xa0b\n".encode())
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a\xa0b")]
