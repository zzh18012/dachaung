"""evaluation/annotation_metrics.py 第五百六十四轮 edges 测试（Round 1204）。

补强 edges141 未触及的角度（第五百七十六批，probe 实证）。

新角度（容差精确界 30/31 / 重复 chunk 文本）：
- **容差精确界**——距界恰 30 → 全 1.0
  （d <= tolerance 含等号）；距界 31 →
  全 0.0——edges137 锁过 d=40/50 的
  宽距两侧，本次锁 30/31 的贴界两侧
  （首锁）
- **中间值容差**——tolerance_chars=7：
  距 30 偏离全 0.0、距 2 命中全 1.0
  （0 与 10**9 之间的普通值同样透传
  + _tolerance_chars 回显 7）
- **重复 chunk 文本**——SAME×3 → 2
  预测界，两个同 marker 锚按 search_
  from 顺流各就各位 → 全 1.0（find
  从 pos 前进不回头首锁）
- **before 贴界**——第二 chunk 起始处
  before 锚距界 1 → 1.0
- forbidden tokens 第六百七十五批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*pairs):
    return {"chunk_boundary_anchors": [
        {"marker": m, "position": p} for m, p in pairs]}


def _prf(r):
    return (r["chunk_boundary_precision"],
            r["chunk_boundary_recall"],
            r["chunk_boundary_f1"])


def _all(value, reason=None):
    return ({"value": value, "reason": reason},
            {"value": value, "reason": reason},
            {"value": value, "reason": reason})


# ---------- 容差精确界 30/31 ----------

def test_tol_dist30_hit_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "B" * 28 + "Z"),
                           _ann(("Z", "after")))
    assert _prf(r) == _all(1.0)


def test_tol_dist31_miss_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "B" * 29 + "Z"),
                           _ann(("Z", "after")))
    assert _prf(r) == _all(0.0)


# ---------- 中间值容差 ----------

def test_tol_intermediate7_miss_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "B" * 28 + "Z"),
                           _ann(("Z", "after")), tolerance_chars=7)
    assert _prf(r) == _all(0.0)
    assert r["_tolerance_chars"] == {"value": 7, "reason": None}


def test_tol_intermediate7_hit_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "B" * 28 + "Z"),
                           _ann(("B", "after")), tolerance_chars=7)
    assert _prf(r) == _all(1.0)
    assert r["_tolerance_chars"] == {"value": 7, "reason": None}


def test_default_tol_echo_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                           _ann(("AAAA", "after")))
    assert r["_tolerance_chars"] == {"value": 30, "reason": None}


# ---------- 重复 chunk 文本 ----------

def test_dup_chunk_texts_batch402():
    r = chunk_boundary_prf(_doc("SAME", "SAME", "SAME"),
                           _ann(("SAME", "after"),
                                ("SAME", "after")))
    assert _prf(r) == _all(1.0)


# ---------- before 贴界 ----------

def test_before_second_chunk_batch402():
    r = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                           _ann(("BBBB", "before")))
    assert _prf(r) == _all(1.0)


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch402():
    src = _src()
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "predicted.append(end)" in src
    assert "gt_positions.append(find_pos)" in src
    assert "gt_positions.append(find_pos + len(marker))" in src
    assert "if find_pos < 0:" in src


# ---------- forbidden tokens 第六百七十五批 ----------

def test_source_no_eval_batch402():
    assert "eval(" not in _src()


def test_source_no_exec_batch402():
    assert "exec(" not in _src()


def test_source_no_compile_batch402():
    assert "compile(" not in _src()


def test_source_no_globals_batch402():
    assert "globals(" not in _src()


def test_source_no_locals_batch402():
    assert "locals(" not in _src()


def test_source_no_os_system_batch402():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch402():
    assert "subprocess" not in _src()


def test_source_no_popen_batch402():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch402():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch402():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch402():
    assert "socket" not in _src()


def test_source_no_requests_batch402():
    assert "requests" not in _src()


def test_source_no_urllib_batch402():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch402():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch402():
    assert "yield" not in _src()


def test_source_no_async_await_batch402():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_no_open_batch402():
    assert "open(" not in _src()
