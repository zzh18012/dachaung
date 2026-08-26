r"""pipeline 超限两段不合并与图片不打断
合并（Round 1733）。

新角度：R1732 锁贪心合并——**764+189 超
800 各自成 chunk、html 段落跨 image 照常
合并（'aaa bbb'，ids 2）**零覆盖：

- **764 字符段 + 189 字符段**：两个
  chunk（764/189，各 1 id，合并会超
  max_chars）
- **p/img/p**：两段合并 'aaa bbb' 单
  chunk（image 元素被旁路，不参与也不打
  断合并）
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def test_over_limit_pair_separate(tmp_path):
    p = tmp_path / "d.txt"
    long_p = " ".join(f"w{i}" for i in range(175))
    short_p = " ".join(f"s{i}" for i in range(50))
    assert (len(long_p), len(short_p)) == (764, 189)
    p.write_text(long_p + "\n\n" + short_p,
                 encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="text")
    assert errors == []
    assert [(len(c.text),
             len(c.source_element_ids))
            for c in doc.chunks] == [
        (764, 1), (189, 1)]


def test_image_does_not_interrupt_merge(tmp_path):
    p = tmp_path / "d.html"
    p.write_text(
        '<p>aaa</p><img src="i.png" alt="A"><p>bbb</p>',
        encoding="utf-8")
    doc, errors = process_single(
        p, write_json=False, parser_name="html")
    assert errors == []
    assert [(e.type, e.content) for e in doc.elements] == [
        ("paragraph", "aaa"), ("image", None),
        ("paragraph", "bbb")]
    assert len(doc.chunks) == 1
    assert doc.chunks[0].text == "aaa bbb"
    assert len(doc.chunks[0].source_element_ids) == 2
