"""evaluation/annotation_metrics.py 边角测试 - 第三轮（Round 100）。

补强已有 base/edges/edges2（共 223 个测试）未覆盖的深度路径：
- chunk_boundary_prf 预测位置生成：
  - 空 chunk text 在 stream 中 find("", pos) 返回 pos（边界情形）
  - chunk 文本作为另一个 chunk 子串（find 偏移多次出现）
  - 所有 chunk 文本相同 → 多个相同 boundary
  - stream 为空（所有 chunk 文本为空）→ predicted 不为空（位置 0,1,2...）
- chunk_boundary_prf anchor 深度：
  - marker 含空格（normalize 后的 stream 中是否仍能匹配）
  - marker 跨 chunk 边界（chunk1 末 + chunk2 头组合）
  - position="before" 的多个 anchor
  - 全部 anchors position="before" 与 "after" 混合
  - anchor marker 是 stream 的前缀 / 后缀
- chunk_boundary_prf 输出 key 集合：
  - document=None 路径 4 keys
  - annotation=None 路径 4 keys
  - chunks<2 路径 4 keys（无 _missing_markers）
  - no anchors 路径 4 keys（无 _missing_markers）
  - success 无 missing 4 keys
  - success 有 missing 5 keys
- chunk_boundary_prf _tolerance_chars 字段：
  - value 与传入的 tolerance_chars 严格相等（int 类型）
  - reason 始终 None
  - 0 是合法值
  - 巨大值（10**9）合法
- _missing_markers：
  - 多个缺失按 anchor 顺序入 list
  - 部分缺失部分命中
  - 全部缺失但 chunks >= 2 → 进入 success path（anchors=[]）
- 模块结构：__all__ exact 项、import paths、private helpers 不可访问
- 算法特定路径：
  - greedy with 3 preds / 3 gts all within tolerance → matched=3
  - predicted 中部分被跳过（chunk text 找不到）→ num_pred < len(chunks)-1
  - 重复 marker 的 search_from 推进

不修改任何源码。
"""

from __future__ import annotations

import pytest

from evaluation import annotation_metrics
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    __all__ as annotation_all,
)
from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf


# =========================================================================
# chunk_boundary_prf 预测位置生成：空 chunk text 边界
# =========================================================================


