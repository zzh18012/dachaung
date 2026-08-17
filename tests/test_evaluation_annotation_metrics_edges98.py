"""evaluation/annotation_metrics.py 第二百七十轮 edges 测试（Round 826）。

补强 edges97 未触及的角度（第二百批）。

新角度：
- annotation 空 dict {}：`if not annotation` falsy →
  no_annotation（空标注与 None 同归宿，但 _tolerance_chars
  仍带）
- document 缺 chunks 键：`or []` → 空列表 → < 2 →
  no_predicted_boundaries 路径（precision/f1 null、
  recall 0.0 非 null、_tolerance_chars 带）
- 单 chunk + 锚点：同路径，_tolerance_chars 记 9
- forbidden tokens 第二百九十六批
"""

from __future__ import annotations

import inspect

import evaluation.annotation_metrics as am
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts):
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors):
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 空标注 ----------

def test_empty_dict_annotation_batch55():
    out = chunk_boundary_prf(_doc("A", "B"), {}, 2)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall",
              "chunk_boundary_f1"):
        assert out[k] == {"value": None,
                          "reason": "no_annotation"}
    assert out["_tolerance_chars"] == {"value": 2, "reason": None}


# ---------- 缺 chunks 键 ----------

def test_document_without_chunks_key_batch55():
    out = chunk_boundary_prf({"elements": []},
                             _ann({"marker": "A"}), 2)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["chunk_boundary_f1"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["_tolerance_chars"] == {"value": 2, "reason": None}


# ---------- 单 chunk ----------

def test_single_chunk_with_anchors_batch55():
    out = chunk_boundary_prf(_doc("AB"),
                             _ann({"marker": "A"}), 9)
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"] == {"value": 0.0,
                                            "reason": None}
    assert out["_tolerance_chars"] == {"value": 9, "reason": None}


# ---------- 源码补强 ----------

def _src():
    return inspect.getsource(am)


def test_source_key_lines_batch55():
    src = _src()
    assert 'chunks = document.get("chunks") or []' in src
    assert "if not chunks or len(chunks) < 2:" in src
    assert 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}' in src


# ---------- forbidden tokens 第二百九十六批 ----------

def test_source_no_eval_batch55():
    assert "eval(" not in _src()


def test_source_no_exec_batch55():
    assert "exec(" not in _src()


def test_source_no_compile_batch55():
    assert "compile(" not in _src()


def test_source_no_globals_batch55():
    assert "globals(" not in _src()


def test_source_no_locals_batch55():
    assert "locals(" not in _src()


def test_source_no_os_system_batch55():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch55():
    assert "subprocess" not in _src()


def test_source_no_popen_batch55():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch55():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch55():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch55():
    assert "socket" not in _src()


def test_source_no_requests_batch55():
    assert "requests" not in _src()


def test_source_no_urllib_batch55():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch55():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch55():
    assert "yield" not in _src()


def test_source_no_async_await_batch55():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch55():
    assert "open(" not in _src()
