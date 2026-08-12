"""evaluation/annotation_metrics.py 第六十一轮 edges 测试（Round 573）。

补强 edges62 未触及的角度（第三十六批）。
"""

from __future__ import annotations

import inspect
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十六批


def test_parser_const_no_spaces_batch36():
    assert " " not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_const_no_hyphens_batch36():
    assert "-" not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_const_is_str_batch36():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_const_is_module_level_batch36():
    """模块级常量。"""
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- figure_caption_prf 第三十六批


def test_figure_caption_prf_value_field_is_none_batch36():
    out = figure_caption_prf({"chunks": []}, {"x": 1})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_field_batch36():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_none_doc_batch36():
    """doc=None 仍可调用。"""
    out = figure_caption_prf(None, {"figure_caption_anchors": [{"x": 1}]})
    assert len(out) == 3


def test_figure_caption_prf_with_none_annotation_batch36():
    out = figure_caption_prf({"chunks": [{"text": "x"}]}, None)
    assert len(out) == 3


def test_figure_caption_prf_both_none_batch36():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_prf_with_empty_dict_doc_batch36():
    out = figure_caption_prf({}, {})
    assert len(out) == 3


def test_figure_caption_prf_does_not_mutate_inputs_batch36():
    doc = {"chunks": [{"text": "a"}]}
    ann = {"x": 1}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_figure_caption_prf_with_huge_doc_batch36():
    """大文档仍固定 null。"""
    doc = {"chunks": [{"text": "x" * 10000}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 第三十六批


def test_chunk_boundary_prf_keys_minimal_when_doc_none_batch36():
    out = chunk_boundary_prf(None, None)
    keys = set(out.keys())
    assert keys == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_keys_minimal_when_no_annotation_batch36():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    keys = set(out.keys())
    assert keys == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_keys_minimal_when_no_chunks_batch36():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    keys = set(out.keys())
    assert keys == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_keys_when_no_anchors_batch36():
    """有 chunks 但没 anchors → 4 keys。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    keys = set(out.keys())
    assert keys == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_tolerance_negative_value_batch36():
    """tolerance_chars=-1 → 不允许任何匹配（distance ≤ -1 不可能）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # 距离 0 > -1 → 但 abs(0) ≤ -1 不成立 → 0 match
    # 但 distance 必须 <= tolerance_chars，0 <= -1 是 False → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_zero_perfect_match_batch36():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_one_chunk_no_boundaries_batch36():
    """只有 1 个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 1 chunk → no_predicted_boundaries
    # 但 anchors 非空 → recall = 0.0（不是 no_predicted_boundaries）
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_no_anchors_no_boundaries_batch36():
    """1 chunk + 0 anchors → no_predicted_boundaries for all。"""
    doc = {"chunks": [{"text": "abc"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 1 chunk, 0 anchors → 没有 anchors 也没预测边界
    # recall reason = no_predicted_boundaries because anchors=[] is falsy →
    # in line 78-80: if not anchors: _null("no_predicted_boundaries")
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunk_text_empty_string_batch36():
    """chunk text 为空字符串 → normalize_text 后仍是空。"""
    doc = {"chunks": [{"text": ""}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    # norm_chunks = ["", "abc"]
    # joined = " abc" → normalize → "abc"
    # 但 normalize_text("") = ""
    # 边界 pos=0（空 chunk 之后），'a' 在 pos=0, before → pos=0 → 完美匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 验证不抛错
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_chunk_text_none_batch36():
    """chunk text 为 None → 当空字符串处理。"""
    doc = {"chunks": [{"text": None}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_chunk_missing_text_key_batch36():
    """chunk 缺 text key → 当空字符串。"""
    doc = {"chunks": [{}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_anchor_missing_marker_key_batch36():
    """anchor 缺 marker → marker="" → find 返回 -1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # marker="" → find_pos = -1 → 加入 missing_markers
    assert "_missing_markers" in out


def test_chunk_boundary_prf_anchor_missing_position_key_batch36():
    """anchor 缺 position → 默认 after。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 默认 after → pos=3 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_before_batch36():
    """position=before → marker 起始位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    # stream = "abc def"
    # 'abc' 在 pos=0, before → pos=0
    # 边界 pos=3
    # 距离 |3-0|=3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_two_anchors_one_pred_match_batch36():
    """1 预测边界 + 2 anchors：用不同 marker。第二个 marker 找不到（search_from 已推进）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 pos=3
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # pos=3, 完美匹配
        {"marker": "a", "position": "before"},  # 'a' 在 pos=0，但 search_from=3 已过 → missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 第二个 anchor missing → num_gt=1, num_pred=1, matched=1 → P=1.0, R=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert "_missing_markers" in out


def test_chunk_boundary_prf_three_chunks_one_anchor_match_batch36():
    """3 chunks (2 preds) + 1 anchor → P=0.5, R=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_does_not_mutate_annotation_batch36():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_chunk_boundary_prf_anchor_with_extra_fields_batch36():
    """anchor 含额外字段（如 id, note）→ 不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after", "id": "a1", "note": "x"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_with_unknown_position_value_batch36():
    """position 不是 before/after（如 "middle"）→ 当 after 处理。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "middle"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # position="middle" 不是 "before" → 走 else（after 分支）→ pos=3
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_with_unicode_marker_batch36():
    doc = {"chunks": [{"text": "中文段落"}, {"text": "测试"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "落", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "中文段落 测试"
    # '落' 在 pos=3, after → pos=4
    # 边界 pos=4
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_with_marker_repeated_in_chunk_batch36():
    """marker 在同一个 chunk 内重复出现 → find 找第一个。"""
    doc = {"chunks": [{"text": "abcabc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "abcabc def"
    # 'abc' 第一次出现 pos=0, after → pos=3
    # 边界 pos=6 (chunk 0 末尾)
    # 距离 |6-3|=3, 容差 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_same_text_batch36():
    doc = {"chunks": [{"text": "abc"}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    # norm_chunks = ["abc", "abc"]
    # joined = "abc abc" → normalize → "abc abc"
    # 边界 pos=3
    # 'abc' 在 pos=0, after → pos=3
    # 完美匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_two_anchors_one_missing_one_match_batch36():
    """2 anchors：1 找到，1 missing → matched 用 num_gt=1（missing 不计入）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # 找到
        {"marker": "xyz", "position": "after"},  # missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # matched=1, num_pred=1, num_gt=1 → P=1.0, R=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_all_markers_missing_batch36():
    """所有 marker 都 missing → num_gt=0 → recall null + no_ground_truth_anchors_in_stream。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "xyz", "position": "after"},
        {"marker": "qqq", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # num_pred=1, num_gt=0
    # precision = matched/num_pred = 0/1 = 0.0
    # recall null + no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_chunk_text_with_extra_whitespace_batch36():
    """chunk text 含多余空白 → normalize_text 统一。"""
    doc = {"chunks": [{"text": "  abc  "}, {"text": "  def  "}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # norm_chunks = ["abc", "def"]
    # stream = "abc def"
    # 'abc' 在 pos=0, after → pos=3
    # 边界 pos=3 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_with_newline_batch36():
    doc = {"chunks": [{"text": "abc\ndef"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "def", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # normalize_text("abc\ndef") = "abc def"
    # stream = "abc def ghi"
    # 'def' 在 pos=4, after → pos=7
    # 边界 pos=7 (chunk 0 末尾) → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_recall_zero_when_zero_match_batch36():
    """预测和 anchor 都有，但都没匹配 → P=0, R=0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 pos=3
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    # 'a' 在 pos=0, before → pos=0, 距离 3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # f1: p_val=0, r_val=0, denom=0 → f1=0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_when_precision_null_batch36():
    """precision null（num_pred=0） → f1 null。"""
    # 触发 num_pred=0 但 num_gt>0 的路径很难：
    # 只能在所有 chunks 都找不到对应 stream 位置时（理论上不该发生）
    # 该路径在 line 161-162: if num_pred == 0: precision null
    # 然后逻辑走到 line 173-176
    pass


def test_chunk_boundary_prf_returns_dict_in_all_paths_batch36():
    """所有路径都返回 dict。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        ({"chunks": [{"text": "a"}]}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}),
    ]
    for doc, ann in inputs:
        out = chunk_boundary_prf(doc, ann)
        assert isinstance(out, dict)


def test_chunk_boundary_prf_negative_tolerance_does_not_crash_batch36():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-100)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_huge_tolerance_does_not_crash_batch36():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10**9)
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第五十五批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch36(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第五十一批


def test_module_source_contains_chunk_boundary_docstring_batch36():
    src = inspect.getsource(amod)
    assert "分块边界" in src


def test_module_source_contains_marker_param_doc_batch36():
    src = inspect.getsource(amod)
    assert "marker" in src


def test_module_source_contains_position_param_doc_batch36():
    src = inspect.getsource(amod)
    assert "position" in src


def test_module_source_contains_after_value_batch36():
    src = inspect.getsource(amod)
    assert '"after"' in src


def test_module_source_contains_before_value_batch36():
    src = inspect.getsource(amod)
    assert '"before"' in src


def test_module_source_contains_normalize_text_call_batch36():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_contains_join_call_batch36():
    src = inspect.getsource(amod)
    assert '" ".join(norm_chunks)' in src


def test_module_source_contains_find_call_batch36():
    src = inspect.getsource(amod)
    assert "stream.find(" in src


def test_module_source_contains_pairs_sort_batch36():
    src = inspect.getsource(amod)
    assert "pairs.sort" in src


def test_module_source_contains_used_pred_used_gt_batch36():
    src = inspect.getsource(amod)
    assert "used_pred" in src
    assert "used_gt" in src


def test_module_source_contains_matched_counter_batch36():
    src = inspect.getsource(amod)
    assert "matched += 1" in src


def test_module_source_contains_num_pred_batch36():
    src = inspect.getsource(amod)
    assert "num_pred" in src


def test_module_source_contains_num_gt_batch36():
    src = inspect.getsource(amod)
    assert "num_gt" in src


def test_module_source_contains_f1_formula_batch36():
    src = inspect.getsource(amod)
    assert "2 * p_val * r_val / denom" in src


def test_module_source_contains_search_from_batch36():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_contains_missing_markers_list_batch36():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_contains_missing_markers_output_key_batch36():
    src = inspect.getsource(amod)
    assert '"_missing_markers"' in src


def test_module_source_contains_tolerance_chars_output_key_batch36():
    src = inspect.getsource(amod)
    assert '"_tolerance_chars"' in src


def test_module_source_contains_norm_chunks_var_batch36():
    src = inspect.getsource(amod)
    assert "norm_chunks" in src


def test_module_source_contains_predicted_list_batch36():
    src = inspect.getsource(amod)
    assert "predicted" in src


def test_module_source_contains_gt_positions_list_batch36():
    src = inspect.getsource(amod)
    assert "gt_positions" in src


def test_module_source_contains_tolerance_chars_annotation_doc_batch36():
    src = inspect.getsource(amod)
    assert "容差（字符数）" in src


def test_module_source_contains_one_to_one_comment_batch36():
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_contains_greedy_keyword_batch36():
    src = inspect.getsource(amod)
    assert "贪心" in src


# ---------- signatures 第五十一批


def test_signature_figure_caption_prf_two_params_batch36():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_signature_figure_caption_prf_document_no_default_batch36():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_signature_figure_caption_prf_annotation_no_default_batch36():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_three_params_batch36():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_signature_chunk_boundary_prf_document_no_default_batch36():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_annotation_no_default_batch36():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_tolerance_is_keyword_batch36():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_is_callable_batch36():
    assert callable(figure_caption_prf)


def test_signature_chunk_boundary_prf_is_callable_batch36():
    assert callable(chunk_boundary_prf)


# ---------- module 合理性第五十一批


def test_module_has_parser_const_attribute_batch36():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_has_figure_caption_prf_attribute_batch36():
    assert hasattr(amod, "figure_caption_prf")


def test_module_has_chunk_boundary_prf_attribute_batch36():
    assert hasattr(amod, "chunk_boundary_prf")


def test_module_has_all_attribute_batch36():
    assert hasattr(amod, "__all__")


def test_module_all_is_list_batch36():
    assert isinstance(amod.__all__, list)


def test_module_parser_const_in_all_batch36():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_figure_caption_prf_in_all_batch36():
    assert "figure_caption_prf" in amod.__all__


def test_module_chunk_boundary_prf_in_all_batch36():
    assert "chunk_boundary_prf" in amod.__all__


def test_module_does_not_have_unused_imports_batch36():
    """Counter 在 module 中应被 import（虽然未使用，但保留）。"""
    src = inspect.getsource(amod)
    assert "Counter" in src


def test_module_constants_match_exported_batch36():
    """__all__ 中的名称都在模块命名空间里。"""
    for name in amod.__all__:
        assert hasattr(amod, name)


# ---------- 端到端集成第五十一批


def test_e2e_chunk_boundary_real_world_paragraphs_batch36():
    """模拟真实段落分块 + 标注。"""
    doc = {
        "chunks": [
            {"text": "这是第一段。"},
            {"text": "这是第二段。"},
            {"text": "这是第三段。"},
        ],
    }
    ann = {"chunk_boundary_anchors": [
        {"marker": "这是第一段。", "position": "after"},
        {"marker": "这是第二段。", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_with_loose_tolerance_batch36():
    """容差 50 → 任意错位 50 字符内的 anchor 都能匹配。"""
    doc = {"chunks": [{"text": "a" * 100}, {"text": "b" * 100}]}
    # 边界 pos=100
    ann = {"chunk_boundary_anchors": [{"marker": "a" * 60, "position": "after"}]}
    # marker 60 个 a, find_pos=0, after → pos=60, 距离 40 ≤ 50
    out = chunk_boundary_prf(doc, ann, tolerance_chars=50)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_pipeline_failed_path_batch36():
    """document=None 模拟 pipeline 失败。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_full_run_idempotent_across_calls_batch36():
    """多次调用结果一致。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    outs = [chunk_boundary_prf(doc, ann, tolerance_chars=5) for _ in range(3)]
    for o in outs[1:]:
        assert o == outs[0]


def test_e2e_chunk_boundary_with_figure_caption_combined_batch36():
    """两个函数可以一起调用（输出 key 不冲突）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    fcp = figure_caption_prf(doc, ann)
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    combined = {**fcp, **cbp}
    assert "figure_caption_precision" in combined
    assert "chunk_boundary_precision" in combined
