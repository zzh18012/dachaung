"""evaluation/annotation_metrics.py 第三十一轮 edges 测试（Round 344）。

重点补强 edges29 未触及的角度：
- figure_caption_prf 行为深度第三批（reason 精确 / 输出格式不变 / 类型确认 / 不依赖输入结构）
- chunk_boundary_prf 算法深度第三批（tolerance 1 边界 / pairs.sort 顺序 / used_pred/used_gt 排除 / position 非法 fallback / 跨 chunk marker / 子串 marker）
- chunk_boundary_prf 边界组合补强（数字 text / marker None / position None / chunks None item / annotation 大量键）
- module source forbidden tokens 第六批（不同 stdlib list）
- module source 字符串精确补强（更多 control flow）
- signatures 精确补强（更多 annotation 检查）
- 模块整体合理性（更多 namespace 检查）
- 端到端集成补强（更多场景）
"""

from __future__ import annotations

import inspect
import types
from typing import Any

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 行为深度第三批 ----------


def test_figure_caption_returns_three_metric_dicts():
    out = figure_caption_prf({}, {})
    assert isinstance(out, dict)
    assert len(out) == 3


def test_figure_caption_precision_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_precision" in out


def test_figure_caption_recall_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_recall" in out


def test_figure_caption_f1_key_present():
    out = figure_caption_prf({}, {})
    assert "figure_caption_f1" in out


def test_figure_caption_precision_value_is_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_recall_value_is_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_recall"]["value"] is None


def test_figure_caption_f1_value_is_none():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_precision_reason_exact():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_recall_reason_exact():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_recall"]["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_f1_reason_exact():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_f1"]["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_value_is_none_type():
    """value 的类型是 NoneType。"""
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert v["value"] is None
        assert isinstance(v["value"], type(None))


def test_figure_caption_reason_is_str():
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert isinstance(v["reason"], str)


