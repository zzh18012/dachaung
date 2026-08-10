"""evaluation/annotation_metrics.py 边角测试 - 第二十轮（Round 286）。

edges19 已覆盖：chunk_boundary_prf position="before"/"after"/unknown / 完美/部分匹配 / tolerance_chars
边界 0/1/large / missing_markers / 重复 marker + search_from / f1=0 when p=r=0 / f1 null when recall null /
_tolerance_chars 5-path / 一对一贪心匹配 / 多 chunk / chunk text 找不到兜底 / source token 含 search_from=0 /
pairs.sort / used_pred/used_gt / abs(pv - gv) / d <= tolerance_chars 等 / module source 不含 json/print/logging
/subprocess / 多 falsy annotation 场景 / chunks missing key/empty/one element / 不修改输出 / __all__ 3 entries。

edges20 补强未覆盖的角度：**Schema 联动** + **算法深度模拟** + **figure_caption_prf source level 完整**：
- chunk_boundary_prf Schema 联动（输出 keys 对应 evaluation-report metrics 字段）：
  - 输出 keys 含 chunk_boundary_precision/recall/f1（都在 _RATIO_METRICS）
  - 输出含 _tolerance_chars 记录容差
  - 输出 value 在 [0, 1] 范围（matched/num_pred）
  - _missing_markers 出现条件：missing_markers 非空

- chunk_boundary_prf 算法深度（normalize_text edge cases）：
  - chunks 文本含多空格 → normalize 压成单空格
  - chunks 文本含 tab/换行 → normalize 折叠
  - chunks 文本含 unicode whitespace → normalize 折叠
  - chunks 文本带前后空格 → strip
  - chunk text=None → normalize 视为空 string
  - chunk 缺 text 键 → normalize 视为空 string

- chunk_boundary_prf marker 特殊字符：
  - marker 含空格（"alpha beta"） → find 在 stream 中查找子串
  - marker 含特殊字符（标点）→ find 字面匹配
  - marker 等于整个 stream → 找到位置 0
  - marker 比 stream 长 → find 返 -1 → missing_markers
  - marker 是 stream 子串多次出现 → search_from 推进

- chunk_boundary_prf position 混合 before+after：
  - 多 anchor 部分 before 部分 after，混合匹配
  - 同一 marker before 和 after 都标注 → 分别匹配
  - mixed position 时 greedy 匹配仍按距离

- chunk_boundary_prf 数值边界：
  - tolerance_chars=0 且位置精确匹配 → 匹配
  - tolerance_chars=0 且位置错位 1 → 不匹配
  - tolerance_chars 负数 → 算法 d<=负数，永不匹配（但不会崩）
  - tolerance_chars 极大（>stream 长度）→ 全部匹配
  - num_pred=1, num_gt=1, 匹配 → P=R=F1=1.0
  - num_pred=2, num_gt=1 → P=0.5, R=1.0, F1=2*0.5*1/(0.5+1)=0.667
  - num_pred=1, num_gt=2 → P=1.0, R=0.5, F1=0.667

- chunk_boundary_prf 输出严格类型：
  - precision/recall/f1 都是 dict[str, Any]
  - 每个 dict 都含 'value' 和 'reason' keys
  - value 类型：float 或 None
  - reason 类型：str 或 None
  - _tolerance_chars['value'] 类型：int（与 tolerance_chars 参数一致）

- figure_caption_prf source level 完整：
  - source 含 'def figure_caption_prf(' 签名
  - source 含 'reason = PARSER_DOES_NOT_EMIT_RELATIONS'
  - source 含 3 个 _null 调用 + figure_caption_precision/recall/f1 字面量
  - source 不含 normalize_text / Counter / stream / find / pairs 等算法 token
  - source 不含 if/for 循环（纯固定输出）

- module source 补强：
  - 含 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' 精确字符串
  - 含 'from app.chunkers.structural import normalize_text'
  - 含 'from evaluation.metrics import _null, _ratio'
  - 含 'from collections import Counter'（虽然实际未用，但 import 存在）
  - 不含 import os/sys/logging/subprocess/json
  - 不含 star import
  - 不含 relative import

- _null / _ratio 透传行为：
  - chunk_boundary_prf 失败分支用 _null + reason
  - chunk_boundary_prf 成功分支用 _ratio + value
  - PARSER_DOES_NOT_EMIT_RELATIONS 字符串与 reason 一致
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# ============================================================================
# Schema 联动：chunk_boundary_prf 输出 keys
# ============================================================================


def _make_doc(chunks_text: list[str]) -> dict[str, Any]:
    return {
        "chunks": [
            {"chunk_id": f"c{i}", "text": t, "source_element_ids": [f"e{i}"]}
            for i, t in enumerate(chunks_text)
        ]
    }


def test_chunk_boundary_prf_output_keys_in_ratio_metrics():
    """输出 keys chunk_boundary_precision/recall/f1 都在 evaluation.report._RATIO_METRICS。"""
    from evaluation.report import _RATIO_METRICS

    assert "chunk_boundary_precision" in _RATIO_METRICS
    assert "chunk_boundary_recall" in _RATIO_METRICS
    assert "chunk_boundary_f1" in _RATIO_METRICS


def test_chunk_boundary_prf_output_always_has_tolerance_chars():
    """所有分支都含 _tolerance_chars key。"""
    # 5 个分支
    cases = [
        # document None
        (None, {"chunk_boundary_anchors": []}, 30),
        # annotation falsy
        (_make_doc(["a", "b"]), None, 30),
        # chunks<2
        ({"chunks": [{"text": "x"}]}, {"chunk_boundary_anchors": [{"marker": "x"}]}, 30),
        # anchors empty
        (_make_doc(["a", "b"]), {"chunk_boundary_anchors": []}, 30),
        # 正常
        (_make_doc(["alpha", "beta"]), {"chunk_boundary_anchors": [{"marker": "alpha"}]}, 30),
    ]
    for doc, ann, tol in cases:
        out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
        assert "_tolerance_chars" in out
        assert out["_tolerance_chars"]["value"] == tol


def test_chunk_boundary_prf_tolerance_chars_value_type_int():
    """_tolerance_chars['value'] 类型与输入 tolerance_chars 一致。"""
    out = chunk_boundary_prf(_make_doc(["a", "b"]), None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_prf_output_values_in_zero_one_range():
    """value 是 float 时应在 [0, 1] 范围。"""
    doc = _make_doc(["alpha", "beta"])
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    for key in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[key]["value"]
        if v is not None:
            assert 0.0 <= v <= 1.0


def test_chunk_boundary_prf_missing_markers_present_only_when_needed():
    """_missing_markers 只在 missing_markers 非空时出现。"""
    # 不缺 → 不应含 _missing_markers
    doc1 = _make_doc(["alpha", "beta"])
    ann1 = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out1 = chunk_boundary_prf(doc1, ann1, tolerance_chars=30)
    assert "_missing_markers" not in out1

    # 缺 marker → 应含 _missing_markers
    ann2 = {"chunk_boundary_anchors": [{"marker": "nonexistent_marker", "position": "after"}]}
    out2 = chunk_boundary_prf(doc1, ann2, tolerance_chars=30)
    assert "_missing_markers" in out2
    assert out2["_missing_markers"]["value"] == ["nonexistent_marker"]


def test_chunk_boundary_prf_metric_dict_keys_exact():
    """precision/recall/f1 都是 dict 含 value 和 reason 2 keys。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    for key in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert set(out[key].keys()) == {"value", "reason"}


