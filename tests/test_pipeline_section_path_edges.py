r"""pipeline section_path 边角：跳级/回退/全类型
继承（Round 1630）。

新角度：R1629 锁标记变体——**heading 跳级、
向上回退、代码块与列表继承**零覆盖（R1596 只锁
相邻嵌套与同级重置）：

- **跳级**：# A 后直接 ### C → 'A > C'
  （不补隐含中间层）
- **向上回退**：## B 回到 # Z → 'Z' 干净重置
- **全类型继承**：代码围栏段落与 list_item
  都带所在节的 section_path
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


def _paths(doc):
    return [(e.type,
             e.source_locator["section_path"])
            for e in doc.elements]


def test_level_skip(tmp_path):
    doc = _run(
        tmp_path,
        "# A\n\ntext\n\n### C\n\nmore\n")
    assert _paths(doc) == [
        ("heading", "A"),
        ("paragraph", "A"),
        ("heading", "A > C"),
        ("paragraph", "A > C")]


def test_up_reset(tmp_path):
    doc = _run(
        tmp_path,
        "# A\n\n## B\n\nb\n\n# Z\n\nz\n")
    assert _paths(doc) == [
        ("heading", "A"),
        ("heading", "A > B"),
        ("paragraph", "A > B"),
        ("heading", "Z"),
        ("paragraph", "Z")]


def test_inheritance_all_types(tmp_path):
    doc = _run(
        tmp_path,
        "# Sec\n\n```py\nx=1\n```\n\n- li\n")
    assert _paths(doc) == [
        ("heading", "Sec"),
        ("paragraph", "Sec"),
        ("list_item", "Sec")]
