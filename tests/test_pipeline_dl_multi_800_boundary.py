r"""pipeline dl 多项拼接、双空 cell 警告、800
字符边界与标题紧接表格（Round 1701）。

新角度：R1700 锁 md 注释原样——**dl 多项
全拼接、两个空 code cell 各自警告、恰好
800 字符单 chunk 不切、标题后无空行表格
照常、成功路径携带 cell 警告**零覆盖：

- **dt A + dt B + dd C**：单段 'ABC' 全
  拼接
- **两个空 code cell**：两条
  ipynb_empty_code_cell（cell_index 0/1）
  + ipynb_no_content，doc None
- **800 字符无空格 text**：单 chunk 800，
  strategy 'sequential'（边界含 800 不切）
- **'# T' 直接接表格行**：heading 与 table
  都识别（表格不做惰性续行）
- **空 code cell + markdown cell**：doc 有
  'hi'，warnings 携带 cell #0 警告
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


def test_dl_multi_all_merge(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<dl><dt>A</dt><dt>B</dt><dd>C</dd></dl>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "ABC", {})]


def test_ipynb_two_empty_code_cells(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": [],
             "outputs": []},
            {"cell_type": "code", "source": [],
             "outputs": []}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"], w.get("details"))
            for w in ws] == [
        ("ipynb_empty_code_cell",
         "cell #0 是空 code cell", {"cell_index": 0}),
        ("ipynb_empty_code_cell",
         "cell #1 是空 code cell", {"cell_index": 1}),
        ("ipynb_no_content",
         ".ipynb 未提取到任何 element"
         "（空 notebook 或仅含空 cell）", None)]


def test_text_exact_800_one_chunk(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(("x" * 800).encode())
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert len(doc.elements) == 1
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0].text) == 800
    assert doc.chunks[0].metadata["strategy"] == \
        "sequential"


def test_heading_then_table_no_blank(tmp_path):
    doc, errors = _run(
        tmp_path,
        "# T\n| a | b |\n| --- | --- |\n| x | y |\n",
        "d.md")
    assert errors == []
    assert [(e.type, e.metadata)
            for e in doc.elements] == [
        ("heading", {"level": 1}),
        ("table", {"row_count": 2, "col_count": 2,
                   "source": "markdown_pipe_table"})]


def test_ipynb_mixed_empty_and_content(tmp_path):
    p = tmp_path / "c2.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": [],
             "outputs": []},
            {"cell_type": "markdown", "source": ["hi"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "hi")]
    assert [(w.code, w.reason) for w in doc.warnings] == [
        ("ipynb_empty_code_cell",
         "cell #0 是空 code cell")]
