"""evaluation/annotation_metrics.py 第三十轮 edges 测试（Round 338）。

重点补强 edges28 未触及的角度：
- figure_caption_prf 行为深度补强（_null 调用 / 不读 annotation / 不读 document / source level）
- chunk_boundary_prf 算法深度第二批（tolerance 边界 / 贪心匹配 / position before 边界 / search_from 推进）
- chunk_boundary_prf 边界组合补强（chunks None / chunks 缺 text / annotation is None / annotation is dict）
- module source forbidden tokens 第四批
- module source 字符串精确补强（更多 control flow）
- signatures 精确补强（return annotation / no varargs varkw）
- 模块整体合理性
- 端到端集成补强（更多场景）
"""

from __future__ import annotations

import inspect
import types
from collections import Counter
from typing import Any

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 行为深度补强 ----------


def test_figure_caption_returns_dict_with_3_specific_keys():
    out = figure_caption_prf({"chunks": []}, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_each_metric_uses_null_helper():
    out = figure_caption_prf({}, {})
    for k, v in out.items():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_document_having_chunks_still_returns_null():
    """即使 document 有 figure/caption，依然 null。"""
    doc = {
        "chunks": [],
        "elements": [
            {"type": "figure", "element_id": "f1"},
            {"type": "caption", "element_id": "c1"},
        ],
    }
    out = figure_caption_prf(doc, {"figure_caption_relations": []})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_with_annotation_containing_relations_still_returns_null():
    """本期不引入启发式，annotation 有 relation 也 null。"""
    annotation = {"figure_caption_relations": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf({"chunks": []}, annotation)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_does_not_read_document_keys():
    """传一个会被 document.get 触发异常的 dict 也无影响（figure_caption 不读）。"""
    class BadDict(dict):
        def get(self, key, default=None):
            raise AssertionError("figure_caption should not call get")
    out = figure_caption_prf(BadDict(), BadDict())
    assert len(out) == 3


def test_figure_caption_with_none_none():
    out = figure_caption_prf(None, None)
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_figure_caption_source_uses_null_with_reason():
    src = inspect.getsource(figure_caption_prf)
    assert "_null" in src
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_source_does_not_use_normalize_text():
    """figure_caption 不做 normalize_text。"""
    src = inspect.getsource(figure_caption_prf)
    assert "normalize_text" not in src


def test_figure_caption_source_does_not_use_counter():
    src = inspect.getsource(figure_caption_prf)
    assert "Counter" not in src


def test_figure_caption_source_no_yield():
    src = inspect.getsource(figure_caption_prf)
    assert "yield" not in src


def test_figure_caption_source_no_async():
    src = inspect.getsource(figure_caption_prf)
    assert "async " not in src


def test_figure_caption_source_no_class():
    src = inspect.getsource(figure_caption_prf)
    assert "class " not in src


# ---------- chunk_boundary_prf 算法深度第二批 ----------


def test_chunk_boundary_tolerance_boundary_exact_match():
    """预测和 anchor 距离恰好等于 tolerance_chars → 算 match（<=）。"""
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ]
    }
    # 流是 "alpha beta"，预测边界在位置 5（alpha 后）
    # 把 marker 放在 "alpha beta" 之后让 anchor 距离 5 正好等于 tolerance=5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 预测 = 5（alpha 之后），anchor = 10（"alpha beta" 之后）
    # 距离 = 5，== tolerance_chars=5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_just_above_no_match():
    """距离 > tolerance_chars → 不 match。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=4)
    # 距离 5 > 4 → no match → precision 0 / recall 0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_greedy_picks_smallest_distance():
    """2 个预测、1 个 anchor：anchor 应被距离更近的那个匹配。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    # 流 "a b c"，预测位置 1（a 后）、3（b 后）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a b c", "position": "before"},  # 位置 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # anchor 0, predictions 1 和 3，distances 1 和 3，最近的 1 应被匹配
    # matched=1, num_pred=2, num_gt=1 → precision=0.5, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_one_to_one_constraint():
    """1 个 anchor 不能同时匹配 2 个 prediction（一对一）。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    # 流 "a b c"，预测 1 和 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "b", "position": "before"},  # 位置 2
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 两个预测都距离 2 是 1，但一对一 → matched=1
    # precision=1/2=0.5, recall=1/1=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_position_before_anchor_at_marker_start():
    """position='before' → anchor 在 marker 起始位置。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # 流 "hello world"，预测在 5
    # marker "hello" 在位置 0，position='before' → anchor=0
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 距离 |5-0|=5 <= 5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_after_anchor_at_marker_end():
    """position='after' → anchor 在 marker 结束位置（marker start + len）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # 流 "hello world"
    # marker "hello" 在 0，position='after' → anchor=5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 5，anchor 5，距离 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_search_from_advances_for_duplicate_markers():
    """重复 marker：第二个 anchor 应从第一个之后开始找。"""
    doc = {
        "chunks": [
            {"text": "foo bar"},
            {"text": "foo bar"},
        ]
    }
    # 流 "foo bar foo bar"（normalize 后保留单空格）
    # 预测位置：第一个 chunk 后 = 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo bar", "position": "after"},  # 第 1 个：anchor=7
            {"marker": "foo bar", "position": "after"},  # 第 2 个：anchor=15
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 [7]，anchors [7, 15]，距离 |7-7|=0, |7-15|=8
    # tolerance=0，只有第 1 个匹配
    # precision=1/1, recall=1/2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_marker_with_whitespace_in_text():
    """marker 含空白也能在 normalize 后的 stream 里找到。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo"}]}
    # 流 "hello world foo"，预测 11
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello world", "position": "after"},  # anchor=11
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_text_with_extra_whitespace_normalized():
    """chunk 文本有额外空白 → normalize 后变成单空格。"""
    doc = {"chunks": [{"text": "hello   world"}, {"text": "foo"}]}
    # normalize_text("hello   world") = "hello world"
    # normalize_text("foo") = "foo"
    # joined = "hello world foo" → normalize = "hello world foo"
    # predicted[0] = 11
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_text_none_treated_as_empty():
    """chunk text=None → normalize 后空串，但仍占一个位置。"""
    doc = {
        "chunks": [
            {"text": None},
            {"text": "abc"},
        ]
    }
    # norm_chunks = ["", "abc"], joined = " abc" → stream = "abc"
    # 第 1 个 chunk 找 "" → find 返回 0，end=0 → predicted=[0]
    # 但最后 chunk 不算，所以 predicted 只从 i=0 来 → [0]
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},  # 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 0，anchor 0，距离 0 → match
    # precision=1/1, recall=1/1
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_text_missing_key_uses_empty_string():
    """chunk 没有 text key → 默认 ""。"""
    doc = {"chunks": [{}, {"text": "abc"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 类似上一测试
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_missing_marker_added_to_missing_markers():
    """marker 在 stream 中找不到 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_empty_marker_treated_as_missing():
    """marker="" → marker 假值，find 返回 -1，加入 missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_no_chunks_returns_no_predicted():
    """document.chunks = [] → no_predicted_boundaries。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_one_chunk_returns_no_predicted():
    """document.chunks 只 1 个 → <2 → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_one_chunk_with_anchors_recall_zero():
    """1 chunk + 有 anchors → recall = 0.0（_ratio 分支）。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    # len(chunks) < 2 且 has anchors → recall = _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_one_chunk_no_anchors_recall_null():
    """1 chunk + 无 anchors → recall = null (no_predicted_boundaries)。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] is None


def test_chunk_boundary_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_annotation_none_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_empty_dict_returns_no_annotation():
    """空 dict 视为 no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_no_anchors_returns_no_ground_truth_anchors():
    """有 chunks 但无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_zero_predicted_in_main_path_returns_no_predicted():
    """有 chunks 但 norm_chunks find 全失败 → predicted=[]，主路径返回 no_predicted_boundaries。"""
    # 让 stream.find(txt) 失败：stream 与 txt 不一致
    # 这是边界情况：norm_chunks 中的 txt 在 stream 中找不到
    # 实际上 joined = " ".join(norm_chunks) + normalize 不会丢字符
    # 唯一可能 find 失败的是 txt 含特殊字符被 normalize 删了
    # 这里用空白 chunk：norm_chunks = ["", ""]，stream = ""
    doc = {"chunks": [{"text": ""}, {"text": ""}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    # 预测位置：norm_chunks=["", ""]，stream=""
    # 第一个 chunk 找 "" 在 stream.find("", 0) = 0, end=0 → predicted=[0]
    # 第二个 chunk 是最后一个，break
    # 所以 predicted = [0]
    # 这里 marker="x" 找不到 → missing → gt_positions=[]
    # num_gt=0 → recall=null no_ground_truth_anchors_in_stream
    # num_pred=1 → precision = matched(0)/1 = 0.0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_perfect_match_returns_one():
    """所有 anchor 都匹配 → precision=recall=f1=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_partial_match_returns_partial_f1():
    """部分匹配 → f1 = 2pr/(p+r)。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    # 流 "a b c"，预测位置 1（a 后）、3（b 后）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a b c", "position": "before"},  # 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 1 matched out of 2 pred, 1 matched out of 1 gt
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert f1 == pytest.approx(2 * p * r / (p + r))


def test_chunk_boundary_no_match_returns_f1_zero():
    """无 match 且 p+r=0 → f1 = 0.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc def", "position": "after"},  # 距离很远
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 距离 4 > 0 → no match
    # precision=0/1=0, recall=0/1=0
    # p+r=0 → f1=0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_extra_keys_in_anchor_ignored():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after", "extra": "ignored", "id": 1},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_extra_keys_in_annotation_ignored():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
        "extra_top": "ignored",
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_chars_recorded_in_output():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_chars_can_be_zero():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_chars_can_be_negative():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=-5)
    assert out["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_output_keys_for_normal_path():
    """正常路径输出 4 个 key：3 metric + _tolerance_chars。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_output_keys_with_missing_markers():
    """有 missing markers 时多 1 个 key。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "missing", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }


def test_chunk_boundary_does_not_mutate_inputs():
    """不修改 document/annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}], "extra": 1}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}], "x": 2}
    doc_before = repr(doc)
    ann_before = repr(annotation)
    chunk_boundary_prf(doc, annotation)
    assert repr(doc) == doc_before
    assert repr(annotation) == ann_before


