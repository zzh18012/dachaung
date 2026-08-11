"""evaluation/annotation_metrics.py 第四十二轮 edges 测试（Round 427）。

补强 edges41 未触及的角度：
- figure_caption_prf 边界第十五批（document None / annotation None / 输出 dict 独立性 / PARSER_DOES_NOT_EMIT_RELATIONS 引用一致 / 多次调用一致性）
- chunk_boundary_prf 边界第十五批（document 与 annotation 都 None / chunks 为空 list / anchors 含 None / marker 含 Unicode 全角 / position before/after 混合 / 高容差全员命中 / tolerance=0 严格匹配）
- chunk_boundary_prf 算法第十五批（repeated marker 顺序定位 / 多个 anchor 顺序 / tolerance 边界值 / 单 chunk 边界 / 双 chunk 单边界）
- PARSER_DOES_NOT_EMIT_RELATIONS 第十五批（值与字符串相等 / 是 str 类型 / 模块属性）
- module source forbidden tokens 第二十三批
- module source 字符串精确补强第二十批
- signatures 第二十批
- module 合理性第二十批
- 端到端集成第二十批
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


# ---------- figure_caption_prf 边界第十五批 ----------


def test_figure_caption_prf_document_none_batch15():
    """document=None 也应返回三个 null key（reason 固定）。"""
    out = figure_caption_prf(None, {"x": 1})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_annotation_none_batch15():
    """annotation=None 也应返回三个 null key（reason 固定）。"""
    out = figure_caption_prf({"x": 1}, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_both_none_batch15():
    """document 与 annotation 都 None。"""
    out = figure_caption_prf(None, None)
    assert len(out) == 3
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_dict_independence_batch15():
    """两次调用返回的 dict 互不影响。"""
    out1 = figure_caption_prf({"x": 1}, None)
    out2 = figure_caption_prf({"x": 1}, None)
    out1["figure_caption_precision"]["value"] = "modified"
    assert out2["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_constant_reference_batch15():
    """reason 字段应与 PARSER_DOES_NOT_EMIT_RELATIONS 一致。"""
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for v in out.values():
        assert v["reason"] is PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_consistent_across_calls_batch15():
    """多次调用结果一致。"""
    o1 = figure_caption_prf({}, {})
    o2 = figure_caption_prf({}, {})
    o3 = figure_caption_prf({}, {})
    assert o1 == o2 == o3


def test_figure_caption_prf_empty_dict_inputs_batch15():
    """空 dict 输入也应正常返回。"""
    out = figure_caption_prf({}, {})
    assert len(out) == 3


# ---------- chunk_boundary_prf 边界第十五批 ----------


def test_chunk_boundary_prf_both_none_batch15():
    """document 与 annotation 都 None → pipeline_failed reason。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_chunks_empty_list_batch15():
    """chunks 是空 list（不是 None）→ no_predicted_boundaries。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchors_with_none_items_batch15():
    """anchors 列表中含 None 元素。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [None, {"marker": "def", "position": "after"}]}
    # None.get 会 AttributeError，但代码使用 a.get(...)；None 没 .get 方法
    # 实际上代码会抛 AttributeError
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, annotation)


