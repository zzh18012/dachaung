r"""pipeline 次行 th 非表头、kernelspec 语言、
围栏内波浪线与散表格文本（Round 1699）。

新角度：R1698 锁围栏长度——**第二行 th 不
当表头（首行隐式表头）、kernelspec.language
写入 cell 与 doc 元数据、'```' 内 '~~~' 是
内容、`<table>` 直接文本丢弃致 no_content**
零覆盖：

- **text 'a\\n\\n\\n\\nb'**：空行串折叠，
  两段 'a'/'b'
- **`<h2>a &amp; b</h2>`**：实体解码成
  'a & b'
- **第二行 `<th>H</th>`**：非表头；首行
  'a' 隐式表头 '| a |\\n| --- |'，'H' 为
  数据格
- **kernelspec.language 'python'**：cell
  metadata language 'python' 且 doc.metadata
  language 'python'
- **'```' 内 '~~~'**：内容原样，'```' 闭合
- **`<table>loose</table>`**：散文本丢，
  doc None + html_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    parser = ("html" if name.endswith("html")
              else "text" if name.endswith("txt")
              else "markdown")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_text_multi_blank_collapses(tmp_path):
    doc, errors = _run(tmp_path, "a\n\n\n\nb\n", "d.txt")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "a"), ("paragraph", "b")]


def test_entity_in_heading(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>a &amp; b</h2>", "d.html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "a & b")]


def test_second_row_th_not_header(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<table><tr><td>a</td></tr>"
        "<tr><th>H</th></tr></table>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("table", "| a |\n| --- |\n| H |",
         {"row_count": 2, "col_count": 1,
          "source": "html_table"})]


def test_kernelspec_language(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["x=1"],
                   "outputs": []}],
        "metadata": {"kernelspec": {
            "language": "python"}},
        "nbformat": 4}), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "x=1",
         {"kind": "code_cell", "language": "python"})]
    assert doc.metadata["language"] == "python"


def test_tilde_inside_bt_fence(tmp_path):
    doc, errors = _run(
        tmp_path, "```\n~~~\n```\ntail\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "~~~",
         {"kind": "code_block", "language": ""}),
        ("paragraph", "tail", {})]


def test_loose_table_text_no_content(tmp_path):
    doc, errors = _run(
        tmp_path, "<table>loose</table>", "d.html")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    ws = errors[0].details["warnings"]
    assert [(w["code"], w["reason"]) for w in ws] == [
        ("html_no_content",
         "HTML 文件未提取到任何 element"
         "（可能为空 body 或仅含 head/script）")]
