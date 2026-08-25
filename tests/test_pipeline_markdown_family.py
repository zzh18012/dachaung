r"""pipeline Markdown 解析器：raw 保留家族（Round 1598）。

新角度：R1597 锁 html——**markdown 行内语法
不做转换**与图片/表格细节零覆盖：

- **行内 raw**：链接 `[t](url)` 原样保留、
  setext 下划线成段原样、HTML 实体不解码、
  围栏代码语言标记丢弃
- **图片**：content=None、resource_path=src、
  alt 进 metadata、不产 chunk
- **管道表格**：识别为 table + isolated_table
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="markdown")
    assert errors == []
    return doc


def test_inline_raw_preserved(
        tmp_path):
    doc = _run(
        tmp_path,
        "See [the docs](http://x/y)"
        " now.\n\nSetext H1\n"
        "=========\n\n"
        "Text &amp; entity"
        " &lt;tag&gt;\n\n"
        "```python\n"
        "print('hi')\n```\n")
    got = [(e.type, e.content)
           for e in doc.elements]
    assert got == [
        ("paragraph",
         "See [the docs](http://x/y)"
         " now."),
        ("paragraph",
         "Setext H1\n========="),
        ("paragraph",
         "Text &amp; entity"
         " &lt;tag&gt;"),
        ("paragraph",
         "print('hi')")]


def test_markdown_image(tmp_path):
    doc = _run(
        tmp_path,
        "![alt text](pic.png)\n")
    (el,) = doc.elements
    assert el.type == "image"
    assert el.content is None
    assert el.resource_path == "pic.png"
    assert el.metadata == {
        "alt": "alt text"}
    assert doc.chunks == []


def test_markdown_pipe_table(
        tmp_path):
    doc = _run(
        tmp_path,
        "| a | b |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n")
    (el,) = doc.elements
    assert el.type == "table"
    assert el.content == (
        "| a | b |"
        "\n| --- | --- |"
        "\n| 1 | 2 |")
    (c,) = doc.chunks
    assert c.metadata["strategy"] == \
        "isolated_table"
    assert c.text == el.content
