"""evaluation/annotation_metrics.py 第三十四轮 edges 测试（Round 364）。

重点补强 edges32 未触及的角度：
- figure_caption_prf source level 字符串精确补强第三批
- chunk_boundary_prf source level 字符串精确补强第三批
- figure_caption_prf 行为深度第六批
- chunk_boundary_prf 行为深度第六批
- module source forbidden tokens 第八批
- module source 字符串精确补强第三批
- signatures 精确补强第三批
- 模块整体合理性补强第三批
- 端到端集成补强第三批
"""

from __future__ import annotations

import inspect
import types
from collections import Counter

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    PARSER_DOES_NOT_EMIT_RELATIONS as reason_const,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf source level 字符串精确补强第三批 ----------


def test_figure_caption_source_uses_reason_assignment():
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_source_uses_null_three_times():
    src = inspect.getsource(figure_caption_prf)
    assert src.count("_null(reason)") == 3


def test_figure_caption_source_returns_figure_caption_precision():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_precision"' in src


def test_figure_caption_source_returns_figure_caption_recall():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_recall"' in src


def test_figure_caption_source_returns_figure_caption_f1():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_f1"' in src


def test_figure_caption_source_no_args_branch():
    src = inspect.getsource(figure_caption_prf)
    # figure_caption_prf 不分支 document/annotation 状态，固定 null
    assert "if document is None" not in src
    assert "if not annotation" not in src


def test_figure_caption_source_docstring_present():
    src = inspect.getsource(figure_caption_prf)
    assert '"""' in src


def test_figure_caption_source_docstring_mentions_null():
    src = inspect.getsource(figure_caption_prf)
    assert "固定 null" in src or "固定 None" in src


def test_figure_caption_source_no_chunk_boundary_string():
    src = inspect.getsource(figure_caption_prf)
    # figure_caption 不引用 chunk_boundary 关键字
    assert "chunk_boundary" not in src


# ---------- chunk_boundary_prf source level 字符串精确补强第三批 ----------


def test_chunk_boundary_source_uses_out_dict_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "out: dict[str, dict[str, Any]] = {}" in src


def test_chunk_boundary_source_document_none_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None:" in src


def test_chunk_boundary_source_document_none_branch_creates_three_keys():
    src = inspect.getsource(chunk_boundary_prf)
    # 包含 4 个独立的 for-loop 给 out[k] 赋值（document None / no_annotation / <2 chunks / no anchors）
    assert src.count("for k in") >= 2


def test_chunk_boundary_source_no_annotation_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not annotation:" in src


def test_chunk_boundary_source_anchors_get():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src


def test_chunk_boundary_source_chunks_get():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'chunks = document.get("chunks") or []' in src


def test_chunk_boundary_source_len_chunks_lt_2():
    src = inspect.getsource(chunk_boundary_prf)
    assert "len(chunks) < 2" in src


def test_chunk_boundary_source_no_predicted_boundaries_assignment():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"chunk_boundary_precision"] = _null("no_predicted_boundaries")' in src


def test_chunk_boundary_source_recall_branch_in_no_chunks():
    src = inspect.getsource(chunk_boundary_prf)
    # 当 <2 chunks 时 recall 取决于 anchors 是否存在
    assert "if not anchors" in src
    assert "else _ratio(0.0)" in src


def test_chunk_boundary_source_no_ground_truth_anchors_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not anchors:" in src


