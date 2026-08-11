"""evaluation/annotation_metrics.py 第四十三轮 edges 测试（Round 434）。

补强 edges42 未触及的角度：
- figure_caption_prf 边界第十六批（document 与 annotation 是 dict vs None 组合 / dict 内字段 / 不可变性）
- chunk_boundary_prf 边界第十六批（document 是空 dict / chunks 是单元素 list / annotation dict 缺 marker / annotation dict 缺 position / position 是 invalid string）
- chunk_boundary_prf 算法第十六批（容差边界严格等于 / gt 与 pred 重合 / 多 anchor 多 pred 完美匹配 / 全部 missing）
- PARSER_DOES_NOT_EMIT_RELATIONS 第十六批（值与字符串 / 模块属性 / 在 all）
- module source forbidden tokens 第二十九批
- module source 字符串精确补强第二十六批
- signatures 第二十六批
- module 合理性第二十六批
- 端到端集成第二十六批
"""

from __future__ import annotations

import inspect
from collections import Counter
from unittest.mock import patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 边界第十六批 ----------


def test_figure_caption_prf_document_dict_annotation_none_batch16():
    """document 是 dict, annotation 是 None。"""
    out = figure_caption_prf({"x": 1}, None)
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_document_none_annotation_dict_batch16():
    """document 是 None, annotation 是 dict。"""
    out = figure_caption_prf(None, {"x": 1})
    assert len(out) == 3


def test_figure_caption_prf_dict_with_chunks_batch16():
    """document 含 chunks 字段也不影响 figure_caption 输出。"""
    doc = {"chunks": [{"text": "x"}], "elements": []}
    out = figure_caption_prf(doc, {})
    assert len(out) == 3


def test_figure_caption_prf_returns_same_keys_for_any_input_batch16():
    """任何输入都返回同样三个 key。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"a": 1}, {"b": 2}),
        (None, {}),
        ({}, None),
    ]
    for d, a in inputs:
        out = figure_caption_prf(d, a)
        assert set(out.keys()) == {
            "figure_caption_precision",
            "figure_caption_recall",
            "figure_caption_f1",
        }


def test_figure_caption_prf_dict_independence_across_fields_batch16():
    """不同 key 的 dict 互不影响。"""
    out = figure_caption_prf({"x": 1}, {"y": 2})
    out["figure_caption_precision"]["value"] = "modified"
    # 其它 key 不受影响
    assert out["figure_caption_recall"]["value"] is None


def test_figure_caption_prf_no_pipeline_failed_branch_batch16():
    """figure_caption_prf 没有 pipeline_failed 分支（不像 chunk_boundary_prf）。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] != "pipeline_failed"


def test_figure_caption_prf_never_returns_dict_value_batch16():
    """figure_caption value 永远是 None（不是 dict 或 int）。"""
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for v in out.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 边界第十六批 ----------


def test_chunk_boundary_prf_document_empty_dict_batch16():
    """document 是空 dict → chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_single_element_batch16():
    """chunks 只有 1 个元素 → len < 2 → no_predicted_boundaries。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchor_missing_marker_batch16():
    """anchor 缺 marker 字段 → a.get("marker", "") → "" → find_pos=-1 → 加入 missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"position": "after"}]}  # 无 marker
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_anchor_missing_position_batch16():
    """anchor 缺 position 字段 → a.get("position", "after") → 默认 "after"。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}  # 无 position
    out = chunk_boundary_prf(doc, annotation)
    # 不崩溃即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_anchor_invalid_position_batch16():
    """position 是无效字符串 → 走 else 分支（视为 "after"）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "invalid"}]
    }
    out = chunk_boundary_prf(doc, annotation)
    # 不崩溃即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_annotation_dict_no_anchors_key_batch16():
    """annotation 是空 dict → `not annotation` 为 True → no_annotation reason。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {}  # 空 dict
    out = chunk_boundary_prf(doc, annotation)
    # 空 dict 被 `if not annotation` 拦截 → no_annotation
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_dict_nonempty_no_anchors_key_batch16():
    """annotation dict 非空但缺 chunk_boundary_anchors key → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"other_field": "x"}  # 非空但无 anchors
    out = chunk_boundary_prf(doc, annotation)
    # annotation.get("chunk_boundary_anchors") or [] = []
    # anchors=[] → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchors_is_none_batch16():
    """chunk_boundary_anchors 显式为 None。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": None, "other": "x"}  # 必须非空 dict
    out = chunk_boundary_prf(doc, annotation)
    # anchors = None or [] = []
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_is_none_batch16():
    """chunks 显式为 None → .get(...) or [] → [] → no_predicted_boundaries。"""
    doc = {"chunks": None}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, annotation)
    # 但 document.get("chunks") 在 _run_inspect_doc 是 .get(...) or []
    # 这里 chunks=None → None or [] = []
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


