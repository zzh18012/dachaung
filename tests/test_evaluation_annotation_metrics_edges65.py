"""evaluation/annotation_metrics.py 第六十三轮 edges 测试（Round 588）。

补强 edges64 未触及的角度（第三十九批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十九批


def test_parser_const_module_attribute_batch39():
    """模块属性可访问。"""
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_const_module_attribute_settable_batch39():
    """模块属性可被覆写（Python 默认）。"""
    original = amod.PARSER_DOES_NOT_EMIT_RELATIONS
    try:
        amod.PARSER_DOES_NOT_EMIT_RELATIONS = "tmp"
        assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == "tmp"
    finally:
        amod.PARSER_DOES_NOT_EMIT_RELATIONS = original


def test_parser_const_uses_underscores_batch39():
    """全部小写 + 下划线。"""
    s = PARSER_DOES_NOT_EMIT_RELATIONS
    assert s.replace("_", "").isalpha()
    assert s.islower()


def test_parser_const_descriptive_batch39():
    """常量名描述性强（含 parser / does / not / emit / relations）。"""
    parts = PARSER_DOES_NOT_EMIT_RELATIONS.split("_")
    assert "parser" in parts
    assert "does" in parts
    assert "not" in parts
    assert "emit" in parts
    assert "relations" in parts


# ---------- figure_caption_prf 第三十九批


def test_figure_caption_prf_signature_batch39():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_returns_dict_with_3_keys_batch39():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    assert isinstance(out, dict)
    assert len(out) == 3


def test_figure_caption_prf_keys_exact_batch39():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_each_value_has_value_field_batch39():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for v in out.values():
        assert "value" in v


def test_figure_caption_prf_each_value_has_reason_field_batch39():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for v in out.values():
        assert "reason" in v


def test_figure_caption_prf_value_always_none_batch39():
    """figure_caption_prf 永远返回 value=None。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        (None, {"x": 1}),
        ({"chunks": [{"text": "a"}]}, {"x": 1}),
        ({"figure_caption_anchors": [{"x": 1}]}, None),
    ]
    for doc, ann in inputs:
        out = figure_caption_prf(doc, ann)
        for v in out.values():
            assert v["value"] is None


def test_figure_caption_prf_reason_always_parser_const_batch39():
    """reason 始终是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        (None, {"x": 1}),
        ({"x": 1}, {"y": 2}),
    ]
    for doc, ann in inputs:
        out = figure_caption_prf(doc, ann)
        for v in out.values():
            assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_document_no_chunks_batch39():
    """doc 有其他字段但无 chunks → 仍 null。"""
    out = figure_caption_prf({"other_field": 1}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_figure_caption_anchors_batch39():
    """annotation 含 figure_caption_anchors → 仍 null。"""
    out = figure_caption_prf(
        {"chunks": [{"text": "a"}]},
        {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]},
    )
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_does_not_use_annotation_batch39():
    """figure_caption_prf 不读 annotation 的 figure_caption_anchors。"""
    with patch("evaluation.annotation_metrics.normalize_text") as mock_norm:
        figure_caption_prf(
            {"x": 1},
            {"figure_caption_anchors": [{"x": 1}]},
        )
        assert not mock_norm.called


def test_figure_caption_prf_does_not_read_document_batch39():
    """figure_caption_prf 不读 document 内容。"""
    with patch("evaluation.annotation_metrics.normalize_text") as mock_norm:
        figure_caption_prf({"chunks": [{"text": "a"}], "deep": {"nested": "data"}}, None)
        assert not mock_norm.called


def test_figure_caption_prf_output_json_serializable_batch39():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    s = json.dumps(out, ensure_ascii=False)
    assert isinstance(s, str)


# ---------- chunk_boundary_prf 第三十九批


def test_chunk_boundary_prf_signature_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_returns_dict_batch39():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_keys_always_include_tolerance_batch39():
    """输出始终含 _tolerance_chars。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, None),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, None),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []}),
    ]
    for doc, ann in inputs:
        out = chunk_boundary_prf(doc, ann)
        assert "_tolerance_chars" in out


