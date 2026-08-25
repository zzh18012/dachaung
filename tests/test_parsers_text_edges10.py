r"""app/parsers/text_parser.py 边角测试 - 第十轮（Round 1444）。

新角度（probe 实证）文件编码退化（历史 txt 考察全在合法
UTF-8 字节流内，从未跨编码）：
- UTF-16LE 无 BOM：按 UTF-8 读出 NUL 交错
  'U\\x00T\\x00F\\x001\\x006\\x00 ...'（每字符后跟 \\x00）
- UTF-16LE 带 BOM：BOM 两字节 → '\\ufffd\\ufffd' 前缀 +
  NUL 交错；UTF-16BE 带 BOM：'\\x00B\\x00E\\x00 ...'
  NUL 前缀式
- UTF-16 CJK '你好世界' → 乱码 '��`O}Y\\x16NLu'（无编码
  探测，全程 UTF-8 容错解码）
- UTF-8 BOM：'\\ufeff' **留在 content 里**不剥；光杆 BOM
  文件（3 字节）→ 单元素 '\\ufeff'
- latin-1 0xE9 / cp1252 0x93 0x94 → 各自一个 '\\ufffd'
- 空文件 → 0 元素 + text_no_content 告警；管线层
  no_extracted_elements 错误链
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.hash import compute_file_hash
from app.parsers.text_parser import \
    TextParser
from app.pipeline import process_single


def _txt(tmp_path, name, data):
    p = tmp_path / (name + ".txt")
    p.write_bytes(data)
    return p


def _parse(p):
    return TextParser().parse(
        p, compute_file_hash(p))


# ---------- UTF-16 无 BOM ----------

def test_utf16le_nul_interleaved(
        tmp_path):
    p = _txt(tmp_path, "u16",
             "UTF16 text here"
             .encode("utf-16-le"))
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "U\x00T\x00F\x001\x006\x00 " \
        "\x00t\x00e\x00x\x00t\x00 " \
        "\x00h\x00e\x00r\x00e\x00"


# ---------- UTF-16 带 BOM ----------

def test_utf16le_bom_replacement(
        tmp_path):
    p = _txt(tmp_path, "u16b",
             "BOM utf16 text"
             .encode("utf-16"))
    doc = _parse(p)
    c = doc.elements[0].content
    assert c.startswith(
        "��B\x00O\x00M\x00")
    assert "\x00u\x00t\x00f\x001\x00" \
        "6\x00" in c


def test_utf16be_bom_nul_prefix(
        tmp_path):
    p = _txt(tmp_path, "u16be",
             "BE bom text"
             .encode("utf-16-be"))
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "\x00B\x00E\x00 \x00b\x00o" \
        "\x00m\x00 \x00t\x00e\x00x" \
        "\x00t"


def test_utf16_cjk_mojibake(
        tmp_path):
    p = _txt(tmp_path, "u16cjk",
             "你好世界"
             .encode("utf-16"))
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "��`O}Y\x16NLu"


# ---------- UTF-8 BOM ----------

def test_utf8_bom_kept(
        tmp_path):
    p = _txt(
        tmp_path, "u8bom",
        b"\xef\xbb\xbfutf8 bom text")
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "﻿utf8 bom text"


def test_bom_only_single(
        tmp_path):
    p = _txt(tmp_path, "justbom",
             b"\xef\xbb\xbf")
    doc = _parse(p)
    assert [e.content
            for e in doc.elements] == [
        "﻿"]
    assert doc.warnings == []


# ---------- 单字节编码 ----------

def test_latin1_replacement(
        tmp_path):
    p = _txt(tmp_path, "l1",
             b"caf\xe9 latin")
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "caf� latin"


def test_cp1252_quotes(
        tmp_path):
    p = _txt(tmp_path, "cp",
             b"smart \x93quotes\x94")
    doc = _parse(p)
    assert doc.elements[
        0].content == \
        "smart �quotes�"


# ---------- 空文件 ----------

def test_empty_no_content(
        tmp_path):
    p = _txt(tmp_path, "e", b"")
    doc = _parse(p)
    assert doc.elements == []
    assert [w.code
            for w in doc.warnings] == [
        "text_no_content"]


def test_empty_pipeline_error(
        tmp_path):
    p = _txt(tmp_path, "e2", b"")
    doc, errors = process_single(
        p, None,
        parser_name="text",
        max_chars=800)
    assert doc is None
    assert [e.code
            for e in errors] == [
        "no_extracted_elements"]
    det = errors[0].to_dict()[
        "details"]
    assert det["warnings"][0][
        "code"] == "text_no_content"


# ---------- 通用 ----------

def test_utf16_schema_valid(
        tmp_path):
    from app.schema import is_valid
    p = _txt(tmp_path, "s",
             "SC".encode("utf-16-le"))
    doc = _parse(p)
    assert is_valid(doc.to_dict())


def test_utf8_bom_chunk(
        tmp_path):
    p = _txt(
        tmp_path, "c",
        b"\xef\xbb\xbfutf8 bom text")
    doc, errors = process_single(
        p, None,
        parser_name="text",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == \
        "﻿utf8 bom text"


def test_nul_content_chunk(
        tmp_path):
    p = _txt(tmp_path, "nc",
             "AB".encode("utf-16-le"))
    doc, errors = process_single(
        p, None,
        parser_name="text",
        max_chars=800)
    assert errors == []
    assert doc.chunks[
        0].text == \
        "A\x00B\x00"
