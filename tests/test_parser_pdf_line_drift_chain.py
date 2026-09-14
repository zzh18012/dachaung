r"""PDF word 行聚类锚点漂移链锁定（Round 1891，a 优先级）。

`_group_words_to_paragraphs` 行聚类（app/parsers/fallback_parser.py
:127-131）的锚点是**滑动均值**：每并入一词，`current_y` 更新为
`(current_y + yc) / 2`——不是固定首词锚。后果（grep 实证此前无
覆盖，R1891 探针发现）：

- **漂移链**：每步与当前均值锚差 ≤ 3.0 即并入，链上词总 y 跨度
  可远超 3.0（探针 4 词总跨 5.2 仍同行）——斜排/上下标/基线漂
  移文字会被并成一行（候选 B 同族的几何机制）
- **断链**：某步与漂移锚差 > 3.0 → 新行（新行锚重置为该词）
- 行内按 x0 排序、行间按行序拼接——x 序只在行内生效
"""

from __future__ import annotations

from app.parsers.fallback_parser import _group_words_to_paragraphs


def _w(text: str, x0: float, x1: float, top: float) -> dict:
    return {"text": text, "x0": x0, "x1": x1, "top": top, "bottom": top + 12.0}


def test_pdf_group_drift_chain_merges_beyond_tolerance():
    """漂移链：4 词每步距滑动均值锚 ≤3.0（2.9/2.95/2.275），总 y
    跨度 5.2 > 3.0 仍并成**一行**——x 递减布局下文本按 x 序输出
    'D C B A'（若按固定锚分行则会是行序 'A B C D'）。"""
    words = [
        _w("A", 90, 95, 100.0),   # yc 106（行锚起点）
        _w("B", 80, 85, 102.9),   # yc 108.9，Δ2.9 → 并入，锚 107.45
        _w("C", 70, 75, 104.4),   # yc 110.4，Δ2.95 → 并入，锚 108.925
        _w("D", 60, 65, 105.2),   # yc 111.2，Δ2.275 → 并入
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1
    assert paras[0]["text"] == "D C B A"
    # 单段 bbox 覆盖全链（top 100 → bottom 117.2）
    assert paras[0]["bbox"] == [60.0, 100.0, 95.0, 117.2]


def test_pdf_group_drift_chain_breaks_when_step_exceeds_running_anchor():
    """断链：C 距漂移锚 6.55 > 3.0 → 起新行；D 与 B 行锚距 3.55
    也起新行、C 距 D 行锚恰 3.0（含等号）并入——行划分 [A,B]+[D,C]，
    文本 'B A D C'（每行内 x 序：B<A、D<C）。"""
    words = [
        _w("A", 90, 95, 100.0),   # 行1 锚 106
        _w("B", 80, 85, 102.9),   # Δ2.9 并入，锚 107.45
        _w("C", 70, 75, 108.0),   # yc 114，Δ6.55 → 行2（与 D）
        _w("D", 60, 65, 105.0),   # yc 111，距锚 3.55 → 行2 起，锚 111
    ]
    # C 距 D 行锚 |114-111| = 3.0 ≤ 3.0（含等号）→ 并入行2，锚 112.5
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1
    assert paras[0]["text"] == "B A D C"
    assert paras[0]["bbox"] == [60.0, 100.0, 95.0, 120.0]


def test_pdf_group_line_order_overrides_x_across_lines():
    """跨行时行序压过 x 序：两词 y 差 5.2 > 3.0 分属两行，x=40 的
    B 在 x=50 的 A 之后输出（行内 x 序只在行内生效）。"""
    words = [
        _w("A", 50, 55, 100.0),
        _w("B", 40, 45, 105.2),
    ]
    paras = _group_words_to_paragraphs(words)
    assert len(paras) == 1
    assert paras[0]["text"] == "A B"
