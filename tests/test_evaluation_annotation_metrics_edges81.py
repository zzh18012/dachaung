"""evaluation/annotation_metrics.py 第九十九轮 edges 测试（Round 707）。

补强 edges80 未触及的角度（第七十二批）。

新角度：
- position before/after 的位置数学（before=marker 起点 / after=marker 终点，容差 1 下 before 命中 after 不命中）
- tolerance 边界（d == tolerance 命中 / d == tolerance+1 不命中 / 负 tolerance 全不中 → P=R=f1=0.0）
- 一 pred 两 gt（贪心取 d=0 → P=1.0 R=0.5 f1=2/3）
- chunk 缺 text 键 → or "" 分支（空 chunk 仍产生 pred 位置 0）
- 全空 stream + marker 找不到 → precision 0.0 / recall null no_ground_truth_anchors_in_stream / f1 null / _missing_markers
- _missing_markers 键只在有缺失时出现（无缺失 → 键不存在 / 部分缺失 → 值精确）
- figure_caption_prf 任意非 None 参数与 None/None 输出全等
- 源码补强（predicted.append / missing_markers.append / pairs.append / d <= tolerance / matched += 1 / used 集合 / search_from 推进式 / denom 分支 / marker·position 默认值）
- AST 补强（Lambda 1 / IfExp 2 / Break 1 / Continue 3 / append 5 处多重集 / abs 1 / search_from 2 赋值）
- forbidden tokens 第一百七十七批
"""

from __future__ import annotations

import ast
import inspect

import pytest

import evaluation.annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


def _doc(*texts: str) -> dict:
    return {"chunks": [{"text": t} for t in texts]}


def _ann(*anchors: dict) -> dict:
    return {"chunk_boundary_anchors": list(anchors)}


# ---------- position before/after 数学 ----------

def test_before_position_is_marker_start_batch52():
    # stream "AAAA BBBB"；pred=[4]；before "BBBB" → gt=5，d=1
    out = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                             _ann({"marker": "BBBB", "position": "before"}),
                             tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_after_position_is_marker_end_batch52():
    # after "BBBB" → gt=9，d=5，容差 1 下不命中
    out = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                             _ann({"marker": "BBBB", "position": "after"}),
                             tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- tolerance 边界 ----------

def test_tolerance_exact_distance_matches_batch52():
    # stream "AAAA BBBB"；pred=[4]；after "BBBB" → gt=9，d=5 == tolerance → 命中
    out = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                             _ann({"marker": "BBBB", "position": "after"}),
                             tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_tolerance_one_less_fails_batch52():
    out = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                             _ann({"marker": "BBBB", "position": "after"}),
                             tolerance_chars=4)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0  # p=r=0 → denom<=0 → 0.0


def test_negative_tolerance_matches_nothing_batch52():
    out = chunk_boundary_prf(_doc("AAAA", "BBBB"),
                             _ann({"marker": "BBBB", "position": "before"}),
                             tolerance_chars=-1)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


# ---------- 一 pred 两 gt ----------

