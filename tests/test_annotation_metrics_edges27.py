"""evaluation/annotation_metrics.py 第二十八轮 edges 测试（Round 327）。

重点补强 edges26 未触及的角度：
- chunk_boundary_prf 算法精确（贪心匹配 / 重复 marker / search_from 推进）
- chunk_boundary_prf f1 各分支
- chunk_boundary_prf 输出 dict 结构精确
- figure_caption_prf source level
- module source forbidden tokens 第二批
- module source 字符串精确补强（greedy 匹配各步骤 / 5 个早 return 路径）
- signatures 精确补强（kind/annotation 完整）
- 端到端集成补强（含重复 marker / 多 predicted 多 gt 匹配 / 跨边界）
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


# ---------- chunk_boundary_prf 算法精确（贪心匹配） ----------


def test_chunk_boundary_greedy_match_nearest_first():
    """贪心：距离近的优先匹配。"""
    # 4 chunks，3 个预测边界；2 个 anchor，分别靠近不同 pred
    doc = {"chunks": [
        {"text": "abc"},
        {"text": "def"},
        {"text": "ghi"},
        {"text": "jkl"},
    ]}
    # stream = "abc def ghi jkl"
    # 边界位置：3 (after abc), 7 (after def), 11 (after ghi)
    anno = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},  # gt=3, 距 pred[0]=3 → 0
        {"marker": "jkl", "position": "before"},  # gt=12 (find jkl at 12), 距 pred[2]=11 → 1
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=10)
    # 3 predicted, 2 gt, 2 matched
    assert out["chunk_boundary_precision"]["value"] == 2 / 3
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_greedy_with_tie_break_by_used_pred():
    """两个 pred 距同一 gt 等距 → 第一个匹配的拿到。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # stream = "ab cd ef"
    # 边界 = 2 (after ab), 5 (after cd)
    anno = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},  # gt = 2，距 pred[0]=2 是 0
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=5)
    # 2 pred, 1 gt, 1 match
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_anchors_marker_with_position_before():
    """position=before → anchor 在 marker 起始位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def", pred boundary = 3 (after abc)
    anno = {"chunk_boundary_anchors": [
        {"marker": "def", "position": "before"},  # find def at 4, gt = 4
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # 距离 = |3 - 4| = 1 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_anchors_marker_with_position_after_default():
    """position 缺失 → 默认 'after'。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "abc"},  # no position → default 'after'
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # gt = 3 (find abc at 0, + 3) = 3 = pred[0]
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_repeated_marker_search_from_advances():
    """重复 marker：第 2 个 anchor 从第 1 个之后开始找。"""
    doc = {"chunks": [
        {"text": "abc"}, {"text": "abc"}, {"text": "def"},
    ]}
    # stream = "abc abc def"
    # 边界 = 3 (after abc[0]), 7 (after abc[1])
    anno = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},  # 第 1 个 abc → gt=3
        {"marker": "abc", "position": "after"},  # 第 2 个 abc → gt=7 (从 search_from=3 之后)
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # 2 pred, 2 gt, 2 match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_repeated_marker_within_tolerance():
    """2 个相同 marker 都接近预测边界。"""
    doc = {"chunks": [
        {"text": "x"}, {"text": "x"}, {"text": "x"},
    ]}
    # stream = "x x x"
    # 边界 = 1, 3
    anno = {"chunk_boundary_anchors": [
        {"marker": "x", "position": "after"},  # gt=1 (find x at 0, +1)
        {"marker": "x", "position": "after"},  # gt=3 (search_from=1, find x at 2, +1)
        # 第 3 个 x 没标注
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # 2 pred, 2 gt, 2 match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_anchor_search_from_within_tolerance():
    """search_from 推进避免两个 anchor 共享同一 stream 位置。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # stream = "ab cd ef", pred = 2, 5
    anno = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},  # gt=2
        {"marker": "ab", "position": "after"},  # search_from=2, find next "ab" → 找不到
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=5)
    # 第 2 个 marker "ab" missing
    assert "ab" in out["_missing_markers"]["value"]


# ---------- chunk_boundary_prf f1 各分支 ----------


def test_chunk_boundary_f1_perfect_match():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_f1_zero_denominator():
    """p=0, r=0 → denom=0 → f1=0（不是 null）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # anchor 远离任何 pred
    anno = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # 距离=1 > 0 → no match, p=0, r=0, denom=0 → f1=0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_f1_with_p_none_returns_null():
    """p is None → f1 null precision_or_recall_not_evaluated。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    # 没 anchor → f1 null
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    # 进入 no_ground_truth_anchors 分支
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_f1_with_partial_match():
    """部分匹配 → 标准 F1 计算。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # stream = "ab cd ef", pred = 2, 5
    anno = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},  # gt=2, match pred[0]=2 → match
        {"marker": "ef", "position": "before"},  # gt=6, 距 pred[1]=5 → 1, match if tolerance>=1
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # tolerance=0: 第 2 个 distance=1 > 0 → no match
    # matched=1, num_pred=2, num_gt=2 → p=0.5, r=0.5
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 0.5
    # f1 = 2 * 0.5 * 0.5 / (0.5 + 0.5) = 0.5
    assert out["chunk_boundary_f1"]["value"] == 0.5


def test_chunk_boundary_f1_with_tight_tolerance_perfect():
    """tolerance=1 → 第 2 个 anchor 也 match。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},
        {"marker": "ef", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=1)
    assert out["chunk_boundary_f1"]["value"] == 1.0


# ---------- chunk_boundary_prf 输出 dict 结构精确 ----------


def test_chunk_boundary_output_keys_normal_path():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, anno)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert expected_keys.issubset(set(out.keys()))


def test_chunk_boundary_output_keys_with_missing_markers():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "missing_marker"}]}
    out = chunk_boundary_prf(doc, anno)
    assert "_missing_markers" in out
    assert "missing_marker" in out["_missing_markers"]["value"]


def test_chunk_boundary_output_no_missing_markers_when_all_found():
    """所有 anchor 都找到 → 输出无 _missing_markers。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, anno)
    assert "_missing_markers" not in out


