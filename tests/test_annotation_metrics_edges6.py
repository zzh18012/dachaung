r"""evaluation/annotation_metrics.py 边角测试 - 第六轮（Round 157）。

补强已有 base/edges/edges2-5（共 457 测试）未覆盖的深度：
- PARSER_DOES_NOT_EMIT_RELATIONS 常量精确性
- figure_caption_prf 深度（3 key、所有 null、相同 reason、新 dict）
- chunk_boundary_prf 各分支（document None、empty annotation、chunks<2、anchor 0/1/多、tolerance 边界、before/after、相同 marker）
- _tolerance_chars / _missing_markers key 行为
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量
# =========================================================================


def test_parser_does_not_emit_relations_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_module_all():
    import evaluation.annotation_metrics as mod
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in mod.__all__


# =========================================================================
# figure_caption_prf 深度
# =========================================================================


def test_figure_caption_prf_returns_three_keys():
    out = figure_caption_prf({}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_none():
    out = figure_caption_prf({}, {})
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_all_reasons_same():
    out = figure_caption_prf({}, {})
    reasons = {v["reason"] for v in out.values()}
    assert reasons == {PARSER_DOES_NOT_EMIT_RELATIONS}


def test_figure_caption_prf_with_none_document():
    out = figure_caption_prf(None, {})
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_none_annotation():
    out = figure_caption_prf({}, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_both_none():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_realistic_document():
    """真实 document 仍返回 null（parser 不输出 relation）。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "img1"},
            {"type": "caption", "element_id": "cap1", "content": "Figure 1"},
        ],
        "relations": [],
    }
    out = figure_caption_prf(doc, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_having_relations():
    """annotation 含 relation 但仍 null（不是启发式）。"""
    annotation = {
        "relations": [
            {"figure_id": "img1", "caption_id": "cap1"},
        ]
    }
    out = figure_caption_prf({}, annotation)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_returns_new_dict_each_call():
    a = figure_caption_prf({}, {})
    b = figure_caption_prf({}, {})
    assert a is not b
    assert a == b


def test_figure_caption_prf_json_serializable():
    out = figure_caption_prf({}, {})
    s = json.dumps(out)
    assert isinstance(s, str)


# =========================================================================
# chunk_boundary_prf document None 路径
# =========================================================================


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_includes_tolerance():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_document_none_default_tolerance():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


# =========================================================================
# chunk_boundary_prf empty annotation 路径
# =========================================================================


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": []}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_dict_annotation_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": []}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_includes_tolerance():
    out = chunk_boundary_prf({"chunks": []}, None, tolerance_chars=10)
    assert out["_tolerance_chars"]["value"] == 10


# =========================================================================
# chunk_boundary_prf chunks < 2 路径
# =========================================================================


