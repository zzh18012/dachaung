r"""pipeline 硬拆分 source_spans 偏移（Round 1605）。

新角度：R1604 锁 JSON 落盘结构——**跨 chunk 的
source_spans 偏移语义**零覆盖：

- **切片恒等**：每个 chunk.text == 元素内容
  [span.start:span.end]
- **拆分缝隙 = 恰好 1 个分隔空格**（句界拆 797/41，
  词界拆 800/800/197，gap 均为 1 空格）
- **无句读文本也用
  long_paragraph_sentence_split 策略名**
- **不超限 → 单 chunk span [0, len] sequential**
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _spans(chunk):
    return [(s["start"], s["end"])
            for s in chunk.source_spans]


def test_sentence_split_spans(tmp_path):
    p = tmp_path / "s.md"
    p.write_text(" ".join(
        f"Sentence number {i:03d}."
        for i in range(40)) + "\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    el = doc.elements[0]
    assert len(el.content) == 839

    c1, c2 = doc.chunks
    assert c1.metadata["strategy"] == (
        "long_paragraph_sentence_split")
    assert _spans(c1) == [(0, 797)]
    assert _spans(c2) == [(798, 839)]
    for c in (c1, c2):
        (s, e), = _spans(c)
        assert c.text == el.content[s:e]
    assert el.content[797] == " "


def test_word_split_spans(tmp_path):
    p = tmp_path / "w.md"
    p.write_text(" ".join(
        f"word{i:04d}"
        for i in range(200)) + "\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    el = doc.elements[0]
    assert len(el.content) == 1799

    c1, c2, c3 = doc.chunks
    for c in doc.chunks:
        assert c.metadata["strategy"] == (
            "long_paragraph_sentence_split")
        (s, e), = _spans(c)
        assert c.text == el.content[s:e]
    assert _spans(c1) == [(0, 800)]
    assert _spans(c2) == [(801, 1601)]
    assert _spans(c3) == [(1602, 1799)]
    assert el.content[800] == " "
    assert el.content[1601] == " "


def test_undersize_single_span(tmp_path):
    p = tmp_path / "u.md"
    p.write_text(" ".join(
        f"Sentence number {i:03d}."
        for i in range(20)) + "\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    el = doc.elements[0]
    (c,) = doc.chunks
    assert c.metadata["strategy"] == "sequential"
    assert _spans(c) == [(0, 419)]
    assert c.text == el.content
