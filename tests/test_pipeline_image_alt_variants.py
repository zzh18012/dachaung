r"""pipeline 图片 alt 变体：缺省空串、
多余属性丢弃、md raw 内联与置信度家族差
（Round 1759）。

新角度：R1758 锁 source 语义——**img 无
alt/空 alt 都得 {'alt': ''}，title/width
等属性丢弃；md 图片 alt raw 保留（'**b**
`c`'）；置信度家族差：md 图 0.95、html
图 0.9**零覆盖：

- **html 三图**：'a.png'（无 alt）/
  'b.png'（alt=""）都 {'alt': ''}，
  'c.png' 只留 alt 丢 title/width
- **md 三图**：'A'/''/'**b** `c`' raw
- **置信度**：md image 0.95 vs html
  image 0.9
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_alt_default_and_attr_drop(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        '<img src="a.png">'
        '<img src="b.png" alt="">'
        '<img src="c.png" alt="C" title="T" width="10">',
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.resource_path, e.metadata)
            for e in doc.elements] == [
        ("a.png", {"alt": ""}),
        ("b.png", {"alt": ""}),
        ("c.png", {"alt": "C"})]


def test_md_alt_raw_inline(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "![A](a.png)\n\n![](b.png)\n\n"
        "![**b** `c`](c.png)\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.resource_path, e.metadata)
            for e in doc.elements] == [
        ("a.png", {"alt": "A"}),
        ("b.png", {"alt": ""}),
        ("c.png", {"alt": "**b** `c`"})]


def test_image_confidence_family_diff(tmp_path):
    m = tmp_path / "d.md"
    m.write_text("![A](a.png)\n", encoding="utf-8")
    doc, errors = process_single(
        m, write_json=False, parser_name="markdown")
    assert errors == []
    assert doc.elements[0].confidence == 0.95

    h = tmp_path / "d.html"
    h.write_text('<img src="a.png">', encoding="utf-8")
    doc, errors = process_single(
        h, write_json=False, parser_name="html")
    assert errors == []
    assert doc.elements[0].confidence == 0.9
