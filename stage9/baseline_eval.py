# -*- coding: utf-8 -*-
"""Stage 9 批次 26：基线 N 网格评测与 dev 选优（设计 §5 用途矩阵）。

参数搜索仅 dev 集（holdout 只跑最终评测一次）。对每篇标注与每个
(B1 / B2-foldws-v1, N) 组合：切块 → 投影到 text unit → ARI（unit 为
数据点，gold_segment vs chunk 归属两路标签），披露 unmatched chunk /
跨块 unit / uncovered unit（指南 §9：不静默排除）。集级指标 = 非 N/A
文档 macro average；选优规则 = macro ARI 最大者，平局取最小 N（确定
性，登记于报告 selection_rule）。

**B2-foldws-v1（GPT 裁决 2026-09-05 C3 修改后追认）**：设计 §5 原定
B2（保留换行的原始文本输入）未执行/不可复现——标注 JSON 只存 fold-ws
流，评测 harness 无统一原始阅读序文本源（builder 异构、无统一原始文
本接口），用 gold unit 边界合成换行会把标注决策泄漏进基线。冻结显式
变体 B2-foldws-v1：input_view=fold_ws，前两级分隔符（\\n\\n 与 \\n）
恒不命中（newline_level_hits=0，fold-ws 流不含换行的结构性事实），
层级退化为句读级——保守（更难）设定。B1 定义即 fold-ws 流，无偏差。
N* 冻结硬门槛：最终 14 篇 dev 全网格重跑（13 篇 dev 结果非正式）。
"""
from stage9.ari import ari_units_vs_chunks
from stage9.baselines import (
    B1_N_GRID,
    B2_INPUT_VIEW,
    B2_VARIANT,
    b1_fixed_length,
    b2_recursive,
)
from stage9.project import project_chunks_to_units

BASELINES = ("B1", B2_VARIANT)


def evaluate_doc(ann, n_grid=B1_N_GRID, baselines=BASELINES):
    """单篇标注 × (baseline, N) 网格评测。

    返回 {doc_id, chars, text_units, nontext_units, results:
    {baseline: {N: {ari, n_ari_units, unmatched_chunks,
    cross_chunk_units, uncovered_units}}}}。
    """
    stream = ann["stream"]
    text_units = [u for u in ann["units"] if u["char_span"] is not None]
    seg_ids = [u["gold_segment_id"] for u in text_units]
    results = {}
    for bl in baselines:
        per_n = {}
        for n in n_grid:
            if bl == "B1":
                chunks = b1_fixed_length(stream, n)
            elif bl == B2_VARIANT:
                chunks = b2_recursive(stream, n)
            else:
                raise ValueError("unknown baseline: %r" % bl)
            proj = project_chunks_to_units(chunks, stream, text_units)
            labels = [proj.attributions.get(u["unit_id"])
                      for u in text_units]
            ari, _stats = ari_units_vs_chunks(seg_ids, labels)
            per_n[n] = {
                "ari": ari,
                "n_ari_units": sum(1 for x in labels if x is not None),
                "unmatched_chunks": len(proj.unmatched_chunk_indexes),
                "cross_chunk_units": len(proj.cross_chunk_unit_ids),
                "uncovered_units": len(text_units) - len(proj.attributions),
            }
        results[bl] = per_n
    return {
        "doc_id": ann["doc_id"],
        "chars": len(stream),
        "text_units": len(text_units),
        "nontext_units": len(ann["units"]) - len(text_units),
        "results": results,
    }


def macro_average(doc_reports, baseline, n):
    """集级 ARI = 非 N/A 文档 macro average（本工具无 N/A 源，全部
    文档计入了 ARI；无 chunk 覆盖的 doc 由调用方先行剔除并披露）。"""
    vals = [d["results"][baseline][n]["ari"] for d in doc_reports
            if d["results"][baseline][n]["ari"] is not None]
    return sum(vals) / len(vals) if vals else None


def pick_best(macro_by_n):
    """{N: macro_ari} → (best_n, best_ari)。最大者胜，平局取最小 N。"""
    best_n = None
    best_v = None
    for n in sorted(macro_by_n):
        v = macro_by_n[n]
        if v is None:
            continue
        if best_v is None or v > best_v:
            best_n, best_v = n, v
    return best_n, best_v


def select_baselines(doc_reports, n_grid=B1_N_GRID, baselines=BASELINES):
    """网格 → 集级 macro 表 + 选优结果。"""
    macro = {}
    selection = {}
    for bl in baselines:
        macro[bl] = {n: macro_average(doc_reports, bl, n)
                     for n in n_grid}
        best_n, best_v = pick_best(macro[bl])
        selection[bl] = {
            "n": best_n,
            "macro_ari": best_v,
            "tied_with": ([x for x in sorted(macro[bl])
                           if macro[bl][x] == best_v]
                          if best_v is not None else []),
        }
    return macro, selection


BASELINE_CONFIG = {
    "B1": {"input_view": "fold_ws"},
    B2_VARIANT: {
        "input_view": B2_INPUT_VIEW,
        "newline_level_hits": 0,
        "newline_level_hits_note": (
            "fold-ws 流不含换行，前两级分隔符（\\n\\n 与 \\n）结构性"
            "恒不命中；原始 B2（保留换行输入）未执行/不可复现"),
    },
}
