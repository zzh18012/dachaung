r"""pipeline 顺序合并贪心规则：合并到不超
max_chars 为止（Round 1732）。

新角度：R1731 锁百段合并——**两段 389 合
并 779 单 chunk（两 source ids）、三段
389 时前两段合并 779 第三段独立开新 chunk**
零覆盖：

- **2×389 字符段**：单 chunk 779
  （sequential，source_element_ids 2 个）
- **3×389 字符段**：779（2 ids）+ 389
  （1 id）——贪心：加入第三段会超 800，
  故新开 chunk
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, n):
    p = tmp_path / "d.txt"
    paras = [" ".join(f"{ch}{i}" for i in range(100))
             for ch in "abc"[:n]]
    p.write_text("\n\n".join(paras), encoding="utf-8")
    return process_single(
        p, write_json=False, parser_name="text")


def test_two_paragraphs_merge(tmp_path):
    doc, errors = _run(tmp_path, 2)
    assert errors == []
    assert [len(e.content) for e in doc.elements] == [389, 389]
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0].text) == 779
    assert doc.chunks[0].metadata["strategy"] == "sequential"
    assert len(doc.chunks[0].source_element_ids) == 2


def test_three_paragraphs_greedy_split(tmp_path):
    doc, errors = _run(tmp_path, 3)
    assert errors == []
    assert [len(e.content) for e in doc.elements] == [389] * 3
    assert [(len(c.text),
             len(c.source_element_ids))
            for c in doc.chunks] == [
        (779, 2), (389, 1)]
    assert all(c.metadata["strategy"] == "sequential"
               for c in doc.chunks)
