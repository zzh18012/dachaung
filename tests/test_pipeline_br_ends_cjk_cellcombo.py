r"""pipeline br 收尾、标题双 br、CJK 文本与
cell 内标题表格组合（Round 1720）。

新角度：R1719 锁 CRLF 归一——**`<p>a<br>`
末尾 br 无尾随空格、h2 双 br 'a  b' 同 p、
CJK 两段合 1 chunk、同 cell 标题+表格都提
取**零覆盖：

- **`<p>a<br></p>`**：段落 'a'（末尾 br
  不留空格）
- **`<h2>a<br><br>b</h2>`**：'a  b'（双
  br 两空格，同段落行为）
- **'你好\\n\\n世界'**：两段合 1 chunk
- **cell 内 '# T' + 表格行**：heading 与
  table（row_count 1）都提取
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run_html(tmp_path, text):
    p = tmp_path / "d.html"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="html")


def test_br_at_p_end(tmp_path):
    doc, errors = _run_html(tmp_path, "<p>a<br></p>")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a")]


def test_double_br_in_h2(tmp_path):
    doc, errors = _run_html(tmp_path, "<h2>a<br><br>b</h2>")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("heading", "a  b")]


def test_cjk_text_paragraphs(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes("你好\n\n世界\n".encode())
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "你好"), ("paragraph", "世界")]
    assert len(doc.chunks) == 1


def test_cell_heading_table_combo(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["# T\n", "| a | b |\n",
                              "| --- | --- |\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 1}),
        ("table", "| a | b |\n| --- | --- |",
         {"row_count": 1, "col_count": 2,
          "source": "markdown_pipe_table"})]
