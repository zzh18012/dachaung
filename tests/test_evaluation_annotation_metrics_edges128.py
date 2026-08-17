"""evaluation/annotation_metrics.py 第四百七十三轮 edges 测试（Round 1029）。

补强 edges127 未触及的角度（第四百零五批，probe 实证）。

新角度（五机制单次调用合流）：
- 一份标注 5 anchor 同时触发五种机制：近界一对一
  （CCC after d=1 被 DDD before d=0 挤掉）、跨块
  远端命中（FFF before d=3 吃掉 pred2）、真 missing
  （ZZZ）、顺序吞没（AAA 因 search_from 已过 →
  missing，与 ZZZ 组成 ["ZZZ","AAA"] 按标注序）、
  precision 饱和（P 1.0 而 R 2/3、F1 恰 0.8）
- 同一梯子在容差轴上的硬膝跳：tol ∈ {0,1,2} →
  (0.5, 1/3, 0.4)；tol ≥ 3 → (1.0, 2/3, 0.8)——
  d 集合 {0,1,3} 决定只有一级中间台阶
- _tolerance_chars 原样回显（0 也是值不是 null）
- forbidden tokens 第五百批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf

_DOC = {"chunks": [{"text": t, "source_element_ids": ["e"]}
                   for t in ("AAA BBB CCC", "DDD", "EEE FFF")]}

_ANCHORS = {"chunk_boundary_anchors": [
    {"marker": "CCC", "position": "after"},
    {"marker": "DDD", "position": "before"},
    {"marker": "ZZZ", "position": "after"},
    {"marker": "FFF", "position": "before"},
    {"marker": "AAA", "position": "after"}]}


# ---------- 五机制合流 ----------

def test_five_mechanisms_one_call_batch227():
    out = chunk_boundary_prf(_DOC, _ANCHORS)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 2 / 3, "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 0.8,
                                        "reason": None}
    assert out["_missing_markers"] == {"value": ["ZZZ", "AAA"],
                                       "reason": None}
    assert out["_tolerance_chars"] == {"value": 30,
                                       "reason": None}


def test_recall_exact_fraction_batch227():
    out = chunk_boundary_prf(_DOC, _ANCHORS)
    assert out["chunk_boundary_recall"]["value"] == \
        0.6666666666666666


# ---------- 容差硬膝跳 ----------

def test_tolerance_knee_low_side_batch227():
    for tol in (0, 1, 2):
        out = chunk_boundary_prf(_DOC, _ANCHORS,
                                 tolerance_chars=tol)
        assert out["chunk_boundary_precision"] == {
            "value": 0.5, "reason": None}
        assert out["chunk_boundary_recall"] == {
            "value": 1 / 3, "reason": None}
        assert out["chunk_boundary_f1"] == {"value": 0.4,
                                            "reason": None}


def test_tolerance_knee_high_side_batch227():
    for tol in (3, 4, 30, 10_000):
        out = chunk_boundary_prf(_DOC, _ANCHORS,
                                 tolerance_chars=tol)
        assert out["chunk_boundary_precision"] == {
            "value": 1.0, "reason": None}
        assert out["chunk_boundary_recall"] == {
            "value": 2 / 3, "reason": None}
        assert out["chunk_boundary_f1"] == {"value": 0.8,
                                            "reason": None}


def test_tolerance_zero_echoed_as_value_batch227():
    out = chunk_boundary_prf(_DOC, _ANCHORS,
                             tolerance_chars=0)
    assert out["_tolerance_chars"] == {"value": 0,
                                       "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch227():
    src = _src()
    assert "if d <= tolerance_chars:" in src
    assert "pairs.sort(key=lambda x: x[0])" in src
    assert ("search_from = find_pos + len(marker)"
            in src)


# ---------- forbidden tokens 第五百批 ----------

def test_source_no_eval_batch227():
    assert "eval(" not in _src()


def test_source_no_exec_batch227():
    assert "exec(" not in _src()


def test_source_no_compile_batch227():
    assert "compile(" not in _src()


def test_source_no_globals_batch227():
    assert "globals(" not in _src()


def test_source_no_locals_batch227():
    assert "locals(" not in _src()


def test_source_no_os_system_batch227():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch227():
    assert "subprocess" not in _src()


def test_source_no_popen_batch227():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch227():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch227():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch227():
    assert "socket" not in _src()


def test_source_no_requests_batch227():
    assert "requests" not in _src()


def test_source_no_urllib_batch227():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch227():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch227():
    assert "yield" not in _src()


def test_source_no_async_await_batch227():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch227():
    assert "open(" not in _src()
