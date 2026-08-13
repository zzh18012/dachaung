"""evaluation/annotation_metrics.py 第六十六轮 edges 测试（Round 608）。

补强 edges67 未触及的角度（第四十四批）。

新角度：
- PARSER_DOES_NOT_EMIT_RELATIONS 边界（isidentifier / islower / isprintable）
- figure_caption_prf 多次调用返回新对象（不缓存）
- figure_caption_prf document 与 annotation 各种组合都返回固定 null
- figure_caption_prf 即使 document 含 figure 关系也返回 null（实现不读 document）
- chunk_boundary_prf tolerance_chars 边界（0 / 1 / 负值 / 大值）
- chunk_boundary_prf 单 chunk（无内部边界）
- chunk_boundary_prf 多 chunk + 空 anchors → no_ground_truth_anchors
- chunk_boundary_prf marker 在 stream 中重复出现（顺序定位）
- chunk_boundary_prf position="before" anchor
- chunk_boundary_prf position="after" anchor
- chunk_boundary_prf position 缺省（默认 after）
- chunk_boundary_prf marker 缺省（空字符串 → 找不到 → missing_markers）
- chunk_boundary_prf 完全匹配 precision=recall=f1=1.0
- chunk_boundary_prf 全部不匹配 precision=recall=0.0, f1=0.0
- chunk_boundary_prf 部分匹配
- chunk_boundary_prf _tolerance_chars 字段总是存在
- chunk_boundary_prf _missing_markers 仅在 missing 时出现
- module source 字符串精确
- AST 结构
- module 合理性
- forbidden tokens 第七十九批
"""

from __future__ import annotations

import ast
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第四十四批


def test_parser_does_not_emit_relations_isidentifier_batch44():
    """是合法 Python identifier。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS.isidentifier()


def test_parser_does_not_emit_relations_islower_batch44():
    """全小写 + 下划线。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS.islower()


def test_parser_does_not_emit_relations_isprintable_batch44():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.isprintable()


def test_parser_does_not_emit_relations_isascii_batch44():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.isascii()


def test_parser_does_not_emit_relations_no_uppercase_batch44():
    for c in PARSER_DOES_NOT_EMIT_RELATIONS:
        assert not c.isupper()


def test_parser_does_not_emit_relations_starts_with_letter_batch44():
    assert PARSER_DOES_NOT_EMIT_RELATIONS[0].isalpha()


def test_parser_does_not_emit_relations_ends_with_letter_batch44():
    assert PARSER_DOES_NOT_EMIT_RELATIONS[-1].isalpha()


def test_parser_does_not_emit_relations_underscore_count_batch44():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.count("_") == 4


# ---------- figure_caption_prf 第四十四批


def test_figure_caption_prf_callable_batch44():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_signature_batch44():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_return_annotation_dict_batch44():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_figure_caption_prf_document_none_annotation_none_batch44():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    }


def test_figure_caption_prf_document_some_annotation_none_batch44():
    out = figure_caption_prf({"elements": [{"type": "figure"}]}, None)
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_document_none_annotation_some_batch44():
    out = figure_caption_prf(None, {"figure_captions": []})
    assert out["figure_caption_f1"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_both_some_batch44():
    """即使 document 含 figure 关系也返回 null（实现不读 document）。"""
    doc = {"elements": [{"type": "figure", "caption_ref": "cap1"}]}
    ann = {"figure_captions": [{"figure_id": "f1", "caption_id": "cap1"}]}
    out = figure_caption_prf(doc, ann)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_all_values_none_batch44():
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_recall"]["value"] is None
    assert out["figure_caption_f1"]["value"] is None


def test_figure_caption_prf_returns_new_dict_each_call_batch44():
    """不缓存：两次调用返回不同 dict 对象。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 is not out2
    assert out1 == out2


def test_figure_caption_prf_inner_dicts_new_each_call_batch44():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1["figure_caption_precision"] is not out2["figure_caption_precision"]


def test_figure_caption_prf_keys_count_batch44():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_prf_inner_dict_keys_batch44():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}


# ---------- chunk_boundary_prf 签名 第四十四批


def test_chunk_boundary_prf_callable_batch44():
    assert callable(chunk_boundary_prf)


def test_chunk_boundary_prf_signature_batch44():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_chars_default_30_batch44():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_document_no_default_batch44():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_annotation_no_default_batch44():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_return_annotation_dict_batch44():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- chunk_boundary_prf 边界条件 第四十四批


def test_chunk_boundary_prf_document_none_batch44():
    out = chunk_boundary_prf(None, {})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_with_annotation_batch44():
    """document=None 即使有 annotation 也走 pipeline_failed 分支。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_some_annotation_empty_batch44():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_some_annotation_none_batch44():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch44():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_no_anchors_key_batch44():
    """annotation 是 dict 但无 chunk_boundary_anchors → 视作空 anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"other_key": []}
    out = chunk_boundary_prf(doc, ann)
    # chunks >= 2 + no anchors → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchors_empty_list_batch44():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_single_chunk_no_anchors_batch44():
    """1 个 chunk + 无 anchors → no_predicted_boundaries + recall 也 null。"""
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_with_anchors_batch44():
    """1 个 chunk + 有 anchors → recall=0.0（不是 null）。"""
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_empty_chunks_batch44():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_chunks_key_batch44():
    doc = {}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# ---------- chunk_boundary_prf _tolerance_chars 总存在 第四十四批


def test_chunk_boundary_prf_tolerance_chars_recorded_batch44():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_zero_batch44():
    out = chunk_boundary_prf(None, None, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_chars_negative_batch44():
    """负 tolerance 也允许传入（被记录）。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=-1)
    assert out["_tolerance_chars"]["value"] == -1


