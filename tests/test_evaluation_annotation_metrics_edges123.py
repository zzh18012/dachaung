"""evaluation/annotation_metrics.py 第四百三十八轮 edges 测试（Round 994）。

补强 edges122 未触及的角度（第三百七十批，probe 实证）。

新角度：
- marker "B C" 跨越 chunk 间分隔符（子串查找不关心语义）
  → after 位与预测边界距 2 → 命中 1.0
- chunk text 内双空格 "A  B" 被 normalize_text 压成
  "A B" → 标注 marker 写单空格照常命中
- chunk text 内换行 "A\nB" 同样压成 "A B" 命中
- 距离恰等于容差（d=2, tol=2）→ <= 含等号命中 1.0；
  tol=1 → 0.0（闭区间边界锁定）
- forbidden tokens 第四百六十四批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _run(chunks, marker, position="after", tolerance=30):
    doc = {"chunks": [{"text": t} for t in chunks]}
    ann = {"chunk_boundary_anchors": [
        {"marker": marker, "position": position}]}
    return chunk_boundary_prf(doc, ann,
                              tolerance_chars=tolerance)


# ---------- 跨界 marker ----------

def test_marker_spanning_separator_batch192():
    out = _run(["AB", "CD"], "B C")
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 双空格规范化 ----------

def test_double_space_normalized_batch192():
    out = _run(["A  B", "CD"], "A B")
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- 换行规范化 ----------

def test_newline_normalized_batch192():
    out = _run(["A\nB", "CD"], "A B")
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}


# ---------- d == 容差闭区间 ----------

def test_distance_equals_tolerance_inclusive_batch192():
    doc_chunks = ["A" * 30, "B"]
    tol2 = _run(doc_chunks, "B", tolerance=2)
    assert tol2["chunk_boundary_precision"] == {
        "value": 1.0, "reason": None}
    tol1 = _run(doc_chunks, "B", tolerance=1)
    assert tol1["chunk_boundary_precision"] == {
        "value": 0.0, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch192():
    src = _src()
    assert "if d <= tolerance_chars:" in src
    assert "missing_markers.append(marker)" in src
    assert "used_pred = set()" in src
    assert "num_pred = len(predicted)" in src


# ---------- forbidden tokens 第四百六十四批 ----------

def test_source_no_eval_batch192():
    assert "eval(" not in _src()


def test_source_no_exec_batch192():
    assert "exec(" not in _src()


def test_source_no_compile_batch192():
    assert "compile(" not in _src()


def test_source_no_globals_batch192():
    assert "globals(" not in _src()


def test_source_no_locals_batch192():
    assert "locals(" not in _src()


def test_source_no_os_system_batch192():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch192():
    assert "subprocess" not in _src()


def test_source_no_popen_batch192():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch192():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch192():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch192():
    assert "socket" not in _src()


def test_source_no_requests_batch192():
    assert "requests" not in _src()


def test_source_no_urllib_batch192():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch192():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch192():
    assert "yield" not in _src()


def test_source_no_async_await_batch192():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch192():
    assert "open(" not in _src()
