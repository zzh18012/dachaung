"""evaluation/annotation_metrics.py 第四百四十五轮 edges 测试（Round 1001）。

补强 edges123 未触及的角度（第三百七十七批，probe 实证）。

新角度：
- anchor 缺 "position" 键 → a.get("position", "after") 默认
  after 语义 → 照常命中 P/R 1.0
- document {}（无 chunks 键）+ 有 anchors → precision null
  "no_predicted_boundaries"、recall 却是 0.0 值（非 null）、
  f1 null —— 三键三种取值分歧
- 双同 marker 顺序定位（search_from 单向推进）→ 两个 gt
  位置各命中 → P/R/F1 全 1.0 且无 _missing_markers 键
- marker "ZZZZ" 不在流中 → 只进 _missing_markers，不进
  recall 分母 → P/R 仍 1.0（缺失标注不扣 recall）
- forbidden tokens 第四百七十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _run(chunks, anchors, tolerance=30, doc_override=None):
    doc = doc_override if doc_override is not None else \
        {"chunks": [{"text": t} for t in chunks]}
    ann = {"chunk_boundary_anchors": anchors}
    return chunk_boundary_prf(doc, ann, tolerance_chars=tolerance)


# ---------- 缺 position 键 ----------

def test_anchor_missing_position_defaults_after_batch199():
    out = _run(["AB", "CD"], [{"marker": "AB"}])
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 空 document 三键分歧 ----------

def test_empty_doc_recall_value_not_null_batch199():
    out = chunk_boundary_prf(
        {}, {"chunk_boundary_anchors": [
            {"marker": "X", "position": "after"}]},
        tolerance_chars=30)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 双同 marker 顺序定位 ----------

def test_duplicate_marker_sequential_full_hit_batch199():
    out = _run(["AB", "CD", "AB"], [
        {"marker": "AB", "position": "after"},
        {"marker": "AB", "position": "after"}])
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    assert "_missing_markers" not in out


# ---------- 缺失 marker 不扣 recall ----------

def test_missing_marker_not_in_recall_denominator_batch199():
    out = _run(["AAAA", "BBBB", "CCCC"], [
        {"marker": "AAAA", "position": "after"},
        {"marker": "BBBB", "position": "after"},
        {"marker": "ZZZZ", "position": "after"}], tolerance=2)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["_missing_markers"] == {
        "value": ["ZZZZ"], "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch199():
    src = _src()
    assert 'position = a.get("position", "after")' in src
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "stream = normalize_text(joined_raw)" in src
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src


# ---------- forbidden tokens 第四百七十一批 ----------

def test_source_no_eval_batch199():
    assert "eval(" not in _src()


def test_source_no_exec_batch199():
    assert "exec(" not in _src()


def test_source_no_compile_batch199():
    assert "compile(" not in _src()


def test_source_no_globals_batch199():
    assert "globals(" not in _src()


def test_source_no_locals_batch199():
    assert "locals(" not in _src()


def test_source_no_os_system_batch199():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch199():
    assert "subprocess" not in _src()


def test_source_no_popen_batch199():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch199():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch199():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch199():
    assert "socket" not in _src()


def test_source_no_requests_batch199():
    assert "requests" not in _src()


def test_source_no_urllib_batch199():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch199():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch199():
    assert "yield" not in _src()


def test_source_no_async_await_batch199():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch199():
    assert "open(" not in _src()
