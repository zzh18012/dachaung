r"""evaluation/annotation_metrics.py 边角测试 - 第十轮（Round 222）。

补强已有 base/edges/edges2-9（共 ~688 测试）未覆盖的深度：
- chunk_boundary_prf：完整大样本 / 容差配合边界
- chunk_boundary_prf：多个 anchor 部分缺失
- chunk_boundary_prf：tolerance_chars 边界值（1）
- chunk_boundary_prf：missing_markers 多个
- chunk_boundary_prf：anchor position 边界情况
- chunk_boundary_prf：normalize_text 影响
- figure_caption_prf：document / annotation 多种类型
- 模块结构 / imports / 常量
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
# figure_caption_prf 深度（补强 edges9）
# =========================================================================


def test_figure_caption_prf_returns_same_for_all_inputs():
    """无论输入如何，figure_caption_prf 总返回相同结果。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        (None, {"any": "thing"}),
        ({"chunks": [{"text": "x"}]}, {"figure_caption_anchors": [{"marker": "x"}]}),
    ]
    results = [figure_caption_prf(doc, ann) for doc, ann in inputs]
    # 所有结果应相等（固定 null）
    for r in results:
        assert r == results[0]


def test_figure_caption_prf_keys_alphabetical_order_irrelevant():
    """keys 顺序固定（不依赖输入）。"""
    r = figure_caption_prf(None, None)
    keys = list(r.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_metric_dict_keys_exact():
    r = figure_caption_prf(None, None)
    for k, v in r.items():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_reason_value():
    """所有 reason 都是 PARSER_DOES_NOT_EMIT_RELATIONS 常量。"""
    r = figure_caption_prf({"chunks": []}, None)
    for k, v in r.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# chunk_boundary_prf 大样本 / 边界
# =========================================================================


def test_chunk_boundary_prf_many_chunks_one_anchor_at_end():
    """10 chunks，anchor 在最后 chunk 之前 → perfect match（最后一个 anchor）。"""
    document = {"chunks": [{"text": f"chunk{i}"} for i in range(10)]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "chunk8", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # predicted boundaries 9 个；anchor 1 个 → recall 1/1, precision 1/9
    assert result["chunk_boundary_recall"]["value"] == 1.0
    assert result["chunk_boundary_precision"]["value"] == 1 / 9


def test_chunk_boundary_prf_many_anchors_one_chunk_no_predicted():
    """1 chunk + 多 anchor → no_predicted_boundaries。"""
    document = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "abc", "position": "before"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_anchors_one_missing():
    """两个 anchor，一个 marker 找不到 → missing_markers 记录该 marker。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "zzz", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" in result
    assert "zzz" in result["_missing_markers"]["value"]
    # 只有 1 个有效 anchor → recall 1/1
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_two_anchors_both_missing():
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "zzz1", "position": "after"},
        {"marker": "zzz2", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" in result
    missing = result["_missing_markers"]["value"]
    assert "zzz1" in missing
    assert "zzz2" in missing
    # gt_positions 空 → recall null
    assert result["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_tolerance_chars_one():
    """tolerance_chars=1 → 仅精确±1 容差。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"，predicted boundary at 3
    # anchor "def" position=before → find "def" at 4 → gt=4 → |3-4|=1 <= 1 → match
    annotation = {"chunk_boundary_anchors": [
        {"marker": "def", "position": "before"},
    ]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=1)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_chars_zero_no_match():
    """tolerance_chars=0 + 距离 1 → 不 match。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "def", "position": "before"},
    ]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # |3-4|=1 > 0 → no match
    assert result["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_normalize_collapses_whitespace():
    """chunk text 含多余空白 → normalize 后匹配。"""
    document = {"chunks": [
        {"text": "  abc  "},
        {"text": "  def  "},
    ]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # stream = "abc def"
    # predicted: end of "abc" = 3
    # anchor "abc" position=after → 0+3=3 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_normalize_preserves_punctuation():
    """标点不被 normalize 改变。"""
    document = {"chunks": [
        {"text": "hello."},
        {"text": "world!"},
    ]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "hello.", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_unicode_text():
    """中文 chunk text。"""
    document = {"chunks": [{"text": "中文"}, {"text": "测试"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "中文", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_chunk_text():
    """两个 chunks 文本相同 → predicted boundary 应正确。"""
    document = {"chunks": [{"text": "abc"}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # stream = "abc abc"
    # predicted boundaries: end of chunk 0 = 3 (in stream)
    # anchor: find "abc" at 0, +3 = 3 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_chunk_text_two_anchors():
    """两个 chunks 文本相同 + 两个 anchor（相同 marker）。

    只有 1 个 predicted boundary（chunk 0 末尾），但 anchor 找到两次出现（pos 3 和 pos 7）。
    num_pred=1, num_gt=2 → 1 个匹配。
    precision = 1/1 = 1.0
    recall = 1/2 = 0.5
    """
    document = {"chunks": [{"text": "abc"}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},  # first: pos 3
        {"marker": "abc", "position": "after"},  # second: search_from=3, find at 4, +3=7
    ]}
    result = chunk_boundary_prf(document, annotation)
    # predicted: end of chunk 0 = 3 (chunk 1 是 last 不算)
    # anchors: 3, 7 → 只能匹配 1 个
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 0.5


# =========================================================================
# chunk_boundary_prf anchor position 边界
# =========================================================================


def test_chunk_boundary_prf_position_before_with_empty_marker():
    """marker='' + position=before → find_pos=-1（marker 为空）→ missing_markers。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "before"}]}
    result = chunk_boundary_prf(document, annotation)
    assert "_missing_markers" in result
    assert "" in result["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_after_with_empty_marker():
    """marker='' + position=after → find_pos=-1 → missing_markers。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    assert "" in result["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_uppercase_AFTER():
    """position='AFTER'（大写）→ 默认 else（after）分支。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "AFTER"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # 走 else 分支（after 语义），但 marker 找到后 +len = 3 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_uppercase_BEFORE_does_not_match_before_branch():
    """position='BEFORE'（大写）→ 不是 'before' → 走 else（after）分支。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "BEFORE"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # 走 else（after）：find "abc" at 0, +3=3 → match predicted end of chunk 0 (3)
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf tolerance_chars 写入 _tolerance_chars
# =========================================================================


def test_chunk_boundary_prf_tolerance_chars_always_present():
    """所有路径都要写入 _tolerance_chars。"""
    cases = [
        (None, None, 30),
        ({"chunks": []}, None, 30),
        ({}, {"chunk_boundary_anchors": [{"marker": "x"}]}, 30),
        ({"chunks": [{"text": "a"}]}, {"chunk_boundary_anchors": [{"marker": "x"}]}, 30),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []}, 30),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}, 30),
    ]
    for doc, ann, tc in cases:
        result = chunk_boundary_prf(doc, ann, tolerance_chars=tc)
        assert "_tolerance_chars" in result
        assert result["_tolerance_chars"]["value"] == tc


def test_chunk_boundary_prf_tolerance_chars_negative_no_match():
    """tolerance_chars=-5 → |d|<-5 永远 False → 0 matches。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=-5)
    assert result["chunk_boundary_precision"]["value"] == 0.0
    assert result["chunk_boundary_recall"]["value"] == 0.0
    assert result["chunk_boundary_f1"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf 多 predicted
# =========================================================================


def test_chunk_boundary_prf_more_predicted_than_anchors():
    """predicted 多 → precision < 1。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # predicted: end of "a" = 1, end of "b" = 3
    # anchor: "a" after → 1 → match 1
    # precision = 1/2 = 0.5, recall = 1/1 = 1.0
    assert result["chunk_boundary_precision"]["value"] == 0.5
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predicted():
    """anchors 多 → recall < 1。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},  # match
        {"marker": "xyz", "position": "after"},  # missing
        {"marker": "zzz", "position": "after"},  # missing
    ]}
    result = chunk_boundary_prf(document, annotation)
    # predicted: 1 (end of "abc")
    # anchors: 1 valid (abc), 2 missing → gt_positions = [3]
    # match 1 → precision 1/1 = 1.0, recall 1/1 = 1.0
    # missing markers 不算入 num_gt
    assert result["chunk_boundary_precision"]["value"] == 1.0
    assert result["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_predicted_not_in_tolerance():
    """所有 predicted 都超出 tolerance → no match。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # stream = "abc def ghi"
    # predicted: end of "abc" = 3, end of "def" = 7
    annotation = {"chunk_boundary_anchors": [
        {"marker": "ghi", "position": "after"},  # gt: find "ghi" at 8, +3 = 11
    ]}
    result = chunk_boundary_prf(document, annotation, tolerance_chars=2)
    # |3-11|=8, |7-11|=4 → 都 > 2 → no match
    assert result["chunk_boundary_precision"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf return dict 内部键
# =========================================================================


def test_chunk_boundary_prf_returns_dict_with_internal_keys_prefixed():
    """所有内部键以 _ 开头。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    for k in result.keys():
        if k.startswith("_"):
            assert k in ("_tolerance_chars", "_missing_markers")


def test_chunk_boundary_prf_metric_keys_no_underscore():
    """metric keys 都不以 _ 开头。"""
    document = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    result = chunk_boundary_prf(document, annotation)
    metric_keys = [k for k in result.keys() if not k.startswith("_")]
    assert metric_keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ]


