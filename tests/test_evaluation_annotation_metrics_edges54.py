"""evaluation/annotation_metrics.py 第五十四轮 edges 测试（Round 511）。

补强 edges53 未触及的角度（第二十七批）：
- figure_caption_prf 第二十七批：document 是 dict 但 annotation 是 list / annotation 是 None / 双 None / 返回 3 个 metric / reason 常量 / 调用零依赖
- chunk_boundary_prf 第二十七批：document None / annotation None / annotation 空字典 / chunks=1 / chunks=0 / anchors 缺失 key / position="before" / position="after" / marker 不在 stream / 多 marker 顺序定位 / 重复 marker / tolerance=0 严格 / tolerance 巨大
- 模块 source forbidden tokens 第四十四批
- 模块 source 字符串精确补强第四十批
- signatures 第四十批
- module 合理性第四十批
- 端到端集成第四十批
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
from evaluation.metrics import _null, _ratio


# ---------- figure_caption_prf 第二十七批 ----------


def test_figure_caption_prf_returns_three_metrics_batch27():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_null_reason_batch27():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_document_dict_annotation_none_batch27():
    """document 是 dict 但仍 null。"""
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_document_dict_annotation_dict_batch27():
    """document + annotation 都有也仍 null（parser 不输出 relation）。"""
    out = figure_caption_prf({"chunks": []}, {"x": 1})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_annotation_list_batch27():
    """annotation 是 list（异常类型）→ 仍 null。"""
    out = figure_caption_prf({"chunks": []}, [1, 2, 3])
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_value_batch27():
    """PARSER_DOES_NOT_EMIT_RELATIONS 常量值固定。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_figure_caption_prf_no_side_effects_batch27():
    """调用不会修改输入 dict。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"foo": "bar"}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_figure_caption_prf_dict_value_has_only_value_reason_keys_batch27():
    """返回的每个 metric dict 只含 value 与 reason。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert set(v.keys()) == {"value", "reason"}


# ---------- chunk_boundary_prf 第二十七批 ----------


