"""evaluation/annotation_metrics.py 第二百九十一轮 edges 测试（Round 847）。

补强 edges101 未触及的角度（第二百二十一批）。

新角度：
- 3 chunk 2 边界 2 锚 tol=0 全精确 → P=R=F1=1.0
- 容差边界等值：d=2 时 tol=2 命中（<= 含等）、tol=1 未命中
- 锚顺序依赖（search_from 单向推进）：先标 "CD" 再标
  "AB" → "AB" 在流中存在却 missing（其唯一出现位置已被
  跳过），同时已定位锚仍可全 1.0
- 部分缺失：先命中后缺失 → _missing_markers 只列后者
- P=1 R=0.5 形态（第二个锚在容差外）
- forbidden tokens 第三百一十七批
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


# ---------- 多边界全精确 ----------

def test_two_boundaries_exact_tol0_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "AB"}, {"marker": "CD"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 容差边界等值 ----------

def test_tolerance_equality_inclusive_batch55():
    # pred=2, gt=4（"DE" before → find@4）→ d=2
    ann = _ann({"marker": "DE", "position": "before"})
    hit = chunk_boundary_prf(_doc("AB", "CDE"), ann, 2)
    miss = chunk_boundary_prf(_doc("AB", "CDE"), ann, 1)
    assert hit["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    assert miss["chunk_boundary_f1"] == {"value": 0.0,
                                         "reason": None}


# ---------- 锚顺序依赖 ----------

def test_anchor_order_search_from_skip_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "CD"}, {"marker": "AB"}), 3)
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 部分缺失 ----------

def test_partial_missing_only_later_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB"}, {"marker": "ZZ"}), 3)
    assert out["_missing_markers"] == {"value": ["ZZ"],
                                       "reason": None}


# ---------- P=1 R=0.5 ----------

def test_precision_one_recall_half_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CDE"),
        _ann({"marker": "CD", "position": "before"},
             {"marker": "E"}), 1)
    # pred=[2]; gt=[3, 6]; 只有 d=1 的第一对命中，E 锚 d=4 出界
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(2 / 3)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert "if d <= tolerance_chars:" in src
    assert "used_gt.add(gi)" in src
    assert "search_from = find_pos + len(marker)" in src


# ---------- forbidden tokens 第三百一十七批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
