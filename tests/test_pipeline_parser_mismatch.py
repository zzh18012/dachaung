r"""pipeline 解析器×扩展名错配路由（Round 1603）。

新角度：R1602 锁 html 结构——**扩展名路由优先于
parser_name** 零覆盖：

- **错配拒绝**：.md+text / .txt+markdown /
  .ipynb+markdown / 无扩展名 / .md+fallback 全部
  → doc=None + [unsupported_type]（details 含
  path 与小写 suffix）
- **后缀大小写不敏感**：.MD+markdown、.Txt+text
  正常解析；错误 details 中 suffix 仍小写
- **复合后缀取最后一段**：f.md.txt 走 text 解析器，
  markdown 语法原样保留为段落文本
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _err_details(p):
    return {"path": str(p), "suffix": p.suffix.lower()}


def test_mismatch_rejected(tmp_path):
    md = tmp_path / "f.md"
    md.write_text("# Title\n", encoding="utf-8")
    txt = tmp_path / "f.txt"
    txt.write_text("hello\n", encoding="utf-8")
    nb = tmp_path / "f.ipynb"
    nb.write_text('{"cells": [], "metadata": {}}',
                  encoding="utf-8")
    noext = tmp_path / "noext"
    noext.write_text("hello\n", encoding="utf-8")

    for path, parser in [
            (md, "text"), (txt, "markdown"),
            (nb, "markdown"), (noext, "text"),
            (md, "fallback")]:
        doc, errors = process_single(
            path, write_json=False,
            parser_name=parser)
        assert doc is None, (path, parser)
        assert [(e.code, e.details)
                for e in errors] == [
            ("unsupported_type",
             _err_details(path))], (path, parser)


def test_suffix_case_insensitive(
        tmp_path):
    md = tmp_path / "A.MD"
    md.write_text("# Heading\n", encoding="utf-8")
    doc, errors = process_single(
        md, write_json=False,
        parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content,
             e.metadata)
            for e in doc.elements] == [
        ("heading", "Heading",
         {"level": 1})]

    md2 = tmp_path / "B.Txt"
    md2.write_text("plain.\n", encoding="utf-8")
    doc2, errors2 = process_single(
        md2, write_json=False,
        parser_name="text")
    assert errors2 == []
    assert [e.content
            for e in doc2.elements] == ["plain."]

    doc3, errors3 = process_single(
        md, write_json=False,
        parser_name="text")
    assert doc3 is None
    assert errors3[0].details["suffix"] == ".md"


def test_last_suffix_wins(tmp_path):
    p = tmp_path / "f.md.txt"
    p.write_text(
        "# Not a heading\n\n- item\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="text")
    assert errors == []
    assert [(e.type, e.content,
             e.source_locator)
            for e in doc.elements] == [
        ("paragraph", "# Not a heading",
         {"line": 1}),
        ("paragraph", "- item",
         {"line": 3})]
