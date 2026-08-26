r"""pipeline 参差表格补齐、md 图标题泄入
resource_path、level 跨家族（Round 1788）。

新角度：R1787 锁 level 元数据——**行比
表头多列：表头补空 '| a | b |  |'、
col_count 取最大 3；行比表头少列：'| 1 |
|  |' 右补空；md 图 ![alt](url "tip") 的
resource_path 原样含 ' "tip"'（标题不剥）；
html <h2> 与 ipynb ### 同给
{'level': N}**零覆盖：

- **多列行**：'| a | b |  |' 头补齐
- **少列行**：'| 1 |  |  |' 右补空
- **图 resource_path**：'http://x/y.png
  "tip"' 原样
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_ragged_table_pads_to_max_cols(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b |\n| --- | --- |\n| 1 | 2 | 3 |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "table",
        "| a | b |  |\n| --- | --- | --- |\n"
        "| 1 | 2 | 3 |",
        {"row_count": 2, "col_count": 3,
         "source": "markdown_pipe_table"})]


def test_short_row_pads_empty_cells(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b | c |\n| --- | --- | --- |\n"
        "| 1 |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "table",
        "| a | b | c |\n| --- | --- | --- |\n"
        "| 1 |  |  |",
        {"row_count": 2, "col_count": 3,
         "source": "markdown_pipe_table"})]


def test_md_image_title_in_resource_path(tmp_path):
    p = tmp_path / "d.md"
    p.write_text('![alt text](http://x/y.png "tip")\n',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    e = doc.elements[0]
    assert (e.type, e.content, e.metadata) == (
        "image", None, {"alt": "alt text"})
    assert e.resource_path == 'http://x/y.png "tip"'
    assert e.confidence == 0.95


def test_heading_levels_cross_family(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h2>T</h2><p>b</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert doc.elements[0].metadata == {"level": 2}
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "markdown",
         "source": ["### H\n", "text"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.elements[0].metadata == {"level": 3}
