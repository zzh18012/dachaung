r"""parser 文本块与边缘语法：单换行成块、
缩进/h7 非法、pre 剥标签（Round 1794）。

新角度：R1793 锁单元格净化——**text 单
换行整块（内部 \\n 保留、line 1）；前导
空行跳过但物理行号计入（'\\n\\nx' → line
3）；md 4 空格缩进剥空成段（非代码块）；
'#######' 七井非标题（字面段落）；html
pre 内 <b> 剥壳 'a b c'、kind
'preformatted'**零覆盖：

- **'l1\\nl2\\nl3'**：单元素 line 1
- **'\\n\\nx\\n\\n\\n'**：'x' line 3
- **'    indented'**：段落 'indented
  code'、非 code_block
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_text_single_newline_one_paragraph(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("l1\nl2\nl3\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", "l1\nl2\nl3", {"line": 1})]


def test_text_padding_physical_line_locator(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("\n\nx\n\n\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(e.type, e.content, e.source_locator)
            for e in doc.elements] == [
        ("paragraph", "x", {"line": 3})]


def test_md_indent_h7_not_special(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("    indented code\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "indented code", {})]
    p = tmp_path / "e.md"
    p.write_text("####### seven\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "####### seven"]


def test_html_pre_strips_inline_tags(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<pre>a <b>b</b> c</pre>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a b c",
         {"kind": "preformatted"})]
