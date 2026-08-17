"""evaluation/annotation_metrics.py 第四百五十九轮 edges 测试（Round 1015）。

补强 edges125 未触及的角度（第三百九十一批，probe 实证）。

新角度（marker 搜索机制）：
- anchor 乱序：靠后 marker 先列 → search_from 推进吞掉
  靠前 marker（"apple" 明明在流里却进 missing_markers），
  且 P/R/F1 仍全 1.0（分母只剩找得到的）
- 空 marker ""：直接进 missing_markers（if marker else -1），
  不影响其余 anchor
- 未规范化 marker（双空格 "hello  world"）：流已 normalize
  成单空格，marker 原样查找 → 找不到 → recall null
  no_ground_truth_anchors_in_stream、precision 0.0
- tolerance_chars=0：d=0 精确命中仍算（<= 含边界），
  P 0.5 / R 1.0 / F1 2/3
- forbidden tokens 第四百八十五批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


# ---------- anchor 乱序 ----------

def test_out_of_order_anchor_swallowed_batch213():
    doc = {"chunks": [{"text": "apple zebra"}, {"text": "tail"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zebra"},
                                       {"marker": "apple"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {"value": ["apple"],
                                     "reason": None}
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


# ---------- 空 marker ----------

def test_empty_marker_missing_batch213():
    doc = {"chunks": [{"text": "apple zebra"}, {"text": "tail"}]}
    ann = {"chunk_boundary_anchors": [{"marker": ""},
                                       {"marker": "zebra"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {"value": [""],
                                     "reason": None}
    assert r["chunk_boundary_recall"]["value"] == 1.0


# ---------- 未规范化 marker ----------

def test_unnormalized_marker_null_recall_batch213():
    doc = {"chunks": [{"text": "hello  world"}, {"text": "x"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "hello  world"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {
        "value": ["hello  world"], "reason": None}
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert r["chunk_boundary_f1"]["value"] is None


# ---------- tolerance 0 精确命中 ----------

def test_tolerance_zero_exact_match_batch213():
    doc = {"chunks": [{"text": "aaaa"}, {"text": "bbbb"},
                      {"text": "cccc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": " bbbb", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 0.5
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert abs(r["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-9


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch213():
    src = _src()
    assert ("find_pos = stream.find(marker, search_from)"
            " if marker else -1") in src
    assert "search_from = find_pos + len(marker)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第四百八十五批 ----------

def test_source_no_eval_batch213():
    assert "eval(" not in _src()


def test_source_no_exec_batch213():
    assert "exec(" not in _src()


def test_source_no_compile_batch213():
    assert "compile(" not in _src()


def test_source_no_globals_batch213():
    assert "globals(" not in _src()


def test_source_no_locals_batch213():
    assert "locals(" not in _src()


def test_source_no_os_system_batch213():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch213():
    assert "subprocess" not in _src()


def test_source_no_popen_batch213():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch213():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch213():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch213():
    assert "socket" not in _src()


def test_source_no_requests_batch213():
    assert "requests" not in _src()


def test_source_no_urllib_batch213():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch213():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch213():
    assert "yield" not in _src()


def test_source_no_async_await_batch213():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch213():
    assert "open(" not in _src()