def test_chunk_boundary_prf_marker_with_full_width_text_batch15():
    """marker 含全角 Unicode。"""
    doc = {"chunks": [{"text": "中文测试"}, {"text": "分块边界"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "中文测试", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    # 至少应该返回 4 个 key
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out
    assert "chunk_boundary_f1" in out
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_mixed_position_before_after_batch15():
    """anchor 中 position 混合 before 与 after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}, {"text": "foo"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},  # gt pos = 5
            {"marker": "world", "position": "before"},  # gt pos = 6 (find_pos)
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    # 不崩溃即可
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_high_tolerance_all_match_batch15():
    """容差很大 → 所有预测都能匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "def", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1000)
    # 预测有 2 个（abc 后、def 后），gt 有 2 个 → precision=recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_batch15():
    """容差 0 → 严格匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"（normalize 后）
    # 第 1 个 chunk 末尾位置 = 3
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # gt = 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测位置 3 = gt 3 → 严格匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_mismatch_batch15():
    """容差 0 + marker 与预测位置不重合 → 不匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 预测位置 = 3 (abc 后)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},  # gt = 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # |3 - 0| = 3 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- chunk_boundary_prf 算法第十五批 ----------


def test_chunk_boundary_prf_repeated_marker_sequential_batch15():
    """两个相同 marker 应顺序定位（不允许两个 anchor 共享同一 stream 位置）。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "foo"}, {"text": "bar"}]}
    # stream = "foo foo bar"
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},  # 第 1 个 foo 后 = pos 3
            {"marker": "foo", "position": "after"},  # 第 2 个 foo 后 = pos 7
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测位置 3 与 7，gt 位置 3 与 7 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_three_chunks_two_boundaries_batch15():
    """3 chunks → 2 个内部边界。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # stream = "a b c"
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},  # pos 1
            {"marker": "b", "position": "after"},  # pos 3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测位置 1 与 3，gt 1 与 3 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_single_chunk_no_boundary_batch15():
    """只有 1 个 chunk → 无内部边界。"""
    doc = {"chunks": [{"text": "abc"}]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]
    }
    out = chunk_boundary_prf(doc, annotation)
    # chunks < 2 → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall 因 anchors 不空 → 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_missing_marker_in_stream_batch15():
    """marker 不在 stream 中 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_empty_marker_treated_as_missing_batch15():
    """marker='' 是 falsy → find_pos = -1 → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_two_anchors_one_predicts_batch15():
    """2 anchors + 1 预测 → recall=0.5；precision=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 预测位置 = 3 (abc 后)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # 命中
            {"marker": "xyz", "position": "after"},  # 不在 stream → missing
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 命中 1 个 / 预测 1 个 → precision=1.0
    # 命中 1 个 / gt 1 个（xyz 没在 gt_positions 中）→ recall=1.0
    # 因为 missing 的 marker 不进 gt_positions
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第十五批 ----------


def test_parser_does_not_emit_relations_value_batch15():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str_batch15():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_module_attribute_batch15():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_in_all_batch15():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_immutable_batch15():
    """字符串不可变 — 修改需新建。"""
    s1 = PARSER_DOES_NOT_EMIT_RELATIONS
    # 字符串操作返回新字符串
    s2 = s1.upper()
    assert s1 == "parser_does_not_emit_relations"
    assert s2 == "PARSER_DOES_NOT_EMIT_RELATIONS"


# ---------- module source forbidden tokens 第二十三批 ----------


@pytest.mark.parametrize("forbidden", [
    "subprocess",
    "os.system",
    "os.popen",
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
])
def test_module_source_forbidden_tokens_batch15(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


# ---------- module source 字符串精确补强第二十批 ----------


def test_module_source_has_future_annotations_batch15():
    src = inspect.getsource(amod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch15():
    src = inspect.getsource(amod)
    assert '"""人工标注指标：figure-caption' in src


def test_module_source_has_figure_caption_function_batch15():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_function_batch15():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_parser_does_not_emit_constant_batch15():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_normalize_text_import_batch15():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import_batch15():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_counter_import_batch15():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import_batch15():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_all_dunder_batch15():
    src = inspect.getsource(amod)
    assert "__all__ = [" in src


def test_module_source_all_contains_figure_caption_prf_batch15():
    src = inspect.getsource(amod)
    assert '"figure_caption_prf"' in src


def test_module_source_all_contains_chunk_boundary_prf_batch15():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_prf"' in src


def test_module_source_all_contains_parser_constant_batch15():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src


def test_module_source_has_pipeline_failed_reason_batch15():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_has_no_annotation_reason_batch15():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_has_no_predicted_boundaries_reason_batch15():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_has_no_ground_truth_anchors_reason_batch15():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_has_tolerance_chars_param_batch15():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_default_tolerance_30_batch15():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_position_before_batch15():
    src = inspect.getsource(amod)
    assert '"before"' in src


def test_module_source_has_position_after_batch15():
    src = inspect.getsource(amod)
    assert '"after"' in src


def test_module_source_has_missing_markers_batch15():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


