r"""pipeline 闭合围栏尾空白与未闭合引号
（Round 1683）。

新角度：R1682 锁属性/分隔行——**'```  '
  尾空格仍闭合、未闭合引号整行 raw**零
覆盖：

- **闭合围栏尾空白**：'```  ' 照常闭合，
  后续 'more' 成段（与 '``` tail' 一致，
  闭合只看 ``` 前缀）
- **未闭合引号**：'&lt;p title="x&gt;x'
  标签不识别，整行原样段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_close_fence_trailing_ws(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("```\ncode\n```  \nmore\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "code",
         {"kind": "code_block", "language": ""}),
        ("paragraph", "more", {})]


def test_unclosed_quote_raw(tmp_path):
    p = tmp_path / "d.html"
    p.write_text('<p title="x>x', encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", '<p title="x>x', {})]
