r"""pipeline 无值 src、大写实体、脚注原样、
null source 与闭合空格（Round 1711）。

新角度：R1710 锁重复 src——**`<img src>`
无值属性成空 src 图片整个跳过、'&AMP;'
大写命名实体解码、脚注语法原样段落、
ipynb source=null 静默跳 cell**零覆盖：

- **`<img src alt="A">`**：src 空串 → 图
  片跳过，doc None + html_no_content
- **'&AMP; x'**：大写实体解码 '& x'
- **'text[^1]' + '[^1]: note'**：两段原样
  （无脚注支持，定义不单独剔除）
- **markdown cell source=null**：cell 静
  默跳过 → ipynb_no_content
- **'</h2 >'**：闭合标签带空格容忍
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


def test_bare_src_skipped(tmp_path):
    doc, errors = _run(tmp_path, '<img src alt="A">', "d.html")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [w["code"] for w in ws] == ["html_no_content"]


def test_uppercase_entity_decoded(tmp_path):
    doc, errors = _run(tmp_path, "<p>&AMP; x</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "& x")]


def test_footnote_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "text[^1]\n\n[^1]: note\n", "d.md")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "text[^1]"),
        ("paragraph", "[^1]: note")]


def test_ipynb_source_null_skipped(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": None}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [w["code"] for w in ws] == ["ipynb_no_content"]


def test_closing_tag_space(tmp_path):
    doc, errors = _run(tmp_path, "<h2>a</h2 >", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("heading", "a")]
