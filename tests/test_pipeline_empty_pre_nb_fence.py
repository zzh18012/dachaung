r"""pipeline 空 pre 静默丢弃与 ipynb
单元内空围栏警告（Round 1691）。

新角度：R1690 锁 md 空围栏——**html 空
pre 无警告直接丢、markdown cell 内空围栏
的警告带 cell 前缀穿透到 notebook 层**零
覆盖：

- **空 pre**：'<pre></pre><p>x</p>' → 段落
  'x' 照常，errors 空，无任何警告（对比
  md 围栏空块会告 md_empty_code_block）
- **ipynb md cell 空围栏**：cell source
  ['```\\n', '```\\n'] → doc None +
  no_extracted_elements，nested warnings
  依次为 md_empty_code_block（reason 带
  'cell #0 (markdown): ' 前缀、行号 1）
  与 ipynb_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_empty_pre_dropped_silently(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<pre></pre><p>x</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]
    assert doc.warnings == []


def test_empty_fence_in_nb_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["```\n", "```\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("md_empty_code_block",
         "cell #0 (markdown): line 1 处的代码块为空"),
        ("ipynb_no_content",
         ".ipynb 未提取到任何 element"
         "（空 notebook 或仅含空 cell）")]
