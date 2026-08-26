r"""pipeline 家族 locator 形态与 section_path
跨 cell 不传递（Round 1746）。

新角度：R1745 锁 JSON 回验——**html/text
物理行号定位；ipynb 带 cell_index/
cell_type/line 三键；ipynb 内 section_path
不跨 cell 传递（cell1 段落无该键，与 md
文件内跟随标题相反）**零覆盖：

- **html 三元素**：line 1/2/3，h2 起带
  section_path 'T'
- **text 两段**：仅 line 1/3，无
  section_path 键，metadata {'text': True}
- **ipynb 两 cell**：heading cell locator
  含 section_path 'T'，下一 cell 段落
  locator 无 section_path
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_html_physical_line_locators(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<p>aaa</p>\n<h2>T</h2>\n<ul><li>a</li></ul>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.source_locator for e in doc.elements] == [
        {"line": 1}, {"line": 2, "section_path": "T"},
        {"line": 3, "section_path": "T"}]


def test_text_line_only_locators(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("aaa\n\nbbb\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [e.source_locator for e in doc.elements] == [
        {"line": 1}, {"line": 3}]
    assert all(e.confidence == 0.95
               for e in doc.elements)
    assert doc.metadata == {"text": True}


def test_ipynb_cell_locators_no_cross_cell_section(
        tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "markdown", "source": ["## T"]},
            {"cell_type": "markdown", "source": ["bbb"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [e.source_locator for e in doc.elements] == [
        {"cell_index": 0, "cell_type": "markdown",
         "line": 1, "section_path": "T"},
        {"cell_index": 1, "cell_type": "markdown",
         "line": 1}]
