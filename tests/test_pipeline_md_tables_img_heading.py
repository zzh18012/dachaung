r"""pipeline 连续 md 表、img 破坏标题、
ipynb 缺 source 键（Round 1657）。

新角度：R1656 锁实体/围栏——**空行分隔的
两个 md 表各自 isolated、img 进 h2 破坏标
题、cell 缺 source 静默跳过**零覆盖：

- **两个 md 表**：各 1 元素各 1 块
  （isolated_table ×2，与 html 相邻表一致）
- **img 进 h2**：标题不保——image + 普通
  paragraph 'T'（与 img-in-li 破坏同型）
- **缺 source 键**：该 cell 无元素无警告，
  后续 cell 正常，cell_index 保留原值
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_two_md_tables_isolated(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b |\n| --- | --- |\n\n"
        "| c | d |\n| --- | --- |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("| a | b |\n| --- | --- |", 1,
         "isolated_table"),
        ("| c | d |\n| --- | --- |", 1,
         "isolated_table")]


def test_img_in_heading_breaks(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<h2><img src='x.png' alt='A'> T</h2>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("image", None, {"alt": "A"}),
        ("paragraph", "T", {})]


def test_nb_missing_source_skipped(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown"},
                  {"cell_type": "markdown",
                   "source": ["y\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.warnings == []
    assert [(e.type, e.content, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", "y",
         {"cell_index": 1, "cell_type": "markdown",
          "line": 1})]
