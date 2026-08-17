"""evaluation/annotation_metrics.py 第四百二十四轮 edges 测试（Round 980）。

补强 edges120 未触及的角度（第三百五十六批，probe 实证）。

新角度：
- 两条 null 短路路径（document None / no_annotation）都返回
  恰 4 键：3 指标 + _tolerance_chars（且无 _missing_markers）
- 逆序 anchors：search_from 只前进 → 第二个 anchor 的 marker
  在更早位置找不到 → _missing_markers ["AB"]，但已命中的
  P/R 仍 1.0
- 空 text chunk 仍产出边界（find("") 返回 pos）→ 与
  before-anchor 距 0 命中 → P/R/F1 全 1.0
- tolerance 0 且全部距离 > 0 → P=R=0.0 → f1 走
  denom<=0 分支 = 0.0
- 同 marker 双 anchor：第二个从 search_from 起找不到 →
  静默缩分母（num_gt 1 而非 2）→ P/R 仍 1.0
- forbidden tokens 第四百五十批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc():
    return {"chunks": [{"text": "AB"}, {"text": "CD"}]}


# ---------- null 路径 4 键 ----------

def test_null_paths_carry_tolerance_key_batch178():
    out = chunk_boundary_prf({"chunks": [{"text": "AB"}]}, None)
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars"]
    assert out["_tolerance_chars"] == {"value": 30, "reason": None}
    assert "_missing_markers" not in out

    out2 = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert list(out2) == ["chunk_boundary_precision",
                          "chunk_boundary_recall",
                          "chunk_boundary_f1",
                          "_tolerance_chars"]
    assert out2["chunk_boundary_precision"] == {
        "value": None, "reason": "pipeline_failed"}


# ---------- 逆序 anchors ----------

def test_reverse_ordered_anchors_missing_marker_batch178():
    ann = {"chunk_boundary_anchors": [
        {"marker": "CD", "position": "after"},
        {"marker": "AB", "position": "after"}]}
    out = chunk_boundary_prf(_doc(), ann)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}


# ---------- 空 text chunk ----------

def test_empty_text_chunk_still_boundary_batch178():
    doc = {"chunks": [{"text": ""}, {"text": "AB"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "A", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- P=R=0 → f1 denom<=0 ----------

def test_zero_pr_f1_zero_denom_branch_batch178():
    doc = {"chunks": [{"text": "AB"}, {"text": "CD"},
                      {"text": "EF"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "EF", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- 同 marker 双 anchor 缩分母 ----------

def test_duplicate_anchor_marker_shrinks_denominator_batch178():
    ann = {"chunk_boundary_anchors": [
        {"marker": "AB", "position": "after"},
        {"marker": "AB", "position": "after"}]}
    out = chunk_boundary_prf(_doc(), ann)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch178():
    src = _src()
    assert src.count(
        'out["_tolerance_chars"] = {"value": tolerance_chars, '
        '"reason": None}') == 5
    assert "search_from = find_pos + len(marker)" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if denom <= 0:" in src


# ---------- forbidden tokens 第四百五十批 ----------

def test_source_no_eval_batch178():
    assert "eval(" not in _src()


def test_source_no_exec_batch178():
    assert "exec(" not in _src()


def test_source_no_compile_batch178():
    assert "compile(" not in _src()


def test_source_no_globals_batch178():
    assert "globals(" not in _src()


def test_source_no_locals_batch178():
    assert "locals(" not in _src()


def test_source_no_os_system_batch178():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch178():
    assert "subprocess" not in _src()


def test_source_no_popen_batch178():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch178():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch178():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch178():
    assert "socket" not in _src()


def test_source_no_requests_batch178():
    assert "requests" not in _src()


def test_source_no_urllib_batch178():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch178():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch178():
    assert "yield" not in _src()


def test_source_no_async_await_batch178():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch178():
    assert "open(" not in _src()
