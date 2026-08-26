r"""parser md 块级 HTML 原样、裸 URL 原样、
尖括号图 URL 保留（Round 1820）。

新角度：R1819 锁 style/script 丢弃——**
md 不解析块级 HTML——'<div>x</div>'
整行字面段落；裸 URL 不成链接——原文
保留；'![a](<url with space.png>)' 尖
括号本身保留在 resource_path 里（不剥
壳）**零覆盖：

- **'<div>x</div>'**：字面段落
- **'visit http://x.com now'**：原样
- **'<url with space.png>'**：括号保留
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_md_block_html_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "<div>block html</div>\n")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "<div>block html</div>")]


def test_md_bare_url_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "visit http://x.com now\n")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "visit http://x.com now"]


def test_md_angle_img_brackets_kept(tmp_path):
    doc, errors = _run(
        tmp_path, "![a](<url with space.png>)\n")
    assert errors == []
    e = doc.elements[0]
    assert (e.type, e.metadata) == (
        "image", {"alt": "a"})
    assert e.resource_path == "<url with space.png>"
