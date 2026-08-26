r"""pipeline 表格紧贴段落/列表与多空行折叠
（Round 1666）。

新角度：R1665 锁无引号属性——**表格行紧
贴上一块不 lazy 合并、多个空行等同一个**
零覆盖：

- **段落贴表**：'intro text' 下一行即表头
  → paragraph 与 table 各自成块（表格检
  测优先于段落 lazy 延续，与 '--- x' 并入
  段落不同）
- **列表贴表**：list_item 与 table 同样分
  离
- **多空行**：连续 4 空行 = 1 空行，两段
  照常
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


def test_para_adjacent_table(tmp_path):
    doc = _run(
        tmp_path,
        "intro text\n| a | b |\n| --- | --- |\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "intro text", {}),
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_list_adjacent_table(tmp_path):
    doc = _run(
        tmp_path,
        "- x\n| a | b |\n| --- | --- |\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "x"),
        ("table", "| a | b |\n| --- | --- |")]


def test_multiple_blank_lines_collapse(tmp_path):
    doc = _run(tmp_path, "one\n\n\n\n\ntwo\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "one"),
        ("paragraph", "two")]
