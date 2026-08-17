"""evaluation/annotation_metrics.py 第二百三十五轮 edges 测试（Round 791）。

补强 edges92 未触及的角度（第一百五十五批）。

新角度：
- 容差排他：d=2 tol=1 → P=R=F1 全 0.0（denom<=0 → f1 0.0 非 null）
- 零容差精确重合：marker " " before → gt 1 恰等于 pred 1 →
  全 1.0（tolerance_chars 0 可用）
- marker 传 int → TypeError("must be str, not int")
  （stream.find 直接拒，schema 外无防线）
- chunks 列表混入非 dict 元素 → AttributeError
  ('int' object has no attribute 'get')（norm_chunks 循环崩）
- anchor 额外键（"zzz"）被忽略照常匹配
- 超大容差 10**9：等价全匹配 + _tolerance_chars 原样记录
- 对称半分：2 pred 2 anchor 恰 1 配 → P=R=F1=0.5
- forbidden tokens 第二百六十一批
"""

from __future__ import annotations

import inspect

import pytest

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 容差排他 ----------

def test_tolerance_exclusion_all_zero_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "B"}), 1)
    assert out["chunk_boundary_precision"] == {"value": 0.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.0, "reason": None}


# ---------- 零容差精确重合 ----------

def test_zero_tolerance_exact_coincidence_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"),
        _ann({"marker": " ", "position": "before"}), 0)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}
    assert out["_tolerance_chars"] == {"value": 0, "reason": None}


# ---------- 崩溃族 ----------

def test_marker_int_type_error_batch54():
    with pytest.raises(TypeError, match="must be str, not int"):
        chunk_boundary_prf(_doc("A", "B"), _ann({"marker": 5}), 2)


def test_chunk_non_dict_element_attribute_error_batch54():
    with pytest.raises(AttributeError,
                       match="'int' object has no attribute 'get'"):
        chunk_boundary_prf({"chunks": [{"text": "A"}, 5]},
                           _ann({"marker": "B"}), 2)


# ---------- anchor 额外键 ----------

def test_anchor_extra_keys_ignored_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "B", "zzz": 1}), 2)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}


# ---------- 超大容差 ----------

def test_huge_tolerance_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B"), _ann({"marker": "B"}), 10 ** 9)
    assert out["chunk_boundary_f1"] == {"value": 1.0, "reason": None}
    assert out["_tolerance_chars"] == {"value": 10 ** 9, "reason": None}


# ---------- 对称半分 ----------

def test_symmetric_halves_batch54():
    out = chunk_boundary_prf(
        _doc("A", "B", "C"),
        _ann({"marker": "B"}, {"marker": "C"}), 2)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.5, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_branch_lines_batch54():
    src = _src()
    assert "if denom <= 0:" in src
    assert "norm_chunks = [normalize_text(c.get(\"text\") or \"\")" in src
    assert "marker = a.get(\"marker\", \"\")" in src


# ---------- forbidden tokens 第二百六十一批 ----------

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
