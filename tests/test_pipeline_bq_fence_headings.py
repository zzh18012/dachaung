r"""pipeline 引用内围栏、连续标题分块、无竖
线表（Round 1651）。

新角度：R1650 锁标题层级/缩进——**引用内
围栏惰性、heading+heading 不合并、管道表
需首尾竖线**零覆盖：

- **引用内围栏惰性**：'> ```' 逐行剥一个
  '>'，内容 '```\\ncode\\n```' 是 blockquote
  段而非 code_block
- **连续标题各成块**：'# A' 与 '# B' 两个
  sequential chunk（对照 R1611 heading+para
  会合并）
- **无首尾竖线不成表**：'a | b\\n--- | ---'
  是 paragraph（首尾 '|' 必需）
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


def test_bq_fence_inert(tmp_path):
    doc = _run(tmp_path, "> ```\n> code\n> ```\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "```\ncode\n```",
         {"kind": "blockquote"})]


def test_consecutive_headings_separate_chunks(
        tmp_path):
    doc = _run(tmp_path, "# A\n\n# B\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("A", 1, "sequential"),
        ("B", 1, "sequential")]


def test_no_outer_pipes_not_table(tmp_path):
    doc = _run(
        tmp_path, "a | b\n--- | ---\nx | y\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a | b\n--- | ---\nx | y",
         {})]