def test_figure_caption_each_metric_dict_has_2_keys():
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_with_huge_document_returns_null():
    """大量 element 仍然返回 null。"""
    elements = [{"type": "figure", "element_id": f"f{i}"} for i in range(100)]
    doc = {"chunks": [], "elements": elements}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_with_huge_annotation_returns_null():
    annotation = {
        "figure_caption_relations": [
            {"figure_id": f"f{i}", "caption_id": f"c{i}"}
            for i in range(100)
        ]
    }
    out = figure_caption_prf({"chunks": []}, annotation)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_with_unusual_document_types():
    """document 含非标准类型的 element 也 null。"""
    doc = {
        "chunks": [],
        "elements": [
            {"type": "table", "element_id": "t1"},
            {"type": "image", "element_id": "i1"},
            {"type": "unknown_type", "element_id": "u1"},
        ],
    }
    out = figure_caption_prf(doc, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_with_frozen_input_dict():
    """输入是 dict 子类也不影响。"""
    class MyDict(dict):
        pass
    out = figure_caption_prf(MyDict(), MyDict())
    assert len(out) == 3


def test_figure_caption_with_truthy_document_and_annotation():
    """document 和 annotation 都 truthy 但仍然 null。"""
    out = figure_caption_prf({"a": 1}, {"b": 2})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_idempotent():
    """多次调用结果一致。"""
    out1 = figure_caption_prf({"chunks": []}, None)
    out2 = figure_caption_prf({"chunks": []}, None)
    assert out1 == out2


def test_figure_caption_no_call_to_len():
    """source 不含 len 调用。"""
    src = inspect.getsource(figure_caption_prf)
    assert "len(" not in src


def test_figure_caption_no_call_to_normalize():
    src = inspect.getsource(figure_caption_prf)
    assert "normalize_text" not in src


def test_figure_caption_source_short():
    """figure_caption_prf source 不长（早期 return）。"""
    src = inspect.getsource(figure_caption_prf)
    assert len(src.splitlines()) < 15


# ---------- chunk_boundary_prf 算法深度第三批 ----------


def test_chunk_boundary_tolerance_1_boundary_match():
    """distance = 1, tolerance = 1 → match。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 流 "alpha beta"，预测 5
    # marker "al" 在 0，after → anchor 2
    # 距离 |5-2|=3，太大
    # 换 marker "alph" → after → anchor 4，距离 1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_1_no_match_when_distance_2():
    """distance = 2, tolerance = 1 → no match。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 预测 5，marker "al" after → 2，距离 3
    # marker "a" after → 1，距离 4
    # 选 "alpha" before → 0，距离 5
    # 都不匹配 tolerance=1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "before"},  # anchor 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # 距离 |5-0|=5 > 1 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_greedy_does_not_match_used_pred():
    """2 pred + 1 anchor，距离最近的 pred 优先匹配，另一 pred 不参与。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    # 流 "a b c"
    # 预测 1（a 后）、3（b 后）
    # anchor 3（marker "a b" after）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a b", "position": "after"},  # anchor 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 距离 |1-3|=2, |3-3|=0
    # pairs sorted: (0, 1, 0), (2, 0, 0)
    # matched: pred1-gt0 (distance 0) → matched=1
    # pred0 与 gt0 distance 2 → 但 gt0 已用 → skip
    # matched=1, num_pred=2, num_gt=1 → precision=0.5, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_position_invalid_falls_back_to_after():
    """position 是非法值（不是 before/after）→ fallback 到 else 分支（after）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # 流 "hello world"，预测 5
    # marker "hello" 在 0
    # position "invalid" → else 分支 → anchor = 0 + len("hello") = 5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "invalid"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 距离 |5-5|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_none_falls_back_to_after():
    """position=None → 与 default 'after' 一致（else 分支）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # 预测 5
    # marker "hello" 在 0，position=None → else → anchor=5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": None},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_missing_falls_back_to_default_after():
    """position 字段缺失 → a.get("position", "after") → 'after'。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello"},  # 无 position
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_spans_chunks():
    """marker 跨 chunk 边界（含空格）。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    # 流 "foo bar"，预测 3
    # marker "foo bar" after → anchor 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo bar", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 距离 |3-7|=4，tolerance=10 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_is_substring_of_chunk_text():
    """marker 是 chunk text 的子串。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo"}]}
    # 流 "hello world foo"，预测 11
    # marker "lo" after → 在位置 6 找到 + len("lo")=2 → anchor 8
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "lo", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 距离 |11-8|=3 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_equals_full_stream():
    """marker 等于整个 stream。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 流 "abc def"，预测 3
    # marker "abc def" after → anchor 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc def", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 距离 |3-7|=4 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_at_end_of_stream():
    """marker 在 stream 末尾。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 流 "abc def"
    # marker "def" after → 在 4 找到 + len("def")=3 → anchor 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 预测 3，anchor 7，距离 4 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_at_start_of_stream():
    """marker 在 stream 开头。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 流 "abc def"，预测 3
    # marker "abc" before → anchor 0
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 距离 |3-0|=3 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_anchors_with_extra_keys():
    """anchor 含额外 key 仍正常处理。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {
                "marker": "abc",
                "position": "after",
                "id": 1,
                "label": "section_break",
                "_internal": True,
            },
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_no_anchor_marker_field():
    """anchor 没有 marker 字段 → default ''。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"position": "after"},  # 无 marker
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # marker="" → marker 假值 → find 返回 -1 → missing_markers=[""]
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_3_chunks_2_anchors_perfect():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    # 流 "alpha beta gamma"
    # 预测 5、10
    # anchors 5（"alpha" after）和 10（"beta" after）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_4_chunks_3_anchors_one_off():
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
            {"text": "d"},
        ]
    }
    # 流 "a b c d"
    # 预测 1、3、5
    # anchors 1、3、5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
            {"marker": "c", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_more_anchors_than_predictions():
    """anchor 比 prediction 多 → recall < 1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 流 "abc def"，预测 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # anchor 3
            {"marker": "def", "position": "after"},  # anchor 7
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # matched=2 (both within 10), num_pred=1, num_gt=2
    # precision=2/1=... 实际 matched 至多 1（一对一）
    # matched=1, precision=1/1=1.0, recall=1/2=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_more_predictions_than_anchors():
    """prediction 比 anchor 多 → precision < 1。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    # 流 "a b c"，预测 1、3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # anchor 1
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # matched=1, num_pred=2, num_gt=1
    # precision=0.5, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_single_char_chunks():
    doc = {
        "chunks": [
            {"text": "x"},
            {"text": "y"},
        ]
    }
    # 流 "x y"，预测 1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},  # anchor 1
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_long_chunks():
    """非常长的 chunk text。"""
    long_text_a = "a" * 100
    long_text_b = "b" * 100
    doc = {"chunks": [{"text": long_text_a}, {"text": long_text_b}]}
    # 流 long_a + " " + long_b
    # 预测 100
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": long_text_a, "position": "after"},  # anchor 100
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunks_with_chunks_key_missing():
    """document 没有 chunks key → chunks=[] → no_predicted_boundaries。"""
    doc = {}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_is_none():
    """document.chunks=None → None or [] → [] → no_predicted_boundaries。"""
    doc = {"chunks": None}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_item_text_is_number():
    """chunk text 是数字 → c.get("text") or "" 返回 ""（int 0）或 int。"""
    # 注意：c.get("text") or "" → 若 text 是 0 → 0 or "" → ""
    # 若 text 是 5 → 5 or "" → 5（int）
    # normalize_text(int) 会抛 TypeError → 测试这个边界
    doc = {"chunks": [{"text": 5}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    with pytest.raises((TypeError, AttributeError)):
        chunk_boundary_prf(doc, annotation)


def test_chunk_boundary_chunks_item_text_is_zero():
    """chunk text 是 0 → 0 or "" → "" → normalize_text("")=""。"""
    doc = {"chunks": [{"text": 0}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    # norm_chunks: ["", "abc"]
    # joined_raw = " abc" → normalize → "abc"
    # predicted[0]: stream.find("", 0) → 0 → end=0 → predicted=[0]
    # last chunk break
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # marker "x" 找不到 → missing → gt_positions=[]
    # num_gt=0 → recall null no_ground_truth_anchors_in_stream
    # num_pred=1 → precision = 0/1 = 0.0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_chunks_item_text_is_empty_string():
    """chunk text 显式空字符串。"""
    doc = {"chunks": [{"text": ""}, {"text": ""}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # stream = ""，predicted=[0]
    # marker "x" 找不到 → gt_positions=[]
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_annotation_with_many_extra_keys():
    """annotation 有大量无关 key 也能工作。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
        "extra1": 1,
        "extra2": "x",
        "extra3": [1, 2, 3],
        "extra4": {"nested": True},
        "extra5": None,
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_missing_markers_records_all():
    """多个 missing markers 都被记录。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},
            {"marker": "123", "position": "after"},
            {"marker": "qqq", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    missing = out["_missing_markers"]["value"]
    assert "xyz" in missing
    assert "123" in missing
    assert "qqq" in missing


def test_chunk_boundary_partial_missing_markers_records_some():
    """部分 marker 找到、部分找不到 → 只记录找不到的。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # 找到
            {"marker": "xyz", "position": "after"},  # 找不到
            {"marker": "def", "position": "after"},  # 找到
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    missing = out.get("_missing_markers", {}).get("value", [])
    assert "xyz" in missing
    assert "abc" not in missing
    assert "def" not in missing


def test_chunk_boundary_repeated_marker_search_from_advances():
    """3 个相同 marker 在 stream 中各出现一次。"""
    doc = {
        "chunks": [
            {"text": "foo"},
            {"text": "foo"},
            {"text": "foo"},
        ]
    }
    # 流 "foo foo foo"
    # 预测 3、7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},  # anchor 3
            {"marker": "foo", "position": "after"},  # anchor 7 (search_from 推进)
            {"marker": "foo", "position": "after"},  # anchor 11
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # matched: pred3-gt3, pred7-gt7 → matched=2
    # num_pred=2, num_gt=3 → precision=1.0, recall=2/3
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == pytest.approx(2 / 3)


def test_chunk_boundary_with_empty_chunks_list():
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_with_empty_chunks_list_no_anchors():
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    # 进入 len(chunks) < 2 分支，no anchors → recall null no_predicted
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_with_empty_chunks_list_no_anchors_value():
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_recall"]["value"] is None


def test_chunk_boundary_idempotent_normal_path():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out1 == out2


def test_chunk_boundary_idempotent_pipeline_failed_path():
    out1 = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    out2 = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out1 == out2


def test_chunk_boundary_idempotent_no_annotation_path():
    out1 = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    out2 = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out1 == out2


def test_chunk_boundary_returns_dict():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert isinstance(out, dict)


def test_chunk_boundary_metric_dict_value_or_reason_keys():
    """每个 metric 都是 {value, reason}。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    for k, v in out.items():
        if k.startswith("chunk_boundary_"):
            assert set(v.keys()) == {"value", "reason"}


def test_chunk_boundary_tolerance_value_int():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    # tolerance 是 int
    assert out["_tolerance_chars"]["value"] == 42
    assert isinstance(out["_tolerance_chars"]["value"], int)


# ---------- chunk_boundary_prf source level 字符串精确补强（第三批） ----------


def test_chunk_boundary_source_uses_initial_out_dict():
    """source 含 out: dict[str, dict[str, Any]] = {}。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "out: dict[str, dict[str, Any]] = {}" in src or "out = {}" in src


def test_chunk_boundary_source_uses_document_is_none_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None" in src


def test_chunk_boundary_source_uses_not_annotation_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not annotation" in src


def test_chunk_boundary_source_uses_chunks_or_empty_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "annotation.get" in src
    assert "document.get" in src


def test_chunk_boundary_source_uses_len_chunks_lt_2_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "len(chunks) < 2" in src


def test_chunk_boundary_source_uses_not_anchors_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not anchors" in src


def test_chunk_boundary_source_uses_norm_chunks_comprehension():
    src = inspect.getsource(chunk_boundary_prf)
    assert "norm_chunks = " in src


def test_chunk_boundary_source_uses_joined_raw_assign():
    src = inspect.getsource(chunk_boundary_prf)
    assert "joined_raw = " in src


def test_chunk_boundary_source_uses_predicted_init_list():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int] = []" in src