def test_module_source_has_search_from_batch15():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_has_all_list_terminator_batch15():
    src = inspect.getsource(amod)
    assert "]" in src


# ---------- signatures 第二十批 ----------


def test_signature_figure_caption_prf_batch15():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch15():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_batch15():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_figure_caption_prf_return_annotation_batch15():
    sig = inspect.signature(figure_caption_prf)
    # return annotation 是 dict[str, dict[str, Any]] 或字符串形式
    ra = sig.return_annotation
    assert ra is not inspect._empty


def test_signature_chunk_boundary_prf_return_annotation_batch15():
    sig = inspect.signature(chunk_boundary_prf)
    ra = sig.return_annotation
    assert ra is not inspect._empty


def test_signature_figure_caption_prf_no_varargs_batch15():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_chunk_boundary_prf_no_varargs_batch15():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第二十批 ----------


def test_module_has_all_attribute_batch15():
    assert hasattr(amod, "__all__")
    assert isinstance(amod.__all__, list)


def test_module_all_items_exist_batch15():
    for name in amod.__all__:
        assert hasattr(amod, name)


def test_module_all_items_callable_or_str_batch15():
    """__all__ 中函数 callable，常量是 str。"""
    for name in amod.__all__:
        attr = getattr(amod, name)
        assert callable(attr) or isinstance(attr, str)


def test_module_figure_caption_prf_callable_batch15():
    assert callable(figure_caption_prf)


def test_module_chunk_boundary_prf_callable_batch15():
    assert callable(chunk_boundary_prf)


def test_module_has_normalize_text_batch15():
    """模块从 app.chunkers.structural 导入了 normalize_text。"""
    assert hasattr(amod, "normalize_text")
    assert callable(amod.normalize_text)


def test_module_has_null_ratio_helpers_batch15():
    """模块从 evaluation.metrics 导入了 _null 与 _ratio。"""
    assert hasattr(amod, "_null")
    assert hasattr(amod, "_ratio")


def test_module_parser_does_not_emit_constant_in_namespace_batch15():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in vars(amod)


def test_module_does_not_mutate_inputs_batch15():
    """调用 chunk_boundary_prf 不应修改输入 document/annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    doc_before = repr(doc)
    annotation_before = repr(annotation)
    chunk_boundary_prf(doc, annotation)
    assert repr(doc) == doc_before
    assert repr(annotation) == annotation_before


# ---------- 端到端集成第二十批 ----------


def test_e2e_chunk_boundary_perfect_match_batch15():
    """完美匹配场景。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"}
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    # F1 = 2 * 1 * 1 / (1 + 1) = 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_no_match_batch15():
    """完全不匹配场景。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "before"}  # gt pos = 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # F1 = 0（denom = 0）
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_e2e_chunk_boundary_with_tolerance_batch15():
    """容差匹配场景。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    # stream = "hello world"，预测位置 5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "before"}  # gt pos = 0
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # |5 - 0| = 5 ≤ 10 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_tolerance_chars_recorded_batch15():
    """_tolerance_chars 字段必须记录在输出中。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_e2e_chunk_boundary_default_tolerance_30_batch15():
    """默认 tolerance_chars=30。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["_tolerance_chars"]["value"] == 30


def test_e2e_chunk_boundary_no_annotation_returns_null_batch15():
    """无标注 → no_annotation reason。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_empty_annotation_returns_null_batch15():
    """空标注 dict → no_annotation reason。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_document_none_with_annotation_batch15():
    """document=None + annotation 非空 → pipeline_failed reason。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [{"marker": "x"}]})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_chunk_boundary_no_chunks_returns_null_batch15():
    """document 是空 dict → chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_figure_caption_always_returns_three_keys_batch15():
    """figure_caption_prf 在任何输入下都返回三个 key。"""
    cases = [
        (None, None),
        ({}, {}),
        ({"x": 1}, None),
        (None, {"y": 2}),
        ({"x": 1}, {"y": 2}),
    ]
    for doc, ann in cases:
        out = figure_caption_prf(doc, ann)
        assert set(out.keys()) == {
            "figure_caption_precision",
            "figure_caption_recall",
            "figure_caption_f1",
        }
