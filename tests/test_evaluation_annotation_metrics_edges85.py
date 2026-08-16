"""evaluation/annotation_metrics.py 第二百零四轮 edges 测试（Round 735）。

补强 edges83/edges84 未触及的角度（第一百批）。

新角度：
- 重复 marker 顺序定位：两个相同 "X" 各自命中第 1/第 2 次出现 → P=R=1.0
  （search_from 不推进则只会 0.5）
- 顺序推进副作用：后一个 anchor 无法命中更早的覆盖 marker
  （"B" 先占位，"AB" 只在 0 处出现 → missing）
- position 非 before/after（"middle"）→ else 分支按 after 语义
- 纯空白 chunk：normalize 得空串，find("")=0 仍产出边界 → P=R=1.0
- 容差精确边界：d == tolerance 命中、d == tolerance+1 不命中
- find 失败回退分支（108-111 行）：stateful monkeypatch normalize
  使拼接流删掉 chunk 文本 → num_pred=0、P null、R 0.0、
  f1 precision_or_recall_not_evaluated
- _null/_ratio 与 evaluation.metrics 跨模块同一对象
- AST（chunk_boundary_prf If15·For7·Continue3·Break1）
- forbidden tokens 第二百零五批
"""

from __future__ import annotations

import ast
import collections
import inspect

import pytest

import evaluation.annotation_metrics as am
import evaluation.metrics as mm
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors) -> dict:
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 跨模块私有导入 ----------

def test_null_ratio_same_objects_as_metrics_batch54():
    assert am._null is mm._null
    assert am._ratio is mm._ratio


# ---------- 重复 marker 顺序定位 ----------

def test_duplicate_markers_sequential_locations_batch54():
    out = chunk_boundary_prf(
        _doc("XA", "XB", "XC"),
        _ann({"marker": "X", "position": "after"},
             {"marker": "X", "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert "_missing_markers" not in out


def test_sequential_advance_hides_earlier_marker_batch54():
    # "B" 先命中 @1 并推进起点到 2；"AB" 只在 0 处出现 → missing
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "B"}, {"marker": "AB"}))
    assert out["_missing_markers"]["value"] == ["AB"]
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- position 语义 ----------

def test_unrecognized_position_defaults_to_after_batch54():
    out = chunk_boundary_prf(
        _doc("AB", "CD"),
        _ann({"marker": "AB", "position": "middle"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 空白 chunk ----------

def test_whitespace_only_chunk_still_emits_boundary_batch54():
    out = chunk_boundary_prf(
        _doc("   ", "B C"),
        _ann({"marker": "B", "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 容差精确边界 ----------

def test_tolerance_exact_boundary_inclusive_batch54():
    # pred 边界在 4；marker "AA" after → gt=2；d=2
    tol2 = chunk_boundary_prf(
        _doc("AAAB", "B"),
        _ann({"marker": "AA", "position": "after"}), tolerance_chars=2)
    tol1 = chunk_boundary_prf(
        _doc("AAAB", "B"),
        _ann({"marker": "AA", "position": "after"}), tolerance_chars=1)
    assert tol2["chunk_boundary_precision"]["value"] == 1.0
    assert tol1["chunk_boundary_precision"]["value"] == 0.0
    assert tol1["chunk_boundary_f1"]["value"] == 0.0


# ---------- find 失败回退分支 ----------

def test_find_fallback_branch_via_stateful_normalize_batch54(monkeypatch):
    # 前 2 次调用（逐 chunk）原样返回；第 3 次（拼接流）删掉 "aa"
    # → stream 里找不到 chunk 文本 → 回退分支 + num_pred=0
    calls = {"n": 0}

    def weird(s):
        calls["n"] += 1
        if calls["n"] <= 2:
            return s
        return s.replace("aa", "")

    monkeypatch.setattr(am, "normalize_text", weird)
    out = chunk_boundary_prf(
        _doc("aa", "bb"),
        _ann({"marker": "bb", "position": "after"}))
    assert calls["n"] == 3
    assert out["chunk_boundary_precision"] == {
        "value": None, "reason": "no_predicted_boundaries"}
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == \
        "precision_or_recall_not_evaluated"


# ---------- AST ----------

def test_ast_chunk_boundary_prf_structure_batch54():
    tree = ast.parse(inspect.getsource(am))
    f = next(n for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    c = collections.Counter(type(n).__name__ for n in ast.walk(f))
    assert (c["If"], c["For"], c["Continue"], c["Break"], c["ListComp"],
            c["Dict"]) == (15, 7, 3, 1, 1, 7)


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(am)


def test_source_sequential_comment_batch54():
    src = _src()
    assert "重复 marker 顺序定位" in src
    assert "不允许两个 anchor 共享同一 stream 位置" in src
    assert "理论上不该发生" in src


def test_source_private_import_batch54():
    assert "from evaluation.metrics import _null, _ratio" in _src()


# ---------- forbidden tokens 第二百零五批 ----------

def test_source_no_eval_batch54():
    assert "eval(" not in _src()


def test_source_no_exec_batch54():
    assert "exec(" not in _src()


def test_source_no_compile_batch54():
    assert "compile(" not in _src()


def test_source_no_globals_batch54():
    assert "globals(" not in _src()


def test_source_no_locals_batch54():
    assert "locals(" not in _src()


def test_source_no_os_system_batch54():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch54():
    assert "subprocess" not in _src()


def test_source_no_popen_batch54():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch54():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch54():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch54():
    assert "socket" not in _src()


def test_source_no_requests_batch54():
    assert "requests" not in _src()


def test_source_no_urllib_batch54():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch54():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch54():
    assert "yield" not in _src()


def test_source_no_async_await_batch54():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch54():
    assert "open(" not in _src()
