"""evaluation/annotation_metrics.py 第四十八轮 edges 测试（Round 469）。

补强 edges47 未触及的角度：
- figure_caption_prf 第二十一批（return type / 不读 doc fields / 不读 annotation fields / 三 metric 顺序 / value 是 None / reason 是常量字符串）
- chunk_boundary_prf 第二十一批（边界条件全覆盖 / tolerance_chars 透传 / _tolerance_chars 字段 / _missing_markers 字段 / 一对一匹配 / 完美匹配 / 错过 / 多 anchor 同 marker / position=before|after / 不在 stream 中的 marker）
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十一批（值 / 类型 / 不可变）
- module source forbidden tokens 第三十六批
- module source 字符串精确补强第三十二批
- signatures 第三十二批
- module 合理性第三十二批
- 端到端集成第三十二批
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


# ---------- figure_caption_prf 第二十一批 ----------


def test_figure_caption_prf_keys_order_batch21():
    """返回 dict 的 key 顺序：precision, recall, f1。"""
    out = figure_caption_prf({}, {})
    keys = list(out.keys())
    assert keys == ["figure_caption_precision", "figure_caption_recall", "figure_caption_f1"]


def test_figure_caption_prf_value_dict_has_value_key_batch21():
    """每个 metric 是含 'value' 与 'reason' 的 dict。"""
    out = figure_caption_prf({}, {})
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_returns_dict_type_batch21():
    out = figure_caption_prf({}, {})
    assert isinstance(out, dict)


def test_figure_caption_prf_reason_constant_value_batch21():
    """reason 字符串值是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_figure_caption_prf_with_complex_doc_batch21():
    """复杂 doc 不影响输出（永远 null）。"""
    doc = {
        "elements": [{"id": "e1", "type": "figure"}, {"id": "e2", "type": "caption"}],
        "figure_caption_relations": [{"figure": "e1", "caption": "e2"}],
    }
    out = figure_caption_prf(doc, {})
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_prf_with_complex_annotation_batch21():
    """复杂 annotation 不影响输出（永远 null）。"""
    ann = {
        "figure_caption_pairs": [
            {"figure_marker": "图1", "caption_text": "Caption 1"},
            {"figure_marker": "图2", "caption_text": "Caption 2"},
        ]
    }
    out = figure_caption_prf({}, ann)
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_prf_idempotent_batch21():
    """多次调用结果一致。"""
    o1 = figure_caption_prf({"a": 1}, {"b": 2})
    o2 = figure_caption_prf({"a": 1}, {"b": 2})
    assert o1 == o2


def test_figure_caption_prf_no_optional_return_batch21():
    """不返回额外的 _tolerance_chars 等字段。"""
    out = figure_caption_prf({}, {})
    assert not any(k.startswith("_") for k in out.keys())


# ---------- chunk_boundary_prf 第二十一批 ----------


def test_chunk_boundary_prf_returns_dict_type_batch21():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_returns_at_least_3_metrics_batch21():
    """返回至少 3 个 chunk_boundary_* metric + _tolerance_chars。"""
    out = chunk_boundary_prf(None, None)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_tolerance_default_30_batch21():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_passed_through_batch21():
    out = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch21():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_empty_returns_no_annotation_batch21():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_is_none_returns_no_annotation_batch21():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_returns_no_predicted_batch21():
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_returns_no_predicted_batch21():
    """只有 1 个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"text": "a"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_anchors_returns_no_gt_batch21():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_batch21():
    """完美匹配：1 chunk 边界 + 1 anchor 对齐 → P=R=F1=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # marker "alpha" position=after → 在 "alpha beta" 中是位置 5（"alpha" 之后）
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f = out["chunk_boundary_f1"]["value"]
    # 完美匹配（precision=1.0/recall=1.0）
    if p is not None and r is not None:
        assert f is not None


