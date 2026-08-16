"""evaluation/annotation_metrics.py 第二百零八轮 edges 测试（Round 763）。

补强 edges85-88 未触及的角度（第一百二十七批）。

新角度：
- marker == 整条流（"AB CD" after → gt 在流末尾）：d=3 边界 ——
  tol 3 命中 1.0 / tol 2 落空 0.0（容差含等号）
- before 与 after 指向同一 marker：无论顺序，第二个 anchor 因
  search_from 推进而找不到 → recall 1.0 + missing ['AB']（一对一对
  同一 marker 的两种定位互斥，现状记录）
- 三重复 marker X,X,X：顺序推进各就各位 → P=1.0 R=2/3
- 容差含等号：marker "AA"（gt=2）对 pred=4，d=2 → tol 2 命中、
  tol 1 落空
- 中间空 chunk ["AB","","CD"]：空串在流中 find 命中自身位置 →
  多出一个预测边界 → P=0.5 R=1.0（与 edges86 前导空 chunk 互补）
- 空白 marker " " after：定位到拼接分隔空格末尾 == pred → P=R=1.0
  （marker 可以就是分隔符）
- chunk_boundary_anchors 传字符串 / dict → 迭代出非 dict 元素 →
  AttributeError（未守卫，与空 list 的 falsy 分支对照）
- forbidden tokens 第二百三十三批
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


# ---------- marker == 整条流 ----------

def test_marker_equals_whole_stream_batch54():
    for tol, expected in ((3, 1.0), (2, 0.0)):
        out = chunk_boundary_prf(_doc("AB", "CD"),
                                 _ann({"marker": "AB CD"}),
                                 tolerance_chars=tol)
        assert out["chunk_boundary_precision"]["value"] == expected
        assert out["chunk_boundary_recall"]["value"] == expected


# ---------- 同一 marker 双定位互斥 ----------

@pytest.mark.parametrize("order", [
    ({"marker": "AB", "position": "after"},
     {"marker": "AB", "position": "before"}),
    ({"marker": "AB", "position": "before"},
     {"marker": "AB", "position": "after"}),
])
def test_same_marker_two_positions_second_missing_batch54(order):
    out = chunk_boundary_prf(_doc("AB", "C"), _ann(*order))
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["_missing_markers"]["value"] == ["AB"]


# ---------- 三重复 marker ----------

def test_triple_marker_sequential_positions_batch54():
    out = chunk_boundary_prf(_doc("X", "X", "X"),
                             _ann({"marker": "X"}, {"marker": "X"},
                                  {"marker": "X"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == pytest.approx(2 / 3)


# ---------- 容差含等号 ----------

def test_tolerance_inclusive_boundary_batch54():
    for tol, expected in ((2, 1.0), (1, 0.0)):
        out = chunk_boundary_prf(_doc("AAAA", "B"),
                                 _ann({"marker": "AA"}),
                                 tolerance_chars=tol)
        assert out["chunk_boundary_precision"]["value"] == expected


# ---------- 中间空 chunk ----------

def test_middle_empty_chunk_extra_boundary_batch54():
    out = chunk_boundary_prf(_doc("AB", "", "CD"), _ann({"marker": "AB"}))
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 空白 marker ----------

def test_whitespace_marker_hits_separator_batch54():
    out = chunk_boundary_prf(_doc("A", "B"), _ann({"marker": " "}))
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}


# ---------- anchors 非列表 ----------

@pytest.mark.parametrize("bad", ["abc", {"a": 1}])
def test_anchors_non_list_crashes_batch54(bad):
    with pytest.raises(AttributeError):
        chunk_boundary_prf(_doc("A", "B"),
                           {"chunk_boundary_anchors": bad})


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(am_mod)


def test_source_advance_and_join_batch54():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "if d <= tolerance_chars:" in src
    assert 'annotation.get("chunk_boundary_anchors") or []' in src


# ---------- forbidden tokens 第二百三十三批 ----------

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
