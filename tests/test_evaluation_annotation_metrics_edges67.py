"""evaluation/annotation_metrics.py 第六十五轮 edges 测试（Round 599）。

补强 edges66 未触及的角度（第四十三批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第四十三批


def test_parser_does_not_emit_relations_exact_value_batch43():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_no_spaces_batch43():
    assert " " not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_is_str_batch43():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_module_level_batch43():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_in_source_batch43():
    src = inspect.getsource(amod)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS = " in src


def test_parser_does_not_emit_relations_used_by_figure_caption_batch43():
    src = inspect.getsource(amod)
    # 在 figure_caption_prf 中被使用
    assert src.count("PARSER_DOES_NOT_EMIT_RELATIONS") >= 2  # 定义 + 使用


def test_parser_does_not_emit_relations_in_all_batch43():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_lowercase_batch43():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.islower()


# ---------- figure_caption_prf 第四十三批


def test_figure_caption_prf_callable_batch43():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_with_dict_document_batch43():
    out = figure_caption_prf({"document_id": "x"}, None)
    assert set(out.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    }


def test_figure_caption_prf_with_dict_annotation_batch43():
    out = figure_caption_prf(None, {"chunk_boundary_anchors": []})
    # annotation 不影响 figure_caption_*（永远 null）
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None


def test_figure_caption_prf_with_int_inputs_batch43():
    """非 dict 输入也接受（不强校验）。"""
    out = figure_caption_prf(42, 99)
    assert isinstance(out, dict)


def test_figure_caption_prf_with_list_inputs_batch43():
    out = figure_caption_prf([1, 2], [3, 4])
    assert isinstance(out, dict)


def test_figure_caption_prf_each_metric_value_none_batch43():
    out = figure_caption_prf({}, {})
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None


def test_figure_caption_prf_each_metric_reason_batch43():
    out = figure_caption_prf({}, {})
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_idempotent_batch43():
    out1 = figure_caption_prf({"a": 1}, {"b": 2})
    out2 = figure_caption_prf({"a": 1}, {"b": 2})
    assert out1 == out2


def test_figure_caption_prf_does_not_mutate_inputs_batch43():
    doc = {"document_id": "x"}
    ann = {"chunk_boundary_anchors": []}
    import json as _json
    before_doc = _json.dumps(doc, sort_keys=True)
    before_ann = _json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert _json.dumps(doc, sort_keys=True) == before_doc
    assert _json.dumps(ann, sort_keys=True) == before_ann


def test_figure_caption_prf_returns_three_keys_batch43():
    out = figure_caption_prf(None, None)
    assert len(out) == 3


def test_figure_caption_prf_no_extra_keys_batch43():
    out = figure_caption_prf({"x": 1}, None)
    assert set(out.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    }


def test_figure_caption_prf_reason_consistent_across_calls_batch43():
    """多次调用 reason 一致。"""
    r1 = figure_caption_prf({}, {})["figure_caption_precision"]["reason"]
    r2 = figure_caption_prf(None, None)["figure_caption_precision"]["reason"]
    assert r1 == r2 == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_signature_two_params_batch43():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_signature_return_dict_batch43():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- chunk_boundary_prf 第四十三批


def test_chunk_boundary_prf_callable_batch43():
    assert callable(chunk_boundary_prf)


def test_chunk_boundary_prf_document_none_pipeline_failed_batch43():
    """document=None → pipeline_failed reason。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_includes_tolerance_batch43():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_document_empty_dict_no_annotation_batch43():
    """document={} + annotation={} → no_annotation。"""
    out = chunk_boundary_prf({}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_list_batch43():
    """annotation=[]（falsy）→ no_annotation。"""
    out = chunk_boundary_prf({"chunks": []}, [])
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_zero_batch43():
    """annotation=0（falsy）→ no_annotation。"""
    out = chunk_boundary_prf({"chunks": []}, 0)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_with_anchors_batch43():
    """有 anchor 但没有 chunks → recall=0.0。"""
    out = chunk_boundary_prf(
        {"chunks": []},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_one_chunk_no_anchors_batch43():
    """1 个 chunk → 没有 internal boundary。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": []},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_no_anchors_batch43():
    """2 chunks + 无 anchors → no_ground_truth_anchors。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_two_chunks_two_anchors_perfect_match_batch43():
    """完美匹配 → P=R=F1=1.0。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},  # 末尾位置 5
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界位置：len("hello")=5
    # anchor: find_pos=0, position=after → 0+5=5 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch43():
    """position=before → anchor 起始位置。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "before"},  # stream="ab cd"，cd 起始=3
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界位置：len("ab")=2
    # anchor before "cd" 位置=3
    # |2-3|=1 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_position_before_with_tolerance_batch43():
    """position=before + tolerance=1 → 匹配。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "before"},  # 位置=3
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # 预测=2, gt=3, |2-3|=1 ≤ 1 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_unknown_position_defaults_to_after_batch43():
    """position="middle"（未识别）→ 走 else 分支（after）。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "middle"},  # 视为 after → 位置=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测=2, gt=2 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_empty_marker_skipped_batch43():
    """空 marker → find 返回 -1 → 跳过。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 没有 ground truth → no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_marker_not_in_stream_recorded_batch43():
    """marker 不在 stream 中 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_no_missing_markers_no_key_batch43():
    """没有 missing → 不加 _missing_markers 键。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_tolerance_zero_batch43():
    """tolerance=0 → 完美位置匹配才行。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 位置=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测=2, gt=2 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_negative_batch43():
    """tolerance=-1 → 任何距离都不匹配。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 位置=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # 距离 0 > -1（≤ -1 永远 false）→ 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_huge_batch43():
    """tolerance=10**6 → 总是匹配。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 位置=2
            {"marker": "cd", "position": "after"},  # 位置=5
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10**6)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_float_batch43():
    """tolerance=float → 仍能比较。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "before"},  # 位置=3
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1.5)
    # 预测=2, gt=3, |2-3|=1 ≤ 1.5 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_always_returns_tolerance_record_batch43():
    """所有路径都返回 _tolerance_chars。"""
    # pipeline_failed 路径
    out1 = chunk_boundary_prf(None, None)
    assert "_tolerance_chars" in out1
    # no_annotation 路径
    out2 = chunk_boundary_prf({}, {})
    assert "_tolerance_chars" in out2
    # no_predicted_boundaries 路径
    out3 = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    assert "_tolerance_chars" in out3
    # 主路径
    out4 = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    assert "_tolerance_chars" in out4


def test_chunk_boundary_prf_predicted_boundary_search_from_advances_batch43():
    """predicted 边界查找时 pos 推进。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "cd"}]}
    # stream = "ab ab cd"
    # 第一个 ab 末尾=2，第二个 ab 末尾=5
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 第一次出现末尾=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界=[2, 5]，gt=[2]
    # 匹配后 P=1/2=0.5, R=1/1=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_search_from_advances_for_anchors_batch43():
    """anchor 查找时 search_from 推进（两个相同 marker 各自定位）。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "cd"}]}
    # stream = "ab ab cd"
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 第一个 ab 末尾=2
            {"marker": "ab", "position": "after"},  # 第二个 ab 末尾=5
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界=[2, 5]，gt=[2, 5]
    # 一对一匹配 → matched=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_three_chunks_two_anchors_full_match_batch43():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}, {"text": "foo"}]}
    # stream = "hello world foo"
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},  # 末尾=5
            {"marker": "world", "position": "after"},  # 末尾=11
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_with_empty_text_batch43():
    """空 text chunk → 在 stream 中找空字符串 → find 返回 pos（不前进）。"""
    doc = {"chunks": [{"text": ""}, {"text": "ab"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 2 chunks 但第一个 text 空 → 边界位置=0
    # no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_with_whitespace_only_batch43():
    """纯空白 chunk text → normalize 后变空。"""
    doc = {"chunks": [{"text": "  "}, {"text": "ab"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_normalize_collapses_whitespace_batch43():
    """normalize_text 把多空格压成单空格。"""
    doc = {"chunks": [{"text": "a   b"}, {"text": "c"}]}
    # normalize("a   b") = "a b"
    # stream = normalize("a b c") = "a b c"
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "a b", "position": "after"},  # 末尾=3
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测边界：find("a b", 0)=0, end=3 → 边界=3
    # gt: find("a b", 0)=0, after → 3
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_p_zero_batch43():
    """P=0, R=1 → F1=0。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # stream="ab cd ef"，预测边界=[2, 5]
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after"},  # 末尾=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # matched=1, num_pred=2, num_gt=1
    # P=0.5, R=1.0, F1=2*0.5*1.0/1.5=0.667
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


