"""evaluation/annotation_metrics.py 第二百九十八轮 edges 测试（Round 854）。

补强 edges102 未触及的角度（第二百二十八批）。

新角度：
- marker 含正则元字符 "A.B"：str.find 字面语义（非正则）
- CJK marker："中文" 照常定位精确命中
- 2 pred 对 3 anchor（tol=0 两精确一出界）→
  P 1.0、R 2/3、F1 0.8
- chunk_boundary_anchors 传 dict（truthy 非 list）→
  迭代出字符串键 → AttributeError（现状记录）
- forbidden tokens 第三百二十四批
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


# ---------- 字面语义 ----------

def test_regex_meta_marker_literal_batch55():
    out = chunk_boundary_prf(
        _doc("A.B", "CD"), _ann({"marker": "A.B"}), 0)
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- CJK ----------

def test_cjk_marker_batch55():
    out = chunk_boundary_prf(
        _doc("中文", "AB"), _ann({"marker": "中文"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 2 pred 3 anchor ----------

def test_two_preds_three_anchors_batch55():
    out = chunk_boundary_prf(
        _doc("AB", "CD", "EF"),
        _ann({"marker": "AB"}, {"marker": "CD"},
             {"marker": "EF"}), 0)
    assert out["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 2 / 3, "reason": None}
    assert out["chunk_boundary_f1"]["value"] == \
        pytest.approx(0.8)


# ---------- anchors 传 dict ----------

def test_anchors_dict_attribute_error_batch55():
    try:
        chunk_boundary_prf(
            _doc("AB", "CD"),
            {"chunk_boundary_anchors": {"a": 1}}, 3)
        raise AssertionError("no error")
    except AttributeError as e:
        assert "'str' object has no attribute 'get'" in str(e)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src
    assert 'marker = a.get("marker", "")' in src
    assert 'find_pos = stream.find(marker, search_from) if marker else -1' in src


# ---------- forbidden tokens 第三百二十四批 ----------

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
