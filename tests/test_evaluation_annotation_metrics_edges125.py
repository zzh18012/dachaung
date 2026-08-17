"""evaluation/annotation_metrics.py 第四百五十二轮 edges 测试（Round 1008）。

补强 edges124 未触及的角度（第三百八十四批，probe 实证）。

新角度：
- tolerance_chars=-1（负容差）→ d <= -1 永不成立 →
  P/R/F1 三 0.0（分母仍在，值全 0）
- 全空 chunks ["",""]：predict 边界仍在（find("")=0）→
  precision 0.0；marker 找不到 → recall null
  "no_ground_truth_anchors_in_stream"；f1 null
  "precision_or_recall_not_evaluated" —— 三键三态
- 同一边界 mixed before/after 双锚（after ABC=3、
  before DEF=4）→ 贪心一对一到两个不同 pred → 全 1.0
- 远端双锚 tol=2：仅 AAAA 后界命中 → P=1/3、R=1/2、
  F1 精确 0.4（2PR/(P+R)）
- forbidden tokens 第四百七十八批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _run(chunks, anchors, tolerance=30):
    doc = {"chunks": [{"text": t} for t in chunks]}
    return chunk_boundary_prf(
        doc, {"chunk_boundary_anchors": anchors},
        tolerance_chars=tolerance)


# ---------- 负容差 ----------

def test_negative_tolerance_all_zero_batch206():
    out = _run(["AB", "CD"],
               [{"marker": "AB", "position": "after"}],
               tolerance=-1)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- 全空 chunks 三态 ----------

def test_all_empty_chunks_three_way_batch206():
    out = _run(["", ""], [{"marker": "X", "position": "after"}])
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- 同界 mixed before/after ----------

def test_mixed_before_after_same_boundary_batch206():
    out = _run(["ABC", "DEF", "GHI"], [
        {"marker": "ABC", "position": "after"},
        {"marker": "DEF", "position": "before"}])
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 远端双锚 F1 0.4 ----------

def test_far_pair_f1_exact_batch206():
    out = _run(["AAAA", "BBBB", "CCCC", "DDDD"], [
        {"marker": "AAAA", "position": "after"},
        {"marker": "DDDD", "position": "after"}], tolerance=2)
    assert out["chunk_boundary_precision"] == {
        "value": 0.3333333333333333, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.4,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch206():
    src = _src()
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "used_gt = set()" in src
    assert 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}' in src
    assert src.count('out["_tolerance_chars"]') == 5


# ---------- forbidden tokens 第四百七十八批 ----------

def test_source_no_eval_batch206():
    assert "eval(" not in _src()


def test_source_no_exec_batch206():
    assert "exec(" not in _src()


def test_source_no_compile_batch206():
    assert "compile(" not in _src()


def test_source_no_globals_batch206():
    assert "globals(" not in _src()


def test_source_no_locals_batch206():
    assert "locals(" not in _src()


def test_source_no_os_system_batch206():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch206():
    assert "subprocess" not in _src()


def test_source_no_popen_batch206():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch206():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch206():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch206():
    assert "socket" not in _src()


def test_source_no_requests_batch206():
    assert "requests" not in _src()


def test_source_no_urllib_batch206():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch206():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch206():
    assert "yield" not in _src()


def test_source_no_async_await_batch206():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch206():
    assert "open(" not in _src()
