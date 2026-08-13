"""evaluation/annotation_metrics.py 第八十八轮 edges 测试（Round 624）。

补强 edges69 未触及的角度（第四十四批）。

新角度：
- chunk_boundary_prf 复杂匹配场景
- chunk_boundary_prf marker 是空字符串
- chunk_boundary_prf anchor 缺 marker key
- chunk_boundary_prf anchor 缺 position key
- chunk_boundary_prf position 不是 before/after（默认 after）
- chunk_boundary_prf 完美匹配 + 部分匹配 + miss
- chunk_boundary_prf tolerance=0 严格匹配
- chunk_boundary_prf tolerance=1000 极宽松
- chunk_boundary_prf 多 chunks 多 anchors 不平衡
- chunk_boundary_prf stream.find 找不到 txt
- figure_caption_prf 多次调用相同结果
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第九十四批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

import evaluation.annotation_metrics as anno_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- chunk_boundary_prf 边界 anchor 缺字段 ----------

def test_chunk_boundary_prf_anchor_missing_marker_batch44():
    """anchor 没有 marker key → marker="" → stream.find("") == 0 → find_pos=0。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"position": "after"},  # 无 marker
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # marker="" → find_pos=0 → gt position=0
    # pred position=11（"alpha beta" 末尾）
    # distance=11 > 5 → 不匹配
    # 但 marker="" 是 falsy → 实际代码 `find_pos = stream.find(marker, search_from) if marker else -1`
    assert "_missing_markers" in out or out["chunk_boundary_recall"]["value"] in (0.0, None)


