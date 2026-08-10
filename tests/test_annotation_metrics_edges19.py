r"""evaluation/annotation_metrics.py 边角测试 - 第十九轮（Round 280）。

edges18 已覆盖：模块 imports / 常量 / figure_caption_prf source-level / chunk_boundary_prf source-level
详尽 / __all__ / namespace / 行为基本路径 / helper metadata / 签名 / docstring。

edges19 补强未覆盖的角度（chunk_boundary_prf 多分支组合 + 一对一匹配细节）：
- **chunk_boundary_prf position="before"**：marker 起始位置作为 gt 位置
- **chunk_boundary_prf position="after"**（默认）：marker 结束位置作为 gt 位置
- **chunk_boundary_prf 完美匹配（多 anchor）**：2 chunks + 2 anchors，距离<容差 → P/R/F1=1.0
- **chunk_boundary_prf 部分匹配**：anchors 多于预测 → recall<1.0
- **chunk_boundary_prf 预测多于 anchor**：precision<1.0
- **chunk_boundary_prf tolerance_chars=0**：必须精确匹配
- **chunk_boundary_prf tolerance_chars 较大**：宽松匹配
- **chunk_boundary_prf missing_markers**：marker 不在 stream 中 → _missing_markers 含该 marker
- **chunk_boundary_prf 空 marker**：marker='' → find 返 -1 → 加入 missing_markers
- **chunk_boundary_prf 重复 marker**：相同 marker 出现多次，search_from 顺序推进
- **chunk_boundary_prf 容差刚好相等**：d == tolerance_chars 算匹配（<= 比较）
- **chunk_boundary_prf 容差刚好超过**：d == tolerance_chars + 1 不算
- **chunk_boundary_prf f1=0 when p=r=0**：denom<=0 分支 → _ratio(0.0)
- **chunk_boundary_prf 多 chunk 多 anchor 一对一**：贪心按距离排序
- **chunk_boundary_prf predicted 边界位置**：第 i 个 chunk 末尾
- **chunk_boundary_prf 多 anchor 共享 stream 位置不被允许**：search_from 推进
- **chunk_boundary_prf norm_chunks 与 stream 关系**：stream 是 normalize_text(' '.join(norm_chunks))
- **chunk_boundary_prf 最后 chunk 不算边界**
- **chunk_boundary_prf _tolerance_chars 始终在输出**：即使 document/annotation 失败
- **figure_caption_prf 各种输入**：document 是 dict / annotation 是 dict / 都 None / 都空
- **figure_caption_prf 不读 document/annotation 字段**：纯固定输出
- **module source 不含 json/print/logging/subprocess**
- **chunk_boundary_prf source 含 specific 关键 token**：'search_from = 0' / 'pairs.sort' / 'used_pred' / 'used_gt'
- **chunk_boundary_prf 匹配算法**：贪心 + 一对一（用具体 case 验证）
- **chunk_boundary_prf 多 anchor 同 marker**：search_from 防止都命中第 1 次
- **chunk_boundary_prf chunk 文本含 marker**：marker 在 chunk 文本内部
- **chunk_boundary_prf chunk text 找不到（理论不该发生）**：pos += len(txt) + 1 兜底
- **module __all__ 3 entries 顺序精确**
- **PARSER_DOES_NOT_EMIT_RELATIONS 是常量**
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# chunk_boundary_prf: position="before" vs "after"
# =========================================================================


def _make_doc(chunks_text: list[str]) -> dict[str, Any]:
    """构造 document dict，含 chunks（每个 chunk 含 text 字段）。"""
    return {
        "chunks": [
            {"chunk_id": f"c{i}", "text": t, "source_element_ids": [f"e{i}"]}
            for i, t in enumerate(chunks_text)
        ]
    }


def test_chunk_boundary_prf_position_before():
    """position='before' → marker 起始位置作为 gt 位置。"""
    # chunks 文本拼接 normalize 后："alpha beta gamma"
    doc = _make_doc(["alpha", "beta", "gamma"])
    # marker='beta'，position='before' → gt 位置 = stream.find('beta') = 6
    # 预测边界：第 0 个 chunk 末尾（'alpha' 末尾 = 5）+ 第 1 个 chunk 末尾（'beta' 末尾 = 10）
    # gt 位置 = 6；pred[0]=5；|5-6|=1 <= 30 → match
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 个 anchor 匹配 → recall = 1/1 = 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_after_default():
    """position='after'（默认）→ marker 结束位置作为 gt 位置。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    # marker='beta'，position='after' → gt 位置 = stream.find('beta') + len('beta') = 6 + 4 = 10
    # 预测边界：5, 10
    # gt 位置 = 10；pred[1]=10；|10-10|=0 <= 30 → match
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_defaults_to_after():
    """position 非 'before' 也非 'after' → 默认走 else 分支（after 语义）。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "weird"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 走 else 分支 → gt 位置 = find + len(marker) = 10
    # 与 pred[1]=10 距离 0 → match
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf: 完美匹配 / 部分匹配
# =========================================================================


def test_chunk_boundary_prf_perfect_match_two_anchors():
    """2 chunks + 2 anchors，都精确匹配 → P/R/F1=1.0。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    # 2 个内部边界：alpha 末尾(5) 和 beta 末尾(10)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # gt=5
            {"marker": "beta", "position": "after"},   # gt=10
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_partial_match_recall_lt_1():
    """anchors 多于预测 → recall<1.0。"""
    doc = _make_doc(["alpha", "beta"])  # 1 个内部边界
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},  # 这个找不到对应预测
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 个预测，2 个 anchor，最多匹配 1 → recall=1/2=0.5；precision=1/1=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    # f1 = 2*1*0.5 / (1+0.5) = 0.666...
    assert abs(out["chunk_boundary_f1"]["value"] - (2 * 1.0 * 0.5 / 1.5)) < 1e-9


