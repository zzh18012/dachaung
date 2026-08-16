"""evaluation/annotation_metrics.py 第二百零五轮 edges 测试（Round 742）。

补强 edges84/edges85 未触及的角度（第一百零七批）。

新角度：
- 交叉配对：贪心按距离排序天然处理 pred/gt 交叉（P=R=f1=1.0）
- 真 1 pred 2 anchors：P=1.0 R=0.5 f1=2/3（一个 pred 只能命中一个
  anchor，与 edges83 的 2 pred 1 anchor 互补）
- 顺序推进副作用再现：marker "AAAA" 先占位后 "AAAAA" 只能在 4 起找 →
  missing（1p2a 的第一版探针即踩中此路径）
- 首个空 chunk 的回退连锁：pred 只剩 0，但容差吸收 → P=R=1.0
  （错误边界仍在容差内，现状记录）
- annotation {"chunk_boundary_anchors": None} → or [] → no_ground_truth
- document {"chunks": None} → <2 分支：precision null、recall 0.0
- annotation 额外键被忽略
- 未守卫路径：marker 非 str → TypeError（stream.find）；
  chunk text 非 str（≥2 chunk 才触发 normalize）→ TypeError
- forbidden tokens 第二百一十二批
"""

from __future__ import annotations

import inspect

import pytest

from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors) -> dict:
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 交叉配对 ----------

def test_crossing_pairs_matched_by_distance_batch54():
    out = chunk_boundary_prf(
        _doc("AAAAAAAAAA", "B", "AAAAAAAAAB"),
        _ann({"marker": "B", "position": "after"},
             {"marker": "AAAAAAAAAB", "position": "before"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


# ---------- 1 pred 2 anchors ----------

def test_one_pred_two_anchors_half_recall_batch54():
    out = chunk_boundary_prf(
        _doc("AAAAA", "B"),
        _ann({"marker": "AAA"}, {"marker": "A B"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)
    assert "_missing_markers" not in out


def test_sequential_advance_makes_longer_marker_missing_batch54():
    # "AAAA" 命中 @0 并把起点推到 4；"AAAAA" 只在 0 处 → missing
    out = chunk_boundary_prf(
        _doc("AAAAA", "B"),
        _ann({"marker": "AAAA"}, {"marker": "AAAAA"}))
    assert out["_missing_markers"]["value"] == ["AAAAA"]
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 首空 chunk 回退连锁 ----------

def test_leading_empty_chunk_fallback_cascade_batch54():
    # 空 chunk 产出 pred@0 并把 pos 推到 1；后续 "AB"/"CD" 都找不到 →
    # 回退分支吃掉全部真实边界，只剩 pred [0]；容差 30 吸收差值
    out = chunk_boundary_prf(
        _doc("", "AB", "CD"),
        _ann({"marker": "CD", "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- None 容错 ----------

def test_anchors_none_treated_as_empty_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             {"chunk_boundary_anchors": None})
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_ground_truth_anchors"


def test_chunks_none_quadrant_batch54():
    out = chunk_boundary_prf({"chunks": None},
                             _ann({"marker": "x"}))
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_predicted_boundaries"
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"]["reason"] == \
        "no_predicted_boundaries"


def test_annotation_extra_keys_ignored_batch54():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        {"chunk_boundary_anchors": [{"marker": "AB",
                                     "position": "after"}],
         "bogus": 1})
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- 未守卫路径现状记录 ----------

def test_non_string_marker_raises_typeerror_batch54():
    with pytest.raises(TypeError):
        chunk_boundary_prf(_doc("AB", "CD"), _ann({"marker": 5}))


def test_non_string_chunk_text_raises_typeerror_batch54():
    # 单 chunk 走 <2 提前返回；必须两个 chunk 才触发 normalize
    with pytest.raises(TypeError):
        chunk_boundary_prf(_doc("AB", 5), _ann({"marker": "AB"}))
    with pytest.raises(TypeError):
        chunk_boundary_prf(_doc(5, "AB"), _ann({"marker": "AB"}))


# ---------- 源码补强 ----------

def _src() -> str:
    import evaluation.annotation_metrics as am
    return inspect.getsource(am)


def test_source_greedy_comment_batch54():
    src = _src()
    assert "贪心：按 (|pred - gt|) 升序" in src
    assert "used_pred" in src and "used_gt" in src


# ---------- forbidden tokens 第二百一十二批 ----------

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
