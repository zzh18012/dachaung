r"""pipeline Markdown 结构家族：层级/引用/分隔线（Round 1601）。

新角度：R1598/1599 锁 raw 与列表——**ATX 层级、
blockquote、水平线**零覆盖：

- **ATX 标题 #..######** → heading {'level': 1..6}
- **blockquote** → paragraph {'kind': 'blockquote'}
  （'>' 剥除）
- **水平线 ---** → 完全丢弃（无元素）
- **行内强调**（**bold**/*italic*）→ 原样保留
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="markdown")
    assert errors == []
    return doc


def test_heading_levels_1_to_6(
        tmp_path):
    doc = _run(
        tmp_path,
        "# H1\n\n## H2\n\n"
        "### H3\n\n#### H4\n\n"
        "##### H5\n\n"
        "###### H6\n")
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("heading", "H1",
         {"level": 1}),
        ("heading", "H2",
         {"level": 2}),
        ("heading", "H3",
         {"level": 3}),
        ("heading", "H4",
         {"level": 4}),
        ("heading", "H5",
         {"level": 5}),
        ("heading", "H6",
         {"level": 6})]


def test_blockquote_hr_inline(
        tmp_path):
    doc = _run(
        tmp_path,
        "> quoted line\n\n---\n\n"
        "**bold** and *italic*\n")
    got = [(e.type, e.content,
            e.metadata)
           for e in doc.elements]
    assert got == [
        ("paragraph",
         "quoted line",
         {"kind": "blockquote"}),
        ("paragraph",
         "**bold** and *italic*",
         {})]
