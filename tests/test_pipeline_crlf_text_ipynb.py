r"""pipeline text CRLF 分段与 ipynb source
内 CRLF 归一（Round 1719）。

新角度：R1718 键引用散文本——**'\\r\\n\\r\\n'
空行分段、ipynb source 字符串内 '\\r\\n'
归一 '\\n'、cell 内 CRLF 标题照常**零覆盖：

- **text 'a\\r\\n\\r\\nb\\r\\n'**：两段
  'a'/'b'（CRLF 空行分段，write_bytes 精确
  写盘）
- **markdown cell ['l1\\r\\n','l2\\r\\n']**：
  段落 'l1\\nl2'（归一 \\n）
- **cell ['# T\\r\\n','para\\r\\n']**：heading
  + paragraph 照常识别
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_text_crlf_paragraph_split(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(b"a\r\n\r\nb\r\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]


def test_ipynb_source_crlf_normalized(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["l1\r\n", "l2\r\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "l1\nl2", {})]


def test_ipynb_md_cell_crlf_heading(tmp_path):
    p = tmp_path / "c2.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["# T\r\n", "para\r\n"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "T", {"level": 1}),
        ("paragraph", "para", {})]
