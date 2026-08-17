"""evaluation/annotation_metrics.py 第三百零五轮 edges 测试（Round 861）。

补强 edges103 未触及的角度（第二百三十六批）。

新角度：
- 重复 marker 顺序定位：两个 "AB" 各自找到第 1/2 次出现
  （search_from 推进语义）→ P 2/3、R 1.0、F1 0.8
- marker 在规范化流上定位：chunk 原文多空格 "A   B" →
  marker 用单空格 "A B" 才能命中
- document None 早退也带 _tolerance_chars 记录
- 空 marker ""：falsy → find_pos=-1 → 进 _missing_markers
  （空字符串条目）
- tolerance_chars 为负：精确命中也判失配 → 全 0.0
- forbidden tokens 第三百三十一批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 重复 marker 顺序定位 ----------

def test_duplicate_marker_sequential_batch59():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "AB", "EF"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": pytest.approx(2 / 3), "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(0.8)


# ---------- 规范化流定位 ----------

def test_marker_on_normalized_stream_batch59():
    out = chunk_boundary_prf(
        _doc("A   B", "C"),
        _ann({"marker": "A B", "position": "after"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- document None 早退带容差记录 ----------

def test_none_doc_records_tolerance_batch59():
    out = chunk_boundary_prf(None, _ann(), 5)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "pipeline_failed"}
    assert out["_tolerance_chars"] == {"value": 5,
                                       "reason": None}


# ---------- 空 marker ----------

def test_empty_marker_lands_in_missing_batch59():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "", "position": "before"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"
    assert out["_missing_markers"] == {"value": [""],
                                       "reason": None}


# ---------- 负容差 ----------

def test_negative_tolerance_exact_still_miss_batch59():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after"}), -1)
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch59():
    src = _src()
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


# ---------- forbidden tokens 第三百三十一批 ----------

def test_source_no_eval_batch59():
    assert "eval(" not in _src()


def test_source_no_exec_batch59():
    assert "exec(" not in _src()


def test_source_no_compile_batch59():
    assert "compile(" not in _src()


def test_source_no_globals_batch59():
    assert "globals(" not in _src()


def test_source_no_locals_batch59():
    assert "locals(" not in _src()


def test_source_no_os_system_batch59():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch59():
    assert "subprocess" not in _src()


def test_source_no_popen_batch59():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch59():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch59():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch59():
    assert "socket" not in _src()


def test_source_no_requests_batch59():
    assert "requests" not in _src()


def test_source_no_urllib_batch59():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch59():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch59():
    assert "yield" not in _src()


def test_source_no_async_await_batch59():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch59():
    assert "open(" not in _src()
