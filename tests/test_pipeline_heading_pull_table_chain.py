r"""pipeline 标题只向后拉段、表格独立成块
（Round 1734）。

新角度：R1733 锁图片不打断——**'aaa' 与
heading 与 'bbb'：前段独立、标题向后合并
'T bbb'（2 ids）；p+2 列表+p：表格不并入
合并链，三元素各自成 chunk（各 1 id）**零覆盖：

- **'aaa\\n\\n## T\\n\\nbbb'**：chunk1
  'aaa'（1 id）+ chunk2 'T bbb'（2 ids）
  ——标题打断向前合并，只拉入后续段落
- **'aaa' + 2 列表 + 'bbb'**：3 chunks——
  表格元素独占一块，不与前后段落合并
  （首探针用 1 列表退化成段落是假象）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_heading_pulls_following_only(tmp_path):
    doc, errors = _run(tmp_path, "aaa\n\n## T\n\nbbb\n")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "aaa"), ("heading", "T"),
        ("paragraph", "bbb")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa", 1), ("T bbb", 2)]


def test_table_stays_independent(tmp_path):
    doc, errors = _run(
        tmp_path,
        "aaa\n\n| h1 | h2 |\n| --- | --- |\n| v1 | v2 |\n\nbbb\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "paragraph", "table", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa", 1),
        ("| h1 | h2 |\n| --- | --- |\n| v1 | v2 |", 1),
        ("bbb", 1)]
