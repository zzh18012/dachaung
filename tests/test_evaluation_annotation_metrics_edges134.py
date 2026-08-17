"""evaluation/annotation_metrics.py 第五百一十四轮 edges 测试（Round 1070）。

补强 edges130-133 未触及的角度（第四百四十六批，probe 实证）。

新角度（跨接缝 marker 的 before/after 几何不对称膝关节）：
- 流 "AB C"、接缝在 2、marker "B C" 跨缝——同一 marker
  两位置膝盖不同：**before** → gt=marker 起点 1（偏移
  1）→ tol 0 全 0.0、tol 1 全 1.0；**after** → gt=marker
  终点 4（偏移 2，pre+post 两侧都计入）→ tol 0/1 全
  0.0、tol 2 才全 1.0——after 比 before 多拐一格
- **tol 0 只收精确重合**：对照 marker "B" after（终点恰
  落接缝 2，d=0）→ 任意容差（含 0）全 1.0
- 双接缝板 ["AB","CD","EF"]：真实跨缝 marker "D E"
  after 可找到但距最近预测边界 2（tol 0 落空）；不存
  在的 "C D"（CD 间无空格）进 _missing_markers——同板
  找到/缺失双态
- edges115 跨缝只验可找到（tol 10^9）、edges123 膝盖
  用素 marker——缝上 before/after 不对称系首锁
- forbidden tokens 第五百四十一批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(chunks):
    return {"chunks": [{"text": t} for t in chunks]}


def _prf(chunks, marker, position, tol):
    ann = {"annotation_version": "1.0", "doc_id": "x",
           "chunk_boundary_anchors": [
               {"marker": marker,
                "position": position}]}
    out = chunk_boundary_prf(_doc(chunks), ann,
                             tolerance_chars=tol)
    return {k: out[k]["value"] for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1")}, out


_Z = {"chunk_boundary_precision": 0.0,
      "chunk_boundary_recall": 0.0,
      "chunk_boundary_f1": 0.0}
_O = {"chunk_boundary_precision": 1.0,
      "chunk_boundary_recall": 1.0,
      "chunk_boundary_f1": 1.0}


# ---------- 跨缝 before：膝盖 1 ----------

def test_span_before_knee_one_batch269():
    assert _prf(["AB", "C"], "B C", "before", 0)[0] == _Z
    assert _prf(["AB", "C"], "B C", "before", 1)[0] == _O


# ---------- 跨缝 after：膝盖 2（不对称） ----------

def test_span_after_knee_two_batch269():
    assert _prf(["AB", "C"], "B C", "after", 0)[0] == _Z
    assert _prf(["AB", "C"], "B C", "after", 1)[0] == _Z
    assert _prf(["AB", "C"], "B C", "after", 2)[0] == _O


# ---------- tol 0 只收精确重合（对照） ----------

def test_plain_marker_exact_any_tol_batch269():
    for tol in (0, 1, 2):
        assert _prf(["AB", "C"], "B", "after",
                     tol)[0] == _O


# ---------- 双接缝：找到/缺失双态 ----------

def test_two_join_mixed_missing_batch269():
    ann = {"annotation_version": "1.0", "doc_id": "x",
           "chunk_boundary_anchors": [
               {"marker": "D E", "position": "after"},
               {"marker": "C D",
                "position": "before"}]}
    out = chunk_boundary_prf(_doc(["AB", "CD", "EF"]), ann,
                             tolerance_chars=0)
    vals = {k: out[k]["value"] for k in (
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1")}
    assert vals == _Z
    assert out["_missing_markers"] == {
        "value": ["C D"], "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch269():
    src = _src()
    assert "stream = normalize_text(joined_raw)" in src
    assert "if d <= tolerance_chars:" in src


# ---------- forbidden tokens 第五百四十一批 ----------

def test_source_no_eval_batch269():
    assert "eval(" not in _src()


def test_source_no_exec_batch269():
    assert "exec(" not in _src()


def test_source_no_compile_batch269():
    assert "compile(" not in _src()


def test_source_no_globals_batch269():
    assert "globals(" not in _src()


def test_source_no_locals_batch269():
    assert "locals(" not in _src()


def test_source_no_os_system_batch269():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch269():
    assert "subprocess" not in _src()


def test_source_no_popen_batch269():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch269():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch269():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch269():
    assert "socket" not in _src()


def test_source_no_requests_batch269():
    assert "requests" not in _src()


def test_source_no_urllib_batch269():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch269():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch269():
    assert "yield" not in _src()


def test_source_no_async_await_batch269():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch269():
    assert "open(" not in _src()
