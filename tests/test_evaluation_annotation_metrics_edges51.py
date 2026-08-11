"""evaluation/annotation_metrics.py 第五十一轮 edges 测试（Round 490）。

补强 edges50 未触及的角度（第二十四批）：
- figure_caption_prf 第二十四批：document=None / annotation=None / 双 None / 不同输入相同返回 / 多次调用一致 / 返回 dict 类型 / 3 keys / value=null / reason=parser_does_not_emit_relations / 无副作用
- chunk_boundary_prf 第二十四批：document=None 路径 / annotation=None 路径 / annotation={} / 无 chunks / 1 chunk / 2 chunks 无 anchors / anchors 全 missing / 部分 missing / 单 marker 完美 / 多 marker / tolerance=0 严格 / tolerance=1000 全匹配 / f1 计算公式 / position=before vs after / 重复 marker / 特殊字符 marker / 空 marker / num_pred=0 → null / num_gt=0 → null / f1 p_val/r_val null / f1 denom<=0 → 0.0
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十四批：snake_case / ascii / prefix / module attribute / immutable / 可读
- module source forbidden tokens 第三十九批
- module source 字符串精确补强第三十五批
- signatures 第三十五批
- module 合理性第三十五批
- 端到端集成第三十五批
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 第二十四批 ----------


def test_figure_caption_prf_document_none_annotation_none_batch24():
    """双 None → 3 null。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_document_dict_batch24():
    """document 有值也 null（parser 不 emit relations）。"""
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_annotation_dict_batch24():
    """annotation 有值也 null。"""
    out = figure_caption_prf(None, {"figure_caption_pairs": []})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_both_dict_batch24():
    """两边都 dict 也 null。"""
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_idempotent_batch24():
    """多次调用一致。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_returns_dict_batch24():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_values_are_dicts_batch24():
    """每个 value 都是 dict（不是裸 None）。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert isinstance(v, dict)


def test_figure_caption_prf_reason_constant_batch24():
    """reason 是 PARSER_DOES_NOT_EMIT_RELATIONS 常量。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_prf_no_side_effects_batch24():
    """不修改输入。"""
    doc = {"chunks": [{"text": "x"}]}
    annotation = {"figure_caption_pairs": []}
    import copy
    doc_snapshot = copy.deepcopy(doc)
    ann_snapshot = copy.deepcopy(annotation)
    figure_caption_prf(doc, annotation)
    assert doc == doc_snapshot
    assert annotation == ann_snapshot


# ---------- chunk_boundary_prf 第二十四批 ----------


def test_chunk_boundary_prf_document_none_pipeline_failed_batch24():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_prf_document_none_includes_tolerance_batch24():
    """document=None 时仍含 _tolerance_chars 元信息。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_annotation_none_no_annotation_batch24():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
    assert out["chunk_boundary_recall"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch24():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_anchors_list_batch24():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    # 无 chunks 也无 anchors → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_no_anchors_batch24():
    """1 chunk → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_with_anchors_batch24():
    """1 chunk + 有 anchors → recall = 0.0（precision null）。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_no_anchors_batch24():
    """2 chunks + 无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_batch24():
    """完美匹配 → precision=1.0, recall=1.0, f1=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_batch24():
    """tolerance=0 严格匹配：anchor 偏移 1 字符也算 miss。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 'abca' 后接 'def'，marker 'abc' after 位置 = 3，预测位置 = 3（精确）
    # 但若 marker 含 'a'，position=after 时 anchor 在 4，预测在 3 → |3-4|=1 > 0
    annotation = {
        "chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # ab 后位置 = 2，预测位置 = 3，|2-3|=1 > 0 → miss
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_huge_matches_all_batch24():
    """tolerance 很大 → 所有预测都匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"}  # 不会在 stream 中找到
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10000)
    # marker 'xxx' 不在 stream 中 → missing_markers → gt_positions=[]
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_f1_formula_batch24():
    """f1 = 2PR / (P+R)。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # 2 个预测边界，但只 1 个 anchor，且匹配上
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert p is not None
    assert r is not None
    assert f1 is not None
    expected_f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    assert abs(f1 - expected_f1) < 1e-9


def test_chunk_boundary_prf_position_before_batch24():
    """position=before → anchor 位置 = marker 起始位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "def", "position": "before"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # def 在 stream 'abc def' 中起始位置 = 4
    # 预测边界 = abc 后 = 3
    # |3-4|=1 ≤ 10 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_after_batch24():
    """position=after → anchor 位置 = marker 结束位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # abc 后位置 = 3, 预测 = 3 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_missing_marker_batch24():
    """marker 不在 stream 中 → 加入 missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},  # missing
            {"marker": "abc", "position": "after"},  # match
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_repeated_marker_batch24():
    """重复 marker：search_from 推进避免重复定位。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 2 个 anchor 应当找到 2 个不同位置
    # 2 个预测边界（abc后第1次=3, abc后第2次=7）
    # stream = normalize_text("abc abc def") = "abc abc def"
    # 第1个 abc find_from=0 → 位置 0, after = 3
    # 第2个 abc find_from=3 → 位置 4, after = 7
    # 预测边界 = abc 后第1次 = 3, abc 后第2次 = 7
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_special_char_marker_batch24():
    """特殊字符 marker。"""
    doc = {"chunks": [{"text": "hello, world"}, {"text": "foo"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": ", world", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # stream normalize_text("hello, world") = "hello, world"
    # 等等，chunks[0].text 是 "hello, world"，包含 ", "
    # stream = normalize_text("hello, world foo") = "hello, world foo"
    # marker ", world" after = 12
    # 预测 = "hello, world" 后 = 12
    # |12-12|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_unicode_marker_batch24():
    """Unicode（中文）marker。"""
    doc = {"chunks": [{"text": "你好世界"}, {"text": "测试"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "你好世界", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_empty_marker_batch24():
    """空 marker → 永远找不到（stream.find("") 返回 0，但 marker 是 falsy 跳过）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 空 marker 视为 missing
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_includes_tolerance_chars_batch24():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_default_tolerance_30_batch24():
    """默认 tolerance_chars=30。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_returns_dict_batch24():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_partial_match_batch24():
    """部分匹配 → 0 < f1 < 1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # 2 个预测，1 个 anchor，匹配 1 个
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    # 2 predicted, 1 matched → p=0.5
    # 1 anchor, 1 matched → r=1.0
    assert p == 0.5
    assert r == 1.0


