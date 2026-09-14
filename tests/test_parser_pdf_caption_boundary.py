r"""PDF 题注正则边界机制锁定：尾分隔符必需 + 前置空格可零 + 长题注优先（Round 1902，a 优先级）。

grep 零覆盖（edges131/145/186 锁的是分隔类变体/真实 docx/五变体，
均未锁：行尾无分隔符边界、数字前零空格、题注对 80 字长规则的
优先级）。探针 R1902 实证（`_CAPTION_RE` :50-53
`^\s*(?:Table|Figure|Fig\.?|表|图)\s*[0-9０-９]+[\.、:\s]`）：

- **尾分隔符必需**：'Table 1' / 'Figure 12'（行尾即数字尾）→
  **不匹配**——正则要求数字后跟 [\\.、:\\s]；落 heading
  （short_line 启发式）。'Table 1.' / 'Figure 12:' 对照匹配
- **前置空格可零**：`\s*` 是零或多——'Figure1.'、'表2、'、
  'Fig3 x' 全匹配（Fig 还可无点）
- **题注优先于长度规则**：109 字 'Table 1: xxx…' → caption
  （caption 检查在 ≤80 短行规则**之前**——分类优先级
  caption > heading > paragraph）；同长无前缀 → paragraph
"""

from __future__ import annotations

from app.parsers.fallback_parser import _classify_pdf_paragraph, _is_caption


def test_pdf_caption_requires_trailing_separator():
    """判别式：数字后无分隔符（行尾）→ 不匹配 → 落 heading；
    带分隔符对照 → caption。"""
    assert _is_caption("Table 1") is False
    assert _is_caption("Figure 12") is False
    assert _is_caption("Table 1.") is True
    assert _is_caption("Figure 12:") is True
    assert _classify_pdf_paragraph("Table 1") == (
        "heading", {"level": 0, "heuristic": "short_line"})


def test_pdf_caption_leading_space_optional():
    """判别式：数字前空格可零（\\s* 零或多）——'Figure1.'、'表2、'、
    'Fig3 x'（Fig 无点 + 零空格 + 空格分隔）全 caption。"""
    assert _is_caption("Figure1.") is True
    assert _is_caption("表2、") is True
    assert _is_caption("Fig3 x") is True
    assert _classify_pdf_paragraph("Figure1.") == (
        "caption", {"heuristic": "caption_regex"})


def test_pdf_caption_wins_over_length_rule():
    """判别式：109 字 'Table 1: …' → caption（题注检查在 80 字长
    短行规则之前）；同长无题注前缀 → paragraph。"""
    long_caption = "Table 1: " + "x" * 100
    assert len(long_caption) > 80
    assert _classify_pdf_paragraph(long_caption) == (
        "caption", {"heuristic": "caption_regex"})
    assert _classify_pdf_paragraph("y" * 100) == ("paragraph", {})
