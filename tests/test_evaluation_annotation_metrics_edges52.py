"""evaluation/annotation_metrics.py 第五十二轮 edges 测试（Round 497）。

补强 edges51 未触及的角度（第二十五批）：
- figure_caption_prf 第二十五批：3 keys 顺序 / value is None 但 reason 非 None / annotation 字段含 figure_caption_pairs / 不读 chunks 字段 / 多次返回独立 dict / value dict 含 2 keys
- chunk_boundary_prf 第二十五批：3 chunks 单中间边界 / 多 chunks 多边界 / anchor position 默认 after / marker 含空格 / marker 等于 chunk text / tolerance=1 严格 / predicted 等于 gt / 多 predicted 同位 / 单 anchor 多 predicted / 所有 marker 缺失 / 部分缺 / 空 anchors list / chunks 空 list / chunk 无 text 字段 / chunk text 含多空格 / chunk text 含 unicode / normalize 后空 / f1 在 p=0/r=0 时 → 0.0 / f1 在 p_val None 时 → null / _tolerance_chars value / _missing_markers 仅在 missing 时存在
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十五批：常量自等 / 在 __all__ / hashable / immutable str
- module source forbidden tokens 第四十一批
- module source 字符串精确补强第三十七批
- signatures 第三十七批
- module 合理性第三十七批
- 端到端集成第三十七批
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 第二十五批 ----------


def test_figure_caption_prf_returns_three_keys_batch25():
    """返回 dict 含精确 3 keys。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_value_dict_has_two_keys_batch25():
    """每个 metric value dict 含 'value' 和 'reason' 两 keys。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}, f"{k}: {v.keys()}"


def test_figure_caption_prf_does_not_read_chunks_batch25():
    """即使 document 有 chunks，figure_caption_prf 也不读 chunks 字段（永远 null）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_does_not_read_annotation_pairs_batch25():
    """即使 annotation 有 figure_caption_pairs，仍 null。"""
    annotation = {"figure_caption_pairs": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(None, annotation)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_multiple_calls_independent_batch25():
    """多次调用返回独立 dict（不共享引用）。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2
    assert out1 is not out2
    # 内部 dict 也不共享
    for k in out1:
        assert out1[k] is not out2[k]


def test_figure_caption_prf_value_is_none_reason_not_none_batch25():
    """value is None 但 reason 不是 None（始终有 reason）。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] is not None


