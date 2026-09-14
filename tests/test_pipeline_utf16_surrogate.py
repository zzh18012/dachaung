r"""UTF-16 误判 NUL 保留 + ipynb 未配对代理写盘崩溃（Round 1854）。

新角度（probe 实证；evaluation 侧的 utf-16/surrogate 测试是标注
JSON 加载与指标层，**app 管线解析/写盘路径**零覆盖）：
- **UTF-16LE 误判**：ASCII 的 UTF-16LE 字节流（字母+NUL 交替）
  全部是合法 UTF-8 → 逐字解码成 NUL 掺杂 content（24 字符含 12
  个 NUL），零 FFFD、零错误——与 R1852 非法字节替换形成对照
- **未配对代理写盘崩溃**：ipynb source 含 JSON 转义 '\\ud800' →
  json.loads 接受成 lone surrogate → 写盘 `ensure_ascii=False`
  阶段 **UnicodeEncodeError 直接穿透 process_single**（结构化
  errors 不变量在此输入下失守——记录实际行为）
- **合法代理对**：'\\ud83d\\ude00' 转义 → json.loads 组合成 😀、
  正常写盘（同机制的安全半边）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline import process_single


def test_utf16le_misdecoded_nul_preserved(tmp_path: Path):
    p = tmp_path / "a.txt"
    p.write_bytes("<p>hello</p>".encode("utf-16-le"))
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="text")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    content = data["elements"][0]["content"]
    assert len(content) == 24
    assert content.count("\x00") == 12
    assert content.count(chr(0xFFFD)) == 0
    assert content.startswith("<\x00p\x00")


def test_ipynb_unpaired_surrogate_crashes_at_write(tmp_path: Path):
    p = tmp_path / "b.ipynb"
    p.write_bytes(b'{"nbformat": 4, "nbformat_minor": 5, '
                  b'"metadata": {}, "cells": '
                  b'[{"cell_type": "raw", "source": "a\\ud800 b"}]}')
    out = tmp_path / "b.json"
    with pytest.raises(UnicodeEncodeError):
        process_single(p, out, parser_name="ipynb")


def test_ipynb_valid_surrogate_pair_roundtrip(tmp_path: Path):
    p = tmp_path / "c.ipynb"
    p.write_bytes(b'{"nbformat": 4, "nbformat_minor": 5, '
                  b'"metadata": {}, "cells": '
                  b'[{"cell_type": "raw", "source": "a\\ud83d\\ude00 b"}]}')
    out = tmp_path / "c.json"
    _, errs = process_single(p, out, parser_name="ipynb")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["elements"][0]["content"] == "a\U0001F600 b"