def test_chunk_boundary_source_norm_chunks_uses_normalize_text():
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text(c.get(" in src


def test_chunk_boundary_source_joined_raw():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'joined_raw = " ".join(norm_chunks)' in src


def test_chunk_boundary_source_stream_normalize():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_chunk_boundary_source_predicted_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int] = []" in src


def test_chunk_boundary_source_uses_enumerate():
    src = inspect.getsource(chunk_boundary_prf)
    assert "enumerate(norm_chunks)" in src


def test_chunk_boundary_source_break_last_chunk():
    src = inspect.getsource(chunk_boundary_prf)
    assert "break" in src


def test_chunk_boundary_source_uses_stream_find():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(txt, pos)" in src


def test_chunk_boundary_source_find_pos_lt_zero():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if find_pos < 0:" in src


def test_chunk_boundary_source_pos_advance_on_skip():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos += len(txt) + 1" in src


def test_chunk_boundary_source_end_eq_find_pos_plus_len():
    src = inspect.getsource(chunk_boundary_prf)
    assert "end = find_pos + len(txt)" in src


def test_chunk_boundary_source_predicted_append_end():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted.append(end)" in src


def test_chunk_boundary_source_pos_end_plus_one():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos = end + 1" in src


def test_chunk_boundary_source_gt_positions_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions: list[int] = []" in src


def test_chunk_boundary_source_missing_markers_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_chunk_boundary_source_search_from_init_zero():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_source_anchor_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for a in anchors:" in src


def test_chunk_boundary_source_marker_default_empty():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("marker", "")' in src


def test_chunk_boundary_source_position_default_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


def test_chunk_boundary_source_find_pos_marker_ternary():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(marker, search_from) if marker else -1" in src


def test_chunk_boundary_source_missing_markers_append():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers.append(marker)" in src


def test_chunk_boundary_source_position_before_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'if position == "before":' in src


def test_chunk_boundary_source_gt_positions_before_append():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions.append(find_pos)" in src


def test_chunk_boundary_source_gt_positions_after_append():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions.append(find_pos + len(marker))" in src


def test_chunk_boundary_source_search_from_advance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = find_pos + len(marker)" in src


def test_chunk_boundary_source_pairs_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_chunk_boundary_source_used_pred_used_gt_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_chunk_boundary_source_double_for_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for pi, pv in enumerate(predicted):" in src
    assert "for gi, gv in enumerate(gt_positions):" in src


def test_chunk_boundary_source_distance_abs():
    src = inspect.getsource(chunk_boundary_prf)
    assert "d = abs(pv - gv)" in src


def test_chunk_boundary_source_tolerance_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if d <= tolerance_chars:" in src


def test_chunk_boundary_source_pairs_append_tuple():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.append((d, pi, gi))" in src


def test_chunk_boundary_source_pairs_sort_lambda():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_chunk_boundary_source_matched_init_zero():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched = 0" in src


def test_chunk_boundary_source_skip_used_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if pi in used_pred or gi in used_gt:" in src
    assert "continue" in src


def test_chunk_boundary_source_used_pred_add():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred.add(pi)" in src


def test_chunk_boundary_source_used_gt_add():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_gt.add(gi)" in src


def test_chunk_boundary_source_matched_increment():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src


def test_chunk_boundary_source_num_pred_num_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "num_pred = len(predicted)" in src
    assert "num_gt = len(gt_positions)" in src


def test_chunk_boundary_source_precision_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if num_pred == 0:" in src
    assert 'out["chunk_boundary_precision"] = _ratio(matched / num_pred)' in src


def test_chunk_boundary_source_recall_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if num_gt == 0:" in src
    assert 'out["chunk_boundary_recall"] = _ratio(matched / num_gt)' in src


def test_chunk_boundary_source_f1_uses_p_val_r_val():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'p_val = out["chunk_boundary_precision"]["value"]' in src
    assert 'r_val = out["chunk_boundary_recall"]["value"]' in src


def test_chunk_boundary_source_f1_none_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if p_val is None or r_val is None:" in src


def test_chunk_boundary_source_f1_denom_zero_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom = p_val + r_val" in src
    assert "if denom <= 0:" in src


def test_chunk_boundary_source_f1_formula():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_chunk_boundary_source_tolerance_chars_output():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}' in src


def test_chunk_boundary_source_missing_markers_output_conditional():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if missing_markers:" in src
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src


# ---------- figure_caption_prf 行为深度第六批 ----------


def test_figure_caption_returns_dict_type():
    r = figure_caption_prf({"chunks": []}, None)
    assert isinstance(r, dict)


def test_figure_caption_keys_count_is_3():
    r = figure_caption_prf({}, None)
    assert len(r) == 3


def test_figure_caption_precision_is_dict():
    r = figure_caption_prf({}, None)
    assert isinstance(r["figure_caption_precision"], dict)