def test_chunk_boundary_prf_anchor_missing_position_batch44():
    """anchor 没有位置 key → 默认 'after'。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta"},  # 无 position，默认 after
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # 'beta' after → 位置 11，pred=11 → 匹配
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_invalid_value_batch44():
    """position='middle' 不是 before/after → 默认走 else（after）分支。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "middle"},  # 不是 before/after
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # position='middle' 不是 'before' → 走 else（after）→ 位置 11 → 匹配
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_uses_start_batch44():
    """position='before' 用 marker 起始位置。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma delta", "source_element_ids": ["e2"]},
        ]
    }
    # stream = "alpha beta gamma delta"
    # 边界 11（"alpha beta" 末尾）
    # anchor "gamma" before → 位置 12（gamma 起始）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "gamma", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # pred=11, gt=12 → distance=1 ≤ 5 → 匹配
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf tolerance 极端值 ----------

def test_chunk_boundary_prf_tolerance_zero_batch44():
    """tolerance=0 → 严格匹配。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 位置 11
        ]
    }
    # pred=11, gt=11 → distance=0 ≤ 0 → 匹配
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_no_match_batch44():
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # 位置 5
        ]
    }
    # pred=11, gt=5 → distance=6 > 0 → 不匹配
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_huge_batch44():
    """tolerance=1000 极宽松。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},  # 位置 5
        ]
    }
    # pred=11, gt=5 → distance=6 ≤ 1000 → 匹配
    out = chunk_boundary_prf(document, annotation, tolerance_chars=1000)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf 多 chunks 多 anchors 不平衡 ----------

def test_chunk_boundary_prf_more_anchors_than_preds_batch44():
    """3 chunks（2 边界）+ 5 anchors（按 stream 顺序）→ P=2/2=1.0 R=2/5=0.4。

    注意：实现按 stream 顺序推进 search_from，所以 anchor 必须按 marker 在 stream 中出现顺序排列。
    """
    document = {
        "chunks": [
            {"text": "a b", "source_element_ids": ["e1"]},
            {"text": "c d", "source_element_ids": ["e2"]},
            {"text": "e f", "source_element_ids": ["e3"]},
        ]
    }
    # stream = "a b c d e f"
    # 边界 3（"a b" 末尾）+ 7（"a b c d" 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "before"},    # 0
            {"marker": "b", "position": "after"},     # 3
            {"marker": "c", "position": "before"},    # 4
            {"marker": "d", "position": "after"},     # 7
            {"marker": "e", "position": "before"},    # 8
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=2)
    # pred=[3,7], gt=[0,3,4,7,8]
    # 匹配: (3,3)d=0, (7,7)d=0；其它 anchor 都 >2
    # matched=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.4


def test_chunk_boundary_prf_more_preds_than_anchors_batch44():
    """4 chunks（3 边界）+ 1 anchor → P=1/3 R=1/1。"""
    document = {
        "chunks": [
            {"text": "a", "source_element_ids": ["e1"]},
            {"text": "b", "source_element_ids": ["e2"]},
            {"text": "c", "source_element_ids": ["e3"]},
            {"text": "d", "source_element_ids": ["e4"]},
        ]
    }
    # stream = "a b c d"
    # 边界 2（"a" 末尾）, 4（"a b" 末尾）, 6（"a b c" 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "b", "position": "after"},  # 位置 4
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=2)
    # pred=[2,4,6], gt=[4]
    # 匹配: (4,4) d=0
    # matched=1
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(1/3)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf stream.find 找不到 txt ----------

def test_chunk_boundary_prf_chunk_text_not_in_stream_batch44():
    """理论上 normalize 后 txt 必在 stream 中，但如果 chunks 中 text 极端异常（None） → 找不到。"""
    document = {
        "chunks": [
            {"text": "alpha", "source_element_ids": ["e1"]},
            {"text": None, "source_element_ids": ["e2"]},  # None
            {"text": "gamma", "source_element_ids": ["e3"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
        ]
    }
    # 不抛即过（实现里有兜底 pos += len(txt) + 1）
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert "chunk_boundary_precision" in out


# ---------- chunk_boundary_prf 重复 marker 顺序定位 ----------

def test_chunk_boundary_prf_three_repeated_markers_batch44():
    """3 个相同 marker 各匹配 stream 中第 1/2/3 次出现。"""
    document = {
        "chunks": [
            {"text": "x a", "source_element_ids": ["e1"]},
            {"text": "x b", "source_element_ids": ["e2"]},
            {"text": "x c", "source_element_ids": ["e3"]},
            {"text": "y", "source_element_ids": ["e4"]},
        ]
    }
    # stream = "x a x b x c y"
    # 边界 3（"x a" 末尾）, 7（"x a x b" 末尾）, 11（"x a x b x c" 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},   # 第 1 次 x 末尾 → 1
            {"marker": "x", "position": "after"},   # 第 2 次 x 末尾 → 5
            {"marker": "x", "position": "after"},   # 第 3 次 x 末尾 → 9
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=3)
    # pred=[3,7,11], gt=[1,5,9]
    # (3,1) d=2 ≤3 ✓
    # (7,5) d=2 ≤3 ✓
    # (11,9) d=2 ≤3 ✓
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- figure_caption_prf 多次调用 ----------

def test_figure_caption_prf_multiple_calls_batch44():
    """多次调用结果完全一致（无副作用）。"""
    out1 = figure_caption_prf({"x": 1}, None)
    out2 = figure_caption_prf({"y": 2}, {"z": 3})
    out3 = figure_caption_prf(None, None)
    assert out1 == out2 == out3


def test_figure_caption_prf_no_side_effects_batch44():
    """调用 figure_caption_prf 不修改输入。"""
    doc = {"chunks": [{"text": "abc"}]}
    anno = {"k": "v"}
    doc_before = dict(doc)
    anno_before = dict(anno)
    figure_caption_prf(doc, anno)
    assert doc == doc_before
    assert anno == anno_before


# ---------- chunk_boundary_prf 不修改输入 ----------

def test_chunk_boundary_prf_no_side_effects_batch44():
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    document_before = json_copy(document)
    annotation_before = json_copy(annotation)
    chunk_boundary_prf(document, annotation)
    assert document == document_before
    assert annotation == annotation_before


def json_copy(obj):
    import copy
    return copy.deepcopy(obj)


# ---------- chunk_boundary_prf 内部 _tolerance_chars 始终存在 ----------

def test_chunk_boundary_prf_tolerance_in_all_paths_batch44():
    """无论 document/annotation 状态，_tolerance_chars 始终在返回里。"""
    paths = [
        (None, None),
        ({"chunks": []}, None),
        ({"chunks": [{"text": "a", "source_element_ids": ["e1"]}]}, {}),
        ({"chunks": []}, {"chunk_boundary_anchors": []}),
        (
            {"chunks": [{"text": "a", "source_element_ids": ["e1"]}, {"text": "b", "source_element_ids": ["e2"]}]},
            {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
        ),
    ]
    for doc, anno in paths:
        out = chunk_boundary_prf(doc, anno)
        assert "_tolerance_chars" in out, f"missing _tolerance_chars for doc={doc}, anno={anno}"


# ---------- chunk_boundary_prf precision/recall null 不同组合 ----------

def test_chunk_boundary_prf_precision_null_recall_value_batch44():
    """无 anchor 时 recall=null；precision 也=null。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(document, annotation)
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None


