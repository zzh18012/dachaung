r"""pipeline 小 max_chars 区间与 # 变体（Round 1614）。

新角度：R1613 锁下限 32——**32-100 小区间拆分、
超限 heading 不拆、# 紧贴/缩进/尾随 #**零覆盖：

- **小区间词界拆分**：67 字符段 @32 → 31/31/3
  （8 词恰 31）；**表格在小 max_chars 下仍豁免**
  （64 字符单 chunk isolated_table）
- **超限 heading 永不拆**：40 字符 heading @35
  → 单 sequential chunk 原样 40 字符（下限 32
  之上不失败不切，与段落不同）
- **# 变体**：'#HHHH'（无空格）→ 段落 raw；
  '  # Spaced'（缩进）→ 段落 raw；
  '### Title ###' → heading level 3 且**尾随 #
  剥除**（内容 'Title'）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, text, mc=800):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False,
        parser_name="markdown", max_chars=mc)
    assert errors == []
    return doc


def test_small_maxchars_word_split(tmp_path):
    para = " ".join(
        f"w{i:02d}" for i in range(17))
    doc = _run(
        tmp_path, "a.md", para + "\n", 32)
    assert len(doc.elements[0].content) == 67
    got = [(len(c.text), c.text)
           for c in doc.chunks]
    assert got == [
        (31, "w00 w01 w02 w03 w04 w05 "
             "w06 w07"),
        (31, "w08 w09 w10 w11 w12 w13 "
             "w14 w15"),
        (3, "w16")]
    assert all(
        c.metadata["strategy"]
        == "long_paragraph_sentence_split"
        for c in doc.chunks)

    tdoc = _run(
        tmp_path, "t.md",
        "| " + "a" * 32 + " | b |\n"
        "| --- | --- |\n| 1 | 2 |\n", 32)
    (tc,) = tdoc.chunks
    assert tc.metadata["strategy"] == (
        "isolated_table")
    assert len(tc.text) == 64


def test_oversize_heading_never_splits(
        tmp_path):
    doc = _run(
        tmp_path, "b.md",
        "# " + "H" * 40 + "\n", 35)
    (c,) = doc.chunks
    assert len(c.text) == 40
    assert c.metadata["strategy"] == "sequential"
    assert len(c.source_element_ids) == 1


def test_hash_variants(tmp_path):
    doc = _run(
        tmp_path, "n.md",
        "#HHHH world\n", 800)
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "#HHHH world")]

    doc2 = _run(
        tmp_path, "i.md",
        "  # Spaced\n", 800)
    assert [(e.type, e.content)
            for e in doc2.elements] == [
        ("paragraph", "# Spaced")]

    doc3 = _run(
        tmp_path, "t.md",
        "### Title ###\n", 800)
    assert [(e.type, e.content, e.metadata)
            for e in doc3.elements] == [
        ("heading", "Title", {"level": 3})]
