r"""pipeline ipynb source 变体：字符串源、
胞多余字段忽略、minor 0 记录（Round 1811）。

新角度：R1810 锁无空白 forced——**source
可以是纯字符串（非列表）——'plain
string' 直接成段；cell 的 id/
execution_count/metadata.tags 全忽略
（element metadata 恒 {}）；nbformat_
minor 0 合法并录入 doc.metadata**零
覆盖：

- **字符串 source**：paragraph 'plain
  string'
- **多余字段**：metadata 干净
- **minor 0**：{'nbformat_minor': 0}
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _nb(tmp_path, cells, **extra):
    p = tmp_path / "d.ipynb"
    body = {"cells": cells, "metadata": {},
            "nbformat": 4}
    body.update(extra)
    p.write_text(json.dumps(body), encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="ipynb")


def test_ipynb_string_source(tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": "plain string"}])
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "plain string")]


def test_ipynb_cell_extra_fields_ignored(
        tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "markdown", "source": ["x"],
         "id": "abc-123", "execution_count": 5,
         "metadata": {"tags": ["hi"]}}])
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x", {})]


def test_ipynb_minor_zero_recorded(tmp_path):
    doc, errors = _nb(tmp_path, [
        {"cell_type": "markdown", "source": ["y"]}],
        nbformat_minor=0)
    assert errors == []
    assert doc.metadata == {
        "ipynb": True, "nbformat": 4,
        "nbformat_minor": 0, "cell_count": 1,
        "language": ""}
