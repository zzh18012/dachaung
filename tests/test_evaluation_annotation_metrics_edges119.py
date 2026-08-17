"""evaluation/annotation_metrics.py 第四百一十轮 edges 测试（Round 966）。

补强 edges118 未触及的角度（第三百四十二批，probe 实证）。

新角度：
- marker 大小写敏感："ab" 在流 "AB" 找不到 → 进
  _missing_markers + R null
  no_ground_truth_anchors_in_stream
- 分支顺序怪癖：doc 无 chunks 键 + anchors 也空 →
  先撞 `len(chunks) < 2` 分支 → P/R 双 null
  no_predicted_boundaries（而非
  no_ground_truth_anchors——chunks 检查在前）
- 无 chunks + anchors 非空 → P null
  no_predicted_boundaries + R 0.0
- 负容差 -5：d ≥ 0 永不 ≤ -5 → P 0.0 / R 0.0
- CJK marker 码点语义：chunks ["你好","世界"] 流
  "你好 世界"，marker "你好" after → gt 2 = 预测位 2 →
  全 1.0
- forbidden tokens 第四百三十六批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 大小写敏感 ----------

def test_marker_case_sensitive_batch164():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "AB"}, {"text": "CD"}]},
        _ann({"marker": "ab", "position": "after"}))
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"] == {"value": ["ab"],
                                       "reason": None}


# ---------- 分支顺序怪癖 ----------

def test_no_chunks_beats_no_anchors_batch164():
    out = chunk_boundary_prf({"elements": []}, _ann())
    assert out["chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}


def test_no_chunks_with_anchors_batch164():
    out = chunk_boundary_prf(
        {"elements": []},
        _ann({"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_precision"] == {
        "value": None,
        "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}


# ---------- 负容差 ----------

def test_negative_tolerance_never_matches_batch164():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "AB"}, {"text": "CD"}]},
        _ann({"marker": "AB", "position": "after"}),
        tolerance_chars=-5)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- CJK 码点语义 ----------

def test_cjk_marker_codepoint_batch164():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "你好"}, {"text": "世界"}]},
        _ann({"marker": "你好", "position": "after"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch164():
    src = _src()
    assert 'if not chunks or len(chunks) < 2:' in src
    assert "_ratio(matched / num_pred)" in src
    assert "_ratio(matched / num_gt)" in src
    assert "_null(\"precision_or_recall_not_evaluated\")" in src


# ---------- forbidden tokens 第四百三十六批 ----------

def test_source_no_eval_batch164():
    assert "eval(" not in _src()


def test_source_no_exec_batch164():
    assert "exec(" not in _src()


def test_source_no_compile_batch164():
    assert "compile(" not in _src()


def test_source_no_globals_batch164():
    assert "globals(" not in _src()


def test_source_no_locals_batch164():
    assert "locals(" not in _src()


def test_source_no_os_system_batch164():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch164():
    assert "subprocess" not in _src()


def test_source_no_popen_batch164():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch164():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch164():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch164():
    assert "socket" not in _src()


def test_source_no_requests_batch164():
    assert "requests" not in _src()


def test_source_no_urllib_batch164():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch164():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch164():
    assert "yield" not in _src()


def test_source_no_async_await_batch164():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch164():
    assert "open(" not in _src()
