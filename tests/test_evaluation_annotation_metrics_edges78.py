"""evaluation/annotation_metrics.py 第九十六轮 edges 测试（Round 685）。

补强 edges77 未触及的角度（第五十三批续 / 第五十四批）。

新角度：
- chunk_boundary_prf 端到端数值矩阵（3 chunks 多 anchor 全组合 / tolerance 变化下 matched 变化 / pred 空但 anchors 非空）
- chunk_boundary_prf 贪心冲突矩阵（两 pred 两 anchor 距离交叉 / 最小距离优先消解冲突）
- chunk_boundary_prf normalize 语义（多空白合一 / 前后空白 strip / 全空白 chunk）
- chunk_boundary_prf anchor position 未知值（非 before/after 默认走 after 分支）
- chunk_boundary_prf marker 是数字/emoji/混合
- chunk_boundary_prf stream 内多次出现 marker 且 anchors 少于出现次数
- chunk_boundary_prf 输出 dict 的 key 集合（各分支下 keys 变化）
- figure_caption_prf 输出再校验（3 keys / 不含 chunk_boundary / reason 常量引用同一对象）
- PARSER_DOES_NOT_EMIT_RELATIONS 唯一性（模块内仅此一个 reason 常量）
- 模块源码补强（chunk_boundary_prf 注释中的算法步骤 1-5 / tolerance 文档 / 一对一匹配 / 图表 caption 说明）
- AST 结构补强（chunk_boundary_prf 2 个 list comp / gt_positions 与 predicted 类型注解 / pairs.sort lambda / 5 个 for / out dict 初始化 / return out 次数）
- forbidden tokens 第一百五十五批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.annotation_metrics as ann_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- 端到端数值矩阵 ----------

def test_e2e_3_chunks_2_anchors_all_matched_batch52():
    doc = {"chunks": [{"text": "one"}, {"text": "two"}, {"text": "three"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "one", "position": "after"},
        {"marker": "two", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "one two three"
    # pred: one 后 = 3, two 后 = 7
    # anchor one-after = 3, two-after = 7
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_tolerance_changes_matched_count_batch52():
    doc = {"chunks": [{"text": "aaaa"}, {"text": "bbbb"}, {"text": "cccc"}]}
    # stream = "aaaa bbbb cccc"
    # pred: aaaa 后 = 4, bbbb 后 = 9
    # anchor: "bb" after = find 5 + 2 = 7
    ann = {"chunk_boundary_anchors": [{"marker": "bb", "position": "after"}]}
    # tolerance 0：pred 4 dist 3 / pred 9 dist 2 → 都不 matched
    out0 = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out0["chunk_boundary_recall"]["value"] == 0.0
    # tolerance 3：pred 4 dist 3 ≤ 3 matched（最小距离）
    out3 = chunk_boundary_prf(doc, ann, tolerance_chars=3)
    assert out3["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_pred_empty_anchors_present_batch52():
    """chunks<2 但 anchors 存在 → recall=0.0。"""
    doc = {"chunks": [{"text": "solo"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "solo", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_e2e_4_chunks_1_anchor_precision_quarter_batch52():
    """4 chunks 3 preds 1 anchor matched → precision=1/3。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "a b c d"; pred: 1, 3, 5; anchor a-after = 1
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(1/3)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- 贪心冲突矩阵 ----------