def test_chunk_boundary_prf_f1_perfect_batch43():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_both_zero_batch43():
    """P=0 + R=0 → F1=0（denom=0 分支）。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    # 预测边界=[2]，anchor 在远处的位置（容差=0 不匹配）
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "after"},  # 末尾=5
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测=2, gt=5, |2-5|=3 > 0 → 不匹配
    # matched=0, num_pred=1, num_gt=1
    # P=0.0, R=0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_one_to_one_matching_batch43():
    """一对一：两个预测都最近同一 anchor，但 anchor 只能匹配一个。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # stream="a b c"，预测边界=[1, 3]
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # 位置=1
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # 预测=[1, 3], gt=[1]
    # pairs: (0, 0, 0), (2, 1, 0)
    # 排序后：(0,0,0) 先匹配 → used_pred={0}, used_gt={0}
    # (2,1,0) → gi=0 已用 → 跳过
    # matched=1, num_pred=2, num_gt=1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_idempotent_batch43():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert json.dumps(out1, sort_keys=True) == json.dumps(out2, sort_keys=True)


def test_chunk_boundary_prf_does_not_mutate_document_batch43():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    before = json.dumps(doc, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == before


def test_chunk_boundary_prf_does_not_mutate_annotation_batch43():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(ann, sort_keys=True) == before


def test_chunk_boundary_prf_signature_three_params_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_default_30_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_tolerance_annotation_int_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert "int" in str(sig.parameters["tolerance_chars"].annotation)


def test_chunk_boundary_prf_returns_dict_batch43():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunks_not_list_raises_batch43():
    """chunks 是字符串 + 非空 anchors → AttributeError（字符串字符没有 .get）。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            {"chunks": "abc"},
            {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
        )


def test_chunk_boundary_prf_returns_at_least_4_keys_batch43():
    """至少 4 个 key（3 metric + _tolerance_chars）。"""
    out = chunk_boundary_prf(None, None)
    assert len(out) >= 4


def test_chunk_boundary_prf_returns_at_most_5_keys_batch43():
    """至多 5 个 key（3 metric + _tolerance_chars + _missing_markers）。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert len(out) <= 5


def test_chunk_boundary_prf_missing_marker_value_is_list_batch43():
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out["_missing_markers"]["value"], list)


