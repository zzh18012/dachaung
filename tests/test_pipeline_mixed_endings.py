r"""pipeline 混合行尾、尾井号非独立、td 内
pre 换行（Round 1672）。

新角度：R1671 锁空边界——**\\r\\n 与 \\n
混排、'### T ### extra'、td 内 pre 换行**
零覆盖：

- **混合行尾**：一行 \\r\\n 一行 \\n 交错
  → 全归一成 \\n，单段落
- **尾井号非独立**：'T ### extra' 井号是
  标题文本一部分（R1614 只锁井号独立结尾
  才剥）
- **td 内 pre**：'&lt;pre&gt;a\\nb&lt;/pre&gt;'
  换行保留进单元格 '| a\\nb |'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_mixed_endings_normalized(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"one\r\ntwo\nthree\r\nfour")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "one\ntwo\nthree\nfour")]


def test_trailing_hashes_not_alone(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("### T ### extra\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T ### extra", {"level": 3})]


def test_pre_newline_in_cell(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td><pre>a\nb</pre></td>"
        "</tr></table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a\nb |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]
