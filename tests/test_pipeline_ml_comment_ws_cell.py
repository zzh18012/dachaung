r"""pipeline 跨行注释与空白 code 单元
（Round 1689）。

新角度：R1688 锁反斜杠——**多行 HTML 注释
整体丢弃、纯空白 code cell 同样触发
ipynb_empty_code_cell**零覆盖：

- **跨行注释**：'&lt;!-- multi\\nline
  --&gt;' 整块丢弃，后续段落照常
- **'   ' code cell**：空警告按空白也算
  空（cell_index 0 details）+ ipynb_no_
  content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_multiline_comment_dropped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<!-- multi\nline\ncomment --><p>x</p>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]


def test_ws_code_cell_warns_empty(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["   "],
                   "outputs": []}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [w["code"] for w in ws] == [
        "ipynb_empty_code_cell", "ipynb_no_content"]
    assert ws[0]["details"] == {"cell_index": 0}
