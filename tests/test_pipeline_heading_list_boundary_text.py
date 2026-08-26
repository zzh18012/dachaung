r"""pipeline 标题拉列表 799 边界与 text
家族策略同谱（Round 1776）。

新角度：R1775 锁超限策略——**'## '+H×795+
'- bbb' → 799 合并（2 ids）——拉列表与拉
段落边界全同；text 家族策略名同谱：短段
'sequential'、超限 'long_paragraph_
sentence_split'（whitespace 边界）**零
覆盖：

- **h795+'- bbb'**：单 chunk 799（2
  ids）
- **text 1019 词段**：799 whitespace +
  219
- **text 两短段**：'a b' sequential
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_heading_list_pull_boundary(tmp_path):
    p = tmp_path / "d.md"
    p.write_text(
        "## " + "H" * 795 + "\n\n- bbb\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(799, 2)]


def test_text_oversize_strategy(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text(
        " ".join(f"w{i}" for i in range(226)) + "\n",
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text), c.metadata["strategy"],
             c.metadata.get("split_boundary_after"))
            for c in doc.chunks] == [
        (799, "long_paragraph_sentence_split",
         "whitespace"),
        (219, "long_paragraph_sentence_split", None)]


def test_text_short_merge_sequential(tmp_path):
    p = tmp_path / "d.txt"
    p.write_text("a\n\nb\n", encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(c.text, c.metadata["strategy"])
            for c in doc.chunks] == [
        ("a b", "sequential")]
