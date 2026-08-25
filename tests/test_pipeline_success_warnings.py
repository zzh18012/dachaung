r"""pipeline 成功路径警告序列化（Round 1618）。

新角度：R1617 锁失败路径——**成功但有警告**
（空 code cell 夹在真实单元中间）零覆盖：

- **doc.warnings 非空而 errors 空**：每个空
  code cell 一条 WarningRecord
  （ipynb_empty_code_cell，cell_index 保原始
  索引不重编号）
- **JSON 序列化**：warnings 数组带
  code/reason/details 完整落盘，errors 仍 []
- **cell_count 计所有单元**（含空单元）；
  无 kernelspec → language ''
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _cells(tmp_path, cells):
    p = tmp_path / "m.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    return p


def test_empty_cells_warn_but_succeed(
        tmp_path):
    p = _cells(tmp_path, [
        {"cell_type": "code",
         "source": [], "outputs": []},
        {"cell_type": "code",
         "source": ["x=1"], "outputs": []},
        {"cell_type": "code",
         "source": [], "outputs": []}])
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(w.code, w.details["cell_index"])
            for w in doc.warnings] == [
        ("ipynb_empty_code_cell", 0),
        ("ipynb_empty_code_cell", 2)]
    (el,) = doc.elements
    assert el.source_locator == {
        "cell_index": 1, "cell_type": "code"}
    assert doc.metadata["cell_count"] == 3
    assert doc.metadata["language"] == ""


def test_json_warnings_serialized(tmp_path):
    p = _cells(tmp_path, [
        {"cell_type": "code",
         "source": [], "outputs": []},
        {"cell_type": "code",
         "source": ["x=1"], "outputs": []}])
    out = tmp_path / "m.json"
    doc, errors = process_single(
        p, output_path=out, parser_name="ipynb")
    assert errors == []
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["errors"] == []
    assert data["warnings"] == [{
        "code": "ipynb_empty_code_cell",
        "reason": "cell #0 是空 code cell",
        "details": {"cell_index": 0}}]


def test_clean_success_no_warnings(tmp_path):
    p = tmp_path / "c.md"
    p.write_text("# T\n\nbody\n",
                 encoding="utf-8")
    out = tmp_path / "c.json"
    doc, errors = process_single(
        p, output_path=out,
        parser_name="markdown")
    assert errors == []
    assert doc.warnings == []
    data = json.loads(
        out.read_text(encoding="utf-8"))
    assert data["warnings"] == []
