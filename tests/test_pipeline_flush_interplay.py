r"""pipeline 分块 flush 交互：heading×table、
图片旁路合并（Round 1612）。

新角度：R1611 锁家族交互——**heading 累积被 table
打断、image 元素被分块旁路**零覆盖：

- **md heading + table**：table 触发 flush →
  heading 单独成 sequential chunk（heading 累积
  不跨 table），table 成 isolated_table
- **图片旁路**：p/img/p → 两段合并为一个
  sequential chunk 'before after'（2 个 source id，
  image 元素不进 chunk 也不阻断合并）——html 与
  markdown 两家族行为一致
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_heading_flushed_by_table(tmp_path):
    doc = _run(
        tmp_path, "ht.md",
        "# Head\n\n| a | b |\n| --- | --- |\n"
        "| 1 | 2 |\n", "markdown")
    c1, c2 = doc.chunks
    assert c1.text == "Head"
    assert c1.metadata["strategy"] == "sequential"
    assert c1.source_element_ids == [
        doc.elements[0].element_id]
    assert c2.metadata["strategy"] == (
        "isolated_table")
    assert c2.text.startswith("| a | b |")


def test_html_image_bypassed(tmp_path):
    doc = _run(
        tmp_path, "pi.html",
        '<p>before</p><img src="x.png">'
        "<p>after</p>", "html")
    assert [e.type
            for e in doc.elements] == [
        "paragraph", "image", "paragraph"]
    (c,) = doc.chunks
    assert c.text == "before after"
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 2
    img_id = doc.elements[1].element_id
    assert img_id not in c.source_element_ids


def test_md_image_bypassed(tmp_path):
    doc = _run(
        tmp_path, "pi.md",
        "before\n\n![alt](x.png)\n\nafter\n",
        "markdown")
    assert [e.type
            for e in doc.elements] == [
        "paragraph", "image", "paragraph"]
    (c,) = doc.chunks
    assert c.text == "before after"
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 2
