r"""pipeline md 反斜杠转义不生效（Round 1688）。

新角度：R1687 锁管道转义——**'\\#' 不成
标题、反斜杠原样保留、不还原转义**零
覆盖：

- **'\\# not heading'**：行首反斜杠挡住
  标题识别，paragraph 且 '\\' 保留
  （CommonMark 会还原成 '# not heading'
  文本，这里不还原）
- **行内 '\\*'/'\\['**：全部原样
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


def test_backslash_hash_not_heading(tmp_path):
    doc = _run(tmp_path, "\\# not heading\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "\\# not heading", {})]


def test_backslash_inline_raw(tmp_path):
    doc = _run(tmp_path, "a \\* not em \\* b\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "a \\* not em \\* b")]

    doc2 = _run(tmp_path, "\\[not link\\](x)\n")
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "\\[not link\\](x)")]
