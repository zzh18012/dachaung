r"""app/parsers/ipynb_parser.py 边角测试 - 第十四轮（Round 1474）。

新角度（probe 实证）source 类型强转 + nbformat 数值变体 +
子 element 定位传播（edges1-13 未碰过；edges2 单元级已锁
_extract_kernel_language 回退链与弱断言嵌套 list，本轮走 e2e
精确锁，避开）：
- **source list 含非字符串**：str() 逐项强转拼接——
  ["print(", 42, ")\n", 3.5, None, True] → 'print(42)\n3.5NoneTrue'
- **source 是 dict**：_cell_source_to_text 落 else → ""，
  code cell 成空 → ipynb_empty_code_cell + ipynb_no_content
  双告警、零 element
- **nbformat 浮点 4.5**：4.5 >= 4 放行，metadata.nbformat
  原样存浮点 4.5（不作整型归一）
- **nbformat 缺失 + minor 在场**：nbformat None 放行
  （None is not None 短路），metadata nbformat=None /
  nbformat_minor=2 共存
- **markdown 子告警前缀**：空围栏 → md_empty_code_block 的
  reason 带 'cell #0 (markdown): ' 前缀、details 注入
  cell_index=0（warning 传播链）
- **markdown 表格子 element**：type=table 带 cell_index/
  cell_type='markdown'/line=1，row_count/col_count 进 metadata
- **raw cell list source**：['line1\n', 'line2'] 拼接
  'line1\nline2'，kind=raw_cell
- **code cell 内部换行保留**：strip 只削两端，'a = 1\nb =
  2\n\n# comment' 原样（含空行）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.base import ParserError
from app.parsers.ipynb_parser import IpynbParser


def _nb(tmp_path, name, cells, meta=None, **kw):
    d = {"nbformat": 4, "nbformat_minor": 5,
         "metadata": meta or {}, "cells": cells}
    d.update(kw)
    p = tmp_path / name
    p.write_text(json.dumps(d), encoding="utf-8")
    return IpynbParser().parse(p, compute_file_hash(p))


def _code(source):
    return {"cell_type": "code", "source": source,
            "metadata": {}, "outputs": [],
            "execution_count": 1}


def _md(source):
    return {"cell_type": "markdown", "source": source,
            "metadata": {}}


# ---------- source 类型强转 ----------

# adoption 契约 §5 注记（2026-08-27）：source 非法（list 含非 str 项）→ 跳过 cell + ipynb_bad_cell。
def test_nonstr_source_list_coerced(tmp_path):
    doc = _nb(
        tmp_path, "coerce.ipynb",
        [_code(["print(", 42, ")\n", 3.5, None, True])])
    assert doc.elements == []
    assert [w.code for w in doc.warnings] == [
        "ipynb_bad_cell", "ipynb_no_content"]


def test_source_dict_becomes_empty(tmp_path):
    doc = _nb(
        tmp_path, "sdict.ipynb",
        [_code({"lines": ["x"]})])
    assert doc.elements == []
    assert [w.code for w in doc.warnings] == [
        "ipynb_bad_cell",
        "ipynb_no_content",
    ]


# ---------- nbformat 数值变体 ----------

def test_nbformat_float_4_5_rejected(tmp_path):
    """adoption 契约 §2（2026-08-27）：nbformat 必须为整数 → ipynb_bad_structure。"""
    with pytest.raises(ParserError) as ei:
        _nb(
            tmp_path, "f45.ipynb", [_code("x=1")],
            nbformat=4.5)
    assert ei.value.code == "ipynb_bad_structure"


def test_minor_without_major_rejected(tmp_path):
    """adoption 契约 §2（2026-08-27）：nbformat=None → ipynb_bad_structure。"""
    with pytest.raises(ParserError) as ei:
        _nb(
            tmp_path, "nomin.ipynb", [_code("x=1")],
            nbformat=None, nbformat_minor=2)
    assert ei.value.code == "ipynb_bad_structure"


# ---------- markdown 子结果传播 ----------

def test_md_empty_fence_warning_prefix(tmp_path):
    doc = _nb(
        tmp_path, "fp.ipynb", [_md("```\n```\n")])
    w = doc.warnings[0]
    assert w.code == "md_empty_code_block"
    assert w.reason.startswith(
        "cell #0 (markdown): ")
    assert w.details["cell_index"] == 0
    assert doc.elements == []


def test_md_table_sub_locator(tmp_path):
    doc = _nb(
        tmp_path, "tbl.ipynb",
        [_md("| a | b |\n| --- | --- |\n"
             "| 1 | 2 |\n")])
    e = doc.elements[0]
    assert e.type == "table"
    assert e.source_locator == {
        "cell_index": 0,
        "cell_type": "markdown",
        "line": 1,
    }
    assert e.metadata["row_count"] == 2
    assert e.metadata["col_count"] == 2


# ---------- raw / code 源形态 ----------

def test_raw_list_source_concat(tmp_path):
    doc = _nb(
        tmp_path, "raw.ipynb",
        [{"cell_type": "raw",
          "source": ["line1\n", "line2"],
          "metadata": {}}])
    e = doc.elements[0]
    assert e.content == "line1\nline2"
    assert e.metadata["kind"] == "raw_cell"
    assert e.source_locator["cell_type"] == "raw"


def test_code_multiline_inner_preserved(tmp_path):
    doc = _nb(
        tmp_path, "ml.ipynb",
        [_code("a = 1\nb = 2\n\n# comment")])
    assert doc.elements[0].content == (
        "a = 1\nb = 2\n\n# comment")