def test_figure_caption_recall_is_dict():
    r = figure_caption_prf({}, None)
    assert isinstance(r["figure_caption_recall"], dict)


def test_figure_caption_f1_is_dict():
    r = figure_caption_prf({}, None)
    assert isinstance(r["figure_caption_f1"], dict)


def test_figure_caption_precision_value_is_none():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_precision"]["value"] is None


def test_figure_caption_precision_reason_constant():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_recall_value_is_none():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_recall"]["value"] is None


def test_figure_caption_recall_reason_constant():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_recall"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_f1_value_is_none():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_f1"]["value"] is None


def test_figure_caption_f1_reason_constant():
    r = figure_caption_prf({}, None)
    assert r["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_full_document_and_annotation():
    """figure_caption 无论输入都给 null."""
    doc = {
        "elements": [{"type": "image"}, {"type": "caption"}],
        "chunks": [{"text": "x"}],
    }
    ann = {"figure_caption_pairs": [{"figure": "f1", "caption": "c1"}]}
    r = figure_caption_prf(doc, ann)
    assert r["figure_caption_precision"]["value"] is None


def test_figure_caption_with_annotation_none():
    r = figure_caption_prf({"chunks": []}, None)
    assert r["figure_caption_recall"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_document_none():
    r = figure_caption_prf(None, {"x": 1})
    assert r["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_with_both_none():
    r = figure_caption_prf(None, None)
    assert r["figure_caption_precision"]["value"] is None


def test_figure_caption_idempotent():
    r1 = figure_caption_prf({}, {})
    r2 = figure_caption_prf({}, {})
    assert r1 == r2


def test_figure_caption_does_not_mutate_inputs():
    doc = {"chunks": [{"text": "x"}]}
    ann = {"figure_caption_pairs": [1, 2]}
    doc_before = repr(doc)
    ann_before = repr(ann)
    figure_caption_prf(doc, ann)
    assert repr(doc) == doc_before
    assert repr(ann) == ann_before


# ---------- chunk_boundary_prf 行为深度第六批 ----------


def test_chunk_boundary_document_none_with_full_annotation():
    """document None 时忽略 annotation."""
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    r = chunk_boundary_prf(None, ann)
    assert r["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert r["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert r["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_document_none_tolerance_recorded():
    r = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert r["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_no_annotation_with_document_present():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, None)
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_empty_annotation_dict():
    """空 dict 是 falsy，走 no_annotation 分支."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {})
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_truthy_no_anchors():
    """truthy annotation 但缺 chunk_boundary_anchors."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {"other_key": "value"})
    # anchors = [] → no_ground_truth_anchors 分支
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_annotation_truthy_empty_anchors():
    """truthy annotation + 显式空 anchors 列表."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_one_chunk_with_empty_anchors():
    """<2 chunks + 无 anchors → no_predicted_boundaries."""
    doc = {"chunks": [{"text": "a"}]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert r["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_one_chunk_with_anchors_recall_zero():
    """<2 chunks + 有 anchors → recall = 0.0 ratio."""
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 有 anchors，所以 recall = ratio(0.0)
    assert r["chunk_boundary_recall"]["value"] == 0.0
    assert r["chunk_boundary_recall"]["reason"] is None
    assert r["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_two_chunks_full_match_position_after():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    # stream = "hello world"
    # predicted 边界 = 5 (hello 末尾)
    # anchor after hello = 5 (find_pos(0) + len("hello") = 5)
    # match distance 0 <= 30
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_two_chunks_full_match_position_before():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann)
    # predicted = 5 (hello end)
    # anchor before world = find_pos("world") = 6
    # distance = 1 <= 30
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_repeated_marker_sequential_match():
    """重复 marker 应顺序定位（不重复命中同一位置）."""
    doc = {"chunks": [{"text": "x"}, {"text": "x"}, {"text": "y"}]}
    # 两个 anchor "x" after → 应分别命中 position 1 和 3
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # stream = "x x y"
    # norm_chunks = ["x", "x", "y"]
    # predicted boundaries: end of "x" (1), end of "x" (3)
    # gt positions for "x" after: find_pos=0 + len=1 → 1; find_pos=2 + len=1 → 3
    # match distance 0 + 0 → both match
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_marker_not_found_in_stream():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"}
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # marker 找不到 → missing_markers + gt_positions = []
    assert "_missing_markers" in r
    assert r["_missing_markers"]["value"] == ["nonexistent"]
    # num_gt = 0 → recall null
    assert r["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_anchor_empty_marker():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"}
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # 空 marker → find_pos = -1 → missing
    assert "_missing_markers" in r


def test_chunk_boundary_anchor_missing_marker_key():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"position": "after"}  # no marker
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # marker 默认 "" → missing
    assert "_missing_markers" in r


def test_chunk_boundary_anchor_missing_position_key():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "hello"}  # no position → default "after"
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # default position = "after"
    assert r["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_outside_tolerance():
    doc = {"chunks": [{"text": "aaaaaaaaaa"}, {"text": "bbbbbbbbbb"}]}  # 10 + 10
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "bbbbbbbbbb", "position": "before"}
        ]
    }
    r = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # predicted boundary = 10 (end of "aaaaaaaaaa")
    # gt before "bbbbbbbbbb" = 11 (find_pos after space)
    # distance = 1 ≤ 2 → match
    # Actually, let me check: stream = "aaaaaaaaaa bbbbbbbbbb"
    # norm_chunks = ["aaaaaaaaaa", "bbbbbbbbbb"]
    # stream.find("aaaaaaaaaa", 0) = 0, end = 10, predicted = [10], pos = 11
    # stream.find("bbbbbbbbbb", 11) = 11, before = 11
    # distance = |10 - 11| = 1 ≤ 2 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_outside_tolerance_no_match():
    doc = {
        "chunks": [
            {"text": "aaaaaaaaaa"},
            {"text": "bbbbbbbbbb"},
            {"text": "cccccccccc"},
        ]
    }
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "cccccccccc", "position": "before"}
        ]
    }
    r = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # predicted = [10, 21] (end of "aaaaaaaaaa" and "bbbbbbbbbb")
    # gt before "cccccccccc" = 22
    # distances: |10-22|=12, |21-22|=1 → match the second
    assert r["chunk_boundary_precision"]["value"] == 0.5


def test_chunk_boundary_tiny_tolerance_with_match():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "ab cd", predicted = [2], gt after ab = 2
    # distance 0 ≤ 0 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_zero_tolerance_no_match():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "cd", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted = [2], gt before cd = 3
    # distance 1 > 0 → no match
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_f1_when_precision_zero_recall_nonzero():
    """Precision 0 + Recall > 0 → F1 = 0."""
    doc = {
        "chunks": [
            {"text": "x"},
            {"text": "y"},
            {"text": "z"},
        ]
    }
    # 2 predicted boundaries (after x, after y), 0 anchor 匹配
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"}
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # marker 找不到 → gt_positions = [], recall null
    # precision: num_pred=2, matched=0 → 0.0 ratio
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    # f1: p_val=0.0, r_val=None → null precision_or_recall_not_evaluated
    assert r["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_three_chunks_two_boundaries_with_match():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # stream = "alpha beta gamma"
    # predicted: end of alpha=5, end of beta=10
    # gt: 5 (after alpha), 10 (after beta)
    # both match
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_chunk_text_none_skipped():
    """chunk text 是 None 时，被 normalize 处理为 ''."""
    doc = {"chunks": [{"text": None}, {"text": "hello"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann)
    # norm_chunks = ["", "hello"]
    # stream = " hello" → normalize → "hello"
    # Actually " ".join(["", "hello"]) = " hello" → normalize → "hello"
    # predicted: end of "" = 0; end of "hello" skipped (last chunk)
    # gt before hello = 0
    # distance 0 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunk_missing_text_key():
    doc = {"chunks": [{}, {"text": "hello"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann)
    # norm_chunks = ["", "hello"]
    assert "_tolerance_chars" in r


def test_chunk_boundary_tolerance_chars_recorded():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=99)
    assert r["_tolerance_chars"]["value"] == 99
    assert r["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_does_not_mutate_document():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    doc_before = repr(doc)
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    ann_before = repr(ann)
    chunk_boundary_prf(doc, ann)
    assert repr(doc) == doc_before
    assert repr(ann) == ann_before


def test_chunk_boundary_returns_dict_of_dicts():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert isinstance(r, dict)
    for k, v in r.items():
        assert isinstance(v, dict)


def test_chunk_boundary_value_or_reason_in_each_metric():
    """每个 metric dict 至少含 value 或 reason 键."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    for k, v in r.items():
        assert "value" in v
        assert "reason" in v


def test_chunk_boundary_idempotent():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, ann)
    r2 = chunk_boundary_prf(doc, ann)
    assert r1 == r2


def test_chunk_boundary_default_tolerance_30():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert r["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_positional_args():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, 50)
    assert r["_tolerance_chars"]["value"] == 50


def test_chunk_boundary_kwargs_only():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(
        document=doc, annotation=ann, tolerance_chars=15
    )
    assert r["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_doc_with_no_chunks_key():
    """document 缺 chunks 键 → chunks = [] → <2 chunks 分支."""
    r = chunk_boundary_prf({}, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_annotation_no_anchors_key():
    """annotation 缺 chunk_boundary_anchors 键 → anchors = []."""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {"other": "value"})
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_doc_none_and_annotation_none():
    r = chunk_boundary_prf(None, None)
    assert r["chunk_boundary_precision"]["reason"] == "pipeline_failed"


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "importlib",
        "platform",
        "subprocess",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_eighth(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第三批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_counter():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_imports_any():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_imports_normalize_text():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_imports_null_ratio():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_parser_does_not_emit_constant():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_two_functions():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src
    assert "def chunk_boundary_prf(" in src


def test_module_source_no_relative_import_above_app_or_eval():
    src = inspect.getsource(amod)
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from .") and "evaluation" not in stripped and "app" not in stripped:
            assert False, f"Found unexpected relative import: {line}"


def test_module_source_no_star_import():
    src = inspect.getsource(amod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(amod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(amod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(amod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(amod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    src = inspect.getsource(amod)
    lines = src.split("\n")
    has_class = any(line.lstrip().startswith("class ") for line in lines)
    assert not has_class


def test_module_source_no_eval():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(amod)
    assert "compile(" not in src


def test_module_source_no_open():
    src = inspect.getsource(amod)
    assert "open(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(amod)
    assert "unlink" not in src


def test_module_source_no_write():
    src = inspect.getsource(amod)
    assert ".write(" not in src


def test_module_source_no_print():
    src = inspect.getsource(amod)
    assert "print(" not in src


def test_module_source_no_sys():
    src = inspect.getsource(amod)
    assert "import sys" not in src


def test_module_source_no_os():
    src = inspect.getsource(amod)
    assert "import os" not in src


def test_module_source_docstring_present():
    assert amod.__doc__ is not None


def test_module_source_docstring_mentions_人工标注():
    assert "人工标注" in amod.__doc__


def test_module_source_docstring_mentions_figure_caption():
    assert "figure_caption" in amod.__doc__


def test_module_source_docstring_mentions_chunk_boundary():
    assert "chunk_boundary" in amod.__doc__


def test_module_source_docstring_mentions_parser_does_not_emit():
    assert "parser_does_not_emit_relations" in amod.__doc__ or "parser 当前不输出" in amod.__doc__


def test_module_source_docstring_mentions_tolerance():
    assert "tolerance" in amod.__doc__.lower() or "容差" in amod.__doc__


def test_module_source_no_logging_import():
    src = inspect.getsource(amod)
    assert "import logging" not in src


def test_module_source_no_argparse():
    src = inspect.getsource(amod)
    assert "argparse" not in src


def test_module_source_no_json():
    src = inspect.getsource(amod)
    assert "import json" not in src


def test_module_source_no_pathlib():
    src = inspect.getsource(amod)
    assert "pathlib" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_all_3_entries_correct():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_module_source_const_at_module_level():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in dir(amod)


# ---------- signatures 精确补强第三批 ----------


def test_signature_figure_caption_prf_two_params():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "document"
    assert params[1].name == "annotation"


def test_signature_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_figure_caption_prf_no_varargs():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_three_params():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert params[0].name == "document"
    assert params[1].name == "annotation"
    assert params[2].name == "tolerance_chars"


def test_signature_chunk_boundary_prf_doc_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[2].default == 30


def test_signature_chunk_boundary_prf_no_varargs():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_return_annotation_dict():
    sig = inspect.signature(figure_caption_prf)
    # from __future__ import annotations → 字符串
    ra = sig.return_annotation
    assert "dict" in ra


def test_signature_chunk_boundary_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    ra = sig.return_annotation
    assert "dict" in ra


def test_signature_parser_does_not_emit_constant_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_signature_parser_does_not_emit_constant_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_alias_identity():
    """reason_const 是同一个常量."""
    assert reason_const is PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- 模块整体合理性补强第三批 ----------


def test_module_has_docstring():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 10


def test_module_has_all_attribute():
    assert hasattr(amod, "__all__")


def test_module_all_is_list():
    assert isinstance(amod.__all__, list)


def test_module_all_length_3():
    assert len(amod.__all__) == 3


def test_module_all_entries_unique():
    assert len(set(amod.__all__)) == 3


def test_module_all_entries_are_str():
    for entry in amod.__all__:
        assert isinstance(entry, str)


def test_module_all_3_entries_correct():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_namespace_has_2_callables():
    callables = [
        (name, obj) for name, obj in vars(amod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == amod.__name__
    ]
    assert len(callables) == 2


def test_module_namespace_callable_names():
    callables = {
        name for name, obj in vars(amod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == amod.__name__
    }
    assert callables == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_namespace_has_constant():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in vars(amod)


def test_module_no_user_classes():
    classes = [
        (name, obj) for name, obj in vars(amod).items()
        if isinstance(obj, type) and obj.__module__ == amod.__name__
    ]
    assert len(classes) == 0


def test_module_name_is_evaluation_annotation_metrics():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_file_ends_with_annotation_metrics_py():
    assert amod.__file__.endswith("annotation_metrics.py")


def test_module_function_module_eq_amod():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_module_function_name_correct():
    assert figure_caption_prf.__name__ == "figure_caption_prf"
    assert chunk_boundary_prf.__name__ == "chunk_boundary_prf"


def test_module_constant_type_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_callable_count_2():
    """模块内定义的 FunctionType 数量（排除导入的）."""
    funcs = [
        obj for name, obj in vars(amod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == amod.__name__
    ]
    assert len(funcs) == 2


# ---------- 端到端集成补强第三批 ----------


def test_e2e_figure_caption_always_returns_three_metrics():
    """无论输入如何，figure_caption 总返回 3 个 metric."""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        (None, {"x": 1}),
        ({"chunks": [{"text": "a"}]}, {"figure_caption_pairs": [1]}),
    ]
    for doc, ann in inputs:
        r = figure_caption_prf(doc, ann)
        assert len(r) == 3
        assert set(r.keys()) == {
            "figure_caption_precision",
            "figure_caption_recall",
            "figure_caption_f1",
        }


def test_e2e_figure_caption_idempotent():
    r1 = figure_caption_prf({"chunks": []}, {})
    r2 = figure_caption_prf({"chunks": []}, {})
    assert r1 == r2


def test_e2e_figure_caption_does_not_mutate():
    doc = {"chunks": [{"text": "a"}]}
    ann = {"figure_caption_pairs": [1, 2]}
    doc_before = repr(doc)
    ann_before = repr(ann)
    figure_caption_prf(doc, ann)
    assert repr(doc) == doc_before
    assert repr(ann) == ann_before


def test_e2e_figure_caption_positional_args():
    r1 = figure_caption_prf({"chunks": []}, {})
    r2 = figure_caption_prf({"chunks": []}, annotation={})
    assert r1 == r2


def test_e2e_chunk_boundary_does_not_mutate_doc():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
        ]
    }
    doc_before = repr(doc)
    chunk_boundary_prf(doc, ann)
    assert repr(doc) == doc_before


def test_e2e_chunk_boundary_does_not_mutate_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    ann_before = repr(ann)
    chunk_boundary_prf(doc, ann)
    assert repr(ann) == ann_before


def test_e2e_chunk_boundary_idempotent():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, ann)
    r2 = chunk_boundary_prf(doc, ann)
    assert r1 == r2


def test_e2e_chunk_boundary_positional_args():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r1 = chunk_boundary_prf(doc, ann)
    r2 = chunk_boundary_prf(doc, ann, 30)
    assert r1 == r2


def test_e2e_chunk_boundary_kwargs():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(
        document=doc, annotation=ann, tolerance_chars=10
    )
    assert r["_tolerance_chars"]["value"] == 10


def test_e2e_chunk_boundary_default_tolerance():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert r["_tolerance_chars"]["value"] == 30


def test_e2e_chunk_boundary_empty_chunks_list():
    r = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_document_no_chunks_key():
    r = chunk_boundary_prf({}, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_annotation_no_anchors_key():
    r = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"other_key": "value"},
    )
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_e2e_chunk_boundary_returns_dict_of_dicts():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert isinstance(r, dict)
    for v in r.values():
        assert isinstance(v, dict)


def test_e2e_chunk_boundary_value_or_reason_in_each_metric():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    for v in r.values():
        assert "value" in v
        assert "reason" in v


def test_e2e_full_pipeline_with_metrics():
    """模拟完整流程：figure_caption + chunk_boundary 一起调用."""
    doc = {
        "elements": [{"type": "image"}, {"type": "caption"}],
        "chunks": [{"text": "a"}, {"text": "b"}],
    }
    ann = {
        "chunk_boundary_anchors": [{"marker": "a", "position": "after"}],
        "figure_caption_pairs": [{"figure": "f", "caption": "c"}],
    }
    fc = figure_caption_prf(doc, ann)
    cb = chunk_boundary_prf(doc, ann)
    metrics = {}
    metrics.update(fc)
    metrics.update(cb)
    # 6 metric + _tolerance_chars
    assert len(metrics) == 7
    assert "figure_caption_precision" in metrics
    assert "chunk_boundary_precision" in metrics


def test_e2e_chunk_boundary_three_chunks_partial_match():
    doc = {
        "chunks": [
            {"text": "alpha"},
            {"text": "beta"},
            {"text": "gamma"},
        ]
    }
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # match
            {"marker": "nonexistent", "position": "after"},  # missing
        ]
    }
    r = chunk_boundary_prf(doc, ann)
    # predicted = 2 boundaries, gt_positions = 1 (alpha)
    # match: 1
    # precision = 1/2 = 0.5, recall = 1/1 = 1.0
    assert r["chunk_boundary_precision"]["value"] == 0.5
    assert r["chunk_boundary_recall"]["value"] == 1.0
    # f1 = 2 * 0.5 * 1.0 / (0.5 + 1.0) = 1/1.5 = 0.6667
    assert abs(r["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-6


def test_e2e_chunk_boundary_with_long_chunks():
    """长 chunk 文本场景."""
    long_text_a = "word " * 100
    long_text_b = "term " * 100
    doc = {"chunks": [{"text": long_text_a}, {"text": long_text_b}]}
    ann = {"chunk_boundary_anchors": [{"marker": "word", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann)
    # 至少不抛异常
    assert "chunk_boundary_precision" in r


def test_e2e_chunk_boundary_with_unicode_text():
    doc = {"chunks": [{"text": "中文"}, {"text": "测试"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "中文", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_whitespace_text():
    """含大量空白的 chunk text 会被 normalize 压扁."""
    doc = {"chunks": [{"text": "  a  b  "}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a b", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    # stream = normalize("a b c") = "a b c"
    # norm_chunks = ["a b", "c"]
    # actually normalize("  a  b  ") = "a b"
    # stream = "a b c"
    # predicted: end of "a b" = 3
    # anchor after "a b" = find_pos(0) + len = 0 + 3 = 3
    # match
    assert r["chunk_boundary_precision"]["value"] == 1.0
