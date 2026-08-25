r"""pipeline Markdown 管道表边角：对齐标记/
参差行/分隔行必需（Round 1628）。

新角度：R1627 锁 html 孤儿标签——**md 表格
对齐冒号、参差行补空、无分隔行**零覆盖：

- **对齐标记不识别**：'|:--|:-:|--:|' 不匹配
  分隔行正则 → 整块成普通段落 raw
- **参差行补空**：短行补 '||' 到最大列数，
  长行扩展 col_count（3 列）
- **分隔行必需**：无 '| --- |' 行的两行管道
  文本 → 段落 raw
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


def test_alignment_not_recognized(tmp_path):
    doc = _run(
        tmp_path,
        "| L | C | R |\n"
        "|:--|:-:|--:|\n"
        "| 1 | 2 | 3 |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "| L | C | R |\n"
         "|:--|:-:|--:|\n"
         "| 1 | 2 | 3 |", {})]


def test_ragged_rows_padded(tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n"
        "| --- | --- |\n"
        "| one |\n"
        "| x | y | z |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a | b |  |\n"
         "| --- | --- | --- |\n"
         "| one |  |  |\n"
         "| x | y | z |",
         {"row_count": 3, "col_count": 3,
          "source": "markdown_pipe_table"})]


def test_separator_required(tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n| 1 | 2 |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "| a | b |\n| 1 | 2 |", {})]
