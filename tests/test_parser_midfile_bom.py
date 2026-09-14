r"""文件中段 BOM：内容逐字保留、行首杀标题、BOM-ipynb 报错（Round 1853）。

新角度（probe 实证；cross_edges3 只锁**文件起始** BOM 三种劣化，
中段 BOM 全库零覆盖）：
- **中段内容 BOM 保留**：html/md/txt 的 'a\\ufeffb' → U+FEFF
  逐字保留在 content，零错误零剥离（md 不影响其他块的标题识别）
- **行首 BOM（非文件首）杀标题**：'intro\\n\\n\\ufeff# Head' →
  '\\ufeff# Head' 成**字面段落**（标题 RE 不匹配带 BOM 行），
  与文件首 BOM 劣化同型但位置任意
- **BOM 前缀 ipynb**：合法 JSON 加 BOM → `ipynb_invalid_json`
  （json.loads 拒绝 BOM 字节流）+ 不写盘——与 R1852 原始非法字节
  的 `unexpected_parser_error` 是**不同错误码**
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single

BOM = b"\xef\xbb\xbf"
FEFF = chr(0xFEFF)


def test_mid_content_bom_preserved(tmp_path: Path):
    cases = [
        ("a.html", "html", b"<p>a" + BOM + b"b</p>"),
        ("a.md", "markdown", b"# T\n\na" + BOM + b"b\n"),
        ("a.txt", "text", b"a" + BOM + b"b\n"),
    ]
    for name, parser, raw in cases:
        p = tmp_path / name
        p.write_bytes(raw)
        out = tmp_path / (name + ".json")
        _, errs = process_single(p, out, parser_name=parser)
        assert errs == [], name
        data = json.loads(out.read_text(encoding="utf-8"))
        contents = [e["content"] for e in data["elements"]]
        assert f"a{FEFF}b" in contents, (name, contents)
        if parser == "markdown":
            assert data["elements"][0]["type"] == "heading"


def test_line_start_bom_mid_file_kills_heading(tmp_path: Path):
    p = tmp_path / "b.md"
    p.write_bytes(b"intro\n\n" + BOM + b"# Head\n\nbody\n")
    out = tmp_path / "b.json"
    _, errs = process_single(p, out, parser_name="markdown")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [(e["type"], e["content"]) for e in data["elements"]] == [
        ("paragraph", "intro"),
        ("paragraph", FEFF + "# Head"),
        ("paragraph", "body"),
    ]
    assert data["elements"][1]["source_locator"]["line"] == 3


def test_bom_ipynb_invalid_json(tmp_path: Path):
    p = tmp_path / "c.ipynb"
    p.write_bytes(BOM + b'{"nbformat": 4, "nbformat_minor": 5, '
                     b'"metadata": {}, "cells": []}')
    out = tmp_path / "c.json"
    _, errs = process_single(p, out, parser_name="ipynb")
    assert [e.code for e in errs] == ["ipynb_invalid_json"]
    assert not out.exists()