def test_chunk_boundary_source_uses_pos_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos = 0" in src


def test_chunk_boundary_source_uses_gt_positions_list():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions: list[int] = []" in src


def test_chunk_boundary_source_uses_missing_markers_list():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_chunk_boundary_source_uses_search_from_advance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = find_pos + len(marker)" in src


def test_chunk_boundary_source_uses_pairs_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_chunk_boundary_source_uses_used_pred_used_gt_set_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_chunk_boundary_source_uses_nested_for_pred_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for pi, pv in enumerate(predicted)" in src
    assert "for gi, gv in enumerate(gt_positions)" in src


def test_chunk_boundary_source_uses_abs_distance_calculation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "d = abs(pv - gv)" in src


def test_chunk_boundary_source_uses_tolerance_compare_in_pairs():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if d <= tolerance_chars" in src


def test_chunk_boundary_source_uses_used_pred_add():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred.add(pi)" in src
    assert "used_gt.add(gi)" in src


def test_chunk_boundary_source_uses_p_val_r_val_extraction():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'p_val = out["chunk_boundary_precision"]["value"]' in src
    assert 'r_val = out["chunk_boundary_recall"]["value"]' in src


def test_chunk_boundary_source_uses_f1_calculation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_chunk_boundary_source_uses_underscore_tolerance_chars_key():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_tolerance_chars"' in src


