r"""app/parsers/ipynb_parser.py 边角测试 - 第十一轮（Round 1457）。

新角度（probe 实证）source 归一 + 语言推断 + cell 交互
（edges1-10 未碰过）：
- source 列表**逐项 str() 强转**：[1, "a", None, 2.5] →
  '1aNone2.5'；source 缺失 → '' → ipynb_empty_code_cell
- 语言推断三级回退：kernelspec.language > kernelspec.name
  > language_info.name（'python'/'ir'/'julia' 三路实证）
- nbformat 键**缺失被容忍**（doc.metadata nbformat=None）
- markdown cell 的 section_path **逐 cell 隔离**：cell 0 的
  '# A' 不影响 cell 1 的段落（无 section_path）
- markdown 空代码块告警**透传**且加前缀 'cell #0
  (markdown):'，details 合并 cell_index
- 未知 cell_type / 非 dict cell：跳过 + 各自告警，
  element_id **重新连续编号**
- 空 code cell 告警 vs 空 raw cell **静默跳过**（不对称）
- markdown 表格/图片 cell：类型与 resource_path 保留，
  locator 带 cell 信息
"""

from __future__ import annotations

import json

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser

TMP_NAME = "nb_edge11_probe.ipynb"


def _parse(tmp_path, obj, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return IpynbParser().parse(
        p, compute_file_hash(p))


def _nb(cells, metadata=None, **extra):
    d = {"cells": cells,
         "metadata": metadata or {},
         "nbformat": 4,
         "nbformat_minor": 5}
    d.update(extra)
    return d


# ---------- source 归一 ----------

# adoption 契约 §5 注记（2026-08-27）：source 非法（list 含非 str 项）→ 跳过 cell + ipynb_bad_cell。
def test_source_list_coercion(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "code",
         "source": [1, "a", None, 2.5]},
    ]))
    assert doc.elements == []
    assert [w.code for w in doc.warnings] == [
        "ipynb_bad_cell", "ipynb_no_content"]


def test_source_missing_empty_warn(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "code"},
    ]))
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["ipynb_bad_cell",
            "ipynb_no_content"]


# ---------- 语言推断 ----------

def test_lang_ks_language_wins(
        tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x=1"}],
        {"kernelspec": {
            "language": "python",
            "name": "py3"}}))
    assert doc.metadata["language"] \
        == "python"
    assert doc.elements[
        0].metadata["language"] == "python"


def test_lang_ks_name_fallback(
        tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x=1"}],
        {"kernelspec": {"name": "ir"}}))
    assert doc.metadata["language"] == "ir"


def test_lang_language_info(
        tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x=1"}],
        {"language_info": {
            "name": "julia"}}))
    assert doc.metadata["language"] \
        == "julia"


# ---------- nbformat 缺失 ----------

def test_nbformat_missing_rejected(
        tmp_path):
    """adoption 契约 §2（2026-08-27）：版本字段必填 → ipynb_bad_structure。"""
    with pytest.raises(ParserError) as ei:
        _parse(tmp_path, {
            "cells": [{"cell_type": "code",
                       "source": "x=1"}],
            "metadata": {},
        })
    assert ei.value.code == "ipynb_bad_structure"


# ---------- section_path 隔离 ----------

def test_md_section_per_cell(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "# A\nintro"},
        {"cell_type": "markdown",
         "source": "next cell text"},
    ]))
    assert doc.elements[
        0].source_locator["section_path"] \
        == "A"
    assert doc.elements[
        1].source_locator["section_path"] \
        == "A"
    assert "section_path" not in \
        doc.elements[2].source_locator


# ---------- 告警透传 ----------

def test_md_warning_prefixed(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "```\n```\n"},
    ]))
    w = doc.warnings[0]
    assert w.code == "md_empty_code_block"
    assert w.reason.startswith(
        "cell #0 (markdown):")
    assert w.details == {
        "cell_index": 0}


# ---------- 未知 / 坏 cell ----------

def test_unknown_cell_type_warn(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "weird",
         "source": "???"},
        {"cell_type": "code",
         "source": "ok()"},
    ]))
    assert [e.content
            for e in doc.elements] == ["ok()"]
    assert doc.elements[
        0].element_id.endswith("e0000")
    w = doc.warnings[0]
    assert w.code == \
        "ipynb_unknown_cell_type"
    assert w.details == {
        "cell_index": 0,
        "cell_type": "weird"}


def test_bad_cell_skipped(tmp_path):
    doc = _parse(tmp_path, _nb([
        "not a dict",
        {"cell_type": "raw",
         "source": "raw text"},
    ]))
    assert [e.content
            for e in doc.elements] == \
        ["raw text"]
    assert doc.elements[
        0].source_locator["cell_index"] == 1
    assert doc.warnings[
        0].code == "ipynb_bad_cell"


# ---------- 空 cell 不对称 ----------

def test_empty_raw_silent(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "code",
         "source": "x=1"},
        {"cell_type": "raw",
         "source": "   "},
    ]))
    assert len(doc.elements) == 1
    assert [w.code for w in doc.warnings] \
        == []


# ---------- markdown 子元素 ----------

def test_md_table_cell(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "| a | b |\n"
                   "| --- | --- |\n"
                   "| 1 | 2 |"},
    ]))
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata["row_count"] == 2
    assert e.source_locator == {
        "cell_index": 0,
        "cell_type": "markdown",
        "line": 1,
    }


def test_md_image_cell(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "![alt](img.png)"},
    ]))
    e = doc.elements[0]
    assert e.type == "image"
    assert e.resource_path == "img.png"
    assert e.metadata["alt"] == "alt"
    assert e.source_locator == {
        "cell_index": 0,
        "cell_type": "markdown",
        "line": 1,
    }
