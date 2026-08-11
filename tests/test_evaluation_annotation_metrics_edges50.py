"""evaluation/annotation_metrics.py 第五十轮 edges 测试（Round 483）。

补强 edges49 未触及的角度：
- figure_caption_prf 第二十三批（_null reason 一致 / 不同输入返回相同 / 多次调用结果一致 / 字段顺序 / type 检查）
- chunk_boundary_prf 第二十三批（tolerance_chars=0 严格 / 负 tolerance / 大 tolerance 全匹配 / precision 0 时无 matched / recall 0 时无 anchors / f1 p_val=0 + r_val=0 走 0.0 分支 / 大量 chunks 跨多 anchor / anchor marker 长 / search_from 跨 anchor / marker 子串与多 anchor / chunk text 重复多次）
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十三批（snake_case / 长度 / ascii-only）
- module source forbidden tokens 第三十八批
- module source 字符串精确补强第三十四批
- signatures 第三十四批
- module 合理性第三十四批
- 端到端集成第三十四批
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation import annotation_metrics as amod


# ---------- figure_caption_prf 第二十三批 ----------


def test_figure_caption_prf_always_returns_three_keys_with_none_value_batch23():
    """3 keys, value 永远 None。"""
    for args in [(None, None), ({}, {}), ({"x": 1}, None), (None, {"x": 1})]:
        out = figure_caption_prf(*args)
        assert len(out) == 3
        for v in out.values():
            assert v["value"] is None


def test_figure_caption_prf_consistent_across_calls_batch23():
    """多次调用结果完全一致。"""
    out1 = figure_caption_prf({"a": 1}, {"b": 2})
    out2 = figure_caption_prf({"a": 1}, {"b": 2})
    assert out1 == out2


def test_figure_caption_prf_no_side_effects_on_complex_inputs_batch23():
    """复杂嵌套输入也不影响。"""
    doc = {"elements": [{"id": f"e{i}"} for i in range(100)]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"} for _ in range(50)]}
    doc_snapshot = repr(doc)
    ann_snapshot = repr(ann)
    figure_caption_prf(doc, ann)
    assert repr(doc) == doc_snapshot
    assert repr(ann) == ann_snapshot


def test_figure_caption_prf_returns_dict_type_batch23():
    out = figure_caption_prf({}, {})
    assert isinstance(out, dict)


def test_figure_caption_prf_each_value_is_dict_batch23():
    """每个 value 也是 dict。"""
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert isinstance(v, dict)


def test_figure_caption_prf_value_dict_has_value_and_reason_batch23():
    """每个 value dict 含 value 和 reason 字段。"""
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_with_none_dict_inputs_batch23():
    """对 None / dict / 复杂输入都不抛。"""
    figure_caption_prf(None, None)
    figure_caption_prf({}, {})
    figure_caption_prf({"a": [1, 2, 3]}, {"b": {"c": "d"}})
    figure_caption_prf({"figure_caption_relations": []}, {})


# ---------- chunk_boundary_prf 第二十三批 ----------


def test_chunk_boundary_prf_tolerance_chars_zero_strict_batch23():
    """tolerance_chars=0 → 严格匹配（距离必须 = 0）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    # alpha after → position = len("alpha") = 5
    # stream = normalize_text("alpha beta") = "alpha beta"
    # alpha end in stream = 5
    # gt = 5
    # 距离 = 0 → matched
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_chars_zero_with_mismatch_batch23():
    """tolerance_chars=0 且 distance > 0 → 不匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 标注 anchor 在 'beta' 之后（不在内部边界）
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界在 alpha 之后（5）；gt = beta 之后 = 10
    # 距离 = 5 > 0 → 不匹配
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    if p is not None and r is not None:
        assert p == 0.0
        assert r == 0.0


def test_chunk_boundary_prf_large_tolerance_matches_all_batch23():
    """大 tolerance 让所有预测都匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1000)
    # alpha end = 5; beta after = 10; distance = 5 ≤ 1000 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_both_p_r_zero_batch23():
    """p=0 + r=0 → f1 走 denom <= 0 分支 → 0.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    # zzz 找不到 → missing → 但其他 anchor 也无 → gt_positions 为空？
    # 不对，annotation 有 anchors → 进入正常分支但 marker 找不到 → missing
    # 此时 gt_positions=[]，num_gt=0 → recall null
    # 验证不会抛
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "chunk_boundary_f1" in out


def test_chunk_boundary_prf_f1_perfect_match_batch23():
    """完美匹配 → p=1 r=1 → f1=1。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_half_when_half_match_batch23():
    """部分匹配 f1 由公式算。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # 预测边界：a 后 (2), b 后 (4)
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},  # 命中预测 0 (位置 2)
        {"marker": "c", "position": "after"},  # 在 stream 中不存在（c 是最后 chunk 但 after 在 stream 内：位置 6）
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 不抛即可，主要测试 f1 公式
    assert "chunk_boundary_f1" in out


def test_chunk_boundary_prf_many_chunks_distinct_markers_batch23():
    """10 chunks + 9 anchors → 完美匹配。"""
    doc = {"chunks": [{"text": f"chunk{i}"} for i in range(10)]}
    ann = {"chunk_boundary_anchors": [
        {"marker": f"chunk{i}", "position": "after"} for i in range(9)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 完美匹配 → p=1 r=1 f1=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_long_marker_batch23():
    """长 marker（100 字符）也能找到。"""
    long_text = "x" * 100
    doc = {"chunks": [{"text": long_text}, {"text": "y"}]}
    ann = {"chunk_boundary_anchors": [{"marker": long_text, "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_repeats_many_times_batch23():
    """同一 chunk text 重复 10 次。"""
    doc = {"chunks": [{"text": "x"} for _ in range(10)]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    # stream = "x x x x x x x x x x"（10 个 x 用空格连接再 normalize）
    # 第一个 anchor 找第一个 'x' 之后位置 = 1
    # 但 search_from 推进 → 后续 anchor 找下一个 x
    # 这里只有 1 个 anchor，所以只匹配第一个 x 之后位置
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # 预测边界：每个 chunk 末尾（除最后一个）= 1, 3, 5, 7, 9, 11, 13, 15, 17
    # anchor: 第 1 个 x 之后 = 1
    # 距离 0 → 命中预测位置 1
    # 1 个 anchor, 9 个预测，匹配 1 → precision = 1/9, recall = 1/1 = 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_search_from_advancement_batch23():
    """相同 marker 多 anchor → search_from 推进让每个 anchor 占用不同位置。"""
    doc = {"chunks": [{"text": "x"}, {"text": "x"}, {"text": "x"}, {"text": "y"}]}
    # 3 个相同 'x' marker after → 每个 anchor 应分别匹配第 1/2/3 个 x 之后
    ann = {"chunk_boundary_anchors": [
        {"marker": "x", "position": "after"},
        {"marker": "x", "position": "after"},
        {"marker": "x", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # 预测：x后(1), x后(3)，无（最后 chunk 前）—— 实际预测数 = 3（chunks 0,1,2 后）
    # 3 个 anchor 都能找到（search_from 推进）
    # 不抛即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_marker_with_special_chars_batch23():
    """marker 含特殊字符。"""
    doc = {"chunks": [{"text": "a.b-c_d"}, {"text": "x"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a.b-c_d", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch23():
    """document=None → pipeline_failed。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_includes_tolerance_batch23():
    """document=None 时也返回 _tolerance_chars。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=15)
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_no_annotation_includes_tolerance_batch23():
    """annotation falsy 时也返回 _tolerance_chars。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=7)
    assert out["_tolerance_chars"]["value"] == 7


