r"""pipeline img 字段、text 尾空格保留、
nbformat 3 不支持与 td 多项拼接（Round 1707）。

新角度：R1706 锁 unknown cell——**nbformat=3
触发错误级 ipynb_unsupported_version（新错误
码）、img title 属性丢弃、text 行尾空格原样
保留、td 内多个 li 无空格拼接**零覆盖：

- **`<img src alt title>`**：content None、
  resource_path 'pic.png'、metadata 仅 alt
  （title 丢弃）
- **text 'a   \\nb  '**：行尾空格原样保留
  （'a   \\nb'，不做 strip）
- **nbformat 3**：错误 ipynb_unsupported_
  version '仅支持 nbformat ≥ 4，得到
  nbformat=3'（details path/nbformat，
  非嵌套 warning）
- **td 内两个 li**：无空格拼接 'ij' 单元格
- **'- a | b'**：list_item 原样（管道不切）
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


def test_img_full_fields(tmp_path):
    doc, errors = _run(
        tmp_path,
        '<img src="pic.png" alt="A" title="T">',
        "d.html")
    assert errors == []
    img = doc.elements[0]
    assert (img.type, img.content, img.resource_path) == \
        ("image", None, "pic.png")
    assert img.metadata == {"alt": "A"}


def test_text_trailing_spaces_preserved(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"a   \nb  \n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a   \nb")]


def test_ipynb_nbformat3_unsupported(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["x"]}],
        "metadata": {}, "nbformat": 3}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert len(errors) == 1
    assert errors[0].code == "ipynb_unsupported_version"
    assert errors[0].message == \
        "仅支持 nbformat ≥ 4，得到 nbformat=3"
    assert errors[0].details["nbformat"] == 3


def test_multi_li_in_td_concat(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><ul><li>i</li><li>j</li>"
        "</ul></td></tr></table>", "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| ij |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_list_item_pipe_raw(tmp_path):
    doc, errors = _run(tmp_path, "- a | b\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a | b",
         {"ordered": False, "marker": "unordered"})]
