r"""pipeline ul 前散文本、百段合一块与
raw/markdown 交替 cell（Round 1731）。

新角度：R1730 锁引用后表格——**`<ul>` 前
散文本先成段落、100 个 text 段落全并
1 chunk（389 字符）、raw 与 markdown cell
交替顺序保留**零覆盖：

- **`<ul>pre<li>a</li></ul>`**：paragraph
  'pre' + list_item 'a'
- **'w0'…'w99' 100 段**：100 elements →
  单 chunk 389（sequential 全合并）
- **raw/m1/raw 三 cell**：三个段落 kind
  依次 raw_cell/无/raw_cell
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_ul_loose_text_before_li(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<ul>pre<li>a</li></ul>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "pre", {}),
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"})]


def test_100_paragraphs_single_chunk(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("\n\n".join(f"w{i}" for i in range(100)),
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert len(doc.elements) == 100
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0].text) == 389
    assert doc.chunks[0].metadata["strategy"] == "sequential"


def test_alternating_raw_markdown_cells(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "raw", "source": ["r0"]},
            {"cell_type": "markdown", "source": ["m1"]},
            {"cell_type": "raw", "source": ["r2"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "r0", {"kind": "raw_cell"}),
        ("paragraph", "m1", {}),
        ("paragraph", "r2", {"kind": "raw_cell"})]
