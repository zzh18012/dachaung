r"""pipeline 相邻表格与 md 单列表不识别
（Round 1649）。

新角度：R1648 锁围栏语言——**相邻 html 表
各自 isolated、md 管道表需 ≥2 列、'--- x'
非分隔线**零覆盖：

- **相邻 html 表**：两个 table 元素 → 各自
  isolated_table chunk（不合并）
- **md 单列表**：'| a |\\n| --- |\\n| one |'
  是 paragraph 不是 table（有无数据行皆然）
- **仅表头+分隔行的 2 列表**：成 table
  （row_count 1 含表头，source
  'markdown_pipe_table'）；'--- x' 带 x 非
  hr，lazy 并入上段
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def _md(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_adjacent_html_tables_isolated(tmp_path):
    doc = _html(
        tmp_path,
        "<table><tr><td>a</td></tr></table>"
        "<table><tr><td>b</td></tr></table>")
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("| a |\n| --- |", "isolated_table"),
        ("| b |\n| --- |", "isolated_table")]
    assert [c.source_element_ids[0][-5:]
            for c in doc.chunks] == ["e0000", "e0001"]


def test_md_single_column_not_table(tmp_path):
    doc = _md(
        tmp_path, "| a |\n| --- |\n| one |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "| a |\n| --- |\n| one |",
         {})]

    doc2 = _md(tmp_path, "| a |\n| --- |\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "| a |\n| --- |")]


def test_md_two_col_header_only_table(tmp_path):
    doc = _md(
        tmp_path, "| a | b |\n| --- | --- |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]

    doc2 = _md(tmp_path, "T\n--- x\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "T\n--- x")]
