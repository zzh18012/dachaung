"""evaluation/annotation_metrics.py 第六十轮 edges 测试（Round 566）。

补强 edges61 未触及的角度（第三十五批）。
"""

from __future__ import annotations

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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十五批


def test_parser_const_value_exact_batch35():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_const_contains_underscore_batch35():
    assert "_" in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_const_starts_with_parser_batch35():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


def test_parser_const_ends_with_relations_batch35():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.endswith("_relations")


def test_parser_const_in_module_namespace_batch35():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_const_in_all_batch35():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


# ---------- figure_caption_prf 第三十五批


def test_figure_caption_prf_three_keys_only_batch35():
    """figure_caption_prf 永远只返回 3 个 key。"""
    out = figure_caption_prf({"chunks": [{"text": "a"}]}, {"x": 1})
    assert len(out) == 3


def test_figure_caption_prf_keys_order_batch35():
    out = figure_caption_prf(None, None)
    keys = list(out.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_value_structure_batch35():
    """每个 metric 是 dict 含 value + reason。"""
    out = figure_caption_prf({}, {})
    for v in out.values():
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_value_is_none_batch35():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_complex_annotation_batch35():
    """带 figure_caption_anchors 的 annotation（即使有也固定 null）。"""
    ann = {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf({"elements": []}, ann)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_unicode_doc_batch35():
    out = figure_caption_prf({"chunks": [{"text": "中文"}]}, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_idempotent_batch35():
    doc = {"chunks": [{"text": "a"}]}
    ann = {"x": 1}
    o1 = figure_caption_prf(doc, ann)
    o2 = figure_caption_prf(doc, ann)
    assert o1 == o2


def test_figure_caption_prf_ignores_annotation_content_batch35():
    """annotation 不同 → 输出相同。"""
    a1 = figure_caption_prf(None, {"x": 1})
    a2 = figure_caption_prf(None, {"y": 2})
    assert a1 == a2


def test_figure_caption_prf_returns_same_dict_shape_batch35():
    """所有调用返回 dict 形状相同。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        (None, {"figure_caption_anchors": []}),
        ({"chunks": [{"text": "x"}]}, {"x": 1}),
    ]
    shapes = set()
    for doc, ann in inputs:
        out = figure_caption_prf(doc, ann)
        shapes.add(tuple(sorted(out.keys())))
    assert len(shapes) == 1


# ---------- chunk_boundary_prf 第三十五批


def test_chunk_boundary_prf_returns_tolerance_always_batch35():
    """所有路径都返回 _tolerance_chars。"""
    paths = [
        (None, None, 30),
        ({"chunks": []}, None, 5),
        ({"chunks": []}, {"chunk_boundary_anchors": []}, 10),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, None, 99),
    ]
    for doc, ann, tc in paths:
        out = chunk_boundary_prf(doc, ann, tolerance_chars=tc)
        assert "_tolerance_chars" in out
        assert out["_tolerance_chars"]["value"] == tc


def test_chunk_boundary_prf_default_tolerance_30_batch35():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_zero_tolerance_exact_match_batch35():
    """零容差只匹配精确位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    # 边界 pos=3, anchor after c → pos=3, 距离 0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_zero_tolerance_no_match_batch35():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "b", "position": "after"}]}
    # 边界 pos=3, anchor after b → pos=2, 距离 1 > 0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_large_tolerance_batch35():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    # 边界 pos=3, anchor before a → pos=0, 距离 3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1000)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_multi_chunk_multi_anchor_batch35():
    """3 chunks → 2 边界；2 anchors 完美匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # pos=3
        {"marker": "f", "position": "after"},  # pos=7
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 边界：chunk 0 末尾=3, chunk 1 末尾=7
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_p_zero_batch35():
    """precision=0 → f1=0（denom=0+r > 0 时仍为 0）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    # 距离 3, 容差 0 → 0 match
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # p + r = 0 → f1 = 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_normal_value_batch35():
    """完美匹配 f1=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_half_value_batch35():
    """P=0.5, R=1.0 → f1=2*0.5*1/(0.5+1)=1/1.5≈0.6667。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 2 predictions, 1 anchor → matched=1, P=0.5, R=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    f1 = out["chunk_boundary_f1"]["value"]
    assert f1 is not None
    assert abs(f1 - 2 * 0.5 * 1.0 / (0.5 + 1.0)) < 1e-9


def test_chunk_boundary_prf_missing_marker_added_to_output_batch35():
    """marker 在 stream 中找不到 → _missing_markers key 加入输出。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "xyz", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_partial_missing_markers_batch35():
    """部分 marker 找到，部分找不到 → 只 missing 的进列表。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "xyz", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_no_missing_markers_no_key_batch35():
    """无 missing → 不添加 _missing_markers key。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_anchor_position_after_default_batch35():
    """position 字段缺失 → 默认 after。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 默认 after → pos=3 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_two_anchors_same_marker_batch35():
    """两个 anchor 用相同 marker → 第二个找不到（search_from 推进过）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "c", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 第二个 c 找不到 → missing（不计入 num_gt）
    assert "_missing_markers" in out
    # 1 anchor matched, 1 prediction, 1 gt → P=1.0, R=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_doc_none_returns_pipeline_failed_batch35():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_none_returns_no_annotation_batch35():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_returns_dict_type_batch35():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunks_missing_key_batch35():
    """doc 没有 chunks key → 当 []。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": []})
    # 0 chunks → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_missing_anchors_key_batch35():
    """annotation 没有 chunk_boundary_anchors → 当 []。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"other_key": "x"},
    )
    # 0 anchors → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_unicode_chunks_batch35():
    doc = {"chunks": [{"text": "你好世界"}, {"text": "测试数据"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "界", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # '界' 后是空格，stream="你好世界 测试数据"
    # 边界在 pos=4（'界' 后），'界' 在 pos=2, after → pos=3? Wait:
    # stream[0:4] = "你好世界"
    # '界' 是 stream[3], after → pos=4
    # 边界 pos=4, 距离 0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_long_marker_batch35():
    """marker 是多字符子串。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "hello world foo bar"
    # 'world' 起始 pos=6, after → pos=11
    # 边界 pos=11 (chunk 0 末尾)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_does_not_mutate_doc_batch35():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_chunk_boundary_prf_idempotent_batch35():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    o2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert o1 == o2


# ---------- module source forbidden tokens 第五十三批


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
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch35():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_future_annotations_batch35():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_counter_import_batch35():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_normalize_text_import_batch35():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_metrics_import_batch35():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_parser_const_definition_batch35():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_func_batch35():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_func_batch35():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_pipeline_failed_reason_batch35():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_annotation_reason_batch35():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_contains_no_predicted_boundaries_reason_batch35():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_contains_no_ground_truth_anchors_reason_batch35():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason_batch35():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_module_source_contains_precision_or_recall_not_evaluated_reason_batch35():
    src = inspect.getsource(amod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_module_source_contains_tolerance_chars_param_batch35():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_greedy_match_comment_batch35():
    """源码注释含"贪心"或"greedy"。"""
    src = inspect.getsource(amod)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_contains_all_with_three_entries_batch35():
    assert len(amod.__all__) == 3


def test_module_source_all_contains_parser_const_batch35():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src


def test_module_source_all_contains_figure_caption_batch35():
    src = inspect.getsource(amod)
    assert '"figure_caption_prf"' in src


def test_module_source_all_contains_chunk_boundary_batch35():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_prf"' in src


# ---------- signatures 第四十九批


def test_signature_figure_caption_prf_params_batch35():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_signature_figure_caption_prf_return_annotation_batch35():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_params_batch35():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch35():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_return_annotation_batch35():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性第四十九批


def test_module_imports_counter_batch35():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_normalize_text_batch35():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_and_ratio_batch35():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_has_figure_caption_prf_func_batch35():
    assert callable(amod.figure_caption_prf)


def test_module_has_chunk_boundary_prf_func_batch35():
    assert callable(amod.chunk_boundary_prf)


def test_module_all_length_3_batch35():
    assert len(amod.__all__) == 3


# ---------- 端到端集成第四十九批


def test_e2e_chunk_boundary_full_match_batch35():
    """完整流程：3 chunks + 2 anchors 完美匹配 P=R=F1=1.0。"""
    doc = {
        "chunks": [
            {"text": "first paragraph"},
            {"text": "second paragraph"},
            {"text": "third paragraph"},
        ],
    }
    ann = {"chunk_boundary_anchors": [
        {"marker": "first paragraph", "position": "after"},
        {"marker": "second paragraph", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_with_tolerance_flexible_batch35():
    """容差 5 → 部分错位 anchor 仍能匹配。"""
    doc = {"chunks": [{"text": "abcdefgh"}, {"text": "ijklmnop"}]}
    # 边界 pos=8
    ann = {"chunk_boundary_anchors": [{"marker": "f", "position": "after"}]}
    # 'f' 在 pos=5, after → pos=6, 距离 |8-6|=2 ≤ 5
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_no_chunks_no_anchors_batch35():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    # 0 chunks → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_idempotent_results_batch35():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    o2 = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert o1 == o2
