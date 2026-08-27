r"""app/parsers/ipynb_parser.py 边角测试 - 第十二轮（Round 1461）。

新角度（probe 实证）doc.metadata 摘要化 + 类型透传 + 混合
cell 计数（edges1-11 未碰过）：
- doc.metadata 是**扁平摘要**（ipynb/nbformat/nbformat_minor/
  cell_count/language 五键），notebook 原始 metadata（kernelspec
  对象、language_info、authors、title）**整体丢弃**
- 语言推断**不做 str 强转**：kernelspec.language=42（int）原样
  进 doc.metadata 与每个 code cell 的 element metadata
- 单个 markdown cell 多块结构：heading/paragraph/blockquote/
  list_item 全部解析，locator 保留 cell 内 line（1/2/4/6），
  section_path 栈在 cell 内生效（全部承袭 'H'）
- attachments 字段忽略；cell 的 id 字段（nbformat 4.5）忽略
- cell_count = **len(cells) 含被跳过的 cell**（bad str cell、
  unknown type、空 code 各占一计数），element 只有 1 个
- nbformat 为字符串时 line 103 的 `nbformat < 4` **无类型守卫**
  → 直接 TypeError（非 ParserError）
- element confidence 固定 **0.95**（code 与 markdown cell 同）
"""

from __future__ import annotations

import json

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser

TMP_NAME = "nb_edge12_probe.ipynb"


def _parse(tmp_path, obj, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return IpynbParser().parse(
        p, compute_file_hash(p))


def _nb(cells, metadata=None):
    # adoption 契约 §2 注记（2026-08-27）：补 nbformat_minor（版本字段必填）。
    return {"cells": cells,
            "metadata": metadata or {},
            "nbformat": 4, "nbformat_minor": 5}


# ---------- doc.metadata 摘要化 ----------

def test_metadata_flattened_summary(
        tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x"}],
        {"kernelspec": {"name": "py",
                        "language": "python"},
         "language_info": {"name": "python",
                           "version": "3.12"},
         "authors": [{"name": "z"}],
         "title": "T"}))
    assert doc.metadata == {
        "ipynb": True,
        "nbformat": 4,
        # adoption 契约 §2 注记（2026-08-27）：版本字段必填，
        # _nb helper 现补 nbformat_minor=5（原快照为 None 透传）。
        "nbformat_minor": 5,
        "cell_count": 1,
        "language": "python",
    }


def test_lang_int_passthrough(tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x"}],
        {"kernelspec": {"language": 42}}))
    assert doc.metadata["language"] == 42
    assert doc.elements[
        0].metadata["language"] == 42


# ---------- 单 cell 多块 markdown ----------

def test_md_multiblock_one_cell(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "# H\ntext\n\n> quote\n\n- li"},
    ]))
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "H"),
        ("paragraph", "text"),
        ("paragraph", "quote"),
        ("list_item", "li"),
    ]
    lines = [e.source_locator["line"]
             for e in doc.elements]
    assert lines == [1, 2, 4, 6]
    for e in doc.elements:
        assert e.source_locator[
            "section_path"] == "H"
        assert e.source_locator[
            "cell_index"] == 0


# ---------- 忽略字段 ----------

def test_attachments_ignored(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "txt",
         "attachments": {"a": {
             "image/png": "data"}}},
    ]))
    assert len(doc.elements) == 1
    assert "attachments" not in str(
        doc.elements[0].to_dict())
    assert doc.metadata["cell_count"] == 1


def test_cell_id_ignored(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "code",
         "source": "x", "id": "abc-123"},
    ]))
    assert doc.elements[
        0].source_locator == {
        "cell_index": 0,
        "cell_type": "code",
    }
    assert "abc-123" not in str(
        doc.elements[0].to_dict())


# ---------- cell_count 计数语义 ----------

def test_cell_count_includes_skipped(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        "not a dict",
        {"cell_type": "weird",
         "source": "?"},
        {"cell_type": "code",
         "source": "   "},
        {"cell_type": "code",
         "source": "ok()"},
    ]))
    assert doc.metadata["cell_count"] == 4
    assert [e.content
            for e in doc.elements] == ["ok()"]
    assert [w.code for w in doc.warnings] == [
        "ipynb_bad_cell",
        "ipynb_unknown_cell_type",
        "ipynb_empty_code_cell",
    ]


# ---------- nbformat 类型不守卫 ----------

def test_nbformat_str_rejected(
        tmp_path):
    """adoption 契约 §2（2026-08-27）：nbformat 为字符串 → ipynb_bad_structure。

    原快照此处为未捕获 TypeError，契约修订后为结构化错误。
    """
    p = tmp_path / TMP_NAME
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": "x"}],
        "metadata": {},
        "nbformat": "4",
        "nbformat_minor": 5,
    }), encoding="utf-8")
    with pytest.raises(ParserError) as ei:
        IpynbParser().parse(
            p, compute_file_hash(p))
    assert ei.value.code == "ipynb_bad_structure"


# ---------- confidence ----------

def test_confidence_point95(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "code",
         "source": "x=1"},
        {"cell_type": "markdown",
         "source": "prose"},
    ]))
    assert all(
        e.confidence == 0.95
        for e in doc.elements)
