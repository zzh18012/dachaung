"""evaluation/annotation_metrics.py 第二百零六轮 edges 测试（Round 749）。

补强 edges85/edges86 未触及的角度（第一百一十四批）。

新角度：
- 规范化不对称：stream 是 normalize 后的（NBSP→空格），marker 原样
  —— chunk 带 NBSP + marker 带 NBSP → 找不到；marker 用普通空格 → 命中
- 大小写敏感：marker "AB" vs stream "ab" → missing（normalize 不改大小写）
- marker 跨三个 chunk："A B C" after → gt 在流末尾，2 pred 1 gt → P=0.5 R=1.0
- marker 比流还长（50 字符）→ missing + recall reason
  no_ground_truth_anchors_in_stream
- 空 marker 与真 marker 混排：recall 1.0 + missing ['']
- 容差接受浮点（2.7 原样记录、参与比较）
- document 无 chunks 键 → no_predicted_boundaries
- 部分丢失：P=0.5 R=1.0 + missing ['ZZ']
- forbidden tokens 第二百一十九批
"""

from __future__ import annotations

import inspect

import pytest

from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors) -> dict:
    return {"chunk_boundary_anchors": list(anchors)}


NBSP = " "


# ---------- 规范化不对称 ----------

def test_nbsp_marker_unnormalized_missing_batch54():
    # stream 里 NBSP 被压成普通空格；marker 原样保留 NBSP → 找不到
    out = chunk_boundary_prf(_doc(f"A{NBSP}B", "C"),
                             _ann({"marker": f"A{NBSP}B"}))
    assert out["chunk_boundary_recall"] == {
        "value": None, "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"]["value"] == [f"A{NBSP}B"]


def test_space_marker_finds_nbsp_chunk_batch54():
    out = chunk_boundary_prf(_doc(f"A{NBSP}B", "C"),
                             _ann({"marker": "A B"}))
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_case_sensitive_marker_batch54():
    out = chunk_boundary_prf(_doc("ab", "cd"), _ann({"marker": "AB"}))
    assert out["_missing_markers"]["value"] == ["AB"]
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"


# ---------- 跨 chunk / 超长 marker ----------

def test_marker_spanning_three_chunks_batch54():
    out = chunk_boundary_prf(_doc("A", "B", "C"),
                             _ann({"marker": "A B C",
                                   "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_marker_longer_than_stream_batch54():
    out = chunk_boundary_prf(_doc("A", "B"),
                             _ann({"marker": "X" * 50}))
    assert out["chunk_boundary_recall"] == {
        "value": None, "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"]["value"] == ["X" * 50]


# ---------- 混排 ----------

def test_empty_and_real_marker_mixed_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "AB"}, {"marker": ""}))
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["_missing_markers"]["value"] == [""]


def test_partial_missing_half_precision_batch54():
    out = chunk_boundary_prf(_doc("AAAA", "B", "C"),
                             _ann({"marker": "ZZ"}, {"marker": "AAA"}))
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["_missing_markers"]["value"] == ["ZZ"]


# ---------- 容差与键容错 ----------

def test_float_tolerance_recorded_verbatim_batch54():
    out = chunk_boundary_prf(_doc("AAAA", "B"), _ann({"marker": "AA"}),
                             tolerance_chars=2.7)
    assert out["_tolerance_chars"] == {"value": 2.7, "reason": None}


def test_document_without_chunks_key_batch54():
    out = chunk_boundary_prf({}, _ann({"marker": "x"}))
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_predicted_boundaries"


# ---------- 源码补强 ----------

def _src() -> str:
    import evaluation.annotation_metrics as am
    return inspect.getsource(am)


def test_source_marker_raw_comment_batch54():
    src = _src()
    assert "marker = a.get(\"marker\", \"\")" in src
    assert "position = a.get(\"position\", \"after\")" in src


# ---------- forbidden tokens 第二百一十九批 ----------

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
