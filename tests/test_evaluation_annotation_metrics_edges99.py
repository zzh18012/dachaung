"""evaluation/annotation_metrics.py 第二百七十七轮 edges 测试（Round 833）。

补强 edges98 未触及的角度（第二百零七批）。

新角度：
- position 语义对照：同 doc 同 marker，"before"（gt=marker 起点）
  tol=1 命中 1.0，"after"（gt=marker 终点）tol=1 未命中 0.0
- 全部 marker 缺失：precision 0.0 非 null（预测存在）、
  recall null=no_ground_truth_anchors_in_stream、
  f1 null=precision_or_recall_not_evaluated
- p=r=0.0 → denom<=0 分支 → f1 显式 0.0
- tolerance_chars=0 精确命中（d=0 ≤ 0）
- 含 \\n / \\t 的 chunk 文本经 normalize 后匹配（"C D"）
- 多个缺失 marker 顺序保留
- forbidden tokens 第三百零三批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- before / after 语义 ----------

def test_before_position_hit_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), _ann({"marker": "CD",
                                "position": "before"}), 1)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


def test_after_position_miss_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), _ann({"marker": "CD",
                                "position": "after"}), 1)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- 全部 marker 缺失 ----------

def test_all_markers_missing_shape_batch55():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "ZZZ"}), 30)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": ["ZZZ"],
                                       "reason": None}


# ---------- f1 denom 0 ----------

def test_f1_denom_zero_explicit_batch55():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "CD"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0,
                                        "reason": None}


# ---------- tolerance 0 精确 ----------

def test_tolerance_zero_exact_hit_batch55():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "AB"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 空白规范化 ----------

def test_whitespace_normalized_stream_batch55():
    out = chunk_boundary_prf(
        _doc("A\nB", "C\tD"), _ann({"marker": "C D"}), 4)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 多缺失 marker 顺序 ----------

def test_missing_markers_order_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "Z1"}, {"marker": "Z2"}), 30)
    assert out["_missing_markers"] == {"value": ["Z1", "Z2"],
                                       "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert "search_from = find_pos + len(marker)" in src
    assert "if denom <= 0:" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "pos += len(txt) + 1" in src


# ---------- forbidden tokens 第三百零三批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
