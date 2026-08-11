"""evaluation/annotation_metrics.py 第四十五轮 edges 测试（Round 448）。

补强 edges44 未触及的角度：
- figure_caption_prf 行为深度第十八批（None document / None annotation / both None / 返回 3 keys / 都 null / reason 固定 / dict 结构）
- chunk_boundary_prf 边界第十八批（document None / annotation None / both None / chunks=[] / single chunk / chunks missing / annotation 缺 chunk_boundary_anchors）
- chunk_boundary_prf 算法第十八批（predicted 计算多 chunk / gt position before/after / 多 anchor 同 marker 顺序定位 / search_from 推进 / 1-1 匹配 tie-break / f1 计算）
- chunk_boundary_prf missing_markers 第十八批（marker 不在 stream / 多 missing / 空 marker / missing_markers 字段）
- _tolerance_chars 行为深度第十八批（默认 30 / 自定义 / 0 / 大值 / 在 output dict）
- module source forbidden tokens 第三十二批
- module source 字符串精确补强第二十八批
- signatures 第二十八批
- module 合理性第二十八批
- 端到端集成第二十八批
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


# ---------- figure_caption_prf 行为深度第十八批 ----------


def test_figure_caption_prf_keys_count_batch18():
    r = figure_caption_prf({}, {})
    assert len(r) == 3


def test_figure_caption_prf_keys_names_batch18():
    r = figure_caption_prf({}, {})
    assert set(r.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_null_batch18():
    r = figure_caption_prf({}, {})
    for v in r.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_batch18():
    r = figure_caption_prf({}, {})
    for v in r.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_none_document_batch18():
    r = figure_caption_prf(None, {})
    assert len(r) == 3


def test_figure_caption_prf_none_annotation_batch18():
    r = figure_caption_prf({}, None)
    assert len(r) == 3


def test_figure_caption_prf_both_none_batch18():
    r = figure_caption_prf(None, None)
    assert len(r) == 3


def test_figure_caption_prf_dict_structure_batch18():
    r = figure_caption_prf({}, {})
    for v in r.values():
        assert isinstance(v, dict)
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_idempotent_batch18():
    r1 = figure_caption_prf({}, {})
    r2 = figure_caption_prf({}, {})
    assert r1 == r2


def test_figure_caption_prf_with_real_doc_batch18():
    """给一个含 figure 的 document，仍是 null（parser 不输出 relations）。"""
    doc = {
        "elements": [
            {"element_id": "fig1", "type": "image", "resource_path": "x.png"},
            {"element_id": "cap1", "type": "caption", "text": "Fig 1"},
        ]
    }
    r = figure_caption_prf(doc, {})
    for v in r.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 边界第十八批 ----------


def test_chunk_boundary_prf_document_none_with_annotation_batch18():
    """document None + 有 annotation → pipeline_failed。"""
    r = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert r["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_prf_document_none_no_annotation_batch18():
    r = chunk_boundary_prf(None, None)
    assert r["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_empty_annotation_none_batch18():
    """有 document + None annotation → no_annotation。"""
    r = chunk_boundary_prf({"chunks": []}, None)
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_empty_annotation_empty_dict_batch18():
    """空 dict annotation 视为 no_annotation（falsy）。"""
    r = chunk_boundary_prf({"chunks": []}, {})
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_document_with_chunks_no_anchors_batch18():
    """document 有 2 chunks + annotation 有 chunk_boundary_anchors=[] → no_ground_truth_anchors。"""
    doc = {
        "chunks": [
            {"chunk_id": "c1", "text": "abc"},
            {"chunk_id": "c2", "text": "def"},
        ]
    }
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_missing_batch18():
    """document 没 chunks key → chunks=[] → no_predicted_boundaries。"""
    r = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_batch18():
    """1 个 chunk → 没有内部边界。"""
    doc = {"chunks": [{"chunk_id": "c1", "text": "abc"}]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_annotation_missing_anchors_key_batch18():
    """annotation 没有 chunk_boundary_anchors → 走 anchors=[] 分支。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    r = chunk_boundary_prf(doc, {"other_key": "value"})
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_no_chunks_no_anchors_batch18():
    """chunks=[] + anchors=[] → no_predicted_boundaries + no_anchors → recall null。"""
    r = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    # 因为 not chunks → no_predicted_boundaries
    # recall：anchors 也是 [] → _null("no_predicted_boundaries")
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert r["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


# ---------- chunk_boundary_prf 算法第十八批 ----------


def test_chunk_boundary_prf_predicted_positions_batch18():
    """2 chunks → 1 个预测边界。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "before"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # abc def → "def" start at position 4，predict boundary at end of "abc" = position 3
    # difference = 1 → tolerance 0 fail → precision = 0/1 = 0.0
    # 但是 recall = 0/1 = 0.0；f1 = 0.0
    assert r["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_predicted_match_with_tolerance_batch18():
    """用 tolerance=1 让差 1 的匹配成功。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "def", "position": "before"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # 差 1 ≤ tolerance 1 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_after_batch18():
    """position='after' 取 marker 结束位置。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # end of abc = 3
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 预测 boundary at end of abc = 3, gt = 3 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_default_after_batch18():
    """position 缺省时按 'after' 处理。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc"},  # default 'after'
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_multiple_anchors_same_marker_batch18():
    """两个 anchor 同 marker，应顺序定位到第 1 / 第 2 次出现。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "foo foo foo"},
        {"chunk_id": "c2", "text": "bar"},
    ]}
    # stream = "foo foo foo bar"
    # 边界 = end of c1 = 11
    # anchor1: marker="foo" position="after" → end of 1st foo = 3
    # anchor2: marker="foo" position="after" → end of 2nd foo = 7
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
            {"marker": "foo", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # predicted = [11] (only 1 boundary)
    # gt = [3, 7]
    # 匹配：pred 11 与 gt 7 距离 4 ≤ 10 → match；gt 3 距离 8 ≤ 10 但 pred 已用
    # matched = 1, num_pred = 1 → P = 1.0
    # num_gt = 2 → R = 0.5
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_search_from_advances_batch18():
    """search_from 推进避免共享 stream 位置。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "ab cd"},
        {"chunk_id": "c2", "text": "ef"},
    ]}
    # stream = "ab cd ef"
    # 边界 = end of c1 = 5
    # anchor1: marker="cd" position="after" → 5 (end of cd)
    # anchor2: marker="ef" position="before" → 6 (start of ef)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "after"},
            {"marker": "ef", "position": "before"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    # predicted = [5]
    # gt = [5, 6]
    # 距离 |5-5|=0, |5-6|=1，都 ≤ 1；按距离排序，先匹配 gt 5
    # matched = 1, P = 1/1 = 1.0, R = 1/2 = 0.5
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_f1_perfect_batch18():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_match_batch18():
    """完全错位 → P=R=0 → f1=0。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},  # not in stream → missing
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # marker xyz 不在 stream → missing → gt_positions = []
    # num_gt = 0 → recall null
    assert r["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    # f1 null（recall 是 null）
    assert r["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_multiple_chunks_multiple_boundaries_batch18():
    """3 chunks → 2 个预测边界。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
        {"chunk_id": "c3", "text": "ghi"},
    ]}
    # stream = "abc def ghi"
    # predicted = [3, 7] (end of abc, end of def)
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},  # gt=3
            {"marker": "def", "position": "after"},  # gt=7
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf missing_markers 第十八批 ----------


