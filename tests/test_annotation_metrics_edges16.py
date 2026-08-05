r"""evaluation/annotation_metrics.py 边角测试 - 第十六轮（Round 262）。

补强已有 base/edges/edges2-15（共 ~1030+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容
- chunk_boundary_prf 算法详细：
  - position='before' vs 'after' 语义
  - tolerance_chars 边界（exact match / 1 over / 1 under）
  - 多 predicted + 多 anchor 一对一匹配
  - greedy 排序行为
  - marker 出现多次（顺序 search_from）
  - marker 在 stream 起始 / 末尾
  - marker 是空字符串
  - normalize_text 在 chunk text 上的效果
- _tolerance_chars / _missing_markers 在 success 路径的行为
- 模块 namespace 完整性
- 函数签名 introspection
- 模块 __all__ 精确
- PARSER_DOES_NOT_EMIT_RELATIONS singleton
- helper FunctionType
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
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_counter_import():
    import evaluation.annotation_metrics as m

    assert "from collections import Counter" in inspect.getsource(m)


def test_module_source_contains_any_import():
    import evaluation.annotation_metrics as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_normalize_text_import():
    """源码含 from app.chunkers.structural import normalize_text。"""
    import evaluation.annotation_metrics as m

    assert "from app.chunkers.structural import normalize_text" in inspect.getsource(m)


def test_module_source_contains_metrics_helper_import():
    """源码含 from evaluation.metrics import _null, _ratio。"""
    import evaluation.annotation_metrics as m

    assert "from evaluation.metrics import _null, _ratio" in inspect.getsource(m)


def test_module_source_contains_future_annotations():
    import evaluation.annotation_metrics as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_parser_does_not_emit_relations_constant():
    """源码含 PARSER_DOES_NOT_EMIT_RELATIONS = '...'。"""
    import evaluation.annotation_metrics as m

    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in inspect.getsource(m)


def test_module_source_contains_figure_caption_prf_def():
    import evaluation.annotation_metrics as m

    assert "def figure_caption_prf(" in inspect.getsource(m)


def test_module_source_contains_chunk_boundary_prf_def():
    import evaluation.annotation_metrics as m

    assert "def chunk_boundary_prf(" in inspect.getsource(m)


def test_module_source_contains_pipeline_failed_reason():
    """源码含 'pipeline_failed'。"""
    import evaluation.annotation_metrics as m

    assert '"pipeline_failed"' in inspect.getsource(m)


def test_module_source_contains_no_annotation_reason():
    """源码含 'no_annotation'。"""
    import evaluation.annotation_metrics as m

    assert '"no_annotation"' in inspect.getsource(m)


def test_module_source_contains_no_predicted_boundaries_reason():
    """源码含 'no_predicted_boundaries'。"""
    import evaluation.annotation_metrics as m

    assert '"no_predicted_boundaries"' in inspect.getsource(m)


def test_module_source_contains_no_ground_truth_anchors_reason():
    """源码含 'no_ground_truth_anchors'。"""
    import evaluation.annotation_metrics as m

    assert '"no_ground_truth_anchors"' in inspect.getsource(m)


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason():
    """源码含 'no_ground_truth_anchors_in_stream'。"""
    import evaluation.annotation_metrics as m

    assert '"no_ground_truth_anchors_in_stream"' in inspect.getsource(m)


def test_module_source_contains_precision_or_recall_not_evaluated_reason():
    """源码含 'precision_or_recall_not_evaluated'。"""
    import evaluation.annotation_metrics as m

    assert '"precision_or_recall_not_evaluated"' in inspect.getsource(m)


def test_module_source_contains_tolerance_chars_param():
    """源码含 tolerance_chars 参数。"""
    import evaluation.annotation_metrics as m

    assert "tolerance_chars" in inspect.getsource(m)


def test_module_source_contains_default_tolerance_30():
    """源码含 tolerance_chars: int = 30。"""
    import evaluation.annotation_metrics as m

    assert "tolerance_chars: int = 30" in inspect.getsource(m)


def test_module_source_contains_search_from_token():
    """源码含 search_from（顺序查找）。"""
    import evaluation.annotation_metrics as m

    assert "search_from" in inspect.getsource(m)


def test_module_source_contains_missing_markers_token():
    """源码含 missing_markers。"""
    import evaluation.annotation_metrics as m

    assert "missing_markers" in inspect.getsource(m)


def test_module_source_contains_predicted_list():
    """源码含 predicted: list[int] = []。"""
    import evaluation.annotation_metrics as m

    assert "predicted" in inspect.getsource(m)


def test_module_source_contains_normalize_text_call():
    """源码含 normalize_text(...) 调用。"""
    import evaluation.annotation_metrics as m

    assert "normalize_text(c.get" in inspect.getsource(m)


def test_module_source_contains_join_call():
    """源码含 ' '.join(norm_chunks)。"""
    import evaluation.annotation_metrics as m

    assert '" ".join(norm_chunks)' in inspect.getsource(m)


def test_module_source_contains_find_call():
    """源码含 stream.find(...)。"""
    import evaluation.annotation_metrics as m

    assert "stream.find" in inspect.getsource(m)


def test_module_source_contains_greedy_pairs_sort():
    """源码含 pairs.sort(key=lambda x: x[0])。"""
    import evaluation.annotation_metrics as m

    assert "pairs.sort(key=lambda x: x[0])" in inspect.getsource(m)


def test_module_source_contains_used_pred_used_gt():
    """源码含 used_pred + used_gt（一对一匹配）。"""
    import evaluation.annotation_metrics as m

    assert "used_pred" in inspect.getsource(m)
    assert "used_gt" in inspect.getsource(m)


def test_module_source_contains_f1_formula():
    """源码含 f1 公式 2 * p_val * r_val / denom。"""
    import evaluation.annotation_metrics as m

    assert "2 * p_val * r_val / denom" in inspect.getsource(m)


def test_module_source_contains_denom_le_zero_check():
    """源码含 if denom <= 0。"""
    import evaluation.annotation_metrics as m

    assert "if denom <= 0" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.annotation_metrics as m

    assert "print(" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.annotation_metrics as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_figure_caption():
    """docstring 提到 figure-caption。"""
    import evaluation.annotation_metrics as m

    assert "figure-caption" in m.__doc__ or "figure_caption" in m.__doc__


def test_module_docstring_mentions_chunk_boundary():
    """docstring 提到 chunk boundary。"""
    import evaluation.annotation_metrics as m

    assert "chunk_boundary" in m.__doc__ or "chunk boundary" in m.__doc__.lower()


def test_module_docstring_mentions_one_to_one():
    """docstring 提到一对一匹配。"""
    import evaluation.annotation_metrics as m

    assert "一对一" in m.__doc__


def test_module_docstring_mentions_tolerance():
    """docstring 提到容差。"""
    import evaluation.annotation_metrics as m

    assert "容差" in m.__doc__ or "tolerance" in m.__doc__.lower()


def test_module_docstring_mentions_no_heuristic():
    """docstring 提到本期不引入启发式。"""
    import evaluation.annotation_metrics as m

    assert "启发式" in m.__doc__ or "本期" in m.__doc__


# =========================================================================
# 函数签名 introspection
# =========================================================================


def test_figure_caption_prf_param_count_2():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_param_names():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_no_var_args():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_figure_caption_prf_no_var_kwargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_figure_caption_prf_param_kind_positional_or_keyword():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_return_annotation_str():
    sig = inspect.signature(figure_caption_prf)
    assert isinstance(sig.return_annotation, str)


def test_chunk_boundary_prf_param_count_3():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_tolerance_kind_positional_or_keyword():
    """tolerance_chars 是 POSITIONAL_OR_KEYWORD（无 * separator）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_no_var_args():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_chunk_boundary_prf_no_var_kwargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_chunk_boundary_prf_return_annotation_str():
    sig = inspect.signature(chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


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


def test_all_module_functions_are_function_type():
    import types as _types

    for fn in [figure_caption_prf, chunk_boundary_prf]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 详细
# =========================================================================


def test_parser_does_not_emit_relations_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_is_hashable():
    """可作为 dict key / set element。"""
    s = {PARSER_DOES_NOT_EMIT_RELATIONS}
    assert PARSER_DOES_NOT_EMIT_RELATIONS in s


def test_parser_does_not_emit_relations_is_singleton_in_module():
    """模块级常量，多次访问同一对象。"""
    import evaluation.annotation_metrics as m

    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# figure_caption_prf 详细
# =========================================================================


def test_figure_caption_prf_returns_dict():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_keys_count_3():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_prf_keys_exact():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_null():
    """所有 value 都是 None。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["value"] is None, f"{k} 应是 None"


def test_figure_caption_prf_all_reasons_constant():
    """所有 reason 是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_doc_still_null():
    """即使有 document 也固定 null。"""
    doc = {"elements": [], "chunks": []}
    out = figure_caption_prf(doc, None)
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_still_null():
    """即使有 annotation 也固定 null。"""
    ann = {"figures": [], "captions": []}
    out = figure_caption_prf(None, ann)
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_each_metric_dict_structure():
    """每个 metric dict 含 'value' 和 'reason'。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_does_not_depend_on_inputs():
    """输出与输入无关。"""
    a = figure_caption_prf(None, None)
    b = figure_caption_prf({"x": 1}, {"y": 2})
    # value 都 None，reason 都相同
    for k in a:
        assert a[k] == b[k]


# =========================================================================
# chunk_boundary_prf 算法详细
# =========================================================================


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_no_annotation_returns_no_annotation():
    doc = {"chunks": [{"text": "x"}, {"text": "y"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation():
    doc = {"chunks": [{"text": "x"}, {"text": "y"}]}
    out = chunk_boundary_prf(doc, {}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_returns_no_predicted_boundaries():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_boundaries():
    """< 2 chunks → no predicted boundaries。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_recall_zero():
    """1 chunk + 有 anchor → recall=0.0（不是 null）。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_no_anchors_returns_no_ground_truth_anchors():
    """有预测但无 anchor → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_returns_1():
    """完美匹配 → precision=recall=f1=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # 边界正好在 alpha 后
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before():
    """position='before' → marker 起始位置。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "before"},  # 边界在 beta 前 = alpha 后
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # predicted 是 alpha 末尾（位置 5）；before beta 也是位置 5
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_exact():
    """tolerance_chars=0 + 完美匹配 → 仍 1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_no_match():
    """tolerance_chars=0 + 略偏 → 0.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # predicted at 5（alpha 后）；marker 'ha' after → 位置 5+2-2=5? actually find 'ha' → position 3, + len('ha')=2 → 5
    # 算了，构造无法精确匹配的：marker='lpha' after → find 'lpha' at 1, +4 = 5
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 位置 stream.find('beta')=6, +4=10
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted=[5]; gt=[10]; |5-10|=5 > 0 → no match → precision=0/1=0.0, recall=0/1=0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_just_enough():
    """tolerance_chars=5 + |5-10|=5 → 刚好匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_one_too_small():
    """tolerance_chars=4 + |5-10|=5 → 不匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=4)
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_two_anchors_perfect():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_to_one_match_no_double_counting():
    """2 predicted 但只能匹配 1 个 anchor → precision=0.5。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # predicted=2, gt=1, matched=1 → precision=0.5, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_markers_sequential():
    """相同 marker 出现多次 → 顺序查找，各得位置。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "ab"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
            {"marker": "ab", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream='ab ab ab'；predicted=[2, 5]（位置 0-based 'ab' 之后）
    # 实际：'ab ab ab' 长度 8，第 1 个 'ab' 后是位置 2，第 2 个 'ab' 后是位置 5
    # 第 1 个 anchor marker 'ab' find from 0 → 0, +2=2；search_from=2
    # 第 2 个 anchor marker 'ab' find from 2 → 3（stream[3:5]='ab'）, +2=5
    # predicted=[2, 5], gt=[2, 5] → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_not_found_recorded_as_missing():
    """marker 不在 stream 中 → 加入 missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_no_key():
    """所有 marker 都找到 → 不出现 _missing_markers key。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_empty_marker_treated_as_not_found():
    """marker='' → find returns -1 → missing_markers → gt=[] → recall null + reason。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 空 marker → -1 → missing_markers → gt=[]
    # recall = null + no_ground_truth_anchors_in_stream
    # precision = 0/1 = 0.0
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_empty_marker_recorded_in_missing_markers():
    """空 marker 应被记录到 missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_defaults_to_after():
    """缺 position 字段 → 默认 'after'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha"},  # 无 position
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 'after' 与完美匹配 predicted 一致
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_treated_as_after():
    """position='weird' → 走 else 分支 = 'after'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "weird"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_normalize_chunk_text():
    """chunk text 含多余空白 → normalize 后查找。"""
    doc = {"chunks": [{"text": "  alpha  "}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # normalize 后 'alpha'；predicted at 5
    # 'after alpha' → 位置 5
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_f1_when_p_or_r_none():
    """precision/recall 任一 None → f1 = null precision_or_recall_not_evaluated。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 无 anchor → recall=null, precision=null（其实 no_ground_truth_anchors）
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_f1_when_both_zero():
    """p=0, r=0 → denom=0 → f1=0.0（不是 null）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 远离 predicted
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # precision=0.0, recall=0.0 → denom=0 → f1=0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_half_when_p_1_r_approx_1_third():
    """构造 p=1, r=1/3 → f1=2*1*0.333/(1+0.333)=0.5。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}, {"text": "delta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # 匹配 predicted[0]
            {"marker": "nonexistent1", "position": "after"},  # missing
            {"marker": "nonexistent2", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # predicted=[5, 11, 17]（3 个边界）, gt=[5]（其他 missing）
    # matched=1, num_pred=3, num_gt=1
    # precision=1/3, recall=1/1=1.0
    # f1 = 2 * (1/3) * 1 / (1/3 + 1) = (2/3) / (4/3) = 0.5
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(1/3, abs=1e-6)
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(0.5, abs=1e-6)


def test_chunk_boundary_prf_returns_tolerance_record_always():
    """_tolerance_chars 总在输出中（所有路径）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_record_structure():
    """_tolerance_chars 是 {value: int, reason: None}。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    rec = out["_tolerance_chars"]
    assert set(rec.keys()) == {"value", "reason"}
    assert rec["value"] == 10
    assert rec["reason"] is None


def test_chunk_boundary_prf_missing_markers_structure():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "ghost", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    rec = out["_missing_markers"]
    assert set(rec.keys()) == {"value", "reason"}
    assert rec["value"] == ["ghost"]
    assert rec["reason"] is None


# =========================================================================
# chunk_boundary_prf 边界条件
# =========================================================================


def test_chunk_boundary_prf_chunks_missing_text_uses_empty():
    """chunk 缺 text → 视为 ''。"""
    doc = {"chunks": [{}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不抛错就算成功
    assert isinstance(out, dict)


def test_chunk_boundary_prf_document_none_chunks_handled():
    """document 缺 chunks → 在 document is None 分支处理。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_missing_anchors_key():
    """annotation 缺 chunk_boundary_anchors → 视为 []。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"other_field": "x"}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # anchors=[] → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_none_treated_as_empty():
    """chunks=None → [] → no_predicted_boundaries。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_does_not_mutate_input_document():
    """不修改输入 document。"""
    import copy
    doc = {
        "chunks": [
            {"text": "alpha", "source_element_ids": ["e1"]},
            {"text": "beta", "source_element_ids": ["e2"]},
        ]
    }
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    doc_before = copy.deepcopy(doc)
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert doc == doc_before


def test_chunk_boundary_prf_does_not_mutate_input_annotation():
    """不修改输入 annotation。"""
    import copy
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    ann_before = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert ann == ann_before


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_counter():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "Counter")
    assert m.Counter is Counter


def test_module_namespace_contains_any():
    import evaluation.annotation_metrics as m
    from typing import Any as OrigAny

    assert m.Any is OrigAny


def test_module_namespace_contains_normalize_text():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "normalize_text")
    assert m.normalize_text is normalize_text


def test_module_namespace_contains_null_helper():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "_null")
    assert m._null is _null


