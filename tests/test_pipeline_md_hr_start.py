r"""pipeline Markdown 分隔线变体与列表起始号
（Round 1642）。

新角度：R1641 锁内联 raw——**'\*\*\*' /
'\_\_\_' 分隔线、非 1 起始有序列表**零覆盖：

- **'\*\*\*' 与 '\_\_\_' 都是分隔线**：整行
  丢弃（与 '------' 一致），不产出元素
- **起始号 5 的有序列表**：marker 'ordered'，
  起始号不保留在 metadata
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


def test_hr_stars_dropped(tmp_path):
    doc = _run(tmp_path, "above\n\n***\n\nbelow\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "above", {}),
        ("paragraph", "below", {})]


def test_hr_underscores_dropped(tmp_path):
    doc = _run(tmp_path, "above\n\n___\n\nbelow\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "above", {}),
        ("paragraph", "below", {})]


def test_ordered_start_number_dropped(tmp_path):
    doc = _run(tmp_path, "5. five\n6. six\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "five",
         {"ordered": True, "marker": "ordered"}),
        ("list_item", "six",
         {"ordered": True, "marker": "ordered"})]
