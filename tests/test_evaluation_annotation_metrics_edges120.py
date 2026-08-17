"""evaluation/annotation_metrics.py 第四百一十七轮 edges 测试（Round 973）。

补强 edges119 未触及的角度（第三百四十九批，probe 实证）。

新角度：
- chunks 显式 None → `or []` 兜底 → len<2 分支：
  P null no_predicted_boundaries + R 0.0（anchors 在）
- annotation 携带其余合法键（figure_caption_pairs /
  heading_order / annotator / date）被 chunk_boundary
  完全忽略（只读 chunk_boundary_anchors）
- anchors 传 dict 而非 list → dict 真值绕过 or [] →
  for 迭代产出键（str）→ a.get 崩 AttributeError
  （'str' object has no attribute 'get'，锁定现状）
- position "before" gt 0 与预测位 2 距 2 → 命中 1.0
- forbidden tokens 第四百四十三批（open 0）
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


# ---------- chunks None ----------

def test_chunks_none_falsy_fallback_batch171():
    out = chunk_boundary_prf(
        {"chunks": None},
        {"chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"}]})
    assert out["chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}


# ---------- annotation 其余键忽略 ----------

def test_annotation_other_keys_ignored_batch171():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "AB"}, {"text": "CD"}]},
        {"chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"}],
         "figure_caption_pairs": [{"figure_marker": "f",
                                   "caption_text": "c"}],
         "heading_order": [{"level": 1, "text": "H"}],
         "annotator": "me", "date": "2026-01-01"})
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- anchors 传 dict 崩溃 ----------

def test_anchors_dict_attribute_error_batch171():
    with pytest.raises(AttributeError) as ei:
        chunk_boundary_prf(
            {"chunks": [{"text": "AB"}, {"text": "CD"}]},
            {"chunk_boundary_anchors": {
                "marker": "AB", "position": "after"}})
    assert "'str' object has no attribute 'get'" in \
        str(ei.value)


# ---------- before gt 0 ----------

def test_before_position_zero_gt_batch171():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "AB"}, {"text": "CD"}]},
        {"chunk_boundary_anchors": [
            {"marker": "AB", "position": "before"}]})
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch171():
    src = _src()
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src
    assert 'chunks = document.get("chunks") or []' in src
    assert 'marker = a.get("marker", "")' in src
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src


# ---------- forbidden tokens 第四百四十三批 ----------

def test_source_no_eval_batch171():
    assert "eval(" not in _src()


def test_source_no_exec_batch171():
    assert "exec(" not in _src()


def test_source_no_compile_batch171():
    assert "compile(" not in _src()


def test_source_no_globals_batch171():
    assert "globals(" not in _src()


def test_source_no_locals_batch171():
    assert "locals(" not in _src()


def test_source_no_os_system_batch171():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch171():
    assert "subprocess" not in _src()


def test_source_no_popen_batch171():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch171():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch171():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch171():
    assert "socket" not in _src()


def test_source_no_requests_batch171():
    assert "requests" not in _src()


def test_source_no_urllib_batch171():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch171():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch171():
    assert "yield" not in _src()


def test_source_no_async_await_batch171():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch171():
    assert "open(" not in _src()
