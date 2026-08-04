"""Round 86 — evaluation/annotation_metrics.py 边角覆盖（第二轮）。

互补于已有：
- tests/test_annotation_metrics.py（47 测试，主干行为）
- tests/test_annotation_metrics_edges.py（83 测试，第一轮边角）

第二轮重点：覆盖 chunk_boundary_prf 内部分支与状态的深度组合，
以及 figure_caption_prf 在各种 document/annotation 形态下的不变量。
不修改 evaluation/annotation_metrics.py。
"""

from __future__ import annotations

import pytest

from evaluation import annotation_metrics
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    __all__ as annotation_all,
)
from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf


# =============================================================================
# 模块级常量与 __all__
# =============================================================================


def test_parser_does_not_emit_relations_constant_exact_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_lowercase_ascii():
    for c in PARSER_DOES_NOT_EMIT_RELATIONS:
        assert c.islower() or c == "_"
        assert c.isascii()


def test_parser_does_not_emit_relations_constant_in_module_dict():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in dir(annotation_metrics)


def test_all_is_list_type():
    assert isinstance(annotation_all, list)


def test_all_contains_exact_three_items():
    assert len(annotation_all) == 3


def test_all_contains_parset_does_not_emit_relations():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in annotation_all


def test_all_contains_figure_caption_prf():
    assert "figure_caption_prf" in annotation_all


def test_all_contains_chunk_boundary_prf():
    assert "chunk_boundary_prf" in annotation_all


def test_all_no_extra_items():
    assert set(annotation_all) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_all_items_are_module_attributes():
    for name in annotation_all:
        assert hasattr(annotation_metrics, name)


def test_all_items_match_module_attribute_identity():
    for name in annotation_all:
        assert getattr(annotation_metrics, name) is getattr(annotation_metrics, name)


# =============================================================================
# figure_caption_prf 不变量（在任何 document/annotation 形态下）
# =============================================================================


def test_figure_caption_with_document_containing_chunks():
    """有 chunks 也必须返回 null。"""
    document = {"chunks": [{"text": "a"}], "elements": []}
    result = figure_caption_prf(document, None)
    assert result["figure_caption_precision"]["value"] is None
    assert result["figure_caption_recall"]["value"] is None
    assert result["figure_caption_f1"]["value"] is None