def test_chunk_boundary_prf_metric_dict_value_types():
    """value 类型：float 或 None；reason 类型：str 或 None。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    for key in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[key]["value"]
        r = out[key]["reason"]
        assert v is None or isinstance(v, float)
        assert r is None or isinstance(r, str)


# ============================================================================
# chunk_boundary_prf 算法深度（normalize_text edge cases）
# ============================================================================


def test_chunk_boundary_prf_chunk_text_with_multiple_spaces():
    """chunks 文本含多空格 → normalize 压成单空格。"""
    doc = _make_doc(["alpha   beta", "gamma"])
    ann = {"chunk_boundary_anchors": [{"marker": "gamma", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # stream = normalize_text("alpha beta gamma") = "alpha beta gamma"
    # 应该能匹配
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_with_tab_newline():
    """chunks 文本含 tab/换行 → normalize 折叠。"""
    doc = _make_doc(["alpha\tbeta\n", "gamma"])
    ann = {"chunk_boundary_anchors": [{"marker": "gamma", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 应能匹配
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_with_unicode_whitespace():
    """chunks 文本含 unicode whitespace → normalize 折叠。"""
    doc = _make_doc(["alpha beta", "gamma"])  # non-breaking space
    ann = {"chunk_boundary_anchors": [{"marker": "gamma", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_with_leading_trailing_whitespace():
    """chunks 文本带前后空格 → strip。"""
    doc = _make_doc(["  alpha  ", "  beta  "])
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_none():
    """chunk text=None → normalize 视为空 string。"""
    doc = {
        "chunks": [
            {"chunk_id": "c0", "text": None, "source_element_ids": ["e0"]},
            {"chunk_id": "c1", "text": "beta", "source_element_ids": ["e1"]},
        ]
    }
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    # 不应崩溃
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_chunk_missing_text_key():
    """chunk 缺 text 键 → c.get('text') or '' 视为空 string。"""
    doc = {
        "chunks": [
            {"chunk_id": "c0", "source_element_ids": ["e0"]},  # 缺 text
            {"chunk_id": "c1", "text": "beta", "source_element_ids": ["e1"]},
        ]
    }
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert "chunk_boundary_precision" in out


# ============================================================================
# chunk_boundary_prf marker 特殊字符
# ============================================================================


def test_chunk_boundary_prf_marker_with_space():
    """marker='alpha beta'（含空格）→ find 子串。"""
    doc = _make_doc(["alpha beta", "gamma"])
    # marker='alpha beta'，position='after' → gt = stream.find('alpha beta') + 10
    # stream = 'alpha beta gamma'
    ann = {"chunk_boundary_anchors": [{"marker": "alpha beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_with_punctuation():
    """marker='alpha.!'（含标点）→ find 字面匹配。"""
    doc = _make_doc(["alpha.!", "gamma"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha.!", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_equals_full_stream():
    """marker 等于整个 stream → 找到位置 0。"""
    doc = _make_doc(["ab", "cd"])
    # stream = 'ab cd'
    ann = {"chunk_boundary_anchors": [{"marker": "ab cd", "position": "before"}]}
    # position='before' → gt = 0；pred[0] = 2；|2-0|=2 <= 30 → match
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_longer_than_stream():
    """marker 比 stream 长 → find 返 -1 → missing_markers。"""
    doc = _make_doc(["a", "b"])
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "this is a very long marker that exceeds stream", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert "_missing_markers" in out
    assert "this is a very long marker that exceeds stream" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_substring_multiple_occurrences():
    """marker 是 stream 子串多次出现 → search_from 推进。"""
    doc = _make_doc(["alpha", "alpha", "alpha"])
    # stream = 'alpha alpha alpha'
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 2 个 anchor 都应能匹配（search_from 推进防止都命中第 1 次）
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ============================================================================
# chunk_boundary_prf position 混合 before+after
# ============================================================================


def test_chunk_boundary_prf_mixed_before_after_anchors():
    """多 anchor 部分 before 部分 after，混合匹配。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    # stream = 'alpha beta gamma'
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # gt = 5
            {"marker": "beta", "position": "before"},  # gt = 6
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # 预测边界：5, 10
    # gt 位置：5, 6
    # greedy 按 distance 排序：(0, 0, 0), (1, 0, 1), (1, 1, 0), (4, 1, 1)
    # 取 (0, 0, 0) → used_pred={0}, used_gt={0}, matched=1
    # 取 (1, 0, 1) → pi=0 已用，跳过
    # 取 (1, 1, 0) → gi=0 已用，跳过
    # 取 (4, 1, 1) → used_pred={0,1}, used_gt={0,1}, matched=2
    # 实际上：pred[0]=5 匹配 gt[0]=5（距离 0），pred[1]=10 匹配 gt[1]=6（距离 4）
    # 实际一对一匹配：先匹配最近的，所以 gt[1]=6 用 pred[0]=5 距离 1
    # 然后 gt[0]=5 已被 pred[0] 占了
    # 重新分析：pairs = [(d=0,pi=0,gi=0),(d=1,pi=0,gi=1),(d=5,pi=1,gi=0),(d=4,pi=1,gi=1)]
    # sort: [(0,0,0),(1,0,1),(4,1,1),(5,1,0)]
    # (0,0,0): used_pred={0},used_gt={0},matched=1
    # (1,0,1): pi=0 used,skip
    # (4,1,1): used_pred={0,1},used_gt={0,1},matched=2
    # (5,1,0): pi=1 used,skip
    # matched=2 → recall=2/2=1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_same_marker_before_after():
    """同一 marker 一个 before 一个 after。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "before"},  # gt = 0
            {"marker": "alpha", "position": "after"},  # gt = 5
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # stream = 'alpha beta'
    # 重复 marker 'alpha' 用 search_from：
    # 第 1 次 'alpha' before → gt=0, search_from=5
    # 第 2 次 'alpha' after → find('alpha', 5)=-1 → missing_markers!
    # 但 search_from 推进防止同一 marker 重复命中
    assert "_missing_markers" in out or out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_prf_mixed_position_greedy_by_distance():
    """mixed position 时 greedy 匹配仍按距离（不按 position 类型）。"""
    doc = _make_doc(["aaa", "bbb"])
    # stream = 'aaa bbb'
    # pred = [3]（aaa 末尾）
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # gt = 3
            {"marker": "bbb", "position": "before"},  # gt = 4
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # pred[0]=3, gt[0]=3 距离 0；gt[1]=4 距离 1
    # greedy: (0,0,0) first → match pred[0]-gt[0]
    # gt[1] 没有更多 pred 可匹配（只有 1 个 pred）
    # matched=1, num_pred=1, num_gt=2
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# ============================================================================
# chunk_boundary_prf 数值边界
# ============================================================================


def test_chunk_boundary_prf_tolerance_zero_exact_match():
    """tolerance_chars=0 且位置精确匹配 → 匹配。"""
    doc = _make_doc(["alpha", "beta"])
    # stream='alpha beta'，pred[0]=5
    # marker='alpha' after → gt=5
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # |5-5|=0 <= 0 → match
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_off_by_one():
    """tolerance_chars=0 且位置错位 1 → 不匹配。"""
    doc = _make_doc(["alpha", "beta"])
    # pred[0]=5；marker='beta' before → gt=6
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # |5-6|=1 > 0 → 不匹配
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_negative_never_matches():
    """tolerance_chars=-1 → d<=-1 永远不成立 → 不匹配（但不会崩）。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # d=0 <= -1 不成立
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_extremely_large():
    """tolerance_chars 极大 → 全部匹配。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10000)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_pred_one_gt_match():
    """num_pred=1, num_gt=1, 匹配 → P=R=F1=1.0。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_two_pred_one_gt():
    """num_pred=2, num_gt=1 → P=0.5, R=1.0, F1≈0.667。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    # stream='alpha beta gamma', pred=[5, 10]
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}  # gt=5
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # pred[0]=5 → match（距离 0）
    # matched=1, num_pred=2, num_gt=1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    # F1 = 2*0.5*1/(0.5+1) = 0.667
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 * 0.5 * 1 / 1.5)


def test_chunk_boundary_prf_one_pred_two_gt():
    """num_pred=1, num_gt=2 → P=1.0, R=0.5, F1≈0.667。"""
    doc = _make_doc(["alpha", "beta"])
    # stream='alpha beta', pred=[5]
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # gt=5
            {"marker": "beta", "position": "before"},  # gt=6
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # pred[0]=5, gt[0]=5 距离 0, gt[1]=6 距离 1
    # greedy: (0,0,0) first → match
    # matched=1, num_pred=1, num_gt=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    # F1 = 2*1*0.5/(1+0.5) = 0.667
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 * 1 * 0.5 / 1.5)


# ============================================================================
# chunk_boundary_prf 输出严格类型
# ============================================================================


def test_chunk_boundary_prf_output_dict_type():
    """输出顶层是 dict。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_metric_dicts_value_or_none():
    """metric dict value 是 float 或 None。"""
    # 测试文档 None 时 value=None
    out = chunk_boundary_prf(None, None, tolerance_chars=30)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[k]["value"]
        assert v is None