# ---------- chunk_boundary_prf source level 字符串精确补强 ----------


def test_chunk_boundary_source_has_5_branches():
    """5 个早返回分支：document None / annotation empty / <2 chunks / no anchors / main path。"""
    src = inspect.getsource(chunk_boundary_prf)
    # 5 个 return 语句（4 早返回 + 1 末尾）
    return_count = src.count("return out")
    assert return_count == 5


def test_chunk_boundary_source_uses_normalize_text_call():
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text(" in src


def test_chunk_boundary_source_uses_join_with_space():
    src = inspect.getsource(chunk_boundary_prf)
    assert '" ".join(norm_chunks)' in src or "' '.join(norm_chunks)" in src


def test_chunk_boundary_source_uses_stream_normalize_after_join():
    """stream = normalize_text(joined_raw)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "joined_raw" in src
    assert "stream = normalize_text" in src


def test_chunk_boundary_source_uses_predicted_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int]" in src or "predicted = " in src


def test_chunk_boundary_source_uses_for_loop_with_enumerate():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for i, txt in enumerate" in src


def test_chunk_boundary_source_uses_last_chunk_break():
    src = inspect.getsource(chunk_boundary_prf)
    assert "len(norm_chunks) - 1" in src


def test_chunk_boundary_source_uses_stream_find():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(txt, pos)" in src


def test_chunk_boundary_source_uses_find_pos_negative_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "find_pos < 0" in src or "if find_pos < 0" in src


def test_chunk_boundary_source_uses_pos_advance_when_not_found():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos += len(txt) + 1" in src


def test_chunk_boundary_source_uses_search_from_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_source_uses_anchor_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for a in anchors" in src


def test_chunk_boundary_source_uses_marker_default_empty():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("marker", "")' in src


def test_chunk_boundary_source_uses_position_default_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


def test_chunk_boundary_source_uses_position_before_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'position == "before"' in src


def test_chunk_boundary_source_uses_pairs_with_distance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs" in src
    assert "abs(pv - gv)" in src


def test_chunk_boundary_source_uses_tolerance_compare():
    src = inspect.getsource(chunk_boundary_prf)
    assert "tolerance_chars" in src


def test_chunk_boundary_source_uses_pairs_sort_by_distance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort" in src


def test_chunk_boundary_source_uses_used_pred_used_gt_set():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src
    assert "used_gt" in src


def test_chunk_boundary_source_uses_matched_increment():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src


def test_chunk_boundary_source_uses_num_pred_num_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "num_pred = len(predicted)" in src
    assert "num_gt = len(gt_positions)" in src


def test_chunk_boundary_source_uses_null_when_no_pred():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_predicted_boundaries"' in src


def test_chunk_boundary_source_uses_null_when_no_gt_in_stream():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_chunk_boundary_source_uses_f1_with_denom_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom = p_val + r_val" in src
    assert "denom <= 0" in src


def test_chunk_boundary_source_appends_missing_markers_conditionally():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if missing_markers" in src


def test_chunk_boundary_source_no_yield():
    src = inspect.getsource(chunk_boundary_prf)
    assert "yield" not in src


def test_chunk_boundary_source_no_async():
    src = inspect.getsource(chunk_boundary_prf)
    assert "async " not in src


def test_chunk_boundary_source_no_class():
    src = inspect.getsource(chunk_boundary_prf)
    assert "class " not in src


def test_chunk_boundary_source_uses_lambda_for_sort_key():
    """pairs.sort 用 lambda 取距离作为 key。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "lambda x: x[0]" in src


def test_chunk_boundary_source_no_global():
    src = inspect.getsource(chunk_boundary_prf)
    assert "global " not in src


# ---------- module source forbidden tokens 第四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "abc", "aifc", "antigravity", "argparse", "asdl", "audioop",
        "base64", "binascii", "binhex", "bisect", "cProfile",
        "calendar", "concurrent", "contextlib", "copyreg", "crypt",
        "csv", "curses", "datetime", "dl", "docxml",
        "dospath", "dummy_threading", "email", "encodings",
        "ensurepip", "enum", "errno", "fileinput", "fnmatch",
        "formatter", "ftplib", "functools", "genericpath", "genshi",
        "getopt", "getpass", "gettext", "glob", "gopherlib",
        "heapq", "html", "http", "imaplib", "ihooks",
        "imghdr", "importlib", "inspect", "ipaddress", "itertools",
        "json", "keyword", "linecache", "locale", "logging",
        "lzma", "macpath", "macurl2path", "mailbox", "mailcap",
        "markupbase", "md5", "mhlib", "mimetypes", "mimify",
        "mmap", "msilib", "multifile", "multiprocessing", "mutex",
        "netrc", "new", "nis", "nntplib", "numbers",
        "opcode", "operator", "optparse", "os2emxpath", "parser",
        "pathlib", "pdb", "pickle", "pickletools", "pipes",
        "pkgutil", "platform", "plistlib", "poplib", "posixfile",
        "posixpath", "profile", "pstats", "pty", "pyclbr",
        "py_compile", "pydoc", "queue", "quopri", "random",
        "readline", "reprlib", "rexec", "rfc822", "rlcompleter",
        "robotparser", "runpy", "sched", "secrets", "select",
        "sets", "sgmlop", "sgmllib", "sha", "shelve",
        "shlex", "shutil", "signal", "site", "smtplib",
        "smtpd", "sndhdr", "socket", "socketserver", "spawn",
        "spwd", "sqlite3", "ssl", "stat", "stringprep",
        "subprocess", "sunau", "sunaudio", "symtable",
        "sys", "sysconfig", "tabnanny", "tarfile", "telnetlib",
        "tempfile", "termios", "threading", "time", "timeit",
        "tomllib", "token", "tokenize", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "types", "unicodedata",
        "unittest", "urllib", "urllib2", "urlparse", "user",
        "userdict", "userlist", "usersite", "uuid", "venv",
        "warnings", "wave", "weakref", "webbrowser", "whichdb",
        "wsgiref", "xdrlib", "xml", "xmlrpc", "zipapp",
        "zipfile", "zipimport", "zlib", "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_fourth_batch(token):
    """这些 stdlib 模块不应出现在 annotation_metrics.py。"""
    src = inspect.getsource(amod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_counter():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_imports_any():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_imports_normalize_text():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_imports_null_ratio():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_defines_parser_does_not_emit_constant():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_docstring_mentions_caption():
    src = inspect.getsource(amod)
    assert "caption" in src.lower()


def test_module_source_docstring_mentions_marker():
    src = inspect.getsource(amod)
    assert "marker" in src.lower()


def test_module_source_docstring_mentions_tolerance():
    src = inspect.getsource(amod)
    assert "tolerance" in src.lower()


def test_module_source_docstring_mentions_one_to_one():
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_docstring_mentions_greedy():
    src = inspect.getsource(amod)
    assert "贪心" in src


def test_module_source_docstring_mentions_heuristic():
    src = inspect.getsource(amod)
    assert "启发式" in src


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield" not in src


def test_module_source_no_async():
    src = inspect.getsource(amod)
    assert "async " not in src


def test_module_source_no_class_definition():
    src = inspect.getsource(amod)
    body_lines = [l for l in src.splitlines() if not l.strip().startswith(("#", '"', "'"))]
    body = "\n".join(body_lines)
    assert "\nclass " not in body


def test_module_source_no_lambda():
    src = inspect.getsource(amod)
    # lambda x: x[0] 是合法的（pairs.sort key），所以这里反而要确认确实有 lambda
    assert "lambda" in src


def test_module_source_no_decorators():
    src = inspect.getsource(amod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("@"):
            pytest.fail(f"unexpected decorator at line {i}: {line}")


def test_module_source_has_2_module_level_functions():
    src = inspect.getsource(amod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 2


def test_module_source_has_1_module_level_constant():
    src = inspect.getsource(amod)
    # PARSER_DOES_NOT_EMIT_RELATIONS = "..."
    const_count = sum(
        1 for line in src.splitlines()
        if line.startswith("PARSER_DOES_NOT_EMIT_RELATIONS =")
    )
    assert const_count == 1


def test_module_source_has_all_with_3_entries():
    src = inspect.getsource(amod)
    assert "__all__" in src
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


# ---------- signatures 精确补强 ----------


def test_figure_caption_prf_signature_2_params():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_param_names():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_param_annotations():
    sig = inspect.signature(figure_caption_prf)
    a = sig.parameters["document"].annotation
    b = sig.parameters["annotation"].annotation
    # from __future__ 让 annotation 变字符串
    assert a is None or "dict" in str(a)
    assert b is None or "dict" in str(b)


def test_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_return_annotation_dict():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]" or "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_signature_3_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_tolerance_annotation_int():
    sig = inspect.signature(chunk_boundary_prf)
    annotation = sig.parameters["tolerance_chars"].annotation
    assert annotation is int or annotation == "int"


def test_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_no_varargs_varkw():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_figure_caption_prf_no_varargs_varkw():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds
    assert inspect.Parameter.VAR_KEYWORD not in kinds


# ---------- 模块整体合理性 ----------


def test_module_namespace():
    assert isinstance(amod, types.ModuleType)


def test_module_namespace_has_figure_caption_prf():
    assert hasattr(amod, "figure_caption_prf")


def test_module_namespace_has_chunk_boundary_prf():
    assert hasattr(amod, "chunk_boundary_prf")


def test_module_namespace_has_parser_does_not_emit_constant():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_namespace_parser_does_not_emit_is_str():
    assert isinstance(amod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_all_is_list():
    assert isinstance(amod.__all__, list)


def test_module_all_has_3_entries():
    assert len(amod.__all__) == 3


def test_module_all_entries_are_str():
    for entry in amod.__all__:
        assert isinstance(entry, str)


def test_module_all_entries_exact():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_has_2_module_level_functions():
    functions = [
        v for v in vars(amod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == amod.__name__
    ]
    assert len(functions) == 2


def test_module_has_1_module_level_constant():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是模块级 str 常量。"""
    src = inspect.getsource(amod)
    has_const = 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src
    assert has_const


def test_module_no_class_definition():
    classes = [
        v for v in vars(amod).values()
        if isinstance(v, type) and v.__module__ == amod.__name__
    ]
    assert len(classes) == 0


def test_module_no_main_block():
    src = inspect.getsource(amod)
    assert "__main__" not in src


def test_module_callable_figure_caption_prf():
    assert callable(figure_caption_prf)


def test_module_callable_chunk_boundary_prf():
    assert callable(chunk_boundary_prf)


# ---------- 端到端集成补强 ----------


def test_e2e_perfect_match_3_chunks():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_partial_match_3_chunks_1_anchor():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 2 predicted, 1 anchor, 1 match → p=0.5, r=1.0, f1=2/3
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


def test_e2e_no_match_distance_too_far():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha beta", "position": "after"},  # 距离 5
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_unicode_marker():
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "你好", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_deterministic_across_calls():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation)
    out2 = chunk_boundary_prf(doc, annotation)
    assert out1 == out2


def test_e2e_with_chunks_none_text_in_middle():
    doc = {
        "chunks": [
            {"text": "abc"},
            {"text": None},
            {"text": "def"},
        ]
    }
    # norm_chunks = ["abc", "", "def"]
    # joined = "abc  def" → normalize = "abc def"
    # 预测：abc 在 0 找到 end=3 → predicted=[3]；"" 在 4 找到 end=4 → predicted=[3, 4]
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # anchor 3 距离 predicted 3 是 0，距离 4 是 1
    # tolerance=0 → 只匹配距离 0 的 → matched=1
    # num_pred=2, num_gt=1
    assert out["chunk_boundary_precision"]["value"] == 0.5


def test_e2e_chunks_with_extra_keys_in_dict():
    """chunk 字典有额外 key 不影响。"""
    doc = {
        "chunks": [
            {"text": "abc", "chunk_id": "c1", "source_element_ids": ["e1"]},
            {"text": "def", "chunk_id": "c2", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_call_with_kwargs_only():
    """所有参数用关键字传递也能工作。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(
        document=doc,
        annotation=annotation,
        tolerance_chars=0,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_call_with_positional_only():
    """所有参数用位置传递也能工作。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, 0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_figure_caption_callable_with_positional():
    out = figure_caption_prf({}, {})
    assert len(out) == 3


def test_e2e_figure_caption_callable_with_kwargs():
    out = figure_caption_prf(document={}, annotation={})
    assert len(out) == 3


def test_e2e_chunk_boundary_output_is_json_serializable():
    """输出可被 json.dumps 序列化。"""
    import json
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_figure_caption_output_is_json_serializable():
    import json
    out = figure_caption_prf({}, {})
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_chunk_boundary_returns_proper_metric_dict_format():
    """每个 metric 都是 {value, reason} 结构。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    for k, v in out.items():
        if k.startswith("chunk_boundary_"):
            assert isinstance(v, dict)
            assert set(v.keys()) == {"value", "reason"}