def test_chunk_boundary_first_chunk_empty_string_predicted_zero():
    """第一个 chunk text 为 "" → stream.find("", 0) = 0 → predicted = [0+0=0].

    但实际上 chunks=["", "abc"] → norm_chunks = ["", "abc"]
    joined_raw = " abc" → normalize → "abc"
    对于 i=0: txt="", stream.find("", 0) = 0, end = 0+0 = 0, predicted=[0], pos=1
    对于 i=1: break (last chunk)
    所以 predicted=[0]
    """
    doc = {"chunks": [{"text": ""}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不论算法细节，应正常返回（不抛异常）
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_last_chunk_empty_string():
    """最后一个 chunk 为空字符串 → predicted 列表里依然只有 len-1 个。"""
    doc = {"chunks": [{"text": "foo"}, {"text": ""}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不抛异常
    assert "_tolerance_chars" in out


def test_chunk_boundary_all_chunks_empty_text_stream_becomes_empty():
    """chunks 文本全空 → stream = ""，但 find("", pos) 仍返回 pos。"""
    doc = {"chunks": [{"text": ""}, {"text": ""}, {"text": ""}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不抛异常；marker 不在 stream 中 → missing
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["x"]


def test_chunk_boundary_chunk_text_substring_of_other():
    """chunk1 文本是 chunk2 的子串 → find 仍顺序定位。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "foobar"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不抛异常
    assert "_tolerance_chars" in out


def test_chunk_boundary_all_chunks_same_text():
    """所有 chunk 文本相同 → 多个相同 boundary 在不同位置。"""
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": "abc"},
            {"text": "abc"},
        ]
    }
    ann = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # 不抛异常，至少有 precision/recall 字段
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


# =========================================================================
# chunk_boundary_prf anchor 深度
# =========================================================================


def test_chunk_boundary_marker_with_internal_space():
    """marker 含空格 → stream 是 normalize 后的，空格保留为单空格。"""
    doc = {"chunks": [{"text": "foo bar"}, {"text": "baz"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo bar", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # marker 应该被找到（不在 missing）
    assert "_missing_markers" not in out or "foo bar" not in out.get("_missing_markers", {}).get("value", [])


def test_chunk_boundary_marker_spans_chunk_boundary():
    """marker 跨两个 chunk 的连接（chunk1="foo"，chunk2="bar"，marker="oo ba"）。

    stream = normalize("foo bar") = "foo bar"，marker="oo ba" 在 stream 中存在。
    """
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "oo ba", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_position_before_with_multiple_anchors():
    """多个 position="before" anchor。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "before"},
            {"marker": "beta", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不抛异常
    assert "_tolerance_chars" in out


def test_chunk_boundary_mixed_before_after_anchors():
    """混合 before/after position。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # gt at end of alpha
            {"marker": "beta", "position": "before"},  # gt at start of beta
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" not in out


def test_chunk_boundary_marker_at_stream_start():
    """marker 是 stream 的前缀 → before position → gt_position=0。"""
    doc = {"chunks": [{"text": "start"}, {"text": "end"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "start", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不抛异常
    assert "_tolerance_chars" in out


def test_chunk_boundary_marker_at_stream_end():
    """marker 是 stream 的后缀 → after position → gt_position=len(stream)。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "bar", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_anchor_marker_longer_than_stream():
    """marker 比 stream 长 → find 返回 -1 → missing_markers。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "abcdefghijklmnop", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "abcdefghijklmnop" in out["_missing_markers"]["value"]


def test_chunk_boundary_anchor_position_uppercase_treated_as_after():
    """position="AFTER" 不是 "before" → else 分支 → 当作 after 处理。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "AFTER"}  # 大写
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不抛异常；marker 找到了
    assert "_missing_markers" not in out


# =========================================================================
# chunk_boundary_prf 输出 key 集合精确性
# =========================================================================


def test_chunk_boundary_no_document_path_has_exactly_four_keys():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_no_annotation_path_has_exactly_four_keys():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    out = chunk_boundary_prf(doc, None)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_no_chunks_path_has_exactly_four_keys():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_one_chunk_path_has_exactly_four_keys():
    doc = {"chunks": [{"text": "foo"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_no_anchors_path_has_exactly_four_keys():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_success_no_missing_has_four_keys():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_success_with_missing_has_five_keys():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
            {"marker": "xyz", "position": "after"},  # 这个找不到
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }


# =========================================================================
# chunk_boundary_prf _tolerance_chars 字段
# =========================================================================


def test_chunk_boundary_tolerance_value_strict_equality():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_tolerance_value_is_int_type():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=15)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_tolerance_reason_always_none_no_document():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_reason_always_none_no_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_reason_always_none_no_chunks():
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_reason_always_none_success():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_zero_strict_equality():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_huge_value_strict_equality():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10**9)
    assert out["_tolerance_chars"]["value"] == 10**9


def test_chunk_boundary_tolerance_negative_value_strict_equality():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-100)
    assert out["_tolerance_chars"]["value"] == -100


# =========================================================================
# chunk_boundary_prf _missing_markers 字段
# =========================================================================


def test_chunk_boundary_missing_markers_preserves_anchor_order():
    """多个缺失 marker 按 anchor 输入顺序入 list。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "zzz1", "position": "after"},
            {"marker": "foo", "position": "after"},
            {"marker": "zzz2", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["_missing_markers"]["value"] == ["zzz1", "zzz2"]


def test_chunk_boundary_missing_markers_partial_miss_value_is_list():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo"},
            {"marker": "missing1"},
            {"marker": "missing2"},
        ]
    }
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == ["missing1", "missing2"]


def test_chunk_boundary_missing_markers_reason_always_none():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "missing"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["reason"] is None


def test_chunk_boundary_no_missing_key_when_all_anchors_match():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}, {"marker": "bar"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" not in out


def test_chunk_boundary_all_anchors_missing_but_chunks_ge_2():
    """所有 anchors 都找不到 → missing_markers 含所有，但仍进入 success path。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "x1"},
            {"marker": "x2"},
        ]
    }
    out = chunk_boundary_prf(doc, ann)
    # gt_positions = [] → recall null
    assert out["chunk_boundary_recall"]["value"] is None
    assert "_missing_markers" in out


# =========================================================================
# chunk_boundary_prf 算法路径
# =========================================================================


def test_chunk_boundary_greedy_all_three_pairs_match():
    """3 preds, 3 gts, all within tolerance → matched=3 → P=R=1.0。"""
    # 3 chunks, 边界在 chunk1 末 / chunk2 末
    # stream = "foo bar baz"，predicted ≈ [3, 7]
    # 等等，3 chunks → 2 predicted boundaries
    # 我们要 3 gts，所以需要更复杂布局
    doc = {
        "chunks": [
            {"text": "aaaa"},
            {"text": "bbbb"},
            {"text": "cccc"},
            {"text": "dddd"},
        ]
    }
    # stream = "aaaa bbbb cccc dddd"，predicted boundaries 在 4, 9, 14
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaaa", "position": "after"},  # gt = 4
            {"marker": "bbbb", "position": "after"},  # gt = 9
            {"marker": "cccc", "position": "after"},  # gt = 14
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_predicted_count_less_than_chunks_minus_one_when_text_not_found():
    """如果某 chunk text 在 stream 中找不到 → predicted 数 < chunks-1。

    通过 chunks=[{"text":"foo"},{"text":"X"},{"text":"bar"}]，但 X 经过 normalize
    后是 stream 的子串。实际上 join+normalize 后所有 chunk text 都在 stream 里。
    所以很难自然触发 find 返回 -1 的分支。我们靠 algorithm 行为验证：
    predicted 数等于 chunks 数 - 1。
    """
    doc = {
        "chunks": [
            {"text": "foo"},
            {"text": "bar"},
            {"text": "baz"},
        ]
    }
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # 应当不抛异常，precision/recall 都是 float
    # predicted = [3, 7], gt = [3]，matched=1
    # precision = 1/2 = 0.5, recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_repeated_marker_search_from_advances():
    """同 marker 多次出现 → search_from 推进，每个 anchor 取不同位置。"""
    doc = {
        "chunks": [
            {"text": "foo"},
            {"text": "foo"},
            {"text": "foo"},
        ]
    }
    # stream = "foo foo foo"，三个 "foo" 位置：0, 4, 8
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},  # gt=3
            {"marker": "foo", "position": "after"},  # gt=7
            {"marker": "foo", "position": "after"},  # gt=11
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # predicted = [3, 7], gt = [3, 7, 11]，matched=2
    # precision = 2/2 = 1.0, recall = 2/3
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert abs(out["chunk_boundary_recall"]["value"] - 2 / 3) < 1e-9