def test_one_pred_two_gts_greedy_nearest_batch52():
    # stream "AAA BBB"；pred=[3]；gt: after AAA=3（d=0）、before BBB=4（d=1）
    out = chunk_boundary_prf(
        _doc("AAA", "BBB"),
        _ann({"marker": "AAA", "position": "after"},
             {"marker": "BBB", "position": "before"}),
        tolerance_chars=5,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


# ---------- chunk 缺 text / 全空 stream ----------

def test_chunk_missing_text_treated_empty_batch52():
    doc = {"chunks": [{"no_text": 1}, {"text": "AB"}]}
    out = chunk_boundary_prf(doc, _ann({"marker": "AB", "position": "after"}),
                             tolerance_chars=5)
    # norm ["", "AB"] → stream "AB"；pred=[0]（空 chunk 在 0 结束）；gt=2，d=2 ≤ 5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_empty_stream_marker_missing_full_matrix_batch52():
    doc = {"chunks": [{}, {}]}
    out = chunk_boundary_prf(doc, _ann({"marker": "X", "position": "after"}),
                             tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"
    assert out["_missing_markers"] == {"value": ["X"], "reason": None}


# ---------- _missing_markers 键出现条件 ----------

def test_missing_markers_key_absent_when_all_found_batch52():
    out = chunk_boundary_prf(_doc("AAA", "BBB"),
                             _ann({"marker": "AAA", "position": "after"}))
    assert "_missing_markers" not in out


def test_missing_markers_partial_value_exact_batch52():
    out = chunk_boundary_prf(
        _doc("AAA", "BBB"),
        _ann({"marker": "AAA", "position": "after"},
             {"marker": "ZZZ", "position": "after"}),
    )
    assert out["_missing_markers"] == {"value": ["ZZZ"], "reason": None}
    assert out["chunk_boundary_recall"]["value"] == 1.0  # num_gt 只含找到的 1 个


# ---------- figure_caption_prf 参数无关 ----------

def test_figure_caption_junk_args_same_as_none_batch52():
    a = figure_caption_prf({"chunks": [{"text": "x"}]}, {"figure_caption_pairs": [{}]})
    b = figure_caption_prf(None, None)
    assert a == b
    assert a["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(amod)


def test_source_appends_batch52():
    src = _src()
    assert "predicted.append(end)" in src
    assert "missing_markers.append(marker)" in src
    assert "gt_positions.append(find_pos)" in src
    assert "gt_positions.append(find_pos + len(marker))" in src
    assert "pairs.append((d, pi, gi))" in src


def test_source_matching_lines_batch52():
    src = _src()
    assert "if d <= tolerance_chars:" in src
    assert "matched += 1" in src
    assert "used_pred.add(pi)" in src
    assert "used_gt.add(gi)" in src


def test_source_search_from_advance_expr_batch52():
    assert "search_from = find_pos + len(marker)" in _src()


def test_source_marker_position_defaults_batch52():
    src = _src()
    assert 'marker = a.get("marker", "")' in src
    assert 'position = a.get("position", "after")' in _src()


def test_source_f1_denom_branch_batch52():
    src = _src()
    assert "denom = p_val + r_val" in src
    assert "if denom <= 0:" in src
    assert "2 * p_val * r_val / denom" in src


def test_source_missing_markers_out_batch52():
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(amod))


def test_ast_lambda_ifexp_break_continue_counts_batch52():
    tree = _tree()
    kinds = {}
    for n in ast.walk(tree):
        kinds[type(n).__name__] = kinds.get(type(n).__name__, 0) + 1
    assert kinds["Lambda"] == 1
    assert kinds["IfExp"] == 2
    assert kinds["Break"] == 1
    assert kinds["Continue"] == 3


def test_ast_append_multiset_batch52():
    tree = _tree()
    appends = sorted(
        ast.unparse(n.func.value) for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "append"
    )
    assert appends == ["gt_positions", "gt_positions", "missing_markers",
                       "pairs", "predicted"]


def test_ast_single_abs_call_batch52():
    tree = _tree()
    abses = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "abs"]
    assert len(abses) == 1


def test_ast_search_from_two_assigns_batch52():
    tree = _tree()
    exprs = [ast.unparse(n) for n in ast.walk(tree)
             if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id == "search_from"]
    assert exprs == ["search_from = 0", "search_from = find_pos + len(marker)"]


# ---------- forbidden tokens 第一百七十七批 ----------

def test_source_no_eval_batch52():
    assert "eval(" not in _src()


def test_source_no_exec_batch52():
    assert "exec(" not in _src()


def test_source_no_compile_batch52():
    assert "compile(" not in _src()


def test_source_no_globals_batch52():
    assert "globals(" not in _src()


def test_source_no_locals_batch52():
    assert "locals(" not in _src()


def test_source_no_os_system_batch52():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch52():
    assert "subprocess" not in _src()


def test_source_no_popen_batch52():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch52():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch52():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch52():
    assert "socket" not in _src()


def test_source_no_requests_batch52():
    assert "requests" not in _src()


def test_source_no_urllib_batch52():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch52():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch52():
    assert "yield" not in _src()


def test_source_no_async_await_batch52():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_zero_batch52():
    assert "open(" not in _src()
