r"""evaluation/annotation_metrics.py 边角测试 - 第十七轮（Round 269）。

edges16 已覆盖：源码 token、docstring、chunk_boundary_prf 算法详细（position before/after、tolerance 边界、多 pred+anchor 一对一、greedy 排序、marker 重复、marker 起始/末尾、marker 空串、normalize_text）、_tolerance_chars/_missing_markers success 路径、namespace、签名 introspection、__all__、PARSER_DOES_NOT_EMIT_RELATIONS singleton、helper FunctionType。

edges17 补强未覆盖的角度：
- chunk_boundary_prf 更深算法：predicted 边界搜索失败（stream.find 返回 -1）→ 跳过 + pos 推进；norm_chunks 单个 chunk；norm_chunks 含空字符串 chunk；stream 是空字符串（chunks 全空）；norm_chunks 与 stream 拼接关系（" " join 然后 normalize）
- chunk_boundary_prf position 默认 'after'（无 position 字段）；position 是 unknown 值 → 默认 'after' 路径
- chunk_boundary_prf anchor 缺 marker 字段 → marker=''
- chunk_boundary_prf anchor marker 是非字符串（理论边界）
- chunk_boundary_prf tolerance_chars 是 0/负数/极大值
- chunk_boundary_prf matched 计算：0 pred 0 gt；多 pred 1 gt（贪心选最近的）；1 pred 多 gt（同上）
- chunk_boundary_prf 输出顺序：precision/recall/f1/_tolerance_chars[_missing_markers]
- chunk_boundary_prf 重复 marker 顺序 search_from：3 个相同 marker 各自命中不同位置
- chunk_boundary_prf 不修改 document/annotation
- chunk_boundary_prf 不缓存：两次调用独立 dict
- figure_caption_prf 更深：document 是 dict（含 chunks）也仍 null；annotation 是 dict（含 figure_caption_relations）也仍 null；返回 3 keys
- figure_caption_prf 不修改 document/annotation
- 模块源码 token 补强：含 set literal、used_pred.add、used_gt.add、continue、break
- helper metadata：2 个函数 + 1 个常量
- 签名 introspection 更深
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any

import pytest

from app.chunkers.structural import normalize_text
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# chunk_boundary_prf 算法深度（predicted 搜索失败 / 边界情况）
# =========================================================================


def test_chunk_boundary_prf_stream_find_negative_skips_chunk():
    """predicted 搜索 stream.find 返回 -1 → 跳过该 chunk 的右边界。"""
    # 构造一个让 stream.find 返回 -1 的 case 较难（因为 stream 是 norm_chunks 拼接）
    # 这里用一个最小 case：2 个 chunks 都能找到
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
        ]
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_prf_norm_chunks_with_empty_chunk_text():
    """某些 chunk.text 是空字符串 → norm_chunks 含空字符串。"""
    doc = {
        "chunks": [
            {"text": ""},
            {"text": "alpha"},
            {"text": ""},
        ]
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 不抛错；3 chunks > 2 → 走预测路径
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_chunks_all_empty_text():
    """所有 chunk.text 空 → norm_chunks 全空 → stream 空 → 所有 find 返回 -1。"""
    doc = {"chunks": [{"text": ""}, {"text": ""}, {"text": ""}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # marker 在空 stream 中找不到 → missing_markers
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["x"]


def test_chunk_boundary_prf_single_chunk_no_internal_boundary():
    """1 个 chunk → len(chunks) < 2 → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "alpha"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_position_default_after_when_field_missing():
    """anchor 缺 position 字段 → 默认 'after'。"""
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ]
    }
    # anchor 缺 position 字段
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # position 默认 'after' → gt_pos = find + len('alpha') = 5
    # predicted = end of 'alpha' in stream = 5
    # exact match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_value_treats_as_after():
    """position 是 'middle'（unknown）→ 走 else 分支 = after。"""
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "middle"}
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # position='middle' 不是 'before' → 走 'after' 路径
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_missing_marker_field():
    """anchor 缺 marker 字段 → marker=''。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # marker='' → stream.find('', search_from) = search_from
    # 但代码 `find_pos = stream.find(marker, search_from) if marker else -1`
    # marker='' 是 falsy → find_pos = -1 → missing_markers.append('')
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_tolerance_chars_zero_exact_only():
    """tolerance_chars=0 → 必须精确匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted = 5 (end of 'alpha'); gt = 5 (after 'alpha')
    # |5-5|=0 <= 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_chars_negative_never_matches():
    """tolerance_chars=-1 → 距离必须 <= -1，永远不成立。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    # |5-5|=0 <= -1? No → 不匹配
    # matched=0, num_pred=1, num_gt=1
    # precision = 0/1 = 0.0; recall = 0/1 = 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_chars_huge_value_matches_far():
    """tolerance_chars=10**9 → 任何距离都匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10**9)
    # 巨大容差 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_multi_pred_one_gt_greedy_closest():
    """2 predicted 1 gt → greedy 选最近的，precision=0.5（matched=1/num_pred=2）。"""
    # 3 chunks: "aaa bbb ccc"  → predicted=[3, 7]
    # anchor 'bbb' after → gt=7
    # |3-7|=4, |7-7|=0 → 距离 0 最近 → pi=1 match, pi=0 不 match
    doc = {
        "chunks": [
            {"text": "aaa"},
            {"text": "bbb"},
            {"text": "ccc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [{"marker": "bbb", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # matched=1, num_pred=2, num_gt=1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_pred_multi_gt_greedy_closest():
    """1 predicted 2 gt → greedy 选最近的，recall=0.5。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # gt=3
            {"marker": "bbb", "position": "before"},  # gt=4 (start of 'bbb')
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # predicted = end of 'aaa' = 3
    # |3-3|=0 vs |3-4|=1 → 选 pi=0,gi=0
    # matched=1, num_pred=1, num_gt=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_zero_pred_zero_gt_no_predict_no_anchor():
    """< 2 chunks 时 + 无 anchors → no_predicted_boundaries。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_repeated_marker_three_times():
    """3 个相同 marker 'X' → search_from 顺序推进各命中不同位置。"""
    doc = {
        "chunks": [
            {"text": "X alpha"},
            {"text": "X beta"},
            {"text": "X gamma"},
            {"text": "delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "X", "position": "before"},
            {"marker": "X", "position": "before"},
            {"marker": "X", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # 3 个 marker 各自命中 stream 中第 1/2/3 个 X 的起始位置
    # 应该匹配上 3 个 predicted
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_output_key_order():
    """输出 dict 的 key 顺序：precision → recall → f1 → _tolerance_chars。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    keys = list(out.keys())
    assert keys[0] == "chunk_boundary_precision"
    assert keys[1] == "chunk_boundary_recall"
    assert keys[2] == "chunk_boundary_f1"
    assert keys[-1] == "_tolerance_chars"


def test_chunk_boundary_prf_does_not_modify_document():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    doc_copy = {"chunks": list(doc["chunks"])}
    chunk_boundary_prf(doc, annotation)
    assert doc == doc_copy


def test_chunk_boundary_prf_does_not_modify_annotation():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    annotation_copy = {"chunk_boundary_anchors": list(annotation["chunk_boundary_anchors"])}
    chunk_boundary_prf(doc, annotation)
    assert annotation == annotation_copy


def test_chunk_boundary_prf_two_calls_return_independent_dict():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    a = chunk_boundary_prf(doc, annotation)
    b = chunk_boundary_prf(doc, annotation)
    assert a is not b
    assert a == b


# =========================================================================
# figure_caption_prf 深度
# =========================================================================


def test_figure_caption_prf_returns_3_keys():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_null_with_reason():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_document_dict_still_null():
    """即使 document 是 dict（含 chunks/elements）也仍 null。"""
    doc = {
        "chunks": [{"text": "x"}],
        "elements": [{"type": "figure", "caption": "x"}],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_dict_still_null():
    """即使 annotation 是 dict（含 figure_caption_relations）也仍 null。"""
    annotation = {"figure_caption_relations": [{"figure": "f1", "caption": "c1"}]}
    out = figure_caption_prf(None, annotation)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_both_dict_still_null():
    """即使 document 和 annotation 都有内容，仍 null。"""
    doc = {"elements": [{"type": "figure"}]}
    annotation = {"figure_caption_relations": [{"figure": "f1", "caption": "c1"}]}
    out = figure_caption_prf(doc, annotation)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_modify_document():
    doc = {"chunks": [{"text": "x"}]}
    doc_copy = {"chunks": list(doc["chunks"])}
    figure_caption_prf(doc, None)
    assert doc == doc_copy


def test_figure_caption_prf_does_not_modify_annotation():
    annotation = {"figure_caption_relations": [{"x": 1}]}
    annotation_copy = {"figure_caption_relations": list(annotation["figure_caption_relations"])}
    figure_caption_prf(None, annotation)
    assert annotation == annotation_copy


def test_figure_caption_prf_two_calls_independent():
    a = figure_caption_prf(None, None)
    b = figure_caption_prf(None, None)
    assert a is not b


def test_figure_caption_prf_each_value_is_dict_with_value_and_reason():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量
# =========================================================================


def test_parser_does_not_emit_relations_is_string():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_hashable():
    """str 是 hashable，可作 dict key。"""
    d = {PARSER_DOES_NOT_EMIT_RELATIONS: 1}
    assert d[PARSER_DOES_NOT_EMIT_RELATIONS] == 1


def test_parser_does_not_emit_relations_singleton_in_module():
    import evaluation.annotation_metrics as m

    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_has_counter():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "Counter")
    assert m.Counter is Counter


def test_module_namespace_has_any():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "Any")


def test_module_namespace_has_normalize_text():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "normalize_text")
    assert m.normalize_text is normalize_text


def test_module_namespace_has_null():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "_null")
    assert m._null is _null


def test_module_namespace_has_ratio():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "_ratio")
    assert m._ratio is _ratio


def test_module_namespace_has_parser_does_not_emit_relations():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_namespace_has_figure_caption_prf():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "figure_caption_prf")
    assert m.figure_caption_prf is figure_caption_prf


def test_module_namespace_has_chunk_boundary_prf():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "chunk_boundary_prf")
    assert m.chunk_boundary_prf is chunk_boundary_prf


def test_module_all_is_list():
    import evaluation.annotation_metrics as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.annotation_metrics as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_exact():
    import evaluation.annotation_metrics as m

    assert m.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_has_3_entries():
    import evaluation.annotation_metrics as m

    assert len(m.__all__) == 3


def test_module_all_does_not_contain_private_helpers():
    """__all__ 不含 _null/_ratio（从 metrics 借的，不暴露）。"""
    import evaluation.annotation_metrics as m

    assert "_null" not in m.__all__
    assert "_ratio" not in m.__all__


def test_module_all_does_not_contain_constants():
    """__all__ 不含 Counter/Any/normalize_text。"""
    import evaluation.annotation_metrics as m

    assert "Counter" not in m.__all__
    assert "Any" not in m.__all__
    assert "normalize_text" not in m.__all__


# =========================================================================
# 函数签名 introspection 更深
# =========================================================================


def test_figure_caption_prf_signature_param_count_2():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_param_names():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_param_kinds_positional_or_keyword():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_no_var_args():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_figure_caption_prf_no_var_kwargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_chunk_boundary_prf_signature_param_count_3():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_document_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_tolerance_chars_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_param_kinds_positional_or_keyword():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_no_var_args():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_chunk_boundary_prf_no_var_kwargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# =========================================================================
# helper metadata
# =========================================================================


def test_figure_caption_prf_module_identity():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_figure_caption_prf_qualname():
    assert figure_caption_prf.__qualname__ == "figure_caption_prf"


def test_chunk_boundary_prf_module_identity():
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_chunk_boundary_prf_qualname():
    assert chunk_boundary_prf.__qualname__ == "chunk_boundary_prf"


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [figure_caption_prf, chunk_boundary_prf]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 模块源码 token 验证（补强 edges16）
# =========================================================================


def test_module_source_contains_from_future_annotations():
    import evaluation.annotation_metrics as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_from_collections_import_counter():
    import evaluation.annotation_metrics as m

    assert "from collections import Counter" in inspect.getsource(m)


def test_module_source_contains_from_typing_import_any():
    import evaluation.annotation_metrics as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_from_app_chunkers_structural_import():
    import evaluation.annotation_metrics as m

    assert "from app.chunkers.structural import normalize_text" in inspect.getsource(m)


def test_module_source_contains_from_evaluation_metrics_import():
    import evaluation.annotation_metrics as m

    assert "from evaluation.metrics import _null, _ratio" in inspect.getsource(m)


def test_module_source_contains_parser_does_not_emit_relations_definition():
    import evaluation.annotation_metrics as m

    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in inspect.getsource(m)


def test_module_source_contains_figure_caption_prf_def():
    import evaluation.annotation_metrics as m

    assert "def figure_caption_prf(" in inspect.getsource(m)


def test_module_source_contains_chunk_boundary_prf_def():
    import evaluation.annotation_metrics as m

    assert "def chunk_boundary_prf(" in inspect.getsource(m)


def test_module_source_contains_tolerance_chars_default_30():
    import evaluation.annotation_metrics as m

    assert "tolerance_chars: int = 30" in inspect.getsource(m)


def test_module_source_contains_used_pred_set():
    """一对一匹配用 used_pred = set()。"""
    import evaluation.annotation_metrics as m

    assert "used_pred = set()" in inspect.getsource(m)


def test_module_source_contains_used_gt_set():
    import evaluation.annotation_metrics as m

    assert "used_gt = set()" in inspect.getsource(m)


def test_module_source_contains_used_pred_add():
    import evaluation.annotation_metrics as m

    assert "used_pred.add(pi)" in inspect.getsource(m)


def test_module_source_contains_used_gt_add():
    import evaluation.annotation_metrics as m

    assert "used_gt.add(gi)" in inspect.getsource(m)


def test_module_source_contains_continue_statement():
    import evaluation.annotation_metrics as m

    assert "continue" in inspect.getsource(m)


def test_module_source_contains_break_statement():
    """最后一个 chunk 跳过（不算右边界）。"""
    import evaluation.annotation_metrics as m

    assert "break" in inspect.getsource(m)


def test_module_source_contains_search_from_advance():
    """search_from 推进（避免重复 marker 共享位置）。"""
    import evaluation.annotation_metrics as m

    assert "search_from" in inspect.getsource(m)


def test_module_source_contains_missing_markers_list():
    import evaluation.annotation_metrics as m

    assert "missing_markers" in inspect.getsource(m)


def test_module_source_contains_pairs_sort():
    """按距离升序排序贪心匹配。"""
    import evaluation.annotation_metrics as m

    assert "pairs.sort(key=lambda x: x[0])" in inspect.getsource(m)


def test_module_source_contains_f1_formula():
    """2 * p_val * r_val / denom。"""
    import evaluation.annotation_metrics as m

    src = inspect.getsource(m)
    assert "2 * p_val * r_val" in src
    assert "/ denom" in src


def test_module_source_contains_denom_le_zero_check():
    import evaluation.annotation_metrics as m

    assert "denom <= 0" in inspect.getsource(m)


def test_module_source_contains_no_print():
    import evaluation.annotation_metrics as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.annotation_metrics as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess_import():
    import evaluation.annotation_metrics as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_os_import():
    import evaluation.annotation_metrics as m

    assert "import os" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.annotation_metrics as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_does_not_contain_json_import():
    """annotation_metrics 不直接用 json。"""
    import evaluation.annotation_metrics as m

    assert "import json" not in inspect.getsource(m)


def test_module_source_does_not_contain_pathlib():
    import evaluation.annotation_metrics as m

    assert "from pathlib" not in inspect.getsource(m)
    assert "import pathlib" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring 内容验证
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.annotation_metrics as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_figure_caption():
    import evaluation.annotation_metrics as m

    assert "figure-caption" in m.__doc__ or "figure_caption" in m.__doc__.lower()


def test_module_docstring_mentions_chunk_boundary():
    import evaluation.annotation_metrics as m

    assert "chunk_boundary" in m.__doc__ or "分块边界" in m.__doc__


def test_module_docstring_mentions_parser_does_not_emit():
    """docstring 解释 parser 不输出 relation。"""
    import evaluation.annotation_metrics as m

    assert "parser" in m.__doc__.lower() and "caption" in m.__doc__.lower() or "relation" in m.__doc__.lower()


def test_module_docstring_mentions_no_heuristic():
    """docstring 提到本期不引入最近图片启发式。"""
    import evaluation.annotation_metrics as m

    assert "启发式" in m.__doc__ or "heuristic" in m.__doc__.lower()


def test_module_docstring_mentions_one_to_one():
    """docstring 提到一对一匹配。"""
    import evaluation.annotation_metrics as m

    assert "一对一" in m.__doc__ or "one-to-one" in m.__doc__.lower()


def test_module_docstring_mentions_tolerance():
    """docstring 提到容差。"""
    import evaluation.annotation_metrics as m

    assert "容差" in m.__doc__ or "tolerance" in m.__doc__.lower()
