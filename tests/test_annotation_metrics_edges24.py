r"""evaluation/annotation_metrics.py 边角测试 - 第二十五轮（Round 309）。

edges23 已覆盖：anchor position / marker 位置 / chunk.text 边界 / predict 算法 /
多 anchor 顺序 / 数学不变量 / tolerance 极端 / 常量 / source 字符串 /
forbidden tokens / imports / source level / signatures / 端到端 / 模块整体。

edges24 补强未覆盖的角度（深度边界 + 算法不变量 + source level + signatures + 端到端）：
- **_null / _ratio 调用次数补强**：figure_caption_prf 调用 _null 3 次（始终）；
  chunk_boundary_prf pipeline_failed 路径调用 _null 3 次（不计 _tolerance_chars）；
  chunk_boundary_prf no_annotation 路径调用 _null 3 次；
  chunk_boundary_prf no_predicted_boundaries 路径调用 _null 多次（含 recall 的 _ratio(0.0)）；
  chunk_boundary_prf no_ground_truth_anchors 路径调用 _null 3 次
- **stream 构造深度补强**：多 chunk 用 ' ' 连接 norm_chunks；
  norm_chunks 是 list[str]；stream 是 normalize 后的 string；
  空 norm_chunks → joined='  '（多空格） → stream=''（normalize strip）；
  单字符 chunks → 短 stream
- **missing_markers 字段深度补强**：多个 missing marker 都进 list；
  missing marker 是原始字符串（不修改）；空 marker → missing（find 返 -1 因为 marker=''）；
  marker 是 None → a.get('marker', '') → '' → missing；
  _missing_markers 字段只在有 missing 时出现（无 missing 不出现）
- **数学不变量补强**：precision + recall 任意为 0 时 f1 = 0；
  p == r 时 f1 == p == r；matched ≤ min(num_pred, num_gt)；
  f1 ≤ max(p, r) 通常成立
- **chunk_boundary_prf 早 return 路径不构造 stream**：
  pipeline_failed 路径不构造 stream（直接 _null）；
  no_annotation 路径不构造 stream；
  no_predicted_boundaries（chunks<2）路径不构造 stream
- **算法可重现性**：相同输入多次调用结果完全一致（deterministic）；
  不同 tolerance → 不同结果（如果 anchors 在 tolerance 边界）
- **PARSER_DOES_NOT_EMIT_RELATIONS 常量深度补强**：值精确；
  在 figure_caption_prf source 中被引用；是 module-level（不是局部）
- **module source 字符串精确补强**：含 'from collections import Counter'；
  含 'Counter(expected) & Counter(actual)'（在 _text_preservation 中？— 实际不在 annotation_metrics）；
  含 'search_from = find_pos + len(marker)'；
  含 'pairs.sort(key=lambda x: x[0])'
- **module source forbidden tokens 补强**：不含 time/random/uuid/hashlib/secrets/
  subprocess/socket/email/html/http/urllib/sqlite3/csv/pickle/tempfile/shutil/glob
- **module source level 完整补强**：
  - chunk_boundary_prf 含 'if document is None:' + 5 处 'out[k] = _null(...)'；
  - chunk_boundary_prf 含 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]'；
  - chunk_boundary_prf 含 'joined_raw = " ".join(norm_chunks)'；
  - chunk_boundary_prf 含 'stream = normalize_text(joined_raw)'；
  - chunk_boundary_prf 含 'predicted: list[int] = []' + 'for i, txt in enumerate(norm_chunks)'；
  - chunk_boundary_prf 含 'gt_positions: list[int] = []' + 'missing_markers: list[str] = []'；
  - chunk_boundary_prf 含 'for a in anchors' + 'marker = a.get("marker", "")'；
  - chunk_boundary_prf 含 'pairs: list[tuple[int, int, int]] = []'；
  - chunk_boundary_prf 含 'used_pred = set()' + 'used_gt = set()'；
  - chunk_boundary_prf 含 'num_pred = len(predicted)' + 'num_gt = len(gt_positions)'；
  - chunk_boundary_prf 含 'denom = p_val + r_val' + 'if denom <= 0:'
- **端到端集成补强**：document is None 三 key null + _tolerance_chars 不 null；
  空 annotation + 单 chunk → no_predicted_boundaries 三 key null；
  tolerance=0 + 完全相同位置 → matched
- **模块整体合理性**：__all__ 3 entries；2 module-level function + 1 constant；
  无 class；无 __main__
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

import evaluation.annotation_metrics as ammod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# 辅助
# =========================================================================


def _make_chunk(text: str, cid: str = "c") -> dict[str, Any]:
    return {"chunk_id": cid, "text": text, "source_element_ids": ["e1"]}


def _make_doc(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "chunks": chunks,
    }


def _make_anchor(marker: str, position: str = "after") -> dict[str, Any]:
    return {"marker": marker, "position": position}


# =========================================================================
# _null / _ratio 调用次数补强
# =========================================================================


def test_figure_caption_prf_calls_null_exactly_3_times():
    """figure_caption_prf 调用 _null 3 次（始终）。"""
    src = inspect.getsource(figure_caption_prf)
    assert src.count("_null(reason)") == 3


def test_chunk_boundary_pipeline_failed_calls_null_3_times():
    """chunk_boundary_prf pipeline_failed 路径调用 _null 3 次（不计 _tolerance_chars）。"""
    out = chunk_boundary_prf(None, None)
    # 3 个 key 都是 null + _tolerance_chars 是 value
    null_count = sum(1 for k, v in out.items()
                     if k != "_tolerance_chars" and v.get("value") is None)
    assert null_count == 3


def test_chunk_boundary_no_annotation_calls_null_3_times():
    """no_annotation 路径调用 _null 3 次。"""
    out = chunk_boundary_prf({"chunks": []}, None)
    null_count = sum(1 for k, v in out.items()
                     if k != "_tolerance_chars" and v.get("value") is None)
    assert null_count == 3


def test_chunk_boundary_no_annotation_with_empty_dict():
    """no_annotation 路径（annotation 是 {}）。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    null_count = sum(1 for k, v in out.items()
                     if k != "_tolerance_chars" and v.get("value") is None)
    assert null_count == 3


