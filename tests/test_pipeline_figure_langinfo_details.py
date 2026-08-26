r"""pipeline figure 透明、language_info 语言
来源与 details/summary 合并（Round 1726）。

新角度：R1725 锁超长切分——**`<figure>` 透
明、metadata.language_info.name 同样设置
语言（第二个来源）、`<details>/<summary>`
透明合并 'Sb'**零覆盖：

- **`<figure><img><figcaption>`**：image
  + 段落 'cap'（figure 包装透明）
- **metadata.language_info.name 'python'**：
  cell 与 doc 语言 'python'（与 kernelspec
  并列来源）
- **`<details><summary>S</summary><p>b`**：
  两标签透明无空格合并单段 'Sb'
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def test_figure_transparent(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        '<figure><img src="i.png" alt="A">'
        "<figcaption>cap</figcaption></figure>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.resource_path)
            for e in doc.elements] == [
        ("image", None, "i.png"),
        ("paragraph", "cap", None)]


def test_language_info_name_source(tmp_path):
    p = tmp_path / "c.ipynb"
    p.write_text(json.dumps({
        "cells": [{"cell_type": "code",
                   "source": ["x=1"],
                   "outputs": []}],
        "metadata": {"language_info": {
            "name": "python"}},
        "nbformat": 4}), encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="ipynb")
    assert errors == []
    assert doc.elements[0].metadata["language"] == \
        "python"
    assert doc.metadata["language"] == "python"


def test_details_summary_merged(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<details><summary>S</summary><p>b</p>"
        "</details>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "Sb", {})]
