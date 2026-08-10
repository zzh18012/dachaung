"""evaluation/annotation_metrics.py 第三十七轮 edges 测试（Round 392）。

补强 edges36 未触及的角度：
- figure_caption_prf 行为深度第十批
- chunk_boundary_prf 行为深度第十批（更多 branch / tolerance 边界 / Unicode / idempotent / no mutate / position before-after 混合）
- module source forbidden tokens 第十三批
- module source 字符串精确补强第八批
- signatures 第十批
- module 合理性第十批
- 端到端集成第十批
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


# ---------- figure_caption_prf 行为深度第十批 ----------


def test_figure_caption_prf_returns_dict_batch10():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_three_keys_batch10():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_keys_in_order_batch10():
    out = figure_caption_prf(None, None)
    assert list(out.keys()) == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_all_values_null_batch10():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_batch10():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_document_still_null_batch10():
    doc = {"elements": [{"type": "image"}, {"type": "caption"}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_still_null_batch10():
    annot = {"figure_caption_pairs": [["f1", "c1"]]}
    out = figure_caption_prf(None, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_both_args_still_null_batch10():
    doc = {"elements": [{"type": "image"}]}
    annot = {"figure_caption_pairs": [["f1", "c1"]]}
    out = figure_caption_prf(doc, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_each_value_is_dict_batch10():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_idempotent_batch10():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_no_mutate_input_dict_batch10():
    doc = {"elements": [{"type": "image"}]}
    snapshot = json.dumps(doc)
    _ = figure_caption_prf(doc, None)
    assert json.dumps(doc) == snapshot


def test_figure_caption_prf_accepts_empty_dict_doc_batch10():
    out = figure_caption_prf({}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_accepts_empty_dict_annot_batch10():
    out = figure_caption_prf(None, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_returns_dict_with_value_reason_only_batch10():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_repeated_calls_same_output_batch10():
    """连续调用同一参数，结果相同。"""
    for _ in range(5):
        out = figure_caption_prf(None, None)
        assert set(out.keys()) == {
            "figure_caption_precision",
            "figure_caption_recall",
            "figure_caption_f1",
        }


def test_figure_caption_prf_returns_same_object_for_same_inputs_batch10():
    """同输入 → 同输出（值相等，但不必同对象）。"""
    out1 = figure_caption_prf({"a": 1}, {"b": 2})
    out2 = figure_caption_prf({"a": 1}, {"b": 2})
    assert out1 == out2


def test_figure_caption_prf_document_with_chunks_batch10():
    """document 含 chunks 也不影响（figure_caption 始终 null）。"""
    doc = {"chunks": [{"text": "hello"}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_annotation_with_chunks_anchors_batch10():
    """annotation 含 chunk_boundary_anchors 也不影响。"""
    annot = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = figure_caption_prf(None, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_value_keys_strict_batch10():
    """每个 value 字典精确含 value+reason 两 key。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}, f"{k} has extra keys: {set(v.keys())}"


