r"""pipeline 列表入合并链与表格打断标题链
（Round 1736）。

新角度：R1735 锁标题拉列表——**列表项与
段落互通合并（'- a'+para → 'a bbb'；para+
'- a' → 'aaa a'）、标题打断列表链开新链
（'a' + 'T b'）、表格打断标题链（T 无段
可拉独占一块，与 image 旁路不同）**零覆盖：

- **'- a\\n\\nbbb'**：单 chunk 'a bbb'
  （2 ids）——列表项并入顺序合并链
- **'aaa\\n\\n- a'**：单 chunk 'aaa a'
  （2 ids）——段落反向拉列表项
- **'- a\\n\\n## T\\n\\n- b'**：'a'（1
  id）+ 'T b'（2 ids）
- **'## T'+表+'bbb'**：'T'（1 id）+表+
  'bbb'——表 flush 链，标题被截空
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_list_merges_with_paragraph(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\nbbb\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "list_item", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("a bbb", 2)]


def test_paragraph_pulls_list_item(tmp_path):
    doc, errors = _run(tmp_path, "aaa\n\n- a\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("aaa a", 2)]


def test_heading_breaks_list_chain(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\n## T\n\n- b\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("a", 1), ("T b", 2)]


def test_table_breaks_heading_chain(tmp_path):
    doc, errors = _run(
        tmp_path,
        "## T\n\n| h1 | h2 |\n| --- | --- |\n| v1 | v2 |\n\nbbb\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "table", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("T", 1),
        ("| h1 | h2 |\n| --- | --- |\n| v1 | v2 |", 1),
        ("bbb", 1)]
