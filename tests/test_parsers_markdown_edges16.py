r"""app/parsers/markdown_parser.py 边角测试 - 第十六轮（Round 1473）。

新角度（probe 实证）CRLF 全结构 + 表格边界 + 栈语义
（edges1-15 未碰过；base 只锁过 CRLF 标题/段落两例）：
- **CRLF 表格**：全表识别成功、行内容归一 \n、line 1
- **CRLF 列表**：两个 list_item 正常
- **CRLF 引用**：多行 blockquote 内容用 **\n join**（\r\n
  归一后拼接）
- **CRLF 围栏带语言**：code_block language='python'
- **CRLF 混合结构**：heading/para/list/bq 全链路，行号
  1/3/5/7 精确
- **标题尾随空白剥掉**：'## Title   ' → 'Title'（含
  section_path 同步）
- **同名标题不消歧**：两个 '# Same' 的 section_path 都
  'Same'
- **表格前无空行**：para 与 table 各自成 element（表格
  检测不依赖前空行，table line 2）
- **缺尾管道不是表**：'| a | b\n| --- | ---\n| 1 | 2' →
  整块 paragraph
- **H2 后 H1 栈重置**：'## sub\n# top' → section_path
  'sub' → 'top'（弹到根，非 'sub > top'）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.markdown_parser import \
    MarkdownParser

TMP_NAME = "md_edge16_probe.md"


def _parse(tmp_path, text, name=TMP_NAME):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- CRLF 全结构 ----------

def test_crlf_table(tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b |\r\n| --- | --- |\r\n"
        "| 1 | 2 |\r\n")
    e = doc.elements[0]
    assert e.type == "table"
    assert e.content == (
        "| a | b |\n| --- | --- |\n| 1 | 2 |")
    assert e.metadata["row_count"] == 2
    assert e.source_locator["line"] == 1


def test_crlf_list(tmp_path):
    doc = _parse(
        tmp_path, "- a\r\n- b\r\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("list_item", "a"),
        ("list_item", "b"),
    ]


def test_crlf_bq_join_lf(tmp_path):
    doc = _parse(
        tmp_path, "> a\r\n> b\r\n")
    e = doc.elements[0]
    assert e.content == "a\nb"
    assert e.metadata["kind"] == \
        "blockquote"


def test_crlf_fence_lang(tmp_path):
    doc = _parse(
        tmp_path,
        "```python\r\nx=1\r\n```\r\n")
    e = doc.elements[0]
    assert e.content == "x=1"
    assert e.metadata["kind"] == "code_block"
    assert e.metadata["language"] == "python"


def test_crlf_mixed_structures(
        tmp_path):
    doc = _parse(
        tmp_path,
        "# T\r\n\r\npara\r\n\r\n- li\r\n\r\n"
        "> q\r\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("heading", "T"),
        ("paragraph", "para"),
        ("list_item", "li"),
        ("paragraph", "q"),
    ]
    assert [e.source_locator["line"]
            for e in doc.elements] == \
        [1, 3, 5, 7]
    assert all(
        e.source_locator["section_path"] == "T"
        for e in doc.elements)


# ---------- 标题变体 ----------

def test_heading_trailing_ws_stripped(
        tmp_path):
    doc = _parse(
        tmp_path, "## Title   \r\nbody\r\n")
    e = doc.elements[0]
    assert e.content == "Title"
    assert e.source_locator[
        "section_path"] == "Title"


def test_duplicate_headings_same_path(
        tmp_path):
    doc = _parse(
        tmp_path,
        "# Same\na\n# Same\nb\n")
    paths = [e.source_locator.get(
        "section_path")
        for e in doc.elements]
    assert paths == [
        "Same", "Same", "Same", "Same"]


def test_h1_after_h2_resets_stack(
        tmp_path):
    doc = _parse(
        tmp_path, "## sub\n# top\n")
    paths = [e.source_locator[
        "section_path"]
        for e in doc.elements
        if e.type == "heading"]
    assert paths == ["sub", "top"]


# ---------- 表格边界 ----------

def test_table_no_blank_before(
        tmp_path):
    doc = _parse(
        tmp_path,
        "para\n| a | b |\n| --- | --- |\n")
    assert [(e.type,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("paragraph", 1),
        ("table", 2),
    ]


def test_table_missing_trailing_pipes(
        tmp_path):
    doc = _parse(
        tmp_path,
        "| a | b\n| --- | ---\n| 1 | 2\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph",
         "| a | b\n| --- | ---\n| 1 | 2"),
    ]
    assert doc.warnings == []
