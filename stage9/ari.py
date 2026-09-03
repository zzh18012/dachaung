# -*- coding: utf-8 -*-
"""Stage 9 批次 26：ARI（Adjusted Rand Index）零依赖实现。

原子单位 = 标注 text unit（heading 参与、nontext 不参与——由调用方
保证只传入 text units）。两划分：gold_segment_id 聚类 vs 归属 chunk
聚类（投影见 stage9/project.py）。pairwise contingency 组合公式：

ARI = (Σij C(nij,2) − E) / (M − E)，其中
E = Σi C(ai,2)·Σj C(bj,2) / C(n,2)，M = ½[Σi C(ai,2) + Σj C(bj,2)]。

N/A 规则（docs/stage9-annotation-guide.md §9）：
n < 2 → N/A（reason=insufficient_units）；
分母 M − E == 0 → 两划分同为退化单簇，约定 ARI = 1.0。
"""
from math import comb


def _pair(count):
    return comb(count, 2)


def ari_from_contingency(table):
    """table：二维列表 table[i][j] = segment i 与 chunk j 的 unit 数。

    返回 (ari_value, stats_dict)；stats 含 n、index、expected、max。
    """
    rows = [_pair(sum(row)) for row in table]
    cols = [_pair(sum(col)) for col in zip(*table)]
    n = sum(sum(row) for row in table)
    if n < 2:
        return None, {"reason": "insufficient_units", "n": n}
    sum_ij = sum(_pair(cell) for row in table for cell in row)
    total_pairs = _pair(n)
    expected = sum(rows) * sum(cols) / total_pairs
    max_index = 0.5 * (sum(rows) + sum(cols))
    denom = max_index - expected
    if denom == 0:
        return 1.0, {"n": n, "index": sum_ij, "expected": expected,
                     "max": max_index, "degenerate": True}
    return (sum_ij - expected) / denom, {
        "n": n, "index": sum_ij, "expected": expected, "max": max_index}


def ari_units_vs_chunks(unit_segment_ids, unit_chunk_ids):
    """unit 列表的两路标签 → contingency → ARI。

    unit_segment_ids / unit_chunk_ids：等长序列，None 表示缺归属
    （该 unit 不进 ARI，调用方计入 uncovered 披露）。
    """
    seg_index = {}
    chunk_index = {}
    for seg in unit_segment_ids:
        if seg is not None and seg not in seg_index:
            seg_index[seg] = len(seg_index)
    for chk in unit_chunk_ids:
        if chk is not None and chk not in chunk_index:
            chunk_index[chk] = len(chunk_index)
    table = [[0] * len(chunk_index) for _ in seg_index]
    for seg, chk in zip(unit_segment_ids, unit_chunk_ids):
        if seg is None or chk is None:
            continue
        table[seg_index[seg]][chunk_index[chk]] += 1
    return ari_from_contingency(table)
