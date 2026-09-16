# -*- coding: utf-8 -*-
"""Stage 9 批次 26：粒度诊断与合规上界（外部评审 R-B，G⑥ 后 dev only）。

评审 R-B 指认：gold 段长（均值 ~10⁴ 字符级）远超 max_chars（≤2000），
长度约束迫使任何合规 chunker 把单段切成多块 → ARI 结构性受损
（示意：拆 2 ≈0.646、拆 5 ≈0.306）。本模块把该论证机械化：

- segment_spans：按 gold_segment 聚合 text unit 的流区间（段长 =
  末 unit 起点-首 unit 终点， validator 已保证覆盖连续）；
- oracle_pieces：** oracle 合规切块**——段内均分 ceil(段长/N) 片、
  片恒不跨段边界（任何 max_chars≤N 的真实 chunker 不会更好：跨段
  切只会再降 ARI，段内切法以对齐为上界）；
- granularity_bound：oracle 块经 ari_units_vs_chunks 得 **ari_bound**
  = 该 N 下合规切块的 ARI 上界（结构天花板）；随附段长分布
  （median/mean/max、超 N 段数与占比）。

纪律（预注册 stage9/granularity_preregistration.json）：真实 run
仅 G⑥ 后 dev 集 14 篇；**永不修改 ARI 分母**（ARI<0.75 公开差距
与原因，不调口径救指标）；本模块纯函数，CLI 接线走 G⑦ 报告。
"""
import statistics

from stage9.ari import ari_units_vs_chunks


def segment_spans(ann):
    """标注 → 段流区间列表（stream 顺序）。

    返回 [{"gold_segment_id", "start", "end", "chars", "text_units"}]；
    text unit 按 char_span 排序聚合到所属段；段内不连续（区间并集
    < 端点差）时以端点差计长（保守，披露 nontext 空隙不影响段长
    主张——stream 连续性由 validator span 覆盖规则保证）。
    """
    units = [u for u in ann.get("units", [])
             if isinstance(u, dict) and u.get("char_span")]
    by_seg = {}
    for u in units:
        start, end = u["char_span"]
        by_seg.setdefault(u["gold_segment_id"], []).append((start, end))
    out = []
    for gid, spans in by_seg.items():
        spans.sort()
        out.append({"gold_segment_id": gid, "start": spans[0][0],
                    "end": spans[-1][1],
                    "chars": spans[-1][1] - spans[0][0],
                    "text_units": len(spans)})
    out.sort(key=lambda d: d["start"])
    return out


def oracle_pieces(seg_span, n):
    """单段均分切块：ceil(段长/n) 片，片长 ≤ n，恒不跨段。"""
    length = seg_span["end"] - seg_span["start"]
    if length <= 0:
        return []
    pieces = -(-length // n)  # ceil
    bounds = [seg_span["start"] + length * k // pieces
              for k in range(pieces + 1)]
    return [(bounds[k], bounds[k + 1]) for k in range(pieces)
            if bounds[k + 1] > bounds[k]]


def granularity_bound(ann, n_grid):
    """单篇粒度诊断（纯函数）：逐 N 的 oracle 上界 + 段长分布。

    返回 {doc_id, segments: n, segment_chars: {...分布...},
    bounds: {N: {oracle_chunks, split_segments, ari_bound,
    n_ari_units}}}。unit 归片 = 包含 unit 起点的片；ARI 用与
    evaluate_doc 同一 ari_units_vs_chunks（分母不变）。
    """
    stream = ann["stream"]
    text_units = sorted(
        (u for u in ann.get("units", [])
         if isinstance(u, dict) and u.get("char_span")),
        key=lambda u: u["char_span"][0])
    seg_ids = [u["gold_segment_id"] for u in text_units]
    segs = segment_spans(ann)
    lengths = [s["chars"] for s in segs]
    bounds = {}
    for n in n_grid:
        pieces_by_seg = {}
        offset = 0
        for seg in segs:
            pieces = oracle_pieces(seg, n)
            pieces_by_seg[seg["gold_segment_id"]] = [
                (offset + i, a, b) for i, (a, b) in enumerate(pieces)]
            offset += len(pieces)  # 片号全局唯一，防跨段并簇
        oracle_count = offset
        split = sum(1 for p in pieces_by_seg.values() if len(p) >= 2)
        labels = []
        for u in text_units:
            pieces = pieces_by_seg.get(u["gold_segment_id"], [])
            start = u["char_span"][0]
            idx = next((pid for pid, a, b in pieces
                        if a <= start < b), None)
            labels.append(idx if idx is not None else None)
        ari, _stats = ari_units_vs_chunks(seg_ids, labels)
        bounds[n] = {
            "oracle_chunks": oracle_count,
            "split_segments": split,
            "ari_bound": ari,
            "n_ari_units": sum(1 for x in labels
                               if x is not None),
        }
    return {
        "doc_id": ann.get("doc_id"),
        "chars": len(stream),
        "segments": len(segs),
        "segment_chars": {
            "median": statistics.median(lengths) if lengths else None,
            "mean": (sum(lengths) / len(lengths)) if lengths else None,
            "max": max(lengths) if lengths else None,
            "over_grid_max": {
                str(n): sum(1 for x in lengths if x > n)
                for n in n_grid},
        },
        "bounds": bounds,
    }


def granularity_macro(doc_reports, n_grid):
    """集级：ari_bound 的非 None macro（与基线/系统 macro 同规）。"""
    out = {}
    for n in n_grid:
        vals = [d["bounds"][n]["ari_bound"] for d in doc_reports
                if d["bounds"][n]["ari_bound"] is not None]
        out[n] = sum(vals) / len(vals) if vals else None
    return out
