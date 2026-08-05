r"""evaluation/annotation_metrics.py 边角测试 - 第九轮（Round 217）。

补强已有 base/edges/edges2-8（共 ~614 测试）未覆盖的深度：
- figure_caption_prf：reason 一致性 / key 命名 / callable
- chunk_boundary_prf：document={} 但 annotation={} 走 no_annotation（document 不是 None）
- chunk_boundary_prf：document 是 dict 但 chunks 缺字段
- chunk_boundary_prf：annotation 是 dict 但缺 chunk_boundary_anchors
- chunk_boundary_prf：anchor 缺 marker / position 字段
- chunk_boundary_prf：anchor position="before" 计算 find_pos
- chunk_boundary_prf：多个 anchor 重复 marker（推进 search_from）
- chunk_boundary_prf：tolerance_chars=0 边界
- chunk_boundary_prf：predicted/gt_positions 完全无 overlap
- chunk_boundary_prf：f1 = 0 当 p=r=0
- chunk_boundary_prf：marker 找不到（missing_markers 写入）
- chunk_boundary_prf：返回 dict 顶层 keys
- 模块结构 / __all__ / imports / 常量
- 综合行为
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


# =========================================================================
# figure_caption_prf 深度
# =========================================================================


def test_figure_caption_prf_returns_three_keys_when_doc_none():
    result = figure_caption_prf(None, None)
    assert set(result.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_returns_three_keys_when_doc_present():
    result = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    assert set(result.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_reasons_consistent():
    result = figure_caption_prf({"chunks": []}, None)
    for k, v in result.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_all_values_none():
    result = figure_caption_prf({"chunks": []}, None)
    for k, v in result.items():
        assert v["value"] is None


def test_figure_caption_prf_callable():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_signature_two_params():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters)
    assert params == ["document", "annotation"]


def test_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_return_annotation_str():
    sig = inspect.signature(figure_caption_prf)
    assert isinstance(sig.return_annotation, str)


def test_figure_caption_prf_ignores_annotation_content():
    """不论 annotation 含什么，figure_caption_* 总是 null。"""
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf({"chunks": []}, {"any": "thing"})
    assert r1 == r2


def test_figure_caption_prf_with_partial_document():
    """document 可以是任意 dict（含空 dict）。"""
    result = figure_caption_prf({}, {})
    assert set(result.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    }


# =========================================================================
# chunk_boundary_prf document / annotation 形态深度
# =========================================================================


def test_chunk_boundary_prf_document_empty_dict_no_annotation():
    """document={} 但不是 None → 走 annotation falsy 分支。"""
    result = chunk_boundary_prf({}, {})
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_present_annotation_is_none():
    result = chunk_boundary_prf({"chunks": []}, None)
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_present_annotation_empty_dict():
    result = chunk_boundary_prf({"chunks": []}, {})
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_present_annotation_is_empty_list():
    """annotation=[] → falsy → no_annotation。"""
    result = chunk_boundary_prf({"chunks": []}, [])  # type: ignore[arg-type]
    assert result["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_present_chunks_missing_field():
    """document 不含 chunks → chunks=[] → len<2 → no_predicted_boundaries。"""
    result = chunk_boundary_prf(
        {},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_present_chunks_zero():
    result = chunk_boundary_prf(
        {"chunks": []},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall 因为有 anchors 但无 predicted → ratio 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_annotation_present_chunks_one():
    """只有 1 个 chunk → 没有内部边界。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_missing_chunk_boundary_anchors():
    """annotation 是非空 dict 但缺 chunk_boundary_anchors 键 → anchors=[]"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"other_field": "value"},
    )
    # anchors=[] → 走 no_ground_truth_anchors 分支
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunk_boundary_anchors_is_none():
    """chunk_boundary_anchors: None → or [] → []"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": None},
    )
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunk_boundary_anchors_empty_list():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    assert result["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf tolerance_chars 深度
# =========================================================================


def test_chunk_boundary_prf_tolerance_chars_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_tolerance_chars_kind():
    """tolerance_chars 没有 * 分隔 → POSITIONAL_OR_KEYWORD（不是 KEYWORD_ONLY）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_tolerance_chars_propagated_when_doc_none():
    result = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert result["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_tolerance_chars_propagated_when_no_annotation():
    result = chunk_boundary_prf({"chunks": []}, None, tolerance_chars=42)
    assert result["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_propagated_when_no_chunks():
    result = chunk_boundary_prf(
        {}, {"chunk_boundary_anchors": [{"marker": "x"}]},
        tolerance_chars=7,
    )
    assert result["_tolerance_chars"]["value"] == 7


def test_chunk_boundary_prf_tolerance_chars_propagated_when_no_anchors():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
        tolerance_chars=11,
    )
    assert result["_tolerance_chars"]["value"] == 11


def test_chunk_boundary_prf_tolerance_chars_zero():
    """tolerance_chars=0 → 仍要写入 _tolerance_chars 字段。"""
    result = chunk_boundary_prf(None, None, tolerance_chars=0)
    assert result["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_chars_negative():
    """tolerance_chars=-1 → 等价于无任何匹配（|d|<=-1 永远 False）。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
        tolerance_chars=-1,
    )
    assert result["_tolerance_chars"]["value"] == -1
    # 无匹配 → matched=0, num_pred=1, num_gt=1 → p=0, r=0
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf 正常路径
# =========================================================================


