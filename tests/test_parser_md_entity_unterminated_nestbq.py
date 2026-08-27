r"""parser md 实体字面不解码、未闭合
围栏到 EOF 仍成块、html 嵌套引用
扁平（Round 1837）。

新角度：R1836 锁家族分工——**md
'&amp;' '&lt;x&gt;' 整串字面（对
比 html 单次解码）；'```py' 无闭合
——到文件尾仍是 code_block kind+
language='py'；<blockquote> 双层嵌
套扁平单 paragraph kind='blockquote'
（与 md 同一层次）**零覆盖：

- **md 实体**：原文保留不解码
- **未闭合围栏**：kind code_block
- **嵌套 bq**：单层 'deep'
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_md_entities_literal(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("a &amp; b &lt;x&gt; c\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [e.content for e in doc.elements] == [
        "a &amp; b &lt;x&gt; c"]


def test_unterminated_fence_still_block(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("before\n\n```py\nunclosed\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "before", {}),
        ("paragraph", "unclosed",
         {"kind": "code_block", "language": "py"})]


def test_html_nested_bq_flattened(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        "<blockquote><blockquote>deep"
        "</blockquote></blockquote>",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "deep",
         {"kind": "blockquote"})]
