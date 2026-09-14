r"""PDF 混字号下的段落分割中位数锁定（Round 1894，a 优先级）。

R1892 锁了同字号 heights 的中位取法；本轮补**混字号**交互
（R1893 已证混合字号可融合，此处锁它如何反过来改写分割阈值）：
`median_h = sorted(heights)[len//2]`（:140）对所有 word 高度统一
取上取位——大字号词只要占到 idx 位置就把阈值抬到 1.5×24=36，
落在 idx 之后则完全不抬（1.5×8=12）。探针 R1894 三组判别式实证。
"""

from __future__ import annotations

from pathlib import Path

from app.parsers.fallback_parser import _group_words_to_paragraphs, _parse_pdf
from tests.test_backlog_pdf_crosspage_table import _build_pdf


def _w(text: str, x0: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + 20, "top": top, "bottom": bottom}


def test_mixed_sizes_at_index_raise_threshold():
    """[8,8,24,24] → 上取 idx2=24 → 阈 36：gap30 并（同号 8pt 阈 12
    必分）、gap37 分——大字号词占到上取位即抬阈 3 倍。"""
    base = [_w("a", 0, 0, 8), _w("b", 50, 0, 8)]
    for gap, expected in [(30, ["a b c d"]), (37, ["a b", "c d"])]:
        top2 = 8 + gap
        words = base + [
            _w("c", 0, top2, top2 + 24), _w("d", 50, top2, top2 + 24)
        ]
        paras = _group_words_to_paragraphs(words)
        assert [p["text"] for p in paras] == expected, f"gap={gap}"


def test_mixed_sizes_beyond_index_do_not_raise():
    """[8,8,8,24] → idx2=8 → 阈 12：单个 24pt 词落在上取位之后不抬
    阈——gap11 并、gap15 分（若被抬到 36 则 gap15 会并）。"""
    base = [_w("a", 0, 0, 8), _w("b", 50, 0, 8), _w("c", 100, 0, 8)]
    for gap, expected in [(11, ["a b c d"]), (15, ["a b c", "d"])]:
        top2 = 8 + gap
        words = base + [_w("d", 0, top2, top2 + 24)]
        paras = _group_words_to_paragraphs(words)
        assert [p["text"] for p in paras] == expected, f"gap={gap}"


def test_mixed_size_threshold_end_to_end_real_pdf(tmp_path):
    """e2e：真实 PDF 8pt 行 + 24pt 行——gap30（< 阈 36）融合成一个
    元素（bbox 跨两行），gap60 分成两个元素。"""
    for gap, n_expected in [(30, 1), (60, 2)]:
        parts = []
        for x, y, size, text in [
            (50, 740, 8, "small line"),
            (50, 740 - 8 - gap, 24, "big line"),
        ]:
            parts.append(f"BT /F1 {size:g} Tf {x:.1f} {y:.1f} Td ({text}) Tj ET")
        pdf_path = tmp_path / f"mix{gap}.pdf"
        pdf_path.write_bytes(_build_pdf(["\n".join(parts).encode("latin-1")]))
        elements, warnings = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
        assert warnings == []
        assert len(elements) == n_expected, f"gap={gap}"
    # gap30 的融合元素文本序：pdfplumber yc 序 small 在前
    pdf_path = tmp_path / "mix30.pdf"
    elements, _ = _parse_pdf(pdf_path, "sha" * 21, "doc-x", None)
    assert elements[0].content == "small line big line"
    bbox = elements[0].source_locator["bbox"]
    assert round(bbox[3] - bbox[1], 1) == 49.3  # 跨 8pt+gap30+24pt 行
