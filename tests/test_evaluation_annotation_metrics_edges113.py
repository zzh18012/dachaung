"""evaluation/annotation_metrics.py 第三百六十八轮 edges 测试（Round 924）。

补强 edges112 未触及的角度（第三百批，probe 实证）。

新角度：
- 大小写敏感：normalize_text 保留大小写，marker "ab" 在
  流 "AB CD" 中找不到 → missing ["ab"]、recall null、
  precision 0.0（反向印证 R910 大写 marker 命中）
- 距离平局按生成顺序破：preds [2,4] 争 gt [3]（tol 5，
  d 均 1）→ pi=0 先入 pairs 胜出 → P 0.5 R 1.0 F1 2/3；
  preds [3] 争 gts [1,5]（d 均 2）→ gi=0 胜出 →
  P 1.0 R 0.5 F1 2/3
- 输出 dict 键序：完整命中 [P, R, F1, _tolerance_chars]；
  有缺失再追加 _missing_markers 居末
- figure_caption_prf 键序 [precision, recall, f1]；
  PARSER_DOES_NOT_EMIT_RELATIONS 常量值
- anchors 传字符串 → 逐字符迭代 → AttributeError
- forbidden tokens 第三百九十四批
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


# ---------- 大小写敏感 ----------

def test_lowercase_marker_missing_batch122():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "ab", "position": "after"}), 0)
    assert out["_missing_markers"] == {"value": ["ab"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}


# ---------- 距离平局 ----------

def test_tie_pred_generation_order_wins_batch122():
    out = chunk_boundary_prf(
        _doc("AB", "C", "D"),
        _ann({"marker": "C", "position": "before"}), 5)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-12


def test_tie_gt_generation_order_wins_batch122():
    out = chunk_boundary_prf(
        _doc("ABC", "DEF"),
        _ann({"marker": "B", "position": "before"},
             {"marker": "E", "position": "before"}), 5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-12


# ---------- 键序 ----------

def test_output_key_order_full_hit_batch122():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after"}), 0)
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars"]


def test_output_key_order_missing_last_batch122():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "ZZ", "position": "after"}), 0)
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars",
                         "_missing_markers"]


def test_figure_caption_key_order_batch122():
    out = figure_caption_prf({}, {})
    assert list(out) == ["figure_caption_precision",
                         "figure_caption_recall",
                         "figure_caption_f1"]
    assert PARSER_DOES_NOT_EMIT_RELATIONS == \
        "parser_does_not_emit_relations"


# ---------- anchors 字符串 ----------

def test_anchors_string_attribute_error_batch122():
    with pytest.raises(AttributeError):
        chunk_boundary_prf(
            _doc("AB", "CD"),
            {"chunk_boundary_anchors": "abc"}, 0)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch122():
    src = _src()
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert "norm_chunks = [normalize_text(c.get(\"text\") or \"\") for c in chunks]" in src
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "used_pred.add(pi)" in src


# ---------- forbidden tokens 第三百九十四批 ----------

def test_source_no_eval_batch122():
    assert "eval(" not in _src()


def test_source_no_exec_batch122():
    assert "exec(" not in _src()


def test_source_no_compile_batch122():
    assert "compile(" not in _src()


def test_source_no_globals_batch122():
    assert "globals(" not in _src()


def test_source_no_locals_batch122():
    assert "locals(" not in _src()


def test_source_no_os_system_batch122():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch122():
    assert "subprocess" not in _src()


def test_source_no_popen_batch122():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch122():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch122():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch122():
    assert "socket" not in _src()


def test_source_no_requests_batch122():
    assert "requests" not in _src()


def test_source_no_urllib_batch122():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch122():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch122():
    assert "yield" not in _src()


def test_source_no_async_await_batch122():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch122():
    assert "open(" not in _src()
