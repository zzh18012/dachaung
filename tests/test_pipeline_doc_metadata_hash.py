r"""pipeline doc.metadata 家族形态、内容
派生 id 与扩展名 source_type（Round 1748）。

新角度：R1747 锁 CJK 拼接——**doc.metadata
随家族：html {'html': True}、ipynb 五键
（nbformat/nbformat_minor/cell_count/
language）；source_hash 与 document_id 均
内容派生——同内容不同文件名 id 相同；
document_id = 'doc-'+hash 前 16 位**
零覆盖：

- **html/ipynb**：metadata 形态锁定
- **同内容两文件**：hash 同、id 同；不
  同内容 id 异
- **id 派生**：document_id == 'doc-' +
  source_hash[:16]
- **扩展名**：'.markdown' → 'markdown'、
  '.txt' → 'text'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_family_doc_metadata(tmp_path):
    h = tmp_path / "d.html"
    h.write_text("<p>x</p>", encoding="utf-8")
    doc, errors = process_single(
        h, write_json=False, parser_name="html")
    assert errors == []
    assert doc.metadata == {"html": True}

    n = tmp_path / "d.ipynb"
    n.write_text(json.dumps({
        "cells": [{"cell_type": "markdown",
                   "source": ["x"]}],
        "metadata": {"kernelspec": {"language": "python"}},
        "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8")
    doc, errors = process_single(
        n, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.metadata == {
        "ipynb": True, "nbformat": 4,
        "nbformat_minor": 5, "cell_count": 1,
        "language": "python"}


def test_content_derived_identity(tmp_path):
    a1 = tmp_path / "a1.md"
    a2 = tmp_path / "a2.md"
    b1 = tmp_path / "b1.md"
    a1.write_text("same", encoding="utf-8")
    a2.write_text("same", encoding="utf-8")
    b1.write_text("diff", encoding="utf-8")
    d1, _ = process_single(
        a1, write_json=False, parser_name="markdown")
    d2, _ = process_single(
        a2, write_json=False, parser_name="markdown")
    d3, _ = process_single(
        b1, write_json=False, parser_name="markdown")
    assert d1.source_hash == d2.source_hash
    assert d1.document_id == d2.document_id
    assert d1.source_hash != d3.source_hash
    assert d1.document_id != d3.document_id


def test_document_id_from_hash_prefix(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("x\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.document_id == (
        "doc-" + doc.source_hash[:16])


def test_source_type_by_extension(tmp_path):
    m = tmp_path / "d.markdown"
    m.write_text("x\n", encoding="utf-8")
    doc, errors = process_single(
        m, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.source_type == "markdown"
    t = tmp_path / "d.txt"
    t.write_text("x\n", encoding="utf-8")
    doc, errors = process_single(
        t, write_json=False, parser_name="text")
    assert errors == []
    assert doc.source_type == "text"
