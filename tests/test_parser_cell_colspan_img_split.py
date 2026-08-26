r"""parser 单元格净化、colspan 空补、标题内
img 拆分、ipynb 单胞多块（Round 1793）。

新角度：R1792 锁表格归一——**html 单元
格内 <b>/<i> 剥壳、实体照解 '1 & 2'；
colspan=2 不生效——'wide' 落首列、次列
空补 '| wide |  |'；<h2>T <img></h2>
——标题 'T' 不含图、img 独立成元素、后
段照拉；ipynb 单 md 胞 heading+list+
table：三类型齐发、表破链 'H li' +
isolated_table**零覆盖：

- **<i>1</i> &amp; 2**：'1 & 2'
- **colspan=2**：'| wide |  |'
- **h2 内 img**：heading 'T' + image 分离
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_html_cell_inline_tags_entities(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th><b>h</b></th><th>n</th></tr>"
        "<tr><td><i>1</i> &amp; 2</td><td>x</td>"
        "</tr></table>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "| h | n |\n| --- | --- |\n| 1 & 2 | x |"]


def test_html_colspan_pads_not_spans(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<table><tr><th>a</th><th>b</th></tr>"
        "<tr><td colspan=2>wide</td></tr></table>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.content, e.metadata["col_count"])
            for e in doc.elements] == [(
        "| a | b |\n| --- | --- |\n| wide |  |", 2)]


def test_html_img_in_heading_splits(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<h2>T <img src='i.png'></h2><p>b</p>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"), ("image", None),
        ("paragraph", "b")]
    assert doc.chunks[0].text == "T b"


def test_ipynb_multiblock_cell(tmp_path):
    p = tmp_path / "d.ipynb"
    p.write_text(json.dumps({"cells": [
        {"cell_type": "markdown", "source": [
            "## H\n\n", "- li\n\n",
            "| a | b |\n| --- | --- |\n| 1 | 2 |"]},
    ], "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "list_item", "table"]
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("H li", "sequential"),
        ("| a | b |\n| --- | --- |\n| 1 | 2 |",
         "isolated_table")]