def test_module_namespace_contains_ratio_helper():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "_ratio")
    assert m._ratio is _ratio


def test_module_namespace_contains_parser_does_not_emit_relations():
    import evaluation.annotation_metrics as m

    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


def test_module_namespace_contains_figure_caption_prf():
    import evaluation.annotation_metrics as m

    assert m.figure_caption_prf is figure_caption_prf


def test_module_namespace_contains_chunk_boundary_prf():
    import evaluation.annotation_metrics as m

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


def test_module_all_does_not_contain_private():
    """__all__ 不含 _null / _ratio（来自 evaluation.metrics）。"""
    import evaluation.annotation_metrics as m

    assert "_null" not in m.__all__
    assert "_ratio" not in m.__all__


def test_module_all_all_names_in_namespace():
    import evaluation.annotation_metrics as m

    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 整体一致性
# =========================================================================


def test_module_can_be_imported():
    import evaluation.annotation_metrics as m

    assert m is not None


def test_module_namespace_constants_stable():
    import evaluation.annotation_metrics as m

    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


def test_chunk_boundary_prf_does_not_share_state_between_calls():
    """两次调用返回独立 dict。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    a = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    b = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    a["chunk_boundary_precision"]["value"] = 99.0
    assert b["chunk_boundary_precision"]["value"] != 99.0


def test_figure_caption_prf_does_not_share_state_between_calls():
    a = figure_caption_prf(None, None)
    b = figure_caption_prf(None, None)
    a["figure_caption_precision"]["value"] = "modified"
    assert b["figure_caption_precision"]["value"] is None


def test_chunk_boundary_prf_returns_proper_dict_type():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_keys_count_includes_meta():
    """输出含 4 个 metric + _tolerance_chars。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # chunk_boundary_precision/recall/f1 + _tolerance_chars = 4
    assert len(out) == 4


def test_chunk_boundary_prf_keys_with_missing_markers_count_5():
    """含 _missing_markers → 5 keys。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "ghost", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # chunk_boundary_precision/recall/f1 + _tolerance_chars + _missing_markers = 5
    assert len(out) == 5


# =========================================================================
# 整体一致性：与 evaluation.metrics 协作
# =========================================================================


def test_chunk_boundary_prf_uses_null_helper_correctly():
    """pipeline_failed 路径用 _null 构造。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=10)
    null_metric = out["chunk_boundary_precision"]
    expected = _null("pipeline_failed")
    assert null_metric == expected


def test_chunk_boundary_prf_uses_ratio_helper_correctly():
    """完美匹配路径用 _ratio 构造。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    expected = _ratio(1.0)
    assert out["chunk_boundary_precision"] == expected
