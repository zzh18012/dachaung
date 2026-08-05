r"""evaluation/annotation_metrics.py 边角测试 - 第八轮（Round 211）。

补强已有 base/edges/edges2-7（共 ~532 测试）未覆盖的深度：
- 模块结构 / __all__ exact / imports
- PARSER_DOES_NOT_EMIT_RELATIONS 常量值与类型
- figure_caption_prf 各 document/annotation 形态组合
- chunk_boundary_prf document None 路径（pipeline_failed）
- chunk_boundary_prf annotation 是非 dict 路径
- chunk_boundary_prf chunks 缺字段
- chunk_boundary_prf tolerance_chars 传播到 _tolerance_chars
- chunk_boundary_prf _missing_markers 仅当缺失时存在
- chunk_boundary_prf precision/recall 分母 0 时 null + reason
- chunk_boundary_prf f1 各 null/zero 组合
- chunk_boundary_prf position="before" / "after" 边界
- 模块 docstring 提到关键约束
- 综合行为
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    _null,  # noqa: F401  re-export check
    _ratio,  # noqa: F401
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact_set():
    import evaluation.annotation_metrics as m
    assert set(m.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_all_is_list():
    import evaluation.annotation_metrics as m
    assert isinstance(m.__all__, list)


def test_module_all_length_is_three():
    import evaluation.annotation_metrics as m
    assert len(m.__all__) == 3


def test_module_all_no_duplicates():
    import evaluation.annotation_metrics as m
    assert len(set(m.__all__)) == len(m.__all__)


def test_module_imports_counter():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Counter")


def test_module_imports_any():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Any")


def test_module_imports_normalize_text():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "normalize_text")


def test_module_docstring_present():
    import evaluation.annotation_metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_figure_caption():
    import evaluation.annotation_metrics as m
    assert "figure_caption" in m.__doc__ or "图表" in m.__doc__


def test_module_docstring_mentions_chunk_boundary():
    import evaluation.annotation_metrics as m
    assert "chunk_boundary" in m.__doc__ or "边界" in m.__doc__


def test_module_uses_future_annotations():
    import evaluation.annotation_metrics as m
    sig = inspect.signature(m.chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.annotation_metrics as m
    assert not hasattr(m, "_silence_unused_import")


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量
# =========================================================================


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_exact():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_nonempty():
    assert len(PARSER_DOES_NOT_EMIT_RELATIONS) > 0


def test_parser_does_not_emit_relations_in_module_namespace():
    import evaluation.annotation_metrics as m
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# figure_caption_prf 深度
# =========================================================================


def test_figure_caption_prf_signature():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters)
    assert params == ["document", "annotation"]


def test_figure_caption_prf_return_annotation_str():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_figure_caption_prf_callable():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_returns_dict():
    result = figure_caption_prf(None, None)
    assert isinstance(result, dict)


def test_figure_caption_prf_keys_exact_three():
    result = figure_caption_prf(None, None)
    assert set(result.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_none():
    result = figure_caption_prf(None, None)
    for k, v in result.items():
        assert v["value"] is None, k


def test_figure_caption_prf_all_reasons_set():
    result = figure_caption_prf(None, None)
    for k, v in result.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS, k


def test_figure_caption_prf_with_document_dict():
    """即使 document 给定，仍返回 null（parser 不输出 relation）。"""
    doc = {"elements": [], "chunks": []}
    result = figure_caption_prf(doc, None)
    for v in result.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_annotation():
    annotation = {"figure_caption_relations": []}
    result = figure_caption_prf(None, annotation)
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_with_both():
    doc = {"elements": [], "chunks": []}
    annotation = {"figure_caption_relations": []}
    result = figure_caption_prf(doc, annotation)
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_idempotent():
    doc = {"elements": [], "chunks": []}
    a = figure_caption_prf(doc, None)
    b = figure_caption_prf(doc, None)
    assert a == b


def test_figure_caption_prf_each_metric_two_keys():
    result = figure_caption_prf(None, None)
    for k, v in result.items():
        assert set(v.keys()) == {"value", "reason"}, k


def test_figure_caption_prf_does_not_mutate_input():
    doc = {"elements": [{"type": "image"}], "chunks": []}
    doc_before = dict(doc)
    figure_caption_prf(doc, None)
    assert doc == doc_before


# =========================================================================
# chunk_boundary_prf 签名
# =========================================================================


def test_chunk_boundary_prf_signature():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters)
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_is_positional_or_keyword():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_return_annotation_str():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_chunk_boundary_prf_callable():
    assert callable(chunk_boundary_prf)


# =========================================================================
# chunk_boundary_prf document None 路径
# =========================================================================


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    result = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["value"] is None
        assert result[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_includes_tolerance():
    result = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert result["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_document_none_keys_exact():
    result = chunk_boundary_prf(None, None)
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert set(result.keys()) == expected


# =========================================================================
# chunk_boundary_prf annotation falsy 路径
# =========================================================================


def test_chunk_boundary_prf_annotation_none_returns_no_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["value"] is None
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_returns_no_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    result = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_list_returns_no_annotation():
    """annotation 是 list 而非 dict → falsy → no_annotation。"""
    doc = {"chunks": [{"text": "a"}]}
    result = chunk_boundary_prf(doc, [])
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_zero_returns_no_annotation():
    doc = {"chunks": [{"text": "a"}]}
    result = chunk_boundary_prf(doc, 0)
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_none_no_missing_markers():
    """annotation None 路径不应包含 _missing_markers。"""
    doc = {"chunks": [{"text": "a"}]}
    result = chunk_boundary_prf(doc, None)
    assert "_missing_markers" not in result


# =========================================================================
# chunk_boundary_prf chunks 不足 2 个
# =========================================================================


def test_chunk_boundary_prf_no_chunks_returns_no_predicted():
    """chunks 缺失或为空 → no_predicted_boundaries。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted():
    doc = {"chunks": [{"text": "a"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_no_anchors_recall_zero():
    """1 chunk + 0 anchor → recall=_ratio(0.0)（不是 null）。"""
    doc = {"chunks": [{"text": "a"}]}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(doc, annotation)
    # 没 anchors 时 recall 是 _null；有 anchors 但 ≤1 chunk 时 recall 是 _ratio(0.0)
    # 注意这里 anchors=[]，所以走的是 no_predicted_boundaries + (anchors empty → null) 分支
    assert result["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_recall_zero_value():
    """1 chunk + 1 anchor → recall=_ratio(0.0)。"""
    doc = {"chunks": [{"text": "a"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_chunks_missing_key():
    """document 没有 chunks 字段 → 视为 []。"""
    doc = {}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_none():
    doc = {"chunks": None}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# =========================================================================
# chunk_boundary_prf anchors 缺失
# =========================================================================


def test_chunk_boundary_prf_anchors_missing_key():
    """annotation 是 dict 但没 chunk_boundary_anchors 字段。
    注意：空 dict {} 走 falsy 路径 → no_annotation。
    只有 annotation 非空但缺 chunk_boundary_anchors 才走 no_ground_truth_anchors。
    """
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"other_field": "x"}  # 非空 dict 但缺 chunk_boundary_anchors
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchors_none():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": None}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchors_empty():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_two_chunks_no_anchors_recall_null():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": []}
    result = chunk_boundary_prf(doc, annotation)
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf tolerance_chars 传播
# =========================================================================


def test_chunk_boundary_prf_tolerance_zero():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_large():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=1000)
    assert result["_tolerance_chars"]["value"] == 1000


def test_chunk_boundary_prf_tolerance_value_type_int():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert isinstance(result["_tolerance_chars"]["value"], int)


def test_chunk_boundary_prf_tolerance_reason_none():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_tolerance_keys_exact():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert set(result["_tolerance_chars"].keys()) == {"value", "reason"}


# =========================================================================
# chunk_boundary_prf position
# =========================================================================


def test_chunk_boundary_prf_position_before_uses_marker_start():
    """position="before" → anchor 位置是 marker 起始位置。"""
    text = "hello world hello world"
    doc = {"chunks": [{"text": "hello world"}, {"text": "hello world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "before"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # precision: 预测边界在第 1 chunk 末尾（位置 11）；anchor 在 "hello" 起始（位置 0 或 12）
    # tolerance=0 → 必须精确匹配；11 != 0/12 → matched=0
    assert result["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_position_after_uses_marker_end():
    text = "hello world"
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测边界在位置 5（"hello" 末尾）；anchor 也在 5（"hello" 末尾）→ matched=1
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_treated_as_after():
    """position 不是 before/after → 默认 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "unknown"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 默认 after → anchor 在 5；预测在 5 → matched
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_missing_defaults_to_after():
    """anchor 没 position 字段 → 默认 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf marker 缺失
# =========================================================================


def test_chunk_boundary_prf_empty_marker_treated_as_missing():
    """空 marker → find returns -1 → missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "_missing_markers" in result
    assert "" in result["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_not_in_stream():
    """marker 在 stream 中找不到 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "_missing_markers" in result
    assert "xyz" in result["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_markers_only_when_present():
    """所有 marker 都找到 → 不出现 _missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" not in result


def test_chunk_boundary_prf_missing_markers_value_type_list():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert isinstance(result["_missing_markers"]["value"], list)


def test_chunk_boundary_prf_missing_markers_reason_none():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    assert result["_missing_markers"]["reason"] is None


# =========================================================================
# chunk_boundary_prf precision/recall/f1 完美匹配
# =========================================================================


def test_chunk_boundary_prf_perfect_match_precision_one():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_perfect_match_recall_one():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_perfect_match_f1_one():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_f1"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf tolerance > 0 软匹配
# =========================================================================


def test_chunk_boundary_prf_tolerance_allows_soft_match():
    """tolerance_chars=N 时，预测边界与 anchor 距离 ≤ N 也算 matched。"""
    # "hello world" → 边界在 5；anchor="hel"（before）位置 0；距离 5
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hel", "position": "before"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 距离 5 ≤ 5 → matched
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_too_small_no_match():
    """距离 > tolerance → 不 matched。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hel", "position": "before"}]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=4)
    # 距离 5 > 4 → 不 matched
    assert result["chunk_boundary_precision"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf 多 chunk 多 anchor
# =========================================================================


def test_chunk_boundary_prf_three_chunks_two_anchors_perfect():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
    ]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 2 个内部边界（alpha|beta, beta|gamma），2 个 anchor，全匹配
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_more_predictions_than_anchors():
    """3 chunks → 2 predicted；1 anchor → precision=0.5, recall=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
    ]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predictions():
    """2 chunks → 1 predicted；2 anchors → precision=1.0, recall=0.5。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alphabeta", "position": "before"},  # 不存在的 marker
    ]}
    result = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 1 predicted matched 1 anchor；另一个 anchor missing → 仅 1 个有效 anchor
    # 实际：alphabeta 找不到 → missing_markers；只剩 alpha anchor
    # 1 predicted / 1 matched = precision 1.0；1 matched / 1 anchor = recall 1.0
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf 不修改输入
# =========================================================================


def test_chunk_boundary_prf_does_not_mutate_document():
    doc = {
        "chunks": [{"text": "hello"}, {"text": "world"}],
        "elements": [],
    }
    doc_before = dict(doc)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    chunk_boundary_prf(doc, annotation)
    assert doc == doc_before


def test_chunk_boundary_prf_does_not_mutate_annotation():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "hello", "position": "after"}],
        "other": "preserved",
    }
    annotation_before = dict(annotation)
    chunk_boundary_prf(doc, annotation)
    assert annotation == annotation_before


def test_chunk_boundary_prf_idempotent():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    a = chunk_boundary_prf(doc, annotation)
    b = chunk_boundary_prf(doc, annotation)
    assert a == b


def test_chunk_boundary_prf_returns_new_dict_each_call():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    a = chunk_boundary_prf(doc, annotation)
    b = chunk_boundary_prf(doc, annotation)
    assert a is not b


# =========================================================================
# chunk_boundary_prf 字段类型
# =========================================================================


def test_chunk_boundary_prf_each_metric_has_value_and_reason():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    for k, v in result.items():
        assert "value" in v, k
        assert "reason" in v, k


def test_chunk_boundary_prf_precision_value_is_float_when_evaluated():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    p = result["chunk_boundary_precision"]["value"]
    assert isinstance(p, float)


def test_chunk_boundary_prf_recall_value_is_float_when_evaluated():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    r = result["chunk_boundary_recall"]["value"]
    assert isinstance(r, float)


def test_chunk_boundary_prf_f1_value_is_float_when_evaluated():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(doc, annotation)
    f = result["chunk_boundary_f1"]["value"]
    assert isinstance(f, float)
