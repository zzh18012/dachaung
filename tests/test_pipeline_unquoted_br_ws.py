r"""pipeline 无引号属性、br/ 自闭合、空白
markdown 单元（Round 1665）。

新角度：R1664 锁大写标签——**无引号属性
值、'&lt;br/&gt;' 变体、纯空白 markdown
cell**零覆盖：

- **无引号属性**：'&lt;img src=x.png alt=A&gt;'
  照常 image（alt 'A'）
- **'&lt;br/&gt;'**：与 &lt;br&gt; 一致成单
  空格 'a b'
- **纯空白 md cell**：无元素无专属警告，
  整本 → no_extracted_elements +
  ipynb_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_unquoted_attrs(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<img src=x.png alt=A>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"})]


def test_br_slash_variant(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>a<br/>b</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a b", {})]


def test_ws_only_markdown_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["   \n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors[0].details["warnings"]] == [
        "ipynb_no_content"]
