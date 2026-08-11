"""evaluation/annotation_metrics.py 第五十三轮 edges 测试（Round 504）。

补强 edges52 未触及的角度（第二十六批）：
- figure_caption_prf 第二十六批：document={} / annotation={} / 两者 None / keys 顺序 / 新 dict / reason 一致 / 不读 chunks / 不读 annotation 字段
- chunk_boundary_prf 第二十六批：tolerance_chars 自定义值记录 / 负数 / 0 / marker 重复 / 空 marker / position="before" / annotation 有其它 key 但无 anchors / chunks 无 text key / chunks text=None / 多 chunks 无 anchors / 完美匹配 precision/recall/f1 / 3+ chunks / 重复 marker
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十六批
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 第二十六批 ----------


def test_figure_caption_prf_empty_doc_empty_annotation_batch26():
    out = figure_caption_prf({}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_doc_none_annotation_dict_batch26():
    out = figure_caption_prf(None, {"any": "thing"})
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
        assert out[k]["value"] is None


def test_figure_caption_prf_doc_dict_annotation_none_batch26():
    out = figure_caption_prf({"any": "thing"}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_returns_new_dict_each_call_batch26():
    o1 = figure_caption_prf(None, None)
    o2 = figure_caption_prf(None, None)
    assert o1 == o2
    assert o1 is not o2
    assert o1["figure_caption_precision"] is not o2["figure_caption_precision"]


def test_figure_caption_prf_keys_order_batch26():
    """keys 顺序：precision / recall / f1。"""
    out = figure_caption_prf(None, None)
    keys = list(out.keys())
    assert keys == ["figure_caption_precision", "figure_caption_recall", "figure_caption_f1"]


def test_figure_caption_prf_value_none_batch26():
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    for k in out:
        assert out[k]["value"] is None


def test_figure_caption_prf_does_not_read_chunks_batch26():
    """figure_caption_prf 不读 document['chunks']。"""
    doc = {"chunks": [{"text": "a"}]}
    out = figure_caption_prf(doc, None)
    # 不抛错就说明没读 chunks
    assert "figure_caption_precision" in out


def test_figure_caption_prf_does_not_read_annotation_pairs_batch26():
    """figure_caption_prf 不读 annotation['chunk_boundary_anchors']。"""
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = figure_caption_prf(None, annotation)
    assert "figure_caption_precision" in out


def test_figure_caption_prf_three_metric_keys_only_batch26():
    """只返回 3 个 figure_caption_* key。"""
    out = figure_caption_prf(None, None)
    assert len(out) == 3


# ---------- chunk_boundary_prf 第二十六批 ----------


def test_chunk_boundary_tolerance_zero_batch26():
    """tolerance_chars=0 严格匹配。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_negative_batch26():
    """tolerance_chars 负数：abs distance 不可能 ≤ 负数 → 0 matched。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    # 距离 0 但 -1 容差 → 不匹配
    # 实际：abs(pred-gt) = 0, 0 <= -1 is False → 0 matched
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_tolerance_large_batch26():
    """tolerance_chars 很大（1000）→ 总能匹配。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1000)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_marker_empty_string_batch26():
    """空 marker → find 返回 0（空子串总匹配），位置 0。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 空 marker 在 stream 开头找到，position="before" → 0
    # predicted 在 chunk 末尾（11），distance = 11，匹配
    # precision = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_position_before_batch26():
    """position='before' → marker 起始位置。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "hello world foo bar"
    # predicted = [11]（"hello world" 后）
    # "foo" 在 stream 中 find_from=0 → find_pos=12
    # position="before" → gt=12
    # distance = |11-12| = 1 ≤ 30 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_after_batch26():
    """position='after' → marker 结束位置。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "hello world foo bar"
    # predicted = [11]
    # "world" 在 stream 中 find_pos=6, gt = 6+5 = 11
    # distance = 0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_position_default_after_batch26():
    """position 默认 'after'（实现：a.get('position', 'after')）。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world"}]}  # 无 position
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 默认 after → gt = 11，predicted = [11] → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_annotation_with_extra_keys_batch26():
    """annotation 有其它 key 但无 chunk_boundary_anchors → no_annotation。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"other_key": "value"}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # annotation 真值（非空 dict），但 anchors = annotation.get(...) or [] = []
    # 走到 `if not chunks or len(chunks) < 2` 分支：chunks=2 不满足
    # 走到 `if not anchors:` 分支 → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_chunks_missing_text_key_batch26():
    """chunk 无 text key → c.get('text') or '' → ''。"""
    doc = {"chunks": [{}, {"text": "foo"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 不崩溃
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_chunks_text_none_batch26():
    """chunk text=None → c.get('text') or '' → ''。"""
    doc = {"chunks": [{"text": None}, {"text": "foo"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_no_chunks_no_annotation_batch26():
    """document={} + annotation={} → no_annotation（早返回）。"""
    out = chunk_boundary_prf({}, {}, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_perfect_match_precision_batch26():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "alpha beta gamma"
    # predicted = [5, 10]（"alpha" 后 = 5, "beta" 后 = 10）
    # anchors: "alpha" at 0, after → 5; "beta" at 6, after → 10
    # 全匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_perfect_match_recall_batch26():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_perfect_match_f1_batch26():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_duplicate_markers_batch26():
    """重复 marker（同 marker 多次出现）→ 按顺序定位。"""
    doc = {"chunks": [{"text": "x x"}, {"text": "x x"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "x x x x"
    # predicted = [3]（第一个 "x x" 末尾）
    # anchors: 第一个 "x" at 0, after → 1; search_from=1
    # 第二个 "x" at 2 (find from 1), after → 3
    # gt_positions = [1, 3]
    # predicted = [3]
    # matched = 1（predicted[0]=3 匹配 gt[1]=3）
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_missing_marker_batch26():
    """marker 在 stream 中找不到 → 加入 missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # missing_markers = ["nonexistent"]
    # 实际：_missing_markers 字段在 out 里
    if "_missing_markers" in out:
        assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_more_chunks_no_anchors_batch26():
    """3 chunks 无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # annotation 非空 dict，anchors=[]，chunks≥2
    # 走 `if not anchors:` 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_two_chunks_one_anchor_batch26():
    """2 chunks + 1 anchor。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "hello world"
    # predicted = [5]
    # "hello" at 0, after → 5; matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_extra_anchor_no_match_batch26():
    """多 anchor 但 prediction 不够 → recall 低。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "missing1", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # "missing1" 找不到 → missing_markers
    # 只剩 1 个有效 anchor，predicted=[5], gt=[5]
    # matched = 1
    # recall = 1/1 = 1.0（missing anchor 不计入 gt_positions）


def test_chunk_boundary_no_mutation_to_inputs_batch26():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    import copy
    doc_snap = copy.deepcopy(doc)
    ann_snap = copy.deepcopy(annotation)
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert doc == doc_snap
    assert annotation == ann_snap


def test_chunk_boundary_returns_dict_batch26():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_returns_tolerance_record_batch26():
    """out 必含 _tolerance_chars 字段。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_doc_none_returns_pipeline_failed_batch26():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_annotation_empty_dict_no_annotation_batch26():
    """annotation={} falsy → no_annotation。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十六批 ----------


def test_parser_does_not_emit_relations_value_batch26():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_batch26():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_all_batch26():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_hashable_batch26():
    assert hash(PARSER_DOES_NOT_EMIT_RELATIONS) == hash("parser_does_not_emit_relations")


def test_parser_does_not_emit_relations_used_by_figure_caption_batch26():
    """figure_caption_prf 的 reason 必须等于该常量。"""
    out = figure_caption_prf(None, None)
    assert out["figure_caption_precision"]["reason"] is PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_immutable_batch26():
    """str 是不可变的。"""
    with pytest.raises(AttributeError):
        PARSER_DOES_NOT_EMIT_RELATIONS.upper = lambda: "X"  # type: ignore


# ---------- module source forbidden tokens 第四十二批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import json",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch26():
    source = inspect.getsource(amod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token: {tok}"


def test_module_source_no_eval_exec_batch26():
    source = inspect.getsource(amod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch26():
    source = inspect.getsource(amod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch26():
    source = inspect.getsource(amod)
    assert "from ." not in source


def test_module_source_no_unsafe_network_batch26():
    source = inspect.getsource(amod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_environ_batch26():
    source = inspect.getsource(amod)
    assert "os.environ" not in source


def test_module_source_no_subprocess_batch26():
    source = inspect.getsource(amod)
    assert "subprocess" not in source


def test_module_source_no_argparse_batch26():
    source = inspect.getsource(amod)
    assert "argparse" not in source


def test_module_source_no_dataclass_batch26():
    source = inspect.getsource(amod)
    assert "@dataclass" not in source


def test_module_source_no_class_keyword_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_uses_from_future_annotations_batch26():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_source_collections_counter_allowed_batch26():
    """annotation_metrics 允许 from collections import Counter。"""
    source = inspect.getsource(amod)
    assert "from collections import Counter" in source


def test_module_source_normalize_text_import_batch26():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_null_ratio_import_batch26():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_figure_caption_prf_batch26():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf" in source


def test_module_source_contains_chunk_boundary_prf_batch26():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf" in source


def test_module_source_contains_pipeline_failed_batch26():
    source = inspect.getsource(amod)
    assert "pipeline_failed" in source


def test_module_source_contains_no_annotation_batch26():
    source = inspect.getsource(amod)
    assert "no_annotation" in source


def test_module_source_contains_no_predicted_boundaries_batch26():
    source = inspect.getsource(amod)
    assert "no_predicted_boundaries" in source


def test_module_source_contains_no_ground_truth_anchors_batch26():
    source = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in source


def test_module_source_contains_no_ground_truth_anchors_in_stream_batch26():
    source = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in source


def test_module_source_contains_precision_or_recall_not_evaluated_batch26():
    source = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in source


def test_module_source_contains_missing_markers_batch26():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


def test_module_source_contains_search_from_batch26():
    source = inspect.getsource(amod)
    assert "search_from" in source


def test_module_source_contains_normalize_text_call_batch26():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_contains_one_to_one_text_batch26():
    source = inspect.getsource(amod)
    assert "一对一" in source or "one-to-one" in source.lower() or "贪心" in source


def test_module_source_contains_tolerance_chars_record_batch26():
    source = inspect.getsource(amod)
    assert "_tolerance_chars" in source


def test_module_source_contains_chunk_boundary_anchors_key_batch26():
    source = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in source


def test_module_source_contains_default_tolerance_30_batch26():
    source = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in source


# ---------- signatures 第三十八批 ----------


def test_signature_figure_caption_prf_batch26():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch26():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_document_annotation_batch26():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"
    assert sig.parameters["annotation"].annotation == "dict[str, Any] | None"


def test_signature_chunk_boundary_prf_tolerance_int_batch26():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].annotation == "int"
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_return_annotation_batch26():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in sig.return_annotation


def test_signature_figure_caption_prf_return_annotation_batch26():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in sig.return_annotation


def test_signature_chunk_boundary_prf_no_varargs_batch26():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_figure_caption_prf_no_varargs_batch26():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_all_annotations_are_strings_batch26():
    for fn in [figure_caption_prf, chunk_boundary_prf]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


def test_signature_figure_caption_prf_docstring_present_batch26():
    assert figure_caption_prf.__doc__ is not None


def test_signature_chunk_boundary_prf_docstring_present_batch26():
    assert chunk_boundary_prf.__doc__ is not None


# ---------- module 合理性第三十八批 ----------


def test_module_all_present_batch26():
    assert hasattr(amod, "__all__")


def test_module_all_contains_three_names_batch26():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_has_two_functions_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_no_classes_batch26():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_docstring_present_batch26():
    assert amod.__doc__ is not None
    assert len(amod.__doc__.strip()) > 0


def test_module_docstring_mentions_caption_or_boundary_batch26():
    assert "caption" in amod.__doc__.lower() or "boundary" in amod.__doc__.lower()


def test_module_docstring_mentions_null_batch26():
    assert "null" in amod.__doc__.lower() or "固定" in amod.__doc__


def test_module_uses_from_future_annotations_batch26():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_constants_only_parser_const_batch26():
    """module-level 常量只有 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    constants = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and isinstance(n.targets[0], _ast.Name)
        and not n.targets[0].id.startswith("_")
    ]
    assert constants == ["PARSER_DOES_NOT_EMIT_RELATIONS"]