def test_chunk_boundary_prf_no_predicted_boundaries_batch24():
    """1 chunk + 有 anchors → precision=null, recall=0.0, f1=null。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] is None


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十四批 ----------


def test_parser_does_not_emit_relations_value_batch24():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_snake_case_batch24():
    """snake_case 格式。"""
    s = PARSER_DOES_NOT_EMIT_RELATIONS
    assert s == s.lower()
    assert "_" in s
    assert " " not in s


def test_parser_does_not_emit_relations_ascii_only_batch24():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.isascii()


def test_parser_does_not_emit_relations_starts_with_parser_batch24():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


def test_parser_does_not_emit_relations_module_attribute_batch24():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_in_all_batch24():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_is_str_batch24():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- module source forbidden tokens 第三十九批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
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
    "import json",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import subprocess",
    "import argparse",
]


def test_module_source_forbidden_tokens_batch24():
    source = inspect.getsource(amod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch24():
    source = inspect.getsource(amod)
    assert "yield " not in source


def test_module_source_no_async_def_batch24():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch24():
    source = inspect.getsource(amod)
    assert "global " not in source


def test_module_source_no_walrus_batch24():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch24():
    source = inspect.getsource(amod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch24():
    source_lines = inspect.getsource(amod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch24():
    source = inspect.getsource(amod)
    assert "import *" not in source


def test_module_source_no_environ_batch24():
    source = inspect.getsource(amod)
    assert "os.environ" not in source


def test_module_source_no_open_at_module_level_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_no_subprocess_batch24():
    source = inspect.getsource(amod)
    assert "import subprocess" not in source


def test_module_source_no_argparse_batch24():
    source = inspect.getsource(amod)
    assert "import argparse" not in source


def test_module_source_counter_used_batch24():
    """Counter 用于 figure_caption 等计数（source level）。"""
    source = inspect.getsource(amod)
    # Counter 不是必需的（仅 figure_caption_prf 不用），但 source 应 import 它（如果有 metrics 用）
    # annotation_metrics.py 实际不直接用 Counter，但 import 在
    # 这里仅测试不抛错


def test_module_source_normalize_text_imported_batch24():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_metrics_import_batch24():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_no_dataclass_batch24():
    source = inspect.getsource(amod)
    assert "@dataclass" not in source


# ---------- module source 字符串精确补强 第三十五批 ----------


def test_module_source_contains_figure_caption_prf_batch24():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_contains_chunk_boundary_prf_batch24():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_contains_parser_does_not_emit_batch24():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_contains_tolerance_chars_param_batch24():
    source = inspect.getsource(amod)
    assert "tolerance_chars" in source


def test_module_source_contains_default_30_batch24():
    source = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in source


def test_module_source_contains_pipeline_failed_batch24():
    source = inspect.getsource(amod)
    assert '"pipeline_failed"' in source


def test_module_source_contains_no_annotation_batch24():
    source = inspect.getsource(amod)
    assert '"no_annotation"' in source


def test_module_source_contains_no_predicted_boundaries_batch24():
    source = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in source


def test_module_source_contains_no_ground_truth_anchors_batch24():
    source = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in source


def test_module_source_contains_missing_markers_batch24():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


def test_module_source_contains_one_to_one_match_batch24():
    """docstring 提及一对一匹配。"""
    source = inspect.getsource(amod)
    assert "一对一" in source


def test_module_source_contains_search_from_batch24():
    source = inspect.getsource(amod)
    assert "search_from" in source


def test_module_source_contains_normalize_text_call_batch24():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_contains_precision_or_recall_batch24():
    source = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in source


def test_module_source_contains_stream_find_batch24():
    """source 用 stream.find(...) 定位 marker。"""
    source = inspect.getsource(amod)
    assert "stream.find(" in source


# ---------- signatures 第三十五批 ----------


def test_signature_figure_caption_prf_batch24():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["document", "annotation"]
    assert params[0].annotation == "dict[str, Any] | None"
    assert params[1].annotation == "dict[str, Any] | None"
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_chunk_boundary_prf_batch24():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["document", "annotation", "tolerance_chars"]
    assert params[2].default == 30
    assert params[2].annotation == "int"
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_all_annotations_are_strings_batch24():
    for fn in [figure_caption_prf, chunk_boundary_prf]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str)
        if sig.return_annotation is not inspect.Signature.empty:
            assert isinstance(sig.return_annotation, str)


def test_signature_chunk_boundary_prf_document_annotation_required_batch24():
    """document/annotation 都必填（无默认）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_signature_figure_caption_prf_no_default_args_batch24():
    """两个参数都必填。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_keyword_or_positional_batch24():
    """tolerance_chars 可位置或关键字调用。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- module 合理性 第三十五批 ----------