def test_chunk_boundary_prf_tolerance_field_structure_batch39():
    out = chunk_boundary_prf(None, None, tolerance_chars=20)
    tol = out["_tolerance_chars"]
    assert "value" in tol
    assert "reason" in tol
    assert tol["value"] == 20


def test_chunk_boundary_prf_tolerance_zero_batch39():
    """tolerance=0 → 仅完美匹配算。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_huge_batch39():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10**6)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_two_chunks_text_concatenated_batch39():
    """chunk text 在 stream 中按 chunk 顺序拼接。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]}
    # stream = "hello world"
    # 边界 pos=5 (after hello)
    # 'o' 在 pos=4, after → pos=5 → 完美匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunks_with_overlap_text_batch39():
    """两个 chunk 有重叠文本（chunker 词内硬切）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "bcd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    # stream = "abc bcd"
    # 边界 pos=3 (after abc)
    # 'abc' 在 pos=0, after → pos=3 → 完美匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_with_chunk_text_containing_space_batch39():
    """chunk text 自带空格 → normalize 后变单空格。"""
    doc = {"chunks": [{"text": "a b"}, {"text": "c d"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "b", "position": "after"}]}
    # normalize("a b") = "a b"
    # stream = "a b c d"
    # 边界 pos=3 (after "a b")
    # 'b' 在 pos=2, after → pos=3 → 完美匹配
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_doc_with_extra_top_level_keys_batch39():
    """doc 含额外字段 → 不影响。"""
    doc = {"document_id": "x", "source_type": "pdf", "chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunks_with_extra_keys_batch39():
    """chunk dict 含额外字段 → 不影响。"""
    doc = {"chunks": [
        {"text": "abc", "source_element_ids": ["e1"], "chunk_id": "c1"},
        {"text": "def", "source_element_ids": ["e2"], "chunk_id": "c2"},
    ]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_with_extra_keys_batch39():
    """anchor dict 含额外字段 → 不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after", "anchor_id": "a1", "note": "x"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_one_chunk_no_pred_batch39():
    """1 chunk → 0 preds。"""
    doc = {"chunks": [{"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_one_pred_batch39():
    """2 chunks → 1 pred。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 1 pred, 1 anchor → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_three_chunks_two_preds_batch39():
    """3 chunks → 2 preds。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 2 preds, 2 anchors → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_precision_value_type_batch39():
    """precision value 是 float（成功时）或 None。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    v = out["chunk_boundary_precision"]["value"]
    assert v is None or isinstance(v, float)


def test_chunk_boundary_prf_f1_value_type_batch39():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    v = out["chunk_boundary_f1"]["value"]
    assert v is None or isinstance(v, float)


def test_chunk_boundary_prf_with_empty_chunks_list_batch39():
    """chunks 是空 list → no_predicted_boundaries。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # empty chunks → 少于 2 → no_predicted_boundaries
    # anchors 非空 → recall = 0.0
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_with_chunks_not_list_batch39():
    """chunks 不是 list（如 None）→ no_predicted_boundaries。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchor_marker_special_chars_batch39():
    """marker 含特殊字符。"""
    doc = {"chunks": [{"text": "a.b,c"}, {"text": "d"}]}
    ann = {"chunk_boundary_anchors": [{"marker": ".", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "a.b,c d"
    # 边界 pos=5
    # '.' 在 pos=1, after → pos=2, 距离 3 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_doc_dict_can_be_empty_batch39():
    """doc={} + annotation=None → no_annotation。"""
    out = chunk_boundary_prf({}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_output_json_serializable_batch39():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    s = json.dumps(out, ensure_ascii=False)
    assert isinstance(s, str)


def test_chunk_boundary_prf_doc_none_pipeline_failed_path_batch39():
    """doc=None → pipeline_failed reason。"""
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_empty_no_annotation_path_batch39():
    """annotation 是空 dict → no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_missing_markers_when_all_found_batch39():
    """所有 anchor 都找到 → 不出现 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" not in out


# ---------- module source forbidden tokens 第六十一批


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
def test_module_source_no_forbidden_tokens_batch39(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第五十七批


def test_module_source_contains_module_docstring_batch39():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_chunk_boundary_keyword_batch39():
    src = inspect.getsource(amod)
    assert "chunk_boundary" in src


def test_module_source_contains_figure_caption_keyword_batch39():
    src = inspect.getsource(amod)
    assert "figure_caption" in src


def test_module_source_contains_one_to_one_keyword_batch39():
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_contains_tolerance_chars_keyword_batch39():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_normalize_text_import_batch39():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch39():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_pipeline_failed_reason_batch39():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_annotation_reason_batch39():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_contains_no_predicted_boundaries_reason_batch39():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_contains_precision_or_recall_not_evaluated_reason_batch39():
    src = inspect.getsource(amod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason_batch39():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_module_source_contains_from_future_import_batch39():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_collections_counter_import_batch39():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch39():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_all_export_batch39():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_contains_parser_const_export_batch39():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src


def test_module_source_contains_figure_caption_prf_export_batch39():
    src = inspect.getsource(amod)
    assert '"figure_caption_prf"' in src


def test_module_source_contains_chunk_boundary_prf_export_batch39():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_prf"' in src


def test_module_source_contains_dict_annotation_batch39():
    src = inspect.getsource(amod)
    assert "dict[str, dict[str, Any]]" in src


# ---------- signatures 第五十七批


def test_signature_chunk_boundary_prf_tolerance_default_30_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_doc_kind_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_annotation_kind_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["annotation"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_tolerance_kind_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_document_kind_batch39():
    sig = inspect.signature(figure_caption_prf)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_return_dict_batch39():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_figure_caption_prf_return_dict_batch39():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- module 合理性 第五十七批


def test_module_has_docstring_batch39():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_mentions_chunk_boundary_batch39():
    assert "chunk-boundary" in amod.__doc__ or "chunk_boundary" in amod.__doc__


def test_module_all_is_list_batch39():
    assert isinstance(amod.__all__, list)


def test_module_all_len_three_batch39():
    assert len(amod.__all__) == 3


def test_module_all_contains_parser_const_batch39():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_all_contains_figure_caption_prf_batch39():
    assert "figure_caption_prf" in amod.__all__


def test_module_all_contains_chunk_boundary_prf_batch39():
    assert "chunk_boundary_prf" in amod.__all__


def test_module_callable_attributes_batch39():
    assert callable(amod.figure_caption_prf)
    assert callable(amod.chunk_boundary_prf)


def test_module_no_class_definitions_batch39():
    src = inspect.getsource(amod)
    assert "\nclass " not in src


def test_module_uses_null_and_ratio_batch39():
    src = inspect.getsource(amod)
    assert "_null(" in src
    assert "_ratio(" in src


# ---------- 端到端集成 第五十七批


def test_e2e_combined_keys_disjoint_batch39():
    """figure_caption_prf + chunk_boundary_prf 输出 keys 不冲突。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    fcp = figure_caption_prf(doc, ann)
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # figure_caption_prf 的 3 keys
    fcp_keys = set(fcp.keys())
    # chunk_boundary_prf 的 keys（除私有）
    cbp_public_keys = {k for k in cbp.keys() if not k.startswith("_")}
    assert fcp_keys.isdisjoint(cbp_public_keys)


def test_e2e_full_pipeline_failed_then_annotation_batch39():
    """doc=None + 含 annotation → 仍走 pipeline_failed。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_e2e_full_workflow_minimal_batch39():
    """最小完整 workflow。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    fcp = figure_caption_prf(doc, ann)
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # figure_caption 三个 null
    for v in fcp.values():
        assert v["value"] is None
    # chunk_boundary 至少含 4 keys（precision / recall / f1 / _tolerance_chars）
    assert len(cbp) >= 4


def test_e2e_idempotent_across_calls_batch39():
    """多次调用结果一致。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    outs = [chunk_boundary_prf(doc, ann, tolerance_chars=5) for _ in range(3)]
    for o in outs[1:]:
        assert o == outs[0]


def test_e2e_does_not_mutate_doc_or_annotation_batch39():
    """不修改 doc / annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before
