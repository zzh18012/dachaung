"""evaluation/annotation_metrics.py 第五百七十三轮 edges 测试（Round 1213）。

补强 edges142 未触及的角度（第五百八十五批，probe 实证）。

新角度（单块内重叠锚 / 跨界 marker / marker 不归一）：
- **单块内重叠锚**——chunk "AAAA" +
  marker "AA" ×2 → gt [2, 4]（find 从
  pos 前进可重叠落位）→ 1 预测界 @4：
  P 1.0 / R 0.5 / F1 2/3（一对一贪心
  取 d0 弃 d2 首锁）
- **跨界 marker**——marker "A B" 含
  join 空格横跨两块边界 → after（末
  5）与 before（首 2）均距界 ≤ 30 →
  全 1.0；tol=0 时 after d5 / before
  d2 仍 > 0 → 全 0.0（贴界容差联动）
- **marker 不归一**——marker "A  B"
  （双空格）在归一后单空格流中找不到
  → _missing_markers ["A  B"]、
  P 0.0 / R None（marker 原样 find，
  只归一 chunk 文本首锁）
- **全空白块**——chunks ["   ",
  "\\n\\n"] → 归一流空但 2 块 → 1
  预测界照样存在 → P 0.0（非
  no_predicted_boundaries）/ R None
- forbidden tokens 第六百八十四批（open 0）
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


# ---------- 单块内重叠锚 ----------

def test_overlapping_anchors_one_chunk_batch411():
    r = chunk_boundary_prf(
        _doc("AAAA", "CCCC"),
        _ann(("AA", "after"), ("AA", "after")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}
    assert r["_tolerance_chars"] == {"value": 30, "reason": None}


def test_overlapping_anchors_no_missing_batch411():
    r = chunk_boundary_prf(
        _doc("AAAA", "CCCC"),
        _ann(("AA", "after"), ("AA", "after")))
    assert r.get("_missing_markers") is None


# ---------- 跨界 marker ----------

def test_spanning_marker_after_batch411():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("A B", "after")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_spanning_marker_before_batch411():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("A B", "before")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_spanning_marker_tol0_batch411():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("A B", "after")), 0)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 0.0, "reason": None}
    assert r["_tolerance_chars"] == {"value": 0, "reason": None}


# ---------- marker 不归一 ----------

def test_marker_double_space_missing_batch411():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("A  B", "after")))
    assert r["_missing_markers"] == {
        "value": ["A  B"], "reason": None}
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert r["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- 全空白块 ----------

def test_whitespace_only_chunks_batch411():
    r = chunk_boundary_prf(
        _doc("   ", "\n\n"), _ann(("x", "after")))
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


def test_whitespace_single_chunk_none_batch411():
    r = chunk_boundary_prf(
        _doc("   "), _ann(("x", "after")))
    assert r["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert r["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch411():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "predicted.append(end)" in src
    assert "gt_positions.append(find_pos)" in src
    assert ("gt_positions.append(find_pos + len(marker))"
            in src)
    assert "if find_pos < 0:" in src


# ---------- forbidden tokens 第六百八十四批 ----------

def test_source_no_eval_batch411():
    assert "eval(" not in _src()


def test_source_no_exec_batch411():
    assert "exec(" not in _src()


def test_source_no_compile_batch411():
    assert "compile(" not in _src()


def test_source_no_globals_batch411():
    assert "globals(" not in _src()


def test_source_no_locals_batch411():
    assert "locals(" not in _src()


def test_source_no_os_system_batch411():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch411():
    assert "subprocess" not in _src()


def test_source_no_popen_batch411():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch411():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch411():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch411():
    assert "socket" not in _src()


def test_source_no_requests_batch411():
    assert "requests" not in _src()


def test_source_no_urllib_batch411():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch411():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch411():
    assert "yield" not in _src()


def test_source_no_async_await_batch411():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch411():
    assert "open(" not in _src()
