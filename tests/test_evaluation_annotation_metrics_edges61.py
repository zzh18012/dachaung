"""evaluation/annotation_metrics.py 第六十一轮 edges 测试（Round 559）。

补强 edges60 未触及的角度（第三十四批）。
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


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十四批


def test_parser_const_value_batch34():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_const_is_str_batch34():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_const_in_all_batch34():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src


# ---------- figure_caption_prf 第三十四批


def test_figure_caption_prf_returns_dict_batch34():
    out = figure_caption_prf({"chunks": []}, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_keys_exact_batch34():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_null_values_batch34():
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_all_reasons_const_batch34():
    out = figure_caption_prf(None, {"figure_caption_anchors": []})
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_mutate_input_batch34():
    doc = {"chunks": [{"text": "x"}], "elements": []}
    ann = {"key": "value"}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    figure_caption_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_figure_caption_prf_module_func_batch34():
    import types
    assert isinstance(amod.figure_caption_prf, types.FunctionType)


# ---------- chunk_boundary_prf 第三十四批：一对一匹配


def test_chunk_boundary_prf_greedy_match_batch34():
    """贪心匹配：距离最小的优先。"""
    # 2 chunks，1 anchor 接近边界 0（chunk 0 末尾），1 接近边界 1
    doc = {"chunks": [{"text": "abcdefgh"}, {"text": "ijklmnop"}, {"text": "qrstuvwx"}]}
    # stream = "abcdefgh ijklmnop qrstuvwx"
    # 边界 0 在 pos=8（h 后），边界 1 在 pos=17（p 后）
    # anchor 'a' after → pos=1，距离 |8-1|=7 到边界 0
    # anchor 'i' after → pos=9，距离 |8-9|=1 到边界 0，|17-9|=8 到边界 1
    ann = {"chunk_boundary_anchors": [
        {"marker": "i", "position": "after"},
        {"marker": "q", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=20)
    # 应该完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_duplicate_pred_match_batch34():
    """一个 pred 不能匹配两个 anchor。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # 边界 0 在 pos=3
    ann = {"chunk_boundary_anchors": [
        {"marker": "c", "position": "after"},  # pos=3
        {"marker": "c", "position": "before"},  # 重复 marker 但 position 不同 → pos=2
    ]}
    # 第一次 'c' 找到在 pos=2（c 在 stream "abc def" 中起始位置）
    # position=after → anchor 位置 = pos + len('c') = 3
    # search_from 推进到 3
    # 第二次 'c' find from 3 → -1（不存在）→ missing
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 1 matched, 1 prediction
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_no_duplicate_gt_match_batch34():
    """一个 anchor 不能匹配两个 pred。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    # 边界 0 = pos 3, 边界 1 = pos 7
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}  # anchor pos=3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 1 matched, 2 predictions → precision 0.5
    # 1 matched, 1 ground truth → recall 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_partial_within_tolerance_batch34():
    """部分匹配在容差内。"""
    doc = {"chunks": [{"text": "abcdefgh"}, {"text": "ijklmnop"}]}
    # 边界 = pos 8
    ann = {"chunk_boundary_anchors": [{"marker": "f", "position": "after"}]}
    # 'f' 在 pos=5（stream "abcdefgh ijklmnop"）
    # after → pos=6
    # 距离 |8-6|=2
    out = chunk_boundary_prf(doc, ann, tolerance_chars=3)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_partial_outside_tolerance_batch34():
    """部分匹配在容差外 → 0 match。"""
    doc = {"chunks": [{"text": "abcdefgh"}, {"text": "ijklmnop"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # 'a' 在 pos=0, after → pos=1
    # 边界 pos=8, 距离 |8-1|=7
    out = chunk_boundary_prf(doc, ann, tolerance_chars=3)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_position_before_within_tolerance_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "d", "position": "before"}]}
    # 'd' 在 pos=4（stream "abc def"）
    # before → pos=4
    # 边界 pos=3，距离 |3-4|=1
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_after_within_tolerance_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 'c' 在 pos=2, after → pos=3
    # 边界 pos=3, 距离 0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_marker_empty_batch34():
    """marker 为空字符串 → find 返回 -1 → missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert "_missing_markers" in out


