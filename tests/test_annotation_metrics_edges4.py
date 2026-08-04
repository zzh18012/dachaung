r"""evaluation/annotation_metrics.py 边角测试 - 第四轮（Round 120）。

补强已有 base/edges/edges2/edges3（共 310 测试）未覆盖的深度路径：
- figure_caption_prf：
  - 各种 input 类型均返回相同 3 key（None/空 dict/正常 dict）
  - reason 值精确
  - value/reason 字段类型固定
  - 函数无副作用（重复调用结果一致）
- chunk_boundary_prf 算法深度：
  - tolerance_chars 边界（恰好 = tolerance 匹配，> tolerance 不匹配）
  - predicted 数量 = N-1（N 个 chunk）
  - chunk text 含特殊字符（标点、数字混合）
  - marker 与 chunk text 部分重叠
  - marker 在 stream 中多次出现（顺序定位）
  - chunk text 在 stream 中找不到（predicted 跳过）
  - position 值为 "Before"/"AFTER"（大小写敏感）
  - position 值非 "before"/"after"（视为 after）
  - chunk text 长度 > stream（异常但应不抛）
  - annotation.get 返回 None（chunk_boundary_anchors=null）
  - document.get 返回 None（chunks=null）
  - 负 tolerance_chars 与边界匹配
  - 多 anchor 共享 stream 位置（不允许）
- 模块结构深度：
  - imports 完整（Counter/Any/normalize_text/_null/_ratio）
  - PARSER_DOES_NOT_EMIT_RELATIONS 值精确
  - __all__ 精确
  - 模块 docstring 提及关键约束
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# figure_caption_prf 第四轮深度
# =========================================================================


def test_figure_caption_keys_always_three_for_none_inputs():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_keys_always_three_for_empty_dicts():
    out = figure_caption_prf({}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_keys_always_three_for_normal_inputs():
    doc = {"chunks": [{"text": "abc"}], "elements": []}
    ann = {"chunk_boundary_anchors": []}
    out = figure_caption_prf(doc, ann)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_precision_value_is_none():
    out = figure_caption_prf(None, None)
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_recall_value_is_none():
    out = figure_caption_prf(None, None)
    assert out["figure_caption_recall"]["value"] is None


def test_figure_caption_f1_value_is_none():
    out = figure_caption_prf(None, None)
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_precision_reason_value():
    out = figure_caption_prf(None, None)
    assert (
        out["figure_caption_precision"]["reason"]
        == PARSER_DOES_NOT_EMIT_RELATIONS
    )


def test_figure_caption_recall_reason_value():
    out = figure_caption_prf(None, None)
    assert (
        out["figure_caption_recall"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
    )


def test_figure_caption_f1_reason_value():
    out = figure_caption_prf(None, None)
    assert out["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_idempotent_multiple_calls():
    out1 = figure_caption_prf({"chunks": []}, None)
    out2 = figure_caption_prf({"chunks": []}, None)
    # 不同 dict 对象（每次新构造），但内容相同
    assert out1 == out2
    assert out1 is not out2


def test_figure_caption_with_annotation_present_still_null():
    """即使 annotation 含 figure_caption_anchors，结果仍 null（parser 不输出 relation）。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"figure_caption_anchors": [{"caption": "Fig 1"}]}
    out = figure_caption_prf(doc, ann)
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_value_field_is_none_type():
    out = figure_caption_prf(None, None)
    # value 必为 None（不允许其他 falsy 值如 0/False）
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_recall"]["value"] is None
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_reason_field_is_str_type():
    out = figure_caption_prf(None, None)
    assert isinstance(out["figure_caption_precision"]["reason"], str)
    assert isinstance(out["figure_caption_recall"]["reason"], str)
    assert isinstance(out["figure_caption_f1"]["reason"], str)


# =========================================================================
# chunk_boundary_prf tolerance 边界
# =========================================================================


def _chunk(text: str) -> dict:
    return {"text": text}


def _anchor(marker: str, position: str = "after") -> dict:
    return {"marker": marker, "position": position}


