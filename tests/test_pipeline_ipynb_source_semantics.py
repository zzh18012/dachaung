r"""pipeline ipynb source 语义：列表拼接
strip、缺键静默与 outputs 忽略（Round 1758）。

新角度：R1757 锁语言优先级——**cell
source = ''.join(items).strip()：['a\\n',
'b\\n'] → 'a\\nb'、'  a  ' → 'a'；source
键缺失或空列表 → 静默跳过（唯一 cell 时
整本 no_extracted_elements，混好 cell 时
无警告成功）；outputs/execution_count 完
全忽略**零覆盖：

- **['a\\n', 'b\\n']**：content 'a\\nb'
- **仅缺 source 的 cell**：(None,
  no_extracted_elements)；+好 cell：
  成功且 warnings []
- **code cell 带 outputs**：只留 source
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, cells):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_source_list_join_and_strip(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown",
         "source": ["a\n", "b\n"]}])
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a\nb"]
    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown", "source": ["  a  "]}])
    assert errors == []
    assert [e.content for e in doc.elements] == ["a"]


def test_missing_source_silent_skip(tmp_path):
    doc, errors = _run(
        tmp_path, [{"cell_type": "markdown"}])
    assert doc is None
    e = errors[0]
    assert e.code == "no_extracted_elements"
    assert e.details["warnings"][0]["code"] == (
        "ipynb_no_content")

    doc, errors = _run(tmp_path, [
        {"cell_type": "markdown", "source": []},
        {"cell_type": "markdown",
         "source": ["good"]}])
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "good"]
    assert doc.warnings == []


def test_outputs_and_execution_ignored(tmp_path):
    doc, errors = _run(tmp_path, [
        {"cell_type": "code", "source": ["x=1"],
         "outputs": [{"text": "1"}],
         "execution_count": 5}])
    assert errors == []
    assert [(e.content, e.metadata)
            for e in doc.elements] == [
        ("x=1", {"kind": "code_cell",
                 "language": ""})]
