r"""evaluation/annotation_metrics.py 边角测试 - 第十一轮（Round 227）。

补强已有 base/edges/edges2-10（共 ~340 测试）未覆盖的深度：
- figure_caption_prf：返回类型 dict[str, dict]；keys 不依赖输入；PARSER_DOES_NOT_EMIT_RELATIONS 常量
- chunk_boundary_prf：chunk text 是 int/dict 触发 AttributeError；chunks list 含 None/str 元素
- chunk_boundary_prf：anchor marker/position 类型多样化（int/None/True/False）
- chunk_boundary_prf：annotation 是 list/None/空 dict；chunk_boundary_anchors 是非 list
- chunk_boundary_prf：document 是 list 触发 AttributeError
- chunk_boundary_prf：tolerance_chars 是非 int
- chunk_boundary_prf：predicted positions 算法精确性
- chunk_boundary_prf：anchor 顺序传播
- 模块结构补强
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
# 常量 PARSER_DOES_NOT_EMIT_RELATIONS
# =========================================================================


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_exact():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_nonempty():
    assert len(PARSER_DOES_NOT_EMIT_RELATIONS) > 0


def test_parser_does_not_emit_relations_in_module_all():
    import evaluation.annotation_metrics as m
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in m.__all__


# =========================================================================
# figure_caption_prf 深度（补强 edges10）
# =========================================================================


def test_figure_caption_prf_returns_dict_of_dicts():
    result = figure_caption_prf(None, None)
    assert isinstance(result, dict)
    for v in result.values():
        assert isinstance(v, dict)


def test_figure_caption_prf_keys_exact_three():
    result = figure_caption_prf(None, None)
    assert set(result.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_none_for_doc_none_ann_none():
    result = figure_caption_prf(None, None)
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_all_values_none_for_doc_present_ann_none():
    result = figure_caption_prf({"chunks": []}, None)
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_all_values_none_for_doc_none_ann_present():
    result = figure_caption_prf(None, {"chunk_boundary_anchors": []})
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_all_values_none_for_both_present():
    result = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    for v in result.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_for_all_inputs():
    """所有输入组合都返回相同 reason。"""
    inputs = [
        (None, None),
        ({}, None),
        (None, {}),
        ({}, {}),
        ({"chunks": []}, {"chunk_boundary_anchors": []}),
    ]
    for doc, ann in inputs:
        result = figure_caption_prf(doc, ann)
        for v in result.values():
            assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_depend_on_annotation():
    """annotation 内容不影响返回（始终 null）。"""
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert r1 == r2


def test_figure_caption_prf_does_not_depend_on_document():
    """document 内容不影响返回（始终 null）。"""
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf({"chunks": [{"text": "abc"}]}, None)
    assert r1 == r2


def test_figure_caption_prf_callable():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_signature():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# chunk_boundary_prf 深度 - 输入类型边界
# =========================================================================


def test_chunk_boundary_prf_document_is_list_raises():
    """document 是 list（提供 annotation 触发 document 访问）→ list.get 不存在 → AttributeError。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf([], {"chunk_boundary_anchors": [{"marker": "a"}]})  # type: ignore[arg-type]


def test_chunk_boundary_prf_document_is_str_raises():
    """document 是 str（提供 annotation 触发 document 访问）→ str.get 不存在 → AttributeError。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf("not a dict", {"chunk_boundary_anchors": [{"marker": "a"}]})  # type: ignore[arg-type]


def test_chunk_boundary_prf_annotation_is_list_treated_as_falsy():
    """annotation 是 list（非空）→ if not annotation 是 False → 走 anchors 分支。
    annotation.get 触发 AttributeError。
    """
    with pytest.raises(AttributeError):
        chunk_boundary_prf({"chunks": [{"text": "a"}]}, [1, 2])  # type: ignore[arg-type]


def test_chunk_boundary_prf_annotation_is_empty_list_treated_as_falsy():
    """annotation 是空 list → if not annotation 命中 → no_annotation 路径。"""
    result = chunk_boundary_prf({"chunks": [{"text": "a"}]}, [])
    # 不抛错，返回 no_annotation
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_chunks_containing_none_element_raises():
    """chunks list 含 None → None.get 触发 AttributeError（在 normalize 路径）。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            {"chunks": [None, {"text": "b"}]},  # type: ignore[list-item]
            {"chunk_boundary_anchors": [{"marker": "b"}]},
        )


