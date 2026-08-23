"""evaluation/annotation_metrics.py 第五百九十六轮 edges 测试（Round 1348）。

补强 edges164 未触及的角度（第七百二十批，probe 实证）。

新角度（中间空 chunk 板 / None text / 乱序吞并交互）：
- **中空 chunk**——[ab,"",cd]
  join 双空格被
  normalize 压掉 →
  preds [2,3] 含
  伪边界 → {0.5,
  1.0, 2/3}
- **None text 等价**
  ——text None 与 ""
  同走 or "" →
  输出全等
- **双中空**——[ab,"",
  "",cd] preds
  [2,3,4] → tol0
  {1/3, 1.0, 0.5}
- **cd-after 翻转**
  ——gt=5 距 pred
  3 差 2 → tol30
  命中 0.5 / tol0
  全零
- **乱序吞并交互**
  ——[cd-before,
  ab-after] 第二锚
  search_from 吞 →
  missing ['ab']
- forbidden tokens 第七百八十九批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import \
    chunk_boundary_prf

MID = {"chunks": [{"text": "ab"}, {"text": ""},
                  {"text": "cd"}]}
TWO = {"chunks": [{"text": "ab"}, {"text": ""},
                  {"text": ""}, {"text": "cd"}]}
NONE_TXT = {"chunks": [{"text": "ab"},
                       {"text": None},
                       {"text": "cd"}]}


def _trio(doc, anchors, tol=30):
    r = chunk_boundary_prf(doc, {
        "chunk_boundary_anchors": anchors}, tol)
    return (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"])


CD_BEFORE = [{"marker": "cd", "position": "before"}]
HALF = ({"value": 0.5, "reason": None},
        {"value": 1.0, "reason": None},
        {"value": 2 / 3, "reason": None})


# ---------- 中空 chunk ----------

def test_mid_empty_cd_before_batch546():
    assert _trio(MID, CD_BEFORE) == HALF


def test_mid_empty_ab_after_batch546():
    assert _trio(MID, [
        {"marker": "ab", "position": "after"}]) == HALF


def test_mid_empty_two_preds_p_half_batch546():
    t = _trio(MID, CD_BEFORE)
    assert t[0]["value"] == 0.5
    assert t[1]["value"] == 1.0
    assert t[2]["value"] == 2 / 3


# ---------- None text 等价 ----------

def test_none_text_equals_empty_batch546():
    a = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": CD_BEFORE}, 30)
    b = chunk_boundary_prf(NONE_TXT, {
        "chunk_boundary_anchors": CD_BEFORE}, 30)
    assert a == b


def test_none_text_half_trio_batch546():
    assert _trio(NONE_TXT, CD_BEFORE) == HALF


# ---------- 双中空 ----------

def test_two_mid_empty_tol0_batch546():
    assert _trio(TWO, CD_BEFORE, 0) == (
        {"value": 1 / 3, "reason": None},
        {"value": 1.0, "reason": None},
        {"value": 0.5, "reason": None})


def test_two_mid_empty_tol30_same_batch546():
    t0 = _trio(TWO, CD_BEFORE, 0)
    t30 = _trio(TWO, CD_BEFORE, 30)
    assert t0 == t30


def test_two_mid_empty_p_third_batch546():
    t = _trio(TWO, CD_BEFORE, 0)
    assert t[0]["value"] == 1 / 3
    assert t[1]["value"] == 1.0


# ---------- cd-after 翻转 ----------

def test_cd_after_tol30_half_batch546():
    assert _trio(MID, [
        {"marker": "cd", "position": "after"}]) == HALF


def test_cd_after_tol0_all_zero_batch546():
    assert _trio(MID, [
        {"marker": "cd", "position": "after"}], 0) == (
        {"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None},
        {"value": 0.0, "reason": None})


# ---------- 乱序吞并交互 ----------

def test_out_of_order_second_swallowed_batch546():
    r = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "before"},
            {"marker": "ab", "position": "after"}]}, 30)
    assert r["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert r["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert r["_missing_markers"] == {
        "value": ["ab"], "reason": None}


def test_out_of_order_key_set_batch546():
    r = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": [
            {"marker": "cd", "position": "before"},
            {"marker": "ab", "position": "after"}]}, 30)
    assert sorted(r.keys()) == [
        "_missing_markers", "_tolerance_chars",
        "chunk_boundary_f1", "chunk_boundary_precision",
        "chunk_boundary_recall"]


def test_hit_board_four_keys_batch546():
    r = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": CD_BEFORE}, 30)
    assert sorted(r.keys()) == [
        "_tolerance_chars", "chunk_boundary_f1",
        "chunk_boundary_precision",
        "chunk_boundary_recall"]


def test_missing_marker_fifth_key_batch546():
    r = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": [
            {"marker": "zz", "position": "before"}]}, 30)
    assert r["_missing_markers"] == {
        "value": ["zz"], "reason": None}


def test_tolerance_echo_batch546():
    r = chunk_boundary_prf(MID, {
        "chunk_boundary_anchors": CD_BEFORE}, 7)
    assert r["_tolerance_chars"] == {
        "value": 7, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_join_renormalize_batch546():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "stream = normalize_text(joined_raw)" in src


def test_source_or_empty_text_batch546():
    assert 'c.get("text") or ""' in _src()


# ---------- forbidden tokens 第七百八十九批 ----------

def test_source_no_eval_batch546():
    assert "eval(" not in _src()


def test_source_no_exec_batch546():
    assert "exec(" not in _src()


def test_source_no_compile_batch546():
    assert "compile(" not in _src()


def test_source_no_globals_batch546():
    assert "globals(" not in _src()


def test_source_no_locals_batch546():
    assert "locals(" not in _src()


def test_source_no_os_system_batch546():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch546():
    assert "subprocess" not in _src()


def test_source_no_popen_batch546():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch546():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch546():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch546():
    assert "socket" not in _src()


def test_source_no_requests_batch546():
    assert "requests" not in _src()


def test_source_no_urllib_batch546():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch546():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch546():
    assert "yield" not in _src()


def test_source_no_async_await_batch546():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_0_batch546():
    assert _src().count("open(") == 0
