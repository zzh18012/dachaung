r"""pipeline 标题链累积深度：连续标题、
拉列表、拉多段、跨图（Round 1735）。

新角度：R1734 锁表格不入链——**标题链
不是只拉一段：连续标题各自开链（T1 独
立 + 'T2 bbb'）、列表项也入链（'T a b'
3 ids）、连拉两段（'T bbb ccc' 3 ids）、
中间图片不打断（'T bbb'）**零覆盖：

- **'## T1\\n\\n## T2\\n\\nbbb'**：'T1'
  （1 id）+ 'T2 bbb'（2 ids）——T1 后无
  段可拉，T2 开新链拉 bbb
- **'## T\\n\\n- a\\n- b'**：单 chunk
  'T a b'（3 ids）
- **'## T\\n\\nbbb\\n\\nccc'**：单 chunk
  'T bbb ccc'（3 ids）
- **'## T\\n\\n![i](i.png)\\n\\nbbb'**：
  'T bbb'（2 ids）——image 旁路不断链
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_consecutive_headings_separate_chains(tmp_path):
    doc, errors = _run(tmp_path, "## T1\n\n## T2\n\nbbb\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "heading", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [
        ("T1", 1), ("T2 bbb", 2)]


def test_heading_pulls_list_items(tmp_path):
    doc, errors = _run(tmp_path, "## T\n\n- a\n- b\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "list_item", "list_item"]
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == "T a b"
    assert len(doc.chunks[0].source_element_ids) == 3


def test_heading_pulls_two_paragraphs(tmp_path):
    doc, errors = _run(tmp_path, "## T\n\nbbb\n\nccc\n")
    assert errors == []
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T bbb ccc", 3)]


def test_image_does_not_break_heading_pull(tmp_path):
    doc, errors = _run(
        tmp_path, "## T\n\n![i](i.png)\n\nbbb\n")
    assert errors == []
    assert [e.type for e in doc.elements] == [
        "heading", "image", "paragraph"]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T bbb", 2)]