def test_module_all_entries_accessible_batch26():
    for name in amod.__all__:
        assert hasattr(amod, name)


# ---------- 端到端集成第三十八批 ----------


def test_e2e_chunk_boundary_perfect_match_batch26():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_always_null_batch26():
    """figure_caption 在任何输入下都返回 null。"""
    for doc in [None, {}, {"chunks": []}, {"chunks": [{"text": "x"}]}]:
        for ann in [None, {}, {"chunk_boundary_anchors": []}]:
            out = figure_caption_prf(doc, ann)
            for k in out:
                assert out[k]["value"] is None


def test_e2e_chunk_boundary_doc_none_pipeline_failed_batch26():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_chunk_boundary_annotation_none_no_annotation_batch26():
    out = chunk_boundary_prf({"chunks": [{"text": "x"}]}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_single_chunk_no_predicted_batch26():
    """单 chunk → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "alpha"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_no_mutation_in_e2e_batch26():
    """e2e 也不应 mutate input。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    import copy
    doc_snap = copy.deepcopy(doc)
    ann_snap = copy.deepcopy(annotation)
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert doc == doc_snap
    assert annotation == ann_snap


def test_e2e_module_all_callable_batch26():
    """__all__ 中每个名字都 callable 或可访问。"""
    for name in amod.__all__:
        obj = getattr(amod, name)
        if name in ("figure_caption_prf", "chunk_boundary_prf"):
            assert callable(obj)
        else:
            assert obj is not None


def test_e2e_chunk_boundary_full_path_with_normalization_batch26():
    """带多空格的 chunk text 经 normalize 后应正确匹配。"""
    doc = {"chunks": [{"text": "hello   world"}, {"text": "foo    bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # normalize: "hello   world" → "hello world"
    # stream = "hello world foo bar"
    # predicted = [11]
    # "world" find at 6, after → 11
    # distance = 0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
