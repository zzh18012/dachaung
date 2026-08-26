r"""pipeline ipynb 策略同谱：cell 切分、
表隔离与标题拉段（Round 1777）。

新角度：R1776 锁 text 同谱——**ipynb 三
策略与 md/text 全同：code cell 900 CJK
→ 800 forced_char+100；md cell 内表格
→ isolated_table；cell 内 '## T'+'bbb'
→ 'T bbb' sequential**零覆盖：

- **code cell 字×900**：两块切分
- **md cell 表格**：单块 isolated_table
- **md cell 标题+段**：'T bbb'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, cells):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_code_cell_oversize_split(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "code", "source": ["字" * 900]}])
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split",
         "forced_char"),
        (100, "long_paragraph_sentence_split", None)]


def test_cell_table_isolated(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown",
         "source": ["| a | b |\n| --- | --- |\n"
                    "| 1 | 2 |"]}])
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "table"]
    assert doc.chunks[0].metadata["strategy"] == (
        "isolated_table")


def test_cell_heading_pull_sequential(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown",
         "source": ["## T\n\nbbb"]}])
    assert errors == []
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("T bbb", "sequential")]
