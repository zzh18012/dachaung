r"""pipeline ipynb 跨 cell 链细节：code
cell 入链、标题跨 cell 拉段、表格 cell 打断
（Round 1739）。

新角度：R1738 锁跨 cell 段落合并——**
code cell 也是链成员（kind 'code_cell'，
language ''）：'aaa print(1) bbb'（3
ids）；cell1 标题拉 cell2 段 'T bbb'（2
ids）；表格 cell 跨 cell 打断三块独立**
零覆盖：

- **md+code+md 三 cell**：单 chunk 三
  源，code cell 元素 kind='code_cell'
- **'## T' cell + 'bbb' cell**：'T bbb'
- **md+表格 cell+md**：'aaa'+表+'bbb'
  三块各 1 id
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, cells):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_code_cell_joins_cross_cell_chain(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown", "source": ["aaa"]},
        {"cell_type": "code", "source": ["print(1)"]},
        {"cell_type": "markdown", "source": ["bbb"]}])
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("paragraph", {}), ("paragraph",
         {"kind": "code_cell", "language": ""}),
        ("paragraph", {})]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa print(1) bbb", 3)]


def test_heading_cell_pulls_next_cell(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown", "source": ["## T"]},
        {"cell_type": "markdown", "source": ["bbb"]}])
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T bbb", 2)]


def test_table_cell_breaks_cross_cell_chain(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown", "source": ["aaa"]},
        {"cell_type": "markdown",
         "source": ["| h1 | h2 |\n| --- | --- |\n| v1 | v2 |"]},
        {"cell_type": "markdown", "source": ["bbb"]}])
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "paragraph", "table", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa", 1),
        ("| h1 | h2 |\n| --- | --- |\n| v1 | v2 |", 1),
        ("bbb", 1)]
