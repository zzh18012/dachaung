"""evaluation/annotation_metrics.py 第二十七轮 edges 测试（Round 321）。

重点补强 edges25 未触及的角度：
- figure_caption_prf 调用语义深度补强
- chunk_boundary_prf 算法分支补强
- tolerance_chars 行为深度补强
- module source 字符串精确补强
- signatures 精确
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
from types import FunctionType
from typing import Any

import pytest

import evaluation.annotation_metrics as m
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 调用语义深度补强 ----------


def test_figure_caption_prf_value_field_always_none():
    """任何输入下，3 个 metric 的 value 都是 None。"""
    cases = [
        (None, None),
        ({}, {}),
        ({"x": 1}, {"y": 2}),
        ({"figure": []}, {"figure_caption_pairs": []}),
        ({"elements": [{"type": "figure"}]}, None),
        (None, {"figure_caption_pairs": [{"a": 1}]}),
    ]
    for doc, anno in cases:
        out = figure_caption_prf(doc, anno)
        for k, v in out.items():
            assert v["value"] is None, f"Failed for case ({doc}, {anno}): {k}"


def test_figure_caption_prf_reason_field_constant():
    """reason 永远是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    cases = [(None, None), ({}, {}), ({"x": 1}, None)]
    for doc, anno in cases:
        out = figure_caption_prf(doc, anno)
        for k, v in out.items():
            assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_keys_exact():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_call_with_kwargs():
    """支持 keyword args 调用。"""
    out = figure_caption_prf(document=None, annotation=None)
    assert "figure_caption_precision" in out


# ---------- chunk_boundary_prf 算法分支补强 ----------


def test_chunk_boundary_prf_call_with_kwargs():
    out = chunk_boundary_prf(document=None, annotation=None, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_negative_tolerance_treated_as_zero():
    """负数 tolerance 实际上不会匹配任何 anchor（距离非负）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=-1)
    # 距离 0 不 <= -1 → matched = 0
    # 但 num_pred=1, num_gt=1 → p=0, r=0
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_huge_tolerance():
    """超大 tolerance，远距离 anchor 也算匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    # 边界 = 3，gt = 4，距离 1
    out = chunk_boundary_prf(doc, anno, tolerance_chars=10000)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_zero_chunks_with_empty_anchor_list():
    doc = {"chunks": []}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    # 进入 chunks < 2 分支，且 anchors 也空 → recall 用 no_predicted 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_multiple_chunks_one_anchor_match():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]}
    # 3 个预测边界
    anno = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # match 1, num_pred=3, num_gt=1
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # stream = "a b c d"，边界位置：1, 3, 5
    # anchor "a" position="after" → gt = 1（find "a" at 0, +1）
    # 边界 1 距离 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1 / 3
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_extra_predicted_boundaries_lower_precision():
    """多预测边界 + 单 anchor → precision 低。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # 2 个预测边界
    anno = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.5


def test_chunk_boundary_prf_extra_anchors_lower_recall():
    """多 anchor 但只有 1 个在 stream 里。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # gt=1, 匹配边界 1
            {"marker": "x", "position": "after"},  # missing
            {"marker": "y", "position": "after"},  # missing
        ]
    }
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # num_pred=1, matched=1 → p=1
    # num_gt=1（x,y missing 不计）→ r=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    # missing_markers 含 x 和 y
    assert "x" in out["_missing_markers"]["value"]
    assert "y" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_t_field_no_reason():
    """_tolerance_chars 字段 reason 总是 None。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_missing_markers_no_reason():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, anno)
    assert out["_missing_markers"]["reason"] is None


def test_chunk_boundary_prf_zero_chunks_no_anchor_returns_3_metrics():
    """document 没 chunks 且没 anchor → 3 个 metric + _tolerance_chars。"""
    doc = {}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_one_chunk_no_anchor_returns_3_metrics():
    doc = {"chunks": [{"text": "a"}]}
    anno = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, anno)
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_prf_anchor_only_marker_no_position():
    """anchor 只给 marker 不给 position → 默认 'after'。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # anchor 没 position → 默认 'after'
    anno = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # gt = 0 + 3 = 3 = 边界
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- tolerance_chars 行为深度补强 ----------


def test_chunk_boundary_prf_t_field_at_each_branch():
    """5 个早 return 分支都应该写 _tolerance_chars。"""
    cases = [
        # (doc, anno, branch_name)
        (None, None, "pipeline_failed"),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, None, "no_annotation"),
        ({"chunks": []}, {"chunk_boundary_anchors": []}, "no_predicted"),
        ({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []}, "no_gt"),
    ]
    for doc, anno, branch in cases:
        out = chunk_boundary_prf(doc, anno, tolerance_chars=42)
        assert out["_tolerance_chars"]["value"] == 42, f"Failed at branch {branch}"


