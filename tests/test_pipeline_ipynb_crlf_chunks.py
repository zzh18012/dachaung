r"""ipynb raw cell CRLF 保留 + chunk 硬切边界（Round 1859）。

新角度（probe 实证；crlf_text_ipynb R1719 只锁 **markdown cell**
'\r\n' 归一 '\n'——raw cell 逐字保留与 chunk 层行为零覆盖）：
- **raw cell 不归一**：source "line1\r\nline2" → content
  'line1\r\nline2' 逐字（与 markdown cell 归一形成 cell 类型
  不对称）
- **\r\n 不是 chunk 分隔符**：'aaaa\r\n'×10 @40 → 恰在 40 字符
  **硬切**（非分隔位切分），切点 '\r\n' 被消费，两半各自保留
  内部 \r\n
- **cell 间空格连接**：两 cell 合 chunk 用 ' '，cell 内部 \r\n
  照留（'x\r\ny\r\nz tail'，双元素 id）
"""

from __future__ import annotations

import json
from pathlib import Path

from app.pipeline import process_single


def _run(tmp_path: Path, cells: list, max_chars: int = 40) -> dict:
    p = tmp_path / "a.ipynb"
    p.write_text(json.dumps({
        "nbformat": 4, "nbformat_minor": 5, "metadata": {},
        "cells": cells}), encoding="utf-8")
    out = tmp_path / "a.json"
    _, errs = process_single(p, out, parser_name="ipynb",
                             max_chars=max_chars)
    assert errs == []
    return json.loads(out.read_text(encoding="utf-8"))


def test_ipynb_raw_cell_crlf_preserved(tmp_path: Path):
    data = _run(tmp_path, [
        {"cell_type": "raw", "source": "line1\r\nline2"}])
    assert data["elements"][0]["content"] == "line1\r\nline2"


def test_chunk_crlf_not_separator_hard_split(tmp_path: Path):
    data = _run(tmp_path, [
        {"cell_type": "raw", "source": "aaaa\r\n" * 10}])
    chunks = data["chunks"]
    assert len(chunks) == 2
    assert chunks[0]["text"] == "aaaa\r\n" * 6 + "aaaa"
    assert chunks[1]["text"] == "aaaa\r\n" * 2 + "aaaa"
    assert all(len(c["source_element_ids"]) == 1 for c in chunks)


def test_chunk_two_cells_join_space_keep_crlf(tmp_path: Path):
    data = _run(tmp_path, [
        {"cell_type": "raw", "source": ["x\r\n", "y\r\n", "z"]},
        {"cell_type": "raw", "source": "tail"}])
    assert len(data["chunks"]) == 1
    assert data["chunks"][0]["text"] == "x\r\ny\r\nz tail"
    assert len(data["chunks"][0]["source_element_ids"]) == 2
