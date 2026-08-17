"""evaluation/annotation_metrics.py 第二百一十四轮 edges 测试（Round 770）。

补强 edges87-89 未触及的角度（第一百三十四批）。

新角度：
- figure_caption_prf 完全无视参数：(None, None) 与带内容 doc/ann 输出
  逐字节相同（三 null + parser_does_not_emit_relations）
- 一对一贪心：1 个预测边界对 2 个等距 anchor（d=0 与 d=1）→
  只 matched 1 → P=1.0 R=0.5 F1=2/3（一个预测不能命中两个标注）
- _tolerance_chars 记录在每个早退分支都在场：document None /
  annotation None；负容差 -5 原样记录（不校验），行为 tol<0 拒配
- 同一缺失 marker 两个 anchor → _missing_markers == ["Y", "Y"]
  （缺失也按 anchor 逐条记录，重复保留）
- 空 marker "" → find 分支 -1 → missing [""]；gt 空 → recall
  null "no_ground_truth_anchors_in_stream"（P 仍 0.0 参与）
- 双空格 marker "A  B" 在规范化流（单空格）中找不到 → missing；
  规范化形式 "A B" → 精确命中 P=1.0
- P=0.0 且 R=0.0 → denom 0 → F1=_ratio(0.0) 而非 null
  （reason None，与 precision_or_recall_not_evaluated 对照）
- 尾部空 chunk：第 2 chunk 的右边界仍是预测边界
  （break 只跳最后一个）→ doc("A","B","") 双 anchor P=R=1.0
- position="middle"（非 before）→ else 分支按 after 语义定位
  （直接调用绕过 schema enum，现状记录）
- forbidden tokens 第二百四十批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- figure_caption 无视参数 ----------

def test_figure_caption_ignores_args_batch54():
    a = figure_caption_prf(None, None)
    b = figure_caption_prf({"chunks": [{"text": "x"}]}, {"y": 1})
    assert a == b
    for k in ("figure_caption_precision", "figure_caption_recall",
              "figure_caption_f1"):
        assert a[k] == {"value": None,
                        "reason": PARSER_DOES_NOT_EMIT_RELATIONS}
    assert PARSER_DOES_NOT_EMIT_RELATIONS == \
        "parser_does_not_emit_relations"


# ---------- 一对一贪心：1 pred 对 2 gt ----------

def test_one_pred_two_anchors_half_recall_batch54():
    out = chunk_boundary_prf(
        _doc("xAB", "CDy"),
        _ann({"marker": "AB"},
             {"marker": "CD", "position": "before"}),
        tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- _tolerance_chars 早退分支 ----------

def test_tolerance_record_doc_none_batch54():
    out = chunk_boundary_prf(None, _ann({"marker": "A"}),
                             tolerance_chars=9)
    assert sorted(out) == ["_tolerance_chars", "chunk_boundary_f1",
                           "chunk_boundary_precision",
                           "chunk_boundary_recall"]
    assert out["_tolerance_chars"] == {"value": 9, "reason": None}


def test_tolerance_record_annotation_none_batch54():
    out = chunk_boundary_prf(_doc("A"), None, tolerance_chars=9)
    assert out["_tolerance_chars"] == {"value": 9, "reason": None}


def test_negative_tolerance_recorded_raw_batch54():
    out = chunk_boundary_prf(_doc("A", "B"), _ann({"marker": "A"}),
                             tolerance_chars=-5)
    assert out["_tolerance_chars"] == {"value": -5, "reason": None}
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- 缺失 marker 记录 ----------

def test_missing_marker_duplicated_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "Y"}, {"marker": "Y"}))
    assert out["_missing_markers"] == {"value": ["Y", "Y"],
                                       "reason": None}


def test_empty_marker_missing_and_recall_null_batch54():
    out = chunk_boundary_prf(_doc("AB", "CD"), _ann({"marker": ""}))
    assert out["_missing_markers"] == {"value": [""], "reason": None}
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 规范化交互 ----------

def test_double_space_marker_missing_batch54():
    out = chunk_boundary_prf(_doc("A  B", "C"), _ann({"marker": "A  B"}))
    assert out["_missing_markers"] == {"value": ["A  B"],
                                       "reason": None}


def test_normalized_marker_exact_hit_batch54():
    out = chunk_boundary_prf(_doc("A  B", "C"), _ann({"marker": "A B"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- F1 零分母 ----------

def test_f1_zero_when_both_zero_batch54():
    out = chunk_boundary_prf(
        _doc("AAAA", "B"),
        _ann({"marker": "B", "position": "before"}),
        tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


# ---------- 尾部空 chunk ----------

def test_trailing_empty_chunk_boundary_counted_batch54():
    out = chunk_boundary_prf(_doc("A", "B", ""),
                             _ann({"marker": "A"}, {"marker": "B"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- position 非 before → after 语义 ----------

def test_position_middle_treated_as_after_batch54():
    out = chunk_boundary_prf(
        _doc("xAB", "C"),
        _ann({"marker": "AB", "position": "middle"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_greedy_and_guard_lines_batch54():
    src = _src()
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "if marker else -1" in src
    assert "search_from = find_pos + len(marker)" in src
    assert "if denom <= 0:" in src


# ---------- forbidden tokens 第二百四十批 ----------

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
