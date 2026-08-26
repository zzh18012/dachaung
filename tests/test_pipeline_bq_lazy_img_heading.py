r"""pipeline 引用无惰性续行、img 打断标题、
cell 内引用与 td 内列表（Round 1703）。

新角度：R1702 锁 li 内 h2——**'> a\\nb' 引
用不做惰性续行（对比段落续行合并）、img 打
断 h2 成三段、ipynb cell 内 '> q' 完整 md
语法**零覆盖：

- **'> a\\nb'**：blockquote 'a' + 独立
  paragraph 'b'（'b' 不并入引用）
- **`<h2>T <img> tail</h2>`**：拆 heading
  'T' + image + paragraph 'tail'
- **'- a\\n# H'**：list_item 与 heading 都
  正常识别
- **ipynb markdown cell '> q\\n'**：段落
  'q'、kind 'blockquote'
- **td 内 `<ul>`**：拍平成单元格文本 'i'
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


def test_bq_no_lazy_continuation(tmp_path):
    doc, errors = _run(tmp_path, "> a\nb\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("paragraph", "b", {})]


def test_img_breaks_heading(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<h2>T <img src="i.png" alt="A"> tail</h2>',
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 2}),
        ("image", None, {"alt": "A"}),
        ("paragraph", "tail", {})]


def test_heading_interrupts_list(tmp_path):
    doc, errors = _run(tmp_path, "- a\n# H\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("heading", "H", {"level": 1})]


def test_bq_in_ipynb_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["> q\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "q", {"kind": "blockquote"})]


def test_ul_in_td_flattens(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><ul><li>i</li></ul></td>"
        "</tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| i |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]
