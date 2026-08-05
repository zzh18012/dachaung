r"""evaluation/annotation_metrics.py 边角测试 - 第十三轮（Round 241）。

补强已有 base/edges/edges2-12（共 ~805+ 测试）未覆盖的深度：
- predicted boundaries 算法精确位置验证（chunks 不同长度组合）
- gt_positions 算法精确位置（before/after + search_from 推进）
- search_from 推进策略（重复 marker 不冲突）
- chunk_text 算法路径：find 在 stream 中精确定位
- normalize_text 在拼接 stream 中的行为
- module 导入 identity（_null/_ratio/normalize_text/Counter）
- chunk_boundary_prf docstring algorithm step 关键词
- figure_caption_prf docstring 内容
- 多 chunk 边界距离与 tolerance 精确匹配
"""

from __future__ import annotations

from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# predicted boundaries 算法位置精确
# =========================================================================


def test_predicted_boundary_position_after_alpha():
    """chunks=['alpha', 'beta'] → predicted at position 5（alpha 末尾）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # alpha len=5; after alpha at position 5; predicted boundary at 5
    # matched → precision/recall/f1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_predicted_boundary_position_after_short_chunk():
    """chunks=['a', 'b'] → predicted at position 1（'a' 末尾）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_predicted_boundary_position_after_long_chunk():
    """chunks=['abcdefghijklmnop', 'xyz'] → predicted at 16。"""
    doc = {"chunks": [{"text": "abcdefghijklmnop"}, {"text": "xyz"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abcdefghijklmnop", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_predicted_boundaries_two_chunks_at_correct_positions():
    """chunks=['alpha', 'beta', 'gamma'] → 2 predicted boundaries。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# gt_positions 算法精确
# =========================================================================


def test_gt_position_anchor_before_at_start_of_marker():
    """marker='alpha' position='before' → gt at 0（marker 起始位置）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "before"}]}
    # stream = "alpha beta"; alpha starts at 0 → gt_position=0
    # predicted boundary at 5; distance = 5
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_gt_position_anchor_after_at_end_of_marker():
    """marker='alpha' position='after' → gt at 5（marker 末尾）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    # gt_position = 0 + len('alpha') = 5
    # predicted boundary at 5 → matched
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_gt_position_anchor_after_position_in_middle_of_stream():
    """marker='beta' position='before' → gt at 6（'beta' 起始）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    # stream = "alpha beta"; beta starts at 6 → gt_position=6
    # predicted boundary at 5; distance = 1
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_gt_position_two_anchors_at_different_positions():
    """2 anchors at different positions → 2 gt_positions。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},  # gt at 5
        {"marker": "beta", "position": "after"},   # gt at 5+1+4=10
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted boundaries: 5, 10
    # gt_positions: 5, 10
    # all matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# search_from 推进策略
# =========================================================================


def test_search_from_advances_after_first_marker():
    """同 marker 出现 2 次：第 1 个 anchor 命中第 1 次出现；第 2 个 anchor 命中第 2 次。"""
    # chunks: alpha alpha gamma
    # stream: "alpha alpha gamma"
    doc = {"chunks": [{"text": "alpha"}, {"text": "alpha"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alpha", "position": "after"},
    ]}
    # 第 1 个 alpha at 0, after → gt=5; search_from=5
    # 第 2 个 alpha at 6 (在 stream "alpha alpha gamma" 中，第 2 个 alpha 起始 6), after → gt=11
    # predicted: after chunk 0 (5), after chunk 1 (5+1+5=11)
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_search_from_marker_at_start_only():
    """marker 只出现 1 次：第 2 个 anchor 找不到 → missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alpha", "position": "after"},  # alpha 已被消耗
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 第 2 个 marker 'alpha' missing（search_from=5 之后没有 alpha）
    assert "alpha" in out["_missing_markers"]["value"]


