r"""pipeline 围栏 info 前导空格与无分号实体
（Round 1681）。

新角度：R1680 锁单元格内联——**'``` py'
前导空格剥离、'&amp;amp' 无分号照常解码**
零覆盖：

- **info 前导空格**：'``` py' → language
  'py'（R1635 的破坏只在词后带参数，前导
  空格不破坏）
- **'&amp;amp;' 无分号**：'a &amp;amp b'
  → 'a & b'（宽松实体）
- **'&amp;lt;' 无分号**：'a &amp;lt b' →
  'a &lt; b'（数字/命名均宽松）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_info_leading_space_stripped(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("``` py\ncode\n```\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": "py"})]


def test_entity_without_semicolon(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>a &amp b</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a & b", {})]


def test_lt_entity_without_semicolon(tmp_path):
    p = tmp_path / "d.html"
    p.write_text("<p>a &lt b</p>", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a < b", {})]
