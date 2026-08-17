"""evaluation/annotation_metrics.py 第四百八十六轮 edges 测试（Round 1042）。

补强 edges129 未触及的角度（第四百一十八批，probe 实证）。

新角度（marker 顺序依赖 + raw/normalized 不对称）：
- 逆序 anchor 对 [DEF-after, ABC-after]：DEF 先命中推进
  search_from=7 后 ABC 从 7 找不到 → missing ["ABC"]，
  但 P/R/F1 全 1.0——吞没静默藏在 missing 里、分数
  无感（与 edges129 重复 marker 家族正交：那是同
  marker 复制，这是不同 marker 逆序）
- marker 不 normalize、stream normalize 的不对称三角：
  尾空格 "ABC " 借 join 空格命中（全 1.0）、双空格
  "ABC  D" 永不命中（P 0.0 / R null / F1 null）、
  chunk 文本里的 \n\n 与 \t 被压成单空格后单空格
  marker 照常命中
- raw 空白 chunk 板（"A\\n\\nB", "C\\tD"）单 pred 双
  gt 争用：P 1.0 / R 0.5 / F1 0.6666666666666666
- forbidden tokens 第五百一十三批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(texts):
    return {"chunks": [{"text": t, "source_element_ids": ["e"]}
                       for t in texts]}


_D = _doc(("ABC", "DEF"))
_KEYS = ("chunk_boundary_precision", "chunk_boundary_recall",
         "chunk_boundary_f1")


# ---------- 逆序 anchor 吞没 ----------

def test_reversed_order_swallows_early_batch240():
    out = chunk_boundary_prf(_D, {"chunk_boundary_anchors": [
        {"marker": "DEF", "position": "after"},
        {"marker": "ABC", "position": "after"}]})
    for k in _KEYS:
        assert out[k] == {"value": 1.0, "reason": None}
    assert out["_missing_markers"] == {"value": ["ABC"],
                                       "reason": None}


# ---------- raw marker × normalized stream ----------

def test_trailing_space_marker_via_join_batch240():
    out = chunk_boundary_prf(_D, {"chunk_boundary_anchors": [
        {"marker": "ABC ", "position": "after"}]})
    for k in _KEYS:
        assert out[k] == {"value": 1.0, "reason": None}
    assert "_missing_markers" not in out


def test_double_space_marker_never_matches_batch240():
    out = chunk_boundary_prf(_D, {"chunk_boundary_anchors": [
        {"marker": "ABC  D", "position": "after"}]})
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}
    assert out["_missing_markers"] == {"value": ["ABC  D"],
                                       "reason": None}


# ---------- raw 空白 chunk 单空格化 ----------

def test_raw_whitespace_chunks_single_spaced_batch240():
    out = chunk_boundary_prf(
        _doc(("A\n\nB", "C\tD")), {"chunk_boundary_anchors": [
            {"marker": "A B", "position": "after"},
            {"marker": "C D", "position": "before"}]})
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 0.5,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}
    assert "_missing_markers" not in out


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch240():
    src = _src()
    assert "if marker else -1" in src
    assert "search_from = find_pos + len(marker)" in src
    assert 'a.get("marker", "")' in src


# ---------- forbidden tokens 第五百一十三批 ----------

def test_source_no_eval_batch240():
    assert "eval(" not in _src()


def test_source_no_exec_batch240():
    assert "exec(" not in _src()


def test_source_no_compile_batch240():
    assert "compile(" not in _src()


def test_source_no_globals_batch240():
    assert "globals(" not in _src()


def test_source_no_locals_batch240():
    assert "locals(" not in _src()


def test_source_no_os_system_batch240():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch240():
    assert "subprocess" not in _src()


def test_source_no_popen_batch240():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch240():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch240():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch240():
    assert "socket" not in _src()


def test_source_no_requests_batch240():
    assert "requests" not in _src()


def test_source_no_urllib_batch240():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch240():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch240():
    assert "yield" not in _src()


def test_source_no_async_await_batch240():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch240():
    assert "open(" not in _src()
