r"""PDF 段落分割阈值精确等值 + 词级中位数锁定（Round 1903，a 优先级）。

grep 零覆盖（既有测试行距全部远离边界：test_parsers_fallback.py :219
行距 2 / :231 行距 88、R1894 gap 30/37 vs 阈 36 与 11/15 vs 阈 12
——均未命中 gap == 1.5×median 的精确等值；`>` 改 `>=` 所有现存
测试仍绿）。探针 R1903 实证（`_group_words_to_paragraphs` :149
`(line_top - last_bottom) > 1.5 * median_h` 严格大于；:139-140
median 按**每个 word** 的高度收集 `sorted(heights)[len//2]`）：

- **等值合并**：h=10 词 median=10 阈 15；下行 top 25 − 上行
  bottom 10 = 15.0 恰等 → **不拆**（严格 >）——1 段
  'w1 w2'；15.1 恰超 → 拆 2 段（边界恰在 15）
- **词级 median 可观察**：同线双词 h=20,20 + 两单词条 h=8,8 →
  词级 heights [20,20,8,8] median=20 阈 30：gap 30 恰等 join、
  gap 32 拆 → ['aa bb cc', 'dd']；若 median 按行高度（8）阈 12
  → 30 > 12 → 3 段——输出可区分词级语义
"""

from __future__ import annotations

from app.parsers.fallback_parser import _group_words_to_paragraphs


def _w(text: str, x0: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + 8 * len(text), "top": top, "bottom": bottom}


def test_pdf_para_split_exact_threshold_joins():
    """判别式：gap == 1.5×median 恰等（15.0 == 15.0）→ 不拆——
    严格大于；把 `>` 改 `>=` 此测试翻红。"""
    paras = _group_words_to_paragraphs([
        _w("w1", 0, 0, 10),
        _w("w2", 0, 25, 35),
    ])
    assert len(paras) == 1
    assert paras[0]["text"] == "w1 w2"


def test_pdf_para_split_just_above_threshold_splits():
    """对照：同几何 + 0.1 → gap 15.1 恰超阈 → 拆 2 段——证明边界
    恰在 15.0 而非更下方。"""
    paras = _group_words_to_paragraphs([
        _w("w1", 0, 0, 10),
        _w("w2", 0, 25.1, 35.1),
    ])
    assert [p["text"] for p in paras] == ["w1", "w2"]


def test_pdf_para_median_is_word_level():
    """判别式：median 收集**每个 word** 高度——同线双词 h=20,20 +
    两单词条 h=8,8 → [8,8,20,20] 上中位 20 阈 30：gap 30 恰等
    join（'aa bb cc' 一段）、gap 32 拆（'dd'）→ 恰 2 段；行级
    median（8，阈 12）会给 3 段。"""
    paras = _group_words_to_paragraphs([
        _w("aa", 0, 0, 20),
        _w("bb", 100, 0, 20),
        _w("cc", 0, 50, 58),
        _w("dd", 0, 90, 98),
    ])
    assert [p["text"] for p in paras] == ["aa bb cc", "dd"]
