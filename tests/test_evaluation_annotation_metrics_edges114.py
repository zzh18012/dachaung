"""evaluation/annotation_metrics.py 第三百七十五轮 edges 测试（Round 931）。

补强 edges113 未触及的角度（第三百零七批，probe 实证）。

新角度：
- 重复 marker 顺序定位：两个 after-anchor 同为 "AB"（流
  "AB AB"）→ gt [2,5]、pred [2] → p 1.0 / r 0.5 / f1 2/3
- 空首 chunk 怪癖：chunks ["","AB"] → 预测边界落在位置 0
  （空串 find 返回 0），anchor "AB" after → gt 2 命中 → 全 1.0
- 缺失 marker 不推进 search_from：[ZZZ 缺, AB 中] → r 1.0
  且 _missing_markers 只含 ZZZ；完整键序末两位
  _tolerance_chars → _missing_markers
- marker 本身不规范化：含 \t 的 marker 在规范化流中找不到
  （chunk 文本才被 normalize），空格版本命中
- 全部 marker 缺失的不对称：precision 0.0（分母 num_pred）
  而 recall null no_ground_truth_anchors_in_stream、
  f1 null precision_or_recall_not_evaluated
- 容差边界含等号：d=1 时 tol=1 命中、tol=0 不命中；
  marker "D" before 造 d=2：tol=2 命中、tol=1 不命中
- 三连重复 chunk：pred [2,5] 与两 anchor 精确对齐 → 全 1.0
- figure_caption_prf 无视实参（连真实标注都给 null 三连）
- chunks 键缺失 / 显式 None + 有 anchor → precision null
  no_predicted_boundaries、recall 0.0（_ratio(0.0) 非 null）
- forbidden tokens 第四百零一批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 重复 marker 顺序定位 ----------

def test_duplicate_marker_sequential_gt_batch129():
    out = chunk_boundary_prf(
        _doc("AB", "AB"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- 空首 chunk 怪癖 ----------

def test_empty_first_chunk_boundary_zero_batch129():
    out = chunk_boundary_prf(
        _doc("", "AB"),
        _ann({"marker": "AB", "position": "after"}))
    # 空串 find 返回 0 → 预测边界在位置 0；gt=2，d=2 ≤ 30 命中
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- 缺失 marker 不推进 search_from ----------

def test_missing_marker_keeps_search_from_batch129():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "ZZZ"},
             {"marker": "AB", "position": "after"}))
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["_missing_markers"] == {"value": ["ZZZ"],
                                       "reason": None}
    assert list(out) == [
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars", "_missing_markers"]


# ---------- marker 不规范化 ----------

def test_marker_not_normalized_tab_batch129():
    out = chunk_boundary_prf(
        _doc("A\nB", "CD"),
        _ann({"marker": "A\tB", "position": "after"},
             {"marker": "A B", "position": "after"}))
    # 流是 "A B CD"：含 \t 的 marker 找不到，空格版命中
    assert out["_missing_markers"] == {"value": ["A\tB"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 全部 marker 缺失的不对称 ----------

def test_all_markers_missing_precision_zero_batch129():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "X1"}, {"marker": "X2"}))
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": ["X1", "X2"],
                                       "reason": None}


# ---------- 容差边界含等号 ----------

def test_tolerance_boundary_inclusive_batch129():
    ann = _ann({"marker": "CD", "position": "before"})
    # stream "AB CD"：pred=2，gt=3 → d=1
    assert chunk_boundary_prf(_doc("AB", "CD"), ann,
                              tolerance_chars=1
                              )["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert chunk_boundary_prf(_doc("AB", "CD"), ann,
                              tolerance_chars=0
                              )["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    ann2 = _ann({"marker": "D", "position": "before"})
    # marker "D" before → gt=4 → d=2
    assert chunk_boundary_prf(_doc("AB", "CD"), ann2,
                              tolerance_chars=2
                              )["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert chunk_boundary_prf(_doc("AB", "CD"), ann2,
                              tolerance_chars=1
                              )["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}


# ---------- 三连重复 chunk ----------

def test_triple_repeated_chunks_batch129():
    out = chunk_boundary_prf(
        _doc("AB", "AB", "AB"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}))
    # pred [2,5] 与 gt [2,5] 精确对齐
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- figure_caption 无视实参 ----------

def test_figure_caption_ignores_annotation_batch129():
    out = figure_caption_prf({"figures": ["f"]},
                             {"figure_caption_pairs": [[1, 2]]})
    assert list(out) == ["figure_caption_precision",
                         "figure_caption_recall",
                         "figure_caption_f1"]
    for v in out.values():
        assert v == {"value": None,
                     "reason": "parser_does_not_emit_relations"}


# ---------- chunks 键缺失 / None ----------

def test_no_chunks_key_with_anchors_batch129():
    out = chunk_boundary_prf({}, _ann({"marker": "AB"}))
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    out2 = chunk_boundary_prf({"chunks": None},
                              _ann({"marker": "AB"}))
    assert out2["chunk_boundary_recall"] == {"value": 0.0,
                                             "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch129():
    src = _src()
    assert "stream = normalize_text(joined_raw)" in src
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src
    assert "search_from = find_pos + len(marker)" in src
    assert "if d <= tolerance_chars:" in src
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src


# ---------- forbidden tokens 第四百零一批 ----------

def test_source_no_eval_batch129():
    assert "eval(" not in _src()


def test_source_no_exec_batch129():
    assert "exec(" not in _src()


def test_source_no_compile_batch129():
    assert "compile(" not in _src()


def test_source_no_globals_batch129():
    assert "globals(" not in _src()


def test_source_no_locals_batch129():
    assert "locals(" not in _src()


def test_source_no_os_system_batch129():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch129():
    assert "subprocess" not in _src()


def test_source_no_popen_batch129():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch129():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch129():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch129():
    assert "socket" not in _src()


def test_source_no_requests_batch129():
    assert "requests" not in _src()


def test_source_no_urllib_batch129():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch129():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch129():
    assert "yield" not in _src()


def test_source_no_async_await_batch129():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch129():
    assert "open(" not in _src()
