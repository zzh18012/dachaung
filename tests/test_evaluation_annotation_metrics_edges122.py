"""evaluation/annotation_metrics.py 第四百三十一轮 edges 测试（Round 987）。

补强 edges121 未触及的角度（第三百六十三批，probe 实证）。

新角度：
- marker 传单空格 " "：在规范化流中命中 chunk 分隔符 →
  after 位 = 分隔符后 → 与预测边界距 1 ≤ 30 → P/R/F1 全 1.0
- 3 chunks 中位锚（CD after）：预测 2 条命中 1 → P 0.5 /
  R 1.0 / F1 = 0.6666666666666666（精确浮点锁定）
- tolerance_chars 传 float 0.5（签名写 int 但运行时照收）：
  距 0 命中、距 1 不命中
- forbidden tokens 第四百五十七批（open 0）
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc2():
    return {"chunks": [{"text": "AB"}, {"text": "CD"}]}


# ---------- 空格 marker ----------

def test_space_marker_matches_separator_batch185():
    ann = {"chunk_boundary_anchors": [
        {"marker": " ", "position": "after"}]}
    out = chunk_boundary_prf(_doc2(), ann)
    assert out["chunk_boundary_precision"] == {"value": 1.0,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {"value": 1.0,
                                        "reason": None}


# ---------- 中位锚 F1 ----------

def test_three_chunks_middle_anchor_f1_batch185():
    doc = {"chunks": [{"text": "AB"}, {"text": "CD"},
                      {"text": "EF"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "CD", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"] == {"value": 0.5,
                                               "reason": None}
    assert out["chunk_boundary_recall"] == {"value": 1.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": 0.6666666666666666, "reason": None}


# ---------- float 容差 ----------

def test_float_tolerance_half_batch185():
    ann_d0 = {"chunk_boundary_anchors": [
        {"marker": "AB", "position": "after"}]}
    ann_d1 = {"chunk_boundary_anchors": [
        {"marker": "CD", "position": "before"}]}
    o1 = chunk_boundary_prf(_doc2(), ann_d0,
                            tolerance_chars=0.5)
    assert o1["chunk_boundary_precision"] == {"value": 1.0,
                                              "reason": None}
    o2 = chunk_boundary_prf(_doc2(), ann_d1,
                            tolerance_chars=0.5)
    assert o2["chunk_boundary_precision"] == {"value": 0.0,
                                              "reason": None}
    assert o2["chunk_boundary_recall"] == {"value": 0.0,
                                           "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am_mod)


def test_source_key_lines_batch185():
    src = _src()
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in src
    assert 'joined_raw = " ".join(norm_chunks)' in src
    assert "stream = normalize_text(joined_raw)" in src
    assert 'if position == "before":' in src


# ---------- forbidden tokens 第四百五十七批 ----------

def test_source_no_eval_batch185():
    assert "eval(" not in _src()


def test_source_no_exec_batch185():
    assert "exec(" not in _src()


def test_source_no_compile_batch185():
    assert "compile(" not in _src()


def test_source_no_globals_batch185():
    assert "globals(" not in _src()


def test_source_no_locals_batch185():
    assert "locals(" not in _src()


def test_source_no_os_system_batch185():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch185():
    assert "subprocess" not in _src()


def test_source_no_popen_batch185():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch185():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch185():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch185():
    assert "socket" not in _src()


def test_source_no_requests_batch185():
    assert "requests" not in _src()


def test_source_no_urllib_batch185():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch185():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch185():
    assert "yield" not in _src()


def test_source_no_async_await_batch185():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch185():
    assert "open(" not in _src()
