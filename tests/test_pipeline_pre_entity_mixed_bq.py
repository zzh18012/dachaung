r"""pipeline pre 内实体与混合层级引用
（Round 1686）。

新角度：R1685 锁分隔线变体——**pre 内实体
照常解码、空行分隔的混合层级引用各自成
块**零覆盖：

- **pre 内 '&amp;amp;'**：解码 '&'
  （kind 'preformatted' 不影响实体处理）
- **'&gt; a' 与 '&gt;&gt; b' 相邻**：两个
  独立 blockquote，第二个内容 '&gt; b'
  （层级不合并）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_pre_entity_decoded(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<pre>a &amp; b</pre>",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a & b",
         {"kind": "preformatted"})]


def test_mixed_level_bq_separate(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("> a\n\n>> b\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a", {"kind": "blockquote"}),
        ("paragraph", "> b",
         {"kind": "blockquote"})]