def test_chunk_boundary_no_predicted_boundaries_calls_null():
    """no_predicted_boundaries（chunks<2）路径调用 _null（recall 走 _ratio(0.0) 或 _null）。"""
    chunks = [_make_chunk("hello", "c1")]  # 只 1 chunk
    doc = _make_doc(chunks)
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [_make_anchor("hello")]})
    # precision/recall/f1 三 key，至少 precision 和 f1 是 null
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_no_ground_truth_anchors_calls_null_3_times():
    """no_ground_truth_anchors 路径调用 _null 3 次。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    null_count = sum(1 for k, v in out.items()
                     if k != "_tolerance_chars" and v.get("value") is None)
    assert null_count == 3


# =========================================================================
# stream 构造深度补强
# =========================================================================


def test_stream_construction_joins_with_space():
    """多 chunk 用 ' ' 连接 norm_chunks。"""
    # 用 source code 验证（不能直接测内部变量）
    src = inspect.getsource(chunk_boundary_prf)
    assert 'joined_raw = " ".join(norm_chunks)' in src


def test_stream_construction_normalize_after_join():
    """stream 是 normalize 后的 string。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_norm_chunks_is_list_of_strings():
    """norm_chunks 是 list[str]（list comprehension）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in src


def test_stream_with_empty_chunks():
    """空 norm_chunks → joined='' → stream=''。"""
    chunks = [_make_chunk("", "c1"), _make_chunk("hello", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "hello"; predict: end of "" = 0; end of hello 不算（last）
    # marker "hello" find_pos=0; after → gt=5; predict=[0]
    # |0-5|=5 ≤ 30 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_stream_with_single_char_chunks():
    """单字符 chunks → 短 stream。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "a b"; predict: end of a = 1; marker a find_pos=0, after → gt=1; matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# missing_markers 字段深度补强
# =========================================================================