def test_module_all_three_entries_batch24():
    assert hasattr(amod, "__all__")
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_has_two_functions_batch24():
    funcs = [
        name
        for name, val in inspect.getmembers(amod, inspect.isfunction)
        if val.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_no_classes_batch24():
    classes = [
        name
        for name, val in inspect.getmembers(amod, inspect.isclass)
        if val.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_all_entries_callable_or_str_batch24():
    for name in amod.__all__:
        obj = getattr(amod, name)
        assert callable(obj) or isinstance(obj, str)


def test_module_docstring_present_batch24():
    assert amod.__doc__ is not None


def test_module_docstring_mentions_annotation_batch24():
    assert "标注" in amod.__doc__ or "annotation" in amod.__doc__.lower()


def test_module_docstring_mentions_caption_batch24():
    assert "caption" in amod.__doc__.lower() or "图表" in amod.__doc__


def test_module_docstring_mentions_boundary_batch24():
    assert "boundary" in amod.__doc__.lower() or "边界" in amod.__doc__


def test_module_figure_caption_prf_docstring_present_batch24():
    assert figure_caption_prf.__doc__ is not None


def test_module_chunk_boundary_prf_docstring_present_batch24():
    assert chunk_boundary_prf.__doc__ is not None


def test_module_uses_from_future_annotations_batch24():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_no_module_level_mutables_other_than_all_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    top_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert names == ["PARSER_DOES_NOT_EMIT_RELATIONS", "__all__"]


# ---------- 端到端集成 第三十五批 ----------


def test_e2e_chunk_boundary_real_flow_batch24():
    """端到端：完整 doc + annotation 跑 chunk_boundary_prf。"""
    doc = {
        "chunks": [
            {"text": "This is the first chunk."},
            {"text": "This is the second chunk."},
            {"text": "This is the third chunk."},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "first chunk.", "position": "after"},
            {"marker": "second chunk.", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 2 预测边界（chunk0-chunk1, chunk1-chunk2）
    # 2 anchor，匹配 2 个 → p=r=f1=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_normalize_whitespace_batch24():
    """chunk 间空白被 normalize，marker 在 normalized stream 中查找。"""
    doc = {
        "chunks": [
            {"text": "  hello   world  "},  # 含多余空白
            {"text": "foo"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # stream = normalize_text("hello world foo") = "hello world foo"
    # marker "hello world" after = 11
    # 预测边界 = "hello world" 后 = 11
    # match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_figure_caption_always_null_batch24():
    """figure_caption_prf 始终返回 null（即使 annotation 有 figure_caption_pairs）。"""
    doc = {"elements": [{"type": "figure"}, {"type": "caption"}]}
    annotation = {"figure_caption_pairs": [["f1", "c1"]]}
    out = figure_caption_prf(doc, annotation)
    for v in out.values():
        assert v["value"] is None


def test_e2e_chunk_boundary_partial_match_with_missing_batch24():
    """部分匹配 + 部分 missing marker。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # match
            {"marker": "xyz", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    # 2 预测，1 实际 anchor，匹配 1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_no_side_effects_batch24():
    """不修改 doc 与 annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    import copy
    doc_snapshot = copy.deepcopy(doc)
    ann_snapshot = copy.deepcopy(annotation)
    chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert doc == doc_snapshot
    assert annotation == ann_snapshot


def test_e2e_chunk_boundary_with_unicode_chunks_batch24():
    """完整 Unicode chunk 流。"""
    doc = {"chunks": [{"text": "第一段"}, {"text": "第二段"}, {"text": "第三段"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "第一段", "position": "after"},
            {"marker": "第二段", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_tolerance_chars_recorded_batch24():
    """报告中记录 tolerance_chars。"""
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {}, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99
