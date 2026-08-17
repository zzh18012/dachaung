"""evaluation/annotation_metrics.py 第四百零三轮 edges 测试（Round 959）。

补强 edges117 未触及的角度（第三百三十五批，probe 实证）。

新角度：
- tolerance_chars=0：精确边界命中（marker AB after 恰在
  预测位 2 → P 0.5 R 1.0）
- tolerance 0 + marker 不在流中 → P 0.0 + R null
  no_ground_truth_anchors_in_stream
- 巨容差 10**9：一对一封顶 → matched = min(pred, gt) =
  2 → P 1.0 R 2/3
- position 非法值 "middle" 走 else 分支 = after 语义 →
  全 1.0
- anchor 携带额外键（confidence/note）被忽略
- anchor 缺 position 键 → 默认 "after"
  （值保留 \\xa0 原字符）+ R null
- marker 原样查找（不规范化）：marker 含 TAB
  "A	B" 在规范化流中找不到 → 进 _missing_markers
- forbidden tokens 第四百二十九批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- tolerance 0 ----------

def test_tolerance_zero_exact_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "AB", "position": "after"}),
        tolerance_chars=0)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


def test_tolerance_zero_missing_marker_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "ABC", "position": "before"}),
        tolerance_chars=0)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 巨容差一对一封顶 ----------

def test_huge_tolerance_capped_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "AB", "position": "before"},
             {"marker": "CD", "position": "before"},
             {"marker": "EF", "position": "before"}),
        tolerance_chars=10**9)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    r = out["chunk_boundary_recall"]["value"]
    assert r is not None and abs(r - 2 / 3) < 1e-9


# ---------- position 非法值 ----------

def test_invalid_position_treated_as_after_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "middle"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 额外键忽略 / 缺 position ----------

def test_anchor_extra_keys_ignored_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "after",
              "confidence": 0.9, "note": "x"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}


def test_anchor_missing_position_defaults_after_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB"}))
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- marker 原样查找（TAB） ----------

def test_marker_tab_not_normalized_batch157():
    out = chunk_boundary_prf(
        _doc("AB", "C"),
        _ann({"marker": "A	B", "position": "after"}))
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["_missing_markers"] == {
        "value": ["A	B"], "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch157():
    src = _src()
    assert 'position = a.get("position", "after")' in src
    assert 'if position == "before":' in src
    assert 'search_from = find_pos + len(marker)' in src
    assert "used_pred = set()" in src and "used_gt = set()" in src


# ---------- forbidden tokens 第四百二十九批 ----------

def test_source_no_eval_batch157():
    assert "eval(" not in _src()


def test_source_no_exec_batch157():
    assert "exec(" not in _src()


def test_source_no_compile_batch157():
    assert "compile(" not in _src()


def test_source_no_globals_batch157():
    assert "globals(" not in _src()


def test_source_no_locals_batch157():
    assert "locals(" not in _src()


def test_source_no_os_system_batch157():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch157():
    assert "subprocess" not in _src()


def test_source_no_popen_batch157():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch157():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch157():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch157():
    assert "socket" not in _src()


def test_source_no_requests_batch157():
    assert "requests" not in _src()


def test_source_no_urllib_batch157():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch157():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch157():
    assert "yield" not in _src()


def test_source_no_async_await_batch157():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch157():
    assert "open(" not in _src()