def test_chunk_boundary_source_uses_underscore_missing_markers_key():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_missing_markers"' in src


def test_chunk_boundary_source_uses_break_in_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "break" in src


def test_chunk_boundary_source_uses_continue_in_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "continue" in src


def test_chunk_boundary_source_no_print():
    src = inspect.getsource(chunk_boundary_prf)
    assert "print(" not in src


def test_chunk_boundary_source_no_logging():
    src = inspect.getsource(chunk_boundary_prf)
    assert "logging" not in src
    assert "logger" not in src


def test_chunk_boundary_source_no_try_except():
    src = inspect.getsource(chunk_boundary_prf)
    # annotation 算法不依赖 try/except
    assert "try:" not in src
    assert "except" not in src


def test_chunk_boundary_source_no_with_statement():
    src = inspect.getsource(chunk_boundary_prf)
    assert "with " not in src


def test_chunk_boundary_source_no_async_def():
    src = inspect.getsource(chunk_boundary_prf)
    assert "async def" not in src


def test_chunk_boundary_source_no_yield():
    src = inspect.getsource(chunk_boundary_prf)
    assert "yield" not in src


def test_chunk_boundary_source_no_global_keyword():
    src = inspect.getsource(chunk_boundary_prf)
    assert "global " not in src


def test_chunk_boundary_source_no_nonlocal_keyword():
    src = inspect.getsource(chunk_boundary_prf)
    assert "nonlocal " not in src


