r"""pipeline 顶层内联标签、td 内 br、ipynb
单元格表格（Round 1655）。

新角度：R1654 锁列表合并——**顶层裸内联
标签、单元格内 br 无空格、ipynb cell 完整
md 表格语法**零覆盖：

- **顶层 '&lt;b&gt;bold&lt;/b&gt; tail'**：
  内联剥除成 paragraph 'bold tail'
- **td 内 br 无贡献**：'a&lt;br&gt;b' 成
  'ab'（对照 p 内 br → 单空格）
- **ipynb cell 表格**：markdown 单元里管道
  表照常成 table，locator 指向 cell
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_inline_tags_top_level(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<b>bold</b> tail", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "bold tail", {})]


def test_td_br_no_space(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td>a<br>b</td></tr></table>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| ab |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_nb_cell_pipe_table(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["| a | b |\n",
                              "| --- | --- |\n",
                              "| x | y |\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.source_locator)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |\n"
                  "| x | y |",
         {"cell_index": 0, "cell_type": "markdown",
          "line": 1})]
