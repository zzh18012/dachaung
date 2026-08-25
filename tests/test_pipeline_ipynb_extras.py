r"""pipeline ipynb outputs/execution_count/
attachments 全部忽略（Round 1643）。

新角度：R1642 锁 hr/起始号——**code 单元的
outputs 与 execution_count、markdown 单元的
attachments 不进文档**零覆盖：

- **outputs 丢弃**：stream 输出文本 '1\\n' 不
  出现，段落只有源码 'print(1)'
- **execution_count 丢弃**：7 不进 locator
- **attachments 丢弃**：markdown 附件不成
  resource/元素
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _nb(tmp_path, cells):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": cells, "metadata": {},
        "nbformat": 4}), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    return doc


def test_outputs_dropped(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "code", "source": ["print(1)"],
         "outputs": [{"output_type": "stream",
                      "text": ["1\n"]}],
         "execution_count": 7}])
    assert [(e.type, e.content, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", "print(1)",
         {"cell_index": 0, "cell_type": "code"})]
    assert "1\n" not in [
        e.content for e in doc.elements]


def test_execution_count_not_in_locator(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "code", "source": ["x=1"],
         "outputs": [], "execution_count": 3}])
    assert doc.elements[0].source_locator == {
        "cell_index": 0, "cell_type": "code"}


def test_attachments_dropped(tmp_path):
    doc = _nb(tmp_path, [
        {"cell_type": "markdown", "source": ["has att\n"],
         "attachments": {"img.png":
                         {"text/plain": ["data"]}}}])
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "has att")]
    assert all(
        e.type != "image" for e in doc.elements)
