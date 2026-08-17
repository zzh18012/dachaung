"""evaluation/annotation_metrics.py 第三百一十九轮 edges 测试（Round 875）。

补强 edges105 未触及的角度（第二百五十批）。

新角度：
- chunk 首尾空白归一：" AB " + "CD" → 边界仍在 2
- 三重相同 marker "AB"：gt [2,5,8] 对 pred [2,5] →
  P 1.0、R 2/3、F1 0.8
- annotation 缺 chunk_boundary_anchors 键（但有其他键）
  → no_ground_truth_anchors（区别于 no_annotation）
- anchor 带额外未知键：metrics 层不重校验，照常计算
- figure_caption_prf(None, None) 三键 null 固定 reason
- forbidden tokens 第三百四十五批
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


# ---------- chunk 首尾空白 ----------

def test_chunk_edge_whitespace_normalized_batch73():
    out = chunk_boundary_prf(
        _doc(" AB ", "CD"),
        _ann({"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 三重 marker ----------

def test_triple_marker_two_preds_batch73():
    out = chunk_boundary_prf(
        _doc("AB", "AB", "AB"),
        _ann({"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"},
             {"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": pytest.approx(2 / 3), "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(0.8)


# ---------- annotation 缺 anchors 键 ----------

def test_annotation_missing_anchors_key_batch73():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        {"other": 1}, 0)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_ground_truth_anchors"}
    assert out["chunk_boundary_f1"]["reason"] == \
        "no_ground_truth_anchors"


# ---------- anchor 额外键 ----------

def test_anchor_extra_keys_not_revalidated_batch73():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after",
              "zz_extra": 1}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- figure_caption None ----------

def test_figure_caption_none_none_batch73():
    out = figure_caption_prf(None, None)
    assert sorted(out) == ["figure_caption_f1",
                           "figure_caption_precision",
                           "figure_caption_recall"]
    for v in out.values():
        assert v == {"value": None,
                     "reason":
                     "parser_does_not_emit_relations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch73():
    src = _src()
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in src
    assert 'out["chunk_boundary_precision"] = _null("no_ground_truth_anchors")' in src


# ---------- forbidden tokens 第三百四十五批 ----------

def test_source_no_eval_batch73():
    assert "eval(" not in _src()


def test_source_no_exec_batch73():
    assert "exec(" not in _src()


def test_source_no_compile_batch73():
    assert "compile(" not in _src()


def test_source_no_globals_batch73():
    assert "globals(" not in _src()


def test_source_no_locals_batch73():
    assert "locals(" not in _src()


def test_source_no_os_system_batch73():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch73():
    assert "subprocess" not in _src()


def test_source_no_popen_batch73():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch73():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch73():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch73():
    assert "socket" not in _src()


def test_source_no_requests_batch73():
    assert "requests" not in _src()


def test_source_no_urllib_batch73():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch73():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch73():
    assert "yield" not in _src()


def test_source_no_async_await_batch73():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch73():
    assert "open(" not in _src()