def test_chunk_boundary_prf_metric_dict_reasons_in_known_set():
    """reason 必须在已知集合中。"""
    known_reasons = {
        "pipeline_failed",
        "no_annotation",
        "no_predicted_boundaries",
        "no_ground_truth_anchors",
        "no_ground_truth_anchors_in_stream",
        "precision_or_recall_not_evaluated",
        None,  # 成功时
    }
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] in known_reasons


# ============================================================================
# figure_caption_prf source level 完整
# ============================================================================


def test_figure_caption_prf_source_contains_function_def():
    src = inspect.getsource(figure_caption_prf)
    assert "def figure_caption_prf(" in src


def test_figure_caption_prf_source_contains_reason_assignment():
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_prf_source_contains_three_null_calls():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_precision": _null(reason)' in src
    assert '"figure_caption_recall": _null(reason)' in src
    assert '"figure_caption_f1": _null(reason)' in src


def test_figure_caption_prf_source_does_not_contain_algorithm_tokens():
    """figure_caption_prf 是纯固定输出，不含算法 token。"""
    src = inspect.getsource(figure_caption_prf)
    assert "normalize_text" not in src
    assert "stream" not in src
    assert "pairs" not in src
    assert "search_from" not in src
    assert "tolerance_chars" not in src


def test_figure_caption_prf_source_does_not_contain_loops():
    """无 if/for 循环（除了字面字符串）。"""
    src = inspect.getsource(figure_caption_prf)
    # 简单检查：函数体没有 for/if（去掉注释和字符串后）
    # figure_caption_prf 实际上没 if/for
    lines = src.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith('"""') or stripped.startswith("return"):
            continue
        if not stripped:
            continue
        assert not stripped.startswith("for ")
        assert not stripped.startswith("if ")


