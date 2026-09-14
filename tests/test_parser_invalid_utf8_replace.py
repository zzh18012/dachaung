r"""无效 UTF-8 输入：三家族 errors=replace 静默替换、ipynb 报错（Round 1852）。

新角度（probe 实证，grep 核实 html/md/text/ipynb 的解码失败路径
全库零覆盖——fallback_edges 的 latin-1 是 PDF 构造字节，非解码测试）：
- **三家族静默替换**：html/md/text 对非法字节 \\x80\\x83 照常成功
  （errors=[]、文件照写），content 含 U+FFFD 替换符——无 warning、
  无 error record
- **ipynb 解码失败**：非法字节进 JSON → `unexpected_parser_error`、
  不写盘（json.loads 字节流解码失败）
- **截断多字节**：3 字节 CJK 前缀 '\\xe4\\xb8'（缺尾字节）折叠为
  **单个** U+FFFD（'\\xe4\\xb8'+'\\x80' 共 2 个替换符）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

FFFD = chr(0xFFFD)


def test_invalid_utf8_replaced_across_families(tmp_path: Path):
    cases = [
        ("a.html", "html", b"<p>ok \x80\x83 bad</p>"),
        ("a.md", "markdown", b"ok \x80\x83 bad\n"),
        ("a.txt", "text", b"ok \x80\x83 bad\n"),
    ]
    for name, parser, raw in cases:
        p = tmp_path / name
        p.write_bytes(raw)
        out = tmp_path / (name + ".json")
        _, errs = process_single(p, out, parser_name=parser)
        assert errs == [], (name, [(e.code, e.message) for e in errs])
        data = json.loads(out.read_text(encoding="utf-8"))
        content = data["elements"][0]["content"]
        assert content.startswith("ok"), (name, content)
        assert FFFD in content, (name, content)
        assert content.endswith("bad"), (name, content)


def test_invalid_utf8_ipynb_errors(tmp_path: Path):
    p = tmp_path / "a.ipynb"
    p.write_bytes(b'{"nbformat": 4, "cells": '
                  b'[{"cell_type": "raw", "source": "\x80"}]}')
    out = tmp_path / "a.ipynb.json"
    _, errs = process_single(p, out, parser_name="ipynb")
    assert [e.code for e in errs] == ["unexpected_parser_error"]
    assert not out.exists()


def test_truncated_multibyte_single_replacement(tmp_path: Path):
    p = tmp_path / "b.txt"
    p.write_bytes(b"ok \xe4\xb8 mid \x80 end")
    out = tmp_path / "b.json"
    _, errs = process_single(p, out, parser_name="text")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    content = data["elements"][0]["content"]
    assert content == f"ok {FFFD} mid {FFFD} end"
    assert content.count(FFFD) == 2
