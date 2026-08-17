"""evaluation/annotation_metrics.py 第五百四十九轮 edges 测试（Round 1105）。

补强 edges136-138 未触及的角度（第四百八十一批，probe 实证）。

新角度（换行孪生 / 全空串流 / tol 0 刀锋）：
- **换行 marker 即 missing**："BBB\\nmid"——流已
  规范化（换行压成空格）、marker 原样查找 →
  missing——空白家族第三孪生（edges118 TAB、
  R1091 双空格、本批换行）
- **全空串 chunk 流**：chunks ["", "", ""] →
  stream 空、marker BBB 必 missing；但空 chunk
  仍产出预测边界（位置 0）→ P 0.0（reason None，
  非空分母）/ R null no_ground_truth / F1 null
  ——P/R 不对称的三件套形态
- **tol 0 刀锋**：marker 恰在 chunk 1 末尾——
  after gt 恰落边界 d=0 → tol 0 三元组全 1.0
  （≤ 含等号的最紧实证）；before gt 差 4 字符
  → 全 0.0——同一 marker 一字之差在 tol 0 下
  完全二值
- forbidden tokens 第五百七十六批（open 0）
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


def _prf(chunks, anchors, tol=30):
    ann = {"annotation_version": "1.0", "doc_id": "d",
           "chunk_boundary_anchors": anchors}
    return chunk_boundary_prf(_doc(chunks), ann,
                              tolerance_chars=tol)


# ---------- 换行 marker 即 missing ----------

def test_newline_marker_missing_batch304():
    out = _prf(
        ["AAA one.", "BBB mid two.", "CCC end."],
        [{"marker": "BBB\nmid", "position": "before"}])
    assert out["_missing_markers"] == {
        "value": ["BBB\nmid"], "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}


# ---------- 全空串 chunk 流 ----------

def test_all_empty_chunks_batch304():
    out = _prf(["", "", ""],
               [{"marker": "BBB", "position": "before"}])
    assert out["_missing_markers"] == {
        "value": ["BBB"], "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- tol 0 刀锋 ----------

def test_zero_tolerance_knife_batch304():
    board = ["head TAIL", "second chunk body text."]
    after = _prf(board, [{"marker": "TAIL",
                          "position": "after"}],
                 tol=0)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert after[k] == {"value": 1.0,
                            "reason": None}
    before = _prf(board, [{"marker": "TAIL",
                           "position": "before"}],
                  tol=0)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert before[k] == {"value": 0.0,
                             "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch304():
    src = _src()
    assert "used_pred" in src
    assert "used_gt" in src


# ---------- forbidden tokens 第五百七十六批 ----------

def test_source_no_eval_batch304():
    assert "eval(" not in _src()


def test_source_no_exec_batch304():
    assert "exec(" not in _src()


def test_source_no_compile_batch304():
    assert "compile(" not in _src()


def test_source_no_globals_batch304():
    assert "globals(" not in _src()


def test_source_no_locals_batch304():
    assert "locals(" not in _src()


def test_source_no_os_system_batch304():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch304():
    assert "subprocess" not in _src()


def test_source_no_popen_batch304():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch304():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch304():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch304():
    assert "socket" not in _src()


def test_source_no_requests_batch304():
    assert "requests" not in _src()


def test_source_no_urllib_batch304():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch304():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch304():
    assert "yield" not in _src()


def test_source_no_async_await_batch304():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch304():
    assert "open(" not in _src()
