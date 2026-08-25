r"""pipeline HTML br 换行与 th 表头（Round 1640）。

新角度：R1639 锁 ipynb section——**br 在段内
的行为、th 表头行渲染**零覆盖：

- **br → 单空格**：'line one<br>line two' 同
  一段落成 'line one line two'
- **双 br 不分段**：'a<br><br>b' 仍单段落
  'a  b'（两个空格，无段落切分）
- **th 渲染表头**：th 行 + '| --- |' 分隔行，
  row_count 含表头；纯 th 表也有表头行
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


def test_br_single_space(tmp_path):
    doc = _run(
        tmp_path,
        "<p>line one<br>line two</p>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "line one line two", {})]


def test_double_br_no_split(tmp_path):
    doc = _run(
        tmp_path, "<p>a<br><br>b</p>")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a  b")]


def test_th_header_row(tmp_path):
    doc = _run(
        tmp_path,
        "<table><tr><th>H1</th><th>H2</th>"
        "</tr><tr><td>a</td><td>b</td></tr>"
        "</table>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H1 | H2 |\n| --- | --- |\n"
                  "| a | b |",
         {"row_count": 2, "col_count": 2,
          "source": "html_table"})]

    doc2 = _run(
        tmp_path,
        "<table><tr><th>Only</th></tr></table>")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("table", "| Only |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]
