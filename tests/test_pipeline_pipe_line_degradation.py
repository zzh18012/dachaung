r"""pipeline 管道行退化：裸分隔行、分隔
行在前皆段落（Round 1774）。

新角度：R1773 锁策略三值——**'| ---
| --- |' 单独成段、分隔行在前整块退化
段落（内部 \\n 保留）——两者都是
sequential 链成员；仅"表头在前+分隔行"
构成真表（row_count 1，isolated_table）**
零覆盖：

- **'| --- | --- |'**：paragraph 单段
- **'| --- | --- |\\n| a | b |'**：
  paragraph 两行一块
- **'| a | b |\\n| --- | --- |'**：
  table row_count 1
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_separator_alone_paragraph(tmp_path):
    doc, errors = _run(
        tmp_path, "| --- | --- |\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "| --- | --- |", {})]
    assert doc.chunks[0].metadata["strategy"] == (
        "sequential")


def test_separator_first_degrades(tmp_path):
    doc, errors = _run(
        tmp_path, "| --- | --- |\n| a | b |\n")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "| --- | --- |\n| a | b |")]
    assert doc.warnings == []


def test_header_then_separator_is_table(tmp_path):
    doc, errors = _run(
        tmp_path, "| a | b |\n| --- | --- |\n")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]
    assert doc.chunks[0].metadata["strategy"] == (
        "isolated_table")