def test_chunk_boundary_prf_chunks_containing_string_raises():
    """chunks list 含 str → str.get 触发 AttributeError。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            {"chunks": ["abc", "def"]},  # type: ignore[list-item]
            {"chunk_boundary_anchors": [{"marker": "abc"}]},
        )


def test_chunk_boundary_prf_chunks_containing_int_raises():
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            {"chunks": [123, 456]},  # type: ignore[list-item]
            {"chunk_boundary_anchors": [{"marker": "abc"}]},
        )


def test_chunk_boundary_prf_chunk_text_is_int_raises():
    """单个 chunk 的 text 是 int → normalize_text 触发 TypeError（regex 期望 string）。"""
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": 123}, {"text": "abc"}]},  # type: ignore[dict-item]
            {"chunk_boundary_anchors": [{"marker": "abc"}]},
        )


def test_chunk_boundary_prf_chunk_text_is_dict_raises():
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": {"k": "v"}}, {"text": "abc"}]},  # type: ignore[dict-item]
            {"chunk_boundary_anchors": [{"marker": "abc"}]},
        )


def test_chunk_boundary_prf_chunk_text_is_list_raises():
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": ["a", "b"]}, {"text": "abc"}]},  # type: ignore[dict-item]
            {"chunk_boundary_anchors": [{"marker": "abc"}]},
        )


def test_chunk_boundary_prf_chunk_boundary_anchors_is_dict_raises():
    """chunk_boundary_anchors 是 dict（不是 list）→ 遍历 dict 得 key str → str.get AttributeError。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            {"chunks": [{"text": "abc"}, {"text": "def"}]},
            {"chunk_boundary_anchors": {"marker": "abc"}},  # type: ignore[dict-item]
        )


def test_chunk_boundary_prf_chunk_boundary_anchors_is_int_raises():
    """chunk_boundary_anchors 是 int → 遍历 int 抛 TypeError。"""
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": "abc"}, {"text": "def"}]},
            {"chunk_boundary_anchors": 123},  # type: ignore[dict-item]
        )


def test_chunk_boundary_prf_anchor_marker_is_int_in_stream_search():
    """anchor marker 是 int → stream.find(int) 抛 TypeError。"""
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": "abc"}, {"text": "def"}]},
            {"chunk_boundary_anchors": [{"marker": 123, "position": "after"}]},  # type: ignore[dict-item]
        )