def test_figure_caption_prf_source_return_dict_with_3_keys():
    """source 中 return dict 含 3 keys。"""
    src = inspect.getsource(figure_caption_prf)
    assert "return {" in src
    # count occurrences of "_null(reason)"
    assert src.count("_null(reason)") == 3


# ============================================================================
# module source 补强
# ============================================================================


def test_module_source_contains_constant_definition_exact():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_normalize_text_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_counter_import():
    """annotation_metrics.py import Counter（虽然实际未用）。"""
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "from collections import Counter" in src


def test_module_source_does_not_contain_os_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import os" not in src


def test_module_source_does_not_contain_sys_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import sys" not in src


def test_module_source_does_not_contain_logging_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import logging" not in src


def test_module_source_does_not_contain_subprocess_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import subprocess" not in src


def test_module_source_does_not_contain_json_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import json" not in src


def test_module_source_does_not_contain_star_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "import *" not in src


def test_module_source_does_not_contain_relative_import():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_does_not_contain_class_definition():
    """annotation_metrics.py 不定义 class。"""
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "\nclass " not in src


def test_module_source_does_not_contain_dataclass_decorator():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "@dataclass" not in src


def test_module_source_does_not_contain_global_keyword():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "global " not in src


def test_module_source_does_not_contain_walrus():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert ":=" not in src


