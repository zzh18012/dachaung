"""evaluation/annotation_metrics.py 第五百七十四轮 edges 测试（Round 1221）。

补强 edges143 未触及的角度（第五百九十三批，probe 实证）。

新角度（非法 position 默认 after / 大小写敏感 / 同词双位锚 / 容让未知键）：
- **非法 position 默认 after**——
  position "middle" 在 tol 17 区分
  板上与 after 同值 1.0、与 before
  异值 0.0（仅 "before" 特判，其余
  全走 after 分支首锁）
- **区分板**——chunks [A×20,
  B×20] 边界 @20，marker "AAAA"
  before → 0（d20 > 17）/ after → 4
  （d16 ≤ 17）
- **大小写敏感**——marker "aaa"
  对 "AAA BBB" → _missing_markers
  ["aaa"]（find 原样不折叠大小写）
- **同词双位锚**——"AA" before +
  "AA" after 同现一次 → 两锚一界：
  P 1.0 / R 0.5 / F1 2/3
- **容让未知键**——anchor 带
  "foo"、顶层带 "bar" → 照算全 1.0
- forbidden tokens 第六百九十批（open 0）
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


# ---------- 非法 position 默认 after ----------

def test_invalid_position_defaults_after_batch419():
    r = chunk_boundary_prf(
        _doc("A" * 20, "B" * 20),
        _ann(("AAAA", "middle")), 17)
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


def test_before_misses_on_split_board_batch419():
    r = chunk_boundary_prf(
        _doc("A" * 20, "B" * 20),
        _ann(("AAAA", "before")), 17)
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


def test_after_hits_on_split_board_batch419():
    r = chunk_boundary_prf(
        _doc("A" * 20, "B" * 20),
        _ann(("AAAA", "after")), 17)
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["_tolerance_chars"] == {"value": 17, "reason": None}


# ---------- 大小写敏感 ----------

def test_case_sensitive_missing_batch419():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"), _ann(("aaa", "after")))
    assert r["_missing_markers"] == {
        "value": ["aaa"], "reason": None}
    assert r["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 同词双位锚 ----------

def test_same_marker_before_after_batch419():
    r = chunk_boundary_prf(
        _doc("AAAA", "BBBB"),
        _ann(("AA", "before"), ("AA", "after")))
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 0.5, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 容让未知键 ----------

def test_unknown_keys_tolerated_batch419():
    r = chunk_boundary_prf(
        _doc("AAA", "BBB"),
        {"chunk_boundary_anchors": [
            {"marker": "A B", "position": "after", "foo": 1}],
         "bar": 2})
    assert r["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["chunk_boundary_f1"] == {
        "value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch419():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "predicted.append(end)" in src
    assert "gt_positions.append(find_pos)" in src
    assert ("gt_positions.append(find_pos + len(marker))"
            in src)
    assert "if find_pos < 0:" in src


# ---------- forbidden tokens 第六百九十批 ----------

def test_source_no_eval_batch419():
    assert "eval(" not in _src()


def test_source_no_exec_batch419():
    assert "exec(" not in _src()


def test_source_no_compile_batch419():
    assert "compile(" not in _src()


def test_source_no_globals_batch419():
    assert "globals(" not in _src()


def test_source_no_locals_batch419():
    assert "locals(" not in _src()


def test_source_no_os_system_batch419():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch419():
    assert "subprocess" not in _src()


def test_source_no_popen_batch419():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch419():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch419():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch419():
    assert "socket" not in _src()


def test_source_no_requests_batch419():
    assert "requests" not in _src()


def test_source_no_urllib_batch419():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch419():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch419():
    assert "yield" not in _src()


def test_source_no_async_await_batch419():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch419():
    assert "open(" not in _src()