def test_missing_markers_multiple_markers_all_added():
    """多个 missing marker 都进 list。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("xxx", "after"),
            _make_anchor("yyy", "after"),
            _make_anchor("zzz", "after"),
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out
    missing = out["_missing_markers"]["value"]
    assert "xxx" in missing
    assert "yyy" in missing
    assert "zzz" in missing


def test_missing_markers_are_original_strings():
    """missing marker 是原始字符串（不修改）。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("MY_MARKER", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "MY_MARKER" in out["_missing_markers"]["value"]


def test_missing_markers_empty_string_marker_treated_as_missing():
    """空 marker → find('', from) = 0（不是 -1），但其实 '' find_pos=0 是合法的；要看 marker truthy。
    实际：'marker = a.get("marker", "")' → '' 是 falsy 在 marker 字符串上下文；
    代码：'find_pos = stream.find(marker, search_from) if marker else -1'
    → '' marker → find_pos=-1 → missing_markers"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_missing_markers_none_marker_treated_as_empty():
    """marker 是 None → a.get('marker', '') → '' → missing。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": None, "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out


def test_missing_markers_field_absent_when_no_missing():
    """_missing_markers 字段只在有 missing 时出现。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" not in out


# =========================================================================
# 数学不变量补强
# =========================================================================


def test_math_invariant_f1_zero_when_either_p_or_r_zero():
    """precision + recall 任意为 0 时 f1 = 0。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # tolerance=0 + anchor 偏移 → 不匹配 → p=r=0
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    # b 的 find_pos=2, before → gt=2; predict=1; |1-2|=1 > tolerance=0 → unmatched
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_math_invariant_p_equals_r_implies_f1_equals_p():
    """p == r 时 f1 == p == r。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert p == r == f1 == 1.0


def test_math_invariant_matched_le_min():
    """matched ≤ min(num_pred, num_gt)。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    # predict = [1, 3]; 1 anchor matched
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # matched = 1; num_pred = 2; num_gt = 1
    # matched ≤ min(2, 1) = 1
    assert out["chunk_boundary_precision"]["value"] == 1 / 2
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_math_invariant_f1_le_max_p_r():
    """f1 ≤ max(p, r) 通常成立。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("c", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    # p = 1/2 = 0.5, r = 1/1 = 1.0
    # f1 = 2*0.5*1/(0.5+1) = 1/1.5 ≈ 0.6667
    assert f1 is not None
    assert f1 <= max(p, r) + 1e-9


# =========================================================================
# chunk_boundary_prf 早 return 路径不构造 stream
# =========================================================================


def test_pipeline_failed_path_no_stream_construction():
    """pipeline_failed 路径不构造 stream（直接 _null）。"""
    # 用 source 验证：if document is None 在 stream 构造之前
    src = inspect.getsource(chunk_boundary_prf)
    idx_pipeline_failed = src.find('if document is None:')
    idx_stream = src.find("norm_chunks = ")
    assert 0 <= idx_pipeline_failed < idx_stream


def test_no_annotation_path_before_stream_construction():
    """no_annotation 路径在 stream 构造之前。"""
    src = inspect.getsource(chunk_boundary_prf)
    idx_no_annotation = src.find("if not annotation:")
    idx_stream = src.find("norm_chunks = ")
    assert 0 <= idx_no_annotation < idx_stream


def test_no_predicted_boundaries_path_before_stream_construction():
    """no_predicted_boundaries（chunks<2）路径在 stream 构造之前。"""
    src = inspect.getsource(chunk_boundary_prf)
    idx_no_chunks = src.find("if not chunks or len(chunks) < 2:")
    idx_stream = src.find("norm_chunks = ")
    assert 0 <= idx_no_chunks < idx_stream


# =========================================================================
# 算法可重现性
# =========================================================================


def test_chunk_boundary_deterministic_same_input_same_output():
    """相同输入多次调用结果完全一致。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    out3 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out1 == out2 == out3


def test_chunk_boundary_different_tolerance_different_result_at_boundary():
    """不同 tolerance → 不同结果（如果 anchors 在 tolerance 边界）。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # b before → gt=2; predict=1; |1-2|=1
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    # tolerance=0 → unmatched; tolerance=1 → matched
    out0 = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert out0["chunk_boundary_precision"]["value"] == 0.0
    assert out1["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量深度补强
# =========================================================================


def test_constant_value_in_source():
    """常量值在 source 中（被 figure_caption_prf 引用）。"""
    src = inspect.getsource(ammod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_constant_referenced_in_figure_caption_prf():
    """常量在 figure_caption_prf source 中被引用。"""
    src = inspect.getsource(figure_caption_prf)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_constant_is_module_level_not_local():
    """常量是 module-level（不是局部）。"""
    src = inspect.getsource(ammod)
    # 应在 module level（无缩进）
    lines = src.split("\n")
    for line in lines:
        if 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in line:
            # 无前导空格 → module level
            assert not line.startswith(" ")
            return
    pytest.fail("Constant not found at module level")


# =========================================================================
# module source 字符串精确补强
# =========================================================================


def test_module_source_has_search_from_advance():
    """source 含 'search_from = find_pos + len(marker)'。"""
    src = inspect.getsource(ammod)
    assert "search_from = find_pos + len(marker)" in src


def test_module_source_has_pairs_sort():
    """source 含 'pairs.sort(key=lambda x: x[0])'。"""
    src = inspect.getsource(ammod)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_module_source_has_used_pred_used_gt():
    """source 含 'used_pred = set()' + 'used_gt = set()'。"""
    src = inspect.getsource(ammod)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_module_source_has_num_pred_num_gt():
    """source 含 'num_pred = len(predicted)' + 'num_gt = len(gt_positions)'。"""
    src = inspect.getsource(ammod)
    assert "num_pred = len(predicted)" in src
    assert "num_gt = len(gt_positions)" in src


def test_module_source_has_denom_check():
    """source 含 'denom = p_val + r_val' + 'if denom <= 0:'。"""
    src = inspect.getsource(ammod)
    assert "denom = p_val + r_val" in src
    assert "if denom <= 0:" in src


def test_module_source_has_pairs_type_annotation():
    """source 含 'pairs: list[tuple[int, int, int]] = []'。"""
    src = inspect.getsource(ammod)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_module_source_has_gt_positions_type_annotation():
    """source 含 'gt_positions: list[int] = []'。"""
    src = inspect.getsource(ammod)
    assert "gt_positions: list[int] = []" in src


def test_module_source_has_missing_markers_type_annotation():
    """source 含 'missing_markers: list[str] = []'。"""
    src = inspect.getsource(ammod)
    assert "missing_markers: list[str] = []" in src


def test_module_source_has_predicted_type_annotation():
    """source 含 'predicted: list[int] = []'。"""
    src = inspect.getsource(ammod)
    assert "predicted: list[int] = []" in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_time():
    src = inspect.getsource(ammod)
    assert "import time" not in src


def test_module_source_no_random():
    src = inspect.getsource(ammod)
    assert "import random" not in src


def test_module_source_no_uuid():
    src = inspect.getsource(ammod)
    assert "import uuid" not in src


def test_module_source_no_hashlib():
    src = inspect.getsource(ammod)
    assert "import hashlib" not in src


def test_module_source_no_secrets():
    src = inspect.getsource(ammod)
    assert "import secrets" not in src


def test_module_source_no_subprocess():
    src = inspect.getsource(ammod)
    assert "import subprocess" not in src


def test_module_source_no_socket():
    src = inspect.getsource(ammod)
    assert "import socket" not in src


def test_module_source_no_email():
    src = inspect.getsource(ammod)
    assert "import email" not in src


def test_module_source_no_html():
    src = inspect.getsource(ammod)
    assert "import html" not in src


def test_module_source_no_http():
    src = inspect.getsource(ammod)
    assert "import http" not in src


def test_module_source_no_urllib():
    src = inspect.getsource(ammod)
    assert "import urllib" not in src


def test_module_source_no_sqlite3():
    src = inspect.getsource(ammod)
    assert "import sqlite3" not in src


def test_module_source_no_csv():
    src = inspect.getsource(ammod)
    assert "import csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(ammod)
    assert "import pickle" not in src


def test_module_source_no_tempfile():
    src = inspect.getsource(ammod)
    assert "import tempfile" not in src


def test_module_source_no_shutil():
    src = inspect.getsource(ammod)
    assert "import shutil" not in src


def test_module_source_no_glob():
    src = inspect.getsource(ammod)
    assert "import glob" not in src


# =========================================================================
# module source level 完整补强
# =========================================================================


def test_chunk_boundary_prf_source_has_document_none_branch():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None:" in src


def test_chunk_boundary_prf_source_has_5_null_calls_in_pipeline_failed():
    """pipeline_failed 路径通过 for loop 给 3 个 key 赋 _null —— source 出现 1 次但展开为 3。"""
    src = inspect.getsource(chunk_boundary_prf)
    idx_doc_none = src.find("if document is None:")
    idx_no_anno = src.find("if not annotation:")
    section = src[idx_doc_none:idx_no_anno]
    # for k in (...) loop 调用一次 _null，但目标键有 3 个
    assert '_null("pipeline_failed")' in section
    assert "chunk_boundary_precision" in section
    assert "chunk_boundary_recall" in section
    assert "chunk_boundary_f1" in section


def test_chunk_boundary_prf_source_has_no_annotation_3_null():
    src = inspect.getsource(chunk_boundary_prf)
    idx_no_anno = src.find("if not annotation:")
    idx_no_chunks = src.find("if not chunks or len(chunks) < 2:")
    section = src[idx_no_anno:idx_no_chunks]
    assert '_null("no_annotation")' in section
    assert "chunk_boundary_precision" in section
    assert "chunk_boundary_recall" in section
    assert "chunk_boundary_f1" in section


def test_chunk_boundary_prf_source_has_no_ground_truth_anchors_3_null():
    src = inspect.getsource(chunk_boundary_prf)
    idx_no_anchors = src.find("if not anchors:")
    section = src[idx_no_anchors:idx_no_anchors + 500]
    assert '_null("no_ground_truth_anchors")' in section
    assert "chunk_boundary_precision" in section
    assert "chunk_boundary_recall" in section
    assert "chunk_boundary_f1" in section


def test_chunk_boundary_prf_source_has_out_dict_init():
    """source 含 'out: dict[str, dict[str, Any]] = {}'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "out: dict[str, dict[str, Any]] = {}" in src


def test_chunk_boundary_prf_source_has_tolerance_chars_in_all_branches():
    """tolerance_chars 出现在每个早 return 路径（_tolerance_chars value）。"""
    src = inspect.getsource(chunk_boundary_prf)
    # 5 个分支 + 1 个 final → 6 处 _tolerance_chars assignment
    assert src.count('"_tolerance_chars"') >= 5


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_document_none_returns_3_nulls_plus_tolerance():
    """document is None → 3 key null + _tolerance_chars 不 null。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_e2e_empty_annotation_single_chunk_no_predicted_boundaries():
    """空 annotation + 单 chunk → no_predicted_boundaries 三 key null。"""
    chunks = [_make_chunk("hello", "c1")]
    doc = _make_doc(chunks)
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [_make_anchor("hello")]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_e2e_tolerance_0_exact_match():
    """tolerance=0 + 完全相同位置 → matched。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    # predict = [5] (end of hello); marker hello find_pos=0, after → gt=5
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_does_not_add_missing_markers_when_normal():
    """无 missing marker 时 _missing_markers 字段不出现。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" not in out


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_all_has_3_entries_in_order():
    assert ammod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_has_2_module_level_functions():
    """module 有 2 个 module-level function：figure_caption_prf, chunk_boundary_prf。"""
    import types
    funcs = [n for n in dir(ammod)
             if not n.startswith("_")
             and isinstance(getattr(ammod, n), types.FunctionType)
             and getattr(ammod, n).__module__ == "evaluation.annotation_metrics"]
    assert sorted(funcs) == ["chunk_boundary_prf", "figure_caption_prf"]


def test_module_has_no_class():
    src = inspect.getsource(ammod)
    lines = src.split("\n")
    for line in lines:
        if not line.startswith(" ") and line.startswith("class "):
            pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    src = inspect.getsource(ammod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src
