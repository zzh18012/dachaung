"""evaluation/annotation_metrics.py 第二百四十九轮 edges 测试（Round 805）。

补强 edges94 未触及的角度（第一百六十九批）。

新角度：
- annotation 传字符串（truthy 非 dict）→ AttributeError
  ('str' object has no attribute 'get')（falsy 才走 no_annotation）
- 主路径负容差 -5：d <= -1 恒假 → 全 0.0（早退分支之外的负值）
- 整流 marker "A B"：after → gt == len(stream)（流末边界）
- 重复 marker 超出现数：stream 只 1 个 "A"、两个 anchor → 第
  二个 missing，但 P=R=F1 全 1.0（recall 分母只数定位成功者，
  与 _missing_markers 并存 —— dup 场景的"分母不含 missing"）
- forbidden tokens 第二百七十五批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


# ---------- annotation 非 dict ----------

def test_annotation_string_attribute_error_batch54():
    with pytest.raises(AttributeError,
                       match="'str' object has no attribute 'get'"):
        chunk_boundary_prf(_doc("A", "B"), "not-a-dict", 2)


# ---------- 主路径负容差 ----------

def test_negative_tolerance_main_path_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        {"chunk_boundary_anchors": [{"marker": "B",
                                     "position": "after"}]}, -5)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}
    assert out["_tolerance_chars"] == {"value": -5, "reason": None}


# ---------- 整流 marker ----------

def test_whole_stream_marker_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        {"chunk_boundary_anchors": [{"marker": "A B",
                                     "position": "after"}]}, 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}


# ---------- 重复 marker 超出现数 ----------

def test_duplicate_marker_beyond_occurrences_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        {"chunk_boundary_anchors": [
            {"marker": "A", "position": "after"},
            {"marker": "A", "position": "after"}]}, 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}
    assert out["_missing_markers"] == {"value": ["A"], "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_early_branches_batch54():
    src = _src()
    assert "if not annotation:" in src
    assert "gt_positions.append(find_pos + len(marker))" in src
    assert "search_from = find_pos + len(marker)" in src


# ---------- forbidden tokens 第二百七十五批 ----------

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
