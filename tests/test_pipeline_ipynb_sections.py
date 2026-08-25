r"""pipeline ipynb 单元内 section 与跨单元重置
（Round 1639）。

新角度：R1638 锁 html 完整文档——**单元内
section_path 嵌套、跨单元重置、code 单元无
section**零覆盖：

- **单元内嵌套完整**：多行 markdown 单元里
  '# T' → '## S' → 'T > S'，行号逐行递增
- **section 每单元重置**：单元 0 的标题不
  影响单元 1（段落 locator 无 section_path 键）
- **code 单元永无 section_path**；后续单元
  的 '##' 从根开始
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _nb(tmp_path, cells):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    return doc


def test_within_cell_nesting(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": ["# T\n", "text under\n",
                    "## S\n", "in s\n"]}])
    assert [e.source_locator
            for e in doc.elements] == [
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 1, "section_path": "T"},
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 2, "section_path": "T"},
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 3,
         "section_path": "T > S"},
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 4,
         "section_path": "T > S"}]


def test_section_resets_per_cell(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": ["# Title\n"]},
        {"cell_type": "markdown",
         "source": ["under title\n"]}])
    assert [e.source_locator
            for e in doc.elements] == [
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 1,
         "section_path": "Title"},
        {"cell_index": 1,
         "cell_type": "markdown",
         "line": 1}]


def test_code_cells_root_restart(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": ["# Title\n"]},
        {"cell_type": "code",
         "source": ["x=1"], "outputs": []},
        {"cell_type": "markdown",
         "source": ["## Sub\n"]},
        {"cell_type": "code",
         "source": ["y=2"], "outputs": []}])
    assert [e.source_locator
            for e in doc.elements] == [
        {"cell_index": 0,
         "cell_type": "markdown",
         "line": 1,
         "section_path": "Title"},
        {"cell_index": 1, "cell_type": "code"},
        {"cell_index": 2,
         "cell_type": "markdown",
         "line": 1, "section_path": "Sub"},
        {"cell_index": 3, "cell_type": "code"}]
