r"""pipeline 801 字符切分、中部 hr、td 内
div、nbsp 与 code cell 表格原样（Round 1704）。

新角度：R1703 锁引用无惰性——**801 字符无
空格 800+1 两块、'---' 中部出现丢弃、
`&nbsp;` 解码 \\xa0、code cell 内表格语法
不解析**零覆盖：

- **801 字符 text**：chunk 800 + 1，均
  strategy 'long_paragraph_sentence_split'
- **'a\\n\\n---\\n\\nb'**：hr 丢弃两段，
  合并 1 chunk
- **td 内 `<div>`**：透明，单元格 'd'
- **'a&nbsp;b'**：解码 'a\\xa0b'
- **code cell 含完整表格语法**：单段
  kind 'code_cell' 原样（不解析成 table）
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


def test_text_801_chars_split(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(("x" * 801).encode())
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split"),
        (1, "long_paragraph_sentence_split")]


def test_md_hr_mid_doc_dropped(tmp_path):
    doc, errors = _run(tmp_path, "a\n\n---\n\nb\n", "d.md")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]
    assert len(doc.chunks) == 1


def test_div_in_td_transparent(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td><div>d</div></td></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| d |\n| --- |",
         {"row_count": 1, "col_count": 1,
          "source": "html_table"})]


def test_nbsp_decoded(tmp_path):
    doc, errors = _run(tmp_path, "<p>a&nbsp;b</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a\xa0b")]


def test_code_cell_table_syntax_raw(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["| a | b |\n",
                              "| --- | --- |\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "| a | b |\n| --- | --- |",
         {"kind": "code_cell", "language": ""})]
