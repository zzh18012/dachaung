r"""app/parsers/markdown_parser.py 边角测试 - 第十一轮（Round 1377）。

补强未触达面（probe 实证，历史对 task list 零覆盖）：
- task list 复选框字面保留：'- [ ] todo' → list_item '[ ] todo'
  （有序/无序/star 全一样）
- 嵌套列表不支持：缩进子项降级为 paragraph 且首层缩进被剥
  （'- inner'）；三层嵌套时只剥一层（'- b\\n    - c' 深层缩进
  保留）；tab 缩进同 2 空格
- 续行不并入 item：'- item\\n  cont line' → item + 独立 paragraph
- 空 item '- ' → paragraph '-'（不是 list_item）
- 强调标记字面保留（'**bold** item'）
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import MarkdownParser


def _parse(md):
    with tempfile.TemporaryDirectory() as td:
        tp = Path(td)
        (tp / "t.md").write_text(md, encoding="utf-8")
        return MarkdownParser().parse(
            tp / "t.md",
            compute_file_hash(tp / "t.md"))


# ---------- task list 复选框 ----------

def test_task_unchecked_literal():
    doc = _parse("- [ ] todo\n- [x] done\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "[ ] todo"),
        ("list_item", "[x] done")]


def test_task_in_ordered_list():
    doc = _parse("1. [ ] one\n2. [x] two\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "[ ] one"),
        ("list_item", "[x] two")]


def test_task_star_marker():
    doc = _parse("* [ ] s\n")
    assert doc.elements[0].content == "[ ] s"


def test_task_numbers_dropped():
    doc = _parse("1. first\n2. second\n")
    assert [e.content for e in doc.elements
            ] == ["first", "second"]


# ---------- 嵌套降级 ----------

def test_nested_two_space_demoted():
    doc = _parse("- outer\n  - inner\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "outer"),
        ("paragraph", "- inner")]


def test_nested_four_space_demoted():
    doc = _parse("- outer\n    - inner\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "outer"),
        ("paragraph", "- inner")]


def test_nested_tab_demoted():
    doc = _parse("- outer\n\t- inner\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "outer"),
        ("paragraph", "- inner")]


def test_three_level_strips_one():
    doc = _parse("- a\n  - b\n    - c\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("paragraph", "- b\n    - c")]


# ---------- 续行 / 独立段 ----------

def test_continuation_separate_paragraph():
    doc = _parse("- item\n  cont line\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "item"),
        ("paragraph", "cont line")]


def test_item_then_blank_paragraph():
    doc = _parse("- item\n\nstandalone\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "item"),
        ("paragraph", "standalone")]


def test_blank_between_items_still_items():
    doc = _parse("- a\n\n- b\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("list_item", "b")]


# ---------- 空 item / 标记 ----------

def test_empty_item_is_paragraph_dash():
    doc = _parse("- \n- b\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "-"),
        ("list_item", "b")]


def test_mixed_markers_all_items():
    doc = _parse("- dash\n+ plus\n* star\n")
    assert [e.type for e in doc.elements
            ] == ["list_item"] * 3
    assert [e.content for e in doc.elements
            ] == ["dash", "plus", "star"]


def test_bold_marker_literal():
    doc = _parse("- **bold** item\n")
    assert doc.elements[0].content == \
        "**bold** item"


# ---------- 与 heading 共存 ----------

def test_heading_then_list():
    doc = _parse("# real heading\n- item\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "real heading"),
        ("list_item", "item")]


def test_list_section_path_none():
    doc = _parse("- item\n")
    assert "section_path" not in \
        doc.elements[0].source_locator


# ---------- schema ----------

def test_task_board_passes_schema():
    from app.schema import is_valid
    doc = _parse("- [ ] todo\n- [x] done\n")
    assert is_valid(doc.to_dict())


def test_nested_board_no_warnings():
    doc = _parse("- outer\n  - inner\n")
    assert doc.warnings == []
