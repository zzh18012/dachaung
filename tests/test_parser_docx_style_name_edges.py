r"""DOCX 样式名解析地雷——复数 typo 静默成 heading、0 级钳制、Subtitle 落 paragraph（Round 1960，a 优先级）。

`_is_heading_style`（fallback_parser.py:406）：s=="title" →
(True,1)；startswith("heading") 且后缀可 int → (True,
max(1,level))；后缀非 int（ValueError）→ **(True,1) 静默降
级**；否则 paragraph。**退化样式名**广扫（headings 复数/
heading0/裸 Heading/Subtitle 各形）实证零覆盖。探针 R1960
实证：

- **D1 "headings"（复数 typo）**：startswith 命中、int 失败
  → **heading level 1**——非标题样式被静默误判（metadata
  style 保留原名可追查）
- **D2 "heading 0"**：int 成功 0 → max(1,0) **钳制为 1**
- **D3 "Subtitle"（真 Word 内置）**：不匹配任何规则 →
  **paragraph**——语义上是标题层的副标题被当正文

判别式：若 startswith 改全词匹配或 int 失败改判 paragraph
则 D1 翻红；若取消 max(1,·) 钳制则 D2 翻红；若规则扩到
subtitle 则 D3 翻红。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE

from app.hash import compute_file_hash
from app.parsers.fallback_parser import FallbackParser


def _parse(style_name: str):
    with tempfile.TemporaryDirectory() as td:
        d = Document()
        try:
            st = d.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
        except ValueError:
            st = d.styles[style_name]
        d.add_paragraph("styled body", style=st)
        p = Path(td) / "s.docx"
        d.save(p)
        return FallbackParser().parse(p, compute_file_hash(p))


def test_plural_typo_silently_heading():
    """D1："headings" 复数 typo → heading level 1（int 失败静默降级）。"""
    d = _parse("headings")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].metadata["level"] == 1
    assert d.elements[0].metadata["style"] == "headings"
    assert d.warnings == []


def test_zero_level_clamped_to_one():
    """D2："heading 0" → max(1,0) 钳制 level 1。"""
    d = _parse("heading 0")
    assert [e.type for e in d.elements] == ["heading"]
    assert d.elements[0].metadata["level"] == 1
    assert d.elements[0].metadata["style"] == "heading 0"
    assert d.warnings == []


def test_builtin_subtitle_is_paragraph():
    """D3："Subtitle" 内置样式 → 不匹配 → paragraph。"""
    d = _parse("Subtitle")
    assert [e.type for e in d.elements] == ["paragraph"]
    assert d.elements[0].metadata["style"] == "Subtitle"
    assert d.warnings == []