def test_search_from_does_not_advance_on_missing_marker():
    """missing marker 不推进 search_from。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "zzz", "position": "after"},  # missing
        {"marker": "alpha", "position": "after"},  # 应当能找到
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 'zzz' missing，但 'alpha' 仍能找到
    assert "zzz" in out["_missing_markers"]["value"]
    assert "alpha" not in out.get("_missing_markers", {}).get("value", [])


# =========================================================================
# chunk_text 算法路径
# =========================================================================


def test_chunk_text_with_internal_whitespace_normalized():
    """chunk text 含内部多空格 → normalize 后变成单空格。"""
    doc = {"chunks": [{"text": "alpha   beta"}, {"text": "gamma"}]}
    # normalize_text("alpha   beta") → "alpha beta"
    # stream = "alpha beta gamma"
    ann = {"chunk_boundary_anchors": [{"marker": "alpha beta", "position": "after"}]}
    # 'alpha beta' 在 stream 中查找；gt_position = 10 (len 10)
    # predicted boundary = 10 (end of "alpha beta")
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_leading_trailing_whitespace_stripped():
    """chunk text 含 leading/trailing whitespace → normalize strip。"""
    doc = {"chunks": [{"text": "  alpha  "}, {"text": "beta"}]}
    # normalize_text("  alpha  ") → "alpha"
    # stream = "alpha beta"
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_newlines_normalized_to_spaces():
    """chunk text 含换行 → normalize 转空格。"""
    doc = {"chunks": [{"text": "alpha\nbeta"}, {"text": "gamma"}]}
    # normalize_text("alpha\nbeta") → "alpha beta"
    # stream = "alpha beta gamma"
    ann = {"chunk_boundary_anchors": [{"marker": "alpha beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# 多 chunk 距离与 tolerance 匹配
# =========================================================================


def test_two_predicted_two_anchors_exact_match_tolerance_zero():
    """predicted 和 anchors 数量相等，位置精确匹配，tolerance=0 → 全匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_two_predicted_close_to_anchors_tolerance_one():
    """predicted 距离 anchors=1 → tolerance=1 匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # predicted at 5
    ann = {"chunk_boundary_anchors": [{"marker": "alph", "position": "after"}]}
    # 'alph' after → gt at 4; distance=1
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_predicted_too_far_from_anchor_tolerance_zero():
    """predicted 距离 anchors=1 → tolerance=0 不匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alph", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


# =========================================================================
# stream 拼接
# =========================================================================


