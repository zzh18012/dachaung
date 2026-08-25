r"""pipeline Markdown 标题空格边界（Round 1644）。

新角度：R1643 锁 ipynb extras——**'#' 后无
空格、裸井号、井号+空格+空**零覆盖：

- **'#Nospace'**：井号后必须有空格才是标题，
  否则整行原样段落
- **裸 '###'**：无标题文本 → 段落 '###'
- **'# '（井号空格空）**：strip 后剩 '#'，
  段落 '#'；标题可在文档任意位置生效
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_no_space_not_heading(tmp_path):
    doc = _run(tmp_path, "#Nospace heading\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "#Nospace heading", {})]


def test_bare_hashes_paragraph(tmp_path):
    doc = _run(tmp_path, "###\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "###", {})]


def test_hash_space_empty_degrades(tmp_path):
    doc = _run(tmp_path, "# \n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "#", {})]

    doc2 = _run(tmp_path, "text\n# mid\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "text", {}),
        ("heading", "mid", {"level": 1})]