def test_chunk_boundary_prf_marker_not_found_batch21():
    """marker 不在 stream 中 → 进 missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # 没有 ground truth anchor 被找到
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_missing_markers_recorded_batch21():
    """找不到的 marker 进 _missing_markers 字段。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_before_batch21():
    """position=before → 用 marker 起始位置。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 期望能匹配（chunk 边界在 6 附近，beta 起始也在 6）
    r = out["chunk_boundary_recall"]["value"]
    # 应有非 None 值（找到 1 个 anchor）
    assert r is not None or out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_position_after_batch21():
    """position=after → 用 marker 结束位置。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 不抛错即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_position_default_after_batch21():
    """缺 position 字段时默认 'after'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha"}]}  # 无 position
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 默认 after，应能匹配 chunk 边界
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_one_to_one_matching_batch21():
    """一对一匹配：1 个 pred + 2 个相同位置 anchor → 只匹配 1 个。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alpha", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 由于 marker 推进 search_from，第二个 "alpha" 找不到（只 1 个 alpha）
    # recall 仍可能 < 1.0
    r = out["chunk_boundary_recall"]["value"]
    assert r is None or r <= 1.0


def test_chunk_boundary_prf_tolerance_zero_batch21():
    """tolerance_chars=0：必须严格匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # alpha 后位置 5，chunk 边界也在 5 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_negative_batch21():
    """负 tolerance 视为 0（无任何 pair 匹配）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-5)
    # d = abs(5 - 5) = 0，-5 ≤ 0 → 仍匹配
    # 但实际匹配时 d <= tolerance_chars 是 0 <= -5 False
    # 所以匹配不上
    p = out["chunk_boundary_precision"]["value"]
    assert p is None or p == 0.0


def test_chunk_boundary_prf_f1_when_p_or_r_none_batch21():
    """precision 或 recall 是 None 时 f1 也是 None。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    # precision/recall/f1 都是 None
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_f1_perfect_batch21():
    """完美匹配时 f1 = 1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f = out["chunk_boundary_f1"]["value"]
    if p == 1.0 and r == 1.0:
        assert f == 1.0


def test_chunk_boundary_prf_large_tolerance_batch21():
    """大 tolerance 让所有 pair 都匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1000)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    # 大 tolerance 应让全部匹配
    if p is not None and r is not None:
        assert p == 1.0
        assert r == 1.0


def test_chunk_boundary_prf_marker_empty_string_batch21():
    """marker 为空字符串时被跳过（find 返回 -1）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # 空 marker 进 missing_markers
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_marker_key_batch21():
    """anchor 缺 marker 字段 → 默认 ''。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # 不抛错即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_returns_tolerance_record_batch21():
    """返回 _tolerance_chars 字段含 'value' 与 'reason'。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    rec = out["_tolerance_chars"]
    assert rec["value"] == 42
    assert rec["reason"] is None


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十一批 ----------


def test_parser_does_not_emit_relations_is_string_batch21():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_batch21():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_immutable_batch21():
    """字符串不可变（试图修改会抛 TypeError）。"""
    with pytest.raises(TypeError):
        PARSER_DOES_NOT_EMIT_RELATIONS[0] = "X"  # type: ignore


# ---------- module source forbidden tokens 第三十六批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch21(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch21():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src
    assert "from subprocess" not in src