def test_stream_single_chunk_no_predicted_boundaries():
    """单 chunk → 无内部边界 → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "alpha"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 有 anchors → recall = _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_stream_many_chunks_proportional_boundaries():
    """5 chunks → 4 predicted boundaries。"""
    doc = {"chunks": [
        {"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}, {"text": "e"}
    ]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
        {"marker": "c", "position": "after"},
        {"marker": "d", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_stream_chunks_with_unicode_text():
    """unicode 文本（中文）→ 正常匹配。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # '你好' len=2 (Python chars), after → gt at 2
    # predicted boundary at 2 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_stream_chunks_with_emoji():
    """emoji 文本（4-byte char）→ 正常匹配。"""
    doc = {"chunks": [{"text": "😀"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "😀", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# module 导入 identity
# =========================================================================


def test_module_null_is_imported_from_metrics():
    """_null 是 evaluation.metrics._null。"""
    import evaluation.annotation_metrics as m
    from evaluation.metrics import _null
    assert m._null is _null


def test_module_ratio_is_imported_from_metrics():
    """_ratio 是 evaluation.metrics._ratio。"""
    import evaluation.annotation_metrics as m
    from evaluation.metrics import _ratio
    assert m._ratio is _ratio


def test_module_normalize_text_is_imported_from_structural():
    """normalize_text 是 app.chunkers.structural.normalize_text。"""
    import evaluation.annotation_metrics as m
    from app.chunkers.structural import normalize_text
    assert m.normalize_text is normalize_text


def test_module_counter_is_imported_from_collections():
    """Counter 是 collections.Counter。"""
    import evaluation.annotation_metrics as m
    from collections import Counter
    assert m.Counter is Counter


def test_module_any_in_namespace():
    """Any 在模块命名空间。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Any")


# =========================================================================
# chunk_boundary_prf docstring algorithm step 关键词
# =========================================================================


def test_chunk_boundary_prf_docstring_mentions_normalize_step():
    """docstring 提到 'normalize' 或 '规范化'。"""
    doc = chunk_boundary_prf.__doc__
    assert "normaliz" in doc.lower() or "规范" in doc or "规范化" in doc


def test_chunk_boundary_prf_docstring_mentions_greedy():
    """docstring 提到 'greedy' 或 '贪心'。"""
    doc = chunk_boundary_prf.__doc__
    assert "greedy" in doc.lower() or "贪心" in doc


def test_chunk_boundary_prf_docstring_mentions_one_to_one():
    """docstring 提到 'one-to-one' 或 '一对一'。"""
    doc = chunk_boundary_prf.__doc__
    assert "one-to-one" in doc.lower() or "一对一" in doc or "一对一边界" in doc


def test_chunk_boundary_prf_docstring_mentions_position():
    """docstring 提到 'position'。"""
    doc = chunk_boundary_prf.__doc__
    assert "position" in doc.lower()


def test_chunk_boundary_prf_docstring_mentions_marker():
    """docstring 提到 'marker'。"""
    doc = chunk_boundary_prf.__doc__
    assert "marker" in doc.lower()


def test_chunk_boundary_prf_docstring_mentions_predicted():
    """docstring 提到 'predicted'。"""
    doc = chunk_boundary_prf.__doc__
    assert "predicted" in doc.lower() or "预测" in doc


def test_chunk_boundary_prf_docstring_mentions_ground_truth():
    """docstring 提到 'ground truth' 或 '标注'。"""
    doc = chunk_boundary_prf.__doc__
    assert "ground truth" in doc.lower() or "标注" in doc


def test_chunk_boundary_prf_docstring_mentions_anchor():
    """docstring 提到 'anchor'。"""
    doc = chunk_boundary_prf.__doc__
    assert "anchor" in doc.lower()


# =========================================================================
# figure_caption_prf docstring
# =========================================================================


def test_figure_caption_prf_docstring_short():
    """figure_caption_prf docstring 简短（少于 100 字符）。"""
    doc = figure_caption_prf.__doc__
    assert len(doc) < 100


def test_figure_caption_prf_docstring_mentions_parser():
    """figure_caption_prf docstring 提到 'parser'。"""
    doc = figure_caption_prf.__doc__
    assert "parser" in doc.lower() or "解析" in doc


def test_figure_caption_prf_docstring_mentions_relation():
    """figure_caption_prf docstring 提到 'relation' 或 '关联'。"""
    doc = figure_caption_prf.__doc__
    assert "relation" in doc.lower() or "关联" in doc


def test_figure_caption_prf_docstring_mentions_null_keyword():
    """figure_caption_prf docstring 提到 'null'。"""
    doc = figure_caption_prf.__doc__
    assert "null" in doc.lower()


# =========================================================================
# chunk_boundary_prf docstring length
# =========================================================================


def test_chunk_boundary_prf_docstring_nontrivial_length():
    """chunk_boundary_prf docstring 不太短（算法说明文档，至少 100 字符）。"""
    doc = chunk_boundary_prf.__doc__
    assert len(doc) > 100


def test_chunk_boundary_prf_docstring_contains_args_section():
    """docstring 含 Args 段（或 '参数'）。"""
    doc = chunk_boundary_prf.__doc__
    assert "args" in doc.lower() or "参数" in doc


def test_chunk_boundary_prf_docstring_contains_algorithm_section():
    """docstring 含算法说明（'算法' 或 'Algorithm'）。"""
    doc = chunk_boundary_prf.__doc__
    assert "算法" in doc or "algorithm" in doc.lower()


# =========================================================================
# module __all__ 与 PARSER_DOES_NOT_EMIT_RELATIONS
# =========================================================================


def test_parser_does_not_emit_relations_value_uses_snake_case():
    """常量值是 snake_case（不含空格/连字符）。"""
    val = PARSER_DOES_NOT_EMIT_RELATIONS
    assert "_" in val
    assert " " not in val
    assert "-" not in val


def test_parser_does_not_emit_relations_lowercase():
    """常量值全小写。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS.islower()


def test_parser_does_not_emit_relations_starts_with_parser():
    """常量值以 'parser_' 开头。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


# =========================================================================
# 一对一贪心匹配策略
# =========================================================================


def test_greedy_matches_closest_pair_first():
    """2 predicted + 2 anchors，贪心先匹配距离最近的。"""
    # predicted=[5, 9], anchors 在 5 和 10
    # 距离矩阵：
    #   p0=5 vs a0=5 → d=0
    #   p0=5 vs a1=10 → d=5
    #   p1=9 vs a0=5 → d=4
    #   p1=9 vs a1=10 → d=1
    # 排序：d=0 (p0,a0), d=1 (p1,a1), d=4 (p1,a0), d=5 (p0,a1)
    # 贪心：先 (p0,a0)；再 (p1,a1)；都 matched
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    # alpha=5 chars, beta=3 chars → predicted=[5, 9] in "alpha beta gamma"
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},  # gt at 5
        {"marker": "gamma", "position": "before"},  # gt at 10 ('gamma' starts at 10)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_greedy_does_not_double_assign_predicted():
    """1 predicted 不能匹配 2 anchors（即使距离都满足）。

    但 search_from 推进：alpha marker 第 2 次找不到（被消耗）→ 第 2 个 anchor missing。
    """
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alpha", "position": "before"},  # alpha 已消耗 → missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # alpha 出现 1 次；第 2 个 anchor 'alpha' missing
    # gt_positions 只有 1 个
    # matched=1, num_pred=1, num_gt=1 → precision/recall/f1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    # 'alpha' missing（第 2 次）
    assert "alpha" in out["_missing_markers"]["value"]


def test_greedy_does_not_double_assign_anchor():
    """1 anchor 不能匹配 2 predicted。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # 'a' after → gt at 1
    # predicted = [1, 3] (after 'a' and after 'b')
    # distance: p0=1 vs gt=1 → d=0; p1=3 vs gt=1 → d=2
    # 贪心：(p0, gt) matched; p1 已无 anchor 可用
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # matched=1, num_pred=2, num_gt=1
    # precision=1/2=0.5, recall=1/1=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# 单 chunk 边界（最后一个 chunk 不贡献边界）
# =========================================================================


def test_last_chunk_does_not_contribute_predicted_boundary():
    """最后一个 chunk 不贡献 predicted boundary。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
        {"marker": "gamma", "position": "after"},  # 最后 chunk 不贡献
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # predicted=[5, 10]（gamma 不贡献）
    # gt_positions: 'alpha' after=5; 'beta' after=10; 'gamma' after=16
    # 贪心：(p0=5, gt=5) matched; (p1=10, gt=10) matched; gt=16 无 p
    # matched=2, num_pred=2, num_gt=3
    # precision=2/2=1.0, recall=2/3
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert abs(out["chunk_boundary_recall"]["value"] - 2/3) < 1e-9


# =========================================================================
# chunks 中文本相同（重复）
# =========================================================================


def test_chunks_with_identical_text_both_contribute_boundaries():
    """2 chunks 文本相同 → 都贡献 boundary（stream 中 find 推进）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "abc"}]}
    # stream = "abc abc"
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "abc", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted: chunk 0 'abc' find at 0, end=3 → predicted=[3]; pos=4
    #   (chunk 1 is last → break, no boundary from it)
    # 所以 predicted=[3]（只 1 个，因为只有 chunk 0 → chunk 1 这一条边界）
    # gt: 第 1 个 abc find from 0 → at 0, after → gt=3; search_from=3
    #     第 2 个 abc find from 3 → at 4, after → gt=7; search_from=7
    # 所以 gt_positions=[3, 7]
    # matched: predicted=[3] vs gt=[3,7] → 只有 (p0=3, gt=3) matched
    # matched=1, num_pred=1, num_gt=2
    # precision=1/1=1.0, recall=1/2=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# =========================================================================