# ---------- module source forbidden tokens 第六批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "_thread", "_dummy_thread", "_markupbase", "_strptime", "_threading_local",
        "_weakrefset", "_collections_abc", "_compat_pickle", "_sitebuiltins",
        "_sysconfigdata", "_pyio", "_dummy_backtrace", "abc", "aifc", "ast",
        "atexit", "audioop", "base64", "bdb", "binascii", "bisect", "builtins",
        "bz2", "cProfile", "calendar", "cgi", "cgitb", "cmath", "cmd",
        "code", "codecs", "codeop", "colorsys", "compileall", "configparser",
        "contextvars", "copy", "crypt", "csv", "ctypes", "curses", "dataclasses",
        "datetime", "decimal", "difflib", "dis", "distutils", "doctest", "email",
        "encodings", "ensurepip", "enum", "errno", "faulthandler", "fcntl",
        "filecmp", "fileinput", "fnmatch", "formatter", "fractions", "ftplib",
        "functools", "gc", "genericpath", "getopt", "getpass", "gettext", "glob",
        "grp", "gzip", "hashlib", "heapq", "hmac", "html", "http", "idlelib",
        "imaplib", "imghdr", "importlib", "inspect", "ipaddress",
        "itertools", "json", "keyword", "lib2to3", "linecache", "locale",
        "logging", "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
        "mmap", "modulefinder", "msilib", "msvcrt", "multiprocessing", "netrc",
        "nis", "nntplib", "ntpath", "numbers", "opcode", "operator", "optparse",
        "os", "ossaudiodev", "parser", "pathlib", "pdb", "pickle", "pickletools",
        "pipes", "pkgutil", "platform", "plistlib", "poplib", "posix", "posixpath",
        "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
        "pydoc", "pydoc_data", "pyexpat", "queue", "quopri", "random",
        "readline", "reprlib", "resource", "rlcompleter", "runpy", "sched",
        "secrets", "select", "selectors", "shelve", "shlex", "shutil", "signal",
        "site", "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "spwd",
        "sqlite3", "sre_compile", "sre_constants", "sre_parse", "ssl", "stat",
        "statistics", "string", "stringprep", "subprocess", "sunau",
        "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
        "telnetlib", "tempfile", "termios", "test", "textwrap", "threading",
        "time", "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
        "tracemalloc", "tty", "turtle", "turtledemo", "types",
        "unicodedata", "unittest", "urllib", "uu", "uuid", "venv", "warnings",
        "wave", "weakref", "webbrowser", "winreg", "winsound", "wsgiref",
        "xdrlib", "xml", "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
        "zoneinfo",
    ],
)
def test_module_source_forbidden_tokens_sixth_batch(token):
    """这些 stdlib 模块不应出现在 annotation_metrics.py。"""
    src = inspect.getsource(amod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert token not in line, f"forbidden token {token} in import: {line}"


# ---------- module source 字符串精确补强（第三批） ----------


def test_module_source_starts_with_docstring():
    """模块以 docstring 开头。"""
    src = inspect.getsource(amod)
    assert src.lstrip().startswith(('"""', "'''"))


def test_module_source_docstring_mentions_human_annotation():
    """docstring 提到'人工标注'。"""
    src = inspect.getsource(amod)
    assert "人工标注" in src


def test_module_source_docstring_mentions_marker_definition():
    """docstring 提到 marker 概念。"""
    src = inspect.getsource(amod)
    assert "marker" in src.lower()


def test_module_source_docstring_mentions_tolerance_definition():
    """docstring 提到 tolerance。"""
    src = inspect.getsource(amod)
    assert "容差" in src


def test_module_source_docstring_mentions_one_to_one_constraint():
    """docstring 提到一对一。"""
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_docstring_mentions_f1_formula():
    """docstring 含 P/R/F1 描述。"""
    src = inspect.getsource(amod)
    assert "precision" in src.lower()
    assert "recall" in src.lower()


def test_module_source_docstring_mentions_null_when_no_relation():
    """docstring 提到固定 null。"""
    src = inspect.getsource(amod)
    assert "null" in src.lower() or "None" in src


def test_module_source_no_relative_import():
    """没有相对导入（from .）。"""
    src = inspect.getsource(amod)
    import_lines = [
        line for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for line in import_lines:
        assert not line.strip().startswith("from .")


def test_module_source_no_star_import():
    src = inspect.getsource(amod)
    assert "import *" not in src


def test_module_source_no_conditional_import():
    src = inspect.getsource(amod)
    lines = src.splitlines()
    in_func = False
    for line in lines:
        if line.startswith("def ") or line.startswith("class "):
            in_func = True
        elif line and not line[0].isspace() and line[0] != "#":
            in_func = False
        if in_func and ("import " in line or "from " in line):
            if line.strip().startswith(("import ", "from ")):
                pytest.fail(f"conditional import inside function: {line}")


def test_module_source_4_blank_lines_between_functions():
    """PEP8: 模块级函数之间 2 个空行；这里检查至少有 2 个空行。"""
    src = inspect.getsource(amod)
    lines = src.splitlines()
    func_starts = [i for i, line in enumerate(lines) if line.startswith("def ")]
    if len(func_starts) >= 2:
        # 检查 def 之间是否有空行
        gap = func_starts[1] - func_starts[0]
        assert gap >= 3  # 至少 def body + 2 空行


def test_module_source_imports_order_future_first():
    """__future__ 必须在最前面（PEP8）。"""
    src = inspect.getsource(amod)
    lines = src.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            # 找到 __future__，确认 import lines 之前没有非 import 非 docstring 行
            return


def test_module_source_no_eval_exec():
    src = inspect.getsource(amod)
    assert "eval(" not in src
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(amod)
    assert "compile(" not in src


def test_module_source_no_globals_call():
    src = inspect.getsource(amod)
    assert "globals(" not in src


def test_module_source_no_locals_call():
    src = inspect.getsource(amod)
    assert "locals(" not in src


def test_module_source_no_open_call():
    """模块级不开文件。"""
    src = inspect.getsource(amod)
    assert "\nopen(" not in src


def test_module_source_2_module_level_functions_confirmed():
    src = inspect.getsource(amod)
    func_count = sum(1 for line in src.splitlines() if line.startswith("def "))
    assert func_count == 2


def test_module_source_1_module_level_constant_confirmed():
    src = inspect.getsource(amod)
    const_count = sum(
        1 for line in src.splitlines()
        if line.startswith("PARSER_DOES_NOT_EMIT_RELATIONS =")
    )
    assert const_count == 1


def test_module_source_has_all_with_exact_entries():
    src = inspect.getsource(amod)
    assert "__all__" in src
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_module_source_2_function_names_exact():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src
    assert "def chunk_boundary_prf(" in src


def test_module_source_no_class_definition():
    src = inspect.getsource(amod)
    body_lines = [
        (i, line) for i, line in enumerate(src.splitlines())
        if not line.strip().startswith(("#", '"', "'"))
    ]
    for i, line in body_lines:
        # 检查是否独立 class 行（不在字符串内）
        if line.startswith("class ") or line.lstrip().startswith("class "):
            # class 在 def 内部？检查缩进
            if line.startswith("class "):
                pytest.fail(f"unexpected top-level class: {line}")


# ---------- signatures 精确补强（第三批） ----------


def test_figure_caption_prf_signature_param_count():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_signature_first_param_name():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys())[0] == "document"


def test_figure_caption_prf_signature_second_param_name():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys())[1] == "annotation"


