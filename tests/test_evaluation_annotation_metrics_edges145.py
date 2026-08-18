"""evaluation/annotation_metrics.py 第五百七十五轮 edges 测试（Round 1228）。

补强 edges144 未触及的角度（第六百批，probe 实证）。

新角度（流首锚 / 三锚争两界 / 空格 marker）：
- **流首锚贴界两侧**——marker
  "AAA" before → gt 0，界 3：tol
  0 → 全 0.0（d3 > 0）、tol 5 →
  全 1.0（d3 ≤ 5）
- **三锚争两界**——chunks 三块
  两界，三锚全可及 → 一对一封顶
  2 中：P 1.0 / R 2/3 / F1 0.8
- **巨容差不救缺锚**——tol 10**9
  + marker 不在流中 → 照旧
  missing + R None（容差只作用
  于已找到的锚首锁）
- **空格 marker**——chunks
  ("A","B") join 空格本身作
  marker → before 落位 1 恰界 →
  全 1.0（空白串非空即合法 marker
  首锁，与空串 "" 进 missing 相对）
- forbidden tokens 第六百九十六批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*pairs):
    return {"chunk_boundary_anchors": [
        {"marker": m, "position": p} for m, p in pairs]}


# ---------- 流首锚贴界两侧 ----------

def test_start_anchor_tol0_miss_batch426():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("AAA", "before")), 0)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}


def test_start_anchor_tol5_hit_batch426():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("AAA", "before")), 5)
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- 三锚争两界 ----------

def test_three_anchors_two_boundaries_batch426():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB", "CCC"),
        _ann(("AAA", "after"), ("BBB", "after"),
             ("CCC", "before")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.6666666666666666, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 0.8, "reason": None}
    assert r.get("_missing_markers") is None


# ---------- 巨容差不救缺锚 ----------

def test_huge_tol_no_rescue_batch426():
    r = chunk_boundary_prf(
        _doc("AAAA", "BBBB"), _ann(("ZZZZ", "before")),
        10**9)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert r["_missing_markers"] == {
        "value": ["ZZZZ"], "reason": None}


# ---------- 空格 marker ----------

def test_space_marker_hits_batch426():
    r = chunk_boundary_prf(
        _doc("A", "B"), _ann((" ", "before")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}
    assert r.get("_missing_markers") is None


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch426():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "predicted.append(end)" in src
    assert "gt_positions.append(find_pos)" in src
    assert ("gt_positions.append(find_pos + len(marker))"
            in src)
    assert "if find_pos < 0:" in src


# ---------- forbidden tokens 第六百九十六批 ----------

def test_source_no_eval_batch426():
    assert "eval(" not in _src()


def test_source_no_exec_batch426():
    assert "exec(" not in _src()


def test_source_no_compile_batch426():
    assert "compile(" not in _src()


def test_source_no_globals_batch426():
    assert "globals(" not in _src()


def test_source_no_locals_batch426():
    assert "locals(" not in _src()


def test_source_no_os_system_batch426():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch426():
    assert "subprocess" not in _src()


def test_source_no_popen_batch426():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch426():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch426():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch426():
    assert "socket" not in _src()


def test_source_no_requests_batch426():
    assert "requests" not in _src()


def test_source_no_urllib_batch426():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch426():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch426():
    assert "yield" not in _src()


def test_source_no_async_await_batch426():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch426():
    assert "open(" not in _src()
