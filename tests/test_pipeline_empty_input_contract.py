r"""pipeline 空输入失败契约：doc=None +
no_extracted_elements 与嵌套家族警告
（Round 1752）。

新角度：R1751 锁 section_path——**空/纯
白 md、空 txt、空 html、空 cells ipynb 统
一返回 (None, [ErrorRecord(code=
'no_extracted_elements')])，家族警告嵌在
details['warnings'] 而非 doc.warnings；纯
图文件反而是成功**零覆盖：

- **空 md**：details 含 warnings[0] code
  'md_no_content' + source_type
- **纯空白 md**：与空文件同
- **纯图 md**：1 image 元素、errors [] —
  图片算内容
- **空 txt/html/ipynb**：同错误壳，嵌套
  code 分别 text_no_content/
  html_no_content/ipynb_no_content
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _err_of(doc, errors):
    assert doc is None
    assert len(errors) == 1
    e = errors[0]
    assert e.code == "no_extracted_elements"
    assert e.message == (
        "解析完成但未提取到任何 element"
        "（可能为扫描件或不支持的内容）")
    return e.details


def test_empty_md_error_contract(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    details = _err_of(doc, errors)
    assert details == {
        "warnings": [{"code": "md_no_content",
                      "reason": "Markdown 文件未提取到任何 "
                                "element（可能为空文件或仅含主题分隔符）"}],
        "source_type": "markdown"}


def test_whitespace_md_same_as_empty(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("   \n\n  \n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    details = _err_of(doc, errors)
    assert details["warnings"][0]["code"] == "md_no_content"


def test_image_only_md_succeeds(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("![i](i.png)\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == ["image"]
    assert doc.warnings == []


def test_empty_per_family_nested_codes(tmp_path):
    cases = [
        ("d.txt", "text", "", "text_no_content"),
        ("d.html", "html", "", "html_no_content"),
    ]
    for name, parser, content, code in cases:
        p = tmp_path / name
        p.write_text(content, encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False, parser_name=parser)
        details = _err_of(doc, errors)
        assert details["warnings"][0]["code"] == code, name
        assert details["source_type"] == parser, name

    n = tmp_path / "d.ipynb"
    n.write_text(json.dumps(
        {"cells": [], "metadata": {}, "nbformat": 4}),
        encoding="utf-8")
    doc, errors = process_single(
        n, write_json=False, parser_name="ipynb")
    details = _err_of(doc, errors)
    assert details["warnings"][0]["code"] == (
        "ipynb_no_content")
    assert details["source_type"] == "ipynb"
