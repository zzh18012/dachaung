"""evaluation/annotation_metrics.py 第三百四十七轮 edges 测试（Round 903）。

补强 edges109 未触及的角度（第二百七十九批，probe 实证）。

新角度：
- before 整流 marker：gt=0，pred=2（tol 2 全 1.0 / tol 1 全 0.0）
- 重复内容 chunks ["AB","AB"] + 同 marker 两次：gts [2,5]
  vs preds [2] → P 1.0 R 0.5
- 距离恰等容差命中（<=）、超出一档即 miss（d=1：tol 1 命中
  / tol 0 miss）
- anchors 传 dict（迭代出 key 字符串）→ AttributeError 未防护
- 全空白 chunks：stream 空 → P 0.0 / R null
  no_ground_truth_anchors_in_stream / F1 null
  precision_or_recall_not_evaluated + _missing_markers ["X"]
- document chunks 为 None → or [] → no_predicted_boundaries
  三件套（recall 0.0）
- forbidden tokens 第三百七十三批
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


# ---------- before 整流 ----------

def test_before_whole_stream_marker_batch101():
    ann = _ann({"marker": "AB CD", "position": "before"})
    hit = chunk_boundary_prf(_doc("AB", "CD"), ann, 2)
    assert hit["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert hit["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert hit["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    miss = chunk_boundary_prf(_doc("AB", "CD"), ann, 1)
    assert miss["chunk_boundary_f1"] == {"value": 0.0,
                                         "reason": None}


# ---------- 重复内容 chunk ----------

def test_repeated_content_chunks_batch101():
    out = chunk_boundary_prf(
        _doc("AB", "AB"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}


# ---------- 距离恰等容差 ----------

def test_distance_equals_tolerance_batch101():
    ann = _ann({"marker": "CD", "position": "before"})  # gt=3, pred=2
    hit = chunk_boundary_prf(_doc("AB", "CD"), ann, 1)
    assert hit["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    miss = chunk_boundary_prf(_doc("AB", "CD"), ann, 0)
    assert miss["chunk_boundary_f1"] == {"value": 0.0,
                                         "reason": None}


# ---------- anchors 传 dict ----------

def test_anchors_dict_attributeerror_batch101():
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            _doc("AB", "CD"),
            {"chunk_boundary_anchors": {"marker": "AB"}}, 0)


# ---------- 全空白 chunks ----------

def test_whitespace_only_chunks_batch101():
    out = chunk_boundary_prf(
        _doc(" ", " "),
        _ann({"marker": "X", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": ["X"],
                                       "reason": None}


# ---------- chunks None ----------

def test_chunks_none_batch101():
    out = chunk_boundary_prf(
        {"chunks": None},
        _ann({"marker": "A", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch101():
    src = _src()
    assert 'chunks = document.get("chunks") or []' in src
    assert "missing_markers.append(marker)" in src
    assert "used_pred.add(pi)" in src
    assert "if p_val is None or r_val is None:" in src


# ---------- forbidden tokens 第三百七十三批 ----------

def test_source_no_eval_batch101():
    assert "eval(" not in _src()


def test_source_no_exec_batch101():
    assert "exec(" not in _src()


def test_source_no_compile_batch101():
    assert "compile(" not in _src()


def test_source_no_globals_batch101():
    assert "globals(" not in _src()


def test_source_no_locals_batch101():
    assert "locals(" not in _src()


def test_source_no_os_system_batch101():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch101():
    assert "subprocess" not in _src()


def test_source_no_popen_batch101():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch101():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch101():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch101():
    assert "socket" not in _src()


def test_source_no_requests_batch101():
    assert "requests" not in _src()


def test_source_no_urllib_batch101():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch101():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch101():
    assert "yield" not in _src()


def test_source_no_async_await_batch101():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch101():
    assert "open(" not in _src()
