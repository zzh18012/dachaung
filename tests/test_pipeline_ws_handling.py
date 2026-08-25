r"""pipeline 首尾空白与内部空白保留（Round 1632）。

新角度：R1631 锁 html section_path——**尾随空白
剥除、标题内行内 raw、html 内部空白不折叠**
零覆盖：

- **尾随空白剥除**：'# Head   ' → 'Head'；
  段落行尾空格同样剥除
- **标题内行内 raw**：'# **Bold** and *it*'
  原样保留（与段落一致，不做强调解析）
- **html 内部空白不折叠**：'double  space\\n\\t
  tabbed   end' 原样（只剥首尾，不按 HTML 规范
  折叠连续空白）
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


def test_trailing_stripped(tmp_path):
    doc = _run(
        tmp_path, "t.md",
        "# Head   \n", "markdown")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "Head", {"level": 1})]

    doc2 = _run(
        tmp_path, "p.md",
        "para with trailing   \n", "markdown")
    assert [e.content
            for e in doc2.elements] == [
        "para with trailing"]


def test_inline_raw_in_heading(tmp_path):
    doc = _run(
        tmp_path, "i.md",
        "# **Bold** and *it*\n", "markdown")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "**Bold** and *it*")]


def test_html_ws_not_collapsed(tmp_path):
    doc = _run(
        tmp_path, "w.html",
        "<p>double  space\n\ttabbed   end</p>",
        "html")
    assert [e.content
            for e in doc.elements] == [
        "double  space\n\ttabbed   end"]
