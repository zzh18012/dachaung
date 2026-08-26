r"""pipeline 孤 dt、html 参差行、标题前导空格
（Round 1663）。

新角度：R1662 锁 code 合并——**dt 无 dd、
html 行比表头短、标题前 1 空格**零覆盖：

- **孤 dt**：'<dt>term</dt>' 无 dd → 普通
  paragraph（不成 termdef）
- **html 参差行**：第二行 1 格 → 补空格
  '| x |  |'，col_count 仍 2（与 md 参差
  一致）
- **标题前导空格**：' # T' → paragraph
  '# T' 原样（任何缩进破坏，与列表一致）
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


def test_orphan_dt_paragraph(tmp_path):
    doc = _run(tmp_path, "<dl><dt>term</dt></dl>",
               "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "term", {})]


def test_html_ragged_row_padded(tmp_path):
    doc = _run(
        tmp_path,
        "<table><tr><td>a</td><td>b</td></tr>"
        "<tr><td>x</td></tr></table>",
        "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |\n"
                  "| x |  |",
         {"row_count": 2, "col_count": 2,
          "source": "html_table"})]


def test_heading_leading_space_raw(tmp_path):
    doc = _run(tmp_path, " # T\n",
               "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "# T", {})]
