r"""app/parsers/markdown_parser.py 边角测试 - 第十八轮（Round 1484）。

新角度（probe 实证）空标题崩溃 + 转义管道不处理 + bq 内
围栏 + setext 尾巴（edges1-17 未碰过；edges12 已锁
'## Title ##' 闭合序列、edges10 已锁实体/HTML 字面、
edges14 已锁 '#Heading' 无空格标题，避开）：
- **纯 '#' + 空白标题 → 忽略 + 警告（BUG-md-1 已修）**：
  '#   \\n' 与 '###   \\n' 命中 ATX RE、strip 后空 title →
  忽略该行并记 empty_markdown_construct_ignored 警告，
  不发空节点、不崩溃（提交 1 曾按崩溃现状锁定，提交 2 修复）
- **'###' 无空格不成标题**：整块 paragraph 字面
- **'\\|' 转义管道不处理**：单元格在 '\\|' 处被切开
  （'a \\' 与 'b' 分列）→ 表格拓宽到 3 列、数据行补空
- **bq 内围栏字面**：'> ```' 不开围栏 → blockquote 内容
  为 '```\nx=1\n```' 字面（kind=blockquote）
- **setext 下划线带尾巴不成标题**：'--- extra' → 整块
  paragraph 'Title\n--- extra'
- **列表标记无空格**：'-item'/'*item' → paragraph 字面
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge18_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 空标题（BUG-md-1 已修：忽略 + 警告） ----------

def test_space_only_heading_ignored(tmp_path):
    """'#   \\n' 空 title → 该行忽略 + 警告，正文保留。

    修复语义：不发空节点、不崩溃；记
    empty_markdown_construct_ignored（details 带 line/construct）。
    """
    for text in ("#   \nbody\n",
                 "###   \nbody\n"):
        doc = _parse(tmp_path, text)
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph", "body"),
        ]
        hits = [w for w in doc.warnings
                if w.code ==
                "empty_markdown_construct_ignored"]
        assert len(hits) == 1
        assert hits[0].details[
            "construct"] == "atx_heading"


def test_empty_hash_no_space_paragraph(
        tmp_path):
    doc = _parse(
        tmp_path, "###\nbody\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "###\nbody"),
    ]


# ---------- 转义管道 ----------

def test_escaped_pipe_splits_cell(
        tmp_path):
    """批次 5 契约 §3：\\| 不分列且反转义；re-render 再转义回 \\|（roundtrip 幂等）。"""
    doc = _parse(
        tmp_path,
        "| a \\| b | c |\n"
        "| --- | --- |\n| 1 | 2 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a \\| b | c |\n"
        "| --- | --- |\n"
        "| 1 | 2 |")
    assert e.metadata["col_count"] == 2


# ---------- bq 内围栏 ----------

def test_fence_in_bq_literal(tmp_path):
    doc = _parse(
        tmp_path,
        "> ```\n> x=1\n> ```\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "```\nx=1\n```"
    assert e.metadata == {
        "kind": "blockquote"}
    assert doc.warnings == []


# ---------- setext 尾巴 ----------

def test_setext_trailing_not_underline(
        tmp_path):
    doc = _parse(
        tmp_path, "Title\n--- extra\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "Title\n--- extra"),
    ]


# ---------- 列表标记无空格 ----------

def test_list_marker_no_space(tmp_path):
    for marker in ("-", "*"):
        doc = _parse(
            tmp_path, marker + "item\n")
        assert [(e.type, e.content)
                for e in doc.elements] == [
            ("paragraph",
             marker + "item"),
        ]
