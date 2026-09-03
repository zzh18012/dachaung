# -*- coding: utf-8 -*-
"""Stage 9 批次 26：预测块 → 标注 unit 的投影规则（ARI 评测共用）。

设计依据 docs/stage9-batch26-design.md §3：
- 预测 chunk 的 text 经同一规范化（fold-ws-v1）后，在文档规范化字符流
  上定位为 span（顺序游标 + 全局回退的精确子串匹配；匹配失败计
  unmatched，不静默）；
- 与某 text unit 的 char_span 相交即候选归属；一个 unit 跨多个 chunk 时
  按最大重叠归属唯一 chunk（平局取先出现的 chunk），跨块 unit 单列披露；
- nontext unit 不进投影（不参与 ARI，关联指标另行计算）。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectionResult:
    # unit_id -> 归属 chunk 下标
    attributions: dict
    # 与 >1 个 chunk 有正重叠、被拆到多个块的 unit
    cross_chunk_unit_ids: tuple
    # 在字符流上定位失败的 chunk 下标
    unmatched_chunk_indexes: tuple
    # 每 chunk 的 [start, end)；定位失败为 None
    chunk_spans: tuple

    def to_json(self):
        return {
            "attributions": {k: v for k, v in sorted(
                self.attributions.items())},
            "cross_chunk_unit_ids": list(self.cross_chunk_unit_ids),
            "unmatched_chunk_indexes": list(self.unmatched_chunk_indexes),
            "chunk_spans": [list(sp) if sp else None
                            for sp in self.chunk_spans],
        }


def locate_chunks(chunks, stream):
    """按顺序在 stream 上定位各 chunk 文本，返回与 chunks 等长的 span 列表。

    游标单调前进（结构性切块的拼接应等于字符流）；游标处找不到时全局
    回退找一次；都失败记 None（unmatched，调用方披露）。
    """
    spans = []
    cursor = 0
    for text in chunks:
        if not text:
            spans.append(None)
            continue
        pos = stream.find(text, cursor)
        if pos < 0:
            pos = stream.find(text)
        if pos < 0:
            spans.append(None)
            continue
        spans.append((pos, pos + len(text)))
        cursor = pos + len(text)
    return spans


def project_chunks_to_units(chunks, stream, text_units):
    """把 chunk 列表投影到 text unit 集合（nontext unit 由调用方排除）。

    chunks：已 fold_ws 的 chunk 文本列表（顺序即文档顺序）。
    text_units：[{unit_id, char_span: [a, b]}, ...]。
    """
    spans = locate_chunks(chunks, stream)
    unmatched = tuple(i for i, sp in enumerate(spans) if sp is None)
    attributions = {}
    cross = []
    for unit in text_units:
        a, b = unit["char_span"]
        best = None
        best_ov = 0
        overlapping = 0
        for i, sp in enumerate(spans):
            if sp is None:
                continue
            ov = min(b, sp[1]) - max(a, sp[0])
            if ov > 0:
                overlapping += 1
            if ov > best_ov:
                best_ov = ov
                best = i
        if best is None:
            continue
        attributions[unit["unit_id"]] = best
        if overlapping > 1:
            cross.append(unit["unit_id"])
    return ProjectionResult(
        attributions=attributions,
        cross_chunk_unit_ids=tuple(cross),
        unmatched_chunk_indexes=unmatched,
        chunk_spans=tuple(spans),
    )
