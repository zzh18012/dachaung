"""evaluation/annotation_metrics.py 第三百一十二轮 edges 测试（Round 868）。

补强 edges104 未触及的角度（第二百四十三批，probe 实证）。

新角度：
- 首 chunk 空文本：pred 落在 0 位（find("")=0），
  与 after-anchor 的 gt=2 距离 2 → tol 2 全 1.0 / tol 0 全 0.0
- marker "CD" before：gt=3 与 pred [2,5] → tol 1 只命中
  近端 → P 0.5、R 1.0、F1 2/3
- marker 位于流起始 before → gt=0，tol 2 命中 pred=2
- 巨容差 1000：一对一约束仍然生效（1 anchor 只吞 1 pred）
  → P 0.5、R 1.0
- forbidden tokens 第三百三十八批
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


# ---------- 首 chunk 空 ----------

def test_leading_empty_chunk_far_anchor_batch66():
    out = chunk_boundary_prf(
        _doc("", "AB"),
        _ann({"marker": "AB", "position": "after"}), 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


def test_leading_empty_chunk_tol0_miss_batch66():
    out = chunk_boundary_prf(
        _doc("", "AB"),
        _ann({"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- 跨界近端 ----------

def test_before_anchor_between_preds_batch66():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "CD", "position": "before"}), 1)
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(2 / 3)


# ---------- 流起始 before ----------

def test_before_anchor_at_stream_start_batch66():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "before"}), 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 巨容差一对一 ----------

def test_huge_tolerance_one_to_one_batch66():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "CD", "position": "after"}), 1000)
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(2 / 3)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch66():
    src = _src()
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if pi in used_pred or gi in used_gt:" in src
    assert 'out[k] = _null("pipeline_failed")' in src


# ---------- forbidden tokens 第三百三十八批 ----------

def test_source_no_eval_batch66():
    assert "eval(" not in _src()


def test_source_no_exec_batch66():
    assert "exec(" not in _src()


def test_source_no_compile_batch66():
    assert "compile(" not in _src()


def test_source_no_globals_batch66():
    assert "globals(" not in _src()


def test_source_no_locals_batch66():
    assert "locals(" not in _src()


def test_source_no_os_system_batch66():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch66():
    assert "subprocess" not in _src()


def test_source_no_popen_batch66():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch66():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch66():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch66():
    assert "socket" not in _src()


def test_source_no_requests_batch66():
    assert "requests" not in _src()


def test_source_no_urllib_batch66():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch66():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch66():
    assert "yield" not in _src()


def test_source_no_async_await_batch66():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch66():
    assert "open(" not in _src()
