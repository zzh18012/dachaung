"""evaluation/annotation_metrics.py 第二百六十三轮 edges 测试（Round 819）。

补强 edges96 未触及的角度（第一百九十批）。

新角度：
- marker 跨 chunk 边界 "B C"（含拼接空格）：stream "AB CD"
  中可定位 → 全 1.0
- marker **不做 normalize**：双空格 "A  B" 在单空格流中找不到
  → missing（标注必须写规范化形态 —— 现状记录）
- marker 大小写敏感："a" 在 "A B" 流中 missing
- annotation 无 chunk_boundary_anchors 键 / 值为 None：均落
  `or []` → no_ground_truth_anchors 三连（有预测无标注路径）
- figure_caption_prf 对参数完全不敏感：(None, None) 与
  (doc, ann) 返回相等常量
- forbidden tokens 第二百八十九批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf, \
    figure_caption_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 跨边界 marker ----------

def test_marker_spanning_chunk_boundary_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B C", "position": "after"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- marker 未规范化 ----------

def test_marker_double_space_not_normalized_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "A  B", "position": "after"}), 2)
    assert out["_missing_markers"] == {"value": ["A  B"],
                                       "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 大小写敏感 ----------

def test_marker_case_sensitive_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": "a", "position": "after"}), 2)
    assert out["_missing_markers"] == {"value": ["a"],
                                       "reason": None}


# ---------- 无 anchors 键 ----------

def test_annotation_without_anchors_key_batch55():
    out = chunk_boundary_prf(_doc("A", "B"), {"doc_id": "d"}, 2)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None,
                          "reason": "no_ground_truth_anchors"}


def test_annotation_anchors_none_batch55():
    out = chunk_boundary_prf(
        _doc("A", "B"), {"chunk_boundary_anchors": None}, 2)
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_ground_truth_anchors"}


# ---------- figure_caption 常量 ----------

def test_figure_caption_constant_batch55():
    a = figure_caption_prf(None, None)
    b = figure_caption_prf({"chunks": []}, {"doc_id": "x"})
    assert a == b
    assert a["figure_caption_f1"] == {
        "value": None,
        "reason": "parser_does_not_emit_relations"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src
    assert 'reason = PARSER_DOES_NOT_EMIT_RELATIONS' in src


# ---------- forbidden tokens 第二百八十九批 ----------

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
