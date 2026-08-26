r"""pipeline 围栏长度不敏感、星加 marker、
raw cell 与超长行分块（Round 1698）。

新角度：R1697 锁闭合类型匹配——**'```' 可
闭合 '````'（长度不敏感，与 CommonMark 相
反）、ipynb raw cell 正常提取非 unknown、
1200 字符长行 799+399 两块 whitespace 边
界**零覆盖：

- **'````' 由 '```' 闭合**：code 'code' +
  paragraph 'more' + 未闭合 '````' 吞
  'tail'
- **'* item'/'+ item'**：marker 均成
  list_item
- **raw cell**：paragraph 'x'、kind
  'raw_cell'、locator cell_type 'raw'
  （非 ipynb_unknown_cell_type）
- **1200 字符 text**：2 chunks（799/399），
  首块 metadata 带 split_boundary_after
  'whitespace'
- **`<a>` 包 `<h2>`**：a 透明，heading 照常
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_four_backtick_closed_by_three(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("````\ncode\n```\nmore\n````\ntail\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": ""}),
        ("paragraph", "more", {}),
        ("paragraph", "tail",
         {"kind": "code_block", "language": ""})]


def test_star_plus_markers(tmp_path):
    for marker in ("*", "+"):
        p = tmp_path / "d.md"
        p.write_text(f"{marker} item\n", encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False, parser_name="markdown")
        assert errors == []
        assert [(e.type, e.content, e.metadata)
                for e in doc.elements] == [
            ("list_item", "item",
             {"ordered": False, "marker": "unordered"})]


def test_ipynb_raw_cell_extracted(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "raw",
                   "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {"kind": "raw_cell"})]
    assert doc.elements[0].source_locator == {
        "cell_index": 0, "cell_type": "raw"}


def test_long_text_line_split(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("w " * 600, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert len(doc.chunks) == 2
    assert [c.metadata["char_count"] for c in doc.chunks] == [
        799, 399]
    assert doc.chunks[0].metadata[
        "split_boundary_after"] == "whitespace"
    assert doc.chunks[0].metadata["strategy"] == \
        "long_paragraph_sentence_split"


def test_a_wrapped_heading(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<a href="u"><h2>x</h2></a>',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "x", {"level": 2})]
