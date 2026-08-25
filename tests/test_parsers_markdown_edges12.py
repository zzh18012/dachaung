r"""app/parsers/markdown_parser.py 边角测试 - 第十二轮（Round 1455）。

新角度（probe 实证）围栏不对称 + section_path 栈 + 表格分隔
行变体（edges1-11 未碰过）：
- 缩进围栏**不被识别**（开栏用原始 line 匹配，关栏却 strip）：
  '   ```' 并入段落；后面的 ``` 反而开栏到 EOF → 空 code
  block + md_empty_code_block 告警
- 4 反引号栏内 3 反引号行**会关栏**（startswith 只看前 3
  字符）；尾随 '````' 再开空栏 → 告警
- 关栏行带尾随文本 '``` extra' → **整行吞掉**（文本不出现
  在任何 element）
- ~~~ 栏内 ``` 行是**代码内容**（栏字符不混用）
- section_path 栈跳跃：H1→H4→H2 → 'H1 > H4' 后弹到
  'H1 > H2'；栏内 '## ' 不影响 path
- 单列 pipe 表**不是表**（分隔行正则要求 ≥2 列）→ 整块
  并入 paragraph
- ':---:' 对齐冒号被**容忍**且规范化成 '---'；
  参差行补空列（col_count=3）
- BOM 杀死标题识别（'\\ufeff# Title' → 整段 paragraph）
- 空 blockquote '>' 行**静默消失**（无 element 无告警）
- 空_alt 图片 '![](url)' 合法；URL 带括号不匹配 → 字面
  paragraph；多位有序号 '10)'/'123.' 正常
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge12_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- 围栏不对称 ----------

def test_indented_fence_not_open(
        tmp_path):
    doc = _parse(
        tmp_path,
        "text\n   ```\ncode\n```\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "text\n   ```\ncode"
    assert [w.code for w in doc.warnings] \
        == ["md_empty_code_block"]


def test_longer_close_reopens_empty(
        tmp_path):
    doc = _parse(
        tmp_path,
        "````\ncode\n```\nstill code?\n````\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "code"),
        ("paragraph", "still code?"),
    ]
    assert [w.code for w in doc.warnings] \
        == ["md_empty_code_block"]


def test_close_line_trailing_swallowed(
        tmp_path):
    doc = _parse(
        tmp_path,
        "```\ncode\n``` extra\nafter\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "code"),
        ("paragraph", "after"),
    ]
    assert doc.warnings == []


def test_tilde_fence_backtick_content(
        tmp_path):
    doc = _parse(
        tmp_path,
        "~~~\n```python\ncode\n~~~\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "```python\ncode"
    assert e.metadata["kind"] == "code_block"
    assert e.metadata["language"] == ""


# ---------- section_path 栈 ----------

def test_section_path_jump(tmp_path):
    doc = _parse(
        tmp_path,
        "# H1\n#### H4\ntext\n## H2\nmore\n")
    paths = [e.source_locator.get(
        "section_path") for e in doc.elements]
    assert paths == [
        "H1", "H1 > H4", "H1 > H4",
        "H1 > H2", "H1 > H2",
    ]
    assert [e.type for e in doc.elements] \
        == ["heading", "heading",
            "paragraph", "heading",
            "paragraph"]


def test_heading_in_fence_no_path(
        tmp_path):
    doc = _parse(
        tmp_path,
        "# H1\n```\n## Not Heading\n```\nafter\n")
    assert [e.content
            for e in doc.elements] == [
        "H1", "## Not Heading", "after",
    ]
    assert doc.elements[1].source_locator[
        "section_path"] == "H1"
    assert doc.elements[2].source_locator[
        "section_path"] == "H1"


# ---------- 表格分隔行变体 ----------

def test_single_column_not_table(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a |\n| --- |\n| 1 |\n")
    assert len(doc.elements) == 1
    assert doc.elements[0].type == "paragraph"
    assert doc.elements[0].content == \
        "| a |\n| --- |\n| 1 |"


def test_colon_sep_normalized(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\n| :---: | ---: |\n| 1 | 2 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a | b |\n| --- | --- |\n| 1 | 2 |"
    )
    assert e.metadata["row_count"] == 2
    assert e.metadata["col_count"] == 2


def test_ragged_rows_padded(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\n| --- | --- |\n| 1 |\n| 1 | 2 | 3 |\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.metadata["col_count"] == 3
    assert e.metadata["row_count"] == 3
    assert "| 1 |  |  |" in e.content
    assert "| 1 | 2 | 3 |" in e.content


# ---------- BOM / 空 blockquote ----------

def test_bom_kills_heading(tmp_path):
    doc = _parse(
        tmp_path, "﻿# Title\nbody\n")
    assert len(doc.elements) == 1
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content.startswith("﻿")
    assert "body" in e.content


def test_empty_blockquote_vanishes(
        tmp_path):
    doc = _parse(
        tmp_path, ">\n>\npara\n")
    assert [e.content
            for e in doc.elements] == ["para"]
    assert doc.warnings == []
    assert doc.elements[0].source_locator[
        "line"] == 3


# ---------- 图片 / 有序列表 ----------

def test_image_empty_alt(tmp_path):
    doc = _parse(
        tmp_path,
        "![](http://x/y.png)\n")
    e = doc.elements[0]
    assert e.type == "image"
    assert e.content is None
    assert e.metadata["alt"] == ""
    assert e.resource_path == "http://x/y.png"


def test_image_paren_url_literal(
        tmp_path):
    doc = _parse(
        tmp_path,
        "![a](http://x/(y).png)\n")
    e = doc.elements[0]
    assert e.type == "paragraph"
    assert e.content == \
        "![a](http://x/(y).png)"


def test_ordered_multidigit(tmp_path):
    doc = _parse(
        tmp_path,
        "10) item ten\n123. item\n")
    assert [(e.content, e.metadata["ordered"])
            for e in doc.elements] == [
        ("item ten", True),
        ("item", True),
    ]


# ---------- 标题变体 ----------

def test_seven_hashes_paragraph(
        tmp_path):
    doc = _parse(
        tmp_path, "####### seven\n")
    assert doc.elements[0].type == "paragraph"


def test_heading_trailing_hashes(
        tmp_path):
    doc = _parse(
        tmp_path, "## Title ##\n")
    e = doc.elements[0]
    assert e.type == "heading"
    assert e.content == "Title"
    assert e.metadata["level"] == 2
    assert e.source_locator[
        "section_path"] == "Title"


def test_thematic_spaced(tmp_path):
    doc = _parse(
        tmp_path,
        "- - -\n*  *  *\nafter\n")
    assert [e.content
            for e in doc.elements] == ["after"]
    assert doc.warnings == []