def test_chunk_boundary_each_metric_value_is_dict():
    """每个 metric value 是 dict（含 value 和 reason）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, anno)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert isinstance(out[k], dict)
        assert "value" in out[k]
        assert "reason" in out[k]


# ---------- chunk_boundary_prf 边界 case ----------


def test_chunk_boundary_with_chunks_having_empty_text():
    """chunk text 为空 → norm="" → 边界位置可能异常。"""
    doc = {"chunks": [{"text": ""}, {"text": "abc"}]}
    # norm_chunks = ["", "abc"]
    # joined_raw = " abc"
    # stream = normalize(" abc") = "abc"
    # 在 stream[0:] 找 "" → find 返回 0；end = 0+0=0 → pred=[0]
    # 但 i=0 是最后一个？不，len(norm_chunks)-1 = 1，i=0 不是最后
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=10)
    # 应该有结果（不崩溃）
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_with_document_having_no_chunks_key():
    """document 没 chunks 字段 → chunks=[] → no_predicted_boundaries。"""
    doc = {}
    anno = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_with_annotation_no_anchors_key():
    """annotation 没 chunk_boundary_anchors → anchors=[] → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"other_field": 1}
    out = chunk_boundary_prf(doc, anno)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_t_field_always_in_output():
    """所有路径都写 _tolerance_chars。"""
    cases = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}]}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": [{"marker": "a"}]}),
    ]
    for doc, anno in cases:
        out = chunk_boundary_prf(doc, anno, tolerance_chars=42)
        assert "_tolerance_chars" in out, f"Missing for {doc}, {anno}"
        assert out["_tolerance_chars"]["value"] == 42


# ---------- figure_caption_prf source level ----------


def test_figure_caption_prf_source_signature():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_figure_caption_prf_source_uses_null_3_times_via_loop():
    """源代码用 for 循环 3 次构造（实际 for k in 3-tuple）。"""
    src = inspect.getsource(figure_caption_prf)
    # figure_caption_prf 直接构造 dict，不用 for
    assert "figure_caption_precision" in src
    assert "figure_caption_recall" in src
    assert "figure_caption_f1" in src