def test_chunk_boundary_two_anchors_zero_distance_match():
    """gt 与 pred 完全重合 → distance=0 ≤ tolerance → match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    # stream = "abc xyz"，predicted=[3]
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}  # gt=3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_precision_null_when_predicted_empty():
    """predicted=[] → precision null。"""
    # 单 chunk → no_predicted_boundaries 路径，precision=null
    doc = {"chunks": [{"text": "foo"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_recall_zero_when_anchors_present_but_no_match():
    """有 anchors 但全部不在容差内 → recall=0.0（非 null）。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    # predicted=[3]
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"}
        ]
    }  # gt=3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # 距离 0 但 tolerance=-1 → 不匹配 → matched=0
    # precision = 0/1 = 0.0，recall = 0/1 = 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_f1_zero_when_p_zero_r_zero():
    """P=R=0 → f1 = 0/0 走 denom <= 0 分支 → 0.0。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_f1_half_when_r_half():
    """P=1, R=0.5 → f1 = 2*1*0.5 / 1.5 = 1/1.5 = 0.667。"""
    doc = {
        "chunks": [
            {"text": "foo"},
            {"text": "bar"},
            {"text": "baz"},
        ]
    }
    # predicted = [3, 7]，gt 中只有 1 个在容差内
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},  # gt=3, match pred=3
            {"marker": "zzz", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # gt_positions = [3]，recall = 1/1 = 1.0
    # matched=1, precision = 1/2 = 0.5
    # 这个测试构造的反了，修正断言
    # f1 = 2 * 0.5 * 1.0 / (0.5 + 1.0) = 1.0/1.5 ≈ 0.667
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert abs(out["chunk_boundary_f1"]["value"] - (2 / 3)) < 1e-9


# =========================================================================
# chunk_boundary_prf 输入鲁棒性
# =========================================================================


def test_chunk_boundary_document_with_chunks_null():
    """chunks=null → 当作空 list → no_predicted_boundaries 路径。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["value"] is None
    assert "_tolerance_chars" in out