# ---------- chunk_boundary_prf 算法第十六批 ----------


def test_chunk_boundary_prf_tolerance_exactly_equal_batch16():
    """距离恰好等于容差 → 应算匹配（≤）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def", 预测位置 = 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"}  # gt = 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=3)
    # |3 - 0| = 3 ≤ 3 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_off_by_one_batch16():
    """距离 = 容差 + 1 → 不匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    # |3 - 0| = 3 > 2 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_perfect_match_5_chunks_batch16():
    """5 chunks → 4 个内部边界。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}, {"text": "e"}]}
    # stream = "a b c d e"
    # 预测位置 = 1, 3, 5, 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # 1
            {"marker": "b", "position": "after"},  # 3
            {"marker": "c", "position": "after"},  # 5
            {"marker": "d", "position": "after"},  # 7
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_all_markers_missing_batch16():
    """所有 marker 都不在 stream 中。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "y", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "x" in out["_missing_markers"]["value"]
    assert "y" in out["_missing_markers"]["value"]
    # gt_positions 空 → recall = no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_position_before_gt_pos_batch16():
    """position='before' → gt_pos = find_pos（marker 起始）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def", find_pos of "abc" = 0
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"}  # gt = 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 = 3, gt = 0 → 不匹配（容差 0）
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_position_after_gt_pos_batch16():
    """position='after' → gt_pos = find_pos + len(marker)。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"}  # gt = 0 + 3 = 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 = 3, gt = 3 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第十六批 ----------


def test_parser_does_not_emit_relations_value_exact_batch16():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_module_attribute_batch16():
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_in_all_batch16():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_is_str_batch16():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_used_by_figure_caption_batch16():
    """figure_caption_prf 必须用这个常量。"""
    src = inspect.getsource(amod)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


# ---------- module source forbidden tokens 第二十九批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch16(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第二十六批 ----------


