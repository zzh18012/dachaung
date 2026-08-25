r"""pipeline ipynb 单元格家族（Round 1600）。

新角度：R1599 锁列表元数据——**ipynb 输出丢弃、
raw 单元、单元内 markdown、语言元数据**零覆盖：

- **code 单元输出（stream/execute_result）→ 完全
  丢弃**，仅提取 source
- **markdown 单元内的列表** → list_item 元素
  （marker 元数据同纯 markdown）
- **raw 单元** → paragraph {'kind': 'raw_cell'}
- **language** → 取 notebook kernelspec.language
  （无则 ''）
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _nb(tmp_path, cells, meta=None):
    nb = {"cells": cells,
          "metadata": meta or {},
          "nbformat": 4,
          "nbformat_minor": 5}
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps(nb),
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="ipynb")
    assert errors == []
    return doc


def test_outputs_dropped(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "code",
         "source": ["x=1"],
         "outputs": [
             {"output_type": "stream",
              "name": "stdout",
              "text": ["hello\n"]},
             {"output_type":
              "execute_result",
              "data": {"text/plain":
                       ["42"]}},
         ]}])
    (el,) = doc.elements
    assert el.type == "paragraph"
    assert el.content == "x=1"
    assert "hello" not in el.content
    assert "42" not in el.content


def test_markdown_list_in_cell(
        tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "markdown",
         "source": ["- a\n- b\n"]}])
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("list_item", "a",
         {"ordered": False,
          "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False,
          "marker": "unordered"})]


def test_raw_cell_and_language(
        tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "raw",
         "source": ["raw cell text"]},
        {"cell_type": "code",
         "source": ["x=1"],
         "outputs": []}],
        meta={"kernelspec": {
            "language": "python",
            "name": "python3"}})
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("paragraph",
         "raw cell text",
         {"kind": "raw_cell"}),
        ("paragraph", "x=1",
         {"kind": "code_cell",
          "language": "python"})]
