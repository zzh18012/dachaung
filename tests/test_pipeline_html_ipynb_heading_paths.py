r"""pipeline html/ipynb 标题路径：' > '
同构嵌套与 cell 内生效（Round 1769）。

新角度：R1768 锁 md 路径算法——**html
h2/h3/h1 同建路径（'T > U'、h1 重置）；ipynb
同 cell 内嵌套标题也建路径（line 1/3/5
逐行）——路径算法三家族同构，仅 ipynb
不跨 cell**零覆盖：

- **html 'T/U/x/H/y'**：'T'/'T >
  U'/'H' 与 md 全同
- **ipynb 单 cell '## T\\n\\n### U\\n\\nx'**：
  'T'/'T > U'（cell_index 同 0）
- **ipynb cell1 '### A' + cell2 'x'**：
  cell2 段落无 section_path（栈不跨 cell）
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_html_nested_heading_paths(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<h2>T</h2><h3>U</h3><p>x</p>"
        "<h1>H</h1><p>y</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.source_locator.get("section_path"))
            for e in doc.elements] == [
        "T", "T > U", "T > U", "H", "H"]


def test_ipynb_in_cell_nested_paths(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["## T\n\n### U\n\nx"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.source_locator["cell_index"],
             e.source_locator["line"],
             e.source_locator["section_path"])
            for e in doc.elements] == [
        (0, 1, "T"), (0, 3, "T > U"),
        (0, 5, "T > U")]


def test_ipynb_heading_stack_no_leak(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "markdown",
             "source": ["### A"]},
            {"cell_type": "markdown",
             "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.elements[0].source_locator[
        "section_path"] == "A"
    assert "section_path" not in (
        doc.elements[1].source_locator)