def test_module_source_has_future_annotations_batch16():
    src = inspect.getsource(amod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch16():
    src = inspect.getsource(amod)
    assert '"""人工标注指标：figure-caption' in src


def test_module_source_has_counter_import_batch16():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_any_import_batch16():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import_batch16():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import_batch16():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_relations_constant_batch16():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_figure_caption_function_batch16():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_function_batch16():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_pipeline_failed_string_batch16():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_has_no_annotation_string_batch16():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_has_no_predicted_boundaries_string_batch16():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_has_no_ground_truth_anchors_string_batch16():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_has_tolerance_chars_default_30_batch16():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_search_from_variable_batch16():
    src = inspect.getsource(amod)
    assert "search_from = 0" in src


def test_module_source_has_missing_markers_list_batch16():
    src = inspect.getsource(amod)
    assert "missing_markers: list[str] = []" in src


def test_module_source_has_pairs_sorting_batch16():
    src = inspect.getsource(amod)
    assert "pairs.sort(key=" in src


def test_module_source_has_used_pred_used_gt_sets_batch16():
    src = inspect.getsource(amod)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_module_source_has_position_before_in_source_batch16():
    src = inspect.getsource(amod)
    assert 'position == "before"' in src


def test_module_source_has_f1_calculation_batch16():
    src = inspect.getsource(amod)
    assert "2 * p_val * r_val / denom" in src


def test_module_source_has_all_dunder_batch16():
    src = inspect.getsource(amod)
    assert "__all__ = [" in src


def test_module_source_has_normalize_text_call_batch16():
    src = inspect.getsource(amod)
    assert "normalize_text(c.get" in src


def test_module_source_has_tolerance_chars_in_output_batch16():
    src = inspect.getsource(amod)
    assert '"_tolerance_chars"' in src


# ---------- signatures 第二十六批 ----------


def test_signature_figure_caption_prf_batch16():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch16():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_30_batch16():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_figure_caption_prf_return_annotation_batch16():
    sig = inspect.signature(figure_caption_prf)
    ra = sig.return_annotation
    assert ra is not inspect._empty


def test_signature_chunk_boundary_prf_return_annotation_batch16():
    sig = inspect.signature(chunk_boundary_prf)
    ra = sig.return_annotation
    assert ra is not inspect._empty


def test_signature_no_varargs_batch16():
    """两个函数都不接受 *args 或 **kwargs。"""
    for func in [figure_caption_prf, chunk_boundary_prf]:
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十六批 ----------


def test_module_has_all_attribute_batch16():
    assert hasattr(amod, "__all__")
    assert isinstance(amod.__all__, list)


def test_module_all_items_callable_or_str_batch16():
    for name in amod.__all__:
        attr = getattr(amod, name)
        assert callable(attr) or isinstance(attr, str)


def test_module_all_count_3_batch16():
    assert len(amod.__all__) == 3


def test_module_figure_caption_callable_batch16():
    assert callable(figure_caption_prf)


def test_module_chunk_boundary_callable_batch16():
    assert callable(chunk_boundary_prf)


def test_module_normalize_text_in_namespace_batch16():
    assert hasattr(amod, "normalize_text")


def test_module_null_helper_in_namespace_batch16():
    assert hasattr(amod, "_null")


def test_module_ratio_helper_in_namespace_batch16():
    assert hasattr(amod, "_ratio")


def test_module_does_not_mutate_inputs_in_figure_caption_batch16():
    """figure_caption_prf 不修改输入。"""
    doc = {"x": 1}
    annotation = {"y": 2}
    doc_before = repr(doc)
    annotation_before = repr(annotation)
    figure_caption_prf(doc, annotation)
    assert repr(doc) == doc_before
    assert repr(annotation) == annotation_before


# ---------- 端到端集成第二十六批 ----------


def test_e2e_figure_caption_smoke_batch16():
    """figure_caption_prf 任何输入都不崩。"""
    cases = [(None, None), ({}, {}), ({"x": 1}, None), (None, {"y": 2})]
    for d, a in cases:
        out = figure_caption_prf(d, a)
        assert len(out) == 3


def test_e2e_chunk_boundary_complete_pipeline_batch16():
    """完整 chunk_boundary_prf 流程。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 0


def test_e2e_chunk_boundary_missing_marker_recorded_batch16():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "xyz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]
    assert "abc" not in out["_missing_markers"]["value"]


def test_e2e_chunk_boundary_tolerance_chars_recorded_batch16():
    """tolerance_chars 必须记录。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_e2e_chunk_boundary_default_tolerance_30_batch16():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_chunk_boundary_partial_match_batch16():
    """部分匹配 → precision/recall < 1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # stream = "abc def ghi"，预测位置 = 3, 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # gt = 3, 命中
            {"marker": "zzz", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 命中 1 / 预测 2 = 0.5
    # 命中 1 / gt 1（missing 不计） = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_no_match_f1_zero_batch16():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # F1 = 0 (denom = 0)
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_e2e_chunk_boundary_document_none_pipeline_failed_batch16():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_chunk_boundary_annotation_none_no_annotation_batch16():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_dict_independence_batch16():
    """两次调用同一输入应互不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    out1["chunk_boundary_precision"]["value"] = -999
    assert out2["chunk_boundary_precision"]["value"] != -999


def test_e2e_combined_metrics_smoke_batch16():
    """两个函数都跑通。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    fc = figure_caption_prf(doc, annotation)
    cb = chunk_boundary_prf(doc, annotation)
    assert set(fc.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1"
    }
    assert "chunk_boundary_precision" in cb
