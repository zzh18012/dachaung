r"""pipeline 家族空输入与损坏输入（Round 1606）。

新角度：R1605 锁 spans 偏移——**md/html/ipynb 的
空内容警告码与损坏 JSON 路径**零覆盖（空家族仅
R1599 锁过 .txt）：

- **空/仅空白/仅装饰元素** → no_extracted_elements，
  details.warnings 带各自专属码：
  md_no_content / html_no_content /
  ipynb_no_content（fallback 之外的新警告码）
- **坏 JSON .ipynb** → ipynb_invalid_json
  （exception_type=JSONDecodeError）
- **markdown frontmatter 无特殊语义**：`---` 当
  水平线丢弃，夹着的内容成普通段落
"""

from __future__ import annotations

import json

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, content, parser):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_empty_family_inputs(tmp_path):
    cases = [
        ("e.md", "", "markdown",
         "md_no_content",
         "Markdown 文件未提取到任何 element"
         "（可能为空文件或仅含主题分隔符）",
         "markdown"),
        ("w.md", "  \n\n  \n", "markdown",
         "md_no_content", None, "markdown"),
        ("e.html", "", "html",
         "html_no_content",
         "HTML 文件未提取到任何 element"
         "（可能为空 body 或仅含 head/script）",
         "html"),
        ("h.html", "<hr><br>", "html",
         "html_no_content", None, "html"),
        ("head.html",
         "<html><head><title>T</title></head>"
         "<body></body></html>", "html",
         "html_no_content", None, "html"),
        ("e.ipynb", json.dumps(
            {"cells": [], "metadata": {},
             "nbformat": 4}), "ipynb",
         "ipynb_no_content",
         ".ipynb 未提取到任何 element"
         "（空 notebook 或仅含空 cell）",
         "ipynb"),
    ]
    for name, content, parser, wcode, reason, stype in cases:
        doc, errors = _run(
            tmp_path, name, content, parser)
        assert doc is None, name
        assert [e.code for e in errors] == [
            "no_extracted_elements"], name
        d = errors[0].details
        assert d["source_type"] == stype, name
        (w,) = d["warnings"]
        assert w["code"] == wcode, name
        if reason is not None:
            assert w["reason"] == reason, name


def test_empty_source_cells(tmp_path):
    doc, errors = _run(
        tmp_path, "es.ipynb",
        json.dumps({"cells": [
            {"cell_type": "code",
             "source": [], "outputs": []},
            {"cell_type": "markdown",
             "source": []}],
            "metadata": {}, "nbformat": 4}),
        "ipynb")
    assert doc is None
    assert [e.code for e in errors] == [
        "no_extracted_elements"]
    assert errors[0].details["warnings"] == [
        {"code": "ipynb_empty_code_cell",
         "reason": "cell #0 是空 code cell",
         "details": {"cell_index": 0}},
        {"code": "ipynb_no_content",
         "reason": ".ipynb 未提取到任何 element"
                   "（空 notebook 或仅含空 cell）"}]


def test_ipynb_invalid_json_and_frontmatter(
        tmp_path):
    for name, raw in [("bad.ipynb", "not json"),
                      ("b2.ipynb", "{broken")]:
        p = tmp_path / name
        p.write_text(raw, encoding="utf-8")
        doc, errors = process_single(
            p, write_json=False,
            parser_name="ipynb")
        assert doc is None
        assert [(e.code, e.details["exception_type"])
                for e in errors] == [
            ("ipynb_invalid_json",
             "JSONDecodeError")]

    fm = tmp_path / "fm.md"
    fm.write_text("---\ntitle: x\n---\n",
                  encoding="utf-8")
    doc2, errors2 = process_single(
        fm, write_json=False,
        parser_name="markdown")
    assert errors2 == []
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "title: x")]
