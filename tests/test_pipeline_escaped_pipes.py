r"""pipeline md 表格单元格无管道转义
（Round 1687）。

新角度：R1686 锁 pre 实体——**'\\|' 反斜
杠不转义管道，照常切格**零覆盖：

- **'a \\| b' 一格**：实际切成 'a \\' 与
  'b' 两格（反斜杠留在前格文本）
- **'\\|' 独占一格**：成 '\\' 格 + 追加
  空格占位；表头行短时补空格
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_escaped_pipe_still_splits(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a \\| b | c |\n| --- | --- | --- |\n"
        "| x \\| y | z |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a \\ | b | c |\n"
         "| --- | --- | --- |\n"
         "| x \\ | y | z |",
         {"row_count": 2, "col_count": 3,
          "source": "markdown_pipe_table"})]


def test_lone_escaped_pipe_cell(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b |\n| --- | --- | --- |\n"
        "| x | \\| |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table",
         "| a | b |  |\n"
         "| --- | --- | --- |\n"
         "| x | \\ |  |",
         {"row_count": 2, "col_count": 3,
          "source": "markdown_pipe_table"})]
