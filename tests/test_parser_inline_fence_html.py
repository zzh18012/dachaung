r"""parser 内联与围栏：md 标记原样、fence
language 入 metadata、html 注释/未知标签
（Round 1785）。

新角度：R1784 锁结构退化——**md 内联
**bold**/*it*/`code`/[t](url) 标记全原样
保留；'```python' 围栏语言进 element
metadata（kind='code_block'，
language='python'，类型仍 paragraph）；
html 注释整段静默丢弃；未知标签
<custom> 剥壳留内容并与后续段落合并
'xy'；thead/tbody 表重建为管道（source
'html_table'，row_count 2）**零覆盖：

- **内联标记**：paragraph 原文逐字符
- **fence 语言**：metadata language
  'python'
- **注释/未知标签**：'a b' 跨注释合并、
  'xy' 跨标签合并
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name=parser)


def test_md_inline_markers_raw(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md",
        "Some **bold** and *it* and `code`"
        " and [t](http://x)\n", "markdown")
    assert errors == []
    assert [(e.type, e.content)
            for e in doc.elements] == [(
        "paragraph",
        "Some **bold** and *it* and `code`"
        " and [t](http://x)")]
    assert doc.chunks[0].text == doc.elements[0].content


def test_fence_language_metadata(tmp_path):
    doc, errors = _run(
        tmp_path, "d.md", "```python\nprint(1)\n```\n",
        "markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "paragraph", "print(1)",
        {"kind": "code_block", "language": "python"})]


def test_html_comment_dropped_unknown_inline(
        tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<p>a</p><!-- hidden --><p>b</p>", "html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a", "b"]
    assert doc.chunks[0].text == "a b"
    doc, errors = _run(
        tmp_path, "e.html",
        "<custom>x</custom><p>y</p>", "html")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "xy"]
    assert doc.warnings == []


def test_html_thead_rebuild(tmp_path):
    doc, errors = _run(
        tmp_path, "d.html",
        "<table><thead><tr><th>h1</th><th>h2</th>"
        "</tr></thead><tbody><tr><td>1</td>"
        "<td>2</td></tr></tbody></table>", "html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [(
        "table", "| h1 | h2 |\n| --- | --- |\n| 1 | 2 |",
        {"row_count": 2, "col_count": 2,
         "source": "html_table"})]
    assert doc.chunks[0].metadata[
        "strategy"] == "isolated_table"