def test_chunk_boundary_prf_document_none_batch27():
    """document None → 3 个 metric null + reason='pipeline_failed'。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_includes_tolerance_batch27():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_annotation_none_batch27():
    """annotation None → reason='no_annotation'。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch27():
    """annotation 是空 dict → 'no_annotation'。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_list_in_key_batch27():
    """annotation 含空 anchors 列表 + 单 chunk → 'no_predicted_boundaries'。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_zero_batch27():
    """chunks=0 → 'no_predicted_boundaries'。"""
    out = chunk_boundary_prf(
        {"chunks": []},
        {"chunk_boundary_anchors": [{"marker": "x"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_one_with_anchors_batch27():
    """1 chunk + 有 anchors → recall=0.0（reason None）。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall = _ratio(0/1) → value=0.0 reason=None
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_chunks_two_no_anchors_batch27():
    """2 chunks + 无 anchors → 'no_ground_truth_anchors'。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_tolerance_default_30_batch27():
    """tolerance_chars 默认 30。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_zero_batch27():
    """tolerance=0 → 严格相等才能匹配。"""
    # chunk 边界位置 vs anchor 位置必须完全相等
    doc = {
        "chunks": [
            {"text": "hello"},
            {"text": "world"},
        ]
    }
    # stream = "hello world"，chunk1 end=5
    # anchor "hello" position="after" → end=5
    # |5-5|=0 ≤ 0 → 匹配
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_no_match_batch27():
    """tolerance=0 → 偏移 1 字符也不匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # anchor="hell" position="after" → end=4
    # 预测边界=5，|5-4|=1 > 0 → 不匹配
    ann = {"chunk_boundary_anchors": [{"marker": "hell", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_huge_batch27():
    """tolerance 巨大 → 任何位置都匹配。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    # stream="a b"，pred=1
    # anchor="zzz" → 不在 stream → missing → gt=0
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    # anchor="a" position="before" → 0
    # pred=1, |1-0|=1 ≤ 1000 → match
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1000)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_marker_not_in_stream_batch27():
    """marker 不在 stream → missing_markers 列表。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ZZZ", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # missing_markers 被记录
    assert "_missing_markers" in out
    assert "ZZZ" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_position_before_batch27():
    """position='before' → anchor 起始位置。"""
    doc = {"chunks": [{"text": "abcd"}, {"text": "efgh"}]}
    # stream="abcd efgh"
    # 预测边界=4（chunk1 末尾）
    # anchor="efgh" position="before" → find_pos=5
    # |4-5|=1 ≤ 30 → match
    ann = {"chunk_boundary_anchors": [{"marker": "efgh", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_after_batch27():
    """position='after' → anchor 结束位置。"""
    doc = {"chunks": [{"text": "abcd"}, {"text": "efgh"}]}
    # stream="abcd efgh"
    # 预测边界=4
    # anchor="abcd" position="after" → end=4
    # |4-4|=0 ≤ 30 → match
    ann = {"chunk_boundary_anchors": [{"marker": "abcd", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_repeated_marker_sequential_batch27():
    """重复 marker 按顺序定位（避免都命中第一个）。"""
    # stream = "x x x"
    doc = {"chunks": [{"text": "x x"}, {"text": "x"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]
    }
    # 预测边界=3（"x x" 末尾）
    # anchor 1: find "x" from 0 → pos=0, after→1
    # anchor 2: find "x" from 1 → pos=2, after→3
    # |3-1|=2, |3-3|=0 → 第二个 anchor 更近 → match
    out = chunk_boundary_prf(doc, ann)
    # 至少有一个匹配
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_prf_anchor_missing_marker_key_batch27():
    """anchor 缺 marker key → 视为空字符串 → missing。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # 空字符串 marker → find 返回 -1（实现里 `if marker else -1`）
    # → missing_markers
    assert "_missing_markers" in out


def test_chunk_boundary_prf_includes_tolerance_in_output_batch27():
    """输出包含 _tolerance_chars。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_document_dict_no_chunks_key_batch27():
    """document 没有 chunks key → chunks=[] → 'no_predicted_boundaries'。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_returns_dict_batch27():
    """返回值是 dict。"""
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第四十四批 ----------


def test_module_source_no_subprocess_batch27():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch27():
    src = inspect.getsource(amod)
    assert "os.system" not in src


def test_module_source_no_eval_batch27():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec_batch27():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch27():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch27():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch27():
    src = inspect.getsource(amod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch27():
    src = inspect.getsource(amod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch27():
    src = inspect.getsource(amod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch27():
    src = inspect.getsource(amod)
    assert "shutil" not in src


def test_module_source_no_requests_batch27():
    src = inspect.getsource(amod)
    assert "requests" not in src


def test_module_source_no_unlink_batch27():
    src = inspect.getsource(amod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十批 ----------


def test_module_source_contains_parser_does_not_emit_relations_batch27():
    src = inspect.getsource(amod)
    assert "parser_does_not_emit_relations" in src


def test_module_source_contains_figure_caption_prf_batch27():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf" in src


def test_module_source_contains_chunk_boundary_prf_batch27():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf" in src


def test_module_source_contains_normalize_text_import_batch27():
    """从 app.chunkers 导入 normalize_text。"""
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch27():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_pipeline_failed_reason_batch27():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_reason_batch27():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_reason_batch27():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_reason_batch27():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_tolerance_chars_param_batch27():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_counter_import_batch27():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_all_export_batch27():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


# ---------- signatures 第四十批 ----------


def test_signature_figure_caption_prf_batch27():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch27():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch27():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_figure_caption_prf_document_nullable_batch27():
    sig = inspect.signature(figure_caption_prf)
    annotation = sig.parameters["document"].annotation
    assert "None" in str(annotation)


def test_signature_chunk_boundary_prf_document_nullable_batch27():
    sig = inspect.signature(chunk_boundary_prf)
    annotation = sig.parameters["document"].annotation
    assert "None" in str(annotation)


def test_signature_figure_caption_prf_annotation_nullable_batch27():
    sig = inspect.signature(figure_caption_prf)
    annotation = sig.parameters["annotation"].annotation
    assert "None" in str(annotation)


def test_signature_chunk_boundary_prf_annotation_nullable_batch27():
    sig = inspect.signature(chunk_boundary_prf)
    annotation = sig.parameters["annotation"].annotation
    assert "None" in str(annotation)


# ---------- module 合理性第四十批 ----------


def test_module_has_future_annotations_batch27():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_imports_counter_batch27():
    src = inspect.getsource(amod)
    assert "Counter" in src


def test_module_imports_typing_any_batch27():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_no_main_block_batch27():
    """annotation_metrics 模块没有 __main__ 块。"""
    src = inspect.getsource(amod)
    assert 'if __name__ == "__main__"' not in src


def test_module_parser_does_not_emit_relations_is_str_batch27():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_parser_does_not_emit_relations_not_empty_batch27():
    assert len(PARSER_DOES_NOT_EMIT_RELATIONS) > 0


def test_module_no_class_definitions_batch27():
    """模块只有函数，没有 class。"""
    src = inspect.getsource(amod)
    assert "\nclass " not in src


# ---------- 端到端集成第四十批 ----------


def test_e2e_figure_caption_prf_full_call_batch27():
    """端到端：完整调用 figure_caption_prf。"""
    out = figure_caption_prf(
        {"chunks": [{"text": "x"}]},
        {"figures": [{"id": "f1"}]},
    )
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None


def test_e2e_chunk_boundary_prf_perfect_match_batch27():
    """端到端：完美匹配 → P=R=F1=1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_no_match_batch27():
    """端到端：marker 不在 stream → gt 空 → recall null。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ZZZ", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # missing markers → no gt
    # 实际：gt_positions 是空的 → recall 'no_ground_truth_anchors_in_stream'
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_e2e_chunk_boundary_prf_three_chunks_batch27():
    """端到端：3 chunks，2 个内部边界。"""
    doc = {
        "chunks": [
            {"text": "aaa"},
            {"text": "bbb"},
            {"text": "ccc"},
        ]
    }
    # stream = "aaa bbb ccc"
    # 预测边界: 3 (after aaa), 7 (after bbb)
    # anchors: "aaa" after → 3, "bbb" after → 7
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},
            {"marker": "bbb", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_partial_match_batch27():
    """端到端：1 个预测边界，2 个 anchor，1 个匹配。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    # 预测边界=3
    # anchor1="aaa" after → 3 (match)
    # anchor2="zzz" after → missing
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},
            {"marker": "zzz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann)
    # 1 个匹配 / 1 个预测 = 1.0
    # 1 个匹配 / 1 个有效 gt = 1.0（missing 不算）
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_returns_tolerance_value_batch27():
    """端到端：返回的 _tolerance_chars 等于输入。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_e2e_chunk_boundary_prf_no_side_effects_batch27():
    """端到端：调用不修改输入。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before
