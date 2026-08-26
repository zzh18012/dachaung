r"""pipeline 前导零列表、nbsp 空格、cell 内
围栏、p 内 div 与表头列数优先（Round 1705）。

新角度：R1704 锁 801 切分——**'01.' 前导零
照常 ordered、纯 '&nbsp;' 单元格成空占位、
markdown cell 内完整围栏语法、p 内 div 无
空格拼接、2 表头 3 分隔以表头为准**零覆盖：

- **'01. item'**：ordered list_item 照常
- **td 仅 '&nbsp;'**：\\xa0 解码后按空白
  处理，成空占位 '|  |'
- **cell 内 '```py' 围栏**：code_block
  段落 language 'py'
- **`<p>a<div>d</div>b</p>`**：div 透明
  且三段无空格拼接 'adb'
- **表头 2 列 + 分隔 3 列**：col_count 2，
  分隔行截断 '| --- | --- |'
- **html bq 内 `<img>`**：引用透明，image
  + 段落 'q'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_leading_zeros_ordered(tmp_path):
    doc, errors = _run(tmp_path, "01. item\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "item",
         {"ordered": True, "marker": "ordered"})]


def test_td_nbsp_only_empty_placeholder(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td>&nbsp;</td><td>x</td>"
        "</tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "|  | x |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "html_table"})]


def test_fence_in_md_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["```py\n", "x = 1\n",
                              "```\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x = 1",
         {"kind": "code_block", "language": "py"})]


def test_div_in_p_merges_no_space(tmp_path):
    doc, errors = _run(
        tmp_path, "<p>a<div>d</div>b</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "adb", {})]


def test_2header_3sep_header_wins(tmp_path):
    doc, errors = _run(
        tmp_path,
        "| a | b |\n| --- | --- | --- |\n| x | y |\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a | b |\n| --- | --- |\n| x | y |",
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_html_bq_img_transparent(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<blockquote><img src="i.png" alt="A">'
        "<p>q</p></blockquote>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"}),
        ("paragraph", "q", {})]