# chunk text 是非 str 但可转 str 的类型
# =========================================================================


def test_chunk_text_with_int_raises_at_normalize():
    """chunk text 是 int → normalize_text(int) raises TypeError（re.sub 不接受 int）。"""
    doc = {"chunks": [{"text": 42}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_text_with_none_in_normalize():
    """chunk text 是 None → `or ""` → normalize_text("")。"""
    doc = {"chunks": [{"text": None}, {"text": "abc"}]}
    # normalize_text("") → ""
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = " abc" → normalize → "abc"
    # predicted: chunk 0 (not last): find("", 0) = 0, end=0, predicted=[0]; pos=1
    # chunk 1 (last): break
    # gt: 'abc' at 0, after → gt=3
    # distance |0-3|=3, tolerance=10 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# module 结构补强
# =========================================================================


def test_module_all_only_exports_three_names():
    """__all__ 3 个元素。"""
    import evaluation.annotation_metrics as m
    assert len(m.__all__) == 3


def test_module_all_first_constant():
    """__all__ 第 1 个是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    import evaluation.annotation_metrics as m
    assert m.__all__[0] == "PARSER_DOES_NOT_EMIT_RELATIONS"


def test_module_all_then_two_functions():
    """__all__ 后 2 个是 figure_caption_prf 和 chunk_boundary_prf。"""
    import evaluation.annotation_metrics as m
    assert m.__all__[1] == "figure_caption_prf"
    assert m.__all__[2] == "chunk_boundary_prf"


def test_module_docstring_module_level():
    """module 级 docstring 非空。"""
    import evaluation.annotation_metrics as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 0


def test_module_docstring_mentions_chunk_boundary():
    """module docstring 提到 chunk_boundary。"""
    import evaluation.annotation_metrics as m
    assert "chunk_boundary" in m.__doc__ or "分块边界" in m.__doc__


def test_module_docstring_mentions_figure_caption():
    """module docstring 提到 figure_caption。"""
    import evaluation.annotation_metrics as m
    assert "figure_caption" in m.__doc__ or "图表" in m.__doc__


def test_module_docstring_mentions_null():
    """module docstring 提到 null。"""
    import evaluation.annotation_metrics as m
    assert "null" in m.__doc__.lower()