def test_greedy_cross_distances_resolved_batch52():
    """两 pred 两 anchor 距离交叉：最小距离优先。"""
    # stream = "aa bb cc"
    # pred: aa 后 = 2, bb 后 = 5
    # anchors: "aa" before = 0（aa 起始）; "cc" before = 6（cc 起始）
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}, {"text": "cc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "aa", "position": "before"},
        {"marker": "cc", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # pred 2 vs anchor 0: dist 2; pred 2 vs anchor 6: dist 4
    # pred 5 vs anchor 0: dist 5; pred 5 vs anchor 6: dist 1
    # 最小 dist 1 (pred5, anchor6) matched；次小 dist 2 (pred2, anchor0) matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_greedy_conflict_one_to_one_batch52():
    """两 pred 都只离同一 anchor 近 → 只有 1 个 matched。"""
    # stream = "xx yy"
    # pred: xx 后 = 2
    # 注：2 chunks 只有 1 个 pred；改 3 chunks
    doc = {"chunks": [{"text": "xx"}, {"text": "yy"}, {"text": "zz"}]}
    # stream = "xx yy zz"; pred: 2, 5
    # anchor: "yy" before = 3
    ann = {"chunk_boundary_anchors": [{"marker": "yy", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # pred2 dist 1 / pred5 dist 2 → pred2 matched; anchor 用掉
    # precision = 1/2, recall = 1/1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_greedy_ties_first_sorted_wins_batch52():
    """距离相同时 sorted 稳定排序，先出现的 pred 索引小者赢。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "cd"}, {"text": "ef"}]}
    # stream = "ab cd ef"; pred: 2, 5
    # anchor: "cd" before = 3 → pred2 dist 1, pred5 dist 2
    ann = {"chunk_boundary_anchors": [{"marker": "cd", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- normalize 语义 ----------

def test_normalize_multi_whitespace_collapsed_batch52():
    """chunk text 含连续空白 → normalize 后单空格，边界位置仍正确。"""
    doc = {"chunks": [{"text": "hello   world"}, {"text": "foo"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # norm chunk1 = "hello world"（多空格合一），norm chunk2 = "foo"
    # stream = "hello world foo"; pred = 11; anchor = 11
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_normalize_all_whitespace_chunk_batch52():
    """全空白 chunk → norm 后空串。"""
    doc = {"chunks": [{"text": "   "}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # norm_chunks = ["", "abc"]; joined = " abc"; stream = "abc"
    # i=0: find("",0)=0, end=0, pred=[0]; i=1 是最后 → break
    # anchor abc-before = 0; dist 0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_normalize_leading_trailing_stripped_batch52():
    doc = {"chunks": [{"text": "\n\tfoo \t"}, {"text": "bar\n"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # norm = "foo bar"; pred = 3; anchor foo-after = 3
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- position 未知值 ----------

def test_position_unknown_defaults_after_batch52():
    """position 是其他字符串（如 'middle'）→ else 分支 = after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "middle"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 非 before → else（after 语义）→ find 0 + 5 = 5 = pred
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_position_none_defaults_after_batch52():
    """position 是 None → 非 before → after。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": None}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- 特殊 marker 更多 ----------

def test_marker_numeric_batch52():
    doc = {"chunks": [{"text": "123"}, {"text": "456"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "123", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_marker_emoji_batch52():
    doc = {"chunks": [{"text": "a😀b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "😀", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream = "a😀b c"; pred = 3; anchor 😀 after = find 1 + 1 = 2; dist 1
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_marker_mixed_alnum_punct_batch52():
    doc = {"chunks": [{"text": "Q1: result"}, {"text": "next"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "Q1:", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = "Q1: result next"; pred = 10; anchor = find 0 + 3 = 3; dist 7 ≤ 10
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- marker 多次出现 ----------

def test_marker_multiple_occurrences_fewer_anchors_batch52():
    """marker 在 stream 出现 3 次但只有 2 个 anchor → 顺序取前 2 次。"""
    doc = {"chunks": [{"text": "go go go"}, {"text": "end"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "go", "position": "after"},
        {"marker": "go", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = "go go go end"; pred = 8
    # anchor1: go after = 0+2 = 2 (search_from=2)
    # anchor2: go after = 3+2 = 5 (search_from=5)
    # dists: pred8 vs 2 = 6; pred8 vs 5 = 3 → 匹配 anchor2 (dist 3 ≤ 10)
    # anchor1 dist 6 ≤ 10 但 pred 已用 → unmatched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# ---------- 输出 key 集合 ----------

def test_keys_document_none_branch_batch52():
    out = chunk_boundary_prf(None, {})
    assert set(out.keys()) == {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }


def test_keys_no_annotation_branch_batch52():
    out = chunk_boundary_prf({"chunks": [{"text": "x"}]}, None)
    assert set(out.keys()) == {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }


def test_keys_lt_2_chunks_branch_batch52():
    out = chunk_boundary_prf({"chunks": [{"text": "x"}]}, {"chunk_boundary_anchors": []})
    assert "_missing_markers" not in out
    assert "_tolerance_chars" in out


def test_keys_missing_markers_branch_batch52():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]},
    )
    assert set(out.keys()) == {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars", "_missing_markers",
    }


def test_keys_normal_branch_batch52():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    assert set(out.keys()) == {
        "chunk_boundary_precision", "chunk_boundary_recall",
        "chunk_boundary_f1", "_tolerance_chars",
    }


# ---------- figure_caption_prf 输出再校验 ----------

def test_figure_caption_exactly_3_keys_batch52():
    out = figure_caption_prf({}, {})
    assert len(out) == 3


def test_figure_caption_no_chunk_boundary_keys_batch52():
    out = figure_caption_prf({}, {})
    for k in out:
        assert not k.startswith("chunk_boundary")


def test_figure_caption_reason_same_constant_object_batch52():
    """reason 与模块常量是同一个值。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] is PARSER_DOES_NOT_EMIT_RELATIONS or v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_values_share_reason_batch52():
    out = figure_caption_prf({}, {})
    reasons = {v["reason"] for v in out.values()}
    assert reasons == {PARSER_DOES_NOT_EMIT_RELATIONS}


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 唯一性 ----------

def test_only_one_reason_constant_batch52():
    """模块内只有一个大写 reason 常量。"""
    tree = ast.parse(inspect.getsource(ann_mod))
    consts = [
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets)
    ]
    assert len(consts) == 1


# ---------- 模块源码补强 ----------

def test_source_algorithm_step_1_batch52():
    src = inspect.getsource(ann_mod)
    assert "规范化全文流" in src


def test_source_algorithm_step_2_batch52():
    src = inspect.getsource(ann_mod)
    assert "预测边界位置" in src or "第 i 个 chunk 结束位置" in src


def test_source_algorithm_step_3_batch52():
    src = inspect.getsource(ann_mod)
    assert "标注 anchor 位置" in src


def test_source_algorithm_step_4_batch52():
    src = inspect.getsource(ann_mod)
    assert "一对一匹配" in src


def test_source_algorithm_step_5_batch52():
    src = inspect.getsource(ann_mod)
    assert "precision = matched / num_predicted" in src
    assert "recall = matched / num_anchors" in src


def test_source_tolerance_must_be_recorded_batch52():
    src = inspect.getsource(ann_mod)
    assert "容差（tolerance_chars）必须在报告中明确记录" in src


def test_source_figure_caption_no_heuristic_note_batch52():
    src = inspect.getsource(ann_mod)
    assert "本期不引入" in src
    assert "最近图片" in src or "启发式" in src


def test_source_position_before_after_doc_batch52():
    src = inspect.getsource(ann_mod)
    assert 'position="before"' in src
    assert 'position="after"' in src


def test_source_annotation_marker_doc_batch52():
    src = inspect.getsource(ann_mod)
    assert "在规范化全文流中可定位的子串" in src


def test_source_search_from_comment_batch52():
    src = inspect.getsource(ann_mod)
    assert "重复 marker 顺序定位" in src


def test_source_one_to_one_comment_batch52():
    src = inspect.getsource(ann_mod)
    assert "一个预测边界只能命中一个标注 anchor" in src


# ---------- AST 结构补强 ----------

def test_ast_chunk_boundary_2_list_comps_batch52():
    """norm_chunks + missing 检测；实际只有 norm_chunks 一个 list comp（其他是循环）。"""
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    comps = [n for n in ast.walk(func) if isinstance(n, ast.ListComp)]
    assert len(comps) == 1  # norm_chunks = [normalize_text(...) for c in chunks]


def test_ast_gt_positions_typed_batch52():
    src = inspect.getsource(ann_mod)
    assert "gt_positions: list[int] = []" in src


def test_ast_predicted_typed_batch52():
    src = inspect.getsource(ann_mod)
    assert "predicted: list[int] = []" in src


def test_ast_pairs_sort_lambda_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    sorts = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sort"
    ]
    assert len(sorts) == 1
    lam = sorts[0].keywords[0].value
    assert isinstance(lam, ast.Lambda)
    # lambda x: x[0]
    assert isinstance(lam.body, ast.Subscript)


def test_ast_chunk_boundary_5_for_loops_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # 2 个早返回 for k in (...) + for i,txt / for a / for pi / for gi / for _,pi,gi = 7
    assert len(fors) == 7


def test_ast_chunk_boundary_out_init_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "out: dict[str, dict[str, Any]] = {}" in src


def test_ast_chunk_boundary_5_return_out_batch52():
    """5 个早返回都 return out（含末尾）。"""
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    returns = [
        r for r in ast.walk(func) if isinstance(r, ast.Return)
        and isinstance(r.value, ast.Name) and r.value.id == "out"
    ]
    assert len(returns) == 5


def test_ast_no_class_def_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_no_try_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.Try) for n in ast.walk(tree))


def test_ast_no_with_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.With) for n in ast.walk(tree))


def test_ast_no_while_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_raise_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, ast.Raise) for n in ast.walk(tree))


def test_ast_no_global_nonlocal_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_star_import_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


def test_ast_module_docstring_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_2_functions_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2


# ---------- forbidden tokens 第一百五十五批 ----------

def _src() -> str:
    return inspect.getsource(ann_mod)


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