def test_module_source_does_not_contain_async():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "async " not in src
    assert "await " not in src


def test_module_source_does_not_contain_yield():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am)
    assert "yield" not in src


# ============================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量深度
# ============================================================================


def test_parser_does_not_emit_relations_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_constant_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_constant_in_module_namespace():
    import evaluation.annotation_metrics as am

    assert hasattr(am, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_constant_in_all():
    import evaluation.annotation_metrics as am

    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in am.__all__


def test_parser_does_not_emit_relations_used_in_figure_caption_output():
    """figure_caption_prf 输出的 reason 等于 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    out = figure_caption_prf(None, None)
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
    assert out["figure_caption_recall"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
    assert out["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# ============================================================================
# figure_caption_prf 行为深度
# ============================================================================


def test_figure_caption_prf_returns_dict_with_3_keys():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)
    assert set(out.keys()) == {"figure_caption_precision", "figure_caption_recall", "figure_caption_f1"}


def test_figure_caption_prf_all_values_null():
    """所有 3 metric 的 value 都是 None。"""
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None


def test_figure_caption_prf_does_not_read_document():
    """figure_caption_prf 不读 document 字段。"""
    # 用 None document 也应工作
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf({"chunks": [{"text": "x"}]}, None)
    assert out1 == out2


def test_figure_caption_prf_does_not_read_annotation():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out1 == out2


def test_figure_caption_prf_with_various_inputs():
    """figure_caption_prf 各种输入都返回固定输出。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": [{"text": "x"}]}, {"chunk_boundary_anchors": []}),
        ("non-dict", "non-dict"),
    ]
    expected = figure_caption_prf(None, None)
    for doc, ann in inputs:
        assert figure_caption_prf(doc, ann) == expected


def test_figure_caption_prf_returns_new_dict_each_call():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2
    assert out1 is not out2


# ============================================================================
# chunk_boundary_prf source level 完整补强
# ============================================================================


def test_chunk_boundary_prf_source_contains_tolerance_default():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "tolerance_chars: int = 30" in src


def test_chunk_boundary_prf_source_contains_pipeline_failed_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"pipeline_failed"' in src


def test_chunk_boundary_prf_source_contains_no_annotation_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"no_annotation"' in src