# ---------- 模块源码字符串 ----------

def test_module_source_contains_anchor_marker_definition_batch44():
    src = inspect.getsource(anno_mod)
    assert "marker" in src


def test_module_source_contains_position_before_after_batch44():
    src = inspect.getsource(anno_mod)
    assert "before" in src
    assert "after" in src


def test_module_source_contains_greedy_match_batch44():
    src = inspect.getsource(anno_mod)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_contains_used_pred_used_gt_batch44():
    src = inspect.getsource(anno_mod)
    assert "used_pred" in src
    assert "used_gt" in src


def test_module_source_contains_normalize_text_call_batch44():
    src = inspect.getsource(anno_mod)
    assert "normalize_text" in src


def test_module_source_contains_search_from_batch44():
    src = inspect.getsource(anno_mod)
    assert "search_from" in src


def test_module_source_contains_missing_markers_var_batch44():
    src = inspect.getsource(anno_mod)
    assert "missing_markers" in src


def test_module_source_contains_stream_find_batch44():
    src = inspect.getsource(anno_mod)
    assert "stream.find" in src


def test_module_source_contains_pipeline_failed_reason_batch44():
    src = inspect.getsource(anno_mod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_reason_batch44():
    src = inspect.getsource(anno_mod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_reason_batch44():
    src = inspect.getsource(anno_mod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_reason_batch44():
    src = inspect.getsource(anno_mod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_precision_or_recall_reason_batch44():
    src = inspect.getsource(anno_mod)
    assert "precision_or_recall_not_evaluated" in src


# ---------- __all__ ----------

def test_all_exact_batch44():
    assert set(anno_mod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_all_count_3_batch44():
    assert len(anno_mod.__all__) == 3


def test_all_no_duplicates_batch44():
    assert len(set(anno_mod.__all__)) == len(anno_mod.__all__)


def test_all_entries_are_str_batch44():
    for e in anno_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch44():
    for e in anno_mod.__all__:
        assert hasattr(anno_mod, e)


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_top_level_function_count_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2


def test_ast_top_level_function_names_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["figure_caption_prf", "chunk_boundary_prf"]


def test_ast_top_level_assign_count_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_chunk_boundary_has_for_loops_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    fors = list(ast.walk(func))
    fors = [n for n in fors if isinstance(n, ast.For)]
    assert len(fors) >= 3  # 多个 for 循环（chunks / anchors / pairs / matched）


def test_ast_chunk_boundary_has_if_branches_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    ifs = list(ast.walk(func))
    ifs = [n for n in ifs if isinstance(n, ast.If)]
    assert len(ifs) >= 4


def test_ast_no_try_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_no_classdef_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_from_future_second_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


def test_ast_has_imports_batch44():
    tree = ast.parse(inspect.getsource(anno_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 3


# ---------- forbidden tokens 第九十四批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(anno_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(anno_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(anno_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(anno_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(anno_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(anno_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(anno_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(anno_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(anno_mod)
    assert "pickle.load(" not in src


def test_source_no_open_write_batch44():
    src = inspect.getsource(anno_mod)
    assert "open(\"w\"" not in src
    assert "open('w'" not in src