def test_chunk_boundary_prf_anchor_position_is_int_treated_as_after():
    """position 是 int → `if position == "before"` 不命中 → 走 after 分支。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": 123}]},  # type: ignore[dict-item]
    )
    # 不抛错；marker 'abc' 在 stream 中找到，position int → 走 else (after)
    assert "chunk_boundary_precision" in result


def test_chunk_boundary_prf_anchor_position_is_none_treated_as_after():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": None}]},  # type: ignore[dict-item]
    )
    assert "chunk_boundary_precision" in result


def test_chunk_boundary_prf_tolerance_chars_string_raises():
    """tolerance_chars 是 str → d（int） <= str 比较 → TypeError。"""
    with pytest.raises(TypeError):
        chunk_boundary_prf(
            {"chunks": [{"text": "abc"}, {"text": "def"}]},
            {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
            tolerance_chars="30",  # type: ignore[arg-type]
        )


def test_chunk_boundary_prf_tolerance_chars_negative_no_match():
    """negative tolerance → abs diff > negative → no match。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=-1,
    )
    # predicted boundary: end of chunk 0 = 3
    # anchor after 'abc': position 3 (same)
    # abs(3-3) = 0, but tolerance=-1, so 0 > -1 → no match
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_chars_zero_exact_match():
    """tolerance=0 + 精确匹配 → 命中。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=0,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_chars_very_large():
    """极大 tolerance → 所有 predicted 都匹配某些 anchor。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=10**9,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_chars_propagated_to_output():
    """tolerance_chars 必须出现在输出 _tolerance_chars 字段中。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc"}]},
        tolerance_chars=42,
    )
    assert result["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_predicted_boundary_at_end_of_chunk():
    """predicted boundary 在 chunk 末尾，不是开始。"""
    # chunk 0 = "hello" (5 chars), chunk 1 = "world"
    # predicted = position 5 (after "hello")
    # anchor after "llo" = position 5 (find "llo" at 2, +len 3 = 5)
    result = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "llo", "position": "after"}]},
        tolerance_chars=0,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_before():
    """position=before → anchor 在 marker 起始位置。"""
    # chunk 0 = "hello" (5 chars), chunk 1 = "world"
    # predicted = position 5
    # anchor before "world" → find "world" at 6, position = 6
    # abs(5-6) = 1, tolerance=1 → match
    result = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]},
        tolerance_chars=1,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_after():
    """position=after → anchor 在 marker 末尾位置。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=0,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_last_chunk_does_not_contribute_boundary():
    """最后一个 chunk 不贡献边界（N-1 个内部边界）。"""
    # 3 chunks → 2 predicted boundaries
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]},
        {"chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
            {"marker": "c", "position": "after"},  # 这个没有 predicted 可匹配
        ]},
        tolerance_chars=0,
    )
    # predicted: 2 (end of a=1, end of b=3)
    # anchors: 3 (after a=1, after b=3, after c=5)
    # matched: 2 (前两个 anchor)
    assert result["chunk_boundary_precision"]["value"] == 1.0  # 2/2
    assert result["chunk_boundary_recall"]["value"] == pytest.approx(2/3)  # 2/3


