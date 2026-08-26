r"""parser html 语义壳透明、md 空 alt
图片、section_path 层级 ' > ' 链
（Round 1826）。

新角度：R1825 锁 ipynb md cell 结构
——**article/section 双层壳完全透明
（无字面残留无 heading）；'![](u.png)'
image content=None + alt=''；'# A' +
'## B' 层级链 section_path 'A > B'
（分隔符空格>空格）**零覆盖：

- **语义壳**：仅 paragraph 'in sec'
- **空 alt**：content None/alt ''
- **层级链**：A / A > B / A > B
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_semantic_wrappers_transparent(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<article><section><p>in sec</p>"
        "</section></article>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "in sec")]


def test_md_empty_alt_image(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("![](u.png)\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    e = doc.elements[0]
    assert (e.type, e.content, e.metadata,
            e.resource_path) == (
        "image", None, {"alt": ""}, "u.png")


def test_section_path_hierarchy(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# A\n\n## B\n\ntext\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.source_locator["section_path"]
            for e in doc.elements] == [
        "A", "A > B", "A > B"]
