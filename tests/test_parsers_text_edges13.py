r"""app/parsers/text_parser.py 边角测试 - 第十三轮（Round 1475）。

新角度（probe 实证）NBSP 语义 + 三种换行混排 + id 进位
（edges1-12 未碰过；edges12 已锁 VT 整行空行与 LS/NEL/PS
不切行，BOM 已由早期轮锁定，避开）：
- **NBSP 整行是空行**：'a\n\xa0\nb' → 两段 lines 1/3
  （\xa0.isspace() 为 True，落进空白行跳过分支）
- **NBSP 行内保留**：'a\xa0b' 单段原样（strip 只削两端）
- **NBSP 行尾不杀行**：'a\xa0\nb' → 单段 'a\xa0\nb'
  （含 NBSP 的行不是 blank，两行并入同段）
- **纯 NBSP 文件** → text_no_content 告警、零 element
- **NBSP 混空白行**（'\t \xa0 \t'）照样作段落分隔
- **三种换行混排一个文件**：'a\r\nb\rc\n\nd' → 首段
  'a\nb\nc' line 1、次段 'd' line 5（归一后统一 LF 计行）
- **CRLF+CR 空行混排**：'x\r\n\r y\r\n\r\nz' → 三段
  lines 1/3/5（'\r ' 归一出空白行）
- **element_id 万位进位**：10001 段 → e9999 之后是
  e10000（:04d 不截断，5 位自然进位）
"""

from __future__ import annotations

from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.text_parser import TextParser

NBSP = "\xa0"


def _parse(tmp_path, text, name="text_edge13_probe.txt"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8",
                 newline="")
    return TextParser().parse(
        p, compute_file_hash(p))


# ---------- NBSP 整行 ----------

def test_nbsp_line_blank(tmp_path):
    doc = _parse(
        tmp_path, "a\n" + NBSP + "\nb")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a", 1), ("b", 3),
    ]


def test_nbsp_inline_kept(tmp_path):
    doc = _parse(
        tmp_path, "a" + NBSP + "b")
    assert [e.content
            for e in doc.elements] == [
        "a" + NBSP + "b",
    ]


def test_nbsp_trailing_line_joins(
        tmp_path):
    doc = _parse(
        tmp_path, "a" + NBSP + "\nb")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a" + NBSP + "\nb", 1),
    ]


def test_nbsp_only_file_warning(
        tmp_path):
    doc = _parse(
        tmp_path, NBSP + "\n" + NBSP)
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["text_no_content"]


def test_nbsp_mixed_ws_line_blank(
        tmp_path):
    doc = _parse(
        tmp_path,
        "a\n\t " + NBSP + " \t\nb")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a", 1), ("b", 3),
    ]


# ---------- 三种换行混排 ----------

def test_mixed_newlines_all_three(
        tmp_path):
    doc = _parse(
        tmp_path, "a\r\nb\rc\n\nd")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("a\nb\nc", 1), ("d", 5),
    ]


def test_crlf_cr_blank_mix(
        tmp_path):
    doc = _parse(
        tmp_path,
        "x\r\n\r y\r\n\r\nz")
    assert [(e.content,
             e.source_locator["line"])
            for e in doc.elements] == [
        ("x", 1), ("y", 3), ("z", 5),
    ]


# ---------- id 进位 ----------

def test_element_id_rollover_10000(
        tmp_path):
    big = "\n\n".join(
        f"para{i}" for i in range(10001))
    doc = _parse(tmp_path, big,
                 name="big.txt")
    assert len(doc.elements) == 10001
    ids = [e.element_id
           for e in doc.elements]
    assert ids[9999].endswith(
        "::e9999")
    assert ids[10000].endswith(
        "::e10000")
