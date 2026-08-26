r"""pipeline 纯 hash 标题内容、nbsp 标题丢弃
与长短段 chunk 组成（Round 1714）。

新角度：R1713 锁引用透明——**'## ###' 内容
成 '#'、仅 '&nbsp;' 的 h2 丢弃、1000 字符
段 + 短段成 3 chunks（799/199/5）、标题内
'> q' 原样**零覆盖：

- **'## ###'**：heading level 2 内容 '#'
  （尾随 hash 剥除后剩一个）
- **`<h2>&nbsp;</h2>`**：\\xa0 按空白处
  理，标题丢弃仅剩 't' 段
- **1000 字符段 + 'short'**：首段切 799+199
  两块，短段第三块（sequential）
- **'## > q'**：heading '> q' 引用符原样
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text, name):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False,
        parser_name="html" if name.endswith("html") else "markdown")


def test_hash_only_heading_content(tmp_path):
    doc, errors = _run(tmp_path, "## ###\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "#", {"level": 2})]


def test_nbsp_only_heading_dropped(tmp_path):
    doc, errors = _run(
        tmp_path, "<h2>&nbsp;</h2><p>t</p>", "d.html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "t")]


def test_long_short_text_chunks(tmp_path):
    p = tmp_path / "d.txt"
    p.write_bytes(("w " * 500).encode() + b"\n\nshort\n")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert len(doc.elements) == 2
    assert [(len(c.text), c.metadata["strategy"])
            for c in doc.chunks] == [
        (799, "long_paragraph_sentence_split"),
        (199, "long_paragraph_sentence_split"),
        (5, "sequential")]


def test_heading_bq_marker_raw(tmp_path):
    doc, errors = _run(tmp_path, "## > q\n", "d.md")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "> q", {"level": 2})]
