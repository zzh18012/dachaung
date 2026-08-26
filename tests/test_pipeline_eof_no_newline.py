r"""pipeline md 文件尾无换行（Round 1659）。

新角度：R1658 锁 CR 字节——**EOF 无尾换
行的表格/列表/标题/带语言未闭合围栏**零
覆盖：

- **表无尾换行**：检测照常，成 table
- **列表/标题无尾换行**：list_item /
  heading 照常
- **带语言未闭合围栏**：吃余文件且 language
  'py' 保留（R1635 只锁空语言版）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, data):
    p = tmp_path / "d.md"
    p.write_bytes(data.encode("utf-8"))
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_table_no_trailing_newline(tmp_path):
    doc = _run(
        tmp_path, "| a | b |\n| --- | --- |")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_list_heading_no_trailing_newline(
        tmp_path):
    doc = _run(tmp_path, "- x")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "x",
         {"ordered": False, "marker": "unordered"})]

    doc2 = _run(tmp_path, "# T")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("heading", "T", {"level": 1})]


def test_unclosed_fence_with_language(tmp_path):
    doc = _run(tmp_path, "```py\ncode")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": "py"})]
