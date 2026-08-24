r"""app/parsers/text_parser.py 边角测试 - 第九轮（Round 1421）。

新角度（probe 实证）控制字符与坏字节（历史只锁过 \r\n /
BOM，未碰 ASCII 控制符与非法 UTF-8）：
- \x0c 换页 / \x0b 垂直制表 / \x1c\x1d 分隔符 / \x00 NUL：
  全部原样进 content、不段落分割、schema 仍绿
- 孤立 \r 归一成 \n **嵌在段内**（不分割段落）；空行照常
  分割
- 合法 UTF-8 NEL（0xC2 0x85）→ '\x85' 字符；孤立坏字节
  0x85 → 替换字符
- U+2028/U+2029 原样保留
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path, name, data):
    p = tmp_path / name
    p.write_bytes(data)
    doc, errors = process_single(
        p, None, parser_name="text",
        max_chars=800)
    assert errors == []
    return doc


# ---------- ASCII 控制符 ----------

def test_formfeed_raw(tmp_path):
    doc = _run(
        tmp_path, "ff.txt",
        b"Page1\x0cPage2\n")
    assert [e.content
            for e in doc.elements] == [
        "Page1\x0cPage2"]


def test_vtab_raw(tmp_path):
    doc = _run(
        tmp_path, "vt.txt",
        b"Before\x0bAfter\n")
    assert [e.content
            for e in doc.elements] == [
        "Before\x0bAfter"]


def test_nul_raw(tmp_path):
    doc = _run(
        tmp_path, "nul.txt",
        b"Before\x00After\n")
    assert [e.content
            for e in doc.elements] == [
        "Before\x00After"]


def test_nul_schema_valid(
        tmp_path):
    from app.schema import is_valid
    doc = _run(
        tmp_path, "nul.txt",
        b"Before\x00After\n")
    assert is_valid(doc.to_dict())


def test_file_group_sep_raw(
        tmp_path):
    doc = _run(
        tmp_path, "fg.txt",
        b"Group1\x1cGroup2\x1d"
        b"End\n")
    assert doc.elements[
        0].content == \
        "Group1\x1cGroup2\x1dEnd"


def test_controls_single_para(
        tmp_path):
    doc = _run(
        tmp_path, "ff.txt",
        b"Page1\x0cPage2\n")
    assert len(doc.elements) == 1


# ---------- 孤立 CR ----------

def test_lone_cr_newline_inline(
        tmp_path):
    doc = _run(
        tmp_path, "cr.txt",
        b"Old mac line1\r"
        b"Old mac line2\r")
    assert [e.content
            for e in doc.elements] == [
        "Old mac line1\n"
        "Old mac line2"]


def test_lone_cr_no_split(
        tmp_path):
    doc = _run(
        tmp_path, "cr.txt",
        b"Old mac line1\r"
        b"Old mac line2\r")
    assert len(doc.elements) == 1


def test_cr_blank_line_still_splits(
        tmp_path):
    doc = _run(
        tmp_path, "mix.txt",
        b"Mac para one\rand two\n"
        b"\nNext para\n")
    assert [e.content
            for e in doc.elements] == [
        "Mac para one\nand two",
        "Next para"]


# ---------- NEL / 坏字节 / Unicode 分隔符 ----------

def test_utf8_nel_kept(tmp_path):
    doc = _run(
        tmp_path, "nel.txt",
        "Line1\x85Line2\n"
        .encode("utf-8"))
    assert doc.elements[
        0].content == \
        "Line1\x85Line2"


def test_invalid_byte_replaced(
        tmp_path):
    doc = _run(
        tmp_path, "bad.txt",
        b"Line1\x85Line2\n")
    assert doc.elements[
        0].content == \
        "Line1�Line2"


def test_unicode_seps_kept(
        tmp_path):
    doc = _run(
        tmp_path, "ls.txt",
        "Uni sep and"
        " ps\n"
        .encode("utf-8"))
    assert doc.elements[
        0].content == \
        "Uni sep " \
        "and ps"


def test_unicode_seps_schema(
        tmp_path):
    from app.schema import is_valid
    doc = _run(
        tmp_path, "ls.txt",
        "Uni sep and"
        " ps\n"
        .encode("utf-8"))
    assert is_valid(doc.to_dict())


# ---------- chunk 层 ----------

def test_cr_para_chunk(tmp_path):
    doc = _run(
        tmp_path, "mix.txt",
        b"Mac para one\rand two\n"
        b"\nNext para\n")
    assert [c.text
            for c in doc.chunks] == [
        "Mac para one\nand two "
        "Next para"]
    assert len(doc.chunks) == 1
    assert len(doc.chunks[0]
               .source_element_ids) == 2


def test_invalid_byte_chunk(
        tmp_path):
    doc = _run(
        tmp_path, "bad.txt",
        b"Line1\x85Line2\n")
    assert doc.chunks[
        0].text == \
        "Line1�Line2"