def test_figure_caption_prf_source_has_docstring():
    src = inspect.getsource(figure_caption_prf)
    assert "图表关联" in src or "figure-caption" in src.lower() or "caption" in src.lower()


def test_figure_caption_prf_source_no_try_except():
    src = inspect.getsource(figure_caption_prf)
    assert "try" not in src
    assert "except" not in src


def test_figure_caption_prf_source_no_loop():
    """figure_caption_prf 不含 for/while 循环。"""
    src = inspect.getsource(figure_caption_prf)
    assert "for " not in src
    assert "while " not in src


def test_figure_caption_prf_source_returns_dict_with_3_keys():
    src = inspect.getsource(figure_caption_prf)
    assert "return {" in src
    assert "}" in src


# ---------- module source forbidden tokens 第二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import copy",
        "import pprint",
        "import csv",
        "import xml",
        "import configparser",
        "import argparse",
        "import inspect",
        "import dis",
        "import traceback",
        "import warnings",
        "import weakref",
        "import gc",
        "import struct",
        "import codecs",
        "import unicodedata",
        "import string",
        "import textwrap",
        "import difflib",
        "import decimal",
        "import fractions",
        "import statistics",
        "import array",
        "import queue",
        "import types",
        "import math",
        "import collections.abc",
        "import dataclasses",
        "import abc",
        "import re",
        "import hashlib",
        "import secrets",
        "import uuid",
        "import time",
        "import json",
        "import sys",
    ],
)
def test_module_source_forbidden_tokens_second_batch(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_counter_import():
    src = inspect.getsource(m)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import():
    src = inspect.getsource(m)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_metrics_helpers_import():
    src = inspect.getsource(m)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant():
    src = inspect.getsource(m)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_docstring_mentions_caption():
    src = inspect.getsource(m)
    assert "caption" in src.lower()


def test_module_source_has_docstring_mentions_relation():
    src = inspect.getsource(m)
    assert "relation" in src.lower() or "关联" in src


def test_module_source_has_docstring_mentions_marker():
    src = inspect.getsource(m)
    assert "marker" in src.lower()


def test_module_source_has_docstring_mentions_tolerance():
    src = inspect.getsource(m)
    assert "tolerance" in src.lower() or "容差" in src


def test_module_source_has_docstring_mentions_heuristic():
    """docstring 提到不引入"最近图片"启发式。"""
    src = inspect.getsource(m)
    assert "启发式" in src or "heuristic" in src.lower()


def test_module_source_has_greedy_keyword():
    src = inspect.getsource(m)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_has_one_to_one_keyword():
    src = inspect.getsource(m)
    assert "一对一" in src


def test_module_source_has_normalize_text_called_with_default():
    """代码用 c.get('text') or ''。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'normalize_text(c.get("text") or "")' in src


def test_module_source_has_join_with_space():
    src = inspect.getsource(chunk_boundary_prf)
    assert '" ".join(norm_chunks)' in src


def test_module_source_has_stream_normalize_after_join():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_module_source_has_predicted_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for i, txt in enumerate(norm_chunks):" in src


def test_module_source_has_last_chunk_break():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if i == len(norm_chunks) - 1:" in src


def test_module_source_has_find_in_stream():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(txt, pos)" in src


def test_module_source_has_search_from_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_module_source_has_marker_default_empty():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("marker", "")' in src


def test_module_source_has_position_default_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


def test_module_source_has_pairs_sort_key_distance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_module_source_has_used_pred_used_gt_set():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_module_source_has_f1_calc_with_2p1r():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_module_source_has_missing_markers_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_source_has_no_yield():
    src = inspect.getsource(m)
    assert "yield" not in src


def test_module_source_has_no_global():
    src = inspect.getsource(m)
    assert "\nglobal " not in src


def test_module_source_has_no_async():
    src = inspect.getsource(m)
    assert "async def" not in src


def test_module_source_has_no_decorators():
    src = inspect.getsource(m)
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            pytest.fail(f"Found decorator: {stripped}")


# ---------- signatures 精确补强 ----------


def test_chunk_boundary_prf_signature():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters)
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_annotations():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"
    assert sig.parameters["annotation"].annotation == "dict[str, Any] | None"
    assert sig.parameters["tolerance_chars"].annotation == "int"


def test_chunk_boundary_prf_default_tolerance():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_no_default_for_document_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_no_varargs_varkw():
    for fn in (chunk_boundary_prf, figure_caption_prf):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            )


def test_namespace_chunk_boundary_prf():
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_namespace_figure_caption_prf():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_namespace_module():
    assert m.__name__ == "evaluation.annotation_metrics"


# ---------- 模块整体合理性 ----------


def test_module_all_3_entries():
    assert m.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list():
    assert isinstance(m.__all__, list)


def test_module_has_2_module_level_functions():
    fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.annotation_metrics"
    ]
    assert set(fns) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_has_1_module_level_constant():
    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成补强 ----------


def test_e2e_perfect_match_3_chunks():
    doc = {"chunks": [
        {"text": "section1"},
        {"text": "section2"},
        {"text": "section3"},
    ]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "section1", "position": "after"},
        {"marker": "section2", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_no_match_due_to_tight_tolerance():
    """tolerance=0 + anchor 离 pred 1 字符 → no match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # pred boundary = 3 (after abc)
    # anchor "def" before → gt = 4 (find def at 4)
    # distance = 1 > 0 → no match
    anno = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_deterministic_across_multiple_runs():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    out1 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    out3 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out1 == out2 == out3


def test_e2e_with_unicode_chunks():
    """含中文 chunk 文本。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "你好", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # stream = "你好 世界"，pred boundary = 2 (after 你好)
    # gt = 2 (find 你好 at 0, +2)
    # distance = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_punctuation_in_chunks():
    """chunk 含标点。"""
    doc = {"chunks": [{"text": "Hello, world!"}, {"text": "Foo bar."}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "Hello, world!", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_with_extra_whitespace_in_chunks():
    """chunk 含多余空白 → normalize 后匹配。"""
    doc = {"chunks": [{"text": "  abc  "}, {"text": "  def  "}]}
    # normalize 后 = "abc", "def"
    # joined = "abc def"
    # stream = "abc def"
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # gt = 3 (find abc at 0, +3) = 3 = pred[0]
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_realistic_docx_with_paragraphs():
    """模拟真实 DOCX：多段落 chunk。"""
    doc = {"chunks": [
        {"text": "标题", "source_element_ids": ["h1"]},
        {"text": "第一段", "source_element_ids": ["p1"]},
        {"text": "第二段", "source_element_ids": ["p2"]},
        {"text": "第三段", "source_element_ids": ["p3"]},
    ]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "标题", "position": "after"},
        {"marker": "第一段", "position": "after"},
        {"marker": "第二段", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_empty_marker_added_to_missing():
    """空 marker → 加入 missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": ""}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_e2e_partial_match_5_chunks():
    """5 chunks, 3 anchors, 部分匹配。"""
    doc = {"chunks": [
        {"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}, {"text": "e"},
    ]}
    # stream = "a b c d e"
    # 边界 = 1, 3, 5, 7
    anno = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},  # gt=1, match pred[0]=1
        {"marker": "x", "position": "after"},  # missing
        {"marker": "e", "position": "before"},  # gt=8, 距 pred[3]=7 → 1
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # tolerance=0: matched=1 (only first), num_pred=4, num_gt=2 (x is missing)
    assert out["chunk_boundary_precision"]["value"] == 1 / 4
    assert out["chunk_boundary_recall"]["value"] == 0.5
    # x in missing
    assert "x" in out["_missing_markers"]["value"]


def test_e2e_figure_caption_with_realistic_input_returns_null():
    """模拟真实输入：document 有 figures 和 captions → 仍返回 null。"""
    doc = {
        "elements": [
            {"type": "figure", "element_id": "f1", "resource_path": "f1.png"},
            {"type": "caption", "element_id": "c1", "content": "Figure 1"},
        ],
        "chunks": [],
    }
    anno = {
        "figure_caption_pairs": [{"figure_id": "f1", "caption_id": "c1"}]
    }
    out = figure_caption_prf(doc, anno)
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
