r"""pipeline 非fallback家族 JSON 落盘结构（Round 1604）。

新角度：R1603 锁扩展名路由——**write_json=True 落盘
JSON 的完整结构**零覆盖（R1596-1602 全用
write_json=False）：

- **chunk JSON 键**：chunk_id `doc-{hash16}::c0000`、
  text、source_element_ids、metadata
  {strategy, max_chars, char_count}、source_spans
  （逐元素 start/end 偏移）
- **source_hash = 文件字节完整 sha256（64 hex）**，
  document_id = 'doc-' + 前 16 hex；两次运行 JSON
  完全一致（确定性）
- **家族 metadata 怪癖**：md/html/text →
  {"<fmt>": true}；ipynb → 附 nbformat/cell_count/
  language；全部通过 schema validate
"""

from __future__ import annotations

import hashlib
import json

from pathlib import Path

from app.pipeline import process_single
from app.schema import validate


def test_chunk_json_structure(tmp_path):
    p = tmp_path / "a.md"
    p.write_text(
        "# Title\n\n- item\n\n> quote\n",
        encoding="utf-8")
    out = tmp_path / "a.json"
    doc, errors = process_single(
        p, output_path=out, parser_name="markdown")
    assert errors == []
    data = json.loads(
        out.read_text(encoding="utf-8"))

    sha = hashlib.sha256(
        p.read_bytes()).hexdigest()
    assert data["source_hash"] == sha
    assert data["document_id"] == (
        "doc-" + sha[:16])

    (chunk,) = data["chunks"]
    assert chunk["text"] == (
        "Title item quote")
    assert chunk["metadata"] == {
        "strategy": "sequential",
        "max_chars": 800,
        "char_count": 16}
    prefix = "doc-" + sha[:16]
    assert chunk["chunk_id"] == (
        prefix + "::c0000")
    assert chunk["source_element_ids"] == [
        prefix + "::e0000",
        prefix + "::e0001",
        prefix + "::e0002"]
    assert chunk["source_spans"] == [
        {"element_id": prefix + "::e0000",
         "start": 0, "end": 5},
        {"element_id": prefix + "::e0001",
         "start": 0, "end": 4},
        {"element_id": prefix + "::e0002",
         "start": 0, "end": 5}]
    assert validate(data) is None


def test_family_metadata_and_validity(
        tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["x=1"],
                   "outputs": []}],
        "metadata": {"kernelspec": {
            "language": "python"}},
        "nbformat": 4}),
        encoding="utf-8")
    out = tmp_path / "c.json"
    doc, errors = process_single(
        p, output_path=out, parser_name="ipynb")
    assert errors == []
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["source_type"] == "ipynb"
    assert data["metadata"] == {
        "ipynb": True, "nbformat": 4,
        "nbformat_minor": None,
        "cell_count": 1,
        "language": "python"}
    assert data["relations"] == []
    assert data["warnings"] == []
    assert validate(data) is None


def test_run_determinism(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<h1>H</h1><p>P</p>",
        encoding="utf-8")
    o1 = tmp_path / "1.json"
    o2 = tmp_path / "2.json"
    _, e1 = process_single(
        p, output_path=o1, parser_name="html")
    _, e2 = process_single(
        p, output_path=o2, parser_name="html")
    assert e1 == [] and e2 == []
    assert (o1.read_bytes()
            == o2.read_bytes())
    data = json.loads(
        o1.read_text(encoding="utf-8"))
    assert data["source_type"] == "html"
    assert data["metadata"] == {
        "html": True}