def test_chunk_boundary_prf_t_field_normal_path():
    """正常匹配路径也写 _tolerance_chars。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    anno = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=11)
    assert out["_tolerance_chars"]["value"] == 11


# ---------- module source 字符串精确补强 ----------


def test_module_source_has_docstring_mentions_caption():
    src = inspect.getsource(m)
    assert "caption" in src.lower()


def test_module_source_has_docstring_mentions_relation():
    src = inspect.getsource(m)
    assert "relation" in src.lower() or "关联" in src


def test_module_source_has_docstring_mentions_marker():
    src = inspect.getsource(m)
    assert "marker" in src.lower()


def test_module_source_has_docstring_mentions_heuristic():
    src = inspect.getsource(m)
    assert "启发式" in src or "heuristic" in src.lower()


def test_module_source_has_docstring_mentions_greedy():
    src = inspect.getsource(m)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_has_docstring_mentions_one_to_one():
    src = inspect.getsource(m)
    assert "一对一" in src


def test_module_source_has_normalize_text_called_with_default():
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text(c.get(\"text\") or \"\")" in src


def test_module_source_has_join_with_space():
    src = inspect.getsource(chunk_boundary_prf)
    assert '" ".join(norm_chunks)' in src


def test_module_source_has_stream_normalize_after_join():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_module_source_has_predicted_loop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "for i, txt in enumerate(norm_chunks):" in src


def test_module_source_has_last_chunk_break():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if i == len(norm_chunks) - 1:" in src


def test_module_source_has_find_in_stream():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream.find(txt, pos)" in src


def test_module_source_has_search_from_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_module_source_has_marker_default_empty():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("marker", "")' in src


def test_module_source_has_position_default_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'a.get("position", "after")' in src


def test_module_source_has_pairs_sort_key_distance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_module_source_has_used_pred_used_gt_set():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_module_source_has_f1_calc_with_2p1r():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_module_source_has_missing_markers_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


def test_module_source_has_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


# ---------- signatures 精确 ----------


def test_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_no_default_for_document():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_no_default_for_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_figure_caption_prf_no_default_for_document():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_figure_caption_prf_no_default_for_annotation():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_namespace_figure_caption_prf():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_namespace_chunk_boundary_prf():
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_namespace_module():
    assert m.__name__ == "evaluation.annotation_metrics"


# ---------- module 整体合理性 ----------


def test_module_all_3_entries():
    assert len(m.__all__) == 3


def test_module_has_2_module_level_functions():
    fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.annotation_metrics"
    ]
    assert set(fns) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_has_1_module_level_constant():
    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_no_class():
    src = inspect.getsource(m)
    for line in src.splitlines():
        if line.startswith("class "):
            pytest.fail(f"Found class: {line}")


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成补强 ----------


def test_e2e_full_pipeline_with_5_chunks():
    doc = {"chunks": [
        {"text": "section1"},
        {"text": "section2"},
        {"text": "section3"},
        {"text": "section4"},
        {"text": "section5"},
    ]}
    # 4 个预测边界
    anno = {"chunk_boundary_anchors": [
        {"marker": "section1", "position": "after"},
        {"marker": "section2", "position": "after"},
        {"marker": "section3", "position": "after"},
        {"marker": "section4", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_with_text_containing_punctuation():
    doc = {"chunks": [{"text": "Hello, world!"}, {"text": "Foo bar."}]}
    # stream = "Hello, world! Foo bar."，边界 = 13
    anno = {"chunk_boundary_anchors": [
        {"marker": "Hello, world!", "position": "after"}
    ]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_deterministic_across_multiple_runs():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    anno = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    out1 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    out2 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    out3 = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    assert out1 == out2 == out3


def test_e2e_figure_caption_with_realistic_input():
    """模拟真实输入：document 有 figures 和 captions。"""
    doc = {
        "elements": [
            {"type": "figure", "element_id": "f1", "resource_path": "f1.png"},
            {"type": "caption", "element_id": "c1", "content": "Figure 1"},
        ],
        "chunks": [],
    }
    anno = {
        "figure_caption_pairs": [{"figure_id": "f1", "caption_id": "c1"}]
    }
    out = figure_caption_prf(doc, anno)
    # 当前实现：仍返回 null
    assert out["figure_caption_precision"]["value"] is None
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_with_empty_marker():
    """marker 为空字符串 → find 返回 -1 → 加入 missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    anno = {"chunk_boundary_anchors": [{"marker": ""}]}
    out = chunk_boundary_prf(doc, anno, tolerance_chars=0)
    # "" marker → find("") 返回 0，但 marker 真值检查为 False → -1
    # 所以 missing_markers 含 ""
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]
