r"""pipeline CJK 内容跨家族：md 结构、
html 与 ipynb（Round 1724）。

新角度：R1723 锁中文句号句界缺失——
**CJK 在 md 标题/列表/表格、html 标题/段
落、ipynb code cell 全部正常**零覆盖：

- **md '# 标题' + '- 项目' + 管道表**：
  heading/list_item/table 全识别（表格
  重建 CJK 原样）
- **html `<h2>章</h2><p>内容</p>`**：
  正常
- **ipynb code cell 中文代码**：code_cell
  段落原样
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_md_cjk_structures(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "# 标题\n\n- 项目一\n- 项目二\n\n"
        "| 列甲 | 列乙 |\n| --- | --- |\n"
        "| 值一 | 值二 |\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "标题", {"level": 1}),
        ("list_item", "项目一",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "项目二",
         {"ordered": False, "marker": "unordered"}),
        ("table",
         "| 列甲 | 列乙 |\n| --- | --- |\n| 值一 | 值二 |",
         {"row_count": 2, "col_count": 2,
          "source": "markdown_pipe_table"})]


def test_html_cjk(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h2>章</h2><p>内容</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "章", {"level": 2}),
        ("paragraph", "内容", {})]


def test_ipynb_cjk_code_cell(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["打印('你好')"],
                   "outputs": []}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "打印('你好')",
         {"kind": "code_cell", "language": ""})]
