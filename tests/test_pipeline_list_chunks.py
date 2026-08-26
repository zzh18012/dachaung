r"""pipeline 列表分块合并与标题贴表
（Round 1654）。

新角度：R1653 锁 hr/title——**list_item 互
相合并（含跨段落打断）、标题后无空行贴表
照常识别**零覆盖：

- **三项列表单块**：'- a\\n- b\\n- c' →
  一个 sequential chunk 'a b c'（3 id）
- **段落打断仍单块**：'- a\\n\\ntext\\n\\n- b'
  → 'a text b'（3 id，html 列表同样 'a b'）
- **标题贴表无空行**：'# H' 下一行即表头，
  heading 与 table 均识别，table isolated
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _md(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_list_items_merge_single_chunk(tmp_path):
    doc = _md(tmp_path, "- a\n- b\n- c\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("a b c", 3, "sequential")]


def test_list_interrupt_still_single_chunk(tmp_path):
    doc = _md(tmp_path, "- a\n\ntext\n\n- b\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("a text b", 3, "sequential")]

    p = tmp_path / "d.html"
    p.write_text("<ul><li>a</li><li>b</li></ul>",
                 encoding="utf-8")
    doc2, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc2.chunks] == [("a b", 2)]


def test_heading_adjacent_table(tmp_path):
    doc = _md(
        tmp_path,
        "# H\n| a | b |\n| --- | --- |\n")
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("H", 1, "sequential"),
        ("| a | b |\n| --- | --- |", 1,
         "isolated_table")]