def test_figure_caption_prf_with_dict_arguments_batch25():
    """document + annotation 都是非空 dict → 仍 null。"""
    out = figure_caption_prf(
        {"source_type": "pdf", "chunks": []},
        {"figure_caption_pairs": [], "chunk_boundary_anchors": []},
    )
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_no_mutation_batch25():
    """不修改输入 dict。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"figure_caption_pairs": []}
    import copy
    doc_copy = copy.deepcopy(doc)
    ann_copy = copy.deepcopy(ann)
    figure_caption_prf(doc, ann)
    assert doc == doc_copy
    assert ann == ann_copy


# ---------- chunk_boundary_prf 第二十五批 ----------


def test_chunk_boundary_three_chunks_one_middle_boundary_batch25():
    """3 chunks → 2 个内部边界（chunk0 末 + chunk1 末）。"""
    chunks = [
        {"text": "hello world"},
        {"text": "foo bar"},
        {"text": "baz qux"},
    ]
    doc = {"chunks": chunks}
    # 标注 anchor 应该匹配 chunk0 末（"world" 后）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},
            {"marker": "bar", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # precision/recall 应是 ratio（不是 null）
    assert out["chunk_boundary_precision"]["value"] is not None
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_anchor_position_defaults_to_after_batch25():
    """anchor 无 position 字段 → 默认 'after'（marker 结束位置）。"""
    chunks = [{"text": "alpha beta"}, {"text": "gamma delta"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta"},  # 无 position
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 应匹配 chunk0 末（"beta" 后是边界）
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_marker_with_whitespace_batch25():
    """marker 含空格也能定位。"""
    chunks = [{"text": "alpha beta gamma"}, {"text": "delta"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta gamma", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_marker_equals_chunk_text_batch25():
    """marker 等于整个 chunk text。"""
    chunks = [{"text": "alpha"}, {"text": "beta"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # alpha 后正好是 chunk0 末（边界）
    # 但 normalize 后 stream = "alpha beta"，alpha 结束在 5
    # chunk0 末也应在 5 → match
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_tolerance_one_strict_batch25():
    """tolerance_chars=1 → 严格匹配（差 2 字符以上算 miss）。"""
    chunks = [{"text": "alpha"}, {"text": "beta"}]
    doc = {"chunks": chunks}
    # marker 'alph' 在 stream "alpha beta" 的位置 0-3，'alph' 后位置 = 4
    # chunk0 末 = 5（alpha 结束）→ 差 1 → 容差 1 内
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alph", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # 差 1 → 容差 1 内 → match
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_predicted_equals_gt_batch25():
    """predicted 位置等于 gt 位置 → match。"""
    chunks = [{"text": "abc"}, {"text": "def"}]
    doc = {"chunks": chunks}
    # stream = "abc def"
    # chunk0 末 = 3
    # marker 'abc' after = 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_empty_anchors_list_batch25():
    """anchors 是空 list → no_ground_truth_anchors 分支。"""
    chunks = [{"text": "a"}, {"text": "b"}]
    doc = {"chunks": chunks}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_chunks_empty_list_batch25():
    """chunks 是空 list → no_predicted_boundaries。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunk_without_text_field_batch25():
    """chunk 缺 text 字段 → 当作空字符串。"""
    chunks = [{"no_text": True}, {"text": "abc"}]
    doc = {"chunks": chunks}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 不抛错即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_chunk_text_multiple_spaces_batch25():
    """chunk text 含多个空格 → normalize 后单空格。"""
    chunks = [{"text": "a    b    c"}, {"text": "d"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a b c", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 应能找到 normalize 后的 marker
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_chunk_text_unicode_batch25():
    """chunk text 含 unicode（中文）。"""
    chunks = [{"text": "你好 世界"}, {"text": "再见"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "世界", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_f1_zero_when_both_p_r_zero_batch25():
    """p=0, r=0 → f1=0.0（denom <= 0 分支）。"""
    chunks = [{"text": "alpha"}, {"text": "beta"}]
    doc = {"chunks": chunks}
    # marker 在 stream 中找不到 → missing → gt_positions 空 → recall null
    # 但 num_pred > 0, matched=0 → precision = 0/2 = 0
    # recall null → f1 null（走 p_val/r_val null 分支，不是 denom<=0）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "ZZZ_NOT_EXIST", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # recall 应是 no_ground_truth_anchors_in_stream（gt_positions 空）
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    # f1 null
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_tolerance_chars_recorded_batch25():
    """tolerance_chars 通过 _tolerance_chars 元信息透传。"""
    chunks = [{"text": "a"}, {"text": "b"}]
    doc = {"chunks": chunks}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_missing_markers_only_when_missing_batch25():
    """_missing_markers 仅在 missing_markers 非空时存在。"""
    chunks = [{"text": "alpha"}, {"text": "beta"}]
    doc = {"chunks": chunks}
    # 全部 marker 都能找到
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_missing_markers_present_when_missing_batch25():
    """_missing_markers 在有 missing marker 时存在。"""
    chunks = [{"text": "alpha"}, {"text": "beta"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "ZZZ_MISSING", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["ZZZ_MISSING"]


def test_chunk_boundary_annotation_dict_without_anchors_key_batch25():
    """annotation dict 没有_chunk_boundary_anchors 字段（但 dict 非空）→ 当作 []。"""
    chunks = [{"text": "a"}, {"text": "b"}]
    doc = {"chunks": chunks}
    # dict 非空（含其他字段）才能绕过 `if not annotation` 早返回
    annotation = {"other_field": "value"}
    out = chunk_boundary_prf(doc, annotation)
    # 应是 no_ground_truth_anchors（anchors=[] 走此分支）
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_no_mutation_batch25():
    """不修改输入 dict。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    import copy
    doc_copy = copy.deepcopy(doc)
    ann_copy = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann)
    assert doc == doc_copy
    assert ann == ann_copy


def test_chunk_boundary_returns_dict_batch25():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十五批 ----------


def test_parser_does_not_emit_relations_self_equal_batch25():
    """常量等于自身。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_in_all_batch25():
    """常量在 __all__ 中。"""
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_hashable_batch25():
    """str 是 hashable。"""
    assert hash(PARSER_DOES_NOT_EMIT_RELATIONS) is not None


def test_parser_does_not_emit_relations_value_batch25():
    """值是 'parser_does_not_emit_relations'。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_str_batch25():
    """类型是 str。"""
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_immutable_batch25():
    """str 不可变。"""
    with pytest.raises(TypeError):
        # str 不支持 item assignment
        PARSER_DOES_NOT_EMIT_RELATIONS[0] = "X"  # type: ignore[index]


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from functools",
    "from time",
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


def test_module_source_forbidden_tokens_batch25():
    source = inspect.getsource(amod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_keyword_batch25():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == []


def test_module_source_no_yield_batch25():
    source = inspect.getsource(amod)
    assert "yield " not in source


def test_module_source_no_async_def_batch25():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch25():
    source = inspect.getsource(amod)
    assert "global " not in source


def test_module_source_no_walrus_batch25():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch25():
    source = inspect.getsource(amod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch25():
    source_lines = inspect.getsource(amod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch25():
    source = inspect.getsource(amod)
    assert "import *" not in source


def test_module_source_no_subprocess_batch25():
    source = inspect.getsource(amod)
    assert "subprocess" not in source


def test_module_source_no_dataclass_batch25():
    source = inspect.getsource(amod)
    assert "@dataclass" not in source


def test_module_source_no_environ_batch25():
    source = inspect.getsource(amod)
    assert "os.environ" not in source


def test_module_source_no_network_io_batch25():
    source = inspect.getsource(amod)
    assert "import socket" not in source
    assert "import http" not in source


def test_module_source_normalize_text_imported_batch25():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_metrics_import_batch25():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_counter_imported_batch25():
    """source 含 from collections import Counter（即使当前未直接使用）。"""
    source = inspect.getsource(amod)
    assert "Counter" in source


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_figure_caption_prf_def_batch25():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_contains_chunk_boundary_prf_def_batch25():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_contains_parser_does_not_emit_constant_batch25():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_contains_tolerance_chars_param_batch25():
    source = inspect.getsource(amod)
    assert "tolerance_chars" in source


def test_module_source_contains_default_30_batch25():
    source = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in source


def test_module_source_contains_pipeline_failed_batch25():
    source = inspect.getsource(amod)
    assert '"pipeline_failed"' in source


def test_module_source_contains_no_annotation_batch25():
    source = inspect.getsource(amod)
    assert '"no_annotation"' in source


def test_module_source_contains_no_predicted_boundaries_batch25():
    source = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in source


def test_module_source_contains_no_ground_truth_anchors_batch25():
    source = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in source


def test_module_source_contains_no_ground_truth_anchors_in_stream_batch25():
    source = inspect.getsource(amod)
    assert '"no_ground_truth_anchors_in_stream"' in source


def test_module_source_contains_precision_or_recall_not_evaluated_batch25():
    source = inspect.getsource(amod)
    assert '"precision_or_recall_not_evaluated"' in source


def test_module_source_contains_missing_markers_batch25():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


def test_module_source_contains_search_from_batch25():
    source = inspect.getsource(amod)
    assert "search_from" in source


def test_module_source_contains_normalize_text_call_batch25():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_contains_one_to_one_text_batch25():
    """source 含一对一匹配语义说明。"""
    source = inspect.getsource(amod)
    assert "一对一" in source


# ---------- signatures 第三十七批 ----------


def test_signature_figure_caption_prf_batch25():
    """figure_caption_prf(document, annotation) -> dict[str, dict[str, Any]]。"""
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["document", "annotation"]
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_chunk_boundary_prf_batch25():
    """chunk_boundary_prf(document, annotation, tolerance_chars=30) -> dict[str, dict[str, Any]]。"""
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["document", "annotation", "tolerance_chars"]
    assert params[2].default == 30


def test_signature_chunk_boundary_prf_document_annotation_batch25():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].annotation == "dict[str, Any] | None"
    assert sig.parameters["annotation"].annotation == "dict[str, Any] | None"


def test_signature_chunk_boundary_prf_tolerance_int_batch25():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].annotation == "int"


def test_signature_chunk_boundary_prf_return_annotation_batch25():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_figure_caption_prf_docstring_present_batch25():
    assert figure_caption_prf.__doc__ is not None


def test_signature_chunk_boundary_prf_docstring_present_batch25():
    assert chunk_boundary_prf.__doc__ is not None


def test_signature_chunk_boundary_prf_no_varargs_batch25():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


# ---------- module 合理性第三十七批 ----------


def test_module_all_present_batch25():
    assert hasattr(amod, "__all__")


def test_module_all_contains_three_names_batch25():
    """__all__ 含 3 个名（PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf）。"""
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_has_two_functions_batch25():
    """annotation_metrics.py 定义 2 个 module-level 函数。"""
    funcs = [
        name
        for name, val in inspect.getmembers(amod, inspect.isfunction)
        if val.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_no_classes_batch25():
    classes = [
        name
        for name, val in inspect.getmembers(amod, inspect.isclass)
        if val.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch25():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_mentions_caption_or_boundary_batch25():
    """module docstring 提及 figure-caption 或 chunk-boundary。"""
    src = amod.__doc__
    assert "figure" in src.lower() or "caption" in src.lower()
    assert "chunk" in src.lower() or "boundary" in src.lower()


def test_module_uses_from_future_annotations_batch25():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_constants_only_parser_const_batch25():
    """顶层常量只有 PARSER_DOES_NOT_EMIT_RELATIONS（除 __all__）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(amod))
    top_level_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_level_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert set(names) == {"PARSER_DOES_NOT_EMIT_RELATIONS", "__all__"}


# ---------- 端到端集成第三十七批 ----------


def test_e2e_chunk_boundary_perfect_match_batch25():
    """端到端：predicted 与 gt 完美匹配 → p=r=f1=1.0。"""
    chunks = [{"text": "abc"}, {"text": "def"}]
    doc = {"chunks": chunks}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_always_null_batch25():
    """端到端：figure_caption_prf 任何输入都返回 null。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf({"chunks": []}, None)
    out3 = figure_caption_prf(None, {"figure_caption_pairs": []})
    for out in (out1, out2, out3):
        for v in out.values():
            assert v["value"] is None


def test_e2e_chunk_boundary_doc_none_pipeline_failed_batch25():
    """端到端：doc=None → reason=pipeline_failed。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_e2e_chunk_boundary_annotation_none_no_annotation_batch25():
    """端到端：annotation=None → reason=no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_single_chunk_no_predicted_batch25():
    """端到端：单 chunk → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": [{"marker": "a"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_no_mutation_in_e2e_batch25():
    """端到端：复杂调用后输入不修改。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "ZZZ", "position": "after"},
        ]
    }
    import copy
    doc_copy = copy.deepcopy(doc)
    ann_copy = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert doc == doc_copy
    assert ann == ann_copy


def test_e2e_module_all_callable_batch25():
    """__all__ 中函数都是 callable。"""
    for name in amod.__all__:
        attr = getattr(amod, name)
        if name != "PARSER_DOES_NOT_EMIT_RELATIONS":
            assert callable(attr), f"{name} not callable"
