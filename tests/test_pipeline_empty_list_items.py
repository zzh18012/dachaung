r"""pipeline md 空列表项退化（Round 1670）。

新角度：R1669 锁属性实体——**'- ' 与
'1. ' 空内容项不成 list_item**零覆盖：

- **'- ' 空项**：paragraph '-'（仅剩标记）
- **'1. ' 空有序项**：paragraph '1.'
- **夹在真实项中间**：空项打断列表成
  paragraph，前后 list_item 保留
"""

from __future__ import annotations

from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, text):
    p = tmp_path / "d.md"
    p.write_bytes(text.encode("utf-8"))
    doc, errors = process_single(
        p, write_json=False, parser_name="markdown")
    assert errors == []
    return doc


def test_empty_bullet_degrades(tmp_path):
    doc = _run(tmp_path, "- \n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "-", {})]


def test_empty_ordered_degrades(tmp_path):
    doc = _run(tmp_path, "1. \n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("paragraph", "1.", {})]


def test_empty_item_between_real(tmp_path):
    doc = _run(tmp_path, "- real\n- \n- also\n")
    assert [(e.type, e.content, e.metadata)
            for e in doc.elements] == [
        ("list_item", "real",
         {"ordered": False, "marker": "unordered"}),
        ("paragraph", "-", {}),
        ("list_item", "also",
         {"ordered": False, "marker": "unordered"})]
