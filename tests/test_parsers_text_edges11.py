r"""app/parsers/text_parser.py 边角测试 - 第十一轮（Round 1458）。

新角度（probe 实证）行号语义 + 空白保留（edges1-10 未碰
过的坐标与内容细节）：
- CRLF 与**纯 CR**（老 Mac）都归一为 LF，行号一致
  （'a\r\n\r\nb' 与 'a\r\rb' 都是 line 1/3）
- 含空白的"空行"（' '、'\t'）算作分隔行且**计入行号**
  （'a\n \n\t\nb' → b 在 line 4）
- 段内行**前导空白保留**（除首行被外层 strip）：'  a\n  b'
  → 'a\n  b'；行尾空白同理（'a   \nb' 内部两个空格保留、
  末行 tab 剥掉）
- BOM **保留在内容里**（'﻿# first para'，不像 markdown
  杀标题——text 无结构可杀）
- 纯空白文件 → text_no_content；开头空行后段落从 line 4
  起；连续多空行 y 在 line 6
"""

from __future__ import annotations

from app.hash import compute_file_hash
from app.parsers.text_parser import \
    TextParser, _split_paragraphs

TMP_NAME = "txt_edge11_probe.txt"


def _parse(tmp_path, data, name=TMP_NAME):
    p = tmp_path / name
    if isinstance(data, str):
        data = data.encode("utf-8")
    p.write_bytes(data)
    return TextParser().parse(
        p, compute_file_hash(p))


# ---------- 换行归一与行号 ----------

def test_crlf_line_numbers(tmp_path):
    doc = _parse(tmp_path, "a\r\n\r\nb\r\n")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a", 1), ("b", 3),
    ]


def test_cr_only_normalized(tmp_path):
    doc = _parse(tmp_path, "a\r\rb\r")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a", 1), ("b", 3),
    ]


def test_whitespace_blank_lines_count(
        tmp_path):
    doc = _parse(
        tmp_path, "a\n \n\t\nb")
    assert doc.elements[
        1].source_locator["line"] == 4


def test_late_start_line(tmp_path):
    doc = _parse(
        tmp_path, "\n\n\nlate start")
    assert doc.elements[
        0].source_locator["line"] == 4


def test_multi_blank_between(
        tmp_path):
    doc = _parse(
        tmp_path, "x\n\n\n\n\ny")
    assert doc.elements[
        1].source_locator["line"] == 6


# ---------- 空白保留 ----------

def test_inner_leading_ws_kept(
        tmp_path):
    doc = _parse(
        tmp_path, "  a\n  b\n\n c")
    assert doc.elements[
        0].content == "a\n  b"
    assert doc.elements[
        1].content == "c"


def test_trailing_ws_partial(
        tmp_path):
    doc = _parse(
        tmp_path, "a   \nb\t\n\nnext")
    assert doc.elements[
        0].content == "a   \nb"
    assert doc.elements[
        1].content == "next"


# ---------- BOM ----------

def test_bom_kept_in_content(
        tmp_path):
    doc = _parse(
        tmp_path, "﻿# first para\n\nsecond")
    assert doc.elements[
        0].content == "﻿# first para"
    assert doc.elements[
        1].content == "second"


# ---------- 边界 ----------

def test_only_blanks_warning(
        tmp_path):
    doc = _parse(
        tmp_path, " \n\t\n  \n")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["text_no_content"]


def test_single_line_no_newline(
        tmp_path):
    doc = _parse(tmp_path, "only")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("only", 1),
    ]


def test_split_direct_simple():
    assert _split_paragraphs(
        "a\n\nb") == [(1, "a"), (3, "b")]
    assert _split_paragraphs("") == []
    assert _split_paragraphs(
        "  \n ") == []
