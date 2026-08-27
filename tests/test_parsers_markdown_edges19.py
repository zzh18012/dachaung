r"""markdown 表格相邻关系与分隔行语义测试（Round 1488）。

probe 实证（2 列表格，避开 edges12 锁定的单列非表格）：

- **空行分隔的两个表 → 两个独立 table**（各 2x2，互不合并）
- **无空行相邻的两个表 → 合并成 5x2 单表**：第二个表头
  '| b | y |' 与第二个分隔行 '| --- | --- |' 全部降级为
  数据行（分隔行字面 '---' 入表）
- **分隔行作数据行**：'| --- | --- |' 紧跟正常分隔行 →
  被当数据行吸收，内容逐字保留 m=2x2
- **纯管道表头 '| | | |' 是表**：3 个空 cell 成表头，
  内容规范化为 '|  |  |  |'（cell 补空格），参差数据行
  '| 1 | 2 |  |' 右侧补空 cell → m=2x3（与 edges17 单列
  空 cell 成段互补）
- **表后紧跟 '## H' → header-only 表 + heading**：仅表头
  无数据行的表仍产出 table，row_count=1
- **表后紧跟文本 → header-only 表 + paragraph**：边界清
  晰，不合并入表
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


# ---------- 两表相邻 ----------

def test_two_tables_blank_separated(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a | x |\n| --- | --- |\n"
        "| 1 | 2 |\n\n"
        "| b | y |\n| --- | --- |\n"
        "| 3 | 4 |\n")
    assert len(doc.elements) == 2
    assert all(
        e.type == "table"
        for e in doc.elements)
    assert [(e.metadata["row_count"],
             e.metadata["col_count"])
            for e in doc.elements] == [
        (2, 2), (2, 2)]
    assert doc.elements[1].content == \
        "| b | y |\n| --- | --- |\n| 3 | 4 |"
    assert doc.warnings == []


def test_two_tables_no_sep_merged(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a | x |\n| --- | --- |\n"
        "| 1 | 2 |\n"
        "| b | y |\n| --- | --- |\n"
        "| 3 | 4 |\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata["row_count"] == 5
    assert e.metadata["col_count"] == 2
    assert e.content == \
        "| a | x |\n| --- | --- |\n" \
        "| 1 | 2 |\n| b | y |\n" \
        "| --- | --- |\n| 3 | 4 |"
    assert doc.warnings == []


def test_separator_as_data_row(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a | b |\n| --- | --- |\n"
        "| --- | --- |\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata["row_count"] == 2
    assert e.metadata["col_count"] == 2
    assert e.content == \
        "| a | b |\n| --- | --- |\n" \
        "| --- | --- |"
    assert doc.warnings == []


def test_pipes_only_header_is_table(
        tmp_path):
    doc = _md(
        tmp_path,
        "| | | |\n"
        "| --- | --- | --- |\n"
        "| 1 | 2 |\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata["row_count"] == 2
    assert e.metadata["col_count"] == 3
    assert e.content == \
        "|  |  |  |\n" \
        "| --- | --- | --- |\n" \
        "| 1 | 2 |  |"
    assert doc.warnings == []


# ---------- 表后直接跟内容 ----------

def test_table_then_heading_no_blank(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a | x |\n| --- | --- |\n"
        "## H\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| a | x |\n| --- | --- |"),
        ("heading", "H"),
    ]
    assert doc.elements[0].metadata[
        "row_count"] == 1
    assert doc.warnings == []


def test_table_then_text_no_blank(
        tmp_path):
    doc = _md(
        tmp_path,
        "| a | x |\n| --- | --- |\n"
        "tail text\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("table",
         "| a | x |\n| --- | --- |"),
        ("paragraph", "tail text"),
    ]
    assert doc.elements[0].metadata[
        "col_count"] == 2
    assert doc.warnings == []
