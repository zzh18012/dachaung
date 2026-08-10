"""evaluation/annotation_metrics.py 第三十八轮 edges 测试（Round 399）。

补强 edges37 未触及的角度：
- figure_caption_prf 行为深度第十一批（dict 类型 / value+reason 结构 / 与 annotation/doc 无关 / idempotent / key order）
- chunk_boundary_prf 行为深度第十一批（更多 branch：marker 缺失 / Unicode marker / position 边界 / tolerance 负数 / chunk text 缺失 / 多 chunk 多 anchor / _missing_markers 触发 / 默认 vs 自定义 tolerance）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第九批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import inspect
import json
import os
from typing import Any

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 行为深度第十一批 ----------


def test_figure_caption_prf_returns_dict_strict_batch11():
    out = figure_caption_prf(None, None)
    assert type(out) is dict


def test_figure_caption_prf_each_value_is_dict_batch11():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert isinstance(v, dict), f"{k} -> {type(v)}"


def test_figure_caption_prf_each_value_has_value_and_reason_batch11():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_idempotent_batch11():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_with_complex_doc_still_null_batch11():
    """复杂 document 仍然 null（caption relation 是 null）。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "img1", "source_locator": {"page": 1}},
            {"type": "caption", "element_id": "cap1", "content": "Figure 1"},
        ],
        "chunks": [],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_complex_annotation_still_null_batch11():
    annot = {
        "figure_caption_pairs": [["img1", "cap1"], ["img2", "cap2"]],
        "chunk_boundary_anchors": [],
    }
    out = figure_caption_prf(None, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_is_str_batch11():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert isinstance(v["reason"], str)


def test_figure_caption_prf_value_is_none_strict_batch11():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_dict_does_not_share_state_batch11():
    """两次调用返回独立 dict。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    out1["new_key"] = "x"
    assert "new_key" not in out2


def test_figure_caption_prf_returns_3_entries_batch11():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_prf_reason_constant_str_value_batch11():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)
    assert "relation" in PARSER_DOES_NOT_EMIT_RELATIONS.lower()


# ---------- chunk_boundary_prf 行为深度第十一批 ----------


def test_chunk_boundary_prf_document_none_annotation_some_batch11():
    """document None 时，即使有 annotation 也走 pipeline_failed。"""
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(None, annot)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_with_chunks_annotation_none_batch11():
    """document 有 chunks 但 annotation=None → no_annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_with_chunks_annotation_empty_batch11():
    """document 有 chunks 但 annotation={} → no_annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_missing_chunks_batch11():
    """document 缺 chunks 字段 → chunks=[] → no_predicted_boundaries。"""
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf({}, annot)
    # 没 chunks → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 有 anchor 但没 chunk → recall = 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_document_one_chunk_batch11():
    """1 个 chunk → 没有内部边界 → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "abc"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_zero_anchors_batch11():
    """2 chunks + 0 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_batch11():
    """2 chunks + 1 anchor 完美对齐 → P=R=F1=1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"
    # predicted end of chunk 0 = 5
    # anchor "hello" position "after" → 5
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_within_tolerance_batch11():
    """距离 < tolerance → match。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # predicted = 5
    # anchor "hel" position "after" → 3 (距离 2)
    annot = {"chunk_boundary_anchors": [{"marker": "hel", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_outside_tolerance_batch11():
    """距离 > tolerance → no match。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # predicted = 5
    # anchor "h" position "after" → 1 (距离 4)
    annot = {"chunk_boundary_anchors": [{"marker": "h", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=2)
    # 1 predicted, 0 matched → precision 0/1 = 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    # 1 anchor, 0 matched → recall 0/1 = 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_position_before_batch11():
    """position="before" → marker 起始位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    # stream = "abc xyz"
    # predicted = 3 (end of chunk 0)
    # anchor "xyz" position "before" → 4 (距离 1)
    annot = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_value_treats_as_after_batch11():
    """position 是未知字符串 → 走 else (after) 分支。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "totally_unknown"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # unknown → else → after → marker 末尾 = 3 (距离 0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_missing_marker_key_batch11():
    """anchor 缺 marker 字段 → marker="" → find 返回 -1 → missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    # 空 marker → find 返回 -1 → 加入 missing_markers → 0 gt_positions → recall no_ground_truth_anchors_in_stream
    assert "_missing_markers" in out
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_marker_not_in_stream_batch11():
    """marker 不在 stream 里 → missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "qwerty", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    assert "_missing_markers" in out
    # 0 gt_positions → recall no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_unicode_marker_batch11():
    """Unicode marker 在 stream 里。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_none_batch11():
    """chunk text 是 None → normalize_text(None or "") → normalize_text("")"""
    doc = {"chunks": [{"text": None}, {"text": "abc"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    # 不抛异常即可
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunk_missing_text_key_batch11():
    """chunk 缺 text 字段 → c.get("text") None → "" → normalize ""。"""
    doc = {"chunks": [{}, {"text": "abc"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_tolerance_negative_batch11():
    """tolerance 是负数 → abs 距离 ≤ 负数 永远 False → 0 match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=-1)
    # 距离 0 ≤ -1 False → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_returns_tolerance_record_batch11():
    """结果包含 _tolerance_chars 记录。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_default_tolerance_30_batch11():
    """默认 tolerance_chars=30。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_no_missing_markers_key_when_all_match_batch11():
    """所有 marker 都找到 → 不写 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_returns_dict_strict_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert type(out) is dict


def test_chunk_boundary_prf_f1_formula_batch11():
    """f1 = 2PR / (P+R)。"""
    # 2 chunks, 2 anchors，1 个 match，1 个不 match
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    # stream = "aaa bbb"
    # predicted = 3 (end of chunk 0)
    # anchor 1: "aaa" position "after" → 3 (距离 0, match with tol=0)
    # anchor 2: "x" position "after" → -1, missing
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},
            {"marker": "bbb", "position": "after"},  # bbb end = 7, 距离 4 > 0
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # matched = 1, predicted = 1, gt = 1 (only "aaa" matched; "bbb" found but distance 4 > 0)
    # Wait - "bbb" is found, so it's in gt_positions. matched=1, gt=2.
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    # f1 = 2*1.0*0.5 / (1.0+0.5) = 1.0/1.5 = 0.6667
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3, abs=1e-3)


def test_chunk_boundary_prf_no_mutation_doc_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    snapshot = json.dumps(doc, sort_keys=True)
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    _ = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert json.dumps(doc, sort_keys=True) == snapshot


def test_chunk_boundary_prf_no_mutation_annotation_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    snapshot = json.dumps(annot, sort_keys=True)
    _ = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert json.dumps(annot, sort_keys=True) == snapshot


def test_chunk_boundary_prf_idempotent_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out1 == out2


def test_chunk_boundary_prf_three_chunks_two_internal_boundaries_batch11():
    """3 chunks → 2 个内部边界。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    # stream = "aaa bbb ccc"
    # predicted = [3, 7]
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # 3
            {"marker": "bbb", "position": "after"},  # 7
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_markers_sequential_match_batch11():
    """两个相同 marker 应顺序匹配（不都命中第 1 个）。"""
    doc = {"chunks": [{"text": "aa"}, {"text": "x aa"}, {"text": "y"}]}
    # norm_chunks = ["aa", "x aa", "y"]
    # joined = "aa x aa y"
    # stream = "aa x aa y"
    # predicted = [2, 7] (end of chunk 0 and chunk 1)
    # anchor 1: "aa" position "after" → 第 1 个 "aa" 末尾 = 2
    # anchor 2: "aa" position "after" → 从位置 2 之后找 "aa" → 位置 5 (start) → 末尾 7
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "aa", "position": "after"},
            {"marker": "aa", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # 2 predicted, 2 anchors, both match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_returns_4_keys_basic_batch11():
    """基本场景：返回 4 keys（3 metric + _tolerance_chars）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert len(out) == 4


def test_chunk_boundary_prf_returns_5_keys_with_missing_batch11():
    """有 missing marker 时：返回 5 keys。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "qwerty", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    assert len(out) == 5
    assert "_missing_markers" in out


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(amod)
    assert token not in source


def test_annotation_metrics_source_no_unlink_batch11():
    source = inspect.getsource(amod)
    assert "unlink" not in source


def test_annotation_metrics_source_no_remove_batch11():
    source = inspect.getsource(amod)
    assert ".remove(" not in source


def test_annotation_metrics_source_no_kill_batch11():
    source = inspect.getsource(amod)
    assert ".kill(" not in source


def test_annotation_metrics_source_no_terminate_batch11():
    source = inspect.getsource(amod)
    assert ".terminate(" not in source


def test_annotation_metrics_source_no_async_def_batch11():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_annotation_metrics_source_no_yield_batch11():
    source = inspect.getsource(amod)
    assert "yield" not in source


def test_annotation_metrics_source_no_walrus_batch11():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_annotation_metrics_source_no_top_level_lambda_batch11():
    source = inspect.getsource(amod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_annotation_metrics_source_no_print_batch11():
    source = inspect.getsource(amod)
    assert "print(" not in source


def test_annotation_metrics_source_no_socket_batch11():
    source = inspect.getsource(amod)
    assert "socket" not in source


def test_annotation_metrics_source_no_threading_batch11():
    source = inspect.getsource(amod)
    assert "threading" not in source


def test_annotation_metrics_source_no_multiprocessing_batch11():
    source = inspect.getsource(amod)
    assert "multiprocessing" not in source


def test_annotation_metrics_source_no_asyncio_batch11():
    source = inspect.getsource(amod)
    assert "asyncio" not in source


def test_annotation_metrics_source_no_pickle_module_batch11():
    source = inspect.getsource(amod)
    assert "import pickle" not in source


def test_annotation_metrics_source_no_yaml_module_batch11():
    source = inspect.getsource(amod)
    assert "import yaml" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_counter_batch11():
    source = inspect.getsource(amod)
    assert "from collections import Counter" in source


def test_module_source_imports_typing_any_batch11():
    source = inspect.getsource(amod)
    assert "from typing import Any" in source


def test_module_source_imports_normalize_text_batch11():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_imports_metrics_helpers_batch11():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_has_parser_does_not_emit_constant_batch11():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_has_figure_caption_prf_def_batch11():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_has_chunk_boundary_prf_def_batch11():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_no_main_block_batch11():
    source = inspect.getsource(amod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch11():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


def test_module_source_docstring_mentions_caption_batch11():
    assert amod.__doc__ is not None
    assert "caption" in amod.__doc__.lower() or "图表" in amod.__doc__


def test_module_source_docstring_mentions_boundary_batch11():
    assert amod.__doc__ is not None
    assert "boundary" in amod.__doc__.lower() or "边界" in amod.__doc__


def test_module_source_docstring_mentions_tolerance_batch11():
    assert amod.__doc__ is not None
    assert "tolerance" in amod.__doc__.lower() or "容差" in amod.__doc__


def test_module_source_docstring_no_overall_score_batch11():
    assert amod.__doc__ is not None
    assert "overall_score" not in amod.__doc__


# ---------- signatures 第十一批 ----------


def test_signature_figure_caption_prf_2_params_batch11():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_signature_figure_caption_prf_param_names_batch11():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_signature_figure_caption_prf_param_kinds_batch11():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_no_defaults_batch11():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_chunk_boundary_prf_3_params_batch11():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_signature_chunk_boundary_prf_param_names_batch11():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_param_kinds_batch11():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_default_tolerance_30_batch11():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_first_two_no_defaults_batch11():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty


def test_signature_funcs_function_type_batch11():
    for func in (figure_caption_prf, chunk_boundary_prf):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch11():
    for func in (figure_caption_prf, chunk_boundary_prf):
        assert func.__module__ == "evaluation.annotation_metrics"


# ---------- module 合理性第十一批 ----------


def test_module_all_value_batch11():
    assert amod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list_batch11():
    assert isinstance(amod.__all__, list)


def test_module_all_entries_unique_batch11():
    assert len(amod.__all__) == len(set(amod.__all__))


def test_module_all_entries_str_batch11():
    for name in amod.__all__:
        assert isinstance(name, str)


def test_module_has_dunder_file_batch11():
    assert hasattr(amod, "__file__")
    assert amod.__file__ is not None


def test_module_dunder_file_endswith_annotation_metrics_py_batch11():
    import os
    sep = os.sep
    assert amod.__file__.endswith("evaluation" + sep + "annotation_metrics.py") or amod.__file__.endswith(
        "evaluation/annotation_metrics.py"
    )


def test_module_name_is_evaluation_annotation_metrics_batch11():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_user_function_count_batch11():
    funcs = [
        n for n, v in vars(amod).items()
        if inspect.isfunction(v) and v.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_user_constant_count_batch11():
    consts = [
        n for n, v in vars(amod).items()
        if not n.startswith("__") and isinstance(v, str) and not callable(v)
    ]
    # PARSER_DOES_NOT_EMIT_RELATIONS + annotations (_Feature from __future__)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in consts


def test_module_no_user_classes_batch11():
    classes = [
        n for n, v in vars(amod).items()
        if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch11():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


# ---------- 端到端集成第十一批 ----------


def test_e2e_figure_caption_prf_full_chain_batch11():
    out = figure_caption_prf(None, None)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_chunk_boundary_prf_full_chain_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_chunk_boundary_prf_kwargs_call_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    out2 = chunk_boundary_prf(document=doc, annotation=annot, tolerance_chars=0)
    assert out1 == out2


def test_e2e_combined_call_chain_batch11():
    """组合调用：figure_caption + chunk_boundary。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = figure_caption_prf(doc, annot)
    out2 = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    # keys 不冲突
    assert set(out1.keys()).isdisjoint(set(out2.keys()))


def test_e2e_chunk_boundary_prf_unicode_full_chain_batch11():
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    text = json.dumps(out, ensure_ascii=False)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_chunk_boundary_prf_does_not_raise_on_complex_input_batch11():
    """复杂输入不抛异常。"""
    doc = {
        "chunks": [
            {"text": "long text " * 10, "id": "c1"},
            {"text": "another " * 5, "id": "c2"},
        ]
    }
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "long", "position": "after"},
            {"marker": "text", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=20)
    assert isinstance(out, dict)


def test_e2e_combined_chain_idempotent_batch11():
    """组合链路 idempotent。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = (figure_caption_prf(doc, annot), chunk_boundary_prf(doc, annot, tolerance_chars=10))
    out2 = (figure_caption_prf(doc, annot), chunk_boundary_prf(doc, annot, tolerance_chars=10))
    assert out1 == out2


def test_e2e_chunk_boundary_prf_no_annotation_present_batch11():
    """无 annotation 的 doc，chunk_boundary 返回 no_annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_prf_dict_type_strict_batch11():
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert type(out) is dict


def test_e2e_chunk_boundary_prf_metric_value_dict_strict_batch11():
    """每个 metric 都是 dict[str, Any]。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert type(out[k]) is dict
