"""evaluation/annotation_metrics.py 第四百八十轮 edges 测试（Round 1036）。

补强 edges128 未触及的角度（第四百一十二批，probe 实证）。

新角度（分母极端 + 吞没两方向）：
- 10 chunk 单 anchor：precision 1/9 精确浮点
  0.1111111111111111、recall 1.0、F1 浮点工件
  0.19999999999999998（≠0.2）——pred 分母 9 的
  极端分数此前未锁过精确值
- 后缀延伸吞没：anchors [AB-after, ABC-after]，AB
  先命中推进 search_from=2 后 "ABC"（仅存于 0）→
  missing ["ABC"]——与 edges111 前缀遮蔽
  [B-after, AB-after] 成方向互补对
- 9 个重复 marker 大批发：search_from 连环推进后
  8 个 missing、只留 1 个有效 anchor → P/R/F1 全
  1.0——重复灾难被吞没机制静默折叠成单 anchor
  （一对一镜像 9R/1P 不可达：吞没先于匹配发生）
- forbidden tokens 第五百零七批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(texts):
    return {"chunks": [{"text": t, "source_element_ids": ["e"]}
                       for t in texts]}


# ---------- 10 chunk 单 anchor ----------

def test_ten_chunks_single_anchor_batch234():
    out = chunk_boundary_prf(
        _doc(list("ABCDEFGHIJ")),
        {"chunk_boundary_anchors": [
            {"marker": "E", "position": "before"}]})
    assert out["chunk_boundary_precision"] == {
        "value": 1 / 9, "reason": None}
    assert out["chunk_boundary_precision"]["value"] == \
        0.1111111111111111
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.19999999999999998, "reason": None}


# ---------- 后缀延伸吞没 ----------

def test_suffix_extension_swallow_batch234():
    out = chunk_boundary_prf(
        _doc(("ABCD", "EFGH")),
        {"chunk_boundary_anchors": [
            {"marker": "AB", "position": "after"},
            {"marker": "ABC", "position": "after"}]})
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["_missing_markers"] == {"value": ["ABC"],
                                       "reason": None}


# ---------- 重复 marker 大批发折叠 ----------

def test_mass_duplicate_collapse_batch234():
    anchors = {"chunk_boundary_anchors": [
        {"marker": m, "position": "after"}
        for m in ("AB", "A", "B", "AB", "B", "AB", "B",
                  "AB", "B")]}
    out = chunk_boundary_prf(_doc(("AB", "CD")), anchors)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}
    missing = out["_missing_markers"]["value"]
    assert len(missing) == 8
    assert set(missing) == {"AB", "A", "B"}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch234():
    src = _src()
    assert "stream.find(marker, search_from)" in src
    assert "num_pred = len(predicted)" in src
    assert "num_gt = len(gt_positions)" in src


# ---------- forbidden tokens 第五百零七批 ----------

def test_source_no_eval_batch234():
    assert "eval(" not in _src()


def test_source_no_exec_batch234():
    assert "exec(" not in _src()


def test_source_no_compile_batch234():
    assert "compile(" not in _src()


def test_source_no_globals_batch234():
    assert "globals(" not in _src()


def test_source_no_locals_batch234():
    assert "locals(" not in _src()


def test_source_no_os_system_batch234():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch234():
    assert "subprocess" not in _src()


def test_source_no_popen_batch234():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch234():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch234():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch234():
    assert "socket" not in _src()


def test_source_no_requests_batch234():
    assert "requests" not in _src()


def test_source_no_urllib_batch234():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch234():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch234():
    assert "yield" not in _src()


def test_source_no_async_await_batch234():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch234():
    assert "open(" not in _src()
