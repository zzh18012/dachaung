r"""BACKLOG 候选 B 真实 PDF 多栏版：元素级跨栏融合（Round 1890，b 优先级）。

**特征锁定（characterization），不是期望行为规格**。R1887 已在
单元级（合成 word-dict）锁定候选 B 机制；本轮用手写最小双栏
PDF（复用 R1888 的 PDF 构造器，无网格线、纯文本定位）走完整
`_parse_pdf` 路径，证明缺陷在**元素级**同样发生——即真实 PDF
（如 real-04 多栏布局）无需任何特殊结构即可触发。

实证（探针 Round 1890）：
- caption 元素内容被右栏正文**逐行穿插**：
  'Figure 1. System The model achieves high architecture overview
  accuracy on all benchmarks'（左栏题注两行 + 右栏两行交替融合）
- 正文融合行级联误判 heading（候选 C 机制叠加工候选 B 几何）
- 两元素 bbox 均横跨双栏（x0=左栏起点 50，x1≈442-469 右栏内）
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf


def _text_page(runs: list[tuple[float, float, str]]) -> bytes:
    """一页内容流：纯文本定位（(x, y_baseline, text) 列表）。"""
    parts = []
    for x, y, text in runs:
        parts.append(f"BT /F1 12 Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
    return "\n".join(parts).encode("latin-1")


def _make_two_col_pdf(path: Path) -> None:
    """单页双栏：左栏 x=50（题注 2 行 + 正文 1 行），右栏 x=320
    （正文 2 行 + 正文 1 行），同行基线对齐。"""
    page = _text_page([
        (50, 700, "Figure 1. System"),
        (320, 700, "The model achieves high"),
        (50, 686, "architecture overview"),
        (320, 686, "accuracy on all benchmarks"),
        (50, 650, "Left column body text"),
        (320, 650, "Right column body text"),
    ])
    path.write_bytes(_build_pdf([page]))


def test_backlog_candB_pdf_caption_element_crosscolumn_pollution(tmp_path):
    """元素级污染：caption 元素内容被右栏正文逐行穿插（左栏题注
    'Figure 1. System / architecture overview' 与右栏两行交替融合），
    仍按前缀判 caption——内容错而类型对。"""
    pdf_path = tmp_path / "twocol.pdf"
    _make_two_col_pdf(pdf_path)
    elements, warnings = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert warnings == []
    captions = [e for e in elements if e.type == "caption"]
    assert len(captions) == 1
    assert captions[0].content == (
        "Figure 1. System The model achieves high "
        "architecture overview accuracy on all benchmarks"
    )
    assert captions[0].metadata == {"heuristic": "caption_regex"}


def test_backlog_candB_pdf_body_fused_and_cascade_misclassified_heading(tmp_path):
    """阅读顺序损坏 + 级联：两栏正文合进**同一个**元素（栏序交错
    而非先左后右），且融合行无终止标点 → 级联误判 heading（候选 C
    机制叠加）。"""
    pdf_path = tmp_path / "twocol.pdf"
    _make_two_col_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert len(elements) == 2
    other = next(e for e in elements if e.type != "caption")
    assert other.content == "Left column body text Right column body text"
    assert other.type == "heading"
    assert other.metadata == {"level": 0, "heuristic": "short_line"}


def test_backlog_candB_pdf_element_bbox_spans_both_columns(tmp_path):
    """几何证据：两元素 bbox 均横跨双栏（x0=左栏起点 50.0，x1 远超
    左栏右界 ~280 进入右栏区）——单栏假设在这些元素上失效。"""
    pdf_path = tmp_path / "twocol.pdf"
    _make_two_col_pdf(pdf_path)
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    for e in elements:
        bbox = e.source_locator["bbox"]
        assert bbox[0] == 50.0  # 左栏起点
        assert bbox[2] > 400.0  # 跨入右栏（左栏文本最右 ~180）
        assert bbox[2] - bbox[0] > 300.0  # 宽度超单栏
