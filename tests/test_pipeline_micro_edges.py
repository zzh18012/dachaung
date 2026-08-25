r"""pipeline pre>code、md 硬换行、html 嵌套
引用、ipynb 字符串 code（Round 1652）。

新角度：R1651 锁引用内围栏——**pre 内 code
透明、行尾双空格保留、嵌套引用单层化、
code 单元字符串 source**零覆盖：

- **'&lt;pre&gt;&lt;code&gt;'**：code 标签
  透明，仍 kind 'preformatted'
- **硬换行空格保留**：'a  \\nb' 行尾两空格
  不剥（strip 只作用于元素首尾）
- **html 嵌套 blockquote**：单层化成单个
  blockquote 段；code 单元字符串 source
  'print(9)' 照常接受
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _html(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def _md(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_pre_code_transparent(tmp_path):
    doc = _html(
        tmp_path, "<pre><code>x = 1</code></pre>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x = 1",
         {"kind": "preformatted"})]


def test_hard_break_spaces_kept(tmp_path):
    doc = _md(tmp_path, "a  \nb\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a  \nb", {})]


def test_nested_bq_and_string_code(tmp_path):
    doc = _html(
        tmp_path,
        "<blockquote><blockquote>deep"
        "</blockquote></blockquote>")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "deep",
         {"kind": "blockquote"})]

    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": "print(9)",
                   "outputs": []}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc2, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.source_locator)
            for e in doc2.elements] == [
        ("paragraph", "print(9)",
         {"cell_index": 0, "cell_type": "code"})]
