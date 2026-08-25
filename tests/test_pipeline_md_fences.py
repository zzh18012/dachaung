r"""pipeline Markdown 围栏变体：波浪线/四反引号/
带参 info/未闭合（Round 1635）。

新角度：R1634 锁列表延续——**围栏字符变体与
info 字符串严格性**零覆盖：

- **~~~ 波浪线围栏**与 **```` 四反引号**均
  识别为 code_block（language ''）
- **带参数 info 字符串破坏围栏**：
  '```python title="x"' 非纯词 → 整块成
  raw 段落
- **未闭合围栏**：其后全部内容入 code_block
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


def test_tilde_and_four_backticks(tmp_path):
    doc = _run(
        tmp_path, "~~~\ncode body\n~~~\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code body",
         {"kind": "code_block",
          "language": ""})]

    doc2 = _run(
        tmp_path, "````\na\n````\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc2.elements] == [
        ("paragraph", "a",
         {"kind": "code_block",
          "language": ""})]


def test_info_string_extra_breaks(tmp_path):
    doc = _run(
        tmp_path,
        '```python title="x"\ncode\n```\n')
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph",
         '```python title="x"\ncode',
         {})]


def test_unclosed_fence(tmp_path):
    doc = _run(
        tmp_path,
        "```\ncode line\nmore\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code line\nmore",
         {"kind": "code_block",
          "language": ""})]
