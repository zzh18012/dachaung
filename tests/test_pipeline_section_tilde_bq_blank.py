r"""pipeline section 透明、波浪线围栏、li 内
嵌 p 与引用内部空行（Round 1696）。

新角度：R1695 锁数字实体——**'````' 4 反
引号与 '~~~' 波浪线围栏都成 code_block、
`<section>` 第 7 个透明包装器、'> a\\n>\\n>
b' 内部空行保留仍单块**零覆盖：

- **`<section>`**：内层 h2/p 照常提取
- **'````'/'~~~'/'~~~py'**：三种围栏都成
  code_block，波浪线可带语言
- **`<li><p>x</p></li>`**：p 透明，list_item
  'x'
- **`<p>   </p>`**：纯空白 p 丢弃
- **引用内部空行**：'a\\n\\nb' 一个
  blockquote 段（空行不拆块）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_html_section_transparent(tmp_path):
    doc, errors = _run(
        tmp_path,
        "<section><h2>S</h2><p>t</p></section>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "S", {"level": 2}),
        ("paragraph", "t", {})]


def test_four_backticks_and_tilde_fences(tmp_path):
    doc, errors = _run(
        tmp_path, "````\ncode\n````\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": ""})]

    doc2, errors2 = _run(
        tmp_path, "~~~\ncode\n~~~\n", "d.md")
    assert errors2 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": ""})]

    doc3, errors3 = _run(
        tmp_path, "~~~py\ncode\n~~~\n", "d.md")
    assert errors3 == []
    assert [(e.type, e.content, e.metadata)
            for e in doc3.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": "py"})]


def test_li_nested_p_and_ws_p(tmp_path):
    doc, errors = _run(
        tmp_path, "<ul><li><p>x</p></li></ul>",
        "d.html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "x",
         {"ordered": False, "marker": "unordered"})]

    doc2, errors2 = _run(
        tmp_path, "<p>   </p><p>y</p>", "d.html")
    assert errors2 == []
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "y")]


def test_bq_empty_interior_line(tmp_path):
    doc, errors = _run(tmp_path, "> a\n>\n> b\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a\n\nb",
         {"kind": "blockquote"})]