def test_chunk_boundary_prf_predicted_more_than_anchors_precision_lt_1():
    """预测多于 anchor → precision<1.0。"""
    doc = _make_doc(["alpha", "beta", "gamma", "delta"])  # 3 个内部边界
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # 只标了 1 个
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 3 个预测，1 个 anchor，最多匹配 1 → precision=1/3；recall=1/1=1.0
    assert abs(out["chunk_boundary_precision"]["value"] - 1/3) < 1e-9
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_at_all():
    """预测和 anchor 都不在容差内 → P/R=0/0 但分母非 0。"""
    doc = _make_doc(["alpha", "beta", "gamma"])  # 边界在 5, 10
    # marker 故意取不在 stream 内的 → missing_markers；剩 0 anchor
    # 但 0 anchor 走 no_ground_truth_anchors 分支（在 chunks>=2 + anchors 非空但没匹配的场景）
    # 这里 anchor list 是 [{'marker': 'unfound'}] → 找不到 → gt_positions 为空
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "zzznotfound", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 0 gt_positions → recall null + no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


# =========================================================================
# chunk_boundary_prf: tolerance_chars 边界值
# =========================================================================


def test_chunk_boundary_prf_tolerance_zero_exact_match():
    """tolerance_chars=0 → 必须精确匹配。"""
    doc = _make_doc(["alpha", "beta"])
    # 边界在 alpha 末尾=5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # gt=5
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # pred=5, gt=5, d=0 <= 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_no_match_when_off_by_one():
    """tolerance_chars=0 + 距离 1 → 不匹配。"""
    doc = _make_doc(["alpha", "beta"])
    # pred=5, gt=6（marker='alphab' 的 after 位置不存在；用 marker='alph' + after=4）
    # 实际上让我们用 marker='alph' position='after' → gt=4
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},  # gt=4
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # pred=5, gt=4, d=1 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_equal_boundary_match():
    """d == tolerance_chars 算匹配（<= 比较）。"""
    doc = _make_doc(["alpha", "beta"])
    # pred=5; 用 marker='alph' after → gt=4; d=1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},  # gt=4
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # d=1 <= 1 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_just_over_no_match():
    """d == tolerance_chars + 1 不算匹配。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},  # gt=4, d=1
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # d=1 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_large_lenient_match():
    """tolerance_chars=100 → 宽松匹配。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},  # gt=4, d=1
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf: missing_markers
# =========================================================================


