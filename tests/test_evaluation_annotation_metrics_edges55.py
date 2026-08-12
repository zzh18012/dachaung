"""evaluation/annotation_metrics.py 第五十五轮 edges 测试（Round 518）。

补强 edges54 未触及的角度（第二十八批）：
- figure_caption_prf 第二十八批：document 是 list / annotation 是 set / 多次调用独立
- chunk_boundary_prf 第二十八批：5 chunks 4 边界 / position 非法 / marker 空 + position before / marker 含 unicode / annotation 含额外 key / chunks 含 text=None / 多 anchor 相同 marker 不丢失
- 模块 source forbidden tokens 第四十五批
- 模块 source 字符串精确补强第四十一批
- signatures 第四十一批
- module 合理性第四十一批
- 端到端集成第四十一批
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


# ---------- figure_caption_prf 第二十八批 ----------


def test_figure_caption_prf_document_list_batch28():
    """document 是 list（异常）→ 仍 null。"""
    out = figure_caption_prf([], None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_annotation_set_batch28():
    """annotation 是 set（异常）→ 仍 null。"""
    out = figure_caption_prf({"chunks": []}, set())
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_idempotent_batch28():
    """多次调用结果相同。"""
    out1 = figure_caption_prf({"chunks": []}, {"x": 1})
    out2 = figure_caption_prf({"chunks": []}, {"x": 1})
    assert out1 == out2


def test_figure_caption_prf_no_input_modification_batch28():
    """不修改输入。"""
    doc = {"chunks": [{"text": "x"}]}
    ann = {"foo": [1, 2, 3]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_figure_caption_prf_three_keys_only_batch28():
    """只返回 3 个 metric，不含其他。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_with_real_document_batch28():
    """含 chunks 的真实 document 也 null。"""
    doc = {
        "elements": [{"type": "image", "element_id": "i1"}],
        "chunks": [{"text": "x"}],
    }
    out = figure_caption_prf(doc, {"figures": [{"id": "f1"}]})
    for v in out.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 第二十八批 ----------


