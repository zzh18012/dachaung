r"""markdown 空标题崩溃家族测试（Round 1486）。

背景：R1484 发现 '#   \\n' 空 ATX 标题 → ValueError 穿透。
本轮扫描崩溃家族的**安全边界**与**传播通道**（edges1-18
未碰过）：

- **setext 空 title 安全**：'   \\n---\\n' 空白行 + 分隔
  线 → 不产空标题、不崩溃，仅 md_no_content（setext 路
  径的 title 取自行内容，空白行直接跳过）
- **裸 '===' 自成段**：'   \\n===\\n' → 单 paragraph
  '==='（= 不是 thematic break，空白前导行不合并）
- **崩溃经 ipynb cell 通道传播**：markdown cell 的
  source 含 '#   \\n' → IpynbParser.parse 同样 ValueError
  穿透（ipynb 循环无 try/except；管线级由
  unexpected_parser_error 兜底，见 R1485）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.hash import compute_file_hash
from app.parsers.ipynb_parser import \
    IpynbParser
from app.parsers.markdown_parser import \
    MarkdownParser


def _md(tmp_path, text):
    p = tmp_path / "probe.md"
    p.write_text(text, encoding="utf-8",
                 newline="")
    return MarkdownParser().parse(
        p, compute_file_hash(p))


# ---------- setext 安全边界 ----------

def test_setext_ws_title_line_safe(
        tmp_path):
    doc = _md(tmp_path, "   \n---\n")
    assert doc.elements == []
    assert [w.code for w in doc.warnings] \
        == ["md_no_content"]


def test_bare_equals_own_paragraph(
        tmp_path):
    doc = _md(tmp_path, "   \n===\n")
    assert [(e.type, e.content)
            for e in doc.elements] == [
        ("paragraph", "==="),
    ]
    assert doc.warnings == []


# ---------- ipynb 通道传播 ----------

def test_ipynb_md_crash_cell_propagates(
        tmp_path):
    nb = {"nbformat": 4,
          "nbformat_minor": 5,
          "metadata": {},
          "cells": [{"cell_type": "markdown",
                     "source": "#   \nbody\n",
                     "metadata": {}}]}
    p = tmp_path / "crash.ipynb"
    p.write_text(json.dumps(nb),
                 encoding="utf-8")
    with pytest.raises(
            ValueError, match=
            "必须至少有 content 或"
            " resource_path"):
        IpynbParser().parse(
            p, compute_file_hash(p))