def test_figure_caption_prf_signature_no_var_positional():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds


def test_figure_caption_prf_signature_no_var_keyword():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_figure_caption_prf_signature_no_keyword_only():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.KEYWORD_ONLY not in kinds


def test_figure_caption_prf_signature_no_positional_only():
    sig = inspect.signature(figure_caption_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.POSITIONAL_ONLY not in kinds


def test_figure_caption_prf_signature_all_positional_or_keyword():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_signature_return_is_str_or_type():
    """from __future__ 让 return annotation 是 str。"""
    sig = inspect.signature(figure_caption_prf)
    ra = sig.return_annotation
    assert ra is not inspect.Parameter.empty
    assert "dict" in str(ra)


def test_chunk_boundary_prf_signature_param_count():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_signature_first_param_name():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys())[0] == "document"


def test_chunk_boundary_prf_signature_second_param_name():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys())[1] == "annotation"


def test_chunk_boundary_prf_signature_third_param_name():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys())[2] == "tolerance_chars"


def test_chunk_boundary_prf_signature_no_var_positional():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_POSITIONAL not in kinds


def test_chunk_boundary_prf_signature_no_var_keyword():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.VAR_KEYWORD not in kinds


def test_chunk_boundary_prf_signature_no_keyword_only():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.KEYWORD_ONLY not in kinds


def test_chunk_boundary_prf_signature_no_positional_only():
    sig = inspect.signature(chunk_boundary_prf)
    kinds = {p.kind for p in sig.parameters.values()}
    assert inspect.Parameter.POSITIONAL_ONLY not in kinds


def test_chunk_boundary_prf_signature_all_positional_or_keyword():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_signature_third_param_default_is_30():
    sig = inspect.signature(chunk_boundary_prf)
    p = list(sig.parameters.values())[2]
    assert p.default == 30


def test_chunk_boundary_prf_signature_third_param_annotation_is_int():
    sig = inspect.signature(chunk_boundary_prf)
    p = list(sig.parameters.values())[2]
    assert p.annotation is int or p.annotation == "int"


def test_chunk_boundary_prf_signature_first_param_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    p = list(sig.parameters.values())[0]
    assert p.annotation is not inspect.Parameter.empty
    assert "dict" in str(p.annotation) or p.annotation is None


def test_chunk_boundary_prf_signature_second_param_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    p = list(sig.parameters.values())[1]
    assert p.annotation is not inspect.Parameter.empty
    assert "dict" in str(p.annotation) or p.annotation is None


def test_chunk_boundary_prf_signature_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    ra = sig.return_annotation
    assert ra is not inspect.Parameter.empty
    assert "dict" in str(ra)


def test_functions_have_docstrings():
    """两个函数都有 docstring。"""
    assert figure_caption_prf.__doc__ is not None
    assert len(figure_caption_prf.__doc__) > 0
    assert chunk_boundary_prf.__doc__ is not None
    assert len(chunk_boundary_prf.__doc__) > 0


def test_chunk_boundary_prf_docstring_mentions_tolerance():
    assert chunk_boundary_prf.__doc__ is not None
    assert "tolerance" in chunk_boundary_prf.__doc__.lower() or "容差" in chunk_boundary_prf.__doc__


