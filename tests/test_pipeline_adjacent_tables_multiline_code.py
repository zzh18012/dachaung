r"""pipeline 相邻表格独立性与无空行并表、
多行代码入链（Round 1742）。

新角度：R1741 锁拼接单空格——**空行分
隔的两表各自成 chunk（各 1 id）互不合并；
无空行直接相连时并成一个 5 行表（第二分
隔行沦为数据行）；多行代码块入链保内部
\\n（'aaa l1\\nl2 bbb'，3 ids）**零覆盖：

- **表+空行+表**：2 elements 2 chunks
- **表直接接表**：1 element row_count=5，
  chunk 文本含 '| c | d |' 行与其后
  '| --- | --- |' 数据行
- **'aaa'+多行围栏代码+'bbb'**：
  'aaa l1\\nl2 bbb'（3 ids）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


T1 = "| a | b |\n| --- | --- |\n| 1 | 2 |"
T2 = "| c | d |\n| --- | --- |\n| 3 | 4 |"


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_two_tables_separate_chunks(tmp_path):
    doc, errors = _run(tmp_path, T1 + "\n\n" + T2 + "\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "table", "table"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        (T1, 1), (T2, 1)]


def test_glued_tables_merge_one_element(tmp_path):
    doc, errors = _run(tmp_path, T1 + "\n" + T2 + "\n")
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("table", {"row_count": 5, "col_count": 2,
                   "source": "markdown_pipe_table"})]
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == T1 + "\n" + T2


def test_multiline_code_internal_newline(tmp_path):
    doc, errors = _run(
        tmp_path, "aaa\n\n```\nl1\nl2\n```\n\nbbb\n")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "aaa"), ("paragraph", "l1\nl2"),
        ("paragraph", "bbb")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa l1\nl2 bbb", 3)]
