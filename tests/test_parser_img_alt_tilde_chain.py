r"""parser html img alt 捕获、md 波浪线
围栏等价、三级 section_path 链
（Round 1827）。

新角度：R1826 锁两级层级链——**
<img src alt> 的 alt 进 metadata
{'alt':'pic'}（content 仍 None）；'~~~
py' 波浪线围栏与反引号围栏完全等价
（kind code_block + language）；h1>
h2>h3 全链 'A > B > C'（末级 para 同
继承）**零覆盖：

- **img alt**：alt 'pic' / path 'p.png'
- **波浪围栏**：code_block language py
- **三级链**：A / A > B / A > B > C
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_html_img_alt_captured(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<img src="p.png" alt="pic">',
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    e = doc.elements[0]
    assert (e.type, e.content, e.metadata,
            e.resource_path) == (
        "image", None, {"alt": "pic"}, "p.png")


def test_md_tilde_fence_equivalent(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("~~~py\ncode\n~~~\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": "py"})]


def test_three_level_section_chain(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("# A\n\n## B\n\n### C\n\nt\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.source_locator["section_path"]
            for e in doc.elements] == [
        "A", "A > B", "A > B > C",
        "A > B > C"]
