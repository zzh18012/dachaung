r"""pipeline 输入形态：ipynb raw cell 有 kind、
CRLF 透明、BOM 不剥破坏标题（Round 1786）。

新角度：R1785 锁内联/注释——**ipynb
'raw' cell 非未知类型：paragraph +
kind='raw_cell' 无警告、照常入合并链
'raw text md ok'；CRLF 输入与 LF 全同
（无 \\r 残留）；UTF-8 BOM 不剥——
'\\ufeff## T' 退化为段落（标题丢失、
section_path None、'\\ufeff## T body'
合并），纯文本段落同样保留 \\ufeff**
零覆盖：

- **raw cell**：paragraph kind
  'raw_cell'、链合并
- **CRLF**：md/txt 段落内容无 \\r
- **BOM**：标题不识别、\\ufeff 入块文
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_ipynb_raw_cell_kind_merges(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "raw", "source": ["raw text"]},
            {"cell_type": "markdown", "source": ["md ok"]},
        ], "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "raw text", {"kind": "raw_cell"}),
        ("paragraph", "md ok", {})]
    assert doc.warnings == []
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("raw text md ok", "sequential")]


def test_crlf_transparent(tmp_path):
    p = tmp_path / "d.md"
    p.write_bytes(b"a\r\n\r\nb\r\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a", "b"]
    p = tmp_path / "e.txt"
    p.write_bytes(b"x\r\n\r\ny\r\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "x", "y"]


def test_bom_not_stripped_breaks_heading(tmp_path):
    p = tmp_path / "d.md"
    p.write_bytes(b"\xef\xbb\xbf## T\r\n\r\nbody\r\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "﻿## T"),
        ("paragraph", "body")]
    assert [(c.text, c.metadata.get("section_path"))
            for c in doc.chunks] == [
        ("﻿## T body", None)]
