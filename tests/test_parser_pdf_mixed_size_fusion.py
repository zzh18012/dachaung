r"""PDF 混字号行融合 + 分类字号不可见性锁定（Round 1893，a 优先级）。

R1893 探针发现（现有构造器全部固定 12pt，多字号几何无覆盖）：

- **混字号行融合**：行聚类容差是绝对磅值 ±3.0（:129，不随字号
  缩放）——24pt 行与 8pt 行的 y 中心可落入彼此容差 → 跨字号
  链式并成一行（探针：24pt 'Results' + 8pt 'Results' + 24pt
  题注行融合为单元素，bbox 高 114）
- **题注身份被吞**：被融合的 24pt 题注行（'Figure 1.' 前缀）不
  再拥有 caption 元素——融合文本 'Results Results Figure 1. …'
  整体按短行启发式判 heading；几何上隔离的 8pt 题注正常成
  caption。现实后果：大字号题注（常见排版）紧邻正文时题注丢失
- **分类字号不可见**：分类器只收文本（:274），字号信号在 words
  → 段落聚合时被丢弃——同文本 8pt 与 24pt 分类恒同（探针长行
  双字号均 paragraph）；字号只活在 bbox 几何里
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf

_LONG = (
    "This is a display-size line of body text that exceeds eighty "
    "characters in total length easily"
)


def _size_page(runs: list[tuple[float, float, float, str]]) -> bytes:
    parts = []
    for x, y, size, text in runs:
        parts.append(f"BT /F1 {size:g} Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _make_mixed_size_pdf(path: Path) -> None:
    """三段混字号布局：24/8pt 'Results' + 24pt 题注紧邻（融合区）；
    8pt 题注隔离；同长行双字号对照。"""
    page = _size_page([
        (50, 740, 24, "Results"),
        (50, 700, 8, "Results"),
        (50, 650, 24, "Figure 1. Tiny caption text in display size"),
        (50, 600, 8, "Figure 2. Same caption shape in footnote size"),
        (50, 540, 24, _LONG),
        (50, 480, 8, _LONG),
    ])
    path.write_bytes(_build_pdf([page]))


def test_pdf_mixed_size_lines_fuse_into_one_element(tmp_path):
    """混字号融合：绝对容差 3.0 不随字号缩放——24pt + 8pt + 24pt
    三行链式并成一个元素，bbox 高 114（跨 24/8/24pt 三行）。"""
    pdf_path = tmp_path / "sizes.pdf"
    _make_mixed_size_pdf(pdf_path)
    elements, warnings = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert warnings == []
    fused = elements[0]
    assert fused.content == (
        "Results Results Figure 1. Tiny caption text in display size"
    )
    assert fused.type == "heading"  # 融合文本短且无终止标点
    bbox = fused.source_locator["bbox"]
    assert round(bbox[3] - bbox[1], 2) == 114.0


def test_pdf_fused_display_caption_loses_caption_identity(tmp_path):
    """题注身份被吞：24pt 题注行融入融合块（无独立 caption 元素）；
    几何隔离的 8pt 题注正常 caption——紧邻正文的大字号题注丢失。"""
    pdf_path = tmp_path / "sizes.pdf"
    _make_mixed_size_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    captions = [e for e in elements if e.type == "caption"]
    assert len(captions) == 1
    assert captions[0].content == (
        "Figure 2. Same caption shape in footnote size"
    )
    # 融合块里 'Figure 1.' 前缀存在但类型是 heading 不是 caption
    assert "Figure 1." in elements[0].content
    assert elements[0].type == "heading"


def test_pdf_classification_is_font_size_blind(tmp_path):
    """字号不可见：同文本 8pt 与 24pt 分类恒同（都 paragraph）；
    字号只体现在 bbox 高度（24 vs 8）。"""
    pdf_path = tmp_path / "sizes.pdf"
    _make_mixed_size_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    longs = [e for e in elements if e.content == _LONG]
    assert len(longs) == 2
    assert [e.type for e in longs] == ["paragraph", "paragraph"]
    heights = sorted(
        round(e.source_locator["bbox"][3] - e.source_locator["bbox"][1], 2)
        for e in longs
    )
    assert heights == [8.0, 24.0]
