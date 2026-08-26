r"""pipeline cell 内列表、h2 内 div、无空行
引用打断与嵌套 pre（Round 1716）。

新角度：R1715 锁 1600 不丢——**ipynb
markdown cell 内列表完整语法、h2 内 div
无空格拼接、'para\\n> q' 引用打断段落不
合并、嵌套 pre 全拼接**零覆盖：

- **cell 内 '- a\\n- b'**：两个 list_item
  合 1 chunk
- **`<h2>a<div>d</div>b</h2>`**：heading
  'adb'（div 透明无空格拼接，同 p）
- **'para\\n> q'**：paragraph 'para' +
  blockquote 'q'（无空行引用打断段落，
  不做惰性合并——对比段落间惰性续行）
- **`<pre>outer<pre>inner</pre>tail</pre>`**：
  全拼接单段 preformatted
  'outerinnertail'
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


def test_ipynb_cell_list(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["- a\n", "- b\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"})]
    assert len(doc.chunks) == 1


def test_div_in_h2_merges(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>a<div>d</div>b</h2>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "adb", {"level": 2})]


def test_para_then_bq_no_blank(tmp_path):
    doc, errors = _run(tmp_path, "para\n> q\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "para", {}),
        ("paragraph", "q", {"kind": "blockquote"})]


def test_nested_pre_merges(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<pre>outer<pre>inner</pre>tail</pre>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "outerinnertail",
         {"kind": "preformatted"})]
