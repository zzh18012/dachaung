"""evaluation/annotation_metrics.py 第二百四十二轮 edges 测试（Round 798）。

补强 edges93 未触及的角度（第一百六十二批）。

新角度：
- position 大小写敏感："BEFORE"/"" 都落 else（after 语义）——
  tol=1 下 before d=1 命中而 after d=2 不命中，可区分两种语义
- marker 含正则特殊字符 "A[" → find 字面匹配（无 regex）
- chunk 文本内 tab 规范化为单空格后 marker "A B" 跨词命中
  （tol=0 精确重合）
- Unicode marker "中文"：码点计数位置，pred 恰重合 → tol=0 全 1
- anchors 传 tuple 而非 list → 迭代等价照常
- 无 chunks 但有 anchors → precision/f1 no_predicted_boundaries
  而 recall 0.0 非 null（三分支不对称，现状记录）
- forbidden tokens 第二百六十八批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- position 大小写 ----------

def test_position_lowercase_before_hits_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "B", "position": "before"}), 1)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


@pytest.mark.parametrize("pos", ["BEFORE", ""])
def test_position_non_lowercase_falls_to_after_batch54(pos):
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "B", "position": pos}), 1)
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


# ---------- 正则特殊字符 ----------

def test_marker_regex_special_literal_batch54():
    out = chunk_boundary_prf(
        _doc("A[", "B"), _ann({"marker": "A["}), 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- tab 规范化 ----------

def test_tab_normalized_to_space_batch54():
    out = chunk_boundary_prf(
        _doc("A\tB", "C"), _ann({"marker": "A B"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- Unicode marker ----------

def test_unicode_marker_codepoint_positions_batch54():
    out = chunk_boundary_prf(
        _doc("中文", "B"), _ann({"marker": "中文"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- tuple anchors ----------

def test_tuple_anchors_accepted_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        {"chunk_boundary_anchors": ({"marker": "B",
                                     "position": "after"},)}, 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- 无 chunks 有 anchors ----------

def test_no_chunks_with_anchors_recall_zero_batch54():
    out = chunk_boundary_prf(
        {"elements": []},
        _ann({"marker": "B", "position": "after"}), 2)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_position_branch_batch54():
    src = _src()
    assert 'if position == "before":' in src
    assert 'position = a.get("position", "after")' in src
    assert "if not chunks or len(chunks) < 2:" in src


# ---------- forbidden tokens 第二百六十八批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
