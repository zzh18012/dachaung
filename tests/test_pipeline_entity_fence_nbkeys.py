r"""pipeline 单元格实体、围栏内表格惰性、
ipynb 缺键（Round 1656）。

新角度：R1655 锁顶层内联——**td 内实体解
码、code_block 内表格语法惰性、nbformat/
cells 键缺失**零覆盖：

- **td 内 '&amp;amp;'**：解码成 '&' 进单
  元格 '| a & b |'
- **围栏内表格不成表**：管道表语法在
  code_block 内原样保留
- **缺 nbformat 仍解析**（metadata nbformat
  None）；缺 cells → no_extracted_elements
  + ipynb_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_entity_in_cell(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><td>a &amp; b</td></tr>"
        "</table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a & b |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_table_in_fence_inert(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "```\n| a | b |\n| --- | --- |\n```\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         "| a | b |\n| --- | --- |",
         {"kind": "code_block", "language": ""})]


def test_nb_missing_keys(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["x\n"]}],
        "metadata": {}}), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.metadata["nbformat"] is None
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "x")]

    p2 = tmp_path / "e.ipynb"
    p2.write_text(json.dumps({
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc2, errors2 = process_single(
        p2, write_json=False, parser_name="ipynb")
    assert doc2 is None
    assert [e.code for e in errors2] == [
        "no_extracted_elements"]
    assert [w["code"] for w in
            errors2[0].details["warnings"]] == [
        "ipynb_no_content"]
