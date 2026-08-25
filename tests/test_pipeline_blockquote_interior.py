r"""pipeline blockquote 内部惰性（Round 1637）。

新角度：R1636 锁嵌套容器——**引用内部的
结构标记全部失效**零覆盖：

- **'>>' 双层引用**：仅剥一个 &gt;，剩
  '&gt; deep quote' 仍是单层 blockquote
- **引用内 '#' 不是标题**：'# Quoted head'
  原样文本；引用内 '- ' 也不是列表
- **惰性延续不属于引用**：无 &gt; 的下一行
  成独立普通段落
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


def test_double_quote_stripped(tmp_path):
    doc = _run(
        tmp_path, ">> deep quote\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "> deep quote",
         {"kind": "blockquote"})]


def test_interior_markers_inert(tmp_path):
    doc = _run(
        tmp_path, "> # Quoted head\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "# Quoted head",
         {"kind": "blockquote"})]

    doc2 = _run(
        tmp_path, "> - quoted item\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "- quoted item",
         {"kind": "blockquote"})]


def test_lazy_continuation_separate(tmp_path):
    doc = _run(
        tmp_path,
        "> first line\nlazy second\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "first line",
         {"kind": "blockquote"}),
        ("paragraph", "lazy second", {})]
