"""evaluation/annotation_metrics.py 第二百五十六轮 edges 测试（Round 812）。

补强 edges95 未触及的角度（第一百七十六批）。

新角度：
- 全部 marker 命中时 _missing_markers 键**不存在**（条件附加，
  非空字典）
- document None → pipeline_failed 三连 + _tolerance_chars 仍带
  （且无 _missing_markers）
- 3-chunk 精确算术：stream "A B C"、pred [1, 3]、marker "B"
  after → gt 3 → tol 0 时第二边界精确命中（P 0.5 / R 1.0 /
  F1 2/3）
- marker "" 空串：`if marker else -1` 直接判 missing →
  _missing_markers [""] + recall
  no_ground_truth_anchors_in_stream
- 空 chunk 文本：find("") 返回当前 pos → 空串也产出一个预测
  边界（P 0.5 / R 1.0）
- before+after 混合：anchor "AB" before(gt 0) 推进 search_from
  到 2，anchor "B" after 找到 3 → gt 4；单 pred=2 与两 gt 均
  d=2 平局 → 贪心稳定排序取列表靠前者（P 1.0 / R 0.5）
- forbidden tokens 第二百八十二批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- _missing_markers 缺席 ----------

def test_missing_markers_key_absent_when_clean_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "B", "position": "after"}), 2)
    assert "_missing_markers" not in out
    assert "_tolerance_chars" in out


# ---------- document None ----------

def test_document_none_pipeline_failed_batch55():
    out = chunk_boundary_prf(None, _ann({"marker": "B"}), 5)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "pipeline_failed"}
    assert out["chunk_boundary_recall"]["reason"] == \
        "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"
    assert out["_tolerance_chars"] == {"value": 5, "reason": None}
    assert "_missing_markers" not in out


# ---------- 3-chunk 精确算术 ----------

def test_three_chunks_exact_second_boundary_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B", "C"),
        _ann({"marker": "B", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"]["value"] == 2 / 3


# ---------- 空串 marker ----------

def test_empty_string_marker_missing_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "", "position": "after"}), 2)
    assert out["_missing_markers"] == {"value": [""],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"]["reason"] == \
        "precision_or_recall_not_evaluated"


# ---------- 空 chunk 文本 ----------

def test_empty_chunk_text_still_yields_boundary_batch55():
    out = chunk_boundary_prf(
        _doc("A", "", "B"),
        _ann({"marker": "B", "position": "after"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- before/after 平局 ----------

def test_tie_prefers_first_anchor_order_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "B"),
        _ann({"marker": "AB", "position": "before"},
             {"marker": "B", "position": "after"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"]["value"] == 2 / 3


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src
    assert "if missing_markers:" in src
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src


# ---------- forbidden tokens 第二百八十二批 ----------

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
