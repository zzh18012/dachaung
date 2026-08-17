"""evaluation/annotation_metrics.py 第二百八十四轮 edges 测试（Round 840）。

补强 edges99 未触及的角度（第二百一十四批）。

新角度：
- 预测侧平局：一个 gt 距两个 pred 等距（d=1,1）→
  (d, pi, gi) 元组序先 pi=0 → P 1/2、R 1.0、F1 2/3
- 贪心非最优：可完美匹配（d=3 与 d=1）但贪心先吃近对 →
  只匹配 1 → P=R=F1 0.5（算法现状记录）
- 空 chunk 中间位：join 后双空格被 normalize 压掉 →
  空 txt find("")=pos 产生边界 3，末 chunk 反而丢边界 →
  P 1/2、R 1.0
- position 未知字符串（"weird"）走 else 分支 = after 语义 →
  精确命中 1.0
- figure_caption 对含 figures 数据的标注仍恒 null
- forbidden tokens 第三百一十批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import (
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 预测侧平局 ----------

def test_pred_tie_first_pred_wins_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "C", "DE"),
        _ann({"marker": "C", "position": "before"}), 1)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- 贪心非最优 ----------

def test_greedy_suboptimal_batch55():
    out = chunk_boundary_prf(
        _doc("A", "BCD", "E"),
        _ann({"marker": "D", "position": "before"},
             {"marker": "E", "position": "before"}), 3)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.5,
                                        "reason": None}


# ---------- 空 chunk 中间 ----------

def test_empty_middle_chunk_boundary_quirk_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "", "CD"), _ann({"marker": "CD"}), 3)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- position 未知值 ----------

def test_unknown_position_defaults_after_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "weird"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- figure_caption 恒 null ----------

def test_figure_caption_rich_annotation_still_null_batch55():
    out = figure_caption_prf(
        _doc("A", "B"),
        {"figures": [{"id": "f1"}], "captions": [{"id": "c1"}]})
    for k in ("figure_caption_precision",
              "figure_caption_recall", "figure_caption_f1"):
        assert out[k] == {
            "value": None,
            "reason": "parser_does_not_emit_relations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert "for pi, pv in enumerate(predicted):" in src
    assert "used_pred.add(pi)" in src
    assert 'position = a.get("position", "after")' in src
    assert 'if position == "before":' in src


# ---------- forbidden tokens 第三百一十批 ----------

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