def test_chunk_boundary_prf_extra_anchor_keys_ignored_batch43():
    """anchor 含未知 key → 不影响。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab", "position": "after", "extra_key": "ignored", "weight": 0.5},
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_extra_document_keys_ignored_batch43():
    """document 含未知 key → 不影响。"""
    doc = {
        "chunks": [{"text": "ab"}, {"text": "cd"}],
        "document_id": "x",
        "source_type": "pdf",
        "elements": [],
        "parser_name": "fallback",
    }
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_default_marker_empty_batch43():
    """anchor 没有 marker key → 默认 ""。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"position": "after"},  # 无 marker
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # marker="" → find 返回 -1 → missing_markers=[""]
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == [""]


def test_chunk_boundary_prf_anchor_default_position_after_batch43():
    """anchor 没有 position key → 默认 "after"。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "ab"},  # 无 position → 默认 "after"
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测=2, gt=find_pos+2=2 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_unicode_marker_batch43():
    """中文 marker 也能匹配。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    # stream = "你好 世界"
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "你好", "position": "after"},  # 末尾=2
        ],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 预测=len("你好")=2, gt=2 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- module source forbidden tokens 第七十二批


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
def test_module_source_no_forbidden_tokens_batch43(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第六十八批


def test_module_source_contains_design_doc_batch43():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_future_annotations_batch43():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_collections_counter_import_batch43():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch43():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_normalize_text_import_batch43():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch43():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_figure_caption_function_batch43():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_function_batch43():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_parser_does_not_emit_relations_definition_batch43():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_no_predicted_boundaries_keyword_batch43():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_keyword_batch43():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_no_annotation_keyword_batch43():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_pipeline_failed_keyword_batch43():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_tolerance_chars_keyword_batch43():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_chunk_boundary_anchors_keyword_batch43():
    src = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in src


def test_module_source_contains_normalize_text_call_batch43():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_contains_all_export_batch43():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_contains_marker_keyword_batch43():
    src = inspect.getsource(amod)
    assert '"marker"' in src or "'marker'" in src


def test_module_source_contains_position_keyword_batch43():
    src = inspect.getsource(amod)
    assert '"position"' in src or "'position'" in src


def test_module_source_contains_before_after_keyword_batch43():
    src = inspect.getsource(amod)
    assert "before" in src
    assert "after" in src


def test_module_source_contains_search_from_keyword_batch43():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_contains_missing_markers_keyword_batch43():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_contains_precision_or_recall_not_evaluated_batch43():
    src = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_batch43():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in src


# ---------- signatures 第六十八批


def test_signature_figure_caption_params_batch43():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_signature_chunk_boundary_params_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_signature_figure_caption_return_annotation_batch43():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_boundary_return_annotation_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_figure_caption_document_annotation_dict_or_none_batch43():
    sig = inspect.signature(figure_caption_prf)
    ann_doc = str(sig.parameters["document"].annotation)
    ann_ann = str(sig.parameters["annotation"].annotation)
    assert "dict" in ann_doc and "None" in ann_doc
    assert "dict" in ann_ann and "None" in ann_ann


def test_signature_chunk_boundary_document_annotation_dict_or_none_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    ann_doc = str(sig.parameters["document"].annotation)
    ann_ann = str(sig.parameters["annotation"].annotation)
    assert "dict" in ann_doc and "None" in ann_doc
    assert "dict" in ann_ann and "None" in ann_ann


def test_signature_chunk_boundary_tolerance_int_annotation_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert "int" in str(sig.parameters["tolerance_chars"].annotation)


def test_signature_chunk_boundary_tolerance_default_30_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性 第六十八批


def test_module_has_all_attribute_batch43():
    assert hasattr(amod, "__all__")


def test_module_all_is_list_batch43():
    assert isinstance(amod.__all__, list)


def test_module_all_three_entries_batch43():
    assert len(amod.__all__) == 3


def test_module_all_contains_parser_constant_batch43():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_all_contains_figure_caption_batch43():
    assert "figure_caption_prf" in amod.__all__


def test_module_all_contains_chunk_boundary_batch43():
    assert "chunk_boundary_prf" in amod.__all__


def test_module_does_not_define_class_batch43():
    src = inspect.getsource(amod)
    assert "\nclass " not in src


def test_module_has_future_annotations_batch43():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_has_figure_caption_attr_batch43():
    assert hasattr(amod, "figure_caption_prf")


def test_module_has_chunk_boundary_attr_batch43():
    assert hasattr(amod, "chunk_boundary_prf")


def test_module_has_parser_does_not_emit_relations_attr_batch43():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_functions_callable_batch43():
    assert callable(amod.figure_caption_prf)
    assert callable(amod.chunk_boundary_prf)


def test_module_no_module_level_code_outside_functions_batch43():
    """AST：顶层只有 import / 常量 / function def / __all__。"""
    import ast
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.Expr))


# ---------- 端到端集成 第六十八批


def test_e2e_full_perfect_match_batch43():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 0
    assert "_missing_markers" not in out


def test_e2e_full_mismatch_batch43():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # marker 不在 stream → missing
    assert out["_missing_markers"]["value"] == ["xyz"]
    # 没有 gt → recall 是 null
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_e2e_json_serializable_output_batch43():
    """输出 JSON 可序列化。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    json.dumps(out)


def test_e2e_figure_caption_always_null_batch43():
    """figure_caption_prf 任何输入下都返回 null。"""
    for doc in [None, {}, {"x": 1}]:
        for ann in [None, {}, {"y": 2}]:
            out = figure_caption_prf(doc, ann)
            for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
                assert out[k]["value"] is None
                assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