def test_chunk_boundary_prf_missing_markers_populated():
    """marker 不在 stream → 加入 missing_markers 列表。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "zzznotfound", "position": "after"},
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out
    assert "zzznotfound" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_markers_no_field_when_all_found():
    """所有 marker 都找到 → 不出现 _missing_markers 字段。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_empty_marker_treated_as_missing():
    """marker='' → find 返 -1 → 加入 missing_markers。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 空 marker → find 返 -1（因 marker falsy）
    # 但 anchors 非空，所以走 chunks>=2 + anchors 分支
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_markers_value_is_list():
    """_missing_markers.value 是 list。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert isinstance(out["_missing_markers"]["value"], list)


# =========================================================================
# chunk_boundary_prf: 重复 marker 与 search_from
# =========================================================================


def test_chunk_boundary_prf_duplicate_markers_sequential_advance():
    """相同 marker 出现多次，search_from 推进避免都命中第 1 次。"""
    # stream: "alpha alpha alpha"（normalize 后）
    doc = _make_doc(["alpha", "alpha", "alpha"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "before"},  # gt=0
            {"marker": "alpha", "position": "before"},  # gt=6（第 2 次）
            {"marker": "alpha", "position": "before"},  # gt=12（第 3 次）
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 预测边界：第 0 个 chunk 末尾=5，第 1 个 chunk 末尾=11
    # gt 位置：0, 6, 12（在 stream "alpha alpha alpha" 中）
    # 一对一匹配（贪心）：
    # pred=5: |5-0|=5, |5-6|=1, |5-12|=7
    # pred=11: |11-0|=11, |11-6|=5, |11-12|=1
    # 排序后 (1, 0, 1), (1, 1, 2), (5, 0, 0), (5, 1, 1), (7, 0, 2), (11, 1, 0)
    # 贪心：先匹配 (1, 0, 1) → pred[0]↔gt[1]；然后 (1, 1, 2) → pred[1]↔gt[2]
    # 然后 (5, 0, 0) → pred[0] 已用；继续；最终 matched=2
    # precision = 2/2 = 1.0；recall = 2/3
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert abs(out["chunk_boundary_recall"]["value"] - 2/3) < 1e-9


# =========================================================================
# chunk_boundary_prf: f1 边界情况
# =========================================================================


def test_chunk_boundary_prf_f1_zero_when_p_and_r_zero():
    """p=0, r=0 → denom<=0 → f1=_ratio(0.0)。"""
    doc = _make_doc(["alpha", "beta"])
    # 距离都很大，无任何匹配 → matched=0
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "before"},  # gt=0
        ]
    }
    # tolerance=0 → pred=5, gt=0, d=5 > 0 → 不匹配
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # f1 = 0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_null_when_recall_null():
    """recall null（gt_positions 为空）→ f1 null + precision_or_recall_not_evaluated。"""
    # 让 stream 为空 → marker 找不到 → gt_positions=[]
    # 但 predicted 非空（find of "" 返 0）
    doc = {"chunks": [{"text": ""}, {"text": ""}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # predicted=[0]（find of "" 返 0）→ num_pred=1, matched=0
    # precision = _ratio(0.0)
    # gt_positions=[] → recall null + no_ground_truth_anchors_in_stream
    # f1: r_val=None → null + precision_or_recall_not_evaluated
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


# =========================================================================
# chunk_boundary_prf: _tolerance_chars 始终在输出
# =========================================================================


def test_chunk_boundary_prf_tolerance_chars_always_present_document_none():
    """document=None → _tolerance_chars 仍在输出。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_always_present_annotation_falsy():
    """annotation={} → _tolerance_chars 仍在输出。"""
    doc = _make_doc(["a", "b"])
    out = chunk_boundary_prf(doc, {}, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_always_present_no_predicted():
    """chunks<2 → _tolerance_chars 仍在输出。"""
    doc = _make_doc(["a"])
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_always_present_no_anchors():
    """有预测但无 anchors → _tolerance_chars 仍在输出。"""
    doc = _make_doc(["a", "b"])
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_always_present_normal():
    """正常路径 → _tolerance_chars 仍在输出。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_reason_always_none():
    """_tolerance_chars.reason 始终 None（不管路径）。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    for tc in [0, 1, 30, 100, 1000]:
        out = chunk_boundary_prf(doc, annotation, tolerance_chars=tc)
        assert out["_tolerance_chars"]["reason"] is None


# =========================================================================
# chunk_boundary_prf: source-level 关键 token
# =========================================================================


def test_chunk_boundary_prf_source_contains_search_from_init_zero():
    """source 含 'search_from = 0'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_prf_source_contains_pairs_sort():
    """source 含 'pairs.sort'（贪心排序）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort" in src


def test_chunk_boundary_prf_source_contains_used_pred_set():
    """source 含 'used_pred' set。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src


def test_chunk_boundary_prf_source_contains_used_gt_set():
    """source 含 'used_gt' set。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_gt" in src


def test_chunk_boundary_prf_source_contains_pairs_tuple_init():
    """source 含 pairs: list[tuple[int, int, int]] = []。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "list[tuple[int, int, int]]" in src


def test_chunk_boundary_prf_source_contains_distance_calculation():
    """source 含 abs(pv - gv) 距离计算。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "abs(pv - gv)" in src


def test_chunk_boundary_prf_source_contains_pairs_append():
    """source 含 pairs.append((d, pi, gi))。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.append" in src
    assert "(d, pi, gi)" in src


def test_chunk_boundary_prf_source_contains_used_pred_add():
    """source 含 used_pred.add(pi)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred.add(pi)" in src


def test_chunk_boundary_prf_source_contains_used_gt_add():
    """source 含 used_gt.add(gi)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_gt.add(gi)" in src


def test_chunk_boundary_prf_source_contains_search_from_advance():
    """source 含 search_from = find_pos + len(marker)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = find_pos + len(marker)" in src


def test_chunk_boundary_prf_source_contains_for_pi_pv_in_enumerate_predicted():
    """source 含 for pi, pv in enumerate(predicted)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "for pi, pv in enumerate(predicted)" in src


def test_chunk_boundary_prf_source_contains_for_gi_gv_in_enumerate_gt_positions():
    """source 含 for gi, gv in enumerate(gt_positions)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "for gi, gv in enumerate(gt_positions)" in src


def test_chunk_boundary_prf_source_contains_d_less_equal_tolerance():
    """source 含 d <= tolerance_chars（<= 不是 <）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "d <= tolerance_chars" in src


def test_chunk_boundary_prf_source_contains_p_val_r_val_checks():
    """source 含 p_val / r_val None 检查。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "p_val = out" in src
    assert "r_val = out" in src
    assert "p_val is None or r_val is None" in src


def test_chunk_boundary_prf_source_contains_denom_le_zero_check():
    """source 含 denom <= 0 检查（f1=0 分支）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom <= 0" in src


def test_chunk_boundary_prf_source_contains_2_p_r_formula():
    """source 含 2 * p_val * r_val / denom 公式。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_chunk_boundary_prf_source_contains_position_before_check():
    """source 含 position == 'before' 检查。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'position == "before"' in src


def test_chunk_boundary_prf_source_contains_find_pos_lt_zero_check():
    """source 含 find_pos < 0 检查（找不到 marker）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "find_pos < 0" in src


def test_chunk_boundary_prf_source_contains_stream_find_marker():
    """source 含 stream.find(marker, search_from)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(marker, search_from)" in src


def test_chunk_boundary_prf_source_contains_last_chunk_break():
    """source 含 i == len(norm_chunks) - 1 时 break（最后 chunk 不算边界）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "i == len(norm_chunks) - 1" in src
    assert "break" in src


def test_chunk_boundary_prf_source_contains_pos_advance_when_not_found():
    """source 含找不到 txt 时 pos += len(txt) + 1 兜底。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos += len(txt) + 1" in src


def test_chunk_boundary_prf_source_contains_stream_find_txt():
    """source 含 stream.find(txt, pos)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(txt, pos)" in src


def test_chunk_boundary_prf_source_contains_pos_end_plus_1():
    """source 含 pos = end + 1（跨过空格）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos = end + 1" in src


def test_chunk_boundary_prf_source_contains_norm_chunks_text_or_empty():
    """source 含 c.get("text") or "" 防 None。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'c.get("text") or ""' in src


def test_chunk_boundary_prf_source_contains_a_get_marker_default_empty():
    """source 含 a.get("marker", "") 默认空字符串。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("marker", "")' in src


def test_chunk_boundary_prf_source_contains_a_get_position_default_after():
    """source 含 a.get("position", "after") 默认 after。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


def test_chunk_boundary_prf_source_contains_missing_markers_append():
    """source 含 missing_markers.append(marker)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers.append(marker)" in src


def test_chunk_boundary_prf_source_contains_position_before_gt_append():
    """source 含 'gt_positions.append(find_pos)'（before 分支）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions.append(find_pos)" in src


def test_chunk_boundary_prf_source_contains_position_after_gt_append():
    """source 含 'gt_positions.append(find_pos + len(marker))'（after 分支）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions.append(find_pos + len(marker))" in src


def test_chunk_boundary_prf_source_contains_predicted_append_end():
    """source 含 predicted.append(end)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted.append(end)" in src


def test_chunk_boundary_prf_source_contains_end_calculation():
    """source 含 end = find_pos + len(txt)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "end = find_pos + len(txt)" in src


# =========================================================================
# chunk_boundary_prf: 不修改输入
# =========================================================================


def test_chunk_boundary_prf_does_not_modify_document_chunks():
    """chunk_boundary_prf 不修改 document['chunks'] 内容。"""
    doc = _make_doc(["alpha", "beta"])
    doc_before = doc["chunks"][0]["text"]
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert doc["chunks"][0]["text"] == doc_before


def test_chunk_boundary_prf_does_not_modify_annotation_anchors():
    """chunk_boundary_prf 不修改 annotation['chunk_boundary_anchors'] 内容。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    anchor_before = dict(annotation["chunk_boundary_anchors"][0])
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert annotation["chunk_boundary_anchors"][0] == anchor_before


# =========================================================================
# chunk_boundary_prf: 一对一匹配（贪心按距离）
# =========================================================================


def test_chunk_boundary_prf_one_to_one_greedy_match_closest():
    """贪心匹配：距离最近的优先。"""
    # 构造场景：1 个预测位置在两个 anchor 之间，但更靠近其中一个
    # stream = "alpha beta gamma"
    doc = _make_doc(["alpha", "beta", "gamma"])
    # 预测：5（alpha 后），10（beta 后）
    annotation = {
        "chunk_boundary_anchors": [
            # gt=4（alph 后），与 pred=5 距离 1
            {"marker": "alph", "position": "after"},
            # gt=10（beta 后），与 pred=10 距离 0
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 2 预测 2 anchor，距离都 < 30 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_to_one_prevents_double_match():
    """一个预测不能同时匹配两个 anchor（一对一）。"""
    # 构造：2 个 anchor 距离同一预测都很近，但只能匹配 1
    doc = _make_doc(["ab", "cd"])  # stream="ab cd"
    # 预测：2（ab 末尾）
    # anchor1: marker='a' after → gt=1（find_pos=0, +len('a')=1）, search_from=1
    # anchor2: marker='b' after → gt=2（find_pos=1, +len('b')=2）, search_from=2
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},   # gt=1, d=|2-1|=1
            {"marker": "b", "position": "after"},   # gt=2, d=|2-2|=0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 预测，2 anchor，贪心 → 匹配 (0, 0, 1)（d=0）→ 1 个 anchor 用了
    # 另一 anchor 没法匹配（pred[0] 已用）
    # precision = 1/1 = 1.0；recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert abs(out["chunk_boundary_recall"]["value"] - 0.5) < 1e-9


# =========================================================================
# chunk_boundary_prf: chunk 文本含 marker
# =========================================================================


def test_chunk_boundary_prf_marker_inside_chunk_text():
    """marker 是 chunk 文本的子串（不影响 find）。"""
    doc = _make_doc(["hello world", "foo bar"])
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},  # gt = 11（"hello world" 后）
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # pred=11（hello world 末尾），gt=11，d=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf: 最后 chunk 不算边界
# =========================================================================


def test_chunk_boundary_prf_last_chunk_no_boundary():
    """最后一个 chunk 末尾不算内部边界。"""
    doc = _make_doc(["alpha", "beta"])  # 只有 alpha 末尾算边界
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 这个不会匹配任何预测
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 预测（alpha 末尾=5），1 anchor（beta 末尾=10）
    # d=5 <= 30 → match
    # 但这是验证 last chunk 不算边界 → 预测只有一个
    # 实际匹配 → P=1/1=1.0, R=1/1=1.0
    # 但这里 gt=10 距离 pred=5 是 5，仍在容差内 → match
    # 改造测试：用 tolerance=2 让 d=5 不匹配
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    assert out2["chunk_boundary_precision"]["value"] == 0.0


# =========================================================================
# figure_caption_prf: 各种输入都返固定 null
# =========================================================================


def test_figure_caption_prf_document_dict_annotation_dict():
    """document 和 annotation 都是 dict → 仍返 3 null。"""
    doc = {"chunks": [{"text": "a"}]}
    annotation = {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, annotation)
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_recall"]["value"] is None
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_prf_document_none_annotation_none():
    out = figure_caption_prf(None, None)
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_recall"]["value"] is None
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_prf_document_empty_annotation_empty():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_does_not_read_document_fields():
    """figure_caption_prf 不读 document 的任何字段（纯固定输出）。"""
    # 即使 document 含 figure_caption_relations，figure_caption_prf 仍返 null
    doc = {"figure_caption_relations": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, None)
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_read_annotation_fields():
    """figure_caption_prf 不读 annotation 的任何字段。"""
    annotation = {"figure_caption_anchors": [{"id": "x"}]}
    out = figure_caption_prf(None, annotation)
    assert out["figure_caption_precision"]["value"] is None


# =========================================================================
# chunk_boundary_prf: source-level 不动其它模块
# =========================================================================


def test_chunk_boundary_prf_source_does_not_contain_json():
    """chunk_boundary_prf 不用 json。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "import json" not in src
    assert "json." not in src


def test_chunk_boundary_prf_source_does_not_contain_subprocess():
    src = inspect.getsource(chunk_boundary_prf)
    assert "subprocess" not in src


def test_chunk_boundary_prf_source_does_not_contain_logging():
    src = inspect.getsource(chunk_boundary_prf)
    assert "logging" not in src


def test_chunk_boundary_prf_source_does_not_contain_print():
    src = inspect.getsource(chunk_boundary_prf)
    assert "print(" not in src


def test_chunk_boundary_prf_source_does_not_contain_os_module():
    src = inspect.getsource(chunk_boundary_prf)
    assert "import os" not in src


def test_chunk_boundary_prf_source_does_not_contain_pathlib():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pathlib" not in src


def test_chunk_boundary_prf_source_does_not_contain_asyncio():
    src = inspect.getsource(chunk_boundary_prf)
    assert "asyncio" not in src


def test_chunk_boundary_prf_source_does_not_contain_threading():
    src = inspect.getsource(chunk_boundary_prf)
    assert "threading" not in src


def test_chunk_boundary_prf_source_does_not_contain_concurrent():
    src = inspect.getsource(chunk_boundary_prf)
    assert "concurrent" not in src


# =========================================================================
# 模块 __all__ 顺序 + 内容
# =========================================================================


def test_module_all_exact_order_3_entries():
    """__all__ 精确顺序：PARSER_DOES_NOT_EMIT_RELATIONS / figure_caption_prf / chunk_boundary_prf。"""
    import evaluation.annotation_metrics as m
    assert m.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list():
    import evaluation.annotation_metrics as m
    assert isinstance(m.__all__, list)


def test_module_all_length_3():
    import evaluation.annotation_metrics as m
    assert len(m.__all__) == 3


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_print():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "print(" not in src


def test_module_source_does_not_contain_logging():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "logging" not in src


def test_module_source_does_not_contain_subprocess():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "subprocess" not in src


def test_module_source_does_not_contain_asyncio():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "asyncio" not in src


def test_module_source_does_not_contain_threading():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "threading" not in src


def test_module_source_does_not_contain_os_module():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "import os" not in src


def test_module_source_does_not_contain_pathlib():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "pathlib" not in src


def test_module_source_does_not_contain_concurrent_futures():
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "concurrent.futures" not in src


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量
# =========================================================================


def test_parser_does_not_emit_relations_value_exact():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_module_identity():
    import evaluation.annotation_metrics as m
    assert PARSER_DOES_NOT_EMIT_RELATIONS is m.PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_underscore_case():
    """值用 snake_case（不含空格、不含驼峰）。"""
    s = PARSER_DOES_NOT_EMIT_RELATIONS
    assert " " not in s
    assert s == s.lower()


# =========================================================================
# chunk_boundary_prf: 不依赖 evaluation.metrics._null/_ratio 的内部实现
# =========================================================================


def test_chunk_boundary_prf_null_uses_evaluation_metrics_null():
    """chunk_boundary_prf 的 _null 调用来自 evaluation.metrics。"""
    import evaluation.annotation_metrics as m
    # 验证 _null 引用是 evaluation.metrics._null
    from evaluation.metrics import _null as metrics_null
    # 直接引用对比（通过模块命名空间）
    assert m._null is metrics_null


def test_chunk_boundary_prf_ratio_uses_evaluation_metrics_ratio():
    """chunk_boundary_prf 的 _ratio 调用来自 evaluation.metrics。"""
    import evaluation.annotation_metrics as m
    from evaluation.metrics import _ratio as metrics_ratio
    assert m._ratio is metrics_ratio


# =========================================================================
# chunk_boundary_prf: normalize_text 来自 app.chunkers.structural
# =========================================================================


def test_chunk_boundary_prf_normalize_text_from_app_chunkers():
    """normalize_text 来自 app.chunkers.structural。"""
    import evaluation.annotation_metrics as m
    from app.chunkers.structural import normalize_text
    assert m.normalize_text is normalize_text


# =========================================================================
# chunk_boundary_prf: 多次调用独立
# =========================================================================


def test_chunk_boundary_prf_three_calls_independent():
    """三次调用结果相等但 dict 不同。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    o2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    o3 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # value 相等
    assert o1 == o2 == o3
    # dict 不同
    assert o1 is not o2
    assert o2 is not o3
    assert o1 is not o3


def test_chunk_boundary_prf_modify_output_does_not_affect_next_call():
    """修改输出不影响下次调用。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    saved_value = o1["chunk_boundary_precision"]["value"]
    o1["chunk_boundary_precision"]["value"] = "tampered"
    o2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert o2["chunk_boundary_precision"]["value"] == saved_value


# =========================================================================
# chunk_boundary_prf: 各种 falsy annotation
# =========================================================================


def test_chunk_boundary_prf_annotation_empty_dict():
    """annotation={} → falsy → no_annotation 分支。"""
    doc = _make_doc(["a", "b"])
    out = chunk_boundary_prf(doc, {}, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_none():
    """annotation=None → falsy → no_annotation 分支。"""
    doc = _make_doc(["a", "b"])
    out = chunk_boundary_prf(doc, None, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_no_chunk_boundary_anchors_key():
    """annotation 不含 chunk_boundary_anchors 键 → anchors=[] → no_ground_truth_anchors 分支。"""
    doc = _make_doc(["a", "b"])
    out = chunk_boundary_prf(doc, {"other_key": 1}, tolerance_chars=30)
    # annotation 非空但 anchors 空 → 走 no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_annotation_chunk_boundary_anchors_empty():
    """annotation.chunk_boundary_anchors=[] → no_ground_truth_anchors 分支。"""
    doc = _make_doc(["a", "b"])
    out = chunk_boundary_prf(
        doc, {"chunk_boundary_anchors": []}, tolerance_chars=30
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf: chunks 各种情况
# =========================================================================


def test_chunk_boundary_prf_chunks_missing_key():
    """document 不含 chunks 键 → chunks=[] → no_predicted_boundaries 分支。"""
    doc = {"elements": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # chunks=[] or len(chunks)<2 → no_predicted_boundaries
    # 但 anchors 非空 → recall = _ratio(0.0)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_chunks_empty_list():
    """document.chunks=[] → no_predicted_boundaries 分支。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_chunks_one_element():
    """document.chunks=[单个] → no_predicted_boundaries 分支。"""
    doc = {"chunks": [{"text": "only"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "only", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # len(chunks)=1 < 2 → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_two_elements_with_no_anchors():
    """chunks>=2 + anchors=[] → no_ground_truth_anchors 分支。"""
    doc = _make_doc(["a", "b"])
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 走 no_ground_truth_anchors 分支（anchors 为空 + chunks>=2）
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"
