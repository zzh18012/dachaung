r"""pipeline WarningRecord 精确形态：
reason 字段、details 键与空块不入元素
（Round 1756）。

新角度：R1755 锁未知 parser——**成功路径
警告记录：WarningRecord 用 reason（非
message）；ipynb 空码 cell details 带
cell_index、未知类型带 cell_index/
cell_type；md 空代码块 details=None 且空
块不入元素（段落照常合并）**零覆盖：

- **code[]+ok+weird 三 cell**：两警告精
  确 dict、元素只留 ok
- **md 'text'+'```\\n```'+'more'**：
  warning reason 'line 3 处的代码块为空'、
  details None、chunks 'text more'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_ipynb_warning_records(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({
        "cells": [
            {"cell_type": "code", "source": []},
            {"cell_type": "code", "source": ["ok = 1"]},
            {"cell_type": "weird", "source": ["x"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert len(doc.warnings) == 2
    w0, w1 = doc.warnings
    assert (w0.code, w0.reason, w0.details) == (
        "ipynb_empty_code_cell", "cell #0 是空 code cell",
        {"cell_index": 0})
    assert (w1.code, w1.reason, w1.details) == (
        "ipynb_unknown_cell_type",
        "cell #2 类型未知: 'weird'",
        {"cell_index": 2, "cell_type": "weird"})
    assert [(e.type, e.content, e.metadata["kind"])
            for e in doc.elements] == [
        ("paragraph", "ok = 1", "code_cell")]


def test_md_empty_code_block_record(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("text\n\n```\n```\n\nmore\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert len(doc.warnings) == 1
    w = doc.warnings[0]
    assert (w.code, w.reason, w.details) == (
        "md_empty_code_block", "line 3 处的代码块为空",
        None)
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "text"), ("paragraph", "more")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("text more", 2)]


def test_warning_reason_vs_error_message_fields(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("x\n\n```\n```\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    w = doc.warnings[0]
    assert [f for f in vars(w)] == [
        "code", "reason", "details"]

    missing = tmp_path / "nope.md"
    _, errors = process_single(
        missing, write_json=False, parser_name="markdown")
    assert [f for f in vars(errors[0])] == [
        "code", "message", "details"]
