r"""parser md 缩进标题退化、段内硬
换行保留、pre 实体解码（Round 1835）。

新角度：R1834 锁缩进围栏退化——**
'  ## T' 缩进 2 空格不识别标题——
paragraph 字面 '## T'（与缩进围栏
平行：块语法需列 0）；'line1␠␠换行
line2' 段内换行+尾随双空格原样保留
在 content；<pre> 内 '&amp;' 照常单
次解码 'a & b'**零覆盖：

- **缩进标题**：paragraph '## T'
- **硬换行**：content 含原始换行
- **pre 实体**：'a & b' kind pre
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_indented_heading_degrades(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("  ## T\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "## T", {})]


def test_hard_break_preserved(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("line1  \nline2\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    e = doc.elements[0]
    assert (e.type, e.content) == (
        "paragraph", "line1  \nline2")


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
