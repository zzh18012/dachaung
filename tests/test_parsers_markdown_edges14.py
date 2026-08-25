r"""app/parsers/markdown_parser.py 边角测试 - 第十四轮（Round 1465）。

新角度（probe 实证）标题合法性 + 引用定义 + 强调 vs 分隔
（edges1-13 未碰过；base 已覆盖 marker 混排/thematic 纯行/
html block，edges10 已覆盖脚注与 &nbsp; 实体，均避开）：
- **# 后无空格不是标题**：'#Heading no space' → paragraph
  字面保留（CommonMark 要求 # 后空白）
- **空标题降级**：'# ' → paragraph 内容 '#'
- **链接引用定义不解析**：'[ref]: http://x' 独立成段且
  正文 '[ref]' 也字面（两段互不相认）
- 删除线 '~~gone~~' 字面（不解析）
- ***text*** **带文字时不是 thematic break**（强调标记
  字面保留成 paragraph；纯 '***' 行才是 break——base 已测）
- **缩进 pipe 表仍是表**（每行 2 空格前缀）：e2e 全表解析
  成功且输出内容**归一去缩进**（base 只测过行级 RE）
- 原生 NBSP 字符（\\xa0，非 &nbsp; 实体）**保留在内容里**
- 列表后**无空行**直接跟正文 → item 与 paragraph 各自成
  element（非缩进，不算续行）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge14_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 标题合法性 ----------

def test_hash_no_space_not_heading(
        tmp_path):
    doc = _parse(
        tmp_path, "#Heading no space\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "#Heading no space"),
    ]
    assert doc.warnings == []


def test_hash_empty_title_degrades(
        tmp_path):
    doc = _parse(tmp_path, "# \n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "#"),
    ]


# ---------- 链接引用定义 ----------

def test_ref_def_literal(tmp_path):
    doc = _parse(
        tmp_path, "[ref]: http://x\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "[ref]: http://x"),
    ]


def test_ref_def_and_use_independent(
        tmp_path):
    doc = _parse(
        tmp_path,
        "[ref]: http://x\n\nuse [ref] here\n")
    assert [(e.type, e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("paragraph", "[ref]: http://x", 1),
        ("paragraph", "use [ref] here", 3),
    ]


# ---------- 强调 / 删除线 ----------

def test_strikethrough_literal(
        tmp_path):
    doc = _parse(tmp_path, "~~gone~~\n")
    assert doc.elements[
        0].content == "~~gone~~"
    assert doc.elements[0].type == \
        "paragraph"


def test_triple_star_text_not_break(
        tmp_path):
    doc = _parse(
        tmp_path, "***triple***\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "***triple***"),
    ]
    assert doc.warnings == []


# ---------- 缩进表 ----------

def test_indented_table_still_table(
        tmp_path):
    doc = _parse(
        tmp_path,
        "  | a | b |\n"
        "  | --- | --- |\n"
        "  | 1 | 2 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a | b |\n"
        "| --- | --- |\n| 1 | 2 |")
    assert e.metadata["row_count"] == 2
    assert e.metadata["col_count"] == 2


# ---------- 原生 NBSP ----------

def test_raw_nbsp_preserved(
        tmp_path):
    doc = _parse(
        tmp_path, "a b\n")
    assert doc.elements[
        0].content == "a b"
    assert doc.elements[
        0].source_locator["line"] == 1


# ---------- 列表后无空行 ----------

def test_list_then_para_no_blank(
        tmp_path):
    doc = _parse(
        tmp_path, "- a\npara\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("paragraph", "para"),
    ]
    assert [e.source_locator["line"]
            for e in doc.elements] == [1, 2]
