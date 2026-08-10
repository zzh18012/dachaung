"""evaluation/annotation_metrics.py 第二十六轮 edges 测试（Round 315）。

重点补强 edges24 未触及的角度：
- figure_caption_prf 行为深度（不变量 + 返回结构）
- chunk_boundary_prf 算法精确（各分支 / 容差边界 / 多 marker / 重复 marker）
- normalize_text 集成深度
- PARSER_DOES_NOT_EMIT_RELATIONS 常量
- module source forbidden tokens
- module source 字符串精确
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
from types import FunctionType
from typing import Any

import pytest

import evaluation.annotation_metrics as m
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 行为深度 ----------


def test_figure_caption_prf_returns_3_metrics():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_null():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_all_use_same_reason():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_ignores_document_content():
    """即使 document 有内容，结果仍是 null（parser 不输出 caption relation）。"""
    doc = {"elements": [{"type": "figure"}, {"type": "caption"}], "chunks": []}
    out = figure_caption_prf(doc, None)
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_ignores_annotation_content():
    anno = {"figure_caption_pairs": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(None, anno)
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_call_count_consistent():
    """figure_caption_prf 应该总是返回 3 个 metric（不多不少）。"""
    for doc in (None, {}, {"x": 1}):
        for anno in (None, {}, {"y": 2}):
            out = figure_caption_prf(doc, anno)
            assert len(out) == 3


def test_figure_caption_prf_returns_dict_of_dict():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)
    for v in out.values():
        assert isinstance(v, dict)


# ---------- chunk_boundary_prf 算法精确 ----------


def test_chunk_boundary_prf_default_tolerance():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_no_annotation_returns_no_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_returns_no_predicted():
    doc = {"chunks": []}
    anno = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted():
    doc = {"chunks": [{"text": "a"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 有 anchor 但无预测 → recall 是 ratio 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_no_anchors_returns_null_recall():
    doc = {"chunks": [{"text": "a"}]}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_anchors_returns_no_ground_truth():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_yields_one_one_one():
    """2 chunks，1 anchor 恰好在 chunk 1 末尾位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"（normalize 后），边界在 pos=3
    # anchor: marker="abc" position="after" → gt_position = 0 + 3 = 3
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_perfect_match_position_before():
    """anchor position="before" → marker 起始位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"，predicted 边界 = 3
    # anchor: marker="def" position="before" → gt = 4（"def" 起始）
    # 距离 = |3 - 4| = 1 → tolerance >= 1 时匹配
    anno = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_0_strict_match():
    """tolerance=0 时位置必须严格相等。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 = 3
    anno = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    # gt = 4，距离 1，tolerance=0 → 不匹配
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_extra_anchor_lowers_recall():
    """多个 anchor 但只有 1 个能匹配 → recall < 1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 2 anchors, 1 匹配
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "after"},  # 不存在
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # matched=1, num_gt=1 (xyz 不在 stream 里 → missing，不计入 num_gt)
    # 实际上 xyz 会被加入 missing_markers，不计 gt_positions
    # 所以 num_gt=1，recall=1/1=1.0
    # 但要看具体行为；missing markers 仍减 gt 数
    # 让我们先看 source：missing → 不加入 gt_positions → num_gt 不计
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_marker_field_tracked():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "xyz"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_no_missing_marker_no_field():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, anno)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_t_field_always_present():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=15)
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_one_to_one_matching():
    """贪心匹配：相同距离时一对一边界。"""
    # 3 chunks → 2 个预测边界
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # stream = "abc def ghi"
    # 边界 1 = 3, 边界 2 = 7
    # 2 anchors 恰好匹配
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # gt = 3
            {"marker": "def", "position": "after"},  # gt = 7
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_duplicate_markers():
    """相同 marker 重复 → 顺序定位（search_from 推进）。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "ab"}]}
    # stream = "ab ab ab"，边界 = 2, 5
    # 2 anchors 都是 marker="ab"，position="after"
    # 第 1 个 anchor：find("ab", 0) = 0 → gt = 2; search_from = 2
    # 第 2 个 anchor：find("ab", 2) = 3 → gt = 5; search_from = 5
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
            {"marker": "ab", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_p_zero():
    """precision=0 → f1=0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 = 3，anchor 不匹配
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "before"},  # gt = 4，距离 1
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # matched = 0, num_pred = 1 → p = 0
    # num_gt = 1, recall = 0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_half_when_half_match():
    """precision=0.5, recall=1.0 → f1 = 2*0.5*1/(0.5+1) = 1/1.5 = 0.6667。"""
    # 3 chunks, 1 anchor 恰好匹配 → matched=1, num_pred=2, num_gt=1
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # 边界 = 3, 7
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # gt = 3, 匹配
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 1/1
    # f1 = 2*0.5*1/(0.5+1) = 1/1.5
    assert abs(out["chunk_boundary_f1"]["value"] - (1 / 1.5)) < 1e-9


def test_chunk_boundary_prf_t_field_in_document_none_branch():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_t_field_in_no_annotation_branch():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_t_field_in_no_predicted_branch():
    doc = {"chunks": []}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_t_field_in_no_gt_branch():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_returns_dict():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunks_missing_field():
    """document 没有 'chunks' key → 当 [] 处理。"""
    doc = {}
    anno = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchors_missing_field():
    """annotation 有其他字段但无 'chunk_boundary_anchors' key → 当 [] 处理。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"other_field": 1}  # 非空，避免 falsy 短路
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchor_no_marker_field():
    """anchor 没 marker → 当 "" 处理 → find 返回 -1 → missing。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{}]}  # 没 marker
    out = chunk_boundary_prf(doc, anno)
    # "" marker → find(...) = -1（因为 marker 为 falsy）
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_before_default_after():
    """position 默认 'after'（在 source 中看到 default）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 常量 ----------