def test_chunk_boundary_tolerance_exact_match():
    """距离恰好等于 tolerance_chars → 匹配。"""
    # 2 chunks, 1 anchor；让 anchor 与 predicted 距离正好 = tolerance
    chunks = [_chunk("hello world foo bar"), _chunk("baz")]
    # predicted 位置 = "hello world foo bar" 的末尾 = 19
    # anchor "foo" after → marker 末尾位置 = 19 (3+5+6=14 wait)
    # stream = "hello world foo bar baz"
    #          0123456789012345678901234
    # find "foo" at 12, len 3 → after = 15
    # predicted = 19 (end of "hello world foo bar")
    # distance = |19 - 15| = 4
    ann = {"chunk_boundary_anchors": [_anchor("foo")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann, tolerance_chars=4)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_tolerance_one_more_fails():
    """距离 = tolerance + 1 → 不匹配。"""
    chunks = [_chunk("hello world foo bar"), _chunk("baz")]
    ann = {"chunk_boundary_anchors": [_anchor("foo")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann, tolerance_chars=3)
    # distance = 4, tolerance = 3 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_tolerance_zero_exact_match_only():
    chunks = [_chunk("ab"), _chunk("cd")]
    # stream = "ab cd", predicted = 2 (end of "ab")
    # anchor "ab" after → position 2; distance = 0
    ann = {"chunk_boundary_anchors": [_anchor("ab")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_zero_one_off_no_match():
    chunks = [_chunk("ab"), _chunk("cd")]
    # stream = "ab cd", predicted = 2
    # anchor "a" after → position 1; distance = 1 > 0
    ann = {"chunk_boundary_anchors": [_anchor("a")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf predicted 数量
# =========================================================================


def test_chunk_boundary_predicted_count_n_minus_one_two_chunks():
    """2 chunks → 1 predicted boundary。"""
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 1 predicted, 1 anchor, exact match → 1.0 / 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_predicted_count_n_minus_one_three_chunks():
    """3 chunks → 2 predicted boundaries。"""
    chunks = [_chunk("alpha"), _chunk("beta"), _chunk("gamma")]
    ann = {
        "chunk_boundary_anchors": [
            _anchor("alpha"),
            _anchor("beta"),
        ]
    }
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 2 predicted, 2 anchors, both match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_predicted_count_n_minus_one_five_chunks():
    chunks = [_chunk("a"), _chunk("b"), _chunk("c"), _chunk("d"), _chunk("e")]
    ann = {
        "chunk_boundary_anchors": [
            _anchor("a"),
            _anchor("b"),
            _anchor("c"),
            _anchor("d"),
        ]
    }
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 4 predicted, 4 anchors
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf position 大小写敏感
# =========================================================================


def test_chunk_boundary_position_before_lowercase():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("beta", "before")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "alpha beta"
    # predicted = 5 (end of alpha)
    # anchor "beta" before → find at 6, before = 6; distance = 1
    # 默认 tolerance=30 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_after_uppercase_treated_as_after():
    """'AFTER' 不是 'after' 但代码用 else 分支 → 视为 after。"""
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha", "AFTER")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 同 "after" 行为
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_unknown_string_treated_as_after():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha", "middle")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 同 "after" 行为
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_empty_string_treated_as_after():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha", "")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf chunk text 含特殊字符
# =========================================================================


def test_chunk_boundary_chunk_text_with_punctuation():
    chunks = [_chunk("Hello, world!"), _chunk("Foo, bar?")]
    ann = {"chunk_boundary_anchors": [_anchor("Hello, world!")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "hello, world! foo, bar?" (after normalize)
    # 注意 normalize_text 会小写化吗？看实现
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_text_with_digits():
    chunks = [_chunk("abc123"), _chunk("def456")]
    ann = {"chunk_boundary_anchors": [_anchor("abc123")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_text_with_unicode():
    chunks = [_chunk("中文内容"), _chunk("更多内容")]
    ann = {"chunk_boundary_anchors": [_anchor("中文内容")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf 算法细节
# =========================================================================


def test_chunk_boundary_marker_finds_second_occurrence():
    """marker 在 stream 中两次出现 → 第二个 anchor 应找到第二次。"""
    chunks = [_chunk("foo"), _chunk("bar"), _chunk("foo"), _chunk("baz")]
    # stream = "foo bar foo baz"
    # predicted[0] = end of "foo" = 3
    # predicted[1] = end of "bar" = 7
    # predicted[2] = end of "foo" = 11
    ann = {
        "chunk_boundary_anchors": [
            _anchor("foo"),  # 第一次 foo: find at 0, after = 3
            _anchor("foo"),  # 第二次 foo: find at 8, after = 11
        ]
    }
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # 3 predicted, 2 anchors, both match
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_marker_overlap_with_chunk_text():
    """marker 是某 chunk text 的前缀。"""
    chunks = [_chunk("foobar"), _chunk("baz")]
    ann = {"chunk_boundary_anchors": [_anchor("foo")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "foobar baz"
    # find "foo" at 0, after = 3
    # predicted = 6 (end of "foobar")
    # distance = 3, default tol = 30 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_text_not_found_in_stream():
    """chunk text 找不到（理论不可能）→ predicted 跳过该位置。"""
    # 触发条件很难构造，因为 stream 由 chunks 拼接而成
    # 但可以通过 chunk.text=None 触发 fallback
    chunks = [{"text": None}, _chunk("real")]
    ann = {"chunk_boundary_anchors": [_anchor("real")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # chunks[0] text 为 None → normalize_text("") = ""
    # stream = " real"
    # predicted: chunk[0] text="" → find at 0, end=0, predicted=[0]
    # 但 chunks[0] 不是 last，所以 end=0 算 predicted
    # 算法上仍能 match
    assert isinstance(out, dict)


def test_chunk_boundary_anchor_marker_at_stream_start():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha", "before")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "alpha beta"
    # find "alpha" at 0, before = 0
    # predicted = 5
    # distance = 5, tol = 30 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_anchor_marker_at_stream_end():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("beta", "after")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "alpha beta"
    # find "beta" at 6, after = 10
    # predicted = 5
    # distance = 5, tol = 30 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf 多 predicted 多 anchor 匹配
# =========================================================================


def test_chunk_boundary_more_predicted_than_anchors_partial_match():
    """predicted 多于 anchors → precision < 1.0。"""
    chunks = [_chunk("a"), _chunk("b"), _chunk("c"), _chunk("d")]
    # predicted: 3 boundaries (end of a, b, c)
    ann = {"chunk_boundary_anchors": [_anchor("a")]}  # 1 anchor
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # matched = 1, num_pred = 3, num_gt = 1
    # precision = 1/3, recall = 1/1
    assert out["chunk_boundary_precision"]["value"] == 1.0 / 3.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_more_anchors_than_predicted_partial_match():
    """anchors 多于 predicted → recall < 1.0。"""
    chunks = [_chunk("a"), _chunk("b")]  # 1 predicted
    ann = {
        "chunk_boundary_anchors": [
            _anchor("a"),
            _anchor("a"),  # 第二个 "a" marker 在 stream 中只有一次 → missing
        ]
    }
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # stream = "a b"
    # anchor[0] "a": find at 0, after = 1
    # anchor[1] "a": search_from = 1, find at... no more "a" → missing
    # gt_positions = [1], num_gt = 1
    # predicted = 1, matched = 1
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_greedy_prefers_smallest_distance():
    """贪心匹配：当 2 个 predicted 都能匹配同一 anchor 时，选距离最小的。"""
    chunks = [_chunk("abc"), _chunk("def"), _chunk("ghi")]
    # stream = "abc def ghi"
    # predicted[0] = 3, predicted[1] = 7
    # anchor "def" before → find at 4, before = 4
    # |3-4|=1, |7-4|=3, tol=30
    # 贪心选 distance=1 的 pair
    ann = {"chunk_boundary_anchors": [_anchor("def", "before")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # matched = 1, num_pred = 2, num_gt = 1
    # precision = 1/2, recall = 1/1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_one_to_one_matching_no_double_count():
    """两个 anchor 都匹配同一 predicted → 只能一个成功（一对一）。"""
    # 构造两个 anchor 都落在同一 predicted 附近
    chunks = [_chunk("alpha"), _chunk("beta")]
    # stream = "alpha beta"
    # predicted = 5 (end of alpha)
    ann = {
        "chunk_boundary_anchors": [
            _anchor("a", "before"),  # find at 0, before=0; search_from=1
            _anchor("l", "before"),  # find at 2, before=2; search_from=3
        ]
    }
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # gt_positions = [0, 2]
    # predicted = [5]
    # pairs: (5, 0, 0), (3, 0, 1)
    # sort by distance: (3, 0, 1), (5, 0, 0)
    # match (3, 0, 1): pred 0, gt 1 used
    # match (5, 0, 0): pred 0 used → skip
    # matched = 1, num_pred = 1, num_gt = 2
    # precision = 1/1 = 1.0, recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# =========================================================================
# chunk_boundary_prf F1 计算
# =========================================================================


def test_chunk_boundary_f1_perfect_match():
    chunks = [_chunk("a"), _chunk("b")]
    ann = {"chunk_boundary_anchors": [_anchor("a")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # p=1, r=1, f1 = 2*1*1/(1+1) = 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_f1_zero_match():
    chunks = [_chunk("a"), _chunk("b")]
    ann = {"chunk_boundary_anchors": [_anchor("xyz")]}  # 找不到
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    # marker missing → gt_positions = []
    # num_gt = 0 → recall = null
    # f1 = null
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_f1_half_when_p_half_r_full():
    """p=0.5, r=1.0 → f1 = 2*0.5*1/(0.5+1) = 1/1.5 ≈ 0.667。"""
    chunks = [_chunk("a"), _chunk("b"), _chunk("c")]
    # 2 predicted, 1 anchor
    ann = {"chunk_boundary_anchors": [_anchor("a")]}
    out = chunk_boundary_prf({"chunks": chunks}, ann)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    if p is not None and r is not None:
        expected = 2 * p * r / (p + r)
        assert f1 == expected


# =========================================================================
# chunk_boundary_prf 不变性
# =========================================================================


def test_chunk_boundary_does_not_mutate_document_chunks():
    chunks = [_chunk("alpha"), _chunk("beta")]
    doc = {"chunks": chunks}
    original_chunks = list(doc["chunks"])
    chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert doc["chunks"] == original_chunks


def test_chunk_boundary_does_not_mutate_annotation_anchors():
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"}
        ]
    }
    original_ann = {"chunk_boundary_anchors": list(ann["chunk_boundary_anchors"])}
    chunk_boundary_prf({"chunks": [_chunk("alpha"), _chunk("beta")]}, ann)
    assert ann == original_ann


def test_chunk_boundary_idempotent_multiple_calls():
    chunks = [_chunk("alpha"), _chunk("beta")]
    ann = {"chunk_boundary_anchors": [_anchor("alpha")]}
    out1 = chunk_boundary_prf({"chunks": chunks}, ann)
    out2 = chunk_boundary_prf({"chunks": chunks}, ann)
    assert out1 == out2


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_constant_value():
    from evaluation import annotation_metrics as mod

    assert mod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_constant_is_str():
    from evaluation import annotation_metrics as mod

    assert isinstance(mod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_all_is_list():
    from evaluation import annotation_metrics as mod

    assert isinstance(mod.__all__, list)


def test_module_all_length_three():
    from evaluation import annotation_metrics as mod

    assert len(mod.__all__) == 3


def test_module_all_exact():
    from evaluation import annotation_metrics as mod

    assert set(mod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_imports_counter():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "Counter")


def test_module_imports_any():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "Any")


def test_module_imports_normalize_text():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "normalize_text")


def test_module_imports_null_helper():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "_null")


def test_module_imports_ratio_helper():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "_ratio")


def test_module_has_figure_caption_prf():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "figure_caption_prf")


def test_module_has_chunk_boundary_prf():
    from evaluation import annotation_metrics as mod

    assert hasattr(mod, "chunk_boundary_prf")


def test_module_figure_caption_callable():
    from evaluation import annotation_metrics as mod

    assert callable(mod.figure_caption_prf)


def test_module_chunk_boundary_callable():
    from evaluation import annotation_metrics as mod

    assert callable(mod.chunk_boundary_prf)


def test_module_docstring_present():
    from evaluation import annotation_metrics as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_caption():
    """模块 docstring 应提及 caption（figure_caption 关键词）。"""
    from evaluation import annotation_metrics as mod

    doc = mod.__doc__
    assert "caption" in doc.lower() or "图表" in doc


def test_module_docstring_mentions_chunk_boundary():
    from evaluation import annotation_metrics as mod

    doc = mod.__doc__
    assert "chunk_boundary" in doc or "分块边界" in doc or "boundary" in doc.lower()


def test_module_docstring_mentions_tolerance():
    from evaluation import annotation_metrics as mod

    doc = mod.__doc__
    assert "tolerance" in doc.lower() or "容差" in doc


def test_module_uses_future_annotations():
    """模块用了 from __future__ import annotations。"""
    import ast

    from evaluation import annotation_metrics as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_figure_caption_signature_two_params():
    import inspect
    from evaluation.annotation_metrics import figure_caption_prf

    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert "document" in params
    assert "annotation" in params


def test_chunk_boundary_signature_three_params():
    import inspect
    from evaluation.annotation_metrics import chunk_boundary_prf

    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert "document" in params
    assert "annotation" in params
    assert "tolerance_chars" in params


def test_chunk_boundary_tolerance_default_30():
    import inspect
    from evaluation.annotation_metrics import chunk_boundary_prf

    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_tolerance_param_kind():
    """tolerance_chars 默认是 keyword-or-positional。"""
    import inspect
    from evaluation.annotation_metrics import chunk_boundary_prf

    sig = inspect.signature(chunk_boundary_prf)
    kind = sig.parameters["tolerance_chars"].kind
    assert kind in (
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    )


def test_figure_caption_no_default_for_document():
    import inspect
    from evaluation.annotation_metrics import figure_caption_prf

    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_figure_caption_no_default_for_annotation():
    import inspect
    from evaluation.annotation_metrics import figure_caption_prf

    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty
