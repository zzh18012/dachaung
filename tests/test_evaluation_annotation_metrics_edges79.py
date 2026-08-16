"""evaluation/annotation_metrics.py 第九十七轮 edges 测试（Round 693）。

补强 edges78 未触及的角度（第五十九批）。

新角度：
- doc/annotation 形状边界（chunk 缺 text key / chunks 是 tuple / chunk_boundary_anchors=None → no_ground_truth / anchor 缺 marker 记空串进 missing / anchor 缺 position 默认 after / annotation falsy 变体 0-""-[]）
- chunks<2 分支细节（chunks=[] + anchors 空 → recall null / chunks=[] + anchors 非空 → recall 0.0）
- tolerance 边界（恰好等于距离 == 命中 / 负数 → 全 0 但 P/R 是 0.0 非 null / 0）
- f1 数值验证（P=1 R=0.5 → 2/3 / P=R=0.5 → 0.5 / P=R=0 → denom 0 → 0.0）
- search_from 推进语义（相同 marker before+after 两次出现 / 前缀 marker ab 与 abc 顺序定位）
- 全空 text chunks（stream="" → predicted 恰 1 个 0 位置）
- _missing_markers 多个按序记录
- figure_caption_prf 参数无关（truthy doc/annotation 同样 3 nulls）
- 源码补强（normalize_text 从 app.chunkers.structural import / _null+_ratio 从 evaluation.metrics / f1 公式 / denom <= 0 / chunks<2 条件 / search_from 推进 / used_pred used_gt）
- AST 补强（pairs.sort lambda / 2 个 set() 初始化 / predicted 循环 break 在最后 chunk / anchors for 内 marker 默认 "" / missing_markers append）
- forbidden tokens 第一百六十三批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any

import pytest

import evaluation.annotation_metrics as ann_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- doc/annotation 形状边界 ----------

def test_chunk_missing_text_key_batch52():
    """chunk 缺 text → or "" → norm 空；边界仍可推。"""
    doc = {"chunks": [{"no_text": 1}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # norm = ["", "abc"]; joined " abc" → stream "abc"
    # i=0: find("")=0 end=0 predicted=[0]; i=1 最后 break
    # anchor abc before = 0 → dist 0 matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunks_tuple_accepted_batch52():
    doc = {"chunks": ({"text": "a"}, {"text": "b"})}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchors_none_no_ground_truth_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


def test_anchor_missing_marker_records_empty_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == [""]
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_anchor_missing_position_defaults_after_batch52():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hello"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 缺 position → 默认 after → find 0 + 5 = 5 = pred
    assert out["chunk_boundary_precision"]["value"] == 1.0


@pytest.mark.parametrize("falsy", [0, "", [], False])
def test_annotation_falsy_variants_batch52(falsy):
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, falsy)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_annotation_empty_dict_no_annotation_batch52():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


# ---------- chunks<2 分支细节 ----------

def test_zero_chunks_empty_anchors_recall_null_batch52():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_zero_chunks_with_anchors_recall_zero_batch52():
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


# ---------- tolerance 边界 ----------

def test_tolerance_equals_distance_matched_batch52():
    # stream "aaaa bbbb"; pred 4; anchor bb after = 5+2 = 7; dist 3
    doc = {"chunks": [{"text": "aaaa"}, {"text": "bbbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "bb", "position": "after"}]}
    out_eq = chunk_boundary_prf(doc, ann, tolerance_chars=3)
    assert out_eq["chunk_boundary_recall"]["value"] == 1.0
    out_lt = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    assert out_lt["chunk_boundary_recall"]["value"] == 0.0


def test_tolerance_negative_all_zero_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # 无 pair → matched 0；num_pred/num_gt 均非 0 → P=R=0.0，f1 denom 0 → 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_tolerance_zero_exact_only_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- f1 数值验证 ----------

def _prf(doc, ann, tol):
    out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
    return (
        out["chunk_boundary_precision"]["value"],
        out["chunk_boundary_recall"]["value"],
        out["chunk_boundary_f1"]["value"],
    )


def test_f1_p1_r05_two_thirds_batch52():
    # 3 preds 1 anchor matched → P=1/3... 换构造：2 chunks 2 anchors 其中 1 matched
    # stream "xx yy zz"; pred: 2, 5; anchors: yy before=3 (matched by 2), zz before=6 (dist 1)
    doc = {"chunks": [{"text": "xx"}, {"text": "yy"}, {"text": "zz"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "yy", "position": "before"},
        {"marker": "zz", "position": "before"},
    ]}
    p, r, f = _prf(doc, ann, 1)
    # pred2 vs gt3 dist1 matched; pred5 vs gt6 dist1 matched → 全 matched
    assert (p, r) == (1.0, 1.0)
    assert f == 1.0


def test_f1_half_half_batch52():
    # stream "aa bb cc dd"; preds: 2,5,8; anchors: aa after=2, dd after=11
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}, {"text": "cc"}, {"text": "dd"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "aa", "position": "after"},
        {"marker": "dd", "position": "after"},
    ]}
    p, r, f = _prf(doc, ann, 3)
    # pred2 vs gt2 dist0 matched; pred5 vs 11 dist6 >3; pred8 vs 11 dist3 matched
    # P = 2/3, R = 2/2 = 1.0 → f1 = 2*(2/3)/(5/3) = 0.8
    assert p == pytest.approx(2 / 3)
    assert r == 1.0
    assert f == pytest.approx(0.8)


def test_f1_both_zero_is_zero_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aa", "position": "after"}]}
    p, r, f = _prf(doc, ann, -1)
    assert (p, r, f) == (0.0, 0.0, 0.0)


# ---------- search_from 推进语义 ----------

def test_same_marker_before_then_after_batch52():
    """两个相同 marker（before + after）→ 第二个从第一个末尾起搜 → 下一处出现。"""
    # stream "go x go y"
    doc = {"chunks": [{"text": "go x"}, {"text": "go y"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "go", "position": "after"},
        {"marker": "go", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # anchor1: go after = 0+2 = 2; search_from=2
    # anchor2: go before = find(go,2)=5 → 5
    # pred: go x 后 = 4
    # dist(4,2)=2 matched; dist(4,5)=1 matched → 一对一只能一个
    # 最小 dist 1 (pred4,gt5) matched；gt2 剩余无 pred → matched=1
    # P=1/1=1.0, R=1/2=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_prefix_markers_sequential_batch52():
    """marker "ab" 与 "abc"（前缀关系）→ search_from 推进后第二个找后续出现。"""
    # stream "ab abc"
    doc = {"chunks": [{"text": "ab"}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},
        {"marker": "abc", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # anchor1: ab after = 2; search_from = 2
    # anchor2: abc find from 2 → 3, after = 6
    # pred: ab 后 = 2
    # dist(2,2)=0 matched; gt6 无近 pred（dist 4 ≤10 但 pred 已用）
    # P=1.0 R=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


# ---------- 全空 text chunks ----------

def test_all_empty_text_chunks_batch52():
    doc = {"chunks": [{"text": ""}, {"text": ""}, {"text": ""}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # joined "  " → normalize "" → stream ""
    # i=0: find("")=0 end=0 predicted=[0] pos=1
    # i=1: find("",1) = -1 → 跳过
    assert out["chunk_boundary_precision"]["value"] == 0.0  # 1 pred 0 matched
    assert out["_missing_markers"]["value"] == ["x"]


# ---------- _missing_markers 多个按序 ----------

def test_missing_markers_multiple_in_order_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "zz", "position": "after"},
        {"marker": "aa", "position": "after"},
        {"marker": "qq", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == ["zz", "qq"]
    # aa 命中 → matched 1 → R = 1/1
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- figure_caption_prf 参数无关 ----------

def test_figure_caption_truthy_args_same_nulls_batch52():
    out = figure_caption_prf({"chunks": [{"text": "x"}]}, {"figure_caption_pairs": [{}]})
    assert set(out.keys()) == {
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    }
    assert all(v["value"] is None for v in out.values())
    assert all(v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS for v in out.values())


# ---------- 源码补强 ----------

def test_source_normalize_text_import_batch52():
    src = inspect.getsource(ann_mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_source_null_ratio_import_batch52():
    src = inspect.getsource(ann_mod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_source_f1_formula_batch52():
    src = inspect.getsource(ann_mod)
    assert "2 * p_val * r_val / denom" in src


def test_source_denom_le_zero_batch52():
    src = inspect.getsource(ann_mod)
    assert "if denom <= 0:" in src


def test_source_chunks_lt_2_condition_batch52():
    src = inspect.getsource(ann_mod)
    assert "if not chunks or len(chunks) < 2:" in src


def test_source_search_from_advance_batch52():
    src = inspect.getsource(ann_mod)
    assert "search_from = find_pos + len(marker)" in src


def test_source_used_sets_batch52():
    src = inspect.getsource(ann_mod)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_source_no_heuristic_promise_batch52():
    src = inspect.getsource(ann_mod)
    assert "本期不引入" in src


# ---------- AST 补强 ----------

def test_ast_pairs_sort_lambda_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    sorts = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "sort"
    ]
    assert len(sorts) == 1
    assert sorts[0].keywords[0].arg == "key"


def test_ast_predicted_loop_break_last_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    breaks = [n for n in ast.walk(func) if isinstance(n, ast.Break)]
    assert len(breaks) == 1  # 最后一个 chunk 不算边界


def test_ast_anchor_marker_default_empty_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "a.get('marker', '')" in src
    assert "a.get('position', 'after')" in src


def test_ast_missing_markers_append_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "missing_markers.append(marker)" in src


def test_ast_early_returns_have_4_keys_max_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    early = [
        n for n in func.body
        if isinstance(n, ast.If) and isinstance(n.body[-1], ast.Return)
    ]
    # document None / no annotation / chunks<2 / no anchors = 4 个早返回 If
    assert len(early) == 4


def test_ast_tolerance_kwarg_only_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    assert len(func.args.args) == 3  # document / annotation / tolerance_chars
    assert len(func.args.defaults) == 1
    assert func.args.defaults[0].value == 30


# ---------- forbidden tokens 第一百六十三批 ----------

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
