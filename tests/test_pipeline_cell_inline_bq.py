r"""pipeline 单元格内剥内联与三层引用
（Round 1680）。

新角度：R1679 锁引用内表格——**td/th 内
内联标签剥除（与正文一致）、'&gt;&gt;&gt;'
三层只剥一层**零覆盖：

- **td 内 &lt;b&gt;**：'| x y |'（内联剥、
  文本拼）
- **th 内 &lt;i&gt;**：'| H |'
- **'&gt;&gt;&gt;'**：剩 '&gt;&gt; deep'
  单层 blockquote（每行只剥一个 '&gt;'）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_b_in_td_stripped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td><b>x</b> y</td></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| x y |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_i_in_th_stripped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th><i>H</i></th></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| H |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_triple_quote_one_stripped(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(">>> deep\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", ">> deep",
         {"kind": "blockquote"})]
