r"""pipeline 前置空行、语言尾空格、非标准
分隔行与 raw cell 多行（Round 1717）。

新角度：R1716 锁 cell 列表——**'\\n\\na'
前置空行忽略、'```py ' 尾随空格剥除、
'| -*- |' 非标准分隔行使整块退化段落、
raw cell 多行保留换行**零覆盖：

- **text '\\n\\na\\n'**：单段 'a'
- **'```py '**：language 'py'（尾随空格
  剥除，与 R1681 前导空格对偶）
- **'| -*- | -*- |'**：非表 → 三行并一
  段落（内嵌换行保留）
- **raw cell ['l1\\n','l2\\n']**：段落
  'l1\\nl2' kind 'raw_cell'
- **两个 td 内 h2**：均拍平 '| A | B |'
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


def test_text_leading_blanks(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"\n\na\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a")]


def test_fence_lang_trailing_space(tmp_path):
    doc, errors = _run(tmp_path, "```py \nx\n```\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x",
         {"kind": "code_block", "language": "py"})]


def test_bad_separator_degrades(tmp_path):
    doc, errors = _run(
        tmp_path,
        "| a | b |\n| -*- | -*- |\n| x | y |\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "| a | b |\n| -*- | -*- |\n| x | y |", {})]


def test_raw_cell_multiline(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "raw",
                   "source": ["l1\n", "l2\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "l1\nl2", {"kind": "raw_cell"})]


def test_h2_in_two_tds(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><h2>A</h2></td>"
        "<td><h2>B</h2></td></tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| A | B |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "html_table"})]
