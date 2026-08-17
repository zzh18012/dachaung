"""evaluation/annotation_metrics.py 第三百八十二轮 edges 测试（Round 938）。

补强 edges114 未触及的角度（第三百一十四批，probe 实证）。

新角度：
- 同 marker before+after 双 anchor：before 消费唯一出现并
  推进 search_from，after 再找 → missing ["AB"]，但
  before 位 gt 0 与 pred 2 距 2 命中 → R 1.0
- 跨 chunk 接缝 marker "B C"（流 "AB CD"）能找到：
  before → gt 1，pred 2，d=1 → 全 1.0
- marker 双空格 "A  B" 在单空格流中 missing（与 \t 同理）
- document 无 elements 键照常工作（本模块只读 chunks）
- annotation 多余键被忽略（只取 chunk_boundary_anchors）
- 空尾 chunk 不产生边界（最后 chunk 本就排除）：全 1.0
- 首 chunk text None ≡ 空串（get or "" 兜底）→ 全 1.0
- dup marker + search_from 耗尽：chunks AB/CDEF/G 双
  "CDEF" anchor → 第二个 missing，preds [2,7] 只剩
  gt [3] → P 0.5 / R 1.0
- forbidden tokens 第四百零八批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 同 marker before+after ----------

def test_same_marker_before_after_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "before"},
             {"marker": "AB", "position": "after"}))
    # before 消费唯一出现；after 从 search_from=2 再找失败
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}


# ---------- 跨接缝 marker ----------

def test_marker_spanning_join_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B C", "position": "before"}))
    # 流 "AB CD"：marker 起点 1，pred 2，d=1 命中
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 双空格 marker ----------

def test_double_space_marker_missing_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "A  B"}, {"marker": "AB"}))
    assert out["_missing_markers"] == {"value": ["A  B"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- document 无 elements 键 ----------

def test_no_elements_key_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- annotation 多余键 ----------

def test_annotation_extra_keys_ignored_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        {"extra": 1, "note": "x",
         "chunk_boundary_anchors": [
             {"marker": "AB", "position": "after"}]})
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 空尾 chunk ----------

def test_empty_last_chunk_no_boundary_batch136():
    out = chunk_boundary_prf(
        _doc("AB", ""),
        _ann({"marker": "AB", "position": "after"}))
    # 最后一个 chunk 本就不产生边界 → pred [2] 仍是唯一
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- None text 首 chunk ----------

def test_none_text_first_chunk_batch136():
    out = chunk_boundary_prf(
        {"chunks": [{"text": None}, {"text": "AB"}]},
        _ann({"marker": "AB", "position": "after"}))
    # c.get("text") or "" → None 当空串，同空首 chunk
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- dup marker 耗尽 search_from ----------

def test_dup_marker_search_exhaustion_batch136():
    out = chunk_boundary_prf(
        _doc("AB", "CDEF", "G"),
        _ann({"marker": "CDEF", "position": "before"},
             {"marker": "CDEF", "position": "after"}),
        tolerance_chars=10**9)
    # 第一个 CDEF 消费后 search_from=7，第二个找不到；
    # preds [2,7] 争唯一 gt [3] → 贪心取 pred 0
    assert out["_missing_markers"] == {"value": ["CDEF"],
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch136():
    src = _src()
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in src
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert 'if position == "before":' in src
    assert "pairs.sort(key=lambda x: x[0])" in src


# ---------- forbidden tokens 第四百零八批 ----------

def test_source_no_eval_batch136():
    assert "eval(" not in _src()


def test_source_no_exec_batch136():
    assert "exec(" not in _src()


def test_source_no_compile_batch136():
    assert "compile(" not in _src()


def test_source_no_globals_batch136():
    assert "globals(" not in _src()


def test_source_no_locals_batch136():
    assert "locals(" not in _src()


def test_source_no_os_system_batch136():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch136():
    assert "subprocess" not in _src()


def test_source_no_popen_batch136():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch136():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch136():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch136():
    assert "socket" not in _src()


def test_source_no_requests_batch136():
    assert "requests" not in _src()


def test_source_no_urllib_batch136():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch136():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch136():
    assert "yield" not in _src()


def test_source_no_async_await_batch136():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch136():
    assert "open(" not in _src()
