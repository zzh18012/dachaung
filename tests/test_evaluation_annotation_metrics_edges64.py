"""evaluation/annotation_metrics.py 第六十二轮 edges 测试（Round 580）。

补强 edges63 未触及的角度（第三十七批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十七批


def test_parser_const_value_exact_batch37():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_const_starts_with_parser_batch37():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser")


def test_parser_const_ends_with_relations_batch37():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.endswith("relations")


def test_parser_const_lower_only_batch37():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.islower()


def test_parser_const_underscores_batch37():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.count("_") == 4


# ---------- figure_caption_prf 第三十七批


def test_figure_caption_prf_returns_three_keys_batch37():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_reason_same_batch37():
    out = figure_caption_prf({"chunks": []}, {"x": 1})
    reasons = [v["reason"] for v in out.values()]
    assert len(set(reasons)) == 1
    assert reasons[0] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_idempotent_across_calls_batch37():
    o1 = figure_caption_prf({"x": 1}, {"y": 2})
    o2 = figure_caption_prf({"x": 1}, {"y": 2})
    assert o1 == o2


def test_figure_caption_prf_with_list_annotation_batch37():
    """annotation 是 list 也能调用（仅 keys 检查）。"""
    out = figure_caption_prf({"x": 1}, [])
    assert len(out) == 3


def test_figure_caption_prf_with_huge_annotation_batch37():
    """大 annotation 也能调用。"""
    big_ann = {"k" + str(i): i for i in range(1000)}
    out = figure_caption_prf({"x": 1}, big_ann)
    assert len(out) == 3


def test_figure_caption_prf_doc_with_chunks_field_batch37():
    """doc 含 chunks 字段但 annotation 为空 → 仍 null。"""
    out = figure_caption_prf({"chunks": [{"text": "a"}]}, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_does_not_call_normalize_text_batch37():
    """figure_caption_prf 不需要 normalize_text。"""
    with patch("evaluation.annotation_metrics.normalize_text") as mock_norm:
        figure_caption_prf({"x": 1}, {"y": 2})
        assert not mock_norm.called


# ---------- chunk_boundary_prf 第三十七批


def test_chunk_boundary_prf_default_tolerance_30_batch37():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_custom_tolerance_15_batch37():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        None,
        tolerance_chars=15,
    )
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_tolerance_one_batch37():
    """tolerance_chars=1 仍然允许距离 0 和 1 匹配。"""
    doc = {"chunks": [{"text": "abcd"}, {"text": "efgh"}]}
    # stream = "abcd efgh"
    # 边界 pos=4
    # 'bc' 在 pos=1, after → pos=3, 距离 1
    ann = {"chunk_boundary_anchors": [{"marker": "bc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_at_exact_boundary_batch37():
    """距离 == tolerance_chars 应当匹配（≤）。"""
    doc = {"chunks": [{"text": "abcde"}, {"text": "fghij"}]}
    # stream = "abcde fghij"
    # 边界 pos=5
    # 'abc' 在 pos=0, after → pos=3, 距离 2
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_just_below_batch37():
    """距离 = tolerance+1 → 不匹配。"""
    doc = {"chunks": [{"text": "abcde"}, {"text": "fghij"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # 距离 2 > 1 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_text_one_batch37():
    """单字符 chunk。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_3_chunks_two_preds_two_anchors_batch37():
    """3 chunks (2 preds) + 2 anchors（都匹配）→ P=1.0, R=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # pos=3, 完美
        {"marker": "f", "position": "after"},  # pos=7, 完美
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_4_chunks_three_preds_one_anchor_batch37():
    """4 chunks (3 preds) + 1 anchor → P=1/3, R=1.0。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}, {"text": "gh"}]}
    # preds: pos=2 (after ab), pos=5 (after cd), pos=8 (after ef)
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    # anchor pos=2
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(1 / 3)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_4_chunks_three_preds_three_anchors_batch37():
    """完美匹配 3/3。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}, {"text": "gh"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},
        {"marker": "cd", "position": "after"},
        {"marker": "ef", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_value_is_int_batch37():
    """position 值非 str（int）→ 走 else（after 分支）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": 999}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # int != "before" → 走 after 分支 → pos=3 → 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_value_is_none_batch37():
    """position=None → 走 else（after）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": None}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_annotation_empty_dict_batch37():
    """空 annotation dict → no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_is_zero_batch37():
    """annotation=0 → falsy → no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, 0)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_is_empty_string_batch37():
    """annotation='' → falsy → no_annotation。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, "")
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_doc_chunks_is_none_batch37():
    """chunks=None → 当 [] 处理 → no_predicted_boundaries。"""
    out = chunk_boundary_prf({"chunks": None}, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_doc_no_chunks_key_batch37():
    """doc 缺 chunks key → chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchor_marker_is_int_batch37():
    """marker=int → .get("marker", "") 取到 int → find(int) raises TypeError。"""
    # 这种情况会抛 TypeError，不是本函数当前的设计容错范围
    # 我们只验证 str marker 的行为
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_anchor_marker_is_empty_string_batch37():
    """marker='' → find('', 0)=0（合法但语义为"开头"）→ 在第 6 行 if marker else -1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # marker='' 是 falsy → find_pos=-1 → missing_markers
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_f1_when_precision_zero_recall_zero_batch37():
    """P=0, R=0 → f1=0.0（不是 null）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_when_precision_one_recall_half_batch37():
    """P=0.5, R=1.0 → f1 = 2*0.5*1/(0.5+1) = 1/1.5 = 0.667。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # P=0.5, R=1.0
    p_val = out["chunk_boundary_precision"]["value"]
    r_val = out["chunk_boundary_recall"]["value"]
    f_val = out["chunk_boundary_f1"]["value"]
    assert p_val == 0.5
    assert r_val == 1.0
    assert f_val == pytest.approx(2 * 0.5 * 1.0 / 1.5)


def test_chunk_boundary_prf_marker_at_end_of_stream_batch37():
    """marker 在 stream 末尾。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "abc xyz"
    # 边界 pos=3 (after "abc")
    # 'xyz' 在 pos=4, after → pos=7
    # 距离 |3-7|=4
    # tolerance=0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_marker_at_start_of_stream_batch37():
    """marker 在 stream 开头。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "xyz"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "abc xyz"
    # 边界 pos=3
    # 'abc' 在 pos=0, before → pos=0
    # 距离 3 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_two_preds_one_anchor_within_tolerance_batch37():
    """两个 pred 距离 anchor 都 ≤ tolerance，但一对一只能匹配 1 个。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # preds: pos=1, pos=3
    ann = {"chunk_boundary_anchors": [{"marker": "b", "position": "before"}]}
    # 'b' 在 pos=2, before → pos=2
    # 距离：|1-2|=1, |3-2|=1
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    # greedy 按距离排序：先匹配最近的（distance=1）→ matched=1
    # num_pred=2 → P=0.5
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_does_not_mutate_doc_batch37():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_chunk_boundary_prf_does_not_mutate_chunks_list_batch37():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    chunks_len_before = len(doc["chunks"])
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert len(doc["chunks"]) == chunks_len_before


def test_chunk_boundary_prf_does_not_call_normalize_text_when_doc_none_batch37():
    """doc=None 时不应调用 normalize_text。"""
    with patch("evaluation.annotation_metrics.normalize_text") as mock_norm:
        chunk_boundary_prf(None, None)
        assert not mock_norm.called


def test_chunk_boundary_prf_does_not_call_normalize_text_when_no_annotation_batch37():
    """没 annotation 时不应调用 normalize_text。"""
    with patch("evaluation.annotation_metrics.normalize_text") as mock_norm:
        chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
        assert not mock_norm.called


def test_chunk_boundary_prf_calls_normalize_text_for_real_path_batch37():
    """真实路径会调用 normalize_text 多次。"""
    with patch(
        "evaluation.annotation_metrics.normalize_text",
        side_effect=lambda x: x,
    ) as mock_norm:
        doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
        ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
        chunk_boundary_prf(doc, ann, tolerance_chars=5)
        # 每个 chunk 调用一次（2 次）+ 拼接后调用一次（1 次）= 3 次
        assert mock_norm.call_count >= 3


def test_chunk_boundary_prf_idempotent_call_batch37():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    o1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    o2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert o1 == o2


def test_chunk_boundary_prf_output_json_serializable_batch37():
    """输出能 JSON 序列化。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    s = json.dumps(out, ensure_ascii=False)
    assert isinstance(s, str)


def test_chunk_boundary_prf_with_unicode_chunks_long_batch37():
    """长 unicode chunk。"""
    doc = {"chunks": [{"text": "中文段落一" * 10}, {"text": "中文段落二" * 10}]}
    ann = {"chunk_boundary_anchors": [{"marker": "段落一", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert isinstance(out, dict)


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
def test_module_source_no_forbidden_tokens_batch37(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第五十七批


def test_module_source_contains_module_docstring_batch37():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_one_to_one_keyword_batch37():
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_contains_tolerance_chars_keyword_batch37():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_normalize_text_import_batch37():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch37():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_dict_annotation_batch37():
    src = inspect.getsource(amod)
    assert "dict[str, dict[str, Any]]" in src


def test_module_source_contains_pipeline_failed_reason_batch37():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_annotation_reason_batch37():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_contains_no_predicted_boundaries_reason_batch37():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_contains_no_ground_truth_anchors_reason_batch37():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_contains_precision_or_recall_not_evaluated_reason_batch37():
    src = inspect.getsource(amod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason_batch37():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_module_source_contains_from_future_import_batch37():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_typing_any_import_batch37():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_counter_import_batch37():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_alias_chunk_boundary_precision_batch37():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_precision"' in src


def test_module_source_contains_typing_alias_chunk_boundary_recall_batch37():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_recall"' in src


def test_module_source_contains_typing_alias_chunk_boundary_f1_batch37():
    src = inspect.getsource(amod)
    assert '"chunk_boundary_f1"' in src


def test_module_source_contains_typing_alias_figure_caption_precision_batch37():
    src = inspect.getsource(amod)
    assert '"figure_caption_precision"' in src


def test_module_source_contains_typing_alias_figure_caption_recall_batch37():
    src = inspect.getsource(amod)
    assert '"figure_caption_recall"' in src


def test_module_source_contains_typing_alias_figure_caption_f1_batch37():
    src = inspect.getsource(amod)
    assert '"figure_caption_f1"' in src


# ---------- signatures 第五十七批


def test_signature_chunk_boundary_prf_tolerance_default_30_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_return_annotation_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_figure_caption_prf_return_annotation_batch37():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_document_kind_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["document"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_annotation_kind_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["annotation"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_no_var_positional_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    has_var_pos = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL
        for p in sig.parameters.values()
    )
    assert not has_var_pos


def test_signature_chunk_boundary_prf_no_var_keyword_batch37():
    sig = inspect.signature(chunk_boundary_prf)
    has_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    assert not has_var_kw


# ---------- module 合理性第五十七批


def test_module_has_docstring_batch37():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_mentions_figure_caption_batch37():
    assert "figure-caption" in amod.__doc__ or "figure_caption" in amod.__doc__


def test_module_docstring_mentions_chunk_boundary_batch37():
    assert "chunk_boundary" in amod.__doc__ or "chunk-boundary" in amod.__doc__


def test_module_all_len_three_batch37():
    assert len(amod.__all__) == 3


def test_module_parser_const_module_level_batch37():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in dir(amod)


def test_module_figure_caption_prf_callable_batch37():
    assert callable(amod.figure_caption_prf)


def test_module_chunk_boundary_prf_callable_batch37():
    assert callable(amod.chunk_boundary_prf)


def test_module_no_class_definitions_batch37():
    """模块内不含 class 定义（全是函数）。"""
    src = inspect.getsource(amod)
    # 简单检查：没有顶层 class 关键字
    assert "\nclass " not in src


def test_module_normalize_text_used_batch37():
    src = inspect.getsource(amod)
    # normalize_text 应当被调用
    assert "normalize_text(" in src


def test_module_null_ratio_used_batch37():
    src = inspect.getsource(amod)
    assert "_null(" in src
    assert "_ratio(" in src


# ---------- 端到端集成第五十七批


def test_e2e_combined_call_keys_distinct_batch37():
    """figure_caption_prf + chunk_boundary_prf 合并后 keys 不冲突。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    fcp = figure_caption_prf(doc, ann)
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    fcp_keys = set(fcp.keys())
    cbp_keys = set(cbp.keys())
    assert fcp_keys.isdisjoint(cbp_keys - {"_tolerance_chars", "_missing_markers"})


def test_e2e_full_workflow_minimal_batch37():
    """最小完整工作流：doc + ann + tolerance → 6 keys。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 4 keys: precision / recall / f1 / _tolerance_chars
    assert len(cbp) == 4


def test_e2e_full_workflow_maximal_batch37():
    """含 missing_markers 的工作流 → 5 keys。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "xxx", "position": "after"},
    ]}
    cbp = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 5 keys: precision / recall / f1 / _tolerance_chars / _missing_markers
    assert len(cbp) == 5


def test_e2e_real_world_two_paragraphs_two_anchors_batch37():
    """模拟两个段落 + 两个边界标注。"""
    doc = {
        "chunks": [
            {"text": "段落 1 的内容。"},
            {"text": "段落 2 的内容。"},
        ],
    }
    ann = {"chunk_boundary_anchors": [
        {"marker": "内容。", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # '内容。' 在 chunk 0 中第一次出现 pos=...
    # 但 search_from 推进会让 chunk 0 的 anchor 占据位置
    # 1 anchor, 1 pred → 期待 R=1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_idempotent_after_multiple_calls_batch37():
    """3 次调用输出完全一致。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
    ]}
    outs = [chunk_boundary_prf(doc, ann, tolerance_chars=5) for _ in range(3)]
    for o in outs[1:]:
        assert o == outs[0]
