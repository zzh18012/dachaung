r"""pipeline 无空行块边界：标题贴表、表贴
段、列表-表-列表三明治（Round 1798）。

新角度：R1797 锁标签大小写——**块类型
交替处无需空行：'## T' 直接贴表行——
heading 与 table 各自成块（表破拉取，
'T' 独块）；表行直接贴 'after'——表与
段各自元素；'- a' 表 '- b'——三块 'a'/
表/'b'（表两侧链全断、不跨表重连）**零
覆盖：

- **h+表贴连**：'T' sequential + 表
  isolated
- **表+段贴连**：两元素两块
- **列表表列表**：3 块各 1 id
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single

TBL = "| a | b |\n| --- | --- |\n| 1 | 2 |"


def test_heading_table_glued(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## T\n" + TBL + "\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "table"]
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("T", "sequential"),
        (TBL, "isolated_table")]


def test_table_paragraph_glued(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(TBL + "\nafter\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "table", "paragraph"]
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        (TBL, "isolated_table"),
        ("after", "sequential")]


def test_list_table_list_split(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "- a\n\n| x | y |\n| --- | --- |\n"
        "| 1 | 2 |\n\n- b\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "list_item", "table", "list_item"]
    assert [(c.text, c.metadata["strategy"],
             len(c.source_element_ids))
            for c in doc.chunks] == [
        ("a", "sequential", 1),
        ("| x | y |\n| --- | --- |\n| 1 | 2 |",
         "isolated_table", 1),
        ("b", "sequential", 1)]
