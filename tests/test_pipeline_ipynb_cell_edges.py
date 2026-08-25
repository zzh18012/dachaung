r"""pipeline ipynb 单元格边角（Round 1610）。

新角度：R1609 锁 pre 拆分——**单元格内代码围栏、
字符串形态 source、未知 cell_type**零覆盖：

- **markdown 单元内代码围栏** → paragraph
  {'kind': 'code_block', 'language': 'python'}
  （单元内用完整 markdown 语法）
- **source 为纯字符串**（非列表）→ 正常解析
- **未知 cell_type** → ipynb_unknown_cell_type
  警告（带 cell_index/cell_type details）+
  ipynb_no_content → doc=None
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _nb(tmp_path, cells):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_fence_in_markdown_cell(tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": ["```python\n", "x = 1\n",
                    "```\n"]}])
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x = 1",
         {"kind": "code_block",
          "language": "python"})]


def test_string_source_accepted(tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": "# Str heading"}])
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "Str heading",
         {"level": 1})]


def test_unknown_cell_type(tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "weird",
         "source": ["?"]}])
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert errors[0].details["warnings"] == [
        {"code": "ipynb_unknown_cell_type",
         "reason": "cell #0 类型未知: 'weird'",
         "details": {"cell_index": 0,
                     "cell_type": "weird"}},
        {"code": "ipynb_no_content",
         "reason": ".ipynb 未提取到任何 element"
                   "（空 notebook 或仅含空 cell）"}]
