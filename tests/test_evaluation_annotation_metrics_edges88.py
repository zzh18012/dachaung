"""evaluation/annotation_metrics.py 第二百零七轮 edges 测试（Round 756）。

补强 edges85-87 未触及的角度（第一百二十批）。

新角度：
- before 定位：3 chunk 流 "A B C"，marker "B" before → gt=2 与两个预测
  （1、3）各距 1：tol 0 → 全落空 P=R=f1=0.0（含 denom<=0 的 f1 分支）；
  tol 1 → 贪心取先枚举的 p0 → P=0.5 R=1.0 f1=2/3
- before 流首：marker "AB" before → gt=0、pred=2，距离 2：
  tol 1 落空（0.0/0.0）、tol 2 命中（1.0/1.0）—— 距离语义量化
- anchors 值 None 或 annotation 只有无关键 → no_ground_truth_anchors
- 负容差（-5）：d<=-5 永不成立 → P=R=f1=0.0（容差不设下限）
- 空 chunk 列表 / 单 chunk 且有 anchor → P/F1 no_predicted_boundaries
  而 recall 走 _ratio(0.0)（三键不同分支）
- 成功路径 _missing_markers 键完全缺席（仅 missing 非空才设置）
- 超大容差 1e9 仍受一对一约束：3 chunk 2 预测 1 anchor → P=0.5 R=1.0
- CJK marker 精确命中（unicode find 无碍）
- AST chunk_boundary_prf：If15/For7/Try0/Call48/Return5/Compare14
- forbidden tokens 第二百二十六批
"""

from __future__ import annotations

import ast
import collections
import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- before 定位 ----------

def test_before_position_tol_zero_all_miss_batch54():
    out = chunk_boundary_prf(_doc("A", "B", "C"),
                             _ann({"marker": "B", "position": "before"}),
                             tolerance_chars=0)
    assert out["chunk_boundary_precision"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    # P=R=0.0 → denom<=0 分支显式 _ratio(0.0)
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


def test_before_position_tol_one_greedy_first_batch54():
    out = chunk_boundary_prf(_doc("A", "B", "C"),
                             _ann({"marker": "B", "position": "before"}),
                             tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


def test_before_stream_start_distance_two_batch54():
    a = {"marker": "AB", "position": "before"}
    near = chunk_boundary_prf(_doc("AB", "C"), _ann(a), tolerance_chars=1)
    assert near["chunk_boundary_precision"]["value"] == 0.0
    assert near["chunk_boundary_recall"]["value"] == 0.0
    hit = chunk_boundary_prf(_doc("AB", "C"), _ann(a), tolerance_chars=2)
    assert hit["chunk_boundary_precision"]["value"] == 1.0
    assert hit["chunk_boundary_recall"]["value"] == 1.0


# ---------- anchors 形态 ----------

def test_anchors_value_none_no_ground_truth_batch54():
    out = chunk_boundary_prf(_doc("A", "B"),
                             {"chunk_boundary_anchors": None})
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors"


def test_annotation_extra_keys_only_batch54():
    out = chunk_boundary_prf(_doc("A", "B"), {"foo": 1})
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_ground_truth_anchors"


# ---------- 负容差 ----------

def test_negative_tolerance_never_matches_batch54():
    out = chunk_boundary_prf(_doc("AB", "C"), _ann({"marker": "AB"}),
                             tolerance_chars=-5)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


# ---------- 少于 2 chunk 且有 anchor ----------

def test_empty_chunks_with_anchor_recall_zero_batch54():
    out = chunk_boundary_prf(_doc(), _ann({"marker": "X"}))
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert "_missing_markers" not in out


def test_single_chunk_with_anchor_recall_zero_batch54():
    out = chunk_boundary_prf(_doc("AB"), _ann({"marker": "AB"}))
    assert out["chunk_boundary_precision"]["reason"] == \
        "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- _missing_markers 缺席 ----------

def test_success_has_no_missing_markers_key_batch54():
    out = chunk_boundary_prf(_doc("AB", "C"), _ann({"marker": "AB"}))
    assert "_missing_markers" not in out
    assert out["_tolerance_chars"] == {"value": 30, "reason": None}


# ---------- 一对一约束 ----------

def test_huge_tolerance_still_one_to_one_batch54():
    out = chunk_boundary_prf(_doc("A", "B", "C"), _ann({"marker": "A"}),
                             tolerance_chars=10 ** 9)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- CJK ----------

def test_cjk_marker_exact_hit_batch54():
    out = chunk_boundary_prf(_doc("数据", "分析"), _ann({"marker": "数据"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}


# ---------- AST ----------

def test_ast_chunk_boundary_prf_structure_batch54():
    tree = ast.parse(inspect.getsource(am_mod))
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef)
              and n.name == "chunk_boundary_prf")
    c = collections.Counter(type(n).__name__ for n in ast.walk(fn))
    assert (c["If"], c["For"], c["Try"], c["Call"], c["Return"],
            c["Compare"]) == (15, 7, 0, 48, 5, 14)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(am_mod)


def test_source_key_lines_batch54():
    src = _src()
    assert "search_from = find_pos + len(marker)" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if missing_markers:" in src


# ---------- forbidden tokens 第二百二十六批 ----------

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
