"""evaluation/annotation_metrics.py 第五十九轮 edges 测试（Round 546）。

补强 edges58 未触及的角度（第三十二批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十二批 ----------


def test_parser_does_not_emit_relations_module_top_level_batch32():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_parser_does_not_emit_relations_value_exact_batch32():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_string_batch32():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_hashable_batch32():
    """常量可 hash（用作 dict key 或 set 元素）。"""
    s = {PARSER_DOES_NOT_EMIT_RELATIONS}
    assert PARSER_DOES_NOT_EMIT_RELATIONS in s


def test_parser_does_not_emit_relations_in_all_batch32():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src


# ---------- figure_caption_prf 第三十二批 ----------


def test_figure_caption_prf_returns_three_keys_batch32():
    out = figure_caption_prf({"chunks": []}, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_none_batch32():
    out = figure_caption_prf({"chunks": [{"text": "x"}]}, {"any": "annotation"})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_all_reasons_fixed_batch32():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_document_none_batch32():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_empty_dict_batch32():
    out = figure_caption_prf({"chunks": []}, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_returns_new_dict_each_call_batch32():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2
    assert out1 is not out2
    # 修改 out1 不影响 out2
    out1["figure_caption_precision"]["value"] = 999
    assert out2["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_does_not_modify_input_batch32():
    doc = {"chunks": [{"text": "x"}]}
    ann = {"key": "value"}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


# ---------- chunk_boundary_prf 第三十二批 ----------


def test_chunk_boundary_prf_returns_dict_batch32():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]})
    assert isinstance(out, dict)


def test_chunk_boundary_prf_keys_count_batch32():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]})
    # 3 base + 1 tolerance = 4 keys minimum
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch32():
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_no_annotation_returns_no_annotation_batch32():
    out = chunk_boundary_prf({"chunks": []}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation_batch32():
    out = chunk_boundary_prf({"chunks": []}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_batch32():
    """单个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_anchors_with_chunks_returns_no_ground_truth_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_batch32():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="hello world", predicted=[5], anchor="hello" after → 5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_batch32():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_huge_batch32():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=999999)
    assert out["_tolerance_chars"]["value"] == 999999


def test_chunk_boundary_prf_missing_marker_recorded_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "nonexistent", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_marker_recall_null_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "nonexistent", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_position_before_batch32():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # stream="abc def", predicted=[3] (chunk0 end), anchor="def" before → 4
    # |3-4|=1 ≤ 1 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_two_chunks_one_match_batch32():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # 2 predicted boundaries
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted=[2, 5], gt=[2] → 1 match
    # P=1/2=0.5, R=1/1=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_f1_with_perfect_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # P=R=1.0 → F1=1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_with_zero_recall_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xxxx", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # recall null (missing marker), precision=0.0 → f1 null
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_prf_no_input_modification_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_chunk_boundary_prf_idempotent_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_chunk_boundary_prf_chunks_with_whitespace_batch32():
    doc = {"chunks": [{"text": "  hello  "}, {"text": "  world  "}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # normalize_text 压缩空白 → stream="hello world"
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- module source forbidden tokens 第四十九批 ----------


def test_module_source_no_subprocess_batch32():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch32():
    src = inspect.getsource(amod)
    assert "os.system" not in src


def test_module_source_no_eval_batch32():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec_batch32():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch32():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch32():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch32():
    src = inspect.getsource(amod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch32():
    src = inspect.getsource(amod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch32():
    src = inspect.getsource(amod)
    assert "shutil" not in src


def test_module_source_no_requests_batch32():
    src = inspect.getsource(amod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch32():
    src = inspect.getsource(amod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_unlink_batch32():
    src = inspect.getsource(amod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十五批 ----------


def test_module_source_contains_module_docstring_batch32():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_parser_does_not_emit_relations_const_batch32():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_func_batch32():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_func_batch32():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_normalize_text_import_batch32():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch32():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_counter_import_batch32():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch32():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_pipeline_failed_reason_batch32():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_reason_batch32():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_reason_batch32():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_reason_batch32():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason_batch32():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in src


def test_module_source_contains_precision_or_recall_not_evaluated_batch32():
    src = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in src


def test_module_source_contains_search_from_local_batch32():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_contains_missing_markers_local_batch32():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_contains_normalize_text_call_batch32():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_contains_tolerance_chars_record_batch32():
    src = inspect.getsource(amod)
    assert '"_tolerance_chars"' in src


# ---------- signatures 第四十五批 ----------


def test_signature_figure_caption_prf_return_dict_batch32():
    sig = inspect.signature(figure_caption_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_return_dict_batch32():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_figure_caption_prf_document_annotation_batch32():
    sig = inspect.signature(figure_caption_prf)
    for p_name in ("document", "annotation"):
        a = sig.parameters[p_name].annotation
        assert "dict" in str(a)
        assert "None" in str(a)


def test_signature_chunk_boundary_prf_document_annotation_batch32():
    sig = inspect.signature(chunk_boundary_prf)
    for p_name in ("document", "annotation"):
        a = sig.parameters[p_name].annotation
        assert "dict" in str(a)
        assert "None" in str(a)


def test_signature_chunk_boundary_prf_tolerance_default_30_batch32():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_tolerance_annotation_int_batch32():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].annotation == "int"


def test_signature_chunk_boundary_prf_params_count_batch32():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_figure_caption_prf_params_count_batch32():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


# ---------- module 合理性第四十五批 ----------


def test_module_has_future_annotations_batch32():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_imports_counter_batch32():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_typing_any_batch32():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text_batch32():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_ratio_batch32():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_has_all_export_batch32():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_all_has_three_entries_batch32():
    src = inspect.getsource(amod)
    for name in [
        '"PARSER_DOES_NOT_EMIT_RELATIONS"',
        '"figure_caption_prf"',
        '"chunk_boundary_prf"',
    ]:
        assert name in src


def test_module_no_main_block_batch32():
    src = inspect.getsource(amod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十五批 ----------


def test_e2e_chunk_boundary_perfect_match_with_tolerance_batch32():
    """端到端：含容差的完美匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hell", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # stream="hello world", predicted=[5]
    # anchor="hell" after → 4, |5-4|=1 ≤ 2 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_returns_three_keys_batch32():
    """端到端：figure_caption 始终返回 3 key。"""
    out = figure_caption_prf({"chunks": []}, None)
    assert len(out) == 3


def test_e2e_chunk_boundary_no_input_modification_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_e2e_chunk_boundary_idempotent_batch32():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_e2e_chunk_boundary_all_reasons_used_batch32():
    """端到端：测各种 reason 都可能出现。"""
    reasons = set()
    # pipeline_failed
    out = chunk_boundary_prf(None, None)
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_annotation
    out = chunk_boundary_prf({"chunks": []}, None)
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_predicted_boundaries
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]})
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_ground_truth_anchors
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []})
    reasons.add(out["chunk_boundary_precision"]["reason"])
    assert reasons == {
        "pipeline_failed",
        "no_annotation",
        "no_predicted_boundaries",
        "no_ground_truth_anchors",
    }


def test_e2e_chunk_boundary_tolerance_recorded_batch32():
    """端到端：tolerance 在输出中记录。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_e2e_figure_caption_with_real_document_with_figures_batch32():
    """端到端：含 figures 的真实 document → figure_caption null。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1"},
            {"type": "caption", "text": "Fig 1"},
        ],
        "chunks": [{"text": "Fig 1"}],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
