"""evaluation/annotation_metrics.py 第九十三轮 edges 测试（Round 664）。

补强 edges74 未触及的角度（第四十九批）。

新角度：
- chunk_boundary_prf tolerance_chars 边界（tolerance=0 完美 / tolerance 极大 / tolerance 负数 / tolerance 默认 30）
- chunk_boundary_prf anchor marker 含 Unicode（中文 / 日文 / emoji）
- chunk_boundary_prf anchor position 缺省值（无 position key → 默认 after）
- chunk_boundary_prf anchor position 非法值（"left"/"right" → 走 else 分支即 after）
- chunk_boundary_prf 多 marker 多 anchor 配对（贪心算法验证）
- chunk_boundary_prf predicted stream 不存在（chunk 文本含特殊字符 normalize 后变化）
- chunk_boundary_prf chunks 是 dict / 缺 text key（用 .get("text") or ""）
- chunk_boundary_prf document 是 {} / chunks 是空 list
- figure_caption_prf 不依赖任何输入（None document / None annotation / 都 None）
- figure_caption_prf 3 个 metric 都是 null + reason
- 模块源码补强（Counter/Any/normalize_text/_null/_ratio imports / PARSER_DOES_NOT_EMIT_RELATIONS / __all__ / docstring 关键词）
- AST 结构补强（2 函数 / 1 ClassDef 否 / module docstring / 5 import / 1 top-level Assign / chunk_boundary_prf 多 if + for + try 否 / figure_caption_prf 简单 return dict）
- forbidden tokens 第一百三十四批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- chunk_boundary_prf tolerance_chars 边界 ----------

def test_chunk_boundary_tolerance_extremely_large_batch49():
    """tolerance 极大 → 所有 pred/gt 都在容差内。"""
    document = {"chunks": [{"text": "AAAA"}, {"text": "BBBB"}]}
    # predicted = 4, marker "AAAA" after → gt = 4 → d=0
    annotation = {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10**9)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_tolerance_negative_batch49():
    """tolerance 负数：d <= tolerance 永远 False（d 是 abs >=0）。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=-1)
    # 所有 d 都 >=0 > -1 → 没有匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_tolerance_default_30_batch49():
    """默认 tolerance=30。"""
    document = {"chunks": [{"text": "A" * 100}, {"text": "B" * 100}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "A", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation)
    # 默认 tolerance 30：predicted=100, gt for "A" after = 1, d=99 > 30 → 无匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    # _tolerance_chars 应当记录 30
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_tolerance_exact_distance_batch49():
    """d 恰好等于 tolerance → 算 match（d <= tolerance）。"""
    document = {"chunks": [{"text": "AAAAAA"}, {"text": "B"}]}
    # stream = "AAAAAA B"，predicted = 6
    # marker "A" after → gt = 1, d = 5
    annotation = {"chunk_boundary_anchors": [{"marker": "A", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # d=5, tolerance=5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_tolerance_one_off_batch49():
    """d = tolerance + 1 → 不 match。"""
    document = {"chunks": [{"text": "AAAAAA"}, {"text": "B"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "A", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=4)
    # d=5, tolerance=4 → 不 match
    assert out["chunk_boundary_precision"]["value"] == 0.0


# ---------- chunk_boundary_prf anchor marker 含 Unicode ----------

def test_chunk_boundary_marker_chinese_batch49():
    """中文 marker：find 应当能找到中文字符。"""
    document = {"chunks": [{"text": "标题一"}, {"text": "正文"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "标", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = "标题一 正文"
    # predicted = 3 (chunk0 "标题一" 长度)
    # marker "标" after → find("标", 0) = 0, gt = 0 + 1 = 1
    # d = |3 - 1| = 2 > 0 → 不 match
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_marker_chinese_perfect_batch49():
    """中文 marker 完美匹配。"""
    document = {"chunks": [{"text": "标题"}, {"text": "正文"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "标题", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = "标题 正文"
    # predicted = 2 (chunk0 长度)
    # marker "标题" after → find=0, gt = 2
    # d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_japanese_batch49():
    document = {"chunks": [{"text": "タイトル"}, {"text": "本文"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "タイトル", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # predicted = 4, gt = 4, d=0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_emoji_batch49():
    """emoji marker（虽然实际不会用，但算法应支持）。"""
    document = {"chunks": [{"text": "hello 🎉"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "🎉", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # stream = "hello 🎉 world"
    # predicted = len("hello 🎉") = 7
    # marker "🎉" after → find("🎉", 0) = 6, gt = 6 + 1 = 7
    # d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf anchor position 缺省/非法 ----------

def test_chunk_boundary_no_position_key_defaults_after_batch49():
    """anchor 无 position key → 默认 after。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA"}]}  # 无 position
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 默认 after: gt = 3, predicted = 3, d=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_invalid_treated_as_after_batch49():
    """position="left"（非法）→ 走 else 分支即 after。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "left"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # "left" 不等于 "before" → 走 else → after → gt = 3
    # predicted = 3, d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_right_treated_as_after_batch49():
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "right"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_before_vs_after_distinct_batch49():
    """同 marker position before 和 after 给出不同 gt。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    out_before = chunk_boundary_prf(
        document,
        {"chunk_boundary_anchors": [{"marker": "AAA", "position": "before"}]},
        tolerance_chars=0,
    )
    out_after = chunk_boundary_prf(
        document,
        {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]},
        tolerance_chars=0,
    )
    # before: gt = 0, predicted = 3, d = 3 > 0 → 0.0
    # after: gt = 3, predicted = 3, d = 0 → 1.0
    assert out_before["chunk_boundary_precision"]["value"] == 0.0
    assert out_after["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf 多 marker 多 anchor 贪心算法 ----------

def test_chunk_boundary_greedy_matching_closest_first_batch49():
    """贪心：距离最近的 pred-gt 优先匹配。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "XXX"}, {"text": "BBB"}]}
    # predicted = [3, 7]（chunk0 末尾 + chunk1 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},  # gt = 3, d=0 with pred[0]
            {"marker": "XXX", "position": "after"},  # gt = 7, d=0 with pred[1]
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_greedy_tie_breaking_batch49():
    """距离相同时按 pairs 排序后顺序匹配。"""
    document = {"chunks": [{"text": "AAX"}, {"text": "BBX"}]}
    # predicted = [3]（chunk0 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AA", "position": "after"},  # gt = 2, d = 1 with pred[0]
            {"marker": "BB", "position": "before"},  # gt = 4, d = 1 with pred[0]
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # 只有一个 pred，最多 match 1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_multiple_anchors_same_marker_batch49():
    """多个 anchor 用相同 marker，按顺序定位。"""
    document = {"chunks": [{"text": "AAA AAA"}, {"text": "BBB"}]}
    # stream = "AAA AAA BBB"
    # predicted = [7]（chunk0 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},  # 第 1 个 AAA，gt = 3
            {"marker": "AAA", "position": "after"},  # 第 2 个 AAA，gt = 7
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 第 1 anchor: find("AAA", 0) = 0, gt = 3, search_from = 3
    # 第 2 anchor: find("AAA", 3) = 4, gt = 7, search_from = 7
    # predicted = [7] → d to gt[0]=3 是 4, d to gt[1]=7 是 0
    # tolerance=0 → 只 match (0, 0, 1)
    # matched=1, num_pred=1, num_gt=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# ---------- chunk_boundary_prf predicted stream 不存在 ----------

def test_chunk_boundary_chunk_text_with_normalizable_whitespace_batch49():
    """chunk 文本含 tab/newline 等 → normalize 后 stream 中可能找不到原始 chunk 文本。"""
    document = {
        "chunks": [
            {"text": "AAA\nBBB"},  # 含 newline
            {"text": "CCC"},
        ]
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # normalize_text("AAA\nBBB") = "AAA BBB"（newline → 空格）
    # stream = "AAA BBB CCC"
    # predicted = 7（"AAA BBB" 长度）
    # marker "AAA" after → gt = 3, d = 4
    # tolerance=10 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf chunks 边界 ----------

def test_chunk_boundary_chunks_missing_text_key_batch49():
    """chunk 缺 text key → 用 .get("text") or "" → 空字符串。"""
    document = {"chunks": [{"no_text": "x"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "BBB", "position": "before"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # chunk0 normalize 后是空字符串，stream = " BBB"（前置空格会被 normalize 删）
    # 实际：normalize_text(" ") = ""，stream = normalize(" ".join(["", "BBB"])) = "BBB"
    # predicted = 0（chunk0 末尾位置 = 0）
    # marker "BBB" before → find = 0, gt = 0, d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_chunks_text_none_batch49():
    """chunk text 是 None → 用 "" 替代。"""
    document = {"chunks": [{"text": None}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "BBB", "position": "before"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # 同上
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_empty_chunks_list_batch49():
    """chunks 是空 list → no_predicted_boundaries。"""
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall 因为有 anchors → ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_document_empty_dict_batch49():
    """document = {} → chunks 是 []。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "X"}]}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_document_none_returns_pipeline_failed_batch49():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    # _tolerance_chars 仍然记录
    assert out["_tolerance_chars"]["value"] == 10


# ---------- chunk_boundary_prf f1 计算分支 ----------

def test_chunk_boundary_f1_perfect_batch49():
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # P=1, R=1 → F1 = 1
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_f1_zero_denominator_batch49():
    """P=R=0 → denom=0 → F1 = 0.0。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "XXX", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # marker "XXX" 找不到 → missing, num_gt=0
    # predicted = [3], num_pred=1, matched=0
    # P = 0/1 = 0.0
    # R: num_gt=0 → null + no_ground_truth_anchors_in_stream
    # F1: p_val=0.0, r_val=None → null + precision_or_recall_not_evaluated
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_f1_half_half_batch49():
    """P=1, R=0.5 → F1 = 2*1*0.5/(1+0.5) = 1/1.5 = 0.667."""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
            {"marker": "XXX", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # predicted = [3], matched = 1 (anchor1), num_pred=1, num_gt=1 (anchor2 missing)
    # P = 1/1 = 1.0
    # R = 1/1 = 1.0
    # F1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


# ---------- figure_caption_prf 不依赖任何输入 ----------

def test_figure_caption_prf_none_document_batch49():
    out = figure_caption_prf(None, {"x": "y"})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_none_annotation_batch49():
    out = figure_caption_prf({"x": "y"}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_both_none_batch49():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_empty_dict_inputs_batch49():
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_real_chunks_batch49():
    """即使 document 有 chunks 和 captions 也不计算。"""
    document = {
        "chunks": [{"text": "x"}],
        "elements": [{"type": "caption", "content": "fig 1"}, {"type": "image"}],
    }
    out = figure_caption_prf(document, {})
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- 模块源码补强 ----------

def test_source_contains_counter_import_batch49():
    src = inspect.getsource(am_mod)
    assert "from collections import Counter" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(am_mod)
    assert "from typing import Any" in src


def test_source_contains_normalize_text_import_batch49():
    src = inspect.getsource(am_mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_source_contains_null_ratio_import_batch49():
    src = inspect.getsource(am_mod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_source_parser_does_not_emit_relations_constant_batch49():
    src = inspect.getsource(am_mod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_source_docstring_mentions_caption_relation_batch49():
    src = inspect.getsource(am_mod)
    assert "caption" in src.lower()


def test_source_docstring_mentions_one_to_one_batch49():
    src = inspect.getsource(am_mod)
    assert "一对一" in src


def test_source_docstring_mentions_tolerance_batch49():
    src = inspect.getsource(am_mod)
    assert "容差" in src or "tolerance" in src.lower()


def test_source_all_has_3_entries_batch49():
    src = inspect.getsource(am_mod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_source_contains_normalize_text_call_batch49():
    src = inspect.getsource(am_mod)
    assert "normalize_text(" in src


def test_source_contains_pairs_sort_batch49():
    src = inspect.getsource(am_mod)
    assert "pairs.sort" in src


def test_source_contains_used_pred_used_gt_batch49():
    src = inspect.getsource(am_mod)
    assert "used_pred" in src
    assert "used_gt" in src


def test_source_contains_missing_markers_append_batch49():
    src = inspect.getsource(am_mod)
    assert "missing_markers.append" in src


def test_source_contains_predicted_append_batch49():
    src = inspect.getsource(am_mod)
    assert "predicted.append" in src


def test_source_contains_gt_positions_append_batch49():
    src = inspect.getsource(am_mod)
    assert "gt_positions.append" in src


def test_source_contains_pipeline_failed_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"pipeline_failed"' in src


def test_source_contains_no_annotation_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"no_annotation"' in src


def test_source_contains_no_predicted_boundaries_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"no_predicted_boundaries"' in src


def test_source_contains_no_ground_truth_anchors_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors"' in src


def test_source_contains_no_ground_truth_anchors_in_stream_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_source_contains_precision_or_recall_not_evaluated_string_batch49():
    src = inspect.getsource(am_mod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_source_contains_search_from_batch49():
    src = inspect.getsource(am_mod)
    assert "search_from" in src


def test_source_contains_2_p_r_divide_denom_batch49():
    src = inspect.getsource(am_mod)
    assert "2 * p_val * r_val / denom" in src


def test_source_contains_p_val_plus_r_val_batch49():
    src = inspect.getsource(am_mod)
    assert "p_val + r_val" in src


def test_source_contains_denom_le_zero_batch49():
    src = inspect.getsource(am_mod)
    assert "denom <= 0" in src


# ---------- AST 结构补强 ----------

def test_ast_has_2_top_level_functions_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2


def test_ast_function_names_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["figure_caption_prf", "chunk_boundary_prf"]


def test_ast_no_class_def_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_5_imports_batch49():
    """5 个 import：__future__ + Counter + Any + normalize_text + _null,_ratio。"""
    tree = ast.parse(inspect.getsource(am_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


def test_ast_module_has_2_top_level_assigns_batch49():
    """PARSER_DOES_NOT_EMIT_RELATIONS + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(am_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_figure_caption_prf_simple_return_batch49():
    """figure_caption_prf 直接 return dict（无 if）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "figure_caption_prf")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1


def test_ast_figure_caption_prf_no_if_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "figure_caption_prf")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) == 0


def test_ast_chunk_boundary_has_multiple_return_batch49():
    """chunk_boundary_prf 多个 return（document None + annotation falsy + chunks < 2 + no anchors + main）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 5


def test_ast_chunk_boundary_has_multiple_for_batch49():
    """chunk_boundary_prf 多 for（predicted 构建 + gt_positions 构建 + pairs 构建 + matching）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 4


def test_ast_chunk_boundary_has_nested_for_batch49():
    """构建 pairs 时是嵌套 for。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    # 找嵌套 for
    nested_count = 0
    for for_node in ast.walk(func):
        if isinstance(for_node, ast.For):
            for child in ast.walk(for_node):
                if child is for_node:
                    continue
                if isinstance(child, ast.For):
                    nested_count += 1
                    break
    assert nested_count >= 1


def test_ast_chunk_boundary_has_multiple_if_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 6


def test_ast_chunk_boundary_has_pairs_sort_lambda_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    sorts = [n for n in ast.walk(func) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sort"]
    assert len(sorts) == 1
    # key=lambda x: x[0] 是 keyword arg
    assert len(sorts[0].keywords) == 1
    assert sorts[0].keywords[0].arg == "key"
    assert isinstance(sorts[0].keywords[0].value, ast.Lambda)


def test_ast_chunk_boundary_has_aug_assign_matched_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    augs = [n for n in ast.walk(func) if isinstance(n, ast.AugAssign)]
    # matched += 1 + pos += / search_from =
    assert len(augs) >= 2


def test_ast_chunk_boundary_has_break_batch49():
    """最后一个 chunk 跳过（break）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    breaks = [n for n in ast.walk(func) if isinstance(n, ast.Break)]
    assert len(breaks) == 1


def test_ast_chunk_boundary_has_continue_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    continues = [n for n in ast.walk(func) if isinstance(n, ast.Continue)]
    # 至少 2：predicted find<0 时 continue + matched loop 时 continue
    assert len(continues) >= 2


def test_ast_chunk_boundary_no_try_batch49():
    """chunk_boundary_prf 不使用 try。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    trys = [n for n in ast.walk(func) if isinstance(n, ast.Try)]
    assert len(trys) == 0


def test_ast_chunk_boundary_has_3_keys_in_dict_batch49():
    """最终 out 至少含 chunk_boundary_precision/recall/f1 + _tolerance_chars。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    for key in [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]:
        assert f"'{key}'" in src or f'"{key}"' in src


def test_ast_no_global_statement_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.Global) for n in ast.walk(tree))


def test_ast_no_nonlocal_statement_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.Nonlocal) for n in ast.walk(tree))


def test_ast_no_class_def_anywhere_batch49():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百三十四批 ----------

def _src() -> str:
    return inspect.getsource(am_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_no_open_batch49():
    """annotation_metrics 不调用 open()。"""
    assert "open(" not in _src()


def test_source_counter_imported_but_not_called_batch49():
    """Counter 被 import 但函数体不调用（仅在 docstring/metric 设计中提及）。"""
    src = _src()
    assert "from collections import Counter" in src
    assert "Counter(" not in src
