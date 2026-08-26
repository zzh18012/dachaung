r"""pipeline 双标题跟随段落分块流、贴段围栏、
code 多行（Round 1660）。

新角度：R1659 锁 EOF 无换行——**A/B/body
三分块流、围栏前无空行照常、ipynb code 多
行 source**零覆盖：

- **双标题+段落**：'# A\\n\\n# B\\n\\nbody'
  → chunk 'A'（1 id）+ 'B body text'
  （2 id）——B 与后随段落合并、A 独占
- **贴段围栏**：'text\\n```\\ncode\\n```' 无
  空行也照常成 code_block（段落不吞围栏）
- **code 多行 source**：['a\\n','b\\n'] →
  段落 'a\\nb'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_two_headings_then_para(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# A\n\n# B\n\nbody text\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("A", 1, "sequential"),
        ("B body text", 2, "sequential")]


def test_fence_adjacent_paragraph(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("text\n```\ncode\n```\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "text", {}),
        ("paragraph", "code",
         {"kind": "code_block", "language": ""})]


def test_code_multiline_source(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["a\n", "b\n"],
                   "outputs": []}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a\nb")]
