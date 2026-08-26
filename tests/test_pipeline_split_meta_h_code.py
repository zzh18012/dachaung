r"""pipeline 切分块 metadata 全键、标题拉
代码链、样式标题原文（Round 1809）。

新角度：R1808 锁 inspect 零块——**切分
块 metadata = {strategy, max_chars,
char_count} + split_boundary_after（仅非
末块有键、char_count==len(text)）；
'## T'+围栏代码+'bbb' → 'T code bbb'
3 ids（代码块是拉取链全成员）；'##
**B** and `x`' 样式标记入标题原文**零
覆盖：

- **字×900**：首块 4 键（含
  forced_char）、末块 3 键
- **T+code+bbb**：单块 3 ids
- ****B** 标题**：原文保留合并
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_split_chunk_metadata_keys(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("字" * 900 + "\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    c1, c2 = doc.chunks
    assert c1.metadata == {
        "strategy": "long_paragraph_sentence_split",
        "max_chars": 800, "char_count": 800,
        "split_boundary_after": "forced_char"}
    assert c2.metadata == {
        "strategy": "long_paragraph_sentence_split",
        "max_chars": 800, "char_count": 100}
    assert c1.metadata["char_count"] == len(c1.text)
    assert c2.metadata["char_count"] == len(c2.text)


def test_heading_pulls_code_chain(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "## T\n\n```\ncode\n```\n\nbbb\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(c.text, len(c.source_element_ids),
             c.metadata["strategy"])
            for c in doc.chunks] == [
        ("T code bbb", 3, "sequential")]


def test_styled_heading_raw_content(tmp_path):
    p = tmp_path / "d.md"
    p.write_text("## **B** and `x`\n\nbody\n",
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("heading", "**B** and `x`",
         {"level": 2}),
        ("paragraph", "body", {})]
    assert doc.chunks[0].text == "**B** and `x` body"
