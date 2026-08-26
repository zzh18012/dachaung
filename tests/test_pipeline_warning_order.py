r"""pipeline 多警告保序：空围栏行号递增、
ipynb 混合警告按胞序（Round 1815）。

新角度：R1814 锁后缀大小写——**三个
空围栏 → 3 条 md_empty_code_block 按
物理行递增（line 3/8/13）；ipynb 未知
胞+空代码胞混合 → 按胞序 unknown
(cell_index 0) 先于 empty (cell_index
1)，各带 details**零覆盖：

- **三围栏**：line 3/8/13 保序
- **ipynb 混合**：胞序 + details 形态
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_three_empty_fences_ordered_lines(
        tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "para\n\n```\n```\n\nmid\n\n"
        "```\n```\n\nend\n\n```\n```\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(w.code, w.reason)
            for w in doc.warnings] == [
        ("md_empty_code_block", "line 3 处的代码块为空"),
        ("md_empty_code_block", "line 8 处的代码块为空"),
        ("md_empty_code_block", "line 13 处的代码块为空")]


def test_ipynb_mixed_warning_cell_order(
        tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "weird", "source": ["x"]},
        {"cell_type": "code", "source": [],
         "outputs": []},
        {"cell_type": "markdown", "source": ["ok"]},
    ], "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(w.code, w.details)
            for w in doc.warnings] == [
        ("ipynb_unknown_cell_type",
         {"cell_index": 0, "cell_type": "weird"}),
        ("ipynb_empty_code_cell",
         {"cell_index": 1})]
