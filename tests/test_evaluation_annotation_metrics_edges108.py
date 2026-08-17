"""evaluation/annotation_metrics.py 第三百三十三轮 edges 测试（Round 889）。

补强 edges107 未触及的角度（第二百六十四批）。

新角度：
- 重复 marker 第二次找不到：只算 missing 不减 recall
  （全 1.0 + _missing_markers 记录）
- marker 等于整条 stream：after 落在末尾 → 命中
- marker 不做归一化：stream 归一成 "A B" 后，
  空格 marker 命中、制表符 marker missing（不对称锁定）
- forbidden tokens 第三百五十九批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 重复 marker 第二次缺失 ----------

def test_duplicate_marker_second_missing_batch87():
    out = chunk_boundary_prf(
        _doc("ABX", "CD"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}), 1)
    assert out["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}


# ---------- 整流 marker ----------

def test_marker_whole_stream_overshoots_batch87():
    # after → gt=5（流末），唯一 pred=2，d=3 → tol 0 全 0.0
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB CD", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    out3 = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB CD", "position": "after"}), 3)
    assert out3["chunk_boundary_f1"] == {"value": 1.0,
                                         "reason": None}


# ---------- marker 不归一 ----------

def test_marker_not_normalized_space_hits_batch87():
    out = chunk_boundary_prf(
        _doc("A\tB", "C"),
        _ann({"marker": "A B", "position": "after"}), 0)
    # stream 归一后是 "A B C"，边界在 3；marker 命中
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


def test_marker_not_normalized_tab_misses_batch87():
    out = chunk_boundary_prf(
        _doc("A\tB", "C"),
        _ann({"marker": "A\tB", "position": "after"}), 0)
    # stream 已无制表符，marker 原样找不到 → gt 空
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_f1"]["reason"] == \
        "precision_or_recall_not_evaluated"
    assert out["_missing_markers"] == {
        "value": ["A\tB"], "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch87():
    src = _src()
    assert "stream = normalize_text(joined_raw)" in src
    assert "marker = a.get(\"marker\", \"\")" in src
    assert "missing_markers.append(marker)" in src


# ---------- forbidden tokens 第三百五十九批 ----------

def test_source_no_eval_batch87():
    assert "eval(" not in _src()


def test_source_no_exec_batch87():
    assert "exec(" not in _src()


def test_source_no_compile_batch87():
    assert "compile(" not in _src()


def test_source_no_globals_batch87():
    assert "globals(" not in _src()


def test_source_no_locals_batch87():
    assert "locals(" not in _src()


def test_source_no_os_system_batch87():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch87():
    assert "subprocess" not in _src()


def test_source_no_popen_batch87():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch87():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch87():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch87():
    assert "socket" not in _src()


def test_source_no_requests_batch87():
    assert "requests" not in _src()


def test_source_no_urllib_batch87():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch87():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch87():
    assert "yield" not in _src()


def test_source_no_async_await_batch87():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch87():
    assert "open(" not in _src()
