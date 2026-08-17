"""evaluation/annotation_metrics.py 第四百六十六轮 edges 测试（Round 1022）。

补强 edges126 未触及的角度（第三百九十八批，probe 实证）。

新角度（missing_markers 细部）：
- 多 marker 缺失按 anchor 列表序保序（["zz1","aa2"]
  非排序）；找到的 zebra 照常匹配 → P/R 仍 1.0
- 空 marker 排在首位时不推进 search_from（marker 假值
  直接 -1，不触碰 find）→ 后续 "apple" 从 0 起找到，
  missing 仅 [""]——与 R1015 乱序吞 marker（zebra 先列
  吞掉 apple）形成对照：空串无害、真 marker 有害
- forbidden tokens 第四百九十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf

_DOC = {"chunks": [{"text": "apple zebra"}, {"text": "tail"}]}


# ---------- 多缺失保序 ----------

def test_multi_missing_anchor_order_batch220():
    ann = {"chunk_boundary_anchors": [
        {"marker": "zz1"}, {"marker": "aa2"},
        {"marker": "zebra"}]}
    r = chunk_boundary_prf(_DOC, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {"value": ["zz1", "aa2"],
                                     "reason": None}
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


# ---------- 空 marker 首位不推进 search_from ----------

def test_empty_marker_first_no_shift_batch220():
    ann = {"chunk_boundary_anchors": [
        {"marker": ""},
        {"marker": "apple", "position": "before"}]}
    r = chunk_boundary_prf(_DOC, ann, tolerance_chars=30)
    assert r["_missing_markers"] == {"value": [""],
                                     "reason": None}
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch220():
    src = _src()
    assert "missing_markers.append(marker)" in src
    assert "if find_pos < 0:" in src
    assert "gt_positions.append(find_pos + len(marker))" in src


# ---------- forbidden tokens 第四百九十二批 ----------

def test_source_no_eval_batch220():
    assert "eval(" not in _src()


def test_source_no_exec_batch220():
    assert "exec(" not in _src()


def test_source_no_compile_batch220():
    assert "compile(" not in _src()


def test_source_no_globals_batch220():
    assert "globals(" not in _src()


def test_source_no_locals_batch220():
    assert "locals(" not in _src()


def test_source_no_os_system_batch220():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch220():
    assert "subprocess" not in _src()


def test_source_no_popen_batch220():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch220():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch220():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch220():
    assert "socket" not in _src()


def test_source_no_requests_batch220():
    assert "requests" not in _src()


def test_source_no_urllib_batch220():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch220():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch220():
    assert "yield" not in _src()


def test_source_no_async_await_batch220():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch220():
    assert "open(" not in _src()