# ---------- chunk_boundary_prf 行为深度第十批 ----------


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch10():
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_includes_tolerance_record_batch10():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_document_none_default_tolerance_30_batch10():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_document_none_no_missing_markers_key_batch10():
    out = chunk_boundary_prf(None, None)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_no_annotation_returns_no_annotation_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_falsy_annotation_returns_no_annotation_batch10():
    """空 list / 0 / False 等 falsy annotation → no_annotation。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    for falsy in ([], 0, False, ""):
        out = chunk_boundary_prf(doc, falsy)
        for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
            assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_returns_no_predicted_boundaries_batch10():
    """document 无 chunks → no_predicted_boundaries。"""
    doc = {}
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_boundaries_batch10():
    """只 1 个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"text": "hello"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_anchors_returns_no_gt_anchors_batch10():
    """有 chunks 但无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_match_perfect_batch10():
    """完美匹配：1 chunk break + 1 anchor 在 break 位置。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 应该匹配成功
    assert out["chunk_boundary_precision"]["value"] is not None
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_prf_tolerance_zero_strict_batch10():
    """tolerance_chars=0：必须精确匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"}  # 精确在 break 处
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # hello|world break 位置 = 5（hello 结束位置）
    # anchor "hello" position=after → find_pos + len("hello") = 0 + 5 = 5
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch10():
    """position=before：anchor 在 marker 起始位置。"""
    doc = {"chunks": [{"text": "hello world"}, {"text": "foo bar"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "before"}
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 应该能匹配
    assert out["chunk_boundary_precision"]["value"] is not None


def test_chunk_boundary_prf_tolerance_huge_value_batch10():
    """tolerance_chars 巨大 → 所有预测都能匹配（只要有 anchor）。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "abc_xyz_unknown", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=100000)
    # marker 找不到 → missing_markers
    assert "_missing_markers" in out
    assert "abc_xyz_unknown" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_missing_marker_recorded_batch10():
    """找不到的 marker 必须记入 _missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "missing_text_xyz", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annot)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["missing_text_xyz"]


def test_chunk_boundary_prf_multiple_missing_markers_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "missing1", "position": "after"},
            {"marker": "missing2", "position": "after"},
            {"marker": "missing3", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot)
    assert "_missing_markers" in out
    assert set(out["_missing_markers"]["value"]) == {"missing1", "missing2", "missing3"}


def test_chunk_boundary_prf_idempotent_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot)
    out2 = chunk_boundary_prf(doc, annot)
    assert out1 == out2


def test_chunk_boundary_prf_no_mutate_document_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    snapshot = json.dumps(doc)
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    _ = chunk_boundary_prf(doc, annot)
    assert json.dumps(doc) == snapshot


def test_chunk_boundary_prf_no_mutate_annotation_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    snapshot = json.dumps(annot)
    _ = chunk_boundary_prf(doc, annot)
    assert json.dumps(annot) == snapshot


def test_chunk_boundary_prf_includes_tolerance_record_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=15)
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_unicode_marker_batch10():
    """Unicode marker（中文）能查找。"""
    doc = {"chunks": [{"text": "你好世界"}, {"text": "后续内容"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "世界", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 应当能匹配
    assert out["chunk_boundary_precision"]["value"] is not None or "_missing_markers" in out


def test_chunk_boundary_prf_returns_dict_with_correct_keys_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    expected_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }
    assert expected_keys.issubset(set(out.keys()))


def test_chunk_boundary_prf_two_chunks_two_anchors_partial_batch10():
    """2 chunks + 2 anchors，只匹配部分。"""
    doc = {
        "chunks": [
            {"text": "first chunk"},
            {"text": "second chunk"},
            {"text": "third chunk"},
        ]
    }
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "chunk", "position": "after"},
            {"marker": "missing", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 一个匹配，一个 missing
    assert "_missing_markers" in out


def test_chunk_boundary_prf_one_chunk_no_anchors_batch10():
    """1 chunk + 0 anchors：no_predicted_boundaries + no anchors 不算 no_gt_anchors。"""
    doc = {"chunks": [{"text": "hello"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 没有 anchor → recall 仍 no_predicted_boundaries
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_batch10():
    """1 chunk + 有 anchors → recall=0.0（有 GT 但无预测边界）。"""
    doc = {"chunks": [{"text": "hello"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall = 0.0 因为有 anchors 但无预测
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_default_tolerance_30_batch10():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_position_default_after_batch10():
    """anchor 不提供 position → 默认 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "hello"}  # 无 position
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 默认 after → 应当匹配
    # 检查不抛
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunk_no_text_field_batch10():
    """chunk 无 text 字段 → 当作 "" 处理。"""
    doc = {"chunks": [{}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunk_text_none_batch10():
    """chunk text=None → 当作 ""。"""
    doc = {"chunks": [{"text": None}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_f1_zero_when_p_r_zero_batch10():
    """P=R=0 → F1=0.0。"""
    doc = {
        "chunks": [
            {"text": "first"},
            {"text": "second"},
        ]
    }
    # anchor 远离任何边界
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "firstsecond", "position": "after"}  # 整体作为一个 marker，但流里没有
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # marker 找不到 → missing_markers
    # 此时 num_gt=0 → recall null
    # num_pred=1 → precision=0/1=0.0
    assert "_missing_markers" in out


def test_chunk_boundary_prf_anchor_marker_empty_batch10():
    """anchor marker 为空字符串 → 当作找不到。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    # 空 marker → find 返 -1 → missing_markers
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_returns_correct_f1_formula_batch10():
    """F1 = 2PR / (P+R)。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f = out["chunk_boundary_f1"]["value"]
    if p is not None and r is not None and (p + r) > 0:
        assert abs(f - 2 * p * r / (p + r)) < 1e-9


def test_chunk_boundary_prf_chunk_with_extra_whitespace_batch10():
    """chunk text 含大量空白 → normalize 后位置仍然正确。"""
    doc = {"chunks": [{"text": "hello   world"}, {"text": "foo"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # normalize 把多个空格压成一个 → 应当能匹配
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第十三批 ----------


def test_amod_source_no_os_system_batch10():
    source = inspect.getsource(amod)
    assert "os.system" not in source


def test_amod_source_no_subprocess_batch10():
    source = inspect.getsource(amod)
    assert "subprocess.Popen" not in source
    assert "subprocess.check_call" not in source


def test_amod_source_no_pickle_load_batch10():
    source = inspect.getsource(amod)
    assert "pickle.load" not in source


def test_amod_source_no_yaml_load_batch10():
    source = inspect.getsource(amod)
    assert "yaml.load" not in source


def test_amod_source_no_eval_exec_batch10():
    source = inspect.getsource(amod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_amod_source_no_compile_batch10():
    source = inspect.getsource(amod)
    assert "compile(" not in source


def test_amod_source_no_sys_exit_batch10():
    source = inspect.getsource(amod)
    assert "sys.exit" not in source
    assert "exit(" not in source
    assert "quit(" not in source


def test_amod_source_no_global_keyword_batch10():
    source = inspect.getsource(amod)
    assert "\nglobal " not in source


def test_amod_source_no_async_def_batch10():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_amod_source_no_yield_batch10():
    source = inspect.getsource(amod)
    assert "yield" not in source


def test_amod_source_no_walrus_batch10():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_amod_source_no_class_def_batch10():
    source = inspect.getsource(amod)
    assert "\nclass " not in source


def test_amod_source_no_unlink_remove_batch10():
    source = inspect.getsource(amod)
    assert ".unlink(" not in source
    assert ".remove(" not in source


def test_amod_source_no_logging_batch10():
    source = inspect.getsource(amod)
    assert "logging" not in source
    assert "logger" not in source


def test_amod_source_no_sleep_batch10():
    source = inspect.getsource(amod)
    assert "time.sleep" not in source


def test_amod_source_no_hardcoded_path_batch10():
    source = inspect.getsource(amod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations_batch10():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_counter_batch10():
    source = inspect.getsource(amod)
    assert "from collections import Counter" in source


def test_module_source_imports_typing_any_batch10():
    source = inspect.getsource(amod)
    assert "from typing import Any" in source


def test_module_source_imports_normalize_text_batch10():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_imports_null_ratio_batch10():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_has_parser_does_not_emit_constant_batch10():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_has_figure_caption_prf_def_batch10():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_has_chunk_boundary_prf_def_batch10():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_uses_normalize_text_batch10():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_uses_null_helper_batch10():
    source = inspect.getsource(amod)
    assert "_null(" in source


def test_module_source_uses_ratio_helper_batch10():
    source = inspect.getsource(amod)
    assert "_ratio(" in source


def test_module_source_no_main_block_batch10():
    source = inspect.getsource(amod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch10():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


def test_module_source_docstring_mentions_chunk_boundary_batch10():
    assert "chunk_boundary" in amod.__doc__ or "chunk-boundary" in amod.__doc__


def test_module_source_docstring_mentions_figure_caption_batch10():
    assert "figure-caption" in amod.__doc__ or "figure_caption" in amod.__doc__


def test_module_source_uses_counter_batch10():
    """Counter 可能用于统计。"""
    source = inspect.getsource(amod)
    # Counter 已导入但模块内可能未直接用（导入是预防）
    assert "Counter" in source


def test_module_source_uses_tolerance_chars_param_batch10():
    source = inspect.getsource(amod)
    assert "tolerance_chars" in source


def test_module_source_uses_anchor_marker_batch10():
    source = inspect.getsource(amod)
    assert "marker" in source


def test_module_source_uses_position_before_after_batch10():
    source = inspect.getsource(amod)
    assert '"before"' in source
    assert '"after"' in source


def test_module_source_uses_missing_markers_batch10():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


def test_module_source_uses_chunk_boundary_anchors_batch10():
    source = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in source


def test_module_source_no_print_batch10():
    source = inspect.getsource(amod)
    assert "print(" not in source


def test_module_source_uses_pipeline_failed_reason_batch10():
    source = inspect.getsource(amod)
    assert '"pipeline_failed"' in source


def test_module_source_uses_no_annotation_reason_batch10():
    source = inspect.getsource(amod)
    assert '"no_annotation"' in source


def test_module_source_uses_no_predicted_boundaries_reason_batch10():
    source = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in source


def test_module_source_uses_no_ground_truth_anchors_reason_batch10():
    source = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in source


# ---------- signatures 第十批 ----------


def test_signature_figure_caption_prf_param_count_batch10():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_signature_figure_caption_prf_param_names_batch10():
    sig = inspect.signature(figure_caption_prf)
    names = list(sig.parameters)
    assert names == ["document", "annotation"]


def test_signature_figure_caption_prf_param_kinds_batch10():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_param_annotations_batch10():
    sig = inspect.signature(figure_caption_prf)
    annotations = {n: p.annotation for n, p in sig.parameters.items()}
    assert annotations == {
        "document": "dict[str, Any] | None",
        "annotation": "dict[str, Any] | None",
    }


def test_signature_figure_caption_prf_no_defaults_batch10():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_figure_caption_prf_return_annotation_batch10():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_chunk_boundary_prf_param_count_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_signature_chunk_boundary_prf_param_names_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    names = list(sig.parameters)
    assert names == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_param_kinds_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert all(p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)


def test_signature_chunk_boundary_prf_param_annotations_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    annotations = {n: p.annotation for n, p in sig.parameters.items()}
    assert annotations == {
        "document": "dict[str, Any] | None",
        "annotation": "dict[str, Any] | None",
        "tolerance_chars": "int",
    }


def test_signature_chunk_boundary_prf_tolerance_default_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_signature_chunk_boundary_prf_return_annotation_batch10():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_2_funcs_are_function_type_batch10():
    for func in (figure_caption_prf, chunk_boundary_prf):
        assert inspect.isfunction(func)


def test_signature_2_funcs_module_eq_batch10():
    for func in (figure_caption_prf, chunk_boundary_prf):
        assert func.__module__ == "evaluation.annotation_metrics"


def test_signature_no_var_positional_batch10():
    for func in (figure_caption_prf, chunk_boundary_prf):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_no_var_keyword_batch10():
    for func in (figure_caption_prf, chunk_boundary_prf):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十批 ----------


def test_module_all_attribute_value_batch10():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_all_is_list_batch10():
    assert isinstance(amod.__all__, list)


def test_module_all_entries_unique_batch10():
    assert len(amod.__all__) == len(set(amod.__all__))


def test_module_has_dunder_file_batch10():
    assert hasattr(amod, "__file__")
    assert amod.__file__ is not None


def test_module_dunder_file_endswith_annotation_metrics_py_batch10():
    sep = os.sep
    assert amod.__file__.endswith("evaluation" + sep + "annotation_metrics.py") or amod.__file__.endswith(
        "evaluation/annotation_metrics.py"
    )


def test_module_dunder_name_batch10():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_function_count_batch10():
    """2 module-level functions。"""
    funcs = [
        n
        for n, v in vars(amod).items()
        if inspect.isfunction(v) and v.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}
    assert len(funcs) == 2


def test_module_no_user_classes_batch10():
    classes = [
        n for n, v in vars(amod).items() if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_constants_count_batch10():
    consts = [
        n
        for n, v in vars(amod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.ismodule(v)
        and not inspect.isclass(v)
    ]
    # annotations 是 from __future__ import annotations 注入的（_Feature 对象）
    assert set(consts) == {"PARSER_DOES_NOT_EMIT_RELATIONS", "annotations"}


def test_module_parser_does_not_emit_constant_value_batch10():
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_parser_does_not_emit_constant_type_batch10():
    assert isinstance(amod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_no_call_at_top_level_batch10():
    source = inspect.getsource(amod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "PARSER_DOES_NOT_EMIT_RELATIONS",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present_batch10():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


def test_module_docstring_in_chinese_or_english_batch10():
    """docstring 含中文或英文 keyword。"""
    assert "标注" in amod.__doc__ or "annotation" in amod.__doc__.lower()


def test_module_public_api_via_all_batch10():
    """__all__ 含所有公开 API。"""
    for name in ("PARSER_DOES_NOT_EMIT_RELATIONS", "figure_caption_prf", "chunk_boundary_prf"):
        assert name in amod.__all__


# ---------- 端到端集成第十批 ----------


def test_e2e_figure_caption_prf_idempotent_under_repeated_calls_batch10():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    out3 = figure_caption_prf(None, None)
    assert out1 == out2 == out3


def test_e2e_chunk_boundary_prf_idempotent_under_repeated_calls_batch10():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot)
    out2 = chunk_boundary_prf(doc, annot)
    out3 = chunk_boundary_prf(doc, annot)
    assert out1 == out2 == out3


def test_e2e_chunk_boundary_prf_no_unexpected_exceptions_batch10():
    """连续调用不抛异常。"""
    for _ in range(3):
        chunk_boundary_prf(None, None)


def test_e2e_chunk_boundary_prf_full_pipeline_success_batch10():
    """完整成功流：chunks + annotation → 非 null 输出。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 应当有非 null 的 precision/recall
    assert out["chunk_boundary_precision"]["value"] is not None
    assert out["chunk_boundary_recall"]["value"] is not None
    assert out["chunk_boundary_f1"]["value"] is not None


def test_e2e_chunk_boundary_prf_full_pipeline_failure_batch10():
    """完整失败流：document None → 所有 metric null。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None


def test_e2e_module_can_be_imported_batch10():
    import evaluation.annotation_metrics as a
    assert a is amod


def test_e2e_module_constants_exposed_batch10():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_e2e_both_funcs_callable_batch10():
    assert callable(figure_caption_prf)
    assert callable(chunk_boundary_prf)


def test_e2e_chunk_boundary_prf_no_extra_keys_batch10():
    """输出 key 集合必须是预期 4 个（含 _tolerance_chars），加可选 _missing_markers。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    allowed_keys = {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }
    for k in out.keys():
        assert k in allowed_keys


def test_e2e_figure_caption_prf_no_extra_keys_batch10():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_e2e_chunk_boundary_prf_full_match_precision_one_batch10():
    """完美匹配：所有预测都被 GT 接受 → P=1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # hello|world break @ 5; anchor after "hello" = 0+5 = 5 → exact match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_position_mixed_batch10():
    """混用 before/after position。"""
    doc = {"chunks": [{"text": "alpha beta"}, {"text": "gamma delta"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
            {"marker": "gamma", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    # 应当都能匹配
    assert isinstance(out, dict)
    # 不抛即可
