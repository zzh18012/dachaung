r"""pipeline section_path 全类型传播与
表格后重组成链（Round 1751）。

新角度：R1750 锁标题内联——**section_path
从标题传播到 table/list_item/code_block/
blockquote 全类型（locator 均带 'T'）；
表格打断后后续元素重组新链（'a c q'
3 ids 混型合并）；无语言围栏 language ''
**零覆盖：

- **'## T'+表+列表+代码+引用**：四元素
  locator 均 {'line': N, 'section_path':
  'T'}、confidence 0.95
- **chunks**：'T'（1 id）+ 表（1 id）+
  'a c q'（3 ids）——表打断后 list/code/
  bq 三型重组成链
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


TEXT = ("## T\n\n| h1 | h2 |\n| --- | --- |\n"
        "| v1 | v2 |\n\n- a\n\n```\nc\n```\n\n> q\n")


def _run(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(TEXT, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_section_path_all_types(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert [(e.type, e.source_locator) for e in doc.elements] == [
        ("heading", {"line": 1, "section_path": "T"}),
        ("table", {"line": 3, "section_path": "T"}),
        ("list_item", {"line": 7, "section_path": "T"}),
        ("paragraph", {"line": 9, "section_path": "T"}),
        ("paragraph", {"line": 13, "section_path": "T"})]
    assert all(e.confidence == 0.95
               for e in doc.elements)


def test_rechain_after_table(tmp_path):
    doc, errors = _run(tmp_path)
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("T", 1),
        ("| h1 | h2 |\n| --- | --- |\n| v1 | v2 |", 1),
        ("a c q", 3)]


def test_bare_fence_empty_language(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("```\nc\n```\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.metadata) for e in doc.elements] == [
        ("paragraph", {"kind": "code_block",
                       "language": ""})]
