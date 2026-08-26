r"""pipeline 失败不落盘与 warnings 序列化
省键（Round 1770）。

新角度：R1769 锁路径同构——**解析失败
（doc=None）时 output_path 完全不写文
件；成功 JSON 的 warnings 列表里
details=None 的记录整键省略（仅
code/reason）、有 details 的保留**零覆
盖：

- **'##   ' 崩溃 + output_path**：文件
  不存在
- **md 空代码块 JSON**：warnings ==
  [{'code', 'reason'}]（无 details 键）
- **ipynb 空码 cell JSON**：warnings[0]
  含 details {'cell_index': 0}
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single
from app.schema import validate


def test_failure_writes_no_output(tmp_path):
    src = tmp_path / "crash.md"
    src.write_text("##   \n", encoding="utf-8")
    out = tmp_path / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert doc is None
    assert errors[0].code == "unexpected_parser_error"
    assert not out.exists()

    missing = tmp_path / "nope.md"
    out2 = tmp_path / "o2.json"
    doc, errors = process_single(
        missing, output_path=out2, parser_name="markdown")
    assert doc is None
    assert not out2.exists()


def test_warning_details_none_omitted(tmp_path):
    src = tmp_path / "d.md"
    src.write_text("text\n\n```\n```\n", encoding="utf-8")
    out = tmp_path / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="markdown")
    assert errors == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["warnings"] == [{
        "code": "md_empty_code_block",
        "reason": "line 3 处的代码块为空"}]
    validate(data)


def test_warning_details_serialized(tmp_path):
    src = tmp_path / "d.ipynb"
    src.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": []},
            {"cell_type": "markdown",
             "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    out = tmp_path / "o.json"
    doc, errors = process_single(
        src, output_path=out, parser_name="ipynb")
    assert errors == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["warnings"] == [{
        "code": "ipynb_empty_code_cell",
        "reason": "cell #0 是空 code cell",
        "details": {"cell_index": 0}}]
    validate(data)
