"""evaluation/annotation_metrics.py 第二百二十八轮 edges 测试（Round 784）。

补强 edges87-91 未触及的角度（第一百四十八批）。

新角度：
- 边界位置算术精确锁：chunks ["A","B"] → stream "A B"、
  pred [1]、marker "B" before → gt 2、d=1 tol=1 全 1.0
  （空格分隔符的 off-by-one 语义）
- before-position 落在 stream 位置 0：marker "AB" before → gt 0
  （标注可指流起点，pred [2]、tol=2 恰好覆盖）
- 重复 marker 顺序定位：两个 "A" → gt [1,5]、pred [3]、
  贪心稳定序取第一个 pair → P 1.0 R 0.5 F1 2/3
  （search_from 推进不共享同一 stream 位置）
- missing marker 不进 recall 分母：["ZZ","B"] → R 1.0 但
  _missing_markers ["ZZ"]（recall 只数定位成功的 anchor）
- anchors [5] → AttributeError（int 无 .get，直接调用绕过 schema）
- 单空格 marker " " 可命中（stream 保留词间单空格；与双空格
  missing 对照）
- 全 missing：P 0.0 非 null、R null no_ground_truth_anchors_in_stream、
  F1 null precision_or_recall_not_evaluated（半评估态）
- 贪心最近优先：pred [1,3] gt [3] → 距离 0 的先配 →
  P 0.5 R 1.0 F1 2/3
- 键序精确：precision→recall→f1→_tolerance_chars→[_missing_markers]；
  全找到时 _missing_markers 键不存在
- forbidden tokens 第二百五十四批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 边界位置算术 ----------

def test_exact_boundary_arith_one_char_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "B", "position": "before"}), 1)
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


def test_before_position_at_stream_zero_batch54():
    out = chunk_boundary_prf(
        _doc("AB", "CD"), _ann({"marker": "AB", "position": "before"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- 重复 marker 顺序定位 ----------

def test_duplicate_marker_sequential_positions_batch54():
    out = chunk_boundary_prf(
        _doc("A B", "A B"), _ann({"marker": "A"}, {"marker": "A"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- missing 不进 recall 分母 ----------

def test_missing_marker_not_in_recall_denominator_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "ZZ"}, {"marker": "B"}), 2)
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["_missing_markers"] == {"value": ["ZZ"], "reason": None}


# ---------- anchors 元素非 dict ----------

def test_anchor_int_element_attribute_error_batch54():
    with pytest.raises(AttributeError,
                       match="'int' object has no attribute 'get'"):
        chunk_boundary_prf(_doc("A", "B"), _ann(5), 2)


# ---------- 单空格 marker ----------

def test_single_space_marker_found_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": " "}), 1)
    assert out["chunk_boundary_precision"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- 全 missing 半评估态 ----------

def test_all_markers_missing_precision_zero_f1_null_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "QQ"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None, "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": ["QQ"], "reason": None}


# ---------- 贪心最近优先 ----------

def test_greedy_nearest_pred_wins_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B", "C"), _ann({"marker": "B"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- 键序与 _missing_markers ----------

def test_missing_markers_order_multiplicity_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "ZZ"}, {"marker": "B"}, {"marker": "QQ"}), 2)
    assert out["_missing_markers"]["value"] == ["ZZ", "QQ"]
    assert list(out.keys()) == [
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars", "_missing_markers"]


def test_no_missing_markers_key_when_all_found_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "B"}), 2)
    assert list(out.keys()) == [
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars"]
    assert "_missing_markers" not in out


# ---------- 常量与导出 ----------

def test_module_exports_batch54():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"
    assert am.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf"]


def test_figure_caption_exact_dicts_batch54():
    out = figure_caption_prf({"chunks": []}, {"anything": 1})
    assert out == {
        "figure_caption_precision": {
            "value": None,
            "reason": "parser_does_not_emit_relations"},
        "figure_caption_recall": {
            "value": None,
            "reason": "parser_does_not_emit_relations"},
        "figure_caption_f1": {
            "value": None,
            "reason": "parser_does_not_emit_relations"}}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_matching_lines_batch54():
    src = _src()
    assert "stream = normalize_text(joined_raw)" in src
    assert "search_from = find_pos + len(marker)" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第二百五十四批 ----------

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
