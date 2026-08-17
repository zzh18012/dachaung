"""evaluation/annotation_metrics.py 第三百二十六轮 edges 测试（Round 882）。

补强 edges106 未触及的角度（第二百五十七批）。

新角度：
- marker "B C" after：gt=4 对 pred=2，tol 2 命中
- 返回 dict 键序 [precision, recall, f1,
  _tolerance_chars]（插入序锁定）
- marker 单空格 " "：可定位（stream 保留单空格分隔）
- tolerance_chars 传 float 1.5：不做 int 强转，
  记录原值、按 float 比较
- 单 chunk 早退：precision/f1 null
  no_predicted_boundaries + recall 0.0
- forbidden tokens 第三百五十二批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 跨界 after ----------

def test_span_marker_after_tol2_batch80():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B C", "position": "after"}), 2)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 键序 ----------

def test_return_key_order_batch80():
    out = chunk_boundary_prf(_doc("AB", "CD"), _ann(), 3)
    assert list(out) == ["chunk_boundary_precision",
                         "chunk_boundary_recall",
                         "chunk_boundary_f1",
                         "_tolerance_chars"]


# ---------- 空格 marker ----------

def test_space_marker_locatable_batch80():
    # "AB CD"：空格在 2，after → gt=3；pred（chunk0 末）=2，
    # d=1 → tol 1 命中、tol 0 失配
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": " ", "position": "after"}), 1)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    out0 = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": " ", "position": "after"}), 0)
    assert out0["chunk_boundary_f1"] == {"value": 0.0,
                                         "reason": None}


# ---------- float 容差 ----------

def test_float_tolerance_passthrough_batch80():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B C", "position": "after"}), 1.5)
    assert out["_tolerance_chars"] == {"value": 1.5,
                                       "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


# ---------- 单 chunk 早退 ----------

def test_single_chunk_early_return_batch80():
    out = chunk_boundary_prf(
        _doc("AB"),
        _ann({"marker": "AB", "position": "after"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"]["reason"] == \
        "no_predicted_boundaries"


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch80():
    src = _src()
    assert "if not chunks or len(chunks) < 2:" in src
    assert 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}' in src
    assert "_null(\"no_predicted_boundaries\") if not anchors else _ratio(0.0)" in src


# ---------- forbidden tokens 第三百五十二批 ----------

def test_source_no_eval_batch80():
    assert "eval(" not in _src()


def test_source_no_exec_batch80():
    assert "exec(" not in _src()


def test_source_no_compile_batch80():
    assert "compile(" not in _src()


def test_source_no_globals_batch80():
    assert "globals(" not in _src()


def test_source_no_locals_batch80():
    assert "locals(" not in _src()


def test_source_no_os_system_batch80():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch80():
    assert "subprocess" not in _src()


def test_source_no_popen_batch80():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch80():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch80():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch80():
    assert "socket" not in _src()


def test_source_no_requests_batch80():
    assert "requests" not in _src()


def test_source_no_urllib_batch80():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch80():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch80():
    assert "yield" not in _src()


def test_source_no_async_await_batch80():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch80():
    assert "open(" not in _src()
