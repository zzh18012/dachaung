r"""pipeline 标题层级范围与列表缩进阈值
（Round 1650）。

新角度：R1649 锁相邻表——**h4-h6 层级、标
题内换行、列表缩进容忍度**零覆盖：

- **h4/h5/h6**：level 4/5/6 全支持
- **标题内换行**：'<h2>a\\nb</h2>' 换行保留
  在 heading content
- **缩进破坏列表**：'\\t- x'、1 空格与
  3 空格缩进都是 paragraph 原样（仅 0 缩
  进成 list_item）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, payload, parser, suffix):
    p = tmp_path / ("d" + suffix)
    p.write_text(payload, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_heading_levels_456(tmp_path):
    doc = _run(tmp_path, "<h4>D</h4><h5>E</h5>"
                         "<h6>F</h6>", "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "D", {"level": 4}),
        ("heading", "E", {"level": 5}),
        ("heading", "F", {"level": 6})]


def test_heading_keeps_newline(tmp_path):
    doc = _run(tmp_path, "<h2>a\nb</h2>",
               "html", ".html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "a\nb", {"level": 2})]


def test_indent_breaks_list(tmp_path):
    doc = _run(tmp_path, "\t- tabbed\n",
               "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "- tabbed", {})]

    doc2 = _run(tmp_path, "   - spaced\n",
                "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "- spaced", {})]

    doc3 = _run(tmp_path, "- zero\n",
                "markdown", ".md")
    assert [(e.type, e.content, e.metadata)
            for e in doc3.elements] == [
        ("list_item", "zero",
         {"ordered": False,
          "marker": "unordered"})]
