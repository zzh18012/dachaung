"""TextParser 解码替换语义的精确刻画（ChatGPT 5.6 Sol 2026-08-27 边界②）。

修正此前"无效字节逐字节 → U+FFFD"的错误概括：Python
decode("utf-8", errors="replace") 按 Unicode maximal subpart 规则——
孤立非法单字节各自替换为一个 U+FFFD；截断的多字节序列（如 E2 82
后接非延续字节或 EOF）整体替换为一个 U+FFFD。

替换次数全部用 element.content 直接精确断言（.count），不依赖
required_markers 子串匹配。holdout fixture（b"\\x80\\xff"）为两个
孤立非法单字节 → 恰好两个 U+FFFD，其连续序列 marker
PAD_END+U+FFFD×2+TAIL_START 同时钉住位置与次数（若多出一个替换符，
连续序列不同，子串不命中）。

BOM 政策（本阶段明示，非由"规格未提及"推导）：保留 U+FEFF 为普通
非空白字符——首段保留、不影响分段、不重复出现。

空文件状态：解析器级成功（errors=[]）、0 elements、0 chunks、
text_no_content 警告；pipeline 级按既定不变量报 no_extracted_elements
（edges10 test_empty_pipeline_error 已钉住）。
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.text_parser import TextParser
from app.schema import validate

REPL = "�"
BOM = "﻿"


def _parse_bytes(tmp_path: Path, name: str, data: bytes):
    p = tmp_path / name
    p.write_bytes(data)
    return TextParser().parse(p, source_hash="9" * 64)


# ---------- 孤立非法单字节：各一个 U+FFFD ----------


def test_two_isolated_invalid_bytes_two_replacements(tmp_path: Path):
    doc = _parse_bytes(tmp_path, "a.txt", b"head\x80\xff tail")
    assert len(doc.elements) == 1
    c = doc.elements[0].content
    assert c == f"head{REPL}{REPL} tail"
    assert c.count(REPL) == 2


def test_gpt_table_ff_ff(tmp_path: Path):
    """ChatGPT 独立核对表：FF FF → 两个 U+FFFD。"""
    doc = _parse_bytes(tmp_path, "b.txt", b"\xff\xff")
    assert doc.elements[0].content.count(REPL) == 2


def test_isolated_byte_between_valid_ascii(tmp_path: Path):
    doc = _parse_bytes(tmp_path, "c.txt", b"A\x80B")
    assert doc.elements[0].content == f"A{REPL}B"
    assert doc.elements[0].content.count(REPL) == 1


# ---------- 截断多字节序列：整体一个 U+FFFD ----------


def test_gpt_table_truncated_e2_82_eof(tmp_path: Path):
    """ChatGPT 独立核对表：E2 82 后直接 EOF → 一个 U+FFFD（非两个）。"""
    doc = _parse_bytes(tmp_path, "d.txt", b"abc\xe2\x82")
    assert doc.elements[0].content == f"abc{REPL}"
    assert doc.elements[0].content.count(REPL) == 1


def test_truncated_sequence_then_valid_byte(tmp_path: Path):
    """E2 82 后接非延续字节 B：截断序列整体一个 U+FFFD，B 正常解出。"""
    doc = _parse_bytes(tmp_path, "e.txt", b"A\xe2\x82B")
    assert doc.elements[0].content == f"A{REPL}B"
    assert doc.elements[0].content.count(REPL) == 1


def test_truncated_four_byte_sequence(tmp_path: Path):
    """F0 9F 98（4 字节序列缺尾）→ 一个 U+FFFD。"""
    doc = _parse_bytes(tmp_path, "f.txt", b"x\xf0\x9f\x98y")
    assert doc.elements[0].content == f"x{REPL}y"
    assert doc.elements[0].content.count(REPL) == 1


# ---------- BOM：显式政策"保留 U+FEFF" ----------


def test_bom_kept_as_ordinary_char(tmp_path: Path):
    doc = _parse_bytes(
        tmp_path, "g.txt", b"\xef\xbb\xbfBOM_A\n\nBOM_B\n"
    )
    assert len(doc.elements) == 2
    assert doc.elements[0].content.startswith(BOM)
    joined = "\n".join(e.content for e in doc.elements)
    assert joined.count(BOM) == 1
    assert doc.elements[1].content == "BOM_B"
    validate(doc.to_dict())


# ---------- 空文件：明确解析状态 / 总元素数 / chunk 数 ----------


def test_empty_file_full_state(tmp_path: Path):
    doc = _parse_bytes(tmp_path, "h.txt", b"")
    assert doc.errors == []
    assert doc.elements == []
    assert doc.chunks == []
    assert [w.code for w in doc.warnings] == ["text_no_content"]
    validate(doc.to_dict())


def test_whitespace_only_file_full_state(tmp_path: Path):
    doc = _parse_bytes(tmp_path, "i.txt", b" \t\r\n\t \r\n")
    assert doc.errors == []
    assert doc.elements == []
    assert doc.chunks == []
    assert [w.code for w in doc.warnings] == ["text_no_content"]
    validate(doc.to_dict())
