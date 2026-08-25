r"""pipeline 多行引用与超长 pre 拆分（Round 1609）。

新角度：R1608 锁 md 结构边角——**blockquote 多行、
含换行内容的词界拆分、pre 内嵌标签**零覆盖：

- **多行 blockquote** → 单 paragraph 'line a\\nline
  b'（内部换行保留）
- **超长 pre（1699 字符含 49 换行）** → 词界硬拆
  799/797/101，可在**行中间切断**（'preformatted
  line' | 'number 023'），缝隙为边界处单个空白符
  （首缝空格、次缝换行），切片恒等仍成立
- **pre 不保护内嵌标签**：&lt;br&gt; 转空格、
  &lt;b&gt; 剥除（kind 仍 preformatted）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, parser):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name=parser)
    assert errors == []
    return doc


def test_multiline_blockquote(tmp_path):
    doc = _run(
        tmp_path, "q.md",
        "> line a\n> line b\n", "markdown")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "line a\nline b",
         {"kind": "blockquote"})]


def test_oversized_pre_word_split(tmp_path):
    pre = "\n".join(
        f"preformatted line number {i:03d} here"
        for i in range(50))
    doc = _run(
        tmp_path, "p.html",
        f"<pre>{pre}</pre>", "html")
    (el,) = doc.elements
    assert len(el.content) == 1699
    assert el.content.count("\n") == 49

    c1, c2, c3 = doc.chunks
    for c in doc.chunks:
        assert c.metadata["strategy"] == (
            "long_paragraph_sentence_split")
        (s, e), = [(sp["start"], sp["end"])
                   for sp in c.source_spans]
        assert c.text == el.content[s:e]
    assert [len(c.text) for c in doc.chunks] == [
        799, 797, 101]
    assert el.content[799] == " "
    assert el.content[1597] == "\n"
    assert c1.text.endswith("\npreformatted line")
    assert c2.text.startswith("number 023")


def test_tags_inside_pre_stripped(tmp_path):
    doc = _run(
        tmp_path, "t.html",
        "<pre>a<br>b <b>bold</b> c</pre>",
        "html")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "a b bold c",
         {"kind": "preformatted"})]