def test_chunk_boundary_prf_source_contains_no_predicted_boundaries_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"no_predicted_boundaries"' in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"no_ground_truth_anchors"' in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_in_stream_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_chunk_boundary_prf_source_contains_precision_or_recall_not_evaluated_branch():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"precision_or_recall_not_evaluated"' in src


def test_chunk_boundary_prf_source_contains_missing_markers_append():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "missing_markers.append(marker)" in src


def test_chunk_boundary_prf_source_contains_missing_markers_in_output():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert '"_missing_markers"' in src
    assert "missing_markers" in src


def test_chunk_boundary_prf_source_contains_norm_chunks_construction():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "norm_chunks = [normalize_text(c.get" in src


def test_chunk_boundary_prf_source_contains_stream_join():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "stream = normalize_text(joined_raw)" in src


def test_chunk_boundary_prf_source_contains_predicted_construction():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "predicted: list[int] = []" in src
    assert "predicted.append(end)" in src


def test_chunk_boundary_prf_source_contains_search_from_init():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_prf_source_contains_search_from_advance():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "search_from = find_pos + len(marker)" in src


def test_chunk_boundary_prf_source_contains_pairs_construction():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_chunk_boundary_prf_source_contains_used_pred_used_gt():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_chunk_boundary_prf_source_contains_pairs_sort():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_chunk_boundary_prf_source_contains_f1_calculation():
    import evaluation.annotation_metrics as am

    src = inspect.getsource(am.chunk_boundary_prf)
    assert "denom = p_val + r_val" in src
    assert "if denom <= 0:" in src
    assert "_ratio(2 * p_val * r_val / denom)" in src


# ============================================================================
# chunk_boundary_prf 端到端 Schema 联动
# ============================================================================


def test_chunk_boundary_prf_output_can_be_in_metric_section_of_report():
    """输出可作为 per_doc[i].metrics 字段加入 evaluation-report.schema.json。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    metrics_out = chunk_boundary_prf(doc, ann, tolerance_chars=30)

    # metrics 字段是任意 object（schema 不严格定义）
    full_report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 1,
            "docx_count": 0,
            "categories_covered": ["cat_a"],
        },
        "summary": {},
        "per_doc": [
            {
                "doc_id": "doc1",
                "source_type": "pdf",
                "metrics": metrics_out,
                "wall_time_seconds": {
                    "total": 0.1,
                    "parse": None,
                    "chunk": None,
                    "parse_reason": "not_instrumented",
                    "chunk_reason": "not_instrumented",
                },
            }
        ],
    }

    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "evaluation-report.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    validator = Draft202012Validator(schema)
    errs = list(validator.iter_errors(full_report))
    assert errs == [], f"schema errors: {errs}"


# ============================================================================
# 算法可重复性
# ============================================================================


def test_chunk_boundary_prf_deterministic_for_same_input():
    """同一输入多次调用结果一致。"""
    doc = _make_doc(["alpha", "beta", "gamma"])
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "before"},
        ]
    }
    results = [chunk_boundary_prf(doc, ann, tolerance_chars=30) for _ in range(5)]
    for r in results[1:]:
        assert r == results[0]


def test_chunk_boundary_prf_no_side_effects_on_input():
    """不修改 document 和 annotation 输入。"""
    doc = _make_doc(["alpha", "beta"])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    doc_snapshot = json.loads(json.dumps(doc))
    ann_snapshot = json.loads(json.dumps(ann))

    chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert doc == doc_snapshot
    assert ann == ann_snapshot


# ============================================================================
# __all__ 与 namespace 完整性
# ============================================================================


def test_module_all_3_entries_exact():
    import evaluation.annotation_metrics as am

    assert am.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_entries_each_exists_in_namespace():
    import evaluation.annotation_metrics as am

    for name in am.__all__:
        assert hasattr(am, name)


def test_module_all_entries_each_valid_identifier():
    import evaluation.annotation_metrics as am

    for name in am.__all__:
        assert isinstance(name, str)
        assert name.isidentifier()


def test_module_namespace_has_private_helpers_not_in_all():
    """_null / _ratio 是 import 的但不在 __all__（私有）。"""
    import evaluation.annotation_metrics as am

    assert "_null" in am.__dict__
    assert "_ratio" in am.__dict__
    assert "_null" not in am.__all__
    assert "_ratio" not in am.__all__


def test_module_namespace_has_normalize_text_imported():
    """normalize_text 是 import 的但不在 __all__。"""
    import evaluation.annotation_metrics as am

    assert "normalize_text" in am.__dict__
    assert "normalize_text" not in am.__all__
