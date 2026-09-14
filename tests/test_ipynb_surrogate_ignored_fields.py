r"""ipynb metadata 代理崩溃 + 忽略字段 + nbformat 浮点泄漏（Round 1855）。

新角度（probe 实证，grep 核实零覆盖——edges12/15 已锁 int language
与 minor 字符串透传；metadata 代理、忽略字段集合、nbformat 浮点无覆盖）：
- **metadata 代理崩溃**：kernelspec language 含 '\\ud800' 转义 →
  与 R1854 元素内容同型的 **UnicodeEncodeError 穿透**（写盘
  ensure_ascii=False 全局失守，不限元素通道）
- **忽略字段集合**：execution_count="1"（字符串）、outputs="notalist"
  （字符串）、cell id="cell-1" 全部**静默忽略**——code cell 照发、
  零错误零告警
- **nbformat 浮点泄漏**：nbformat=4.7（浮点）**被接受**（版本门未
  拦）且 verbatim 进 metadata——与字符串 "4" 的 TypeError 崩溃
  （edges12 已锁）形成类型依赖对照
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pipeline import process_single


def test_ipynb_metadata_surrogate_crashes_at_write(tmp_path: Path):
    p = tmp_path / "a.ipynb"
    p.write_bytes(b'{"nbformat": 4, "nbformat_minor": 5, '
                  b'"metadata": {"kernelspec": {"language": "py\\ud800ton"}}, '
                  b'"cells": [{"cell_type": "raw", "source": "ok"}]}')
    out = tmp_path / "a.json"
    with pytest.raises(UnicodeEncodeError):
        process_single(p, out, parser_name="ipynb")


def test_ipynb_ignored_fields(tmp_path: Path):
    p = tmp_path / "b.ipynb"
    p.write_bytes(b'{"nbformat": 4, "nbformat_minor": 5, "metadata": {}, '
                  b'"cells": [{"cell_type": "code", "source": "print(1)", '
                  b'"outputs": "notalist", "execution_count": "1", '
                  b'"id": "cell-1"}]}')
    out = tmp_path / "b.json"
    _, errs = process_single(p, out, parser_name="ipynb")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data["elements"]) == 1
    e = data["elements"][0]
    assert e["type"] == "paragraph"
    assert e["content"] == "print(1)"
    assert e["metadata"] == {"kind": "code_cell", "language": ""}


def test_ipynb_nbformat_float_leak(tmp_path: Path):
    p = tmp_path / "c.ipynb"
    p.write_bytes(b'{"nbformat": 4.7, "nbformat_minor": 5, "metadata": {}, '
                  b'"cells": [{"cell_type": "raw", "source": "ok"}]}')
    out = tmp_path / "c.json"
    _, errs = process_single(p, out, parser_name="ipynb")
    assert errs == []
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["metadata"]["nbformat"] == 4.7
    assert data["elements"][0]["content"] == "ok"