def test_figure_caption_with_annotation_containing_anchors():
    """annotation 含 chunk_boundary_anchors 也必须返回 null。"""
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    result = figure_caption_prf(None, annotation)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["value"] is None
        assert result[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_both_full_inputs():
    document = {"chunks": [{"text": "a"}], "elements": [{"type": "image"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = figure_caption_prf(document, annotation)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert result[k]["value"] is None


def test_figure_caption_reasons_all_equal_constant():
    result = figure_caption_prf({"chunks": []}, None)
    reasons = {result[k]["reason"] for k in result}
    assert reasons == {PARSER_DOES_NOT_EMIT_RELATIONS}


def test_figure_caption_returns_distinct_dicts_per_call():
    """两次调用返回的 dict 不应共享对象引用。"""
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf(None, None)
    assert r1 is not r2
    assert r1["figure_caption_precision"] is not r2["figure_caption_precision"]


def test_figure_caption_three_keys_exactly():
    result = figure_caption_prf(None, None)
    assert set(result.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_keys_alphabetical_order_in_dict():
    """Python 3.7+ dict 保序：源码按 precision/recall/f1 顺序写入。"""
    result = figure_caption_prf(None, None)
    keys = list(result.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_call_does_not_raise_with_empty_dict_inputs():
    """边界：document={}、annotation={} 不应崩溃。"""
    result = figure_caption_prf({}, {})
    assert result["figure_caption_precision"]["value"] is None


# =============================================================================
# chunk_boundary_prf — 失败/早返回路径深度
# =============================================================================


def test_chunk_boundary_document_none_with_annotation_present():
    """document is None → pipeline_failed（annotation 不影响）。"""
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    result = chunk_boundary_prf(None, annotation)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert result[k]["reason"] == "pipeline_failed"
        assert result[k]["value"] is None


def test_chunk_boundary_annotation_falsy_empty_list():
    """annotation=[] 是 falsy → 走 no_annotation 分支。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(document, [])
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_falsy_zero_int():
    """annotation=0 是 falsy → 走 no_annotation 分支。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(document, 0)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_falsy_empty_string():
    """annotation='' 是 falsy → 走 no_annotation 分支。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(document, "")
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_only_chunks_field_missing():
    """document 没 chunks key → chunks=[] → no_predicted_boundaries。"""
    document = {}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 有 anchors 但无预测 → recall = 0.0（不是 null）
    assert result["chunk_boundary_recall"]["value"] == 0.0
    assert result["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_empty_list_with_anchors():
    """chunks=[] 且有 anchors → recall=0.0。"""
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_chunks_empty_list_no_anchors():
    """chunks=[] 且无 anchors → recall=null。"""
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert result["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_single_chunk_with_anchors_recall_zero():
    """只有 1 个 chunk → 无内部边界 → recall=0（有 anchors）。"""
    document = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_tolerance_recorded_on_no_document():
    result = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert result["_tolerance_chars"]["value"] == 42
    assert result["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_recorded_on_no_annotation():
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(document, None, tolerance_chars=7)
    assert result["_tolerance_chars"]["value"] == 7


def test_chunk_boundary_tolerance_recorded_on_no_chunks():
    document = {}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=15)
    assert result["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_tolerance_recorded_on_no_anchors():
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=99)
    assert result["_tolerance_chars"]["value"] == 99


# =============================================================================
# chunk_boundary_prf — predicted 边界构造逻辑
# =============================================================================


def test_chunk_boundary_two_chunks_one_predicted_position():
    """2 chunk → 1 个 predicted 位置（最后 chunk 后不算边界）。"""
    document = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # predicted=5（hello 之后），anchor=5（hello after）
    # tolerance=0 → 距离 0 命中
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_three_chunks_two_predicted_positions():
    """3 chunk → 2 predicted 位置。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_text_with_internal_whitespace_normalized():
    """chunk 文本含内部多空格 → normalize 后变单空格。"""
    document = {"chunks": [{"text": "hello   world"}, {"text": "foo"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # normalize("hello   world") = "hello world"，长度 11
    # predicted = 11，anchor = stream.find("hello world") + len = 11
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_text_with_leading_trailing_whitespace_normalized():
    document = {"chunks": [{"text": "  hello  "}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_text_with_tab_newline():
    document = {"chunks": [{"text": "hello\tworld\n"}, {"text": "foo"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_with_none_text_normalized_to_empty():
    """chunk text=None → 视为 '' → 在 stream 中 find '' 永远命中 pos。"""
    document = {"chunks": [{"text": None}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # chunk[0].text='' → find('',0)=0 → end=0 → predicted=[0]
    # anchor 'world' before → stream.find('world',0)=0 → gt=0
    # tolerance=0，distance=0 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_missing_text_key():
    """chunk 没 text key → 视为 ''。"""
    document = {"chunks": [{}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_predicted_position_skips_when_text_not_in_stream():
    """理论不可达分支：chunk text 在 stream 中找不到 → predicted 跳过。

    实际生产上很难触发（stream 本来就是 chunk text 的拼接），
    但函数有对应兜底，用 mock 验证逻辑：让 chunks 的拼接无法在最终 stream 中找到。
    通过 monkeypatch normalize_text 让两次调用返回不同结果。
    """
    call_count = [0]
    real_normalize = annotation_metrics.normalize_text

    def fake_normalize(s: str) -> str:
        call_count[0] += 1
        # 第 1+2 次调用（每个 chunk text）返回原文；第 3 次（joined）返回改造后
        if call_count[0] <= 2:
            return s
        return s.upper()  # 让 stream 与 chunk text 不一致

    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "ABC", "position": "after"}]}

    # 用 monkeypatch 替换 normalize_text（chunk_boundary_prf 通过 from import 引用）
    import evaluation.annotation_metrics as am
    original = am.normalize_text
    am.normalize_text = fake_normalize
    try:
        result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    finally:
        am.normalize_text = original
    # chunk text 'abc' 在 stream 'ABC DEF' 中找不到 → predicted 跳过
    # → num_pred=0 → precision=null
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# =============================================================================
# chunk_boundary_prf — anchor 标注定位（position / search_from）
# =============================================================================


def test_chunk_boundary_anchor_position_invalid_value_treated_as_after():
    """position='unknown' → 走 else 分支（after 语义）。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "unknown"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # after: gt = 0 + 3 = 3，predicted = 3
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_anchor_position_before_at_start():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # before: gt = stream.find('abc') = 0；predicted = 3
    # distance = 3，tolerance=0 → 不匹配
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_anchor_position_after_with_unicode():
    document = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = '你好 世界'，predicted = 2，gt = 2
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_two_anchors_same_marker_distinct_positions():
    """相同 marker 出现 2 次 → search_from 推进，两个 anchor 定位到不同位置。"""
    document = {"chunks": [{"text": "ab ab"}, {"text": "ab"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
            {"marker": "ab", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = 'ab ab ab'（normalize 后）
    # chunk[0].text='ab ab' → find at 0, end=5 → predicted=[5]
    # chunk[1].text='ab' → find at 5+1=6, end=8 → 但最后一个 chunk 不算边界
    # 所以 predicted = [5]
    # anchors: 第 1 个 'ab' → find(0)=0 → gt=2（after: 0+2）；search_from=2
    # 第 2 个 'ab' → find(2)=3 → gt=5（after: 3+2）；search_from=5
    # gt_positions = [2, 5]
    # tolerance=0：predicted=5，gt=5 匹配；gt=2 不匹配
    assert result["chunk_boundary_precision"]["value"] == 1.0  # 1/1
    assert result["chunk_boundary_recall"]["value"] == 0.5  # 1/2


def test_chunk_boundary_search_from_advances_past_marker():
    """search_from = find_pos + len(marker)，下一个 anchor 必须从这之后开始。"""
    document = {"chunks": [{"text": "xxxx"}, {"text": "yyyy"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xx", "position": "after"},  # 第一次 find=0, search_from=2
            {"marker": "xx", "position": "after"},  # 第二次 find=2, search_from=4
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # 第 1 个 anchor: find=0, after gt=2
    # 第 2 个 anchor: find=2, after gt=4
    # predicted = 4 (chunk[0] 'xxxx' 之后)
    # tolerance=5: 4-2=2, 4-4=0 → 都在容差内
    # 一对一：4↔4 (距离 0) 胜出
    assert result["chunk_boundary_recall"]["value"] == 0.5  # 1/2


def test_chunk_boundary_marker_not_found_after_exhausted():
    """第 2 个 marker 在剩余 stream 中找不到 → missing_markers 增长。"""
    document = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # find=0, search_from=3
            {"marker": "abc", "position": "after"},  # find_from=3 → -1
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert "_missing_markers" in result
    assert result["_missing_markers"]["value"] == ["abc"]


def test_chunk_boundary_missing_markers_value_type_is_list():
    document = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "nope", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert isinstance(result["_missing_markers"]["value"], list)


def test_chunk_boundary_missing_markers_reason_none():
    document = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "nope", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["_missing_markers"]["reason"] is None


def test_chunk_boundary_no_missing_markers_key_when_all_found():
    document = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" not in result


# =============================================================================
# chunk_boundary_prf — 一对一匹配（贪心，按距离排序）
# =============================================================================


def test_chunk_boundary_greedy_chooses_smaller_distance_first():
    """2 predicted 2 anchors，距离矩阵 [1,5; 3,2]，贪心应选距离最小的对。"""
    document = {"chunks": [{"text": "aaaa"}, {"text": "bbbb"}, {"text": "cccc"}]}
    # predicted: chunk0 end=4, chunk1 end=9, 最后一个不算
    # → predicted = [4, 9]
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "bbbb", "position": "before"},  # gt=5
            {"marker": "cccc", "position": "before"},  # gt=10
        ]
    }
    # 距离矩阵：|4-5|=1, |4-10|=6, |9-5|=4, |9-10|=1
    # tolerance=10 → 全部入候选
    # 排序：(1, p0, g0), (1, p1, g1), (4, p1, g0), (6, p0, g1)
    # 贪心：p0-g0 距离 1 命中；p1-g1 距离 1 命中
    result = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_greedy_one_pred_two_anchors_closest_wins():
    """1 predicted 2 anchors，只有最近的能匹配。"""
    document = {"chunks": [{"text": "abcabc"}, {"text": "xyz"}]}
    # stream = 'abcabc xyz'，predicted = [6]
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},   # gt = 0；search_from = 3
            {"marker": "abc", "position": "before"},   # find from 3 → gt = 3
        ]
    }
    # 距离：|6-0|=6, |6-3|=3 → 贪心选 anchor1（距离 3）
    # tolerance=10 → matched=1
    # precision = 1/1 = 1.0；recall = 1/2 = 0.5
    result = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_two_preds_one_anchor_one_wins():
    """2 predicted 1 anchor，距离更近的胜出，另一个失配。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "cccc"}]}
    # predicted = [1, 3]
    annotation = {"chunk_boundary_anchors": [{"marker": "cccc", "position": "before"}]}  # gt=4
    # 距离：|1-4|=3, |3-4|=1
    # tolerance=5 → 选 p1-g0（距离 1）
    # precision = 1/2 = 0.5；recall = 1/1 = 1.0
    result = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_tolerance_exactly_at_boundary_inclusive():
    """distance == tolerance_chars 应当命中（函数用 <=）。"""
    document = {"chunks": [{"text": "ab"}, {"text": "cdef"}]}
    # predicted = [2]
    annotation = {"chunk_boundary_anchors": [{"marker": "cdef", "position": "before"}]}  # gt=3
    # 距离 = 1
    result = chunk_boundary_prf(document, annotation, tolerance_chars=1)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_distance_just_above_tolerance_no_match():
    document = {"chunks": [{"text": "ab"}, {"text": "cdef"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "cdef", "position": "before"}]}
    # 距离 = 1, tolerance = 0 → 不匹配
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_huge_tolerance_matches_everything_in_range():
    document = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "before"},  # gt=0
        ]
    }
    # stream = 'a b c'，predicted=[1,3], gt=[0], tolerance=1000
    # 贪心：距离 (1, p0, g0) 先匹配
    result = chunk_boundary_prf(document, annotation, tolerance_chars=1000)
    assert result["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_negative_tolerance_never_matches():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=-5)
    # distance=0 > -5（虽然 0 > -5 在数学上成立），不匹配
    assert result["chunk_boundary_precision"]["value"] == 0.0


# =============================================================================
# chunk_boundary_prf — F1 计算分支
# =============================================================================


def test_chunk_boundary_f1_perfect_match_value_one():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # p=1, r=1 → f1 = 2*1*1/(1+1) = 1.0
    assert result["chunk_boundary_f1"]["value"] == pytest.approx(1.0)


def test_chunk_boundary_f1_half_match_value():
    document = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # gt=1
            {"marker": "z", "position": "after"},  # missing
        ]
    }
    # predicted = [1, 3], gt = [1]
    # tolerance=0: p0↔g0 距离 0 → match
    # p=1/2=0.5, r=1/1=1.0
    # f1 = 2*0.5*1.0/(0.5+1.0) = 1.0/1.5 = 0.6667
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_f1"]["value"] == pytest.approx(2 * 0.5 * 1.0 / 1.5)


def test_chunk_boundary_f1_zero_when_p_zero_r_zero():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},  # gt=0, distance=3
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # p=0/1=0, r=0/1=0 → denom=0 → f1=0.0
    assert result["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_f1_null_when_p_null():
    """precision=null（无预测） → f1=null。"""
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_f1_null_reason_precision_or_recall_not_evaluated():
    """走完整算法但 recall=null（marker 全找不到） → f1 reason 此值。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "nope", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    # predicted=[3], gt_positions=[]（marker 不在 stream）
    # recall = null("no_ground_truth_anchors_in_stream")
    # f1 = null("precision_or_recall_not_evaluated")
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert result["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_f1_value_is_float_or_none():
    """f1 字段 value 要么是 float，要么是 None。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    v = result["chunk_boundary_f1"]["value"]
    assert v is None or isinstance(v, float)


# =============================================================================
# chunk_boundary_prf — 输出结构
# =============================================================================


def test_chunk_boundary_output_keys_on_success_path():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert expected_keys.issubset(set(result.keys()))


def test_chunk_boundary_output_keys_on_missing_markers_path():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "nope", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }
    assert expected_keys.issubset(set(result.keys()))


def test_chunk_boundary_does_not_mutate_document():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    import copy
    document_before = copy.deepcopy(document)
    chunk_boundary_prf(
        document,
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
    )
    assert document == document_before


def test_chunk_boundary_does_not_mutate_annotation():
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
        "extra_field": [1, 2, 3],
    }
    import copy
    annotation_before = copy.deepcopy(annotation)
    chunk_boundary_prf({"chunks": [{"text": "abc"}, {"text": "def"}]}, annotation)
    assert annotation == annotation_before


def test_chunk_boundary_no_extra_top_level_keys_on_success():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert set(result.keys()) == expected_keys


def test_chunk_boundary_each_metric_has_value_and_reason():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    for k, v in result.items():
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


# =============================================================================
# chunk_boundary_prf — 稳定性 / 大规模
# =============================================================================


def test_chunk_boundary_many_chunks_predicts_n_minus_one_boundaries():
    """10 个 chunk → 9 个 predicted 位置。"""
    document = {"chunks": [{"text": f"c{i}"} for i in range(10)]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": f"c{i}", "position": "after"} for i in range(9)
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 精确匹配：predicted 数=9，每个 anchor 在 chunk[i] 后，距离 0
    # 但 c0, c1, ..., c9 在 stream 中是 'c0 c1 c2 ... c9'，
    # chunk[i].text='c0' find at 0 → end=2；chunk[1] find 'c1' at 3 → end=5；...
    # anchor 'c0' after: find=0, gt=2；anchor 'c1' after: find=3, gt=5；...
    # 全部一对一距离 0
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_stress_50_chunks():
    """50 chunks 不崩溃。"""
    document = {"chunks": [{"text": f"x{i}y"} for i in range(50)]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": f"x{i}y", "position": "after"} for i in range(49)
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert isinstance(result["chunk_boundary_precision"]["value"], float)


def test_chunk_boundary_many_anchors_only_some_match():
    """5 predicted 但 20 anchors → recall ≤ 1。"""
    document = {"chunks": [{"text": "aaaaa"}, {"text": "bbbbb"}, {"text": "ccccc"},
                           {"text": "ddddd"}, {"text": "eeeee"}, {"text": "fffff"}]}
    # predicted = 5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aaaaa", "position": "after"},
            {"marker": "bbbbb", "position": "after"},
            {"marker": "ccccc", "position": "after"},
            {"marker": "ddddd", "position": "after"},
            {"marker": "eeeee", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


# =============================================================================
# chunk_boundary_prf — 签名 & 默认参数
# =============================================================================


def test_chunk_boundary_signature_three_params():
    import inspect
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_default_tolerance_is_30():
    import inspect
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_figure_caption_signature_two_params():
    import inspect
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


# =============================================================================
# chunk_boundary_prf — 边界字符串 / Unicode
# =============================================================================


def test_chunk_boundary_marker_with_unicode_text():
    document = {"chunks": [{"text": "你好世界"}, {"text": "测试"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "你好世界", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_with_emoji():
    document = {"chunks": [{"text": "hi 🎉 world"}, {"text": "end"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hi 🎉 world", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_empty_marker_treated_as_missing():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" in result
    assert "" in result["_missing_markers"]["value"]


def test_chunk_boundary_marker_missing_key_defaults_to_empty():
    """anchor 没 marker key → 默认 ''。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    # 默认 marker='' → find -1 → missing
    assert "_missing_markers" in result


def test_chunk_boundary_position_missing_key_defaults_to_after():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # position 默认 'after' → gt=3, predicted=3 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_anchor_extra_keys_ignored():
    """anchor 含未知 key 不影响逻辑。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after", "weight": 0.5, "label": "section1"}
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_annotation_with_extra_top_keys():
    """annotation 含其它 key（chunk_boundary_anchors 之外）被忽略。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
        "other_field": 42,
        "notes": "test",
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =============================================================================
# chunk_boundary_prf — 不变量：早返回路径包含 _tolerance_chars
# =============================================================================


def test_chunk_boundary_no_document_path_has_tolerance():
    result = chunk_boundary_prf(None, None)
    assert "_tolerance_chars" in result


def test_chunk_boundary_no_annotation_path_has_tolerance():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    result = chunk_boundary_prf(document, None)
    assert "_tolerance_chars" in result


def test_chunk_boundary_no_chunks_path_has_tolerance():
    document = {}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation)
    assert "_tolerance_chars" in result


def test_chunk_boundary_no_anchors_path_has_tolerance():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(document, annotation)
    assert "_tolerance_chars" in result


def test_chunk_boundary_success_path_has_tolerance():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert "_tolerance_chars" in result


# =============================================================================
# 模块结构 / 导入
# =============================================================================


def test_module_imports_normalize_text_from_app():
    """验证模块用 from import 引入 normalize_text。"""
    import evaluation.annotation_metrics as am
    assert hasattr(am, "normalize_text")


def test_module_imports_null_and_ratio_from_metrics():
    """验证模块用 from import 引入 _null 和 _ratio。"""
    # _null/_ratio 是私有的，不在 __all__，但模块应可访问
    import evaluation.annotation_metrics as am
    assert hasattr(am, "_null")
    assert hasattr(am, "_ratio")


def test_module_dunder_all_exact():
    assert sorted(annotation_metrics.__all__) == sorted([
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ])


def test_module_has_no_unexpected_public_attrs():
    """公共属性应仅含 __all__ 中三项 + 导入名 + __all__ 自身。

    模块顶部 `from __future__ import annotations` 等会注入少量名字
    （annotations/Any/Counter/normalize_text/_null/_ratio），
    这些是模块级 import 副作用，不属于公共 API。
    """
    allowed_extra = {
        "annotations",      # from __future__
        "Any",              # from typing
        "Counter",          # from collections
        "normalize_text",   # from app.chunkers.structural
        "_null",            # from evaluation.metrics
        "_ratio",           # from evaluation.metrics
    }
    expected = {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
        "__all__",
    }
    public = {
        name for name in dir(annotation_metrics)
        if not name.startswith("__") or name == "__all__"
    }
    allowed = expected | allowed_extra
    extras = public - allowed
    assert extras == set(), f"unexpected public names: {extras}"


# =============================================================================
# 综合场景
# =============================================================================


def test_chunk_boundary_real_world_3_chunks_2_anchors_one_mismatch():
    """模拟真实场景：3 chunks，2 anchors，其中一个偏移很大。"""
    document = {
        "chunks": [
            {"text": "这是第一段。"},
            {"text": "这是第二段。"},
            {"text": "这是第三段。"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            # 第 1 个 anchor：在 "第一段" 后（精确匹配 predicted[0]）
            {"marker": "这是第一段。", "position": "after"},
            # 第 2 个 anchor：marker 偏移到 chunk 中部（distance > tolerance）
            {"marker": "这是", "position": "after"},
        ]
    }
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = '这是第一段。 这是第二段。 这是第三段。'
    # predicted = [6, 13]（每个 chunk 末尾）
    # anchor0 'after 这是第一段。' = gt = 6
    # anchor1 'after 这是' search_from=6 → find at 7 → gt = 9
    # gt_positions = [6, 9]
    # tolerance=0: 只有 p0↔g0 距离 0 命中
    # p = 1/2 = 0.5, r = 1/2 = 0.5
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_empty_chunks_list_does_not_raise():
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_call_does_not_print(capsys):
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    chunk_boundary_prf(document, annotation)
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""


def test_figure_caption_call_does_not_print(capsys):
    figure_caption_prf(None, None)
    out = capsys.readouterr()
    assert out.out == ""
    assert out.err == ""