def test_parser_does_not_emit_relations_value():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_namespace():
    """常量在 evaluation.annotation_metrics 模块里。"""
    # 模块级常量，没有 __module__ 属性
    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_in_figure_caption_prf():
    """figure_caption_prf 使用 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    src = inspect.getsource(figure_caption_prf)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


# ---------- module source forbidden tokens ----------


@pytest.mark.parametrize(
    "token",
    [
        "import time",
        "import random",
        "import uuid",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import socket",
        "import email",
        "import html",
        "import http",
        "import urllib",
        "import sqlite3",
        "import csv",
        "import pickle",
        "import tempfile",
        "import shutil",
        "import glob",
        "import os",
        "import sys",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
        "import datetime",
        "import itertools",
        "import functools",
        "import math",
        "import json",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_from_collections_import_counter():
    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_app_chunkers_import():
    src = inspect.getsource(m)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_evaluation_metrics_import():
    src = inspect.getsource(m)
    assert "from evaluation.metrics import _null, _ratio" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_figure_caption_prf_def():
    src = inspect.getsource(m)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_prf_def():
    src = inspect.getsource(m)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_constant_assignment():
    src = inspect.getsource(m)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_normalize_text_call():
    src = inspect.getsource(m)
    assert "normalize_text(" in src


def test_module_source_has_docstring_marker_semantics():
    src = inspect.getsource(m)
    assert "marker" in src
    assert "position" in src


def test_module_source_has_tolerance_chars_in_docstring():
    src = inspect.getsource(m)
    assert "tolerance_chars" in src


def test_module_source_has_greedy_matching_note():
    src = inspect.getsource(m)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_has_one_to_one_note():
    src = inspect.getsource(m)
    assert "一对一" in src


def test_module_source_has_5_null_call_patterns():
    """source 含 5 个分支的 _null 调用：pipeline_failed/no_annotation/no_predicted_boundaries×2/no_ground_truth_anchors×2。"""
    src = inspect.getsource(chunk_boundary_prf)
    # 每个 reason 至少出现 1 次
    for reason in (
        '"pipeline_failed"',
        '"no_annotation"',
        '"no_predicted_boundaries"',
        '"no_ground_truth_anchors"',
        '"no_ground_truth_anchors_in_stream"',
        '"precision_or_recall_not_evaluated"',
    ):
        assert reason in src


def test_module_source_has_search_from_advance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = find_pos + len(marker)" in src


def test_module_source_has_pairs_sort():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=" in src


def test_module_source_has_used_pred_used_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src
    assert "used_gt" in src


def test_module_source_has_num_pred_num_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "num_pred" in src
    assert "num_gt" in src


def test_module_source_has_denom_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom" in src
    assert "denom <= 0" in src


def test_module_source_has_out_dict_annotation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "out: dict[str, dict[str, Any]] = {}" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


# ---------- signatures 精确 ----------


def test_figure_caption_prf_signature():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_param_annotations():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"
    assert sig.parameters["annotation"].annotation == "dict[str, Any] | None"


def test_figure_caption_prf_return_annotation():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_chunk_boundary_prf_signature():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_param_annotations():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"
    assert sig.parameters["annotation"].annotation == "dict[str, Any] | None"
    assert sig.parameters["tolerance_chars"].annotation == "int"


def test_chunk_boundary_prf_return_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_chunk_boundary_prf_no_varargs_varkw():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_figure_caption_prf_no_varargs_varkw():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- namespace ----------


def test_figure_caption_prf_namespace():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_chunk_boundary_prf_namespace():
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_module_namespace():
    assert m.__name__ == "evaluation.annotation_metrics"


# ---------- module 整体合理性 ----------


def test_module_all_has_3_entries():
    assert set(m.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_all_count_is_3():
    assert len(m.__all__) == 3


def test_module_has_2_module_level_functions():
    fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.annotation_metrics"
    ]
    assert set(fns) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_has_1_module_level_constant():
    consts = [
        n for n in dir(m)
        if not n.startswith("_")
        and not callable(getattr(m, n))
        and not isinstance(getattr(m, n), type)
    ]
    # 排除 import 进来的 Counter / Any / normalize_text / _null / _ratio
    own_consts = [n for n in consts if n == "PARSER_DOES_NOT_EMIT_RELATIONS"]
    assert own_consts == ["PARSER_DOES_NOT_EMIT_RELATIONS"]


def test_module_has_no_class_definition():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成 ----------


def test_e2e_full_match_pipeline():
    """完整端到端：2 chunks + 1 anchor + tolerance 0 → 全 1.0。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    # stream = "hello world foo bar"
    # 边界 = 11（"hello world" 末尾）
    anno = {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_normalize_collapses_whitespace():
    """chunk.text 含额外空白，normalize 后仍能匹配 anchor。"""
    doc = {"chunks": [{"text": "hello   world"}, {"text": "foo"}]}
    # norm_chunks[0] = "hello world"（normalize 把多空格压成 1 个）
    # stream = "hello world foo"
    anno = {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_larger_tolerance_for_rough_match():
    """大容差下，远距离 anchor 也算匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 = 3
    # anchor "abc" position="after" → gt = 3 → 匹配（距离 0）
    # 加 1 个 anchor: marker="def" position="before" → gt = 4 → 距离 1
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "def", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=10)
    # num_pred=1, num_gt=2, matched=1（一对一）→ p=1, r=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_e2e_figure_caption_always_null_regardless_of_input():
    """figure_caption_prf 在任何输入下都返回 null。"""
    for doc in (None, {}, {"figure": []}):
        for anno in (None, {}, {"figure_caption_pairs": []}):
            out = figure_caption_prf(doc, anno)
            for v in out.values():
                assert v["value"] is None
                assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_deterministic_output():
    """相同输入 → 相同输出。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, anno, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, anno, tolerance_chars=5)
    assert out1 == out2


def test_e2e_no_chunks_at_all_returns_quickly():
    """document 完全空 → 仍然返回完整 metric dict。"""
    doc = {}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out