def test_chunk_boundary_prf_perfect_match_after_marker():
    """两个 chunks，一个 anchor 在第一个 chunk 末尾 → perfect match。"""
    document = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_perfect_match_before_marker():
    """两个 chunks，anchor position=before，marker=world（第二个 chunk）。"""
    document = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_inside_chunk_text():
    """marker 是 chunk 文本的一部分。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    # predicted: end of "abc" in "abc def" stream → 3
    # anchor: "c" position=after → find "c" at index 2, +1 = 3 → 完美匹配
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_match_within_tolerance():
    """predicted 在 anchor 的 tolerance_chars 内 → match。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # anchor 远在 stream 末尾，tolerance_chars 大
    annotation = {"chunk_boundary_anchors": [{"marker": "def", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=100)
    # predicted=3 (end of abc), anchor: find "def" at 4, +3 = 7 → |3-7|=4 <= 100 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_when_distance_exceeds_tolerance():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "def", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=2)
    # |3-7|=4 > 2 → no match
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_f1_zero_when_p_r_zero():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "def", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # p=0, r=0 → denom=0 → f1=0
    assert result["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_half_when_half_match():
    """一半 pred 匹配 → p=0.5, r=1.0 → f1=2*0.5*1.0/(1.5)≈0.667。"""
    document = {"chunks": [
        {"text": "abc"}, {"text": "def"}, {"text": "ghi"},
    ]}
    # 2 predicted boundaries (after abc, after def)
    # 1 anchor after abc → match 1, p=1/2=0.5, r=1/1=1.0
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 1.0
    # f1 = 2 * 0.5 * 1.0 / 1.5 ≈ 0.666...
    assert abs(result["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-9


# =========================================================================
# chunk_boundary_prf anchor 字段缺失
# =========================================================================


def test_chunk_boundary_prf_anchor_missing_marker_uses_empty_string():
    """anchor 无 marker 键 → marker='' → find 返回 -1 → missing_markers 增加。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    # marker='' → find_pos=-1 → missing_markers=['']
    # gt_positions 空 → recall null with no_ground_truth_anchors_in_stream
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    # _missing_markers 含空字符串
    assert result["_missing_markers"]["value"] == [""]


def test_chunk_boundary_prf_anchor_missing_position_defaults_after():
    """anchor 无 position → 默认 'after'。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    result = chunk_boundary_prf(document, annotation)
    # position=after → find_pos=0, end=3 → 与 predicted end=3 完美匹配
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_unknown_value_treated_as_after():
    """position 不是 before/after → 默认走 else（after）分支。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "weird"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # 走 else 分支（after 语义）
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_not_dict():
    """anchor 不是 dict（如 None 或 str）→ .get 抛 AttributeError → 应不崩溃。

    行为记录：当前实现假设 anchor 是 dict。
    """
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [None]}  # type: ignore[list-item]
    with pytest.raises(AttributeError):
        chunk_boundary_prf(document, annotation)


# =========================================================================
# chunk_boundary_prf 多 anchor
# =========================================================================


def test_chunk_boundary_prf_multiple_anchors_distinct_markers():
    document = {"chunks": [
        {"text": "abc"}, {"text": "def"}, {"text": "ghi"},
    ]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "def", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # 2 predicted, 2 anchors, both perfect match
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_markers_advance_search_from():
    """两个相同 marker 在 stream 中出现两次 → 第二个 anchor 应找到第二次出现。"""
    document = {"chunks": [
        {"text": "abc"}, {"text": "abc"}, {"text": "xyz"},
    ]}
    # stream = "abc abc xyz"
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},  # 第一次: pos 0+3=3
        {"marker": "abc", "position": "after"},  # 第二次: search_from=3, find at 4, +3=7
    ]}
    result = chunk_boundary_prf(document, annotation)
    # predicted boundaries: end of chunk 0 (3), end of chunk 1 (7)
    # anchors: 3 and 7 → 完美匹配
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_marker_not_in_stream_recorded():
    """marker 在 stream 中找不到 → 加入 _missing_markers。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "zzz", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" in result
    assert "zzz" in result["_missing_markers"]["value"]
    # gt_positions 空 → recall null
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_no_missing_markers_key_when_all_found():
    """所有 marker 都找到 → 不写 _missing_markers 键。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" not in result


# =========================================================================
# chunk_boundary_prf 返回 dict 结构
# =========================================================================


def test_chunk_boundary_prf_top_keys_normal_path():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert set(result.keys()) == expected


def test_chunk_boundary_prf_top_keys_with_missing_markers():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars", "_missing_markers",
    }
    assert set(result.keys()) == expected


def test_chunk_boundary_prf_top_keys_pipeline_failed():
    result = chunk_boundary_prf(None, None)
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert set(result.keys()) == expected


def test_chunk_boundary_prf_top_keys_no_annotation():
    result = chunk_boundary_prf({"chunks": []}, None)
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert set(result.keys()) == expected


def test_chunk_boundary_prf_top_keys_no_predicted():
    result = chunk_boundary_prf(
        {}, {"chunk_boundary_anchors": [{"marker": "x"}]},
    )
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert set(result.keys()) == expected


def test_chunk_boundary_prf_top_keys_no_ground_truth():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    expected = {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert set(result.keys()) == expected


# =========================================================================
# chunk_boundary_prf 边界情况
# =========================================================================


def test_chunk_boundary_prf_chunk_text_none_treated_as_empty():
    """chunk.text=None → c.get('text') or '' → ''。"""
    document = {"chunks": [{"text": None}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation)
    # stream = " abc"（normalize 后）→ predicted: end of "" (first chunk) = 0
    # anchor "abc" position=before → find "abc" at 1 → gt_position=1
    # |0-1|=1 <= 30 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_missing_text_field():
    """chunk 没有 text 字段 → c.get('text') → None → or '' → ''"""
    document = {"chunks": [{}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_with_extra_whitespace_in_text():
    """chunk text 含多余空白 → normalize 后等效。"""
    document = {"chunks": [{"text": "  abc  "}, {"text": "  def  "}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    # normalize 后 "abc" / "def" → stream "abc def"
    # predicted: end of "abc" = 3
    # anchor "abc" position=after → 0+3=3 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunks_not_a_list_raises():
    """document['chunks'] 是 str → truthy → 进主路径 → str 元素无 .get → AttributeError。"""
    document = {"chunks": "not a list"}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(document, annotation)  # type: ignore[arg-type]


def test_chunk_boundary_prf_zero_chunks_with_annotation():
    """chunks=[] + anchors 非空 → no_predicted_boundaries, recall=0.0。"""
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_with_annotation():
    document = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# =========================================================================
# chunk_boundary_prf 三个 f1 / p / r 字段命名
# =========================================================================


def test_chunk_boundary_prf_metric_names_exact():
    """返回 dict（去除内部键）的 metric 名精确集合。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    metric_keys = {k for k in result.keys() if not k.startswith("_")}
    assert metric_keys == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    }


def test_chunk_boundary_prf_internal_keys_prefixed_with_underscore():
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    internal_keys = {k for k in result.keys() if k.startswith("_")}
    assert "_tolerance_chars" in internal_keys


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


def test_module_all_length_three():
    import evaluation.annotation_metrics as m
    assert len(m.__all__) == 3


def test_module_imports_counter():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Counter")


def test_module_imports_any():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Any")


def test_module_imports_normalize_text():
    import evaluation.annotation_metrics as m
    assert callable(m.normalize_text)


def test_module_imports_null_ratio_from_metrics():
    import evaluation.annotation_metrics as m
    assert callable(m._null)
    assert callable(m._ratio)


def test_module_parser_does_not_emit_relations_constant():
    import evaluation.annotation_metrics as m
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_parser_does_not_emit_relations_is_str():
    import evaluation.annotation_metrics as m
    assert isinstance(m.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_docstring_present():
    import evaluation.annotation_metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 50


def test_module_docstring_mentions_constraints():
    import evaluation.annotation_metrics as m
    doc = m.__doc__
    assert "figure_caption" in doc or "caption" in doc
    assert "chunk_boundary" in doc or "boundary" in doc
    assert "tolerance" in doc.lower()


def test_module_uses_future_annotations():
    import evaluation.annotation_metrics as m
    sig = inspect.signature(m.chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


def test_module_no_silence_unused():
    import evaluation.annotation_metrics as m
    assert not hasattr(m, "_silence_unused_import")


def test_chunk_boundary_prf_callable():
    assert callable(chunk_boundary_prf)


def test_chunk_boundary_prf_three_params():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters)
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_document_param_kind():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_annotation_param_kind():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
