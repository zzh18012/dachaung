r"""pipeline 合并链跨家族：html 标题链、
html 表格打断与 ipynb 跨 cell 合并
（Round 1738）。

新角度：R1737 锁 md 代码/引用入链——**
合并规则跨家族一致：html 'T bbb'（2
ids）、html 表格同样三块独立、ipynb 两个
markdown cell 的段落合并 'aaa bbb'（2
ids）——cell 边界对分块器不可见**零覆盖：

- **`<h2>T</h2><p>bbb</p>`**：'T bbb'
  （2 ids）——html 标题同样向后拉段
- **html p+表+p**：'aaa' + 表 + 'bbb'
  三块各 1 id；html 表格内容重建为
  markdown 管道文本
- **ipynb 2 cell 'aaa'/'bbb'**：单
  chunk 'aaa bbb'（2 ids）跨 cell 合并
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_html_heading_chain(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h2>T</h2><p>bbb</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T bbb", 2)]


def test_html_table_breaks_chain(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<p>aaa</p><table><tr><th>h1</th><th>h2</th></tr>"
        "<tr><td>v1</td><td>v2</td></tr></table><p>bbb</p>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "paragraph", "table", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa", 1),
        ("| h1 | h2 |\n| --- | --- |\n| v1 | v2 |", 1),
        ("bbb", 1)]


def test_ipynb_cross_cell_merge(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "markdown", "source": ["aaa"]},
            {"cell_type": "markdown", "source": ["bbb"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "aaa"), ("paragraph", "bbb")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa bbb", 2)]