def test_chunk_boundary_prf_tolerance_chars_large_batch44():
    out = chunk_boundary_prf(None, None, tolerance_chars=10000)
    assert out["_tolerance_chars"]["value"] == 10000


def test_chunk_boundary_prf_tolerance_chars_always_present_batch44():
    """所有分支都应记录 _tolerance_chars。"""
    # document None
    out1 = chunk_boundary_prf(None, None, tolerance_chars=10)
    assert "_tolerance_chars" in out1
    # empty annotation
    out2 = chunk_boundary_prf({"chunks": []}, None, tolerance_chars=10)
    assert "_tolerance_chars" in out2
    # single chunk
    out3 = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {"chunk_boundary_anchors": []}, tolerance_chars=10)
    assert "_tolerance_chars" in out3


# ---------- chunk_boundary_prf 正常匹配 第四十四批


def test_chunk_boundary_prf_perfect_match_batch44():
    """预测边界与 anchor 完全一致 → precision=recall=f1=1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"；预测边界在 5（hello 末尾）
    # anchor "hello" position="after" → 5
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch44():
    """position="before" → marker 起始位置。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"；预测边界在 5
    # anchor "world" position="before" → 6（w 起始）→ 距离 |5-6|=1 ≤ tolerance=1
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_default_after_batch44():
    """缺省 position 默认 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_batch44():
    """预测边界距离 anchor 太远 → 不匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 预测边界在 5
    # anchor "beta" position="before" → 6 → |5-6|=1
    # 用 tolerance=0 → 1 > 0 → 不匹配
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_partial_match_batch44():
    """2 个预测边界，1 个匹配 anchor。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # stream = "a b c"；预测边界在 1 (a 后) 和 3 (b 后)
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # anchor 位置 = 1；预测 [1, 3]；tolerance=0 → 只匹配第 1 个
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 1/1


def test_chunk_boundary_prf_one_to_one_matching_batch44():
    """一对一：一个预测只能匹配一个 anchor。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # 预测边界 [1, 3]
    # 两个 anchor 都在位置 1 → 用 tolerance=1 让两个 anchor 都"接近"预测 1
    # 但一对一匹配：预测 1 只匹配距离最近的 anchor；预测 3 匹配另一个
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # 位置 1
            {"marker": "b", "position": "after"},  # 位置 3
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_not_found_batch44():
    """marker 在 stream 中找不到 → missing_markers。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_markers_empty_when_no_missing_batch44():
    """无 missing 时不写 _missing_markers。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_empty_marker_batch44():
    """marker 为空字符串 → find 返回 -1（标记 missing）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out


def test_chunk_boundary_prf_repeated_marker_batch44():
    """同一 marker 多次出现 → 顺序定位。"""
    doc = {"chunks": [{"text": "a a"}, {"text": "a a"}]}
    # stream = "a a a a"
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # 第一次出现：位置 1
            {"marker": "a", "position": "after"},  # 第二次出现：位置 3
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不抛异常即通过；可能匹配率不完美但应稳定
    assert "chunk_boundary_precision" in out


# ---------- chunk_boundary_prf 5 元组结构 第四十四批


def test_chunk_boundary_prf_keys_minimum_batch44():
    """最少 4 个 keys：precision/recall/f1/_tolerance_chars。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1", "_tolerance_chars"):
        assert k in out


