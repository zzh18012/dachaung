r"""pipeline code_block 与列表/段落合并分块
（Round 1662）。

新角度：R1661 锁纯图零 chunk——**code_block
元素与相邻段落/列表合并进同一 sequential
chunk**零覆盖：

- **段落-围栏-段落**：'before code after'
  单块（3 id）
- **列表-围栏-列表**：'a c b' 单块（3 id，
  围栏不切断列表合并）
- **引用单块**：blockquote 成常规 sequential
  chunk
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


def test_para_fence_para_merge(tmp_path):
    doc = _run(
        tmp_path, "before\n```\ncode\n```\nafter\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("before code after", 3, "sequential")]


def test_list_fence_list_merge(tmp_path):
    doc = _run(
        tmp_path,
        "- a\n\n```\nc\n```\n\n- b\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("a c b", 3, "sequential")]


def test_blockquote_chunk(tmp_path):
    doc = _run(tmp_path, "> quoted line\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("quoted line", 1, "sequential")]
