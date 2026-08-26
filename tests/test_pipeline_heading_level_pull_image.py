r"""pipeline 标题 level 元数据、html title
丢弃、标题跨图拉段（Round 1787）。

新角度：R1786 锁输入形态——**heading
元素 metadata {'level': N}（1–3 实证，
段落 metadata 恒 {}）；html <title>
整段丢弃（body 外内容不发射）；标题+
图+段落：图不破拉取，'T bbb' 2 ids，
image 元素 content=None（资源在
metadata）**零覆盖：

- **# / ## / ###**：heading level 1/2/3
- **<title>**：仅剩 body 段落
- **T+img+bbb**：'T bbb' 跨图 2 ids
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_heading_level_metadata(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# H1\n\n## H2\n\n### H3\n\nbbb\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "H1", {"level": 1}),
        ("heading", "H2", {"level": 2}),
        ("heading", "H3", {"level": 3}),
        ("paragraph", "bbb", {})]


def test_html_title_dropped(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<html><head><title>Page</title></head>"
        "<body><p>a</p></body></html>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a")]


def test_heading_pull_across_image(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "## T\n\n![alt](a.png)\n\nbbb\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"), ("image", None),
        ("paragraph", "bbb")]
    assert [(c.text, len(c.source_element_ids))
            for c in doc.chunks] == [("T bbb", 2)]