def test_chunk_boundary_prf_no_chunks_returns_no_predicted_boundaries():
    """0 chunks + 有 anchors：precision/f1 null，recall=0.0（anchors 非空）。"""
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"
    # anchors 非空 → recall = _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_boundaries():
    """单个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"text": "hello"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hel"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_no_anchors_recall_null():
    """1 chunk + 0 anchors → recall = no_predicted_boundaries（anchors 空时走 null 分支）。"""
    doc = {"chunks": [{"text": "hello"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    # anchors 空 → recall 走 null
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_recall_zero():
    """1 chunk + 有 anchors → recall = _ratio(0.0)（anchors 非空走 _ratio）。"""
    doc = {"chunks": [{"text": "hello"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_recall"]["value"] == 0.0


# =========================================================================
# chunk_boundary_prf anchors 但 < 2 chunks
# =========================================================================


def test_chunk_boundary_prf_two_chunks_no_anchors_returns_no_ground_truth():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf 完整匹配路径
# =========================================================================


def test_chunk_boundary_prf_perfect_match():
    """marker 位置正好等于 chunk 边界 → precision/recall/f1 = 1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"，chunk 1 末尾位置 = 5
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before():
    """position="before" → marker 起始位置。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"，chunk 2 起始位置 = 6（"world" 的 w）
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    # 预测边界 = 5（"hello" 末尾）；标注边界 = 6（"world" 起始）
    # |5-6|=1 ≤ 2 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_within_tolerance_match():
    """预测边界与标注距离 ≤ tolerance → match。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # marker "lo world" 在 stream "hello world" 中位置 = 3，结束位置 = 11
    annotation = {"chunk_boundary_anchors": [{"marker": "lo world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 预测边界 5；标注边界 11；|5-11|=6 ≤ 10 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_beyond_tolerance_no_match():
    """距离 > tolerance → no match。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "lo world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    # 距离 6 > 2 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_partial_match_two_chunks_two_anchors():
    """2 anchors（marker 不重叠），1 predicted → 1 match。
    recall=1/2, precision=1/1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"，预测边界 = 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # 找到于 0，after=3
            {"marker": "def", "position": "after"},  # search_from=3 之后找 "def"
                                                    # stream.find("def", 3) = 4，after = 7
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted [3], gt [3, 7]
    # anchor1 (3) 与 predicted 3 距离 0 → match
    # anchor2 (7) 与 predicted 3 距离 4 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == pytest.approx(1 / 2)


def test_chunk_boundary_prf_multiple_chunks_multiple_anchors():
    """3 chunks → 2 predicted boundaries；2 anchors → 2 matches。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    # stream = "aaa bbb ccc"
    # predicted 边界：3 ("aaa" 后), 7 ("bbb" 后)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # 3
            {"marker": "bbb", "position": "after"},  # 7
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_missing_marker_recorded():
    """marker 在 stream 中找不到 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    # _missing_markers 应存在
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["nonexistent"]
    # num_gt=0 → recall null
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_no_missing_markers_no_key():
    """所有 marker 都找到 → 不应有 _missing_markers key。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_empty_marker_treated_as_missing():
    """空 marker → find 返回 -1（被记录为 missing）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_f1_when_p_or_r_none():
    """precision/recall 之一为 None → f1 = null(precision_or_recall_not_evaluated)。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    # num_gt=0 → recall null；f1 null
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_prf_f1_when_p_and_r_zero():
    """precision=0 + recall=0 → f1=_ratio(0.0)（denom ≤ 0）。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"},  # 距离远超 tolerance
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # marker "xxx" 找不到 → missing；num_gt=0 → recall null + f1 null
    # 改用 found marker 但距离远
    annotation2 = {
        "chunk_boundary_anchors": [
            {"marker": "bbb", "position": "after"},  # gt 位置 7
        ]
    }
    out2 = chunk_boundary_prf(doc, annotation2, tolerance_chars=0)
    # predicted [3], gt [7], |3-7|=4 > 0 → no match
    assert out2["chunk_boundary_precision"]["value"] == 0.0
    assert out2["chunk_boundary_recall"]["value"] == 0.0
    assert out2["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_same_marker_twice():
    """同一 marker 出现两次 → 顺序定位（不都命中第一次）。"""
    doc = {"chunks": [{"text": "x"}, {"text": "x"}, {"text": "y"}]}
    # stream = "x x y"
    # predicted: 1 ("x" 后), 3 ("x" 后)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},  # 第一次 x → 位置 1
            {"marker": "x", "position": "after"},  # 第二次 x → 位置 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_includes_tolerance_in_output():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=25)
    assert out["_tolerance_chars"]["value"] == 25
    assert out["_tolerance_chars"]["reason"] is None


# =========================================================================
# chunk_boundary_prf 不修改输入
# =========================================================================


def test_chunk_boundary_prf_does_not_modify_document():
    doc = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
        ]
    }
    import copy
    doc_before = copy.deepcopy(doc)
    chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert doc == doc_before


def test_chunk_boundary_prf_does_not_modify_annotation():
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    import copy
    ann_before = copy.deepcopy(annotation)
    chunk_boundary_prf({"chunks": [{"text": "x"}, {"text": "y"}]}, annotation)
    assert annotation == ann_before


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_list():
    import evaluation.annotation_metrics as mod
    assert mod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_no_duplicates():
    import evaluation.annotation_metrics as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_imports_counter():
    import evaluation.annotation_metrics as mod
    src = inspect.getsource(mod)
    assert "from collections import Counter" in src


def test_module_imports_any():
    import evaluation.annotation_metrics as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text():
    import evaluation.annotation_metrics as mod
    src = inspect.getsource(mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_ratio():
    import evaluation.annotation_metrics as mod
    src = inspect.getsource(mod)
    assert "_null" in src
    assert "_ratio" in src


def test_module_uses_future_annotations():
    import evaluation.annotation_metrics as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.annotation_metrics as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_no_heuristic():
    """docstring 提及"不引入启发式"。"""
    import evaluation.annotation_metrics as mod
    doc = mod.__doc__
    assert "启发式" in doc or "heuristic" in doc.lower()


def test_module_docstring_mentions_one_to_one():
    """docstring 提及一对一匹配。"""
    import evaluation.annotation_metrics as mod
    doc = mod.__doc__
    assert "一对一" in doc or "one-to-one" in doc.lower()


def test_module_docstring_mentions_tolerance():
    """docstring 提及 tolerance 必须在报告中记录。"""
    import evaluation.annotation_metrics as mod
    doc = mod.__doc__
    assert "tolerance" in doc.lower() or "容差" in doc


def test_module_no_silence_unused():
    import evaluation.annotation_metrics as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 签名深度
# =========================================================================


def test_figure_caption_prf_signature_two_params():
    sig = inspect.signature(figure_caption_prf)
    assert set(sig.parameters) == {"document", "annotation"}


def test_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_return_annotation_dict():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation).lower()


def test_chunk_boundary_prf_signature_three_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert set(sig.parameters) == {"document", "annotation", "tolerance_chars"}


def test_chunk_boundary_prf_document_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_tolerance_annotation_int():
    sig = inspect.signature(chunk_boundary_prf)
    assert "int" in str(sig.parameters["tolerance_chars"].annotation)


def test_chunk_boundary_prf_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation).lower()


# =========================================================================
# 综合行为
# =========================================================================


def test_figure_caption_prf_idempotent():
    a = figure_caption_prf({}, {})
    b = figure_caption_prf({}, {})
    assert a == b


def test_chunk_boundary_prf_idempotent():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    a = chunk_boundary_prf(doc, ann)
    b = chunk_boundary_prf(doc, ann)
    # _tolerance_chars / _missing_markers 都是新建 dict，但内容相等
    # 比较时排除 _tolerance_chars（不影响算法正确性）
    assert a["chunk_boundary_precision"] == b["chunk_boundary_precision"]
    assert a["chunk_boundary_recall"] == b["chunk_boundary_recall"]
    assert a["chunk_boundary_f1"] == b["chunk_boundary_f1"]


def test_chunk_boundary_prf_json_serializable():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    s = json.dumps(out)
    assert isinstance(s, str)


def test_chunk_boundary_prf_returns_dict_with_six_or_seven_keys():
    """正常路径：3 PRF key + _tolerance_chars (+ _missing_markers)。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_with_zero_tolerance():
    """tolerance_chars=0 → 仅精确匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界 5；标注边界 5；|5-5|=0 ≤ 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_with_negative_tolerance():
    """tolerance_chars=-1 → 任何距离都不匹配（|x| ≥ 0 > -1 永远 False）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # |0| ≤ -1 → False → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
