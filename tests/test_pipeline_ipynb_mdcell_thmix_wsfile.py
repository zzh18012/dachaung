r"""pipeline ipynb md cell 结构解析、
html 混排 th/td 行全表头、纯空白
text 文件报空（Round 1825）。

新角度：R1824 锁嵌套表行提升——**
ipynb markdown cell 内 '## MT' 真解析
出 heading（locator 带 cell_index/
cell_type/line/section_path）；<tr>
内 th+td 混排整行按表头处理 '| H |
D |'；纯空白 text 文件 doc=None +
no_extracted_elements**零覆盖：

- **ipynb md cell**：heading+para 双元
  素 locator 四键
- **混排行**：'| H | D |' 全表头
- **空白文件**：no_extracted_elements
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def test_ipynb_md_cell_structure(tmp_path):
    nb = {
        "cells": [{"cell_type": "markdown",
                   "source": ["## MT\n", "\n",
                              "body text"],
                   "metadata": {}}],
        "metadata": {}, "nbformat": 4,
        "nbformat_minor": 5}
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps(nb), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("heading", "MT"), ("paragraph", "body text")]
    assert doc.elements[0].source_locator == {
        "cell_index": 0, "cell_type": "markdown",
        "line": 1, "section_path": "MT"}
    assert doc.elements[1].source_locator == {
        "cell_index": 0, "cell_type": "markdown",
        "line": 3, "section_path": "MT"}


def test_mixed_th_td_row(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th>H</th><td>D</td></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| H | D |\n| --- | --- |"]


def test_ws_only_text_file(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("\n\n  \n\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