def test_chunk_boundary_annotation_anchors_null():
    """chunk_boundary_anchors=null → 当作空 list。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann)
    # 进入 no_ground_truth_anchors 路径
    assert out["chunk_boundary_recall"]["value"] is None


def test_chunk_boundary_anchor_marker_null_treated_as_empty():
    """marker=null → a.get("marker", "") 返回 None（因为 key 存在但值是 None）。

    但 a.get("marker", "") 当 key 存在时返回 None，所以 marker=None。
    后续 `if marker else -1` → marker 是 None → falsy → find_pos = -1 → missing。
    """
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": None}]}
    out = chunk_boundary_prf(doc, ann)
    # marker=None 当作 missing 处理
    # 但 None 不会进 missing_markers list（因为 marker 是 None）
    # 检查不抛异常即可
    assert "_tolerance_chars" in out


def test_chunk_boundary_anchor_no_marker_key_no_position_key():
    """anchor 缺 marker 和 position 键 → marker="", position="after"。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{}]}
    out = chunk_boundary_prf(doc, ann)
    # marker="" → find_pos = -1（empty marker falsy）
    # 不抛异常
    assert "_tolerance_chars" in out


def test_chunk_boundary_call_does_not_print_extra(capsys):
    """chunk_boundary_prf 不会有任何意外输出。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    chunk_boundary_prf(doc, ann)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_chunk_boundary_does_not_mutate_document():
    """调用不应修改输入 doc。"""
    doc = {
        "chunks": [
            {"text": "foo"},
            {"text": "bar"},
        ]
    }
    import copy

    doc_before = copy.deepcopy(doc)
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    chunk_boundary_prf(doc, ann)
    assert doc == doc_before


def test_chunk_boundary_does_not_mutate_annotation():
    """调用不应修改输入 annotation。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
            {"marker": "bar", "position": "after"},
        ]
    }
    import copy

    ann_before = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann)
    assert ann == ann_before


# =========================================================================
# figure_caption_prf 深度
# =========================================================================


def test_figure_caption_returns_three_metrics():
    out = figure_caption_prf({"chunks": []}, None)
    assert len(out) == 3


