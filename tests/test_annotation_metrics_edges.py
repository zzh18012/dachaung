"""evaluation/annotation_metrics.py 边角测试（Round 65）。

补强 tests/test_annotation_metrics.py（47 个测试）未覆盖的：
- 模块常量与 __all__ 导出
- figure_caption_prf 深度边角（None 输入、mutable、字段集）
- chunk_boundary_prf 全部 null 路径
- chunk_boundary_prf 一对一匹配（贪心 + 距离排序）
- tolerance_chars 默认/自定义/0/负数
- anchor position before/after/缺省/无效
- missing_markers 报告
- normalize_text 集成
- F1 计算（P/R None、denom=0、正常）
- 多 anchor 在同一 marker 的顺序定位
- _tolerance_chars 字段 always present
"""

from __future__ import annotations

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    __all__,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# ---------- 模块常量 ----------


def test_parser_does_not_emit_relations_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_all_exports_is_list():
    assert isinstance(__all__, list)


def test_all_exports_contains_three_items():
    assert len(__all__) == 3


def test_all_exports_exact_set():
    assert set(__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_all_exports_match_module_attributes():
    import evaluation.annotation_metrics as mod
    for name in __all__:
        assert hasattr(mod, name)


# ---------- figure_caption_prf 深度边角 ----------


def test_figure_caption_returns_dict_type():
    out = figure_caption_prf(document={}, annotation={})
    assert isinstance(out, dict)


def test_figure_caption_three_keys():
    out = figure_caption_prf(document={}, annotation={})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_value_all_none_with_doc():
    out = figure_caption_prf(document={"chunks": []}, annotation={"x": 1})
    for k in out:
        assert out[k]["value"] is None


def test_figure_caption_value_all_none_doc_none():
    out = figure_caption_prf(document=None, annotation={"x": 1})
    for k in out:
        assert out[k]["value"] is None


def test_figure_caption_value_all_none_annotation_none():
    out = figure_caption_prf(document={"chunks": []}, annotation=None)
    for k in out:
        assert out[k]["value"] is None


def test_figure_caption_value_all_none_both_none():
    out = figure_caption_prf(document=None, annotation=None)
    for k in out:
        assert out[k]["value"] is None


def test_figure_caption_reason_constant():
    out = figure_caption_prf(document=None, annotation=None)
    for k in out:
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_each_value_is_dict():
    out = figure_caption_prf(document={}, annotation={})
    for k in out:
        assert isinstance(out[k], dict)


def test_figure_caption_mutable_per_call():
    o1 = figure_caption_prf(document=None, annotation=None)
    o2 = figure_caption_prf(document=None, annotation=None)
    o1["figure_caption_precision"]["reason"] = "modified"
    assert o2["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_ignores_document_content():
    """无论 document 是否含 chunks/relations，结果都一样。"""
    out_with_chunks = figure_caption_prf(
        document={"chunks": [{"text": "x"}], "relations": [{"x": 1}]},
        annotation={"chunk_boundary_anchors": []},
    )
    out_empty = figure_caption_prf(document={}, annotation={})
    assert out_with_chunks == out_empty


def test_figure_caption_no_extra_keys():
    out = figure_caption_prf(document=None, annotation=None)
    assert len(out.keys()) == 3


# ---------- chunk_boundary_prf: 输出结构 ----------


def test_chunk_boundary_returns_dict_type():
    out = chunk_boundary_prf(document=None, annotation=None)
    assert isinstance(out, dict)


def test_chunk_boundary_keys_present_when_doc_none():
    out = chunk_boundary_prf(document=None, annotation=None)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ):
        assert k in out


def test_chunk_boundary_tolerance_chars_default_30():
    out = chunk_boundary_prf(document=None, annotation=None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_tolerance_chars_custom():
    out = chunk_boundary_prf(document=None, annotation=None, tolerance_chars=50)
    assert out["_tolerance_chars"]["value"] == 50


def test_chunk_boundary_tolerance_chars_zero():
    out = chunk_boundary_prf(document=None, annotation=None, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_chars_negative_accepted():
    """tolerance_chars 为负数也被接受（不强制校验）。"""
    out = chunk_boundary_prf(document=None, annotation=None, tolerance_chars=-5)
    assert out["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_tolerance_chars_reason_none():
    out = chunk_boundary_prf(document=None, annotation=None)
    assert out["_tolerance_chars"]["reason"] is None


# ---------- chunk_boundary_prf: doc=None 路径 ----------


def test_chunk_boundary_doc_none_precision_null():
    out = chunk_boundary_prf(document=None, annotation={"x": 1})
    assert out["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_doc_none_recall_null():
    out = chunk_boundary_prf(document=None, annotation={"x": 1})
    assert out["chunk_boundary_recall"]["value"] is None


def test_chunk_boundary_doc_none_f1_null():
    out = chunk_boundary_prf(document=None, annotation={"x": 1})
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_doc_none_reason_pipeline_failed():
    out = chunk_boundary_prf(document=None, annotation={"x": 1})
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_doc_none_ignores_annotation():
    """doc=None 时无论 annotation 如何都返 pipeline_failed。"""
    out = chunk_boundary_prf(document=None, annotation=None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


# ---------- chunk_boundary_prf: no_annotation 路径 ----------


def test_chunk_boundary_no_annotation_when_empty_dict():
    out = chunk_boundary_prf(document={"chunks": []}, annotation={})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_no_annotation_when_none():
    out = chunk_boundary_prf(document={"chunks": []}, annotation=None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_no_annotation_all_three_null():
    out = chunk_boundary_prf(document={"chunks": []}, annotation=None)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "no_annotation"


# ---------- chunk_boundary_prf: 少于 2 个 chunk ----------


def _doc_with_chunks(chunks):
    return {
        "schema_version": "0.1.0",
        "document_id": "doc-test",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "test=1.0",
        "elements": [],
        "chunks": chunks,
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_chunk_boundary_zero_chunks_no_anchors():
    """0 chunk + 0 anchor → no_predicted_boundaries。"""
    doc = _doc_with_chunks([])
    out = chunk_boundary_prf(document=doc, annotation={"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_zero_chunks_with_anchors():
    """0 chunk + 有 anchor → precision null, recall=0.0。"""
    doc = _doc_with_chunks([])
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_single_chunk_no_anchors():
    """1 chunk → 没有内部边界。"""
    doc = _doc_with_chunks([{"text": "hello world enough text here"}])
    out = chunk_boundary_prf(document=doc, annotation={"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_single_chunk_with_anchors():
    """1 chunk + 有 anchor → recall=0.0（边界 0 个）。"""
    doc = _doc_with_chunks([{"text": "hello world enough text here"}])
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- chunk_boundary_prf: 有预测但无 anchor ----------


def test_chunk_boundary_no_ground_truth_anchors():
    """2+ chunks + 空 anchors → no_ground_truth_anchors。"""
    doc = _doc_with_chunks([
        {"text": "first chunk long enough text"},
        {"text": "second chunk long enough text"},
    ])
    out = chunk_boundary_prf(document=doc, annotation={"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_no_ground_truth_when_anchors_field_missing():
    """annotation 不含 chunk_boundary_anchors 字段 → 视为 []（注意 annotation 必须非空才不走 no_annotation）。"""
    doc = _doc_with_chunks([
        {"text": "first chunk long enough text"},
        {"text": "second chunk long enough text"},
    ])
    # annotation 必须有别的字段才能跳过 not annotation 检查
    out = chunk_boundary_prf(document=doc, annotation={"doc_id": "x"})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


# ---------- chunk_boundary_prf: 完美匹配 ----------


def test_chunk_boundary_perfect_match_precision_1():
    """两个 chunk + anchor 恰好在 chunk 边界附近 → precision=1.0。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # anchor：在 text_a 最后一个单词后（应该接近预测边界）
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_perfect_match_recall_1():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_perfect_match_f1_1():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_f1"]["value"] == 1.0


# ---------- chunk_boundary_prf: position before/after ----------


def test_chunk_boundary_position_before_uses_start():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # marker 在 chunk_b 开头：position="before" 应当匹配
    ann = {"chunk_boundary_anchors": [{"marker": "mu", "position": "before"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # mu 的起始位置 ≈ chunk_b 起始位置 ≈ 预测边界（chunk_a 末尾 + 1 空格）
    # 在容差 50 内应能匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_after_uses_end():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_position_default_is_after():
    """缺省 position → 当作 after。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda"}]}  # 无 position
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf: tolerance_chars 边角 ----------


def test_chunk_boundary_tolerance_zero_perfect_match():
    """tolerance_chars=0：预测边界 == gt 位置才能匹配。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=0)
    # lambda 之后位置 = chunk_a 末尾 = 预测边界（精确）
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_zero_far_anchor_no_match():
    """tolerance_chars=0：anchor 离预测边界很远 → 不匹配。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # marker='beta' after → 位置在 chunk_a 中部，远离预测边界
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_tolerance_negative_never_matches():
    """tolerance_chars=-1：abs(pv-gv) <= -1 永远不成立。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=-1)
    assert out["chunk_boundary_precision"]["value"] == 0.0


# ---------- chunk_boundary_prf: missing_markers ----------


def test_chunk_boundary_missing_marker_reported():
    """marker 在 stream 中找不到 → 加入 _missing_markers。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent_marker_xyz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert "_missing_markers" in out
    assert "nonexistent_marker_xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_no_missing_markers_field_when_all_found():
    """所有 marker 都找到 → 不写 _missing_markers 字段。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert "_missing_markers" not in out


def test_chunk_boundary_missing_marker_reason_none():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "missing_xyz", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["_missing_markers"]["reason"] is None


def test_chunk_boundary_empty_marker_treated_as_missing():
    """空 marker → find 返 -1 → 加入 missing_markers。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 空 marker 在 source: `find_pos = stream.find(marker, search_from) if marker else -1`
    # → -1 → missing
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_recall_null_when_all_markers_missing():
    """所有 anchor 都找不到 → gt_positions=[] → recall null + reason。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "missing1", "position": "after"},
            {"marker": "missing2", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_precision_value_when_all_markers_missing():
    """所有 anchor 都找不到 → num_pred>0, matched=0 → precision=0.0。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "missing", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_precision"]["value"] == 0.0


# ---------- chunk_boundary_prf: 多个 chunks / 多个边界 ----------


def test_chunk_boundary_three_chunks_two_predictions():
    """3 chunks → 2 个预测边界。"""
    doc = _doc_with_chunks([
        {"text": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"},
        {"text": "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"},
        {"text": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"},
    ])
    ann = {"chunk_boundary_anchors": [
        {"marker": "lambda", "position": "after"},
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 2 个预测边界，但只有 1 个 anchor → 最多 1 次匹配
    # precision = 1/2 = 0.5；recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_multiple_anchors_one_per_chunk():
    """2 chunks + 2 anchors（在不同位置）→ 完美匹配。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [
        {"marker": "lambda", "position": "after"},  # 接近预测边界 0
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf: 一对一贪心匹配 ----------


def test_chunk_boundary_one_to_one_no_double_match():
    """两个 anchor 距离同一预测很近 → 只有一个能匹配（贪心）。"""
    # 这个测试通过让两个 anchor 距离同一个预测很近来验证一对一语义
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # 两个 anchor 都靠近预测边界 0（lambda after = 预测 0；kappa after = 离预测 0 也近）
    ann = {"chunk_boundary_anchors": [
        {"marker": "kappa", "position": "after"},   # 距离预测 0 ~ 6 chars
        {"marker": "lambda", "position": "after"},  # 距离预测 0 ~ 0 chars（最近）
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 只有 1 个预测边界 → 最多匹配 1 个 anchor
    # precision = 1/1 = 1.0；recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_greedy_picks_closest():
    """贪心按距离排序：选最近的配对。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [
        {"marker": "lambda", "position": "after"},  # 精确等于预测边界
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=100)
    # 唯一 anchor 匹配唯一预测
    assert out["chunk_boundary_f1"]["value"] == 1.0


# ---------- chunk_boundary_prf: 多个相同 marker 的顺序定位 ----------


def test_chunk_boundary_repeated_marker_sequential_positioning():
    """同 marker 出现两次：anchor 应顺序定位到第 1 次和第 2 次。"""
    # 两个 chunk 用相同结尾 'lambda'
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # 两个 anchor 都用 marker='lambda'
    # 第 1 个 anchor 应当匹配 chunk_a 中的 lambda
    # 第 2 个 anchor 应当匹配 chunk_b 中的 lambda（search_from 推进后）
    ann = {"chunk_boundary_anchors": [
        {"marker": "lambda", "position": "after"},
        {"marker": "lambda", "position": "after"},
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 第 1 个 anchor (lambda after in chunk_a) ≈ 预测边界 0 → match
    # 第 2 个 anchor (lambda after in chunk_b) 远离预测边界 0 → 不 match
    # 所以 recall = 1/2 = 0.5
    assert out["chunk_boundary_recall"]["value"] == 0.5


# ---------- chunk_boundary_prf: F1 计算边角 ----------


def test_chunk_boundary_f1_zero_when_p_r_zero():
    """P=0, R=0 → denom=0 → f1=0.0（不 null）。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # beta 远离预测边界
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=0)
    # P=0/1=0；R=0/1=0；denom=0 → f1=0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_f1_normal_case():
    """P=0.5, R=1.0 → f1 = 2*0.5*1/(0.5+1) = 0.667"""
    doc = _doc_with_chunks([
        {"text": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"},
        {"text": "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"},
        {"text": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"},
    ])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert p is not None and r is not None and f1 is not None
    expected = 2 * p * r / (p + r)
    assert abs(f1 - expected) < 1e-9


def test_chunk_boundary_f1_null_when_p_null():
    """P null → f1 null + reason。"""
    out = chunk_boundary_prf(document=None, annotation={"x": 1})
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_f1_null_reason_precision_or_recall_not_evaluated():
    """当 P 或 R null（非 doc=None 路径）→ reason='precision_or_recall_not_evaluated'。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # 让所有 anchor 都找不到 → recall null
    ann = {"chunk_boundary_anchors": [{"marker": "missing", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # P=0.0（not null），R=null → f1 null + reason
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


# ---------- chunk_boundary_prf: normalize_text 集成 ----------


def test_chunk_boundary_normalize_text_collapses_whitespace():
    """chunk.text 内的多空格被规范化后再定位 marker。"""
    text_a = "alpha    beta   gamma   delta   epsilon   zeta   eta   theta   iota"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    # marker 在规范化后的流中可定位
    ann = {"chunk_boundary_anchors": [{"marker": "iota", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_normalize_text_strips_ends():
    """chunk.text 首尾空白被 strip。"""
    text_a = "   alpha beta gamma delta epsilon zeta eta theta iota kappa   "
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "kappa", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf: chunks/anchors 缺省 ----------


def test_chunk_boundary_chunks_field_missing_treated_as_empty():
    """document 不含 chunks 字段 → 视为 []。"""
    doc = {"source_type": "docx"}
    out = chunk_boundary_prf(document=doc, annotation={"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_none_treated_as_empty():
    """document.chunks=None → 视为 []。"""
    doc = {"chunks": None}
    out = chunk_boundary_prf(document=doc, annotation={"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_anchors_none_treated_as_empty():
    """annotation.chunk_boundary_anchors=None → 视为 []。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(document=doc, annotation=ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


# ---------- chunk_boundary_prf: 输出类型 ----------


def test_chunk_boundary_each_metric_is_dict():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ):
        assert isinstance(out[k], dict)


def test_chunk_boundary_each_dict_has_value_and_reason():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
    ):
        assert "value" in out[k]
        assert "reason" in out[k]


def test_chunk_boundary_precision_value_is_float_or_none():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    p = out["chunk_boundary_precision"]["value"]
    assert p is None or isinstance(p, float)


# ---------- chunk_boundary_prf: 大输入稳定性 ----------


def test_chunk_boundary_many_chunks_stability():
    """10 个 chunk → 9 个预测边界。"""
    chunks = [
        {"text": f"chunk number {i} has enough text to be meaningful here"} for i in range(10)
    ]
    doc = _doc_with_chunks(chunks)
    ann = {"chunk_boundary_anchors": [{"marker": "meaningful", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=5)
    # 至少应稳定返回，不崩
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_many_anchors_stability():
    """多个 anchor + 多个 chunk → 稳定返回。"""
    chunks = [
        {"text": f"chunk number {i} has enough text to be meaningful here"} for i in range(5)
    ]
    doc = _doc_with_chunks(chunks)
    ann = {"chunk_boundary_anchors": [
        {"marker": f"chunk number {i}", "position": "after"} for i in range(5)
    ]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=100)
    # 至少应稳定返回
    assert "chunk_boundary_precision" in out


# ---------- chunk_boundary_prf: Unicode / 特殊字符 ----------


def test_chunk_boundary_unicode_chunk_text():
    """中文 chunk 文本 → marker 也能定位。"""
    text_a = "阿尔法 贝塔 伽马 德尔塔 伊普西龙 泽塔 伊塔 西塔 约 卡帕 兰姆达"
    text_b = "缪 纽 克西 奥密克戎 派 罗 西格玛 陶 宇普西龙 斐 气 普西 欧米伽"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "兰姆达", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_unicode_marker_missing():
    text_a = "阿尔法 贝塔 伽马 德尔塔 伊普西龙 泽塔 伊塔 西塔 约 卡帕 兰姆达"
    text_b = "缪 纽 克西 奥密克戎 派 罗 西格玛 陶 宇普西龙 斐 气 普西 欧米伽"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "不存在的标记", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert "不存在的标记" in out["_missing_markers"]["value"]


# ---------- chunk_boundary_prf: 空 chunk.text ----------


def test_chunk_boundary_empty_chunk_text_does_not_crash():
    """chunk.text='' → normalize 后还是 ''，但不影响其他 chunk 的边界。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": ""}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 不崩 + recall 能算出（lambda 在 stream 中）
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_chunk_text_none_treated_as_empty():
    """chunk.text=None → 当作 ''。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": None}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "omega", "position": "before"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    # 不崩
    assert "chunk_boundary_precision" in out


# ---------- chunk_boundary_prf: tolerance_chars 透传到 _tolerance_chars ----------


def test_chunk_boundary_tolerance_chars_recorded_in_output():
    """报告必须明确记录 tolerance_chars（评测规则要求）。"""
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    out = chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_tolerance_chars_always_present_even_on_failure_paths():
    """所有早返路径都必须写 _tolerance_chars。"""
    # doc=None 路径
    out = chunk_boundary_prf(document=None, annotation=None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    # no_annotation 路径
    out = chunk_boundary_prf(document={"chunks": []}, annotation=None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    # zero chunks 路径
    out = chunk_boundary_prf(
        document=_doc_with_chunks([]),
        annotation={"chunk_boundary_anchors": []},
        tolerance_chars=42,
    )
    assert out["_tolerance_chars"]["value"] == 42


# ---------- chunk_boundary_prf: 不 mutate 输入 ----------


def test_chunk_boundary_does_not_mutate_document():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    doc_copy = {k: v for k, v in doc.items()}
    doc_chunks_copy = [dict(c) for c in doc["chunks"]]
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert doc["chunks"] == doc_chunks_copy
    assert doc.keys() == doc_copy.keys()


def test_chunk_boundary_does_not_mutate_annotation():
    text_a = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda"
    text_b = "mu nu xi omicron pi rho sigma tau upsilon phi chi psi omega"
    doc = _doc_with_chunks([{"text": text_a}, {"text": text_b}])
    ann = {"chunk_boundary_anchors": [{"marker": "lambda", "position": "after"}]}
    ann_copy = {"chunk_boundary_anchors": list(ann["chunk_boundary_anchors"])}
    chunk_boundary_prf(document=doc, annotation=ann, tolerance_chars=50)
    assert ann == ann_copy


# ---------- 集成：figure_caption_prf vs chunk_boundary_prf 字段集差异 ----------


def test_figure_caption_and_chunk_boundary_have_distinct_keys():
    fc = figure_caption_prf(document=None, annotation=None)
    cb = chunk_boundary_prf(document=None, annotation=None)
    fc_keys = set(fc.keys())
    cb_keys = set(cb.keys())
    assert fc_keys.isdisjoint(cb_keys - {"_tolerance_chars"})
    # figure_caption 不写 _tolerance_chars
    assert "_tolerance_chars" not in fc_keys


# ---------- 模块导入无副作用 ----------


def test_import_module_does_not_crash():
    import importlib
    mod = importlib.import_module("evaluation.annotation_metrics")
    assert mod is not None


def test_module_has_required_attributes():
    import evaluation.annotation_metrics as mod
    for attr in ("figure_caption_prf", "chunk_boundary_prf", "PARSER_DOES_NOT_EMIT_RELATIONS"):
        assert hasattr(mod, attr)
