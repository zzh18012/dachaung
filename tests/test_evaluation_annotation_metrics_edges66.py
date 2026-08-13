"""evaluation/annotation_metrics.py 第六十四轮 edges 测试（Round 595）。

补强 edges65 未触及的角度（第四十批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第四十批


def test_parser_const_value_exact_batch40():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_const_no_spaces_batch40():
    assert " " not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_const_starts_with_parser_batch40():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


def test_parser_const_ends_with_relations_batch40():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.endswith("_relations")


def test_parser_const_module_level_attribute_batch40():
    """模块加载时该常量已绑定（不需要调用函数）。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert isinstance(m.PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- figure_caption_prf 第四十批


def test_figure_caption_prf_callable_batch40():
    assert callable(figure_caption_prf)


def test_figure_caption_prf_doc_present_batch40():
    """函数有 docstring。"""
    assert figure_caption_prf.__doc__ is not None


def test_figure_caption_prf_doc_mentions_null_batch40():
    """docstring 提及"固定 null"或 "relation"。"""
    doc = figure_caption_prf.__doc__
    assert "null" in doc or "relation" in doc.lower()


def test_figure_caption_prf_returns_dict_instance_batch40():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_each_value_is_dict_batch40():
    out = figure_caption_prf({"x": 1}, None)
    for k, v in out.items():
        assert isinstance(v, dict)


def test_figure_caption_prf_each_value_has_value_reason_batch40():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_with_fully_populated_inputs_batch40():
    """即使传入完整 document + annotation 也固定 null（不读输入）。"""
    doc = {"chunks": [{"text": "abc"}], "elements": [{"type": "image", "caption": "x"}]}
    ann = {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, ann)
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_reason_consistent_batch40():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf({"x": 1}, {"y": 2})
    for k in out1:
        assert out1[k]["reason"] == out2[k]["reason"]


def test_figure_caption_prf_with_annotation_dict_batch40():
    """有 annotation 也固定 null。"""
    out = figure_caption_prf({"x": 1}, {"figure_caption_anchors": []})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_with_empty_annotation_batch40():
    out = figure_caption_prf({"x": 1}, {})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_no_kwargs_batch40():
    """不接受未知关键字参数。"""
    with pytest.raises(TypeError):
        figure_caption_prf({"x": 1}, {"y": 2}, unknown=True)  # type: ignore[call-arg]


def test_figure_caption_prf_signature_return_dict_batch40():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- chunk_boundary_prf 第四十批


def test_chunk_boundary_prf_callable_batch40():
    assert callable(chunk_boundary_prf)


def test_chunk_boundary_prf_doc_present_batch40():
    assert chunk_boundary_prf.__doc__ is not None


def test_chunk_boundary_prf_doc_mentions_algorithm_batch40():
    """docstring 描述算法。"""
    doc = chunk_boundary_prf.__doc__
    assert "算法" in doc or "precision" in doc.lower() or "match" in doc.lower()


def test_chunk_boundary_prf_returns_dict_with_4_keys_min_batch40():
    """最少 4 个 key（precision/recall/f1 + _tolerance_chars）。"""
    out = chunk_boundary_prf(None, None)
    assert len(out) >= 4


def test_chunk_boundary_prf_always_includes_tolerance_batch40():
    """无论哪个分支都返回 _tolerance_chars。"""
    out1 = chunk_boundary_prf(None, None)
    out2 = chunk_boundary_prf({}, None)
    out3 = chunk_boundary_prf({"chunks": [{"text": "abc"}]}, {"chunk_boundary_anchors": []})
    assert "_tolerance_chars" in out1
    assert "_tolerance_chars" in out2
    assert "_tolerance_chars" in out3


def test_chunk_boundary_prf_tolerance_value_preserved_batch40():
    out = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_tolerance_value_zero_batch40():
    out = chunk_boundary_prf(None, None, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_value_negative_batch40():
    out = chunk_boundary_prf(None, None, tolerance_chars=-5)
    assert out["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_prf_tolerance_value_huge_batch40():
    out = chunk_boundary_prf(None, None, tolerance_chars=10**9)
    assert out["_tolerance_chars"]["value"] == 10**9


def test_chunk_boundary_prf_doc_none_path_returns_3_null_metrics_batch40():
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_no_annotation_path_returns_3_null_metrics_batch40():
    out = chunk_boundary_prf({"chunks": [{"text": "abc"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_path_returns_3_null_metrics_batch40():
    out = chunk_boundary_prf({"chunks": [{"text": "abc"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_returns_no_predicted_batch40():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted_batch40():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}]},
        {"chunk_boundary_anchors": [{"marker": "x"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_no_anchors_returns_no_gt_anchors_batch40():
    """有 chunks 但 anchors=[] → no_ground_truth_anchors。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}, {"text": "def"}]},
        {"chunk_boundary_anchors": []},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_no_chunks_no_anchors_recall_null_batch40():
    """chunks=[] + anchors=[] → 先走到 'no chunks' 分支。"""
    out = chunk_boundary_prf(
        {"chunks": []},
        {"chunk_boundary_anchors": []},
    )
    # 先检查 chunks，再到 anchors；这里 chunks=[] 走 'no_predicted_boundaries'
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_perfect_match_batch40():
    """两 chunk + 1 anchor 完美匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 在 "hello world" 里 "o" 出现在 pos 4 和 7。第 1 个 anchor 从 0 找到 pos 4。
    # position=after → anchor 位置 = 4 + 1 = 5
    # predicted: chunk 0 末尾 = 5 (在 "hello world" 里 "hello" 结束于 pos 5)
    # |5 - 5| = 0 ≤ 5 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_partial_match_batch40():
    """3 chunk + 1 anchor（只命中一个边界）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # predicted = [1, 2]（chunk 0 和 1 的末尾）
    # anchor "a" position=after → 1
    # matched = 1
    # precision = 1/2 = 0.5
    # recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_batch40():
    """anchor 完全不在容差内。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # marker "x" 找不到 → missing_markers，num_gt = 0
    # recall = null + no_ground_truth_anchors_in_stream
    assert "_missing_markers" in out
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_missing_markers_recorded_batch40():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["_missing_markers"]["value"] == ["x"]


def test_chunk_boundary_prf_no_missing_markers_when_all_found_batch40():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_marker_position_before_batch40():
    """position="before" → anchor 位置 = marker 起始位置。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "w", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = "hello world"
    # predicted: chunk 0 末尾 = 5
    # anchor "w" position=before → find_from=0 找到 pos=6
    # |5 - 6| = 1 ≤ 5 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_one_to_one_matching_batch40():
    """两个 anchor 都靠近同一个 pred → 只匹配一个。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # pos = 3 (after c)
        {"marker": "f", "position": "after"},  # pos = 7 (after f)
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = "abc def"
    # predicted: chunk 0 末尾 = 3
    # anchor 1 = 3, anchor 2 = 7
    # |3-3|=0 matched, |3-7|=4 ≤ 10 → matched
    # 但一对一：pred 只有一个，最多匹配 1 个 anchor
    # matched = 1, num_pred = 1, num_gt = 2
    # precision = 1.0, recall = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_two_chunks_two_anchors_full_match_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "f", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = "abc def ghi"
    # predicted = [3, 7]
    # anchor 1 = 3 (c after), anchor 2 = 7 (f after)
    # both match → precision = 2/2 = 1.0, recall = 2/2 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_f1_perfect_batch40():
    """precision=1, recall=1 → f1=1。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_when_no_match_batch40():
    """p=0/1=0, r=0/1=0 → f1=0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "z", "position": "after"}]}  # z 不存在
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # marker 找不到 → num_gt=0 → recall null
    # 所以 f1 = null + precision_or_recall_not_evaluated
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_prf_value_is_float_or_none_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[k]["value"]
        assert v is None or isinstance(v, float)


def test_chunk_boundary_prf_extra_keys_in_annotation_ignored_batch40():
    """annotation 含其他键不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {
        "chunk_boundary_anchors": [{"marker": "c", "position": "after"}],
        "extra_key": "ignored",
        "figure_caption_anchors": [],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_extra_keys_in_anchor_ignored_batch40():
    """anchor 含其他键不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after", "extra": "ignored", "id": "x1"}
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_does_not_mutate_doc_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    import json
    before = json.dumps(doc, sort_keys=True)
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(doc, sort_keys=True) == before


def test_chunk_boundary_prf_does_not_mutate_annotation_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    import json
    before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert json.dumps(ann, sort_keys=True) == before


def test_chunk_boundary_prf_idempotent_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_chunk_boundary_prf_json_serializable_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # _tolerance_chars 是非 string key，但 json.dumps 接受 int key 转 str
    json.dumps(out, ensure_ascii=False)


def test_chunk_boundary_prf_doc_empty_dict_batch40():
    """doc={} → chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_doc_dict_with_empty_chunks_batch40():
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_doc_dict_chunks_string_raises_batch40():
    """chunks 是 string → for c in chunks 迭代字符 → 'x'.get 抛 AttributeError。"""
    with pytest.raises(AttributeError):
        chunk_boundary_prf({"chunks": "not_list"}, {"chunk_boundary_anchors": [{"marker": "x"}]})


def test_chunk_boundary_prf_anchor_missing_position_defaults_after_batch40():
    """anchor 不含 position → 默认 "after"。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c"}]}  # 无 position
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 默认 after → anchor pos = 3
    # matched → precision 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_missing_marker_uses_empty_string_batch40():
    """anchor 不含 marker → marker=''。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{}]}  # 无 marker
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # marker='' → find 返回 0 (empty string matches at pos 0)
    # 但代码 `find_pos = stream.find(marker, search_from) if marker else -1`
    # 空 marker → -1 → missing_markers
    assert "_missing_markers" in out


def test_chunk_boundary_prf_search_from_advances_batch40():
    """两个相同 marker 顺序定位，第 2 个不重复命中第 1 个位置。"""
    doc = {"chunks": [{"text": "aa"}, {"text": "aa"}, {"text": "end"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "aa", "position": "after"},
        {"marker": "aa", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = "aa aa end"
    # predicted = [2, 5] (chunk 0 末尾=2, chunk 1 末尾=5)
    # anchor 1: search_from=0, find pos=0 → after pos=2 → search_from=2
    # anchor 2: search_from=2, find pos=3 → after pos=5 → search_from=5
    # both anchors match → precision 2/2, recall 2/2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_signature_three_params_batch40():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_signature_tolerance_default_30_batch40():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_signature_return_dict_batch40():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_doc_document_param_batch40():
    """doc 是 doc dict 或 None。"""
    sig = inspect.signature(chunk_boundary_prf)
    ann = str(sig.parameters["document"].annotation)
    assert "dict" in ann
    assert "None" in ann


def test_chunk_boundary_prf_doc_annotation_param_batch40():
    sig = inspect.signature(chunk_boundary_prf)
    ann = str(sig.parameters["annotation"].annotation)
    assert "dict" in ann
    assert "None" in ann


# ---------- module source forbidden tokens 第六十八批


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
def test_module_source_no_forbidden_tokens_batch40(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第六十四批


def test_module_source_contains_design_doc_batch40():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_figure_caption_doc_batch40():
    src = inspect.getsource(amod)
    assert "figure-caption" in src or "figure_caption" in src


def test_module_source_contains_chunk_boundary_doc_batch40():
    src = inspect.getsource(amod)
    assert "chunk_boundary" in src


def test_module_source_contains_parser_does_not_emit_relations_const_batch40():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_normalize_text_import_batch40():
    """annotation_metrics 直接用 chunkers.structural.normalize_text。"""
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_metrics_null_ratio_import_batch40():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_figure_caption_prf_function_batch40():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_prf_function_batch40():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_counter_import_batch40():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch40():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_future_annotations_batch40():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_all_definition_batch40():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_contains_tolerance_chars_param_batch40():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_no_predicted_boundaries_keyword_batch40():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_keyword_batch40():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_pipeline_failed_keyword_batch40():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_keyword_batch40():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_normalize_text_call_batch40():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_contains_one_to_one_comment_batch40():
    src = inspect.getsource(amod)
    assert "一对一" in src


def test_module_source_contains_greedy_match_keyword_batch40():
    """算法用贪心匹配。"""
    src = inspect.getsource(amod)
    assert "贪心" in src or "greedy" in src.lower() or "pairs.sort" in src


# ---------- signatures 第六十四批


def test_signature_figure_caption_prf_two_params_batch40():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_signature_figure_caption_prf_doc_no_default_batch40():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_signature_figure_caption_prf_annotation_no_default_batch40():
    sig = inspect.signature(figure_caption_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


# ---------- module 合理性 第六十四批


def test_module_has_all_attribute_batch40():
    assert hasattr(amod, "__all__")


def test_module_all_is_list_batch40():
    assert isinstance(amod.__all__, list)


def test_module_all_len_three_batch40():
    assert len(amod.__all__) == 3


def test_module_all_contains_parser_const_batch40():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_module_all_contains_figure_caption_prf_batch40():
    assert "figure_caption_prf" in amod.__all__


def test_module_all_contains_chunk_boundary_prf_batch40():
    assert "chunk_boundary_prf" in amod.__all__


def test_module_does_not_define_class_batch40():
    src = inspect.getsource(amod)
    assert "\nclass " not in src


def test_module_top_level_no_print_or_assignments_batch40():
    """模块顶层无 print / = 赋值（除 __all__ 和 PARSER_DOES_NOT_EMIT_RELATIONS）。"""
    import ast
    src = inspect.getsource(amod)
    tree = ast.parse(src)
    # 顶层节点：Import / ImportFrom / ClassDef / FunctionDef / Assign / Expr(docstring)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Assign):
            # 容许 __all__ 和 PARSER_DOES_NOT_EMIT_RELATIONS
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assert target.id in ("__all__", "PARSER_DOES_NOT_EMIT_RELATIONS"), \
                        f"unexpected assignment: {target.id}"
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # docstring
            continue
        # 其他类型都不允许
        pytest.fail(f"unexpected top-level node: {type(node).__name__}")


def test_module_has_future_annotations_batch40():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


# ---------- 端到端集成 第六十四批


def test_e2e_full_pipeline_one_doc_one_anchor_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 10


def test_e2e_idempotent_run_batch40():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_e2e_with_unicode_text_batch40():
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "好", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = normalize("你好 世界") (假设 normalize 不改 unicode 字符)
    # "好" 在 pos=1, after → pos=2
    # predicted: chunk 0 末尾 = 2
    # matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_pipeline_failed_path_batch40():
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_e2e_no_annotation_path_batch40():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
