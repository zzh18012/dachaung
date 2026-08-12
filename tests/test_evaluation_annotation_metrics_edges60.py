"""evaluation/annotation_metrics.py 第六十轮 edges 测试（Round 552）。

补强 edges59 未触及的角度（第三十三批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十三批


def test_parser_does_not_emit_relations_used_by_figure_caption_batch33():
    """figure_caption_prf 的 reason 用此常量。"""
    out = figure_caption_prf({"chunks": []}, None)
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_is_lowercase_batch33():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS.lower()


def test_parser_does_not_emit_relations_no_spaces_batch33():
    assert " " not in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_starts_with_parser_batch33():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.startswith("parser_")


def test_parser_does_not_emit_relations_length_batch33():
    assert len(PARSER_DOES_NOT_EMIT_RELATIONS) == len("parser_does_not_emit_relations")


# ---------- figure_caption_prf 第三十三批


def test_figure_caption_prf_signature_batch33():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_figure_caption_prf_return_annotation_batch33():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_figure_caption_prf_keys_exact_order_batch33():
    out = figure_caption_prf({"chunks": []}, None)
    keys = list(out.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_value_field_is_none_batch33():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert "value" in v
        assert v["value"] is None


def test_figure_caption_prf_reason_field_exists_batch33():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for k, v in out.items():
        assert "reason" in v


def test_figure_caption_prf_value_field_only_batch33():
    """每个 metric dict 只含 value + reason 两个 key。"""
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_annotation_dict_full_batch33():
    """即使 annotation 含 figure_caption_anchors，依然 null（本期不实现）。"""
    ann = {"figure_caption_anchors": [{"figure": "f1", "caption": "c1"}]}
    out = figure_caption_prf({"chunks": []}, ann)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_document_with_figures_batch33():
    """document 中有 figure element，仍 null。"""
    doc = {"elements": [{"type": "figure", "content": None, "resource_path": "/x.png"}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_not_a_method_batch33():
    """模块级函数，非类方法。"""
    import types
    assert isinstance(amod.figure_caption_prf, types.FunctionType)


# ---------- chunk_boundary_prf 第三十三批


def test_chunk_boundary_prf_signature_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_default_tolerance_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_return_annotation_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch33():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_includes_tolerance_batch33():
    out = chunk_boundary_prf(None, None, tolerance_chars=15)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_annotation_empty_returns_no_annotation_batch33():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch33():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_one_chunk_no_anchors_batch33():
    """1 个 chunk → no_predicted_boundaries，no anchors → recall 也是 no_predicted。"""
    doc = {"chunks": [{"text": "hello"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_batch33():
    """1 个 chunk + 有 anchors → recall=0.0（不是 null）。"""
    doc = {"chunks": [{"text": "hello"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "h"}]})
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_no_anchors_batch33():
    """2 chunks + 0 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_perfect_match_batch33():
    """2 chunks 'abc'+'def'，anchor 'c' position after → 完美匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch33():
    """2 chunks 'abc'+'def'，anchor 'd' position before → 完美匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "d", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_too_tight_batch33():
    """tolerance=0：预测边界 pos=3，anchor 'c' after pos=3，距离 0 → 匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_too_loose_batch33():
    """tolerance 太小，预测位置与 anchor 距离大 → 0 匹配。"""
    doc = {"chunks": [{"text": "abcdefghij"}, {"text": "klmnop"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    # marker 不在 stream 里 → missing
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "x" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_duplicate_markers_batch33():
    """相同 marker 多次出现：用 search_from 推进，每次找下一个。"""
    doc = {"chunks": [{"text": "x"}, {"text": "x"}, {"text": "x"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "x", "position": "after"},
        {"marker": "x", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # 2 个预测位置（chunk 0 末尾 + chunk 1 末尾），2 个 anchor
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_returns_tolerance_key_batch33():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_tolerance_value_reflected_batch33():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_three_chunks_two_boundaries_batch33():
    """3 chunks → 2 个内部预测边界。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "f", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predictions_batch33():
    """anchors 多于 predictions → recall < 1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "f", "position": "after"},  # 不存在（"def" 末尾就是 f 但需要在 stream 中查找）
    ]}
    # 实际上 "f" 在 stream "abc def" 中存在，所以这个 anchor 也会找到
    # 让我们用一个不存在的 marker
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "ZZZ", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 1 matched, 1 prediction → precision 1.0
    # 1 matched, 2 ground truth 但 1 个 missing → num_gt=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert "_missing_markers" in out


def test_chunk_boundary_prf_more_predictions_than_anchors_batch33():
    """predictions 多于 anchors → precision < 1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 1 matched, 2 predictions → precision 0.5
    # 1 matched, 1 ground truth → recall 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_f1_calculation_batch33():
    """f1 = 2*p*r/(p+r)。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    p = 0.5
    r = 1.0
    expected_f1 = 2 * p * r / (p + r)
    assert abs(out["chunk_boundary_f1"]["value"] - expected_f1) < 1e-9


def test_chunk_boundary_prf_zero_match_batch33():
    """完全不匹配（marker 太远）→ p=0, r=0, f1=0。"""
    doc = {"chunks": [{"text": "aaaaaaaaaa"}, {"text": "bbbbbbbbbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # anchor 'a' 在 stream 中第一次出现 pos=0，after pos=1
    # 预测边界 = chunk 0 末尾 = 10
    # 距离 |10 - 1| = 9 > tolerance=0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_returns_dict_batch33():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_chunk_no_text_field_batch33():
    """chunk 没有 text 字段 → 视为空字符串。"""
    doc = {"chunks": [{"no_text": True}, {"no_text": True}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # 两个空 chunk → stream 空 → marker 找不到 → missing
    assert "_missing_markers" in out


def test_chunk_boundary_prf_does_not_mutate_document_batch33():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_chunk_boundary_prf_does_not_mutate_annotation_batch33():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_chunk_boundary_prf_negative_tolerance_batch33():
    """负 tolerance：所有距离绝对值都比 |tolerance| 大 → 不匹配。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # abs(d) <= -1 永远 False
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_zero_chunks_batch33():
    """0 chunks → no_predicted_boundaries。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_dict_chunks_none_batch33():
    """annotation 是 None → no_annotation。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_position_default_after_batch33():
    """anchor 不指定 position → 默认 after。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- module source forbidden tokens 第五十二批


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
    "pty",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch33(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第四十八批


def test_module_source_contains_docstring_batch33():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_future_annotations_batch33():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_counter_import_batch33():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_import_batch33():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_normalize_text_import_batch33():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch33():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_parser_does_not_emit_const_batch33():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_func_batch33():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_func_batch33():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_pipeline_failed_reason_batch33():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_annotation_reason_batch33():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_contains_no_predicted_boundaries_reason_batch33():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_contains_no_ground_truth_reason_batch33():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_contains_tolerance_chars_param_batch33():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_all_batch33():
    src = inspect.getsource(amod)
    assert "__all__" in src
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


# ---------- signatures 第四十八批


def test_signature_chunk_boundary_prf_params_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_figure_caption_prf_params_batch33():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_tolerance_default_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_return_dict_batch33():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


# ---------- module 合理性第四十八批


def test_module_has_future_annotations_batch33():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_has_figure_caption_func_batch33():
    assert callable(amod.figure_caption_prf)


def test_module_has_chunk_boundary_func_batch33():
    assert callable(amod.chunk_boundary_prf)


def test_module_has_parser_const_batch33():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_has_all_batch33():
    assert hasattr(amod, "__all__")
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__
    assert "figure_caption_prf" in amod.__all__
    assert "chunk_boundary_prf" in amod.__all__


# ---------- 端到端集成第四十八批


def test_e2e_figure_caption_with_real_doc_batch33():
    """完整 PDF doc → figure_caption 仍然 null。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "figure", "content": None, "resource_path": "/x.png",
             "element_id": "f1", "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]}},
            {"type": "caption", "content": "Fig 1", "element_id": "c1"},
        ],
        "chunks": [],
    }
    ann = {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, ann)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_with_realistic_doc_batch33():
    """完整 doc → chunk_boundary 完美匹配。"""
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc def ghi"}],
        "chunks": [
            {"text": "abc", "source_element_ids": ["e1"]},
            {"text": "def", "source_element_ids": ["e1"]},
            {"text": "ghi", "source_element_ids": ["e1"]},
        ],
    }
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},
        {"marker": "f", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_idempotent_batch33():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_e2e_chunk_boundary_does_not_read_other_annotation_keys_batch33():
    """annotation 中无关字段不影响。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {
        "chunk_boundary_anchors": [{"marker": "c", "position": "after"}],
        "irrelevant_field": "xxx",
        "another": [1, 2, 3],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
