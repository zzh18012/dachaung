"""evaluation/annotation_metrics.py 第四十六轮 edges 测试（Round 455）。

补强 edges45 未触及的角度：
- figure_caption_prf 行为深度第十九批（None document / None annotation / 任意输入都返固定 3 keys / reason 不依赖输入）
- chunk_boundary_prf 边界第十九批（document 含额外字段 / annotation 含额外字段 / document 缺 chunks / chunks 是 dict 不是 list）
- chunk_boundary_prf 算法第十九批（多 chunk 多边界 / 全部 match / 全部 miss / 部分匹配 / tolerance 0 strict / tolerance 大）
- chunk_boundary_prf missing_markers 第十九批（marker 空 string / marker None / marker 多个 missing）
- _tolerance_chars 第十九批（always in output / negative tolerance / large tolerance）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十一批
- signatures 第二十九批
- module 合理性第二十九批
- 端到端集成第二十九批
"""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation import annotation_metrics as amod


# ---------- figure_caption_prf 行为深度第十九批 ----------


def test_figure_caption_prf_keys_constant_batch19():
    """任何输入都返 3 keys。"""
    r = figure_caption_prf({}, {})
    assert len(r) == 3


def test_figure_caption_prf_with_complete_doc_and_annotation_batch19():
    """给完整 doc + annotation 也仍是 null。"""
    doc = {
        "elements": [
            {"element_id": "fig1", "type": "image"},
            {"element_id": "cap1", "type": "caption", "text": "Fig 1"},
        ]
    }
    annotation = {"figure_caption_pairs": [("fig1", "cap1")]}
    r = figure_caption_prf(doc, annotation)
    for v in r.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_independent_of_input_batch19():
    """reason 不依赖输入。"""
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf({"x": 1}, {"y": 2})
    for k in r1:
        assert r1[k]["reason"] == r2[k]["reason"]


