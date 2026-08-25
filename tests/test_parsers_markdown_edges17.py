r"""app/parsers/markdown_parser.py 边角测试 - 第十七轮（Round 1479）。

新角度（probe 实证）分隔行 RE 的最短横线 + 列数自适应 +
围栏空白体（edges1-16 未碰过；edges12 已锁带空格 ':---: '
容忍、base 已锁 ordered/tilde/hr/setext，避开）：
- **2 短横线杀死表格**：'| :-- | :-: |'（带空格）与
  '|:--|:-:|'（不带空格）→ 整块 paragraph（分隔行 RE 要
  ≥3 横线；空格无关）
- **3 横线不带空格 + 冒号 → 仍是表**：'|:---:|---:|' 被
  识别且规范化输出 '| --- | --- |'
- **参差行拓宽表格**：2 列 header + 3 列数据行 → header
  补空 '| a | b |  |'、col_count=3（对照 edges 单元级
  短行填充，此处锁 e2e 长行拓宽）
- **围栏体纯空白保留**：'```\\n   \\n```' → code_block
  content **'   ' 原样**（非空 → 不发 md_empty_code_block，
  对照空体告警链）
- **空表头不是表**：'|  |\\n| --- |\\n| x |' → 整块
  paragraph（空 header 单元格不成立表格）
- **列表项内容以数字开头不误判**：'- 1. looks ordered'
  → list_item '1. looks ordered'、unordered
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge17_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 分隔行最短横线 ----------

def test_align_short_dashes_not_table(
        tmp_path):
    for sep in ("| :-- | :-: |",
                "|:--|:-:|"):
        doc = _parse(
            tmp_path,
            "| a | b |\n" + sep
            + "\n| 1 | 2 |\n")
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph",
             "| a | b |\n" + sep
             + "\n| 1 | 2 |"),
        ]
        assert doc.warnings == []


def test_align_nospace_3dash_is_table(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\n|:---:|---:|\n"
        "| 1 | 2 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a | b |\n"
        "| --- | --- |\n| 1 | 2 |")
    assert e.metadata["col_count"] == 2


# ---------- 参差行 ----------

def test_ragged_row_widens_table(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\n| --- | --- |\n"
        "| 1 | 2 | 3 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a | b |  |\n"
        "| --- | --- | --- |\n"
        "| 1 | 2 | 3 |")
    assert e.metadata["col_count"] == 3
    assert e.metadata["row_count"] == 2


# ---------- 围栏空白体 ----------

def test_ws_only_fence_body_preserved(
        tmp_path):
    doc = _parse(
        tmp_path, "```\n   \n```\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == "   "
    assert e.metadata == {
        "kind": "code_block",
        "language": "",
    }
    assert doc.warnings == []


# ---------- 空表头 ----------

def test_empty_header_not_table(tmp_path):
    doc = _parse(
        tmp_path,
        "|  |\n| --- |\n| x |\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "|  |\n| --- |\n| x |"),
    ]
    assert doc.warnings == []


# ---------- 列表项数字内容 ----------

def test_num_content_list_stays_unordered(
        tmp_path):
    doc = _parse(
        tmp_path,
        "- 1. looks ordered\n")
    e = doc.elements[0]
    assert e.type == "list_item"
    assert e.content == "1. looks ordered"
    assert e.metadata["ordered"] is False