def test_chunk_boundary_prf_keys_maximum_with_missing_markers_batch44():
    """最多 5 个 keys（含 _missing_markers）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert len(out) == 5


def test_chunk_boundary_prf_tolerance_value_int_batch44():
    out = chunk_boundary_prf(None, None, tolerance_chars=10)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_prf_tolerance_reason_none_batch44():
    out = chunk_boundary_prf(None, None, tolerance_chars=10)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_missing_markers_reason_none_batch44():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["_missing_markers"]["reason"] is None


# ---------- module source 字符串精确 第四十四批


def test_module_source_contains_docstring_batch44():
    src = inspect.getsource(amod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch44():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_collections_counter_import_batch44():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch44():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_normalize_text_import_batch44():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch44():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_parser_does_not_emit_relations_const_batch44():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_prf_function_batch44():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_prf_function_batch44():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_pipeline_failed_keyword_batch44():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_keyword_batch44():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_keyword_batch44():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_keyword_batch44():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_tolerance_chars_keyword_batch44():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_normalize_text_call_batch44():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_contains_one_to_one_note_batch44():
    """docstring 提到一对一匹配。"""
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_contains_marker_keyword_batch44():
    src = inspect.getsource(amod)
    assert "marker" in src


def test_module_source_contains_position_keyword_batch44():
    src = inspect.getsource(amod)
    assert "position" in src


def test_module_source_contains_chunk_boundary_anchors_keyword_batch44():
    src = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in src


def test_module_source_contains_missing_markers_keyword_batch44():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_contains_all_definition_batch44():
    src = inspect.getsource(amod)
    assert "__all__" in src


# ---------- AST 结构 第四十四批


def test_ast_top_level_no_class_no_loop_no_with_batch44():
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.ClassDef, ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_two_functions_batch44():
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "figure_caption_prf" in funcs
    assert "chunk_boundary_prf" in funcs


def test_ast_no_async_functions_batch44():
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_top_level_only_allowed_kinds_batch44():
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.FunctionDef, ast.Assign))


def test_ast_has_module_docstring_batch44():
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


def test_ast_parser_const_assign_batch44():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是顶层 Assign。"""
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    assigns = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PARSER_DOES_NOT_EMIT_RELATIONS" for t in n.targets)
    ]
    assert len(assigns) == 1


# ---------- module 合理性 第四十四批


def test_module_has_all_attribute_batch44():
    assert hasattr(amod, "__all__")


def test_module_all_is_list_batch44():
    assert isinstance(amod.__all__, list)


def test_module_all_three_entries_batch44():
    assert len(amod.__all__) == 3


def test_module_all_contains_const_batch44():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_all_contains_figure_caption_prf_batch44():
    assert "figure_caption_prf" in amod.__all__


def test_module_all_contains_chunk_boundary_prf_batch44():
    assert "chunk_boundary_prf" in amod.__all__


def test_module_all_contains_only_strings_batch44():
    for name in amod.__all__:
        assert isinstance(name, str)


def test_module_all_no_duplicates_batch44():
    assert len(amod.__all__) == len(set(amod.__all__))


def test_module_has_parser_does_not_emit_relations_attr_batch44():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_has_figure_caption_prf_attr_batch44():
    assert hasattr(amod, "figure_caption_prf")


def test_module_has_chunk_boundary_prf_attr_batch44():
    assert hasattr(amod, "chunk_boundary_prf")


def test_module_functions_callable_batch44():
    assert callable(amod.figure_caption_prf)
    assert callable(amod.chunk_boundary_prf)


# ---------- 端到端集成 第四十四批


def test_e2e_full_round_trip_chunk_boundary_batch44():
    """完整 chunk 端到端：完美匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 0


def test_e2e_round_trip_idempotent_batch44():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_e2e_figure_caption_idempotent_batch44():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_e2e_with_large_tolerance_batch44():
    """大 tolerance 让所有 anchor 都匹配。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "z", "position": "after"},  # 找不到
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1000)
    # z 找不到 → missing_markers
    assert "_missing_markers" in out


# ---------- module source forbidden tokens 第七十九批


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
def test_module_source_no_forbidden_tokens_batch44(token):
    src = inspect.getsource(amod)
    assert token not in src
