"""evaluation/annotation_metrics.py 第二百零三轮 edges 测试（Round 728）。

补强 edges81/edges82/edges83 未触及的角度（第九十三批）。

新角度：
- 巨大容差（1e9）仍一对一（2 pred 1 anchor → P=0.5 R=1.0）
- 负容差精确命中也不匹配（d=0 <= -1 假）→ P=R=f1=0.0 全 ratio
- marker 跨 chunk 边界（"B C" 含拼接空格）可找到 → recall 1.0
- 3 pred 1 anchor → P=1/3 R=1.0
- 全部找到时 _missing_markers 键不存在
- normalize_text 依赖性：monkeypatch 恒等后原样双空格 marker 可找到
  （stream 未经规范化，现状记录模块对该函数的依赖）
- __all__ 三元素精确名单
- forbidden tokens 第一百九十八批
"""

from __future__ import annotations

import ast
import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf, figure_caption_prf


def _doc(*texts) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


# ---------- 容差边界 ----------

def test_huge_tolerance_still_one_to_one_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB", "CCCC"),
        {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]},
        tolerance_chars=10**9)
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(0.5)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_negative_tolerance_blocks_exact_match_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB"),
        {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]},
        tolerance_chars=-1)
    assert out["chunk_boundary_precision"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


# ---------- marker 跨边界 ----------

def test_marker_spanning_chunk_boundary_batch53():
    # chunks B/C → stream "B C"；marker "B C" after → gt=3 = pred
    out = chunk_boundary_prf(
        _doc("B", "C"),
        {"chunk_boundary_anchors": [{"marker": "B C", "position": "after"}]})
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- 多 pred 单 anchor ----------

def test_three_preds_one_anchor_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB", "CCCC", "DDDD"),
        {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]})
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(1 / 3)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- _missing_markers 键语义 ----------

def test_missing_markers_key_absent_when_all_found_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB"),
        {"chunk_boundary_anchors": [{"marker": "AAAA"},
                                    {"marker": "BBBB"}]})
    assert "_missing_markers" not in out
    assert "_tolerance_chars" in out


def test_missing_markers_key_present_when_any_lost_batch53():
    out = chunk_boundary_prf(
        _doc("AAAA", "BBBB"),
        {"chunk_boundary_anchors": [{"marker": "AAAA"}, {"marker": "ZZ"}]})
    assert out["_missing_markers"]["value"] == ["ZZ"]


# ---------- normalize_text 依赖 ----------

def test_normalize_identity_dependency_batch53(monkeypatch):
    # 把模块内 normalize_text 换成恒等：拼接后不再压双空格，
    # 原样 "a  b" marker 就能找到（与 edges83 的规范化测试互补）
    monkeypatch.setattr(am, "normalize_text", lambda s: s)
    out = chunk_boundary_prf(
        _doc("a  b", "c"),
        {"chunk_boundary_anchors": [{"marker": "a  b"}]})
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_normalize_uppercase_dependency_batch53(monkeypatch):
    # 恒等 normalize 下，chunk 内部双空格也会原样进入 stream
    monkeypatch.setattr(am, "normalize_text", lambda s: s)
    out = chunk_boundary_prf(
        _doc("a  b", "c"),
        {"chunk_boundary_anchors": [{"marker": "a b"}]})  # 单空格找不到
    assert out["chunk_boundary_recall"]["reason"] == \
        "no_ground_truth_anchors_in_stream"


# ---------- figure_caption 稳定性 ----------

def test_figure_caption_returns_three_nulls_batch53():
    out = figure_caption_prf(None, None)
    assert list(out.keys()) == ["figure_caption_precision",
                                "figure_caption_recall",
                                "figure_caption_f1"]


# ---------- __all__ 与源码 ----------

def test_all_list_exact_batch53():
    tree = ast.parse(inspect.getsource(am))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "__all__")
    assert [e.value for e in all_assign.value.elts] == [
        "PARSER_DOES_NOT_EMIT_RELATIONS", "figure_caption_prf",
        "chunk_boundary_prf",
    ]
    assert am.__all__ == ["PARSER_DOES_NOT_EMIT_RELATIONS",
                          "figure_caption_prf", "chunk_boundary_prf"]


def _src() -> str:
    return inspect.getsource(am)


def test_source_docstring_guarantees_batch53():
    src = _src()
    assert "一对一" in src
    assert "tolerance_chars" in src
    assert "必须在报告中明确记录" in src


# ---------- forbidden tokens 第一百九十八批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
