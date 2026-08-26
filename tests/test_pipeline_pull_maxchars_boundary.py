r"""pipeline 标题拉段撞 max_chars 精确边界
与列表贪心（Round 1740）。

新角度：R1739 锁跨 cell 链——**标题只在
合并后 ≤ 800 时拉段：恰 800 → 单 chunk
（2 ids）；801 → 'T' 独立 + 段独立；段自身
超限时标题永不并入其切分块；列表项贪心与
段落全同（779+389）**零覆盖：

- **'## T'+798 字符段**：'T '+798=800 恰
  合并 → 单 chunk 800（2 ids，'T ' 开头）
- **'## T'+799 字符段**：801 超 → 'T'（1
  id）+ 799（1 id）两块
- **'## T'+909 字符段**：'T'（1 id）+ 段
  自行切 799/109——标题不沾切分块
- **3×389 列表项**：779（2 ids）+389（1
  id），贪心同段落
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_text(text, encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="markdown")


def test_pull_at_exactly_800(tmp_path):
    para = " ".join(["ab"] * 265 + ["abc"])
    assert len(para) == 798
    doc, errors = _run(tmp_path, "## T\n\n" + para + "\n")
    assert errors == []
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0].text) == 800
    assert doc.chunks[0].text.startswith("T ")
    assert len(doc.chunks[0].source_element_ids) == 2


def test_no_pull_at_801(tmp_path):
    para = " ".join(["ab"] * 265 + ["abcd"])
    assert len(para) == 799
    doc, errors = _run(tmp_path, "## T\n\n" + para + "\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(1, 1), (799, 1)]


def test_heading_never_joins_split_chunks(tmp_path):
    para = " ".join(f"w{i}" for i in range(204))
    assert len(para) == 909
    doc, errors = _run(tmp_path, "## T\n\n" + para + "\n")
    assert errors == []
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [
        (1, 1), (799, 1), (109, 1)]
    assert doc.chunks[0].text == "T"


def test_list_items_greedy_like_paragraphs(tmp_path):
    items = "\n".join(
        "- " + " ".join(f"{c}{i}" for i in range(100))
        for c in "abc")
    doc, errors = _run(tmp_path, items + "\n")
    assert errors == []
    assert [len(e.content) for e in doc.elements] == [389] * 3
    assert [(len(c.text), len(c.source_element_ids))
            for c in doc.chunks] == [(779, 2), (389, 1)]
