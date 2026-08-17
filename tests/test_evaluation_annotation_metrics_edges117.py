"""evaluation/annotation_metrics.py 第三百九十六轮 edges 测试（Round 952）。

补强 edges116 未触及的角度（第三百二十八批，probe 实证）。

新角度：
- 全部 marker 命中 → _missing_markers 键不出现（四键
  [P, R, F1, _tolerance_chars]）
- 混合命中/缺失 → _missing_markers 追加在最后（值
  ["ZZ"]）；缺失不计入分母 → P/R/F1 全 1.0
- 最近匹配贪心：preds [2,5]、gt 3（marker "CD" before）
  → 距离对 (1,p0)/(2,p1) → p0 胜出 → P 0.5 R 1.0
- chunk 缺 text 键 → c.get("text") or "" 当空串 →
  空 chunk 仍产出一个预测边界（P 0.5）
- 同 marker before/before 两次：["ABX","XAB"] 流
  "ABX XAB" → 1 预测边界 (3) vs 2 标注 [2,4] →
  P 1.0 / R 0.5 / F1 0.6666…
- 空 marker "" → find 短路为 -1 → 进 _missing_markers、
  gt 空 → recall null no_ground_truth_anchors_in_stream
- forbidden tokens 第四百二十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- _missing_markers 键存在性 ----------

def test_missing_markers_key_absent_batch150():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after"}))
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars"]
    assert "_missing_markers" not in out


def test_missing_markers_appended_last_batch150():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "ZZ", "position": "after"}))
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars",
                         "_missing_markers"]
    assert out["_missing_markers"] == {"value": ["ZZ"],
                                       "reason": None}
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k] == {"value": 1.0, "reason": None}


# ---------- 最近匹配贪心 ----------

def test_nearest_match_greedy_batch150():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "CD", "position": "before"}),
        tolerance_chars=30)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- chunk 缺 text 键 ----------

def test_chunk_missing_text_key_batch150():
    doc = {"chunks": [{"text": "AB"}, {}, {"text": "CD"}]}
    out = chunk_boundary_prf(
        doc, _ann({"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}


# ---------- 同 marker before/before ----------

def test_same_marker_before_before_batch150():
    out = chunk_boundary_prf(
        _doc("ABX", "XAB"),
        _ann({"marker": "X", "position": "before"},
             {"marker": "X", "position": "before"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    f1 = out["chunk_boundary_f1"]["value"]
    assert f1 is not None and abs(f1 - 2 / 3) < 1e-9


# ---------- 空 marker ----------

def test_empty_marker_missing_batch150():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "", "position": "after"}))
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"] == {"value": [""],
                                       "reason": None}


# ---------- figure_caption 固定 null ----------

def test_figure_caption_constants_batch150():
    out = figure_caption_prf({"chunks": []}, {"x": 1})
    assert out == {
        "figure_caption_precision": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
        "figure_caption_recall": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
        "figure_caption_f1": {
            "value": None,
            "reason": PARSER_DOES_NOT_EMIT_RELATIONS},
    }


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch150():
    src = _src()
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src
    assert "if d <= tolerance_chars:" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if missing_markers:" in src


# ---------- forbidden tokens 第四百二十二批 ----------

def test_source_no_eval_batch150():
    assert "eval(" not in _src()


def test_source_no_exec_batch150():
    assert "exec(" not in _src()


def test_source_no_compile_batch150():
    assert "compile(" not in _src()


def test_source_no_globals_batch150():
    assert "globals(" not in _src()


def test_source_no_locals_batch150():
    assert "locals(" not in _src()


def test_source_no_os_system_batch150():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch150():
    assert "subprocess" not in _src()


def test_source_no_popen_batch150():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch150():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch150():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch150():
    assert "socket" not in _src()


def test_source_no_requests_batch150():
    assert "requests" not in _src()


def test_source_no_urllib_batch150():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch150():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch150():
    assert "yield" not in _src()


def test_source_no_async_await_batch150():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch150():
    assert "open(" not in _src()
