r"""parser 内联 HTML 原样、单列表退化、
实体单趟解码、有序列表去号（Round 1789）。

新角度：R1788 锁参差补齐——**md 段内
<b> 原样保留；'\\|' 单列头+分隔行不构成
表——整块退化多行段落（\\n 保留）；
html 实体单趟解码：'&amp;amp;' → '&amp;'
（不再解第二趟）、无分号 '&copy' → '©'
（宽松解析）；md '1. one' 与 html ol 同
——裸 list_item、编号丢弃**零覆盖：

- **'<b>bold</b>'**：md 段原样
- **'\\|' 单列**：paragraph 多行退化
- **'&amp;amp; &lt;x&gt; &copy'**：
  '&amp; <x> ©'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_md_inline_html_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "before <b>bold</b> after\n",
        "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [(
        "paragraph", "before <b>bold</b> after")]


def test_single_col_escaped_pipe_degrades(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md",
        "| a \\| b |\n| --- |\n| x |\n", "markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "paragraph",
        "| a \\| b |\n| --- |\n| x |", {})]
    assert doc.warnings == []


def test_html_entities_single_decode(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html", "<p>&amp;amp; &lt;x&gt; &copy</p>",
        "html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "&amp; <x> ©"]


def test_md_ordered_list_markers_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "1. one\n2. two\n", "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "one"), ("list_item", "two")]
    assert doc.chunks[0].text == "one two"
