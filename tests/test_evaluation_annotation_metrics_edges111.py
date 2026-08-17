"""evaluation/annotation_metrics.py 第三百五十四轮 edges 测试（Round 910）。

补强 edges110 未触及的角度（第二百八十六批，probe 实证）。

新角度：
- 前缀 marker 遮蔽：anchors [B-after, AB-after]，B 命中后
  search_from=2，"AB" 只存在于 pos 0 → missing（指标仍全 1.0
  + _missing_markers ["AB"]）
- 贪心最近：preds [2,4] 争 gt [2]（tol 5）→ 距离 0 者胜出
  → P 0.5 R 1.0 F1 2/3
- forbidden tokens 第三百八十批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 前缀 marker 遮蔽 ----------

def test_prefix_marker_shadows_later_marker_batch108():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B", "position": "after"},
             {"marker": "AB", "position": "after"}), 0)
    # B 命中 pos 1 → gt 2；search_from=2；"AB" 只在 pos 0 → missing
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    assert out["_missing_markers"] == {"value": ["AB"],
                                       "reason": None}


# ---------- 贪心最近 ----------

def test_greedy_nearest_pred_wins_batch108():
    out = chunk_boundary_prf(
        _doc("AB", "C", "D"),
        _ann({"marker": "AB", "position": "after"}), 5)
    # stream "AB C D"，preds [2,4]，gt [2]：d0 胜出
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-12


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch108():
    src = _src()
    assert "d = abs(pv - gv)" in src
    assert "if d <= tolerance_chars:" in src
    assert "used_gt.add(gi)" in src


# ---------- forbidden tokens 第三百八十批 ----------

def test_source_no_eval_batch108():
    assert "eval(" not in _src()


def test_source_no_exec_batch108():
    assert "exec(" not in _src()


def test_source_no_compile_batch108():
    assert "compile(" not in _src()


def test_source_no_globals_batch108():
    assert "globals(" not in _src()


def test_source_no_locals_batch108():
    assert "locals(" not in _src()


def test_source_no_os_system_batch108():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch108():
    assert "subprocess" not in _src()


def test_source_no_popen_batch108():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch108():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch108():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch108():
    assert "socket" not in _src()


def test_source_no_requests_batch108():
    assert "requests" not in _src()


def test_source_no_urllib_batch108():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch108():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch108():
    assert "yield" not in _src()


def test_source_no_async_await_batch108():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch108():
    assert "open(" not in _src()