# =========================================================================
# chunk_boundary_prf 边界值
# =========================================================================


def test_chunk_boundary_prf_single_chunk_two_anchors():
    """1 chunk + 2 anchors → no_predicted_boundaries，但 recall 是 0.0（有 anchors）。"""
    document = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "abc", "position": "before"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    assert result["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert result["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_chunk_with_only_whitespace():
    """chunk text 是纯空白 → normalize 后空 → predicted 仍按位置计算。"""
    document = {"chunks": [{"text": "   "}, {"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "before"},
    ]}
    result = chunk_boundary_prf(document, annotation)
    # normalize 后 "abc" → stream "abc"
    # predicted: end of "" (first chunk normalized) = 0
    # anchor: "abc" position=before → find at 0 → gt=0 → |0-0|=0 → match
    assert result["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_is_int():
    """position 是 int（不是 str）→ != "before" → 走 else。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": 0},  # type: ignore[dict-item]
    ]}
    result = chunk_boundary_prf(document, annotation)
    # 走 else（after）：find "abc" at 0, +3=3 → match predicted end of "abc" (3)
    assert result["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# 模块结构补充
# =========================================================================


def test_module_all_contains_three_entries():
    import evaluation.annotation_metrics as m
    assert len(m.__all__) == 3


def test_module_all_order():
    """__all__ 顺序：PARSER_DOES_NOT_EMIT_RELATIONS / figure_caption_prf / chunk_boundary_prf。"""
    import evaluation.annotation_metrics as m
    assert list(m.__all__) == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_constants_count():
    """模块只有一个公开常量 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    import evaluation.annotation_metrics as m
    public_upper = [n for n in dir(m) if n.isupper() and not n.startswith("_")]
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in public_upper


def test_module_uses_normalize_text_from_app_chunkers():
    """normalize_text 应来自 app.chunkers.structural。"""
    import evaluation.annotation_metrics as m
    from app.chunkers.structural import normalize_text
    assert m.normalize_text is normalize_text


def test_module_imports_null_ratio_from_metrics():
    """_null/_ratio 应来自 evaluation.metrics。"""
    import evaluation.annotation_metrics as m
    from evaluation.metrics import _null, _ratio
    assert m._null is _null
    assert m._ratio is _ratio


def test_module_docstring_mentions_one_to_one():
    """docstring 应提及一对一匹配。"""
    import evaluation.annotation_metrics as m
    doc = m.__doc__
    assert "一对一" in doc or "one-to-one" in doc.lower()


def test_chunk_boundary_prf_signature_positional_count():
    sig = inspect.signature(chunk_boundary_prf)
    positional = [p for p in sig.parameters.values()
                  if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
    assert len(positional) == 3


def test_chunk_boundary_prf_keyword_only_count():
    sig = inspect.signature(chunk_boundary_prf)
    kw_only = [p for p in sig.parameters.values()
               if p.kind == inspect.Parameter.KEYWORD_ONLY]
    assert len(kw_only) == 0  # tolerance_chars 不是 KEYWORD_ONLY


def test_figure_caption_prf_signature_positional_count():
    sig = inspect.signature(figure_caption_prf)
    positional = [p for p in sig.parameters.values()
                  if p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD]
    assert len(positional) == 2


# =========================================================================
# 综合行为
# =========================================================================


def test_chunk_boundary_prf_returns_consistent_keys_across_paths():
    """不同路径返回的 metric keys 应一致（只 _missing_markers 有差异）。"""
    paths = [
        chunk_boundary_prf(None, None),
        chunk_boundary_prf({"chunks": []}, None),
        chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]}),
        chunk_boundary_prf(
            {"chunks": [{"text": "a"}, {"text": "b"}]},
            {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
        ),
    ]
    base_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    for r in paths:
        assert base_keys.issubset(set(r.keys()))


def test_chunk_boundary_prf_no_side_effects():
    """chunk_boundary_prf 不应修改输入 document 或 annotation。"""
    document = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    import copy
    doc_snapshot = copy.deepcopy(document)
    ann_snapshot = copy.deepcopy(annotation)
    chunk_boundary_prf(document, annotation)
    assert document == doc_snapshot
    assert annotation == ann_snapshot
