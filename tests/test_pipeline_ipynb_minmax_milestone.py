r"""pipeline ipynb 代码胞句界/raw 胞切分、
max_chars=32 极限拉取与表豁免（Round 1800）。

新角度：R1799 锁 bq/pre 隔离——**ipynb
code cell 带句号 1007 → 723+283（与 md
围栏同用句界）；raw cell 字×900 →
800+100 forced；max_chars=32 极限：H30
+'- b' → 恰 32 合并（2 ids）；33 字表
仍单块 isolated_table（豁免与 800 无
关）**零覆盖：

- **code cell 句界**：723+283
- **raw cell 900**：800+100
- **H30+b@32**：单块 32 合并
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _sent():
    return " ".join(
        "S%d. %s" % (i, " ".join(f"w{i}_{j}" for j in range(25)))
        for i in range(7))


def test_ipynb_code_cell_sentence_split(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "code", "source": [_sent()]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(len(c.text),
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (723, None), (283, None)]


def test_ipynb_raw_cell_oversize_split(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "raw", "source": ["字" * 900]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (800, "long_paragraph_sentence_split"),
        (100, "long_paragraph_sentence_split")]


def test_pull_at_min_maxchars(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## " + "H" * 30 + "\n\n- b\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars=32)
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        (32, 2, "sequential")]


def test_table_exempt_at_min_maxchars(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "| a | b |\n| --- | --- |\n| 1 | 2 |\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown",
        max_chars=32)
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (33, "isolated_table")]
