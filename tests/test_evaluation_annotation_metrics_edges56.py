"""evaluation/annotation_metrics.py 第五十六轮 edges 测试（Round 525）。

补强 edges55 未触及的角度（第二十九批）：
- PARSER_DOES_NOT_EMIT_RELATIONS 第二十九批：是 str / 值精确
- figure_caption_prf 第二十九批：3 keys / 都 null / reason 一致 / annotation=None / document 含 figure
- chunk_boundary_prf 第二十九批：tolerance 默认 30 / tolerance=0 / 多 chunk 多 anchor / 重复 marker / missing marker / F1 计算
- module source forbidden tokens 第四十六批
- module source 字符串精确补强第四十二批
- signatures 第四十二批
- module 合理性第四十二批
- 端到端集成第四十二批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第二十九批 ----------


def test_parser_does_not_emit_relations_is_str_batch29():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_batch29():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_constant_batch29():
    """模块顶层常量。"""
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


# ---------- figure_caption_prf 第二十九批 ----------


def test_figure_caption_prf_three_keys_batch29():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_null_batch29():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_consistent_batch29():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_annotation_none_batch29():
    """annotation=None 也 null。"""
    out = figure_caption_prf({"chunks": [{"text": "x"}]}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_real_document_with_figures_batch29():
    """含 figure 的真实 document 也 null（parser 不输出 relation）。"""
    doc = {
        "elements": [{"type": "image", "element_id": "i1"}],
        "chunks": [{"text": "x"}],
    }
    annotation = {"figure_caption_relations": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, annotation)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_idempotent_batch29():
    out1 = figure_caption_prf({"chunks": []}, {"x": 1})
    out2 = figure_caption_prf({"chunks": []}, {"x": 1})
    assert out1 == out2


def test_figure_caption_prf_returns_dict_batch29():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_no_input_modification_batch29():
    doc = {"chunks": [{"text": "x"}]}
    ann = {"foo": [1, 2, 3]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_figure_caption_prf_annotation_empty_dict_batch29():
    """annotation 是空 dict 也 null。"""
    out = figure_caption_prf({"chunks": []}, {})
    for v in out.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 第二十九批 ----------


def test_chunk_boundary_prf_default_tolerance_30_batch29():
    """默认 tolerance=30。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_zero_perfect_match_batch29():
    """tolerance=0 完美匹配。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="aaa bbb", 预测边界=3, anchor="aaa" after → 3 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_no_match_batch29():
    """tolerance=0 距离 1 → 不匹配。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="aaa bbb", 预测边界=3, anchor="a" after → 1, |3-1|=2 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_f1_perfect_batch29():
    """F1 完美：P=R=1.0 → F1=1.0。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_batch29():
    """F1 零：P=R=0 → F1=0。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_half_batch29():
    """F1 半：P=1, R=0.5 → F1=2*1*0.5/(1+0.5)=2/3。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # 3
            {"marker": "zzz", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 2 predicted boundaries (3, 7), 1 anchor match
    # precision=1/2, recall=1/1=1.0 → f1=2*0.5*1/(0.5+1)=1/1.5=2/3
    # Wait: anchors list has 2 entries, but "zzz" is missing
    # So gt_positions only has 1 entry → recall=1/1=1.0
    # predicted has 2 → precision=1/2
    assert abs(out["chunk_boundary_precision"]["value"] - 0.5) < 1e-9
    assert abs(out["chunk_boundary_recall"]["value"] - 1.0) < 1e-9
    assert abs(out["chunk_boundary_f1"]["value"] - 2.0 / 3.0) < 1e-9


def test_chunk_boundary_prf_returns_dict_batch29():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_document_none_pipeline_failed_batch29():
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_empty_no_annotation_batch29():
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_none_no_annotation_batch29():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_one_chunk_no_predicted_batch29():
    """单 chunk → 无预测边界。"""
    doc = {"chunks": [{"text": "aaa"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_zero_chunks_batch29():
    """无 chunks → 无预测边界。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_has_chunks_no_anchors_batch29():
    """有 chunks 但无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_missing_markers_recorded_batch29():
    """missing marker 被记录。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},
            {"marker": "zzz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" in out
    assert "zzz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_no_key_batch29():
    """无 missing marker → 不含 _missing_markers key。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_idempotent_batch29():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_chunk_boundary_prf_no_input_modification_batch29():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_chunk_boundary_prf_returns_six_keys_minimum_batch29():
    """返回至少含 6 个 metric key（3 P/R/F1 + _tolerance_chars）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_tolerance_int_batch29():
    """_tolerance_chars 是 int。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert isinstance(out["_tolerance_chars"]["value"], int)
    assert out["_tolerance_chars"]["value"] == 42


# ---------- module source forbidden tokens 第四十六批 ----------


def test_module_source_no_subprocess_batch29():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch29():
    src = inspect.getsource(amod)
    assert "os.system" not in src


def test_module_source_no_eval_batch29():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec_batch29():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch29():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch29():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch29():
    src = inspect.getsource(amod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch29():
    src = inspect.getsource(amod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch29():
    src = inspect.getsource(amod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch29():
    src = inspect.getsource(amod)
    assert "shutil" not in src


def test_module_source_no_requests_batch29():
    src = inspect.getsource(amod)
    assert "requests" not in src


def test_module_source_no_unlink_batch29():
    src = inspect.getsource(amod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十二批 ----------


def test_module_source_contains_module_docstring_batch29():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_parser_does_not_emit_relations_batch29():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_docstring_batch29():
    src = inspect.getsource(amod)
    assert "图表关联" in src


def test_module_source_contains_chunk_boundary_docstring_batch29():
    src = inspect.getsource(amod)
    assert "分块边界" in src


def test_module_source_contains_normalize_text_call_batch29():
    src = inspect.getsource(amod)
    assert "normalize_text" in src


def test_module_source_contains_pipeline_failed_batch29():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_batch29():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_batch29():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_batch29():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_batch29():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in src


def test_module_source_contains_precision_or_recall_not_evaluated_batch29():
    src = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in src


def test_module_source_contains_tolerance_chars_param_batch29():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_contains_counter_import_batch29():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


# ---------- signatures 第四十二批 ----------


def test_signature_figure_caption_prf_return_annotation_batch29():
    sig = inspect.signature(figure_caption_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_return_annotation_batch29():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_figure_caption_prf_document_annotation_batch29():
    sig = inspect.signature(figure_caption_prf)
    for p_name in ("document", "annotation"):
        annotation = sig.parameters[p_name].annotation
        assert "dict" in str(annotation)
        assert "None" in str(annotation)


def test_signature_chunk_boundary_prf_document_annotation_batch29():
    sig = inspect.signature(chunk_boundary_prf)
    annotation = sig.parameters["document"].annotation
    assert "dict" in str(annotation)
    assert "None" in str(annotation)


def test_signature_chunk_boundary_prf_tolerance_default_batch29():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_tolerance_annotation_batch29():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].annotation == "int"


# ---------- module 合理性第四十二批 ----------


def test_module_has_future_annotations_batch29():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_imports_counter_batch29():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_typing_any_batch29():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text_batch29():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_ratio_batch29():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_all_export_three_entries_batch29():
    src = inspect.getsource(amod)
    for name in [
        '"PARSER_DOES_NOT_EMIT_RELATIONS"',
        '"figure_caption_prf"',
        '"chunk_boundary_prf"',
    ]:
        assert name in src


def test_module_no_class_definitions_batch29():
    src = inspect.getsource(amod)
    assert "\nclass " not in src


def test_module_no_main_block_batch29():
    src = inspect.getsource(amod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十二批 ----------


def test_e2e_chunk_boundary_prf_full_pipeline_batch29():
    """端到端：完整跑 chunk_boundary。"""
    doc = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
            {"text": "foo"},
        ]
    }
    # stream="hello world foo"
    # predicted boundaries: 5 (after hello), 11 (after world)
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
            {"marker": "world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_prf_full_pipeline_batch29():
    """端到端：figure_caption_prf 完整调用。"""
    out = figure_caption_prf(
        {"elements": [{"type": "image", "caption_id": "c1"}]},
        {"figure_caption_relations": [{"figure_id": "f1", "caption_id": "c1"}]},
    )
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_prf_with_tolerance_batch29():
    """端到端：tolerance 容差匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream="hello world", predicted=5
    # anchor="hell" after → 4, |5-4|=1 ≤ 5 → match
    ann = {"chunk_boundary_anchors": [{"marker": "hell", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_returns_dict_with_metrics_batch29():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out, dict)
    assert "chunk_boundary_precision" in out


def test_e2e_chunk_boundary_prf_no_side_effects_batch29():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_e2e_chunk_boundary_prf_idempotent_batch29():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_e2e_chunk_boundary_prf_tolerance_in_output_batch29():
    """端到端：tolerance 记录在输出中。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