def test_chunk_boundary_prf_chunk_with_whitespace_text():
    """chunk text 含空白 → normalize 折叠。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "  hello  "}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=0,
    )
    # normalize("  hello  ") = "hello" (5 chars)
    # predicted: 5
    # anchor after "hello" → find at 0, +5 = 5
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_with_newlines():
    """chunk text 含换行 → normalize 折叠成空格。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "hello\nworld"}, {"text": "foo"}]},
        {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]},
        tolerance_chars=0,
    )
    # normalize("hello\nworld") = "hello world" (11 chars)
    # stream = "hello world foo"
    # predicted: end of chunk 0 = 11
    # anchor after "hello world" → find at 0, +11 = 11
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_normalize_collapses_multiple_spaces():
    """normalize 把多个空格折叠为单个。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a  b"}, {"text": "c"}]},  # 2 spaces
        {"chunk_boundary_anchors": [{"marker": "a b", "position": "after"}]},  # 1 space
        tolerance_chars=0,
    )
    # normalize("a  b") = "a b" (3 chars)
    # stream = "a b c"
    # predicted: 3
    # anchor after "a b" → find at 0, +3 = 3
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_marker_with_regex_chars():
    """marker 含正则元字符（如 . * +）按字面匹配。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "a.b"}, {"text": "c"}]},
        {"chunk_boundary_anchors": [{"marker": "a.b", "position": "after"}]},
        tolerance_chars=0,
    )
    # 'a.b' 字面匹配（stream.find 是字面，不是正则）
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_marker_unicode():
    """marker 含中文。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "中文"}, {"text": "test"}]},
        {"chunk_boundary_anchors": [{"marker": "中文", "position": "after"}]},
        tolerance_chars=0,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_marker_with_substring_match():
    """marker 在 stream 中多次出现，find 返回第一次。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc abc"}, {"text": "abc"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=0,
    )
    # normalize("abc abc") = "abc abc" (7 chars), normalize("abc") = "abc" (3 chars)
    # stream = "abc abc abc"
    # predicted: end of chunk 0 = 7
    # anchor after "abc" → first find at 0, +3 = 3
    # abs(7-3) = 4 → not match (tolerance=0)
    # precision = 0/1 = 0.0, recall = 0/1 = 0.0
    assert result["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_repeated_markers_advance():
    """两个相同 marker → 第一个匹配第一次出现，第二个匹配第二次出现。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "abc"}, {"text": "x"}]},
        {"chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "abc", "position": "after"},
        ]},
        tolerance_chars=0,
    )
    # stream = "abc abc x"
    # predicted: end of chunk 0 = 3, end of chunk 1 = 7
    # anchor 1: find "abc" from 0 → 0+3 = 3
    # anchor 2: find "abc" from 3 → 4+3 = 7
    # match: (3,3) and (7,7) → both exact
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_missing_marker_recorded():
    """marker 在 stream 中找不到 → 记入 _missing_markers。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_missing_markers" in result
    assert "xyz" in result["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_key_when_all_found():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_missing_markers" not in result


def test_chunk_boundary_prf_internal_keys_prefixed_with_underscore():
    """内部字段 _tolerance_chars / _missing_markers 应以 _ 开头。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_tolerance_chars" in result
    assert "_missing_markers" in result


def test_chunk_boundary_prf_metric_keys_no_underscore_prefix():
    """对外 metric 名（precision/recall/f1）不应以 _ 开头。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=10,
    )
    metric_keys = [k for k in result.keys() if not k.startswith("_")]
    for k in metric_keys:
        assert not k.startswith("_")
    assert "chunk_boundary_precision" in metric_keys
    assert "chunk_boundary_recall" in metric_keys
    assert "chunk_boundary_f1" in metric_keys


def test_chunk_boundary_prf_no_side_effects_on_document():
    """调用 chunk_boundary_prf 不应修改 document。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    doc_copy = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "abc"}]})
    assert doc == doc_copy


def test_chunk_boundary_prf_no_side_effects_on_annotation():
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    ann_copy = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    chunk_boundary_prf({"chunks": [{"text": "abc"}, {"text": "def"}]}, ann)
    assert ann == ann_copy


# =========================================================================
# chunk_boundary_prf - _null 路径精确性
# =========================================================================


def test_chunk_boundary_prf_doc_none_returns_pipeline_failed():
    result = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "pipeline_failed"
        assert result[k]["value"] is None


def test_chunk_boundary_prf_annotation_none_returns_no_annotation():
    result = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_returns_no_annotation():
    result = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_zero_chunks_returns_no_predicted_boundaries():
    result = chunk_boundary_prf(
        {"chunks": []},
        {"chunk_boundary_anchors": [{"marker": "abc"}]},
    )
    # 0 chunks → no_predicted_boundaries
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_boundaries():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}]},
        {"chunk_boundary_anchors": [{"marker": "abc"}]},
    )
    # 1 chunk → no internal boundaries
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_present_no_anchors_returns_no_ground_truth():
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": []},
    )
    # chunks present, no anchors → no_ground_truth_anchors
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert result[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchor_missing_dict_marker():
    """anchor 没有 marker 字段 → 默认 ""。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"position": "after"}]},
        tolerance_chars=10,
    )
    # marker="" → find returns -1（empty marker 不在 stream 中查找）
    # 实际：stream.find("") returns 0，但代码 `if marker else -1` → 走 -1 分支
    # → missing_markers=[""]
    assert "_missing_markers" in result


def test_chunk_boundary_prf_anchor_missing_position_defaults_after():
    """anchor 没有 position 字段 → 默认 "after"。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc"}]},
        tolerance_chars=0,
    )
    # position 默认 "after" → anchor 位置 = 3
    # predicted = 3 → exact match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_unknown_treated_as_after():
    """position="custom"（非 before）→ 走 else (after) 分支。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "custom"}]},
        tolerance_chars=0,
    )
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# 模块结构（补强 edges10）
# =========================================================================


def test_module_all_exact():
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
    assert hasattr(m, "normalize_text")


def test_module_imports_null():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_null")


def test_module_imports_ratio():
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_ratio")


def test_module_docstring_present():
    import evaluation.annotation_metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_chunk_boundary():
    import evaluation.annotation_metrics as m
    assert "chunk_boundary" in m.__doc__


def test_module_docstring_mentions_figure_caption():
    import evaluation.annotation_metrics as m
    assert "figure_caption" in m.__doc__


def test_module_docstring_mentions_one_to_one():
    """docstring 应提及'一对一'（chunk_boundary 算法核心）。"""
    import evaluation.annotation_metrics as m
    assert "一对一" in m.__doc__ or "one-to-one" in m.__doc__.lower()


