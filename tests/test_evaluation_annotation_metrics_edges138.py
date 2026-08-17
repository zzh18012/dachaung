"""evaluation/annotation_metrics.py 第五百四十二轮 edges 测试（Round 1098）。

补强 edges135-137 未触及的角度（第四百七十四批，probe 实证）。

新角度（跨块标记 / 空串锚 / position 语义载荷 / 双现仲裁）：
- **跨块标记照命中**："para graph" 横跨两 chunk
  （"…para" + "graph…"）→ 不 missing、P 1.0 /
  R 1.0——stream 用空格 join，跨块文本可寻
  （块边界在标记中间不打断查找）
- **空串 marker 即 missing [""]**：find guard
  `if marker else -1` 直接落空 → P 0.0 /
  R null no_ground_truth / F1 null
  precision_or_recall（R1084 只锁了 guard 源码行，
  行为首锁）
- **position 语义载荷**：marker "BBBBB" 恰在 chunk
  1 末尾、tol 1——before gt 在边界前 5 字符 → 全
  0.0；after gt 恰落边界 → 0.5 / 1.0 /
  0.6666666666666666——before/after 差一个
  len(marker)，紧容差下分野
- **双现同名仲裁**：[BBB, BBB] 双锚、流中两次真实
  出现（search_from 顺序推进各得其所）→ 无
  missing、P/R/F1 全 0.5——一对一贪心配对下两
  gt 争一边界，双方各半
- forbidden tokens 第五百六十九批（open 0）
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


# ---------- 跨块标记照命中 ----------

def test_marker_spanning_chunks_found_batch297():
    out = _prf(["AAA first para", "graph body two."],
               [{"marker": "para graph",
                 "position": "before"}])
    assert "_missing_markers" not in out
    assert out["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}


# ---------- 空串 marker 即 missing ----------

def test_empty_marker_missing_batch297():
    out = _prf(["AAA one.", "BBB two."],
               [{"marker": "", "position": "before"}])
    assert out["_missing_markers"] == {
        "value": [""], "reason": None}
    assert out["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"] == {
        "value": None,
        "reason": "no_ground_truth_anchors_in_stream"}
    assert out["chunk_boundary_f1"] == {
        "value": None,
        "reason": "precision_or_recall_not_evaluated"}


# ---------- position 语义载荷 ----------

def test_position_semantics_tight_tol_batch297():
    board = ["AAAA first.", "second BBBBB.",
             "third tail."]
    before = _prf(board, [{"marker": "BBBBB",
                           "position": "before"}],
                  tol=1)
    after = _prf(board, [{"marker": "BBBBB",
                          "position": "after"}],
                 tol=1)
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall", "chunk_boundary_f1"):
        assert before[k] == {"value": 0.0,
                             "reason": None}
    assert after["chunk_boundary_precision"] == {
        "value": 0.5, "reason": None}
    assert after["chunk_boundary_recall"] == {
        "value": 1.0, "reason": None}
    assert after["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- 双现同名仲裁 ----------

def test_dup_marker_two_occurrences_batch297():
    out = _prf(["BBB alpha one.", "mid BBB delta two.",
                "tail end."],
               [{"marker": "BBB", "position": "before"},
                {"marker": "BBB", "position": "before"}])
    assert "_missing_markers" not in out
    for k in ("chunk_boundary_precision",
              "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": 0.5,
                          "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch297():
    src = _src()
    assert src.count("stream.find(") == 2
    assert src.count("normalize_text(") == 3


# ---------- forbidden tokens 第五百六十九批 ----------

def test_source_no_eval_batch297():
    assert "eval(" not in _src()


def test_source_no_exec_batch297():
    assert "exec(" not in _src()


def test_source_no_compile_batch297():
    assert "compile(" not in _src()


def test_source_no_globals_batch297():
    assert "globals(" not in _src()


def test_source_no_locals_batch297():
    assert "locals(" not in _src()


def test_source_no_os_system_batch297():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch297():
    assert "subprocess" not in _src()


def test_source_no_popen_batch297():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch297():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch297():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch297():
    assert "socket" not in _src()


def test_source_no_requests_batch297():
    assert "requests" not in _src()


def test_source_no_urllib_batch297():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch297():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch297():
    assert "yield" not in _src()


def test_source_no_async_await_batch297():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch297():
    assert "open(" not in _src()
