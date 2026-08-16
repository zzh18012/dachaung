"""evaluation/annotation_metrics.py 第二百轮 edges 测试（Round 714）。

补强 edges81 未触及的角度（第七十九批）。

新角度：
- 多 chunk pred 位置（内部空格 chunk "AA AA"+"BB" → pred=[5]，before BB gt=6，d=1）
- 三 chunk 双 pred 单 anchor（mid anchor 命中 pred2 → P=0.5 R=1.0 f1=2/3）
- 重复 marker 两次出现都找到（search_from 推进 → 两 anchor 各自命中 → P=R=1.0）
- anchor 位置 0（before "A" 在 stream 首位 → gt=0，与 pred d=2）
- 空标注 dict 精确 4 键相等（默认容差 30）
- 源码补强（四个容器 AnnAssign / used 双集合 / pos 推进两式 / num_pred·num_gt / break 注释行 / for k 元组循环 ×2）
- AST 补强（chunk_boundary_prf 15 If / 7 For / 4 个 Tuple for-target / 5 个 AnnAssign 精确名单）
- forbidden tokens 第一百八十四批
"""

from __future__ import annotations

import ast
import inspect

import pytest

import evaluation.annotation_metrics as amod
from evaluation.annotation_metrics import chunk_boundary_prf


def _doc(*texts: str) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors: dict) -> dict:
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- 多 chunk pred 位置 ----------

def test_chunk_with_internal_space_pred_position_batch53():
    # norm ["AA AA", "BB"] → stream "AA AA BB"；pred=[5]；before "BB" → gt=6，d=1
    out = chunk_boundary_prf(_doc("AA AA", "BB"),
                             _ann({"marker": "BB", "position": "before"}),
                             tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_three_chunks_mid_anchor_batch53():
    # stream "A B C"；preds=[1,3]；after "B" → gt=3 → 命中 pred2
    out = chunk_boundary_prf(_doc("A", "B", "C"),
                             _ann({"marker": "B", "position": "after"}))
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- 重复 marker 两次出现 ----------

def test_duplicate_marker_both_found_batch53():
    # stream "XA XB XC"；两 anchor "X" after → gt=1 与 gt=4（search_from 推进）
    # preds=[2,5] → 各自 d=1 匹配
    out = chunk_boundary_prf(
        _doc("XA", "XB", "XC"),
        _ann({"marker": "X", "position": "after"},
             {"marker": "X", "position": "after"}),
        tolerance_chars=2,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert "_missing_markers" not in out


# ---------- anchor 位置 0 ----------

def test_anchor_at_stream_start_batch53():
    # stream "AB CD"；before "A" → gt=0；pred=[2]，d=2
    out = chunk_boundary_prf(_doc("AB", "CD"),
                             _ann({"marker": "A", "position": "before"}),
                             tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 空标注精确相等 ----------

def test_empty_annotation_exact_dict_batch53():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out == {
        "chunk_boundary_precision": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_recall": {"value": None, "reason": "no_annotation"},
        "chunk_boundary_f1": {"value": None, "reason": "no_annotation"},
        "_tolerance_chars": {"value": 30, "reason": None},
    }


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(amod)


def test_source_container_annotations_batch53():
    src = _src()
    assert "predicted: list[int] = []" in src
    assert "gt_positions: list[int] = []" in src
    assert "missing_markers: list[str] = []" in src
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_source_used_sets_batch53():
    src = _src()
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_source_pos_advances_batch53():
    src = _src()
    assert "pos = end + 1" in src
    assert "pos += len(txt) + 1" in src


def test_source_num_pred_gt_batch53():
    src = _src()
    assert "num_pred = len(predicted)" in src
    assert "num_gt = len(gt_positions)" in src


def test_source_for_k_tuple_loop_twice_batch53():
    assert _src().count(
        'for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):'
    ) == 2


def test_source_break_comment_line_batch53():
    assert "break  # 最后一个 chunk 后面不算边界" in _src()


def test_source_pval_rval_lines_batch53():
    src = _src()
    assert 'p_val = out["chunk_boundary_precision"]["value"]' in src
    assert 'r_val = out["chunk_boundary_recall"]["value"]' in src


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(amod))


def _func(name: str) -> ast.FunctionDef:
    return next(n for n in _tree().body
                if isinstance(n, ast.FunctionDef) and n.name == name)


def test_ast_chunk_boundary_if_for_counts_batch53():
    import collections
    c = collections.Counter(type(n).__name__ for n in ast.walk(_func("chunk_boundary_prf")))
    assert c["If"] == 15
    assert c["For"] == 7


def test_ast_tuple_for_targets_batch53():
    targets = [ast.unparse(n.target) for n in ast.walk(_func("chunk_boundary_prf"))
               if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)]
    assert targets == ["(i, txt)", "(pi, pv)", "(_, pi, gi)", "(gi, gv)"]


def test_ast_annassign_names_batch53():
    names = [ast.unparse(n) for n in ast.walk(_func("chunk_boundary_prf"))
             if isinstance(n, ast.AnnAssign)]
    assert names == [
        "out: dict[str, dict[str, Any]] = {}",
        "predicted: list[int] = []",
        "gt_positions: list[int] = []",
        "missing_markers: list[str] = []",
        "pairs: list[tuple[int, int, int]] = []",
    ]


# ---------- forbidden tokens 第一百八十四批 ----------

def test_source_no_eval_batch53():
    assert "eval(" not in _src()


def test_source_no_exec_batch53():
    assert "exec(" not in _src()


def test_source_no_compile_batch53():
    assert "compile(" not in _src()


def test_source_no_globals_batch53():
    assert "globals(" not in _src()


def test_source_no_locals_batch53():
    assert "locals(" not in _src()


def test_source_no_os_system_batch53():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch53():
    assert "subprocess" not in _src()


def test_source_no_popen_batch53():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch53():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch53():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch53():
    assert "socket" not in _src()


def test_source_no_requests_batch53():
    assert "requests" not in _src()


def test_source_no_urllib_batch53():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch53():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch53():
    assert "yield" not in _src()


def test_source_no_async_await_batch53():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch53():
    assert "open(" not in _src()