def test_chunk_boundary_prf_anchor_marker_missing_key_batch34():
    """anchor 没有 marker key → 默认 ""。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 默认 marker="" → find 返回 -1 → missing
    assert "_missing_markers" in out


def test_chunk_boundary_prf_anchor_position_missing_key_batch34():
    """anchor 没有 position key → 默认 after。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_text_missing_batch34():
    """chunk 没有 text 字段 → normalize 后空字符串。"""
    doc = {"chunks": [{"no_text": True}, {"no_text": True}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # 两个空 chunk → stream 空 → marker 找不到
    assert "_missing_markers" in out


def test_chunk_boundary_prf_does_not_mutate_doc_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_chunk_boundary_prf_does_not_mutate_ann_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_chunk_boundary_prf_returns_tolerance_key_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert "_tolerance_chars" in out
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_negative_tolerance_no_match_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # abs(d) <= -1 永远 False
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_no_chunks_with_anchors_batch34():
    """chunks=[] 且 anchors 非空 → no_predicted_boundaries (recall=0.0)。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 1 chunk 逻辑：有 anchors 但 0 chunks → recall=0.0（_ratio）
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_no_anchors_recall_null_batch34():
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    # 1 chunk + 0 anchors → recall 也是 no_predicted_boundaries
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_doc_none_pipeline_failed_batch34():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_none_no_annotation_batch34():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch34():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_anchors_batch34():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_returns_dict_batch34():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


# ---------- module source forbidden tokens 第五十三批


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
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(amod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_future_annotations_batch34():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_counter_import_batch34():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_normalize_text_import_batch34():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_metrics_import_batch34():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_parser_const_batch34():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_func_batch34():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_func_batch34():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_pipeline_failed_batch34():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_contains_no_annotation_batch34():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_contains_tolerance_chars_batch34():
    src = inspect.getsource(amod)
    assert "tolerance_chars" in src


def test_module_source_contains_all_batch34():
    src = inspect.getsource(amod)
    assert "__all__" in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


# ---------- signatures 第四十九批


def test_signature_figure_caption_prf_params_batch34():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_signature_chunk_boundary_prf_params_batch34():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_tolerance_batch34():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_return_dict_batch34():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


def test_signature_figure_caption_prf_return_dict_batch34():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation == "dict[str, dict[str, Any]]"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch34():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_has_figure_caption_func_batch34():
    assert callable(amod.figure_caption_prf)


def test_module_has_chunk_boundary_func_batch34():
    assert callable(amod.chunk_boundary_prf)


def test_module_has_parser_const_batch34():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_has_all_batch34():
    assert hasattr(amod, "__all__")
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__
    assert "figure_caption_prf" in amod.__all__
    assert "chunk_boundary_prf" in amod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_chunk_boundary_full_pipeline_batch34():
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


def test_e2e_chunk_boundary_idempotent_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "c", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_e2e_chunk_boundary_irrelevant_annotation_keys_batch34():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {
        "chunk_boundary_anchors": [{"marker": "c", "position": "after"}],
        "irrelevant": "x",
        "another": [1, 2],
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_figure_caption_with_realistic_doc_batch34():
    doc = {
        "elements": [
            {"type": "figure", "content": None, "resource_path": "/x.png"},
            {"type": "caption", "content": "Fig 1"},
        ],
        "chunks": [],
    }
    ann = {"figure_caption_anchors": [{"figure_id": "f1", "caption_id": "c1"}]}
    out = figure_caption_prf(doc, ann)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_figure_caption_docx_batch34():
    """DOCX doc → figure_caption 也固定 null。"""
    doc = {"source_type": "docx", "elements": [], "chunks": []}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None