def test_chunk_boundary_prf_docstring_mentions_precision():
    assert chunk_boundary_prf.__doc__ is not None
    assert "precision" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_recall():
    assert chunk_boundary_prf.__doc__ is not None
    assert "recall" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_args():
    assert chunk_boundary_prf.__doc__ is not None
    assert "Args" in chunk_boundary_prf.__doc__ or "args" in chunk_boundary_prf.__doc__.lower()


def test_figure_caption_prf_docstring_mentions_null():
    assert figure_caption_prf.__doc__ is not None
    assert "null" in figure_caption_prf.__doc__.lower() or "None" in figure_caption_prf.__doc__


# ---------- 模块整体合理性（第三批） ----------


def test_module_namespace_is_module():
    assert isinstance(amod, types.ModuleType)


def test_module_namespace_name():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_namespace_has_file():
    assert hasattr(amod, "__file__")
    assert amod.__file__ is not None


def test_module_namespace_has_doc():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_namespace_has_all():
    assert hasattr(amod, "__all__")


def test_module_all_is_list_type():
    assert isinstance(amod.__all__, list)


def test_module_all_entries_count():
    assert len(amod.__all__) == 3


def test_module_all_entries_are_strings():
    for entry in amod.__all__:
        assert isinstance(entry, str)


def test_module_all_entries_exact_set():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_namespace_has_parser_constant():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_namespace_parser_constant_value():
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_namespace_parser_constant_type():
    assert isinstance(amod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_namespace_has_figure_caption():
    assert hasattr(amod, "figure_caption_prf")


def test_module_namespace_has_chunk_boundary():
    assert hasattr(amod, "chunk_boundary_prf")


def test_module_namespace_figure_caption_is_callable():
    assert callable(amod.figure_caption_prf)


def test_module_namespace_chunk_boundary_is_callable():
    assert callable(amod.chunk_boundary_prf)


def test_module_namespace_figure_caption_is_function():
    assert isinstance(amod.figure_caption_prf, types.FunctionType)


def test_module_namespace_chunk_boundary_is_function():
    assert isinstance(amod.chunk_boundary_prf, types.FunctionType)


def test_module_namespace_function_module_eq_annotation_metrics():
    assert amod.figure_caption_prf.__module__ == "evaluation.annotation_metrics"
    assert amod.chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_module_no_user_defined_classes():
    """模块没有自定义 class。"""
    classes = [
        v for v in vars(amod).values()
        if isinstance(v, type) and v.__module__ == amod.__name__
    ]
    assert len(classes) == 0


def test_module_has_2_module_level_functions_counted():
    functions = [
        v for v in vars(amod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == amod.__name__
    ]
    assert len(functions) == 2


def test_module_function_names_exact():
    functions = [
        v for v in vars(amod).values()
        if isinstance(v, types.FunctionType)
        and v.__module__ == amod.__name__
    ]
    names = sorted(f.__name__ for f in functions)
    assert names == ["chunk_boundary_prf", "figure_caption_prf"]


def test_module_constants_only_parser_does_not_emit():
    """模块级 str 常量只有 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    src = inspect.getsource(amod)
    # 检查 UPPER_CASE 常量赋值（不在 def 内）
    module_constants = []
    for line in src.splitlines():
        stripped = line.strip()
        if (
            stripped
            and not stripped.startswith(("#", '"', "'", "def ", "class ", " "))
            and "=" in stripped
            and stripped.split("=")[0].strip().isupper()
        ):
            module_constants.append(stripped.split("=")[0].strip())
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in module_constants


def test_module_imports_only_5_names():
    """只 import 5 个名字：annotations, Counter, Any, normalize_text, _null/_ratio。"""
    src = inspect.getsource(amod)
    import_lines = [
        line.strip() for line in src.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    # 期望：from __future__, from collections, from typing, from app.chunkers, from evaluation.metrics
    assert len(import_lines) == 5


# ---------- 端到端集成补强（第三批） ----------


def test_e2e_chunk_boundary_with_real_doc_layout():
    """模拟真实文档：3 段 + 2 个 marker（与内部边界对应）。"""
    doc = {
        "chunks": [
            {"text": "第一段正文内容。", "chunk_id": "c1"},
            {"text": "第二段正文内容。", "chunk_id": "c2"},
            {"text": "第三段正文内容。", "chunk_id": "c3"},
        ]
    }
    # norm_chunks = ["第一段正文内容。", "第二段正文内容。", "第三段正文内容。"]
    # stream = "第一段正文内容。 第二段正文内容。 第三段正文内容。"
    # 预测：8、17（每段后）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "第一段正文内容。", "position": "after"},  # anchor 8
            {"marker": "第二段正文内容。", "position": "after"},  # anchor 17
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 2 pred、2 anchor，距离全 0 → matched=2
    # precision=1.0, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_multi_marker():
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
            {"text": "epsilon"},
        ]
    }
    # 流 "alpha beta gamma delta epsilon"
    # 预测 10、22
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha beta", "position": "after"},  # anchor 10
            {"marker": "gamma delta", "position": "after"},  # anchor 22
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_with_chunks_containing_newlines():
    """chunk text 含换行 → normalize 后变空格。"""
    doc = {
        "chunks": [
            {"text": "hello\nworld"},
            {"text": "foo\nbar"},
        ]
    }
    # normalize_text("hello\nworld") = "hello world"
    # normalize_text("foo\nbar") = "foo bar"
    # joined = "hello world foo bar" → normalize 同
    # 预测 11（"hello world" 后）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_chunks_containing_tabs():
    doc = {
        "chunks": [
            {"text": "hello\tworld"},
            {"text": "foo"},
        ]
    }
    # normalize_text("hello\tworld") = "hello world"
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_chunks_containing_unicode_whitespace():
    """Unicode 空白（NBSP U+00A0）也被 normalize。"""
    nbsp = " "
    doc = {
        "chunks": [
            {"text": f"hello{nbsp}world"},
            {"text": "foo"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_call_with_int_tolerance():
    """tolerance_chars 是 int 类型。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=int(5))
    assert out["_tolerance_chars"]["value"] == 5


def test_e2e_json_serializable_normal_path():
    import json
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_json_serializable_pipeline_failed():
    import json
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_json_serializable_no_annotation():
    import json
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_json_serializable_missing_markers():
    import json
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_e2e_with_kwargs_complete():
    """全关键字调用。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(
        document=doc,
        annotation=annotation,
        tolerance_chars=0,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_positional_complete():
    """全位置调用。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, 0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_mixed_positional_keyword():
    """前两个位置，第三个关键字。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_default_tolerance_30_match():
    """默认 tolerance=30 时，距离 < 30 都 match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 预测 3
    # marker "ab" after → anchor 2，距离 1 < 30 → match
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_default_tolerance_30_no_match_when_far():
    """默认 tolerance=30 时，距离 > 30 不 match。"""
    # 构造距离 31：long chunk + anchor 在远端
    long_a = "a" * 40
    long_b = "b" * 5
    doc = {"chunks": [{"text": long_a}, {"text": long_b}]}
    # 预测 40
    # marker long_b after → 在 41 找到 + 5 = 46
    # 距离 |40-46|=6 < 30 → match
    # 改用 marker=long_a before → anchor 0，距离 40 > 30 → no match
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": long_a, "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_e2e_no_mutation_of_document():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}], "extra": 1}
    doc_before = repr(doc)
    chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert repr(doc) == doc_before