def test_chunk_boundary_prf_five_chunks_batch28():
    """5 chunks → 4 内部边界。"""
    doc = {
        "chunks": [
            {"text": "aaa"},
            {"text": "bbb"},
            {"text": "ccc"},
            {"text": "ddd"},
            {"text": "eee"},
        ]
    }
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},
            {"marker": "bbb", "position": "after"},
            {"marker": "ccc", "position": "after"},
            {"marker": "ddd", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_invalid_value_batch28():
    """position 是非法值（非 before/after）→ 当 after 处理（else 分支）。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "weird"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # position="weird" → else 分支 → find_pos + len(marker) = 0+3 = 3 = 预测边界 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_empty_marker_position_before_batch28():
    """空 marker + position before → find 返回 -1（实现 if marker else -1）。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out


def test_chunk_boundary_prf_unicode_marker_batch28():
    """unicode marker。"""
    doc = {"chunks": [{"text": "你好世界"}, {"text": "test"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "你好世界", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="你好世界 test"，预测边界=4（'你好世界' 末尾）
    # anchor="你好世界" after → 4
    # match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_annotation_extra_keys_ignored_batch28():
    """annotation 含额外 key 不影响。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {
        "chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}],
        "extra_key": "ignored",
        "another": [1, 2, 3],
    }
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_none_batch28():
    """chunk text=None → 当作空字符串。"""
    doc = {"chunks": [{"text": None}, {"text": "aaa"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # stream=" aaa"（normalize_text 把 None→""，然后 " ".join(["", "aaa"]) → " aaa" → normalize → " aaa"）
    # 实际：norm_chunks=["", "aaa"]，joined_raw=" aaa"，stream=normalize(" aaa")=" aaa"
    # 预测边界：chunk1 end=0（"" 末尾）→ 但 stream.find("", 0) 返回 0，end=0+0=0；跳过最后一个
    # chunk2 是最后，break
    # 实际 predicted=[0]
    # anchor="aaa" before → find_pos=1
    # |0-1|=1 ≤ 1 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_missing_position_key_batch28():
    """anchor 缺 position key → 默认 'after'。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # position 默认 'after' → end=3 = 预测边界
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_three_same_markers_batch28():
    """三个相同 marker 按顺序定位。"""
    doc = {"chunks": [{"text": "x x x"}, {"text": "y"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]
    }
    # stream="x x x y"
    # 预测边界: chunk1 末尾 = 5（"x x x" 长度）
    # anchor 1: find "x" from 0 → 0, after→1
    # anchor 2: find "x" from 1 → 2, after→3
    # anchor 3: find "x" from 3 → 4, after→5
    # |5-1|=4, |5-3|=2, |5-5|=0 → 取距离最近 → anchor 3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 1 个预测，最多匹配 1 个
    assert out["chunk_boundary_precision"]["value"] == 1.0
    # 3 个 anchor，匹配 1 个 → recall = 1/3
    assert abs(out["chunk_boundary_recall"]["value"] - 1.0 / 3.0) < 1e-9


def test_chunk_boundary_prf_doc_with_no_chunks_key_batch28():
    """document 没有 chunks key。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    # chunks=[] → 'no_predicted_boundaries'
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_anchor_matched_one_not_batch28():
    """两个 anchor，一个匹配，一个不在 stream。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "aaa", "position": "after"},  # 匹配
            {"marker": "zzz", "position": "after"},  # 不在 stream
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 1 个预测边界，匹配 1 个
    assert out["chunk_boundary_precision"]["value"] == 1.0
    # missing marker 不算 gt → 1/1 = 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_document_none_includes_missing_markers_key_absent_batch28():
    """document None → 不含 _missing_markers（早期返回）。"""
    out = chunk_boundary_prf(None, None)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_two_chunks_one_call_batch28():
    """简单 2-chunk 调用不抛。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "chunk_boundary_precision" in out


# ---------- module source forbidden tokens 第四十五批 ----------


def test_module_source_no_subprocess_batch28():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch28():
    src = inspect.getsource(amod)
    assert "os.system" not in src


def test_module_source_no_eval_batch28():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec_batch28():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch28():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch28():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch28():
    src = inspect.getsource(amod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch28():
    src = inspect.getsource(amod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch28():
    src = inspect.getsource(amod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch28():
    src = inspect.getsource(amod)
    assert "shutil" not in src


def test_module_source_no_requests_batch28():
    src = inspect.getsource(amod)
    assert "requests" not in src


def test_module_source_no_unlink_batch28():
    src = inspect.getsource(amod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十一批 ----------


def test_module_source_contains_module_docstring_batch28():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_parser_does_not_emit_constant_batch28():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_docstring_batch28():
    src = inspect.getsource(amod)
    assert "图表关联" in src


def test_module_source_contains_chunk_boundary_docstring_batch28():
    src = inspect.getsource(amod)
    assert "分块边界" in src


def test_module_source_contains_normalize_text_call_batch28():
    src = inspect.getsource(amod)
    assert "normalize_text" in src


def test_module_source_contains_pipeline_failed_batch28():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_batch28():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_batch28():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_batch28():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_batch28():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in src


def test_module_source_contains_precision_or_recall_not_evaluated_batch28():
    src = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in src


def test_module_source_contains_tolerance_chars_param_batch28():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


# ---------- signatures 第四十一批 ----------


def test_signature_figure_caption_prf_return_annotation_batch28():
    sig = inspect.signature(figure_caption_prf)
    # dict[str, dict[str, Any]]
    assert "dict[str, dict[str" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_return_annotation_batch28():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict[str, dict[str" in str(sig.return_annotation)


def test_signature_figure_caption_prf_document_annotation_batch28():
    sig = inspect.signature(figure_caption_prf)
    for p_name in ("document", "annotation"):
        annotation = sig.parameters[p_name].annotation
        assert "dict" in str(annotation)
        assert "None" in str(annotation)


def test_signature_chunk_boundary_prf_document_annotation_batch28():
    sig = inspect.signature(chunk_boundary_prf)
    annotation = sig.parameters["document"].annotation
    assert "dict" in str(annotation)
    assert "None" in str(annotation)


# ---------- module 合理性第四十一批 ----------


def test_module_has_future_annotations_batch28():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_imports_counter_batch28():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_typing_any_batch28():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text_batch28():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_ratio_batch28():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_all_export_three_entries_batch28():
    src = inspect.getsource(amod)
    for name in ['"PARSER_DOES_NOT_EMIT_RELATIONS"', '"figure_caption_prf"', '"chunk_boundary_prf"']:
        assert name in src


def test_module_no_class_definitions_batch28():
    src = inspect.getsource(amod)
    assert "\nclass " not in src


def test_module_parser_does_not_emit_relations_str_value_batch28():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- 端到端集成第四十一批 ----------


def test_e2e_chunk_boundary_prf_perfect_match_with_tolerance_batch28():
    """端到端：完美匹配含容差。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream="abc def"，预测边界=3
    # anchor "ab" after → 2，|3-2|=1 ≤ 5 → match
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_no_match_at_all_batch28():
    """端到端：anchor 都不在 stream。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "zzz", "position": "after"},
            {"marker": "yyy", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "_missing_markers" in out
    assert "zzz" in out["_missing_markers"]["value"]
    assert "yyy" in out["_missing_markers"]["value"]


def test_e2e_chunk_boundary_prf_multiple_chunks_multiple_anchors_batch28():
    """端到端：复杂场景。

    stream = "hello world foo bar"
    预测边界: 5 (after hello), 11 (after world), 15 (after foo)
    anchors: hello after → 5, foo before → 12
    tolerance=0: 只有 |5-5|=0 匹配 → P=1/3, R=1/2
    """
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}, {"text": "foo"}, {"text": "bar"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},  # 5
            {"marker": "foo", "position": "before"},  # 12
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 3 predicted, 1 match → precision=1/3
    assert abs(out["chunk_boundary_precision"]["value"] - 1.0 / 3.0) < 1e-9
    # 2 gt, 1 match → recall=1/2
    assert abs(out["chunk_boundary_recall"]["value"] - 0.5) < 1e-9


def test_e2e_chunk_boundary_prf_idempotent_batch28():
    """端到端：相同输入两次得到相同输出。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_e2e_chunk_boundary_prf_no_side_effects_batch28():
    """端到端：调用不修改输入。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_e2e_figure_caption_prf_with_real_call_batch28():
    """端到端：figure_caption_prf 完整调用。"""
    out = figure_caption_prf(
        {"elements": [{"type": "image", "caption_id": "c1"}]},
        {"figure_caption_relations": [{"figure_id": "f1", "caption_id": "c1"}]},
    )
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_prf_returns_tolerance_int_batch28():
    """端到端：_tolerance_chars 是 int。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert isinstance(out["_tolerance_chars"]["value"], int)
    assert out["_tolerance_chars"]["value"] == 42