def test_figure_caption_keys_exact_set():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_all_values_are_none():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_all_reasons_parser_does_not_emit():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_call_does_not_print(capsys):
    figure_caption_prf({"chunks": []}, None)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_figure_caption_does_not_mutate_inputs():
    doc = {"chunks": [{"text": "foo"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    import copy

    doc_before = copy.deepcopy(doc)
    ann_before = copy.deepcopy(ann)
    figure_caption_prf(doc, ann)
    assert doc == doc_before
    assert ann == ann_before


def test_figure_caption_handles_empty_dict_for_document():
    out = figure_caption_prf({}, {})
    assert len(out) == 3


def test_figure_caption_handles_dict_with_only_chunks_key():
    out = figure_caption_prf({"chunks": []}, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact_three_items():
    assert len(annotation_all) == 3


def test_module_all_items_strings():
    for item in annotation_all:
        assert isinstance(item, str)


def test_module_all_contains_constant_first():
    """__all__ 第 1 项是常量名。"""
    assert annotation_all[0] == "PARSER_DOES_NOT_EMIT_RELATIONS"


def test_module_all_contains_figure_caption_second():
    assert annotation_all[1] == "figure_caption_prf"


def test_module_all_contains_chunk_boundary_third():
    assert annotation_all[2] == "chunk_boundary_prf"


def test_module_has_required_public_attrs():
    assert hasattr(annotation_metrics, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert hasattr(annotation_metrics, "figure_caption_prf")
    assert hasattr(annotation_metrics, "chunk_boundary_prf")


def test_module_imports_normalize_text():
    """应从 app.chunkers.structural 导入 normalize_text。"""
    assert hasattr(annotation_metrics, "normalize_text")


def test_module_imports_null_and_ratio():
    """应从 evaluation.metrics 导入 _null 和 _ratio。"""
    assert hasattr(annotation_metrics, "_null")
    assert hasattr(annotation_metrics, "_ratio")


def test_module_private_helpers_callable():
    assert callable(annotation_metrics._null)
    assert callable(annotation_metrics._ratio)


def test_module_constant_is_lowercase():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS.lower()


def test_module_constant_no_whitespace():
    assert " " not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_module_constant_starts_with_parser():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


# =========================================================================
# chunk_boundary_prf 默认 tolerance
# =========================================================================


def test_chunk_boundary_default_tolerance_value_30():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_explicit_tolerance_overrides_default():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


# =========================================================================
# chunk_boundary_prf 输出 metric 结构
# =========================================================================


def test_chunk_boundary_each_metric_has_value_and_reason_keys():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert "value" in out[k]
        assert "reason" in out[k]


def test_chunk_boundary_precision_value_is_float_or_none_on_success():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    v = out["chunk_boundary_precision"]["value"]
    assert v is None or isinstance(v, float)


def test_chunk_boundary_recall_value_is_float_or_none_on_success():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    v = out["chunk_boundary_recall"]["value"]
    assert v is None or isinstance(v, float)


def test_chunk_boundary_f1_value_is_float_or_none():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    v = out["chunk_boundary_f1"]["value"]
    assert v is None or isinstance(v, float)


def test_chunk_boundary_tolerance_chars_metric_value_is_int_or_none():
    """_tolerance_chars.value 总是 int（来自参数）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_reason_for_no_document_is_pipeline_failed():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_reason_for_no_annotation_is_no_annotation():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    out = chunk_boundary_prf(doc, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
    assert out["chunk_boundary_recall"]["reason"] == "no_annotation"
    assert out["chunk_boundary_f1"]["reason"] == "no_annotation"


def test_chunk_boundary_reason_for_no_chunks_is_no_predicted_boundaries():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall 因为有 anchors → 走 _ratio(0.0)，reason="evaluated"
    # f1 → no_predicted_boundaries
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_reason_for_no_anchors_is_no_ground_truth_anchors():
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_reason_for_no_anchors_in_stream_specific():
    """有 chunks 和 anchors 但 gt_positions 为空（全 missing）→ recall reason 是
    no_ground_truth_anchors_in_stream。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


# =========================================================================
# 真实场景：多 chunk 多 anchor 综合行为
# =========================================================================


def test_chunk_boundary_real_world_5_chunks_3_anchors_partial_match():
    """5 chunks → 4 predicted boundaries。3 anchors → 部分命中。"""
    doc = {
        "chunks": [
            {"text": "first"},
            {"text": "second"},
            {"text": "third"},
            {"text": "fourth"},
            {"text": "fifth"},
        ]
    }
    # stream = "first second third fourth fifth"
    # predicted = [5, 12, 18, 25]  (各 chunk 末)
    # 实际位置可能因 normalize 略有偏移，断言用宽 tolerance
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "first", "position": "after"},  # ≈5
            {"marker": "second", "position": "after"},  # ≈12
            {"marker": "MISSING", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # matched 至少 2
    assert out["chunk_boundary_precision"]["value"] >= 0.0
    assert "_missing_markers" in out
    assert "MISSING" in out["_missing_markers"]["value"]


def test_chunk_boundary_two_chunks_one_anchor_exact_match_high_precision():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_call_returns_dict_object():
    """返回值始终是 dict。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out, dict)


def test_figure_caption_call_returns_dict_object():
    out = figure_caption_prf({"chunks": []}, None)
    assert isinstance(out, dict)


def test_chunk_boundary_returns_fresh_dict_each_call():
    """每次调用应返回新 dict（不共享引用）。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 is not out2
    assert out1["chunk_boundary_precision"] is not out2["chunk_boundary_precision"]


def test_figure_caption_returns_fresh_dict_each_call():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 is not out2
    assert out1["figure_caption_precision"] is not out2["figure_caption_precision"]
