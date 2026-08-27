r"""app/parsers/ipynb_parser.py 边角测试 - 第十三轮（Round 1468）。

新角度（probe 实证）cell_type 变体 + md cell 无内容静默 +
语言推断坏值（edges1-12 未碰过；base 已锁 unknown 类型/
cell_type 缺失/代码 cell strip，避开）：
- cell_type **空串**与缺失同样落 'unknown'（details
  cell_type='unknown'）；**大写 'CODE' 也 unknown**（大小写
  敏感，details 保留原值 'CODE'）
- markdown cell 只有无内容内容（thematic '---'）→ **零
  element 且无 cell 级告警**（只有顶层 ipynb_no_content；
  md_no_content 不透传——md parser 对非空文本不告警）
- markdown cell 带 BOM：'# H' **标题识别被杀**降级 paragraph
  '﻿# H\ntext'（镜像 markdown 直接解析行为）
- language_info **无 name 键** → language ''
- kernelspec/language_info/metadata **非 dict** →
  _extract_kernel_language 无守卫直接 AttributeError
- raw cell 内容同样 strip（'  raw txt ' → 'raw txt'）
"""

from __future__ import annotations

import json

import pytest

from app.hash import compute_file_hash
from app.parsers.ipynb_parser import IpynbParser

TMP_NAME = "nb_edge13_probe.ipynb"


def _parse(tmp_path, obj, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return IpynbParser().parse(
        p, compute_file_hash(p))


def _nb(cells, metadata=None):
    return {"cells": cells,
            "metadata": metadata or {},
            "nbformat": 4}


# ---------- cell_type 变体 ----------

def test_cell_type_empty_unknown(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "", "source": "x"},
    ]))
    assert doc.elements == []
    w = doc.warnings[0]
    assert w.code == "ipynb_unknown_cell_type"
    assert w.details == {
        "cell_index": 0,
        "cell_type": "unknown",
    }


def test_cell_type_uppercase_unknown(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "CODE", "source": "x"},
    ]))
    w = doc.warnings[0]
    assert w.code == "ipynb_unknown_cell_type"
    assert w.details == {
        "cell_index": 0,
        "cell_type": "CODE",
    }


# ---------- md cell 无内容静默 ----------

def test_md_thematic_only_silent(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "---\n"},
    ]))
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["ipynb_no_content"]


# ---------- md cell BOM ----------

def test_md_cell_bom_kills_heading(
        tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "markdown",
         "source": "﻿# H\ntext"},
    ]))
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "﻿# H\ntext"
    assert e.source_locator["line"] == 1


# ---------- 语言推断坏值 ----------

def test_lang_info_no_name_empty(
        tmp_path):
    doc = _parse(tmp_path, _nb(
        [{"cell_type": "code",
          "source": "x"}],
        {"language_info": {
            "version": "3"}}))
    assert doc.metadata["language"] == ""


def test_kernelspec_not_dict_crashes(
        tmp_path):
    p = tmp_path / TMP_NAME
    p.write_text(json.dumps(_nb(
        [{"cell_type": "code",
          "source": "x"}],
        {"kernelspec": "python"})),
        encoding="utf-8")
    with pytest.raises(AttributeError):
        IpynbParser().parse(
            p, compute_file_hash(p))


def test_metadata_not_dict_crashes(
        tmp_path):
    p = tmp_path / TMP_NAME
    p.write_text(json.dumps(_nb(
        [{"cell_type": "code",
          "source": "x"}],
        "bad")),
        encoding="utf-8")
    with pytest.raises(AttributeError):
        IpynbParser().parse(
            p, compute_file_hash(p))


# ---------- raw cell strip ----------

def test_raw_cell_stripped(tmp_path):
    doc = _parse(tmp_path, _nb([
        {"cell_type": "raw",
         "source": "  raw txt "},
    ]))
    assert [e.content
            for e in doc.elements] == \
        ["raw txt"]
    assert doc.elements[
        0].metadata["kind"] == "raw_cell"
