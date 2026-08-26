r"""parser 嵌套列表扁平、hr 丢弃、ipynb 粘
连标题识别、链接定义字面（Round 1795）。

新角度：R1794 锁边缘语法——**html 嵌套
<ul> 全部扁平同级（'a','b','c' 三
list_item、无嵌套信息、合并 'a b c'）；
<hr> 与 md '---' 同——静默丢弃、两侧
合并；ipynb '## T\\nbbb' 无空行仍识别
heading+paragraph；'[ref]: url' 链接
定义不消费——字面段落**零覆盖：

- **嵌套 ul**：3×list_item 同级 'a b c'
- **<hr>**：无元素、'a b' 跨合并
- **'## T\\nbbb'**：heading 'T' + 段落
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_html_nested_list_flattened(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<ul><li>a<ul><li>b</li></ul></li>"
        "<li>c</li></ul>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "a",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "b",
         {"ordered": False, "marker": "unordered"}),
        ("list_item", "c",
         {"ordered": False, "marker": "unordered"})]
    assert doc.chunks[0].text == "a b c"


def test_html_hr_dropped_merge(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>a</p><hr><p>b</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a", "b"]
    assert doc.warnings == []
    assert doc.chunks[0].text == "a b"


def test_ipynb_glued_heading_recognized(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "markdown",
         "source": ["## T\nbbb"]}],
        "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"), ("paragraph", "bbb")]
    assert doc.chunks[0].text == "T bbb"


def test_md_link_definition_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("[ref]: http://x\n\nbody\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "[ref]: http://x", "body"]
