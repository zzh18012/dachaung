"""evaluation/annotation_metrics.py 第二百二十一轮 edges 测试（Round 777）。

补强 edges87-90 未触及的角度（第一百四十一批）。

新角度：
- chunks 键显式 None → or [] → no_predicted_boundaries（与缺键同路径）
- chunks 传 int 5 → truthy 但 len(int) TypeError（未守卫）
- 三重复 chunk 双 anchor：search_from 顺序推进 → 两个 gt 分别对位
  两个 pred → P=R=1.0（R763 三 anchor 补角）
- 前导空 chunk：空串 find 命中自身位置 0 → 虚假边界 0；
  "AB" before-marker gt=0 → d=0 巧合全匹配；"A" after → d=1 同样
  tol30 命中（空 chunk 边界落点与流首重合，现状记录）
- 非空 annotation 无 anchors 键（{"x":1} truthy）→
  no_ground_truth_anchors 三 null（与空 dict falsy → no_annotation
  分支对照）
- 全部 marker 缺失：P=0.0 参与（pred 在而 gt 不在）+
  R null no_ground_truth_anchors_in_stream + missing ['Y','Z']
- 跨分隔符 marker "B C"：stream 级 find 无视 chunk 结构可定位，
  after 位置 gt=5 对 pred=3 → d=2：tol2 命中 1.0 / tol1 落空 0.0
- forbidden tokens 第二百四十七批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- chunks 键形态 ----------

def test_chunks_none_no_predicted_batch54():
    out = chunk_boundary_prf({"chunks": None}, {"x": 1})
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}


def test_chunks_int_typeerror_batch54():
    with pytest.raises(TypeError):
        chunk_boundary_prf({"chunks": 5}, {"x": 1})


# ---------- 三重复 chunk 双 anchor ----------

def test_triple_chunks_two_anchors_perfect_batch54():
    out = chunk_boundary_prf(_doc("A", "A", "A"),
                             _ann({"marker": "A"}, {"marker": "A"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 前导空 chunk ----------

def test_leading_empty_chunk_coincident_boundary_batch54():
    out = chunk_boundary_prf(
        _doc(" ", "AB"), _ann({"marker": "AB", "position": "before"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_leading_empty_chunk_near_marker_batch54():
    out = chunk_boundary_prf(
        _doc(" ", "AB"), _ann({"marker": "A", "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- annotation 无 anchors 键 ----------

def test_annotation_without_anchors_key_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"), {"x": 1})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None,
                          "reason": "no_ground_truth_anchors"}


def test_empty_annotation_dict_different_reason_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"), {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


# ---------- 全部 marker 缺失 ----------

def test_all_markers_missing_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "Y"}, {"marker": "Z"}))
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"]["value"] == ["Y", "Z"]


# ---------- 跨分隔符 marker ----------

def test_marker_spanning_separator_batch54():
    for tol, expected in ((2, 1.0), (1, 0.0)):
        out = chunk_boundary_prf(
            _doc("A B", "C D"), _ann({"marker": "B C"}),
            tolerance_chars=tol)
        assert out["chunk_boundary_precision"]["value"] == expected
        assert out["chunk_boundary_recall"]["value"] == expected


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_guard_lines_batch54():
    src = _src()
    assert 'document.get("chunks") or []' in src
    assert "if not chunks or len(chunks) < 2:" in src
    assert "pos += len(txt) + 1" in src


# ---------- forbidden tokens 第二百四十七批 ----------

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
