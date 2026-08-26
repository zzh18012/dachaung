r"""pipeline 同级标题替换与标题自身入路径
（Round 1677）。

新角度：R1676 锁 html 引用透明——**同级
兄弟标题替换（不嵌套）、回到 h1 重置、
heading 元素自身 section_path 含自己**零
覆盖：

- **'## B' 后 '## C'**：C 是 'A > C' 而
  非 'A > B > C'（同级替换）
- **回到 '# C'**：路径从根重来 'C'
- **标题自身入路径**：heading 'B' 的
  section_path 是 'A > B'（含自己）
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


def test_sibling_replace_not_nested(tmp_path):
    doc = _run(
        tmp_path,
        "# A\n\ntext a\n\n## B\n\ntext b\n\n"
        "## C\n\ntext c\n")
    assert [(e.content,
             e.source_locator["section_path"])
            for e in doc.elements] == [
        ("A", "A"),
        ("text a", "A"),
        ("B", "A > B"),
        ("text b", "A > B"),
        ("C", "A > C"),
        ("text c", "A > C")]


def test_back_to_h1_resets(tmp_path):
    doc = _run(
        tmp_path,
        "# A\n\n## B\n\nb\n\n# C\n\nc\n")
    assert [(e.content,
             e.source_locator["section_path"])
            for e in doc.elements] == [
        ("A", "A"),
        ("B", "A > B"),
        ("b", "A > B"),
        ("C", "C"),
        ("c", "C")]
