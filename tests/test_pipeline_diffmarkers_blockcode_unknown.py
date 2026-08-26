r"""pipeline 异 marker 列表合并、块级 code、
unknown cell reason 与 emoji 实体（Round 1706）。

新角度：R1705 锁前导零——**'- a\\n\\n* b'
异 marker 列表合 1 chunk、块级 `<code>` 成
普通段落、'custom' cell 的完整 reason 格式、
'&#x1F600;' emoji 解码**零覆盖：

- **'- a\\n\\n* b'**：两个 list_item（不同
  marker），单 chunk 合并
- **`<body><code>sys</code></body>`**：段落
  'sys'（无 code_block kind）
- **cell_type 'custom'**：doc None +
  no_extracted_elements，warnings [
  ipynb_unknown_cell_type（reason
  "cell #0 类型未知: 'custom'"，details
  cell_index/cell_type）、ipynb_no_content]
- **'## T   '**：尾随空格剥除 'T'
- **'&#x1F600;'**：解码 'a 😀 b'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_diff_markers_merge_one_chunk(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\n* b\n", "d.md")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("list_item", "a"), ("list_item", "b")]
    assert len(doc.chunks) == 1


def test_block_code_plain_paragraph(tmp_path):
    doc, errors = _run(
        tmp_path, "<body><code>sys</code></body>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "sys", {})]


def test_unknown_cell_type_reason(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "custom",
                   "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"], w.get("details"))
            for w in ws] == [
        ("ipynb_unknown_cell_type",
         "cell #0 类型未知: 'custom'",
         {"cell_index": 0, "cell_type": "custom"}),
        ("ipynb_no_content",
         ".ipynb 未提取到任何 element"
         "（空 notebook 或仅含空 cell）", None)]


def test_heading_trailing_spaces_stripped(tmp_path):
    doc, errors = _run(tmp_path, "## T   \n", "d.md")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T")]


def test_emoji_hex_entity_decoded(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>a &#x1F600; b</h2>", "d.html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "a 😀 b")]
