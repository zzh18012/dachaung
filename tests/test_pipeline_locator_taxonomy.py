r"""pipeline 多解析器 source_locator 分类学（Round 1596）。

新角度：R1594 锁 confidence——**markdown/text/
ipynb 的 locator 结构与 section_path 嵌套**在
pipeline 层零覆盖：

- **markdown**：{line, section_path}；嵌套标题
  用 ' > ' 连接（'A > B'）、同级/更高级标题重置
- **text**：仅 {line}
- **ipynb**：markdown 单元 {cell_index, cell_type,
  line, section_path}；code 单元仅
  {cell_index, cell_type}
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_markdown_section_path_nested(
        tmp_path):
    p = tmp_path / "n.md"
    p.write_text(
        "# A\n\n## B\n\nUnder B.\n\n"
        "# C\n\nUnder C.\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="markdown")
    assert errors == []
    got = [(e.type,
            e.source_locator)
           for e in doc.elements]
    assert got == [
        ("heading",
         {"line": 1,
          "section_path": "A"}),
        ("heading",
         {"line": 3,
          "section_path": "A > B"}),
        ("paragraph",
         {"line": 5,
          "section_path": "A > B"}),
        ("heading",
         {"line": 7,
          "section_path": "C"}),
        ("paragraph",
         {"line": 9,
          "section_path": "C"})]


def test_text_locator_line_only(
        tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("Line1\nLine2\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="text")
    assert errors == []
    (el,) = doc.elements
    assert el.source_locator == {"line": 1}


def test_ipynb_locator_cells(
        tmp_path):
    p = tmp_path / "d.ipynb"
    nb = {
        "cells": [
            {"cell_type": "markdown",
             "source": ["# NB\n",
                        "text"]},
            {"cell_type": "code",
             "source": ["print(1)"]},
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    p.write_text(json.dumps(nb),
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="ipynb")
    assert errors == []
    got = [(e.type,
            e.source_locator)
           for e in doc.elements]
    assert got == [
        ("heading",
         {"cell_index": 0,
          "cell_type": "markdown",
          "line": 1,
          "section_path": "NB"}),
        ("paragraph",
         {"cell_index": 0,
          "cell_type": "markdown",
          "line": 2,
          "section_path": "NB"}),
        ("paragraph",
         {"cell_index": 1,
          "cell_type": "code"})]