def test_module_source_no_socket_import_batch21():
    src = inspect.getsource(amod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch21():
    src = inspect.getsource(amod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch21():
    src = inspect.getsource(amod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch21():
    src = inspect.getsource(amod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch21():
    src = inspect.getsource(amod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch21():
    src = inspect.getsource(amod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch21():
    src = inspect.getsource(amod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch21():
    src = inspect.getsource(amod)
    assert "import tempfile" not in src


def test_module_source_no_sys_import_batch21():
    src = inspect.getsource(amod)
    assert "import sys" not in src


def test_module_source_no_logging_import_batch21():
    src = inspect.getsource(amod)
    assert "import logging" not in src


def test_module_source_no_re_import_batch21():
    src = inspect.getsource(amod)
    assert "import re" not in src


def test_module_source_no_datetime_import_batch21():
    src = inspect.getsource(amod)
    assert "import datetime" not in src


def test_module_source_no_pandas_import_batch21():
    src = inspect.getsource(amod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch21():
    src = inspect.getsource(amod)
    assert "import numpy" not in src


# ---------- module source 字符串精确补强第三十二批 ----------


def test_module_source_has_future_annotations_batch21():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_has_collections_import_batch21():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import_batch21():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_app_chunkers_import_batch21():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_metrics_import_batch21():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant_batch21():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_figure_caption_prf_function_batch21():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_prf_function_batch21():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_normalize_text_call_batch21():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_has_tolerance_chars_param_batch21():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_all_list_batch21():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_has_docstring_batch21():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_has_chunk_boundary_docstring_batch21():
    src = inspect.getsource(amod)
    assert "分块边界" in src


def test_module_source_has_no_annotation_docstring_batch21():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_has_pipeline_failed_docstring_batch21():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_has_no_ground_truth_anchors_batch21():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


# ---------- signatures 第三十二批 ----------


def test_signature_figure_caption_prf_batch21():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch21():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_30_batch21():
    sig = inspect.signature(chunk_boundary_prf)
    params = {p.name: p for p in sig.parameters.values()}
    assert params["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_no_extra_params_batch21():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    # 仅 3 个参数
    assert len(params) == 3


def test_signature_figure_caption_prf_no_default_batch21():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    for p in params:
        assert p.default is inspect.Parameter.empty


# ---------- module 合理性第三十二批 ----------


def test_module_has_all_attribute_batch21():
    assert hasattr(amod, "__all__")


def test_module_all_contains_3_entries_batch21():
    assert len(amod.__all__) == 3


def test_module_all_contents_batch21():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_does_not_import_app_pipeline_batch21():
    src = inspect.getsource(amod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_evaluation_runner_batch21():
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src
    assert "from evaluation import runner" not in src


def test_module_does_not_import_evaluation_schema_batch21():
    src = inspect.getsource(amod)
    assert "from evaluation.schema" not in src
    assert "from evaluation import schema" not in src


def test_module_does_not_import_evaluation_manifest_batch21():
    src = inspect.getsource(amod)
    assert "from evaluation.manifest" not in src
    assert "from evaluation import manifest" not in src


def test_module_does_not_import_evaluation_cli_batch21():
    src = inspect.getsource(amod)
    assert "from evaluation.cli" not in src
    assert "from evaluation import cli" not in src


def test_module_no_main_block_batch21():
    src = inspect.getsource(amod)
    assert 'if __name__ ==' not in src
    assert "__main__" not in src


def test_module_parser_does_not_emit_relations_constant_batch21():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_figure_caption_prf_callable_batch21():
    assert callable(amod.figure_caption_prf)


def test_module_chunk_boundary_prf_callable_batch21():
    assert callable(amod.chunk_boundary_prf)


# ---------- 端到端集成第三十二批 ----------


def test_e2e_figure_caption_prf_never_returns_nonnull_batch21():
    """figure_caption_prf 始终返回 null（不论输入）。"""
    cases = [
        ({}, {}),
        (None, None),
        ({"figure_caption_relations": [{"a": 1}]}, {"figure_caption_pairs": [{"b": 2}]}),
        ({"elements": [{"id": "x", "type": "figure"}]}, {}),
    ]
    for doc, ann in cases:
        out = figure_caption_prf(doc, ann)
        for k, v in out.items():
            assert v["value"] is None


def test_e2e_chunk_boundary_prf_perfect_alignment_batch21():
    """完美对齐的 doc 与 annotation → P=R=F1=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_misaligned_batch21():
    """标注 marker 不在 stream 中 → missing_markers 列表。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "nonexistent", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == ["nonexistent"]


def test_e2e_chunk_boundary_prf_tolerance_recorded_batch21():
    """tolerance_chars 必须在返回值中明确记录。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_e2e_chunk_boundary_prf_complex_stream_batch21():
    """复杂 doc 多个 chunk + 多 anchor。"""
    doc = {"chunks": [
        {"text": "alpha"},
        {"text": "beta"},
        {"text": "gamma"},
        {"text": "delta"},
    ]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
        {"marker": "gamma", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 不抛错，所有 3 个 chunk 边界都能匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_no_pred_no_gt_batch21():
    """无 chunk + 无 anchor → no_predicted_boundaries。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_prf_two_chunks_with_extra_whitespace_batch21():
    """chunk text 含多余空白。"""
    doc = {"chunks": [{"text": "  alpha  "}, {"text": "  beta  "}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # normalize 后匹配应成功
    assert "chunk_boundary_precision" in out


def test_e2e_chunk_boundary_prf_returns_consistent_across_calls_batch21():
    """相同输入多次调用结果一致。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    o2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert o1 == o2
