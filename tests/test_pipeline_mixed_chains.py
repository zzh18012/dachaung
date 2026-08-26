r"""pipeline 混型连续链：夹心、标题居中
与混标记全并（Round 1766）。

新角度：R1765 锁纯图零 chunk——**列表-
段落-列表夹心不断链（'a mid b' 3 ids）；
标题居中：前段独立 + 标题连拉两段
（'T bbb ccc' 3 ids）；无序+有序+段落
全并一块（'a b para' 3 ids）**零覆盖：

- **'- a\\n\\nmid\\n\\n- b'**：单 chunk
  三源
- **'aaa\\n\\n## T\\n\\nbbb\\n\\nccc'**：
  'aaa'（1）+ 'T bbb ccc'（3）
- **'- a\\n\\n1. b\\n\\npara'**：'a b
  para'（3），marker 无序/有序各自保留
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_sandwich_list_para_list(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\nmid\n\n- b\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "list_item", "paragraph", "list_item"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("a mid b", 3)]


def test_mid_chain_heading_pulls_two(tmp_path):
    doc, errors = _run(
        tmp_path, "aaa\n\n## T\n\nbbb\n\nccc\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("aaa", 1), ("T bbb ccc", 3)]


def test_mixed_markers_full_chain(tmp_path):
    doc, errors = _run(tmp_path, "- a\n\n1. b\n\npara\n")
    assert errors == []
    assert [(e.type, e.metadata.get("marker"))
            for e in doc.elements] == [
        ("list_item", "unordered"),
        ("list_item", "ordered"),
        ("paragraph", None)]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("a b para", 3)]
