r"""PDF 段落分割阈值的中位数实现锁定（Round 1892，a 优先级）。

`_group_words_to_paragraphs` 段落聚类阈值 = 1.5 × `median_h`，而
`median_h = sorted(heights)[len(heights) // 2]`（app/parsers/
fallback_parser.py:140）——**不是真中位数**：

- 偶数个词取**上取中位**（[10,10,20,20] → 20，非均值 15/下取 10）
- 奇数个词恰取中位（[10,12,40] → 12——离群高词既不抬也不被丢）
- 词高离群但落在上取位**之后**不抬阈（[10,10,10,30] → 10）
- 分割判定是严格 `>`：gap 恰等阈值不分割

三组用例各为判别式设计（在真假中位数假设下结果不同），R1892
探针实证。edges3 已锁"阈值用法"（行距 vs 1.5×median），本轮锁
"median 本身的取法"。
"""

from __future__ import annotations

from app.parsers.fallback_parser import _group_words_to_paragraphs


def _w(text: str, x0: float, top: float, bottom: float) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + 20, "top": top, "bottom": bottom}


def test_pdf_para_split_even_count_takes_upper_median():
    """偶数 [10,10,20,20] → 取 20 → 阈值 30：gap25 并（真中位均值 15
    或下取 10 都会分）、gap31 分（恰排除阈值为 25~30 以外任何值）。"""
    base = [_w("a", 0, 0, 10), _w("b", 50, 0, 10)]
    line2_gap25 = [_w("c", 0, 35, 55), _w("d", 50, 35, 55)]
    line2_gap31 = [_w("c", 0, 41, 61), _w("d", 50, 41, 61)]
    joined = _group_words_to_paragraphs(base + line2_gap25)
    assert [p["text"] for p in joined] == ["a b c d"]  # 25 < 30 并
    split = _group_words_to_paragraphs(base + line2_gap31)
    assert [p["text"] for p in split] == ["a b", "c d"]  # 31 > 30 分


def test_pdf_para_split_odd_count_takes_exact_middle():
    """奇数 [10,12,40] → 取 12 → 阈值 18：gap16 并（排除下取 10 阈
    15）、gap30 分（排除上取/离群 40 阈 60）——只在真中位 12 下两者
    同时成立。"""
    b_far = [_w("c", 0, 160, 200)]  # 第三词 h40，远处分段恒成立
    joined = _group_words_to_paragraphs(
        [_w("a", 0, 0, 10), _w("b", 0, 26, 38)] + b_far
    )
    assert [p["text"] for p in joined] == ["a b", "c"]  # 16 < 18 并
    split = _group_words_to_paragraphs(
        [_w("a", 0, 0, 10), _w("b", 0, 40, 52)] + b_far
    )
    assert [p["text"] for p in split] == ["a", "b", "c"]  # 30 > 18 分


def test_pdf_para_split_outlier_height_does_not_raise_threshold():
    """[10,10,10,30] → 取 idx2=10 → 阈值 15：h30 离群词不抬阈；
    gap 恰 15 并（严格 > 边界——15 > 15 为假）、gap 16 分。"""
    base = [_w("a", 0, 0, 10), _w("b", 50, 0, 10), _w("c", 100, 0, 10)]
    at_threshold = _group_words_to_paragraphs(base + [_w("d", 0, 25, 55)])
    assert [p["text"] for p in at_threshold] == ["a b c d"]  # 15 ≯ 15 并
    over_threshold = _group_words_to_paragraphs(base + [_w("d", 0, 26, 56)])
    assert [p["text"] for p in over_threshold] == ["a b c", "d"]  # 16 > 15 分
