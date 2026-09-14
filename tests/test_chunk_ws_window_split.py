r"""chunker isspace 窗口切分机制：\r\n / \t / U+2028 全是切分点（Round 1860）。

新角度（probe 实证 + structural.py:64 代码核对；R1859 的
'aaaa\r\n'×10 输入 '\r' 恰落上界 40 造成"硬切"误读，本轮用
**周期错开**输入实证窗口回扫机制；R1851 称 U+2028/NEL/VT
"惰性"同理需修正——它们 isspace()，窗口内被优先选中）：
- **\r\n 窗口切分**：'aa\r\n'×30 @40 → **恰 3 个 38 字符
  chunk**（'aa\r\n'×9+'aa'）——切在窗口内最右 '\n'（39 位）
  而非上界 40，切点 '\r\n' 被消费
- **\t 与 U+2028 同机制**：'aa\t'×30 与 ('ab'+U2028)×30 @40
  → 38/38/11 三段（末段 rstrip 剥尾随分隔符）
- **低于上限多空格逐字保留**：'xxxx'+10 空格+'yyyy'+6 空格
  +'zzzz'（28 字符）@40 → 单 chunk 原样（内部空格不折叠）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

U2028 = chr(0x2028)


def _chunks(tmp_path: Path, src: str, max_chars: int = 40) -> list[str]:
    p = tmp_path / "a.ipynb"
    p.write_text(json.dumps({
        "nbformat": 4, "nbformat_minor": 5, "metadata": {},
        "cells": [{"cell_type": "raw", "source": src}]}),
        encoding="utf-8")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="ipynb",
                             max_chars=max_chars)
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    return [c["text"] for c in data["chunks"]]


def test_chunk_crlf_window_split(tmp_path: Path):
    texts = _chunks(tmp_path, "aa\r\n" * 30)
    assert texts == ["aa\r\n" * 9 + "aa"] * 3


def test_chunk_tab_and_u2028_window_split(tmp_path: Path):
    texts = _chunks(tmp_path, "aa\t" * 30)
    assert texts == [
        "aa\t" * 12 + "aa",
        "aa\t" * 12 + "aa",
        "aa\t" * 3 + "aa"]

    texts = _chunks(tmp_path, ("ab" + U2028) * 30)
    assert texts == [
        ("ab" + U2028) * 12 + "ab",
        ("ab" + U2028) * 12 + "ab",
        ("ab" + U2028) * 3 + "ab"]


def test_chunk_multispace_preserved_under_max(tmp_path: Path):
    src = "x" * 4 + " " * 10 + "y" * 4 + " " * 6 + "z" * 4
    texts = _chunks(tmp_path, src)
    assert texts == [src]
