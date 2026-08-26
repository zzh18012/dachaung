r"""pipeline md 注释原样、li 内 b 剥离、
script 剔除与 hr-only cell（Round 1700）。

新角度：R1699 锁次行 th——**md 中 HTML 注释
不剔除原样并段（对比 html 剔除）、li 内
<b> 剥离（对比链接保留）、空 li 丢弃、
script/style 剔除、hr-only markdown cell
→ ipynb_no_content**零覆盖：

- **'<!-- c -->\\np'**：注释原样并入段落，
  内嵌换行保留（惰性续行）
- **li 内 `<b>`**：剥离 'a bold b'（链接
  则原样，R1653）
- **`<li></li>`**：空项丢弃，仅剩 'x'
- **`<script>`/`<style>`**：内容整体剔除
- **text 'a\\n\\nb'**：两段一个 chunk
- **markdown cell 只有 '---'**：hr 丢弃无
  element，doc None + ipynb_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    parser = ("html" if name.endswith("html")
              else "text" if name.endswith("txt")
              else "markdown")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_md_html_comment_raw(tmp_path):
    doc, errors = _run(tmp_path, "<!-- c -->\np\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "<!-- c -->\np", {})]


def test_b_stripped_in_li(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<ul><li>a <b>bold</b> b</li></ul>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a bold b",
         {"ordered": False, "marker": "unordered"})]


def test_empty_li_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "<ul><li></li><li>x</li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "x")]


def test_script_style_dropped(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<script>var x=1;</script>"
        "<style>.a{}</style><p>t</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "t")]


def test_text_two_para_one_chunk(tmp_path):
    doc, errors = _run(tmp_path, "a\n\nb\n", "d.txt")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]
    assert len(doc.chunks) == 1


def test_ipynb_hr_only_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["---\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("ipynb_no_content",
         ".ipynb 未提取到任何 element"
         "（空 notebook 或仅含空 cell）")]