def test_figure_caption_prf_returns_same_dict_for_different_inputs_batch19():
    """不同输入返同结构（因为总是 null）。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"x": 1}, None),
        (None, {"y": 2}),
        ({"x": 1}, {"y": 2}),
    ]
    results = [figure_caption_prf(d, a) for d, a in inputs]
    for r in results:
        for v in r.values():
            assert v["value"] is None
            assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_value_reason_keys_only_batch19():
    """每个 value dict 只含 value + reason 2 key。"""
    r = figure_caption_prf({}, {})
    for v in r.values():
        assert set(v.keys()) == {"value", "reason"}


# ---------- chunk_boundary_prf 边界第十九批 ----------


def test_chunk_boundary_prf_doc_with_extra_fields_batch19():
    """document 含额外字段也能工作。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [],
        "chunks": [
            {"chunk_id": "c1", "text": "abc"},
            {"chunk_id": "c2", "text": "def"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_annotation_with_extra_fields_batch19():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "doc_id": "d1",
        "annotation_version": "1.0",
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_chunks_key_missing_batch19():
    """document 缺 chunks key → chunks=[]。"""
    r = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_none_batch19():
    """annotation 是 None → no_annotation。"""
    doc = {"chunks": [{"chunk_id": "c1", "text": "abc"}]}
    r = chunk_boundary_prf(doc, None)
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch19():
    """annotation 是 {} → falsy → no_annotation。"""
    doc = {"chunks": [{"chunk_id": "c1", "text": "abc"}]}
    r = chunk_boundary_prf(doc, {})
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


# ---------- chunk_boundary_prf 算法第十九批 ----------


def test_chunk_boundary_prf_3_chunks_2_boundaries_all_match_batch19():
    """3 chunks → 2 predicted boundaries，都 match。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
        {"chunk_id": "c3", "text": "ghi"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "def", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_all_mismatch_batch19():
    """全部 anchor 都不在 stream → gt 空 → recall null。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz1", "position": "after"},
            {"marker": "xyz2", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # num_gt=0 → recall null
    assert r["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_partial_match_batch19():
    """3 anchors，2 个匹配，1 个不匹配。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
        {"chunk_id": "c3", "text": "ghi"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # match (3)
            {"marker": "def", "position": "after"},  # match (7)
            {"marker": "xyz", "position": "after"},  # missing
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted = [3, 7], gt = [3, 7] → matched=2, P=2/2=1.0, R=2/2=1.0
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_batch19():
    """tolerance=0 严格匹配。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    # stream = "abc def"
    # predict boundary at end of abc = 3
    # anchor def before → start of def = 4
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "before"},  # gt=4
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # |3-4|=1 > 0 → no match → P=0/1=0.0
    assert r["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_large_match_batch19():
    """tolerance=10 让所有 anchor 都匹配。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "before"},  # gt=4
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # |3-4|=1 ≤ 10 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_f1_perfect_batch19():
    """完美匹配 → f1=1.0。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_half_batch19():
    """P=1.0, R=0.5 → f1 = 2*1*0.5/(1+0.5) = 0.6667。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "foo"},
        {"chunk_id": "c2", "text": "bar"},
    ]}
    # stream = "foo bar"
    # predicted = [3] (end of foo)
    # 2 anchors: foo after (gt=3), bar before (gt=4)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
            {"marker": "bar", "position": "before"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # predicted=1, gt=2 → matched=1 (whichever is closer)
    # P=1/1=1.0, R=1/2=0.5, F1=2*1*0.5/1.5=0.6667
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 0.5
    assert abs(r["chunk_boundary_f1"]["value"] - 2/3) < 0.001


# ---------- chunk_boundary_prf missing_markers 第十九批 ----------


def test_chunk_boundary_prf_empty_marker_treated_as_missing_batch19():
    """空 marker → find 返回 -1 → 加入 missing。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in r
    assert "" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_not_in_stream_batch19():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in r
    assert "xyz" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_multiple_missing_markers_batch19():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz1", "position": "after"},
            {"marker": "xyz2", "position": "before"},
            {"marker": "xyz3", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    miss = r["_missing_markers"]["value"]
    assert len(miss) == 3


def test_chunk_boundary_prf_no_missing_no_field_batch19():
    """所有 marker 都找到 → 不加 _missing_markers 字段。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" not in r


# ---------- _tolerance_chars 第十九批 ----------


def test_chunk_boundary_prf_negative_tolerance_batch19():
    """tolerance=-1 → 没有 anchor 能匹配（distance 都 >=0 > -1）。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=-1)
    # distance=0 ≤ -1 False → no match
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["_tolerance_chars"]["value"] == -1


def test_chunk_boundary_prf_tolerance_in_output_with_no_document_batch19():
    """document None 时 _tolerance_chars 也在 output。"""
    r = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert r["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_in_output_with_no_annotation_batch19():
    doc = {"chunks": [{"chunk_id": "c1", "text": "abc"}]}
    r = chunk_boundary_prf(doc, None, tolerance_chars=15)
    assert r["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_tolerance_default_30_batch19():
    doc = {"chunks": [{"chunk_id": "c1", "text": "abc"}]}
    r = chunk_boundary_prf(doc, None)
    assert r["_tolerance_chars"]["value"] == 30


# ---------- module source forbidden tokens 第三十三批 ----------


@pytest.mark.parametrize("forbidden", [
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
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch19(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch19():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch19():
    src = inspect.getsource(amod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第三十一批 ----------


def test_module_source_has_future_annotations_batch19():
    src = inspect.getsource(amod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch19():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_has_counter_import_batch19():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_import_batch19():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_import_batch19():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import_batch19():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant_batch19():
    src = inspect.getsource(amod)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_module_source_has_figure_caption_function_batch19():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_function_batch19():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_all_dunder_batch19():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_no_main_block_batch19():
    src = inspect.getsource(amod)
    assert "__main__" not in src


# ---------- signatures 第二十九批 ----------


def test_signature_figure_caption_prf_batch19():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch19():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_batch19():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性第二十九批 ----------


def test_module_has_all_attribute_batch19():
    assert hasattr(amod, "__all__")
    assert isinstance(amod.__all__, list)


def test_module_all_count_3_batch19():
    assert len(amod.__all__) == 3


def test_module_all_contents_batch19():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_figure_caption_callable_batch19():
    assert callable(figure_caption_prf)


def test_module_chunk_boundary_callable_batch19():
    assert callable(chunk_boundary_prf)


def test_module_does_not_import_unsafe_modules_batch19():
    src = inspect.getsource(amod)
    for unsafe in ["import pickle", "import marshal", "import shelve"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_runner_batch19():
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch19():
    src = inspect.getsource(amod)
    assert "from evaluation.cli" not in src


def test_module_constant_is_string_batch19():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- 端到端集成第二十九批 ----------


def test_e2e_figure_caption_always_returns_3_metrics_batch19():
    """figure_caption_prf 任何输入都返固定 3 keys。"""
    test_cases = [
        (None, None),
        ({}, {}),
        ({"elements": []}, {"chunk_boundary_anchors": []}),
        (None, {"x": 1}),
    ]
    for doc, ann in test_cases:
        r = figure_caption_prf(doc, ann)
        assert set(r.keys()) == {
            "figure_caption_precision",
            "figure_caption_recall",
            "figure_caption_f1",
        }


def test_e2e_chunk_boundary_full_pipeline_batch19():
    """完整 chunk_boundary_prf pipeline。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "hello"},
        {"chunk_id": "c2", "text": "world"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert set(r.keys()) >= {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_normalize_text_integration_batch19():
    """normalize_text 影响 stream 位置。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "  hello   world  "},  # → "hello world"
        {"chunk_id": "c2", "text": "foo"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "world", "position": "after"}]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # stream = "hello world foo"
    # predicted = end of c1 normalize = 11
    # gt = end of "world" in stream = 11 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_unicode_batch19():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "你好"},
        {"chunk_id": "c2", "text": "世界"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_combined_figure_and_chunk_batch19():
    """组合调用 figure_caption_prf + chunk_boundary_prf。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    fc = figure_caption_prf(doc, annotation)
    cb = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert len(fc) == 3
    assert "chunk_boundary_precision" in cb


def test_e2e_chunk_boundary_with_image_in_doc_batch19():
    """doc 含 image element 但 chunk 仍正常计算。"""
    doc = {
        "elements": [
            {"element_id": "img1", "type": "image", "resource_path": "x.png"},
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "abc"},
            {"chunk_id": "c2", "text": "def"},
        ],
    }
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_no_text_in_chunk_batch19():
    """chunk 缺 text → 视为 ""。"""
    doc = {"chunks": [
        {"chunk_id": "c1"},  # no text
        {"chunk_id": "c2", "text": "abc"},
    ]}
    annotation = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    # 应不抛异常
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert isinstance(r, dict)