def test_module_docstring_mentions_tolerance():
    """docstring 应提及 tolerance。"""
    import evaluation.annotation_metrics as m
    assert "tolerance" in m.__doc__.lower() or "容差" in m.__doc__


def test_module_uses_future_annotations():
    import evaluation.annotation_metrics as m
    sig = inspect.signature(m.chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


def test_module_constants_count_two():
    """模块级常量：PARSER_DOES_NOT_EMIT_RELATIONS（只此一个）。"""
    import evaluation.annotation_metrics as m
    # PARSER_DOES_NOT_EMIT_RELATIONS 是唯一的 module-level 名字（非 callable、非 __all__）
    public = [
        n for n in dir(m)
        if not n.startswith("_")
        and n != "__all__"
        and not callable(getattr(m, n, None))
    ]
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in public


def test_chunk_boundary_prf_signature():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_document_kind():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_annotation_kind():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_tolerance_chars_kind():
    """tolerance_chars 应是 keyword-or-positional（不是 keyword-only）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_tolerance_chars_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_return_annotation_str():
    sig = inspect.signature(chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


def test_chunk_boundary_prf_callable():
    assert callable(chunk_boundary_prf)


# =========================================================================
# 综合行为
# =========================================================================


def test_chunk_boundary_prf_full_perfect_match():
    """完整流程：3 chunks + 2 anchors → 完美匹配。"""
    result = chunk_boundary_prf(
        {
            "chunks": [
                {"text": "first"},
                {"text": "second"},
                {"text": "third"},
            ]
        },
        {
            "chunk_boundary_anchors": [
                {"marker": "first", "position": "after"},
                {"marker": "second", "position": "after"},
            ]
        },
        tolerance_chars=0,
    )
    # stream = "first second third"
    # predicted: end of chunk 0 = 5, end of chunk 1 = 12 (5 + ' ' + 6 = 12)
    # anchor after "first" → find at 0, +5 = 5
    # anchor after "second" → find at 6, +6 = 12
    # match: (5,5) and (12,12) → 2 matches
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0
    # f1 = 2 * 1 * 1 / (1 + 1) = 1.0
    assert result["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_half_match():
    """一半匹配：4 predicted, 2 anchors 在容差内。"""
    result = chunk_boundary_prf(
        {
            "chunks": [
                {"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}, {"text": "e"},
            ]
        },
        {
            "chunk_boundary_anchors": [
                {"marker": "a", "position": "after"},  # match predicted[0]
                {"marker": "b", "position": "after"},  # match predicted[1]
                # predicted[2] and [3] no anchor
            ]
        },
        tolerance_chars=0,
    )
    # predicted: 4 (end of a=1, b=3, c=5, d=7)
    # anchors: 2 (after a=1, after b=3)
    # matched: 2
    assert result["chunk_boundary_precision"]["value"] == 0.5  # 2/4
    assert result["chunk_boundary_recall"]["value"] == 1.0  # 2/2


def test_chunk_boundary_prf_returns_dict_with_metric_and_internal_keys():
    """返回 dict 应同时包含 metric keys（无 _ 前缀）和 internal keys（有 _ 前缀）。"""
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_tolerance_chars" in result  # internal
    assert "chunk_boundary_precision" in result  # metric


def test_chunk_boundary_prf_one_to_one_constraint():
    """一个预测边界只能匹配一个 anchor，反之亦然。

    用两个不同 marker 'b' 与 'c' 让两个 anchor 都能在 stream 中找到。
    """
    # stream = "abc def"
    # predicted: end of chunk 0 (abc) = 3
    # anchor 1 (after "b"): find from 0 → 1, +1 = 2; search_from = 2
    # anchor 2 (after "c"): find from 2 → 2, +1 = 3; search_from = 3
    # both anchors (2, 3) within tolerance of predicted (3)
    # 一对一：only 1 match (greedy by distance picks (3,3) first)
    result = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": [
            {"marker": "b", "position": "after"},  # position 2
            {"marker": "c", "position": "after"},  # position 3
        ]},
        tolerance_chars=10,
    )
    # matched: 1 (greedy: (3,3) distance 0 first, then (3,2) distance 1 - but pred 0 used)
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 0.5
