r"""pipeline HTML section_path 机制（Round 1631）。

新角度：R1630 锁 md section_path 边角——**html
的同名嵌套、跳级、任意层级起步、孤儿 li 继承**
零覆盖：

- **html 与 md 同一套 section_path 机制**：
  h1→h2 嵌套、回 h1 重置、后续元素（含孤儿
  li）继承当前节
- **同名嵌套** 'X > X'；**跳级** 'A > C'；
  **任意层级起步**（首标题 h4 也成为根）
- line 恒为 1（html 不逐行计数）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, html):
    p = tmp_path / "d.html"
    p.write_text(html, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    return doc


def test_nesting_flow(tmp_path):
    doc = _run(
        tmp_path,
        "<h1>Top</h1><p>in top</p>"
        "<h2>Sub</h2><p>in sub</p>"
        "<h1>Again</h1><p>in again</p>"
        "<li>orphan li</li>")
    assert [(e.type,
             e.source_locator["section_path"],
             e.source_locator["line"])
            for e in doc.elements] == [
        ("heading", "Top", 1),
        ("paragraph", "Top", 1),
        ("heading", "Top > Sub", 1),
        ("paragraph", "Top > Sub", 1),
        ("heading", "Again", 1),
        ("paragraph", "Again", 1),
        ("list_item", "Again", 1)]


def test_dup_skip_root(tmp_path):
    doc = _run(
        tmp_path,
        "<h1>X</h1><h2>X</h2><p>p</p>")
    assert [e.source_locator["section_path"]
            for e in doc.elements] == [
        "X", "X > X", "X > X"]

    doc2 = _run(
        tmp_path,
        "<h1>A</h1><h3>C</h3><p>p</p>")
    assert [e.source_locator["section_path"]
            for e in doc2.elements] == [
        "A", "A > C", "A > C"]

    doc3 = _run(
        tmp_path,
        "<h4>Deep</h4><p>p</p>")
    assert [e.source_locator["section_path"]
            for e in doc3.elements] == [
        "Deep", "Deep"]