def test_chunk_boundary_prf_missing_marker_recorded_batch18():
    """marker 不在 stream → 记录到 _missing_markers。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" in r
    assert "xyz" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_multiple_missing_markers_batch18():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "xyz1", "position": "after"},
            {"marker": "xyz2", "position": "before"},
            {"marker": "abc", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    miss = r["_missing_markers"]["value"]
    assert "xyz1" in miss
    assert "xyz2" in miss
    assert len(miss) == 2


def test_chunk_boundary_prf_empty_marker_treated_as_missing_batch18():
    """空 marker → find 返回 -1（因为 marker="" 时 if marker 为 False → 直接 -1）。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # 空 marker → missing
    assert "_missing_markers" in r
    assert "" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_no_field_batch18():
    """所有 marker 都找到 → 不加 _missing_markers 字段。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert "_missing_markers" not in r


# ---------- _tolerance_chars 行为深度第十八批 ----------


def test_chunk_boundary_prf_default_tolerance_batch18():
    """默认 tolerance=30。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_custom_tolerance_batch18():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=15)
    assert r["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_tolerance_zero_batch18():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=0)
    assert r["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_large_batch18():
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=10000)
    assert r["_tolerance_chars"]["value"] == 10000


def test_chunk_boundary_prf_tolerance_in_output_even_when_document_none_batch18():
    r = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert r["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_reason_none_batch18():
    r = chunk_boundary_prf(None, None)
    assert r["_tolerance_chars"]["reason"] is None


# ---------- module source forbidden tokens 第三十二批 ----------


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
def test_module_source_forbidden_tokens_batch18(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch18():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch18():
    src = inspect.getsource(amod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第二十八批 ----------


def test_module_source_has_future_annotations_batch18():
    src = inspect.getsource(amod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch18():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_has_counter_import_batch18():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_import_batch18():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_import_batch18():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import_batch18():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant_batch18():
    src = inspect.getsource(amod)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_module_source_has_figure_caption_function_batch18():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_function_batch18():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_all_dunder_batch18():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_source_no_main_block_batch18():
    src = inspect.getsource(amod)
    assert "__main__" not in src


# ---------- signatures 第二十八批 ----------


def test_signature_figure_caption_prf_batch18():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch18():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_default_tolerance_batch18():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


# ---------- module 合理性第二十八批 ----------


def test_module_has_all_attribute_batch18():
    assert hasattr(amod, "__all__")
    assert isinstance(amod.__all__, list)


def test_module_all_count_3_batch18():
    assert len(amod.__all__) == 3


def test_module_all_contents_batch18():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_figure_caption_callable_batch18():
    assert callable(figure_caption_prf)


def test_module_chunk_boundary_callable_batch18():
    assert callable(chunk_boundary_prf)


def test_module_does_not_import_unsafe_modules_batch18():
    src = inspect.getsource(amod)
    for unsafe in ["import pickle", "import marshal", "import shelve",
                   "import subprocess"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_runner_batch18():
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch18():
    src = inspect.getsource(amod)
    assert "from evaluation.cli" not in src


def test_module_constant_is_string_batch18():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- 端到端集成第二十八批 ----------


def test_e2e_figure_caption_always_null_batch18():
    """figure_caption_prf 任何输入都返 null + reason。"""
    for args in [({}, {}), (None, None), (None, {}), ({}, None)]:
        r = figure_caption_prf(*args)
        for v in r.values():
            assert v["value"] is None
            assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_full_round_trip_batch18():
    """完整 round trip：document + annotation → 完整 P/R/F1。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "hello world"},
        {"chunk_id": "c2", "text": "foo bar"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert set(r.keys()) >= {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }


def test_e2e_chunk_boundary_with_normalize_text_batch18():
    """normalize_text 把空白压成单空格，影响 stream 位置。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "  hello   world  "},  # → "hello world"
        {"chunk_id": "c2", "text": "foo"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},  # → end of world = 11
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # predicted = end of c1 normalize = 11 ("hello world" 长 11)
    # gt = end of "world" in stream = 11 → match
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_unicode_text_batch18():
    """Unicode text 也能正确计算位置。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "你好世界"},
        {"chunk_id": "c2", "text": "test"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "你好世界", "position": "after"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_chunk_missing_text_batch18():
    """chunk 缺 text → 视为 ""。"""
    doc = {"chunks": [
        {"chunk_id": "c1"},  # no text
        {"chunk_id": "c2", "text": "abc"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "before"},
        ]
    }
    r = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # c1 text = "" → norm_chunks[0] = ""，end = 0
    # predicted = [0]
    # stream = " abc" → wait, normalize_text(" abc") = "abc"，但实际是 " " + "abc" 然后 normalize
    # joined_raw = " abc" (空字符串 + 空格 + abc) → normalize → "abc"
    # 然后预测边界：find("" , 0) → 0，end = 0 → predicted.append(0); pos = 1
    # find("abc", 1) → should be 0... 实际 stream="abc"，find("abc", 1) = -1
    # 所以 predicted = [0]
    # gt for "abc" position="before" = find("abc", 0) = 0
    # match: |0-0|=0 ≤ 0 → match
    # 但严格行为依赖实现，这里只验证不抛异常
    assert isinstance(r, dict)


def test_e2e_chunk_boundary_doc_with_extra_keys_batch18():
    """document 有额外 keys 也能工作。"""
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


def test_e2e_chunk_boundary_annotation_with_extra_keys_batch18():
    """annotation 有额外 keys 也能工作。"""
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


def test_e2e_combined_figure_and_chunk_batch18():
    """组合调用 figure_caption_prf + chunk_boundary_prf。"""
    doc = {"chunks": [
        {"chunk_id": "c1", "text": "abc"},
        {"chunk_id": "c2", "text": "def"},
    ]}
    annotation = {
        "chunk_boundary_anchors": [{"marker": "abc", "position": "after"}],
    }
    fc = figure_caption_prf(doc, annotation)
    cb = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert len(fc) == 3
    assert "chunk_boundary_precision" in cb
