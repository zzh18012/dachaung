r"""pipeline 闭合围栏带尾文本与 h7/h0
（Round 1673）。

新角度：R1672 锁混合行尾——**'``` tail'
闭合变体、超范围标题层级**零覆盖：

- **闭合围栏带尾**：'``` tail' 仍闭合
  code_block，但 ' tail' 文本被丢弃（不成
  段落）
- **'&lt;h7&gt;'**：超 6 级 → 普通段落
- **'&lt;h0&gt;'**：低于 1 级 → 普通段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_close_fence_with_tail(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("```\ncode\n``` tail\nmore\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": ""}),
        ("paragraph", "more", {})]


def test_h7_paragraph(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h7>X</h7>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "X", {})]


def test_h0_paragraph(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<h0>Y</h0>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "Y", {})]
