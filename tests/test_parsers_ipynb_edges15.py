r"""app/parsers/ipynb_parser.py 边角测试 - 第十五轮（Round 1482）。

新角度（probe 实证）metadata 透传不校验 + BOM/嵌套经
cell 通道（edges1-14 未碰过；nbformat 数值变体已由
edges14 锁、嵌套降级已由 md edges11 锁 md 通道，本轮锁
ipynb 通道传播）：
- **nbformat_minor 字符串透传**：'5' 不校验不转 int，
  metadata.nbformat_minor == '5'
- **kernelspec.language 数值透传**：42 直接进 element
  metadata.language 与 doc.metadata['language']（无类型
  强转）
- **markdown cell 带 BOM**：'\\ufeff# heading' 不成标题
  → 单 paragraph 字面保留
- **markdown cell 嵌套 tab 列表降级**：经 cell 通道同样
  '- tabbed' 成 paragraph（line 2），外层 list_item 正常
- **坏 cell 在前好 cell 在后**：warning cell #0 + element
  cell_index=1 共存、cell_count=2（计数含坏 cell）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser


def _nb(tmp_path, name, cells, meta=None,
        **kw):
    d = {"nbformat": 4,
         "nbformat_minor": 5,
         "metadata": meta or {},
         "cells": cells}
    d.update(kw)
    p = tmp_path / name
    p.write_text(json.dumps(d),
                 encoding="utf-8")
    return IpynbParser().parse(
        p, compute_file_hash(p))


def _code(source):
    return {"cell_type": "code",
            "source": source,
            "metadata": {},
            "outputs": [],
            "execution_count": None}


def _md(source):
    return {"cell_type": "markdown",
            "source": source,
            "metadata": {}}


# ---------- metadata 透传 ----------

def test_nbformat_minor_string_rejected(
        tmp_path):
    """adoption 契约 §2（2026-08-27）：nbformat_minor 为字符串 → ipynb_bad_structure。"""
    with pytest.raises(ParserError) as ei:
        _nb(
            tmp_path, "ms.ipynb",
            [_code("x=1")],
            nbformat_minor="5")
    assert ei.value.code == "ipynb_bad_structure"


def test_kernel_language_numeric_passthrough(
        tmp_path):
    doc = _nb(
        tmp_path, "ln.ipynb",
        [_code("x=1")],
        meta={"kernelspec": {
            "language": 42}})
    assert doc.metadata["language"] == 42
    assert doc.elements[0].metadata[
        "language"] == 42


# ---------- markdown cell 通道 ----------

def test_md_cell_bom_kills_heading(tmp_path):
    doc = _nb(
        tmp_path, "bom.ipynb",
        [_md("﻿# heading\nbody")])
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "﻿# heading\nbody"),
    ]
    assert doc.elements[0].source_locator == {
        "cell_index": 0,
        "cell_type": "markdown",
        "line": 1,
    }


def test_md_cell_tab_nested_demoted(
        tmp_path):
    doc = _nb(
        tmp_path, "tn.ipynb",
        [_md("- top\n\t- tabbed\n")])
    assert [(e.type, e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("list_item", "top", 1),
        ("paragraph", "- tabbed", 2),
    ]


# ---------- 坏 cell 混排 ----------

def test_bad_cell_then_good_cell(tmp_path):
    doc = _nb(
        tmp_path, "bg.ipynb",
        ["not-a-dict", _code("good")])
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "good"),
    ]
    assert doc.elements[
        0].source_locator["cell_index"] \
        == 1
    assert len(doc.warnings) == 1
    assert doc.warnings[0].code == \
        "ipynb_bad_cell"
    assert doc.warnings[0].details == {
        "cell_index": 0}
    assert doc.metadata["cell_count"] \
        == 2
