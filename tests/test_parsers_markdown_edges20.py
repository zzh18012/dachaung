r"""markdown 混合标记/混合下划线/tab 位置测试（Round 1498）。

probe 实证（edges1-19 与主文件未碰）：

- **三种无序标记混排**：'- a / * b / + c' → 三个独立
  list_item，marker 元数据统一 'unordered'（标记差异
  不进元素）
- **无序→有序切换**：'- a\n1. b' → ordered 标记正确切
  换
- **混合 setext 下划线不成标题**：'Title\n=-=' 与
  'Title\n-=-' → 合并 paragraph（setext RE 只认单字符
  纯下划线；'-=-' 也非 thematic break——含 '='）
- **'-\\titem' tab 做分隔**：列表标记后 tab 照常分隔
- **'#\\tHead' tab 做分隔**：ATX # 后 tab 照常成标题
- **表格 cell 内 tab 逐字保留**：'| a\\tb | c |' 原样
  进 content
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser


def _md(tmp_path, text):
    p = tmp_path / "probe.md"
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 混合列表标记 ----------

def test_mixed_unordered_markers(
        tmp_path):
    doc = _md(tmp_path,
              "- a\n* b\n+ c\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("list_item", "b"),
        ("list_item", "c"),
    ]
    assert all(
        e.metadata == {"ordered": False,
                       "marker": "unordered"}
        for e in doc.elements)
    assert doc.warnings == []


def test_unordered_then_ordered(
        tmp_path):
    doc = _md(tmp_path,
              "- a\n1. b\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("list_item", "b"),
    ]
    assert doc.elements[0].metadata == {
        "ordered": False,
        "marker": "unordered"}
    assert doc.elements[1].metadata == {
        "ordered": True,
        "marker": "ordered"}


# ---------- 混合 setext 下划线 ----------

def test_mixed_equals_dashes_not_setext(
        tmp_path):
    doc = _md(tmp_path,
              "Title\n=-=\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Title\n=-="),
    ]
    assert doc.warnings == []


def test_mixed_dashes_equals_not_setext(
        tmp_path):
    doc = _md(tmp_path,
              "Title\n-=-\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "Title\n-=-"),
    ]


# ---------- tab 位置 ----------

def test_tab_after_list_marker(
        tmp_path):
    doc = _md(tmp_path, "-\titem\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "item"),
    ]
    assert doc.warnings == []


def test_tab_after_hash_heading(
        tmp_path):
    doc = _md(tmp_path, "#\tHead\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "Head"),
    ]
    assert doc.elements[0].metadata == {
        "level": 1}


def test_tab_in_table_cell_preserved(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a\tb | c |\n"
        "| --- | --- |\n"
        "| 1 | 2 |\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| a\tb | c |\n"
         "| --- | --- |\n"
         "| 1 | 2 |"),
    ]
    assert doc.elements[0].metadata == {
        "row_count": 2,
        "col_count": 2,
        "source": "markdown_pipe_table",
    }
    assert doc.warnings == []
