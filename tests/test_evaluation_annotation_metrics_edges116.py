"""evaluation/annotation_metrics.py 第三百八十九轮 edges 测试（Round 945）。

补强 edges115 未触及的角度（第三百二十一批，probe 实证）。

新角度：
- 预测位置在规范化空间计算：chunk "A\\nB" 规范化成
  "A B"，stream "A B C" 边界 3 与 marker "B" after →
  gt 3 精确重合 → 全 1.0
- chunk 首尾空白被 normalize 剥掉：[" AB ", "CD"] 与
  ["AB","CD"] 同流同界 → 全 1.0
- chunk 内多空格折叠成单空格：marker "A B" 在流
  "A B C" 命中 → 1.0
- anchors 空列表 [] 与显式 None 同一分支 →
  no_ground_truth_anchors 三连
- __all__ 三项有序 [PARSER_DOES_NOT_EMIT_RELATIONS,
  figure_caption_prf, chunk_boundary_prf]
- 单 chunk 早退分支也带 _tolerance_chars（自定义 11
  原样）：precision null no_predicted_boundaries、
  recall 0.0
- forbidden tokens 第四百一十五批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 规范化空间预测位置 ----------

def test_newline_chunk_normalized_pred_batch143():
    out = chunk_boundary_prf(
        _doc("A\nB", "C"),
        _ann({"marker": "B", "position": "after"}))
    # 流 "A B C"：边界 3 = marker B 之后位置
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


def test_chunk_edges_stripped_batch143():
    out = chunk_boundary_prf(
        _doc(" AB ", "CD"),
        _ann({"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


def test_multi_space_collapsed_batch143():
    out = chunk_boundary_prf(
        _doc("A  B", "C"),
        _ann({"marker": "A B", "position": "after"}))
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- anchors 空/None ----------

def test_anchors_empty_list_batch143():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_ground_truth_anchors"}
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors"


def test_anchors_none_batch143():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), {"chunk_boundary_anchors": None})
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_ground_truth_anchors"}


# ---------- __all__ ----------

def test_all_three_ordered_batch143():
    assert am_mod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


# ---------- 单 chunk 分支带 tolerance ----------

def test_single_chunk_branch_tolerance_batch143():
    out = chunk_boundary_prf(
        _doc("AB"), _ann({"marker": "AB"}), tolerance_chars=11)
    assert out["_tolerance_chars"] == {"value": 11,
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch143():
    src = _src()
    assert 'if not chunks or len(chunks) < 2:' in src
    assert 'if not anchors:' in src
    assert 'if not annotation:' in src
    assert 'if document is None:' in src
    assert 'if num_pred == 0:' in src


# ---------- forbidden tokens 第四百一十五批 ----------

def test_source_no_eval_batch143():
    assert "eval(" not in _src()


def test_source_no_exec_batch143():
    assert "exec(" not in _src()


def test_source_no_compile_batch143():
    assert "compile(" not in _src()


def test_source_no_globals_batch143():
    assert "globals(" not in _src()


def test_source_no_locals_batch143():
    assert "locals(" not in _src()


def test_source_no_os_system_batch143():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch143():
    assert "subprocess" not in _src()


def test_source_no_popen_batch143():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch143():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch143():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch143():
    assert "socket" not in _src()


def test_source_no_requests_batch143():
    assert "requests" not in _src()


def test_source_no_urllib_batch143():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch143():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch143():
    assert "yield" not in _src()


def test_source_no_async_await_batch143():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch143():
    assert "open(" not in _src()