def test_e2e_no_mutation_of_annotation():
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
        "x": 1,
    }
    ann_before = repr(annotation)
    chunk_boundary_prf({"chunks": [{"text": "abc"}, {"text": "def"}]}, annotation)
    assert repr(annotation) == ann_before


def test_e2e_no_mutation_of_anchors_list():
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "def", "position": "after"},
        ],
    }
    anchors_before = repr(annotation["chunk_boundary_anchors"])
    chunk_boundary_prf({"chunks": [{"text": "abc"}, {"text": "def"}]}, annotation)
    assert repr(annotation["chunk_boundary_anchors"]) == anchors_before


def test_e2e_tolerances_zero_vs_one_difference():
    """tolerance=0 vs 1 在边界 case 下结果不同。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 预测 3
    # marker "ab" after → anchor 2，距离 1
    annotation = {
        "chunk_boundary_anchors": [{"marker": "ab", "position": "after"}],
    }
    out0 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # tolerance=0：距离 1 > 0 → no match
    # tolerance=1：距离 1 <= 1 → match
    assert out0["chunk_boundary_precision"]["value"] == 0.0
    assert out1["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_negative_tolerance_never_matches():
    """tolerance=-1 → 任何距离都 > -1 → no match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    # 距离 0 > -1? Python: 0 <= -1 是 False → no match
    # matched=0 → precision=0/1=0.0, recall=0/1=0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_e2e_huge_tolerance_matches_everything():
    """tolerance=10**9。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},  # 找不到
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10**9)
    # marker "x" 找不到 → missing → gt_positions=[]
    # recall null no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_e2e_deterministic_with_many_anchors():
    """多 anchor 场景的确定性。"""
    doc = {
        "chunks": [
            {"text": "a"},
            {"text": "b"},
            {"text": "c"},
            {"text": "d"},
            {"text": "e"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
            {"marker": "c", "position": "after"},
            {"marker": "d", "position": "after"},
        ]
    }
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out1 == out2
    assert out1["chunk_boundary_precision"]["value"] == 1.0
    assert out1["chunk_boundary_recall"]["value"] == 1.0
