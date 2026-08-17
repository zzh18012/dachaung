"""evaluation/annotation_metrics.py 第五百三十五轮 edges 测试（Round 1091）。

补强 edges134-136 未触及的角度（第四百六十七批，probe 实证）。

新角度（marker 空白形态 + 多缺失锚序 + 流尾 after 膝盖）：
- **marker 带首尾单空格照命中**：" BBB " 在规范化流
  （"one. BBB mid"）里逐字找到——marker 不 strip、
  单空格形态流里真实存在 → P 0.5 / R 1.0
- **marker 内双空格即 missing**："BBB  mid"（双空格）
  ——流已规范化单空格、marker 原样查找 → missing +
  P 0.0 / R null / F1 null（edges118 的 TAB 变体的
  空白孪生）
- **多缺失保锚序**：[X1, BBB, X2, X3] 四锚——BBB 命中
  夹在中间不打断缺失序列，_missing_markers ==
  [X1, X2, X3] 严格锚序
- **流尾 after 膝盖**：末 chunk 40 字符整段做 marker
  （after）→ gt 落流尾，最近预测边界在末 chunk 前——
  d=40：tol 30 全 0.0（marker 找到但无一命中）、
  tol 50 全 1.0——after 位置在流尾的距离几何
- forbidden tokens 第五百六十二批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(chunks):
    els = [{"element_id": f"e{i}", "type": "paragraph",
            "content": {"text": t}}
           for i, t in enumerate(chunks)]
    chs = [{"chunk_id": f"c{i}", "text": t,
            "source_element_ids": [f"e{i}"]}
           for i, t in enumerate(chunks)]
    return {"document_id": "d", "elements": els,
            "chunks": chs}


_BOARD = ["AAA first paragraph body one.",
          "BBB mid paragraph body two.",
          "CCC third paragraph body three."]


def _prf(chunks, anchors, tol=30):
    ann = {"annotation_version": "1.0", "doc_id": "d",
           "chunk_boundary_anchors": anchors}
    return chunk_boundary_prf(_doc(chunks), ann,
                              tolerance_chars=tol)


# ---------- marker 首尾单空格照命中 ----------

def test_marker_surrounding_spaces_batch290():
    out = _prf(_BOARD, [
        {"marker": " BBB ", "position": "before"}])
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- marker 内双空格即 missing ----------

def test_marker_double_space_missing_batch290():
    out = _prf(_BOARD, [
        {"marker": "BBB  mid", "position": "before"}])
    assert out["_missing_markers"] == {
        "value": ["BBB  mid"], "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- 多缺失保锚序 ----------

def test_multi_missing_anchor_order_batch290():
    out = _prf(_BOARD, [
        {"marker": "X1", "position": "before"},
        {"marker": "BBB", "position": "before"},
        {"marker": "X2", "position": "before"},
        {"marker": "X3", "position": "before"}])
    assert out["_missing_markers"] == {
        "value": ["X1", "X2", "X3"], "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 流尾 after 膝盖 ----------

def test_trailing_anchor_knee_batch290():
    tail = ["AAA first.", "B" * 40]
    anchors = [{"marker": "B" * 40, "position": "after"}]
    out30 = _prf(tail, anchors, tol=30)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out30[k] == {"value": 0.0, "reason": None}
    assert "_missing_markers" not in out30
    out50 = _prf(tail, anchors, tol=50)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out50[k] == {"value": 1.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch290():
    src = _src()
    assert ('norm_chunks = [normalize_text('
            'c.get("text") or "") for c in chunks]') in src
    assert 'stream = normalize_text(joined_raw)' in src


# ---------- forbidden tokens 第五百六十二批 ----------

def test_source_no_eval_batch290():
    assert "eval(" not in _src()


def test_source_no_exec_batch290():
    assert "exec(" not in _src()


def test_source_no_compile_batch290():
    assert "compile(" not in _src()


def test_source_no_globals_batch290():
    assert "globals(" not in _src()


def test_source_no_locals_batch290():
    assert "locals(" not in _src()


def test_source_no_os_system_batch290():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch290():
    assert "subprocess" not in _src()


def test_source_no_popen_batch290():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch290():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch290():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch290():
    assert "socket" not in _src()


def test_source_no_requests_batch290():
    assert "requests" not in _src()


def test_source_no_urllib_batch290():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch290():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch290():
    assert "yield" not in _src()


def test_source_no_async_await_batch290():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch290():
    assert "open(" not in _src()
