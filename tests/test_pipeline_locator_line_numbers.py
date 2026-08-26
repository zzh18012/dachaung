r"""pipeline 物理行号跨家族：html/text/md
空行计数、section_path 同居 locator
（Round 1817）。

新角度：R1816 锁混合链——**html
'<p>a</p>\\n<h2>T</h2>\\n\\n<p>b</p>'
→ 行 1/2/4（空行跳过但计数）；text
'one\\n\\ntwo\\n\\n\\nthree' → 行
1/3/6（连续空行全计入）；md 行 1/3/5
且 section_path 键与 line 同在
source_locator——首段无路径键**零
覆盖：

- **html**：1/2/4
- **text**：1/3/6
- **md**：1/3/5 + section_path 'T'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_physical_lines(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>a</p>\n<h2>T</h2>\n\n<p>b</p>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", {"line": 1}),
        ("heading", {"line": 2, "section_path": "T"}),
        ("paragraph", {"line": 4, "section_path": "T"})]


def test_text_blank_lines_counted(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("one\n\ntwo\n\n\nthree\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.content, e.source_locator)
            for e in doc.elements] == [
        ("one", {"line": 1}),
        ("two", {"line": 3}),
        ("three", {"line": 6})]


def test_md_lines_with_section_path(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("para\n\n## T\n\nbody\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", {"line": 1}),
        ("heading", {"line": 3, "section_path": "T"}),
        ("paragraph", {"line": 5, "section_path": "T"})]
