"""evaluation/annotation_metrics.py 第三百六十一轮 edges 测试（Round 917）。

补强 edges111 未触及的角度（第二百九十三批，probe 实证）。

新角度：
- 空 marker：find 分支 `if marker else -1` → 进 missing
  （_missing_markers [""]），recall null
  no_ground_truth_anchors_in_stream，F1 null
- anchor 缺 position 键 → 默认 "after"；position 非法值
  （"weird"）→ else 分支同样按 after 处理
- before-anchor 推进 search_from 后遮蔽后续 marker：
  ["AB" before, "B" after] → "B" missing → P/R/F1 全 0.0
- tolerance_chars=-5：d <= 负数 永不成立 → P/R/F1 全 0.0，
  _tolerance_chars 原样记录 -5
- annotation 真值但缺 chunk_boundary_anchors 键 →
  no_ground_truth_anchors 三连 null
- 单 chunk + 有 anchors → recall 0.0（ratio），precision/F1
  null no_predicted_boundaries
- 全失配（d>tol）→ P/R/F1 全 0.0（denom<=0 → F1 0.0 而非 null）
- document None → pipeline_failed 三连 + _tolerance_chars 7
- forbidden tokens 第三百八十七批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 空 marker ----------

def test_empty_marker_missing_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": [""], "reason": None}


# ---------- position 缺省与非法值 ----------

def test_position_default_after_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), _ann({"marker": "B"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


def test_position_foreign_value_after_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B", "position": "weird"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- before-anchor 遮蔽 ----------

def test_before_anchor_shadows_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "before"},
             {"marker": "B", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}
    assert out["_missing_markers"] == {"value": ["B"], "reason": None}


# ---------- 负容差 ----------

def test_negative_tolerance_all_zero_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "C"),
        _ann({"marker": "AB", "position": "after"}), -5)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}
    assert out["_tolerance_chars"] == {"value": -5, "reason": None}


# ---------- annotation 缺 anchors 键 ----------

def test_annotation_without_anchors_key_batch115():
    out = chunk_boundary_prf(_doc("AB", "CD"), {"other": 1}, 0)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None,
                          "reason": "no_ground_truth_anchors"}


# ---------- 单 chunk + 有 anchors ----------

def test_single_chunk_with_anchors_batch115():
    out = chunk_boundary_prf(
        _doc("AB"), _ann({"marker": "A", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 全失配 F1 走 denom<=0 ----------

def test_all_miss_f1_zero_not_null_batch115():
    out = chunk_boundary_prf(
        _doc("AB", "C"),
        _ann({"marker": "C", "position": "after"}), 1)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


# ---------- document None ----------

def test_none_document_pipeline_failed_with_tolerance_batch115():
    out = chunk_boundary_prf(
        None, _ann({"marker": "A", "position": "after"}), 7)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None, "reason": "pipeline_failed"}
    assert out["_tolerance_chars"] == {"value": 7, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch115():
    src = _src()
    assert ("find_pos = stream.find(marker, search_from) "
            "if marker else -1") in src
    assert "search_from = find_pos + len(marker)" in src
    assert "if denom <= 0:" in src
    assert ('out["_missing_markers"] = {"value": missing_markers, '
            '"reason": None}') in src


# ---------- forbidden tokens 第三百八十七批 ----------

def test_source_no_eval_batch115():
    assert "eval(" not in _src()


def test_source_no_exec_batch115():
    assert "exec(" not in _src()


def test_source_no_compile_batch115():
    assert "compile(" not in _src()


def test_source_no_globals_batch115():
    assert "globals(" not in _src()


def test_source_no_locals_batch115():
    assert "locals(" not in _src()


def test_source_no_os_system_batch115():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch115():
    assert "subprocess" not in _src()


def test_source_no_popen_batch115():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch115():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch115():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch115():
    assert "socket" not in _src()


def test_source_no_requests_batch115():
    assert "requests" not in _src()


def test_source_no_urllib_batch115():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch115():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch115():
    assert "yield" not in _src()


def test_source_no_async_await_batch115():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch115():
    assert "open(" not in _src()