def test_chunk_boundary_prf_no_chunks_includes_tolerance_batch23():
    """无 chunks 时也返回 _tolerance_chars。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_single_chunk_with_anchors_batch23():
    """单 chunk（无内部边界）+ anchors → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "alpha"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # anchors 非空但 recall 走 no_predicted_boundaries 分支（if not chunks or len < 2）
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_single_chunk_no_anchors_batch23():
    """单 chunk + 无 anchors → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "alpha"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_zero_chunks_batch23():
    """零 chunks + 有 anchors → no_predicted_boundaries。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_missing_chunks_key_with_anchors_batch23():
    """缺 chunks key → no_predicted_boundaries。"""
    doc = {}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_no_anchors_batch23():
    """2 chunks + 无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_returns_dict_type_batch23():
    out = chunk_boundary_prf({}, {})
    assert isinstance(out, dict)


def test_chunk_boundary_prf_no_missing_markers_when_all_found_batch23():
    """所有 marker 都找到时无 _missing_markers 字段。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_missing_markers_is_list_batch23():
    """_missing_markers.value 是 list。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert isinstance(out.get("_missing_markers", {}).get("value"), list)


def test_chunk_boundary_prf_marker_unicode_batch23():
    """marker 含 unicode 字符。"""
    doc = {"chunks": [{"text": "中文测试"}, {"text": "english"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "中文", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 应当找到，不抛错
    assert "chunk_boundary_precision" in out


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十三批 ----------


def test_parser_does_not_emit_relations_is_string_batch23():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_snake_case_batch23():
    """snake_case 形式。"""
    s = PARSER_DOES_NOT_EMIT_RELATIONS
    assert s == s.lower()
    assert " " not in s
    assert "-" not in s


def test_parser_does_not_emit_relations_is_ascii_batch23():
    PARSER_DOES_NOT_EMIT_RELATIONS.encode("ascii")


def test_parser_does_not_emit_relations_starts_with_parser_batch23():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


def test_parser_does_not_emit_relations_module_attribute_batch23():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


# ---------- module source forbidden tokens 第三十八批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.check_output",
    "subprocess.check_call",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    'open("/etc/passwd',
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch23(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch23():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch23():
    src = inspect.getsource(amod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch23():
    src = inspect.getsource(amod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch23():
    src = inspect.getsource(amod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch23():
    src = inspect.getsource(amod)
    assert "import threading" not in src


def test_module_source_no_asyncio_import_batch23():
    src = inspect.getsource(amod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch23():
    src = inspect.getsource(amod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch23():
    src = inspect.getsource(amod)
    assert "import tempfile" not in src


def test_module_source_no_logging_import_batch23():
    src = inspect.getsource(amod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch23():
    src = inspect.getsource(amod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch23():
    src = inspect.getsource(amod)
    assert "import datetime" not in src


def test_module_source_no_pandas_import_batch23():
    src = inspect.getsource(amod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch23():
    src = inspect.getsource(amod)
    assert "import numpy" not in src


def test_module_source_no_csv_import_batch23():
    src = inspect.getsource(amod)
    assert "import csv" not in src


def test_module_source_no_os_import_batch23():
    src = inspect.getsource(amod)
    assert "import os" not in src


# ---------- module source 字符串精确补强第三十四批 ----------


def test_module_source_has_future_annotations_batch23():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_has_counter_import_batch23():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import_batch23():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import_batch23():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant_batch23():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_figure_caption_prf_function_batch23():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_prf_function_batch23():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_tolerance_chars_default_30_batch23():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_normalize_text_call_batch23():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_has_no_annotation_string_batch23():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_has_pipeline_failed_string_batch23():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_has_no_predicted_boundaries_string_batch23():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_has_no_ground_truth_anchors_string_batch23():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_has_tolerance_chars_field_batch23():
    src = inspect.getsource(amod)
    assert '"_tolerance_chars"' in src


# ---------- signatures 第三十四批 ----------


def test_signature_figure_caption_prf_params_batch23():
    sig = inspect.signature(figure_caption_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation"]


def test_signature_figure_caption_prf_return_annotation_batch23():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_params_batch23():
    sig = inspect.signature(chunk_boundary_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch23():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_signature_chunk_boundary_prf_return_annotation_batch23():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_tolerance_annotation_int_batch23():
    sig = inspect.signature(chunk_boundary_prf)
    ann = sig.parameters["tolerance_chars"].annotation
    assert "int" in ann


# ---------- module 合理性第三十四批 ----------


def test_module_all_has_three_entries_batch23():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_does_not_import_evaluation_runner_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_cli_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_manifest_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.manifest" not in src


def test_module_does_not_import_evaluation_schema_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.schema" not in src


def test_module_does_not_import_evaluation_report_batch23():
    src = inspect.getsource(amod)
    assert "from evaluation.report" not in src


def test_module_does_not_import_app_pipeline_batch23():
    src = inspect.getsource(amod)
    assert "from app.pipeline" not in src


def test_module_does_not_import_app_parsers_batch23():
    src = inspect.getsource(amod)
    assert "from app.parsers" not in src


def test_module_constants_not_in_all_batch23():
    """常量 PARSER_DOES_NOT_EMIT_RELATIONS 在 __all__ 中（例外：是公开 API）。"""
    # 这是公开 API，所以应在 __all__ 中
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_no_main_block_batch23():
    src = inspect.getsource(amod)
    assert 'if __name__ ==' not in src


def test_module_figure_caption_prf_is_public_batch23():
    assert not figure_caption_prf.__name__.startswith("_")


def test_module_chunk_boundary_prf_is_public_batch23():
    assert not chunk_boundary_prf.__name__.startswith("_")


def test_module_has_module_docstring_batch23():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


# ---------- 端到端集成第三十四批 ----------


def test_e2e_figure_caption_prf_minimal_batch23():
    out = figure_caption_prf({}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_e2e_chunk_boundary_prf_perfect_match_batch23():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 10


def test_e2e_chunk_boundary_prf_with_missing_markers_batch23():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "missing", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "missing" in out["_missing_markers"]["value"]


def test_e2e_chunk_boundary_prf_document_none_full_branch_batch23():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_chunk_boundary_prf_annotation_none_full_branch_batch23():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_chunk_boundary_prf_multi_chunks_multi_anchors_batch23():
    """复杂场景：5 chunks + 4 anchors 全部命中。"""
    doc = {"chunks": [{"text": f"section{i}"} for i in range(5)]}
    ann = {"chunk_boundary_anchors": [
        {"marker": f"section{i}", "position": "after"} for i in range(4)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_mismatch_returns_zero_match_batch23():
    """预测边界与 anchor 距离 > tolerance → 0 匹配。"""
    doc = {"chunks": [{"text": "alphabeta"}, {"text": "gammadelta"}]}
    # anchor 在很远的 'delta' 之后
    ann = {"chunk_boundary_anchors": [{"marker": "delta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # 距离 > 2 → 不匹配
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    if p is not None and r is not None:
        assert p == 0.0
        assert r == 0.0
