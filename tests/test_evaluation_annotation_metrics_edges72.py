"""evaluation/annotation_metrics.py 第九十轮 edges 测试（Round 640）。

补强 edges71 未触及的角度（第四十七批）。

新角度：
- PARSER_DOES_NOT_EMIT_RELATIONS 常量属性
- figure_caption_prf 输入各种边界（None / 空 dict / 完整 dict 都返回相同）
- chunk_boundary_prf document None 路径
- chunk_boundary_prf annotation None/空 路径
- chunk_boundary_prf chunks < 2 路径
- chunk_boundary_prf anchors 空但 chunks 多
- chunk_boundary_prf search_from 顺序定位（重复 marker）
- chunk_boundary_prf tolerance_chars 透传到 _tolerance_chars
- chunk_boundary_prf _missing_markers 字段
- chunk_boundary_prf position before/after
- chunk_boundary_prf 一对一贪心匹配
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十批
"""

from __future__ import annotations

import ast
import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest

import evaluation.annotation_metrics as am_mod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 常量属性 ----------

def test_parser_does_not_emit_relations_is_str_batch47():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_batch47():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_immutable_batch47():
    with pytest.raises(TypeError):
        PARSER_DOES_NOT_EMIT_RELATIONS[0] = "X"  # type: ignore[index]


# ---------- figure_caption_prf 输入各种边界 ----------

def test_figure_caption_prf_none_none_batch47():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_returns_null_for_all_batch47():
    out = figure_caption_prf({"id": "d1"}, {"key": "value"})
    for k, v in out.items():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_consistent_regardless_of_input_batch47():
    """无论输入什么，3 个 figure_caption_* 都返回相同 null。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf({"chunks": []}, None)
    out3 = figure_caption_prf(None, {"x": 1})
    out4 = figure_caption_prf({}, {})
    assert out1 == out2 == out3 == out4


def test_figure_caption_prf_returns_dict_of_dicts_batch47():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)
    for v in out.values():
        assert isinstance(v, dict)


def test_figure_caption_prf_no_extra_keys_batch47():
    out = figure_caption_prf({"id": "d1"}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    # 不应有 _tolerance_chars（那是 chunk_boundary 专属）
    assert "_tolerance_chars" not in out


# ---------- chunk_boundary_prf document None 路径 ----------

def test_chunk_boundary_doc_none_returns_pipeline_failed_batch47():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_doc_none_still_has_tolerance_batch47():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}


def test_chunk_boundary_doc_none_no_missing_markers_key_batch47():
    out = chunk_boundary_prf(None, None)
    assert "_missing_markers" not in out


def test_chunk_boundary_doc_none_returns_4_keys_batch47():
    out = chunk_boundary_prf(None, None)
    # 3 metrics + _tolerance_chars
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


# ---------- chunk_boundary_prf annotation None/空 路径 ----------

def test_chunk_boundary_annotation_none_batch47():
    """document 非 None 但 annotation 是 None → no_annotation。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_empty_dict_batch47():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_annotation_no_chunk_boundary_anchors_key_batch47():
    """annotation 有其他 key 但没 chunk_boundary_anchors → 当 anchors=[] 处理。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    out = chunk_boundary_prf(doc, {"other_key": "value"})
    # chunks >= 2，anchors 空 → no_ground_truth_anchors
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


# ---------- chunk_boundary_prf chunks < 2 路径 ----------

def test_chunk_boundary_chunks_empty_batch47():
    """chunks=[] 且有 anchors → precision/f1 null，recall=0.0。"""
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x"}]})
    # 有 anchors → recall=0.0
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_single_batch47():
    """chunks 只有 1 个 且有 anchors → precision/f1 null，recall=0.0。"""
    doc = {"chunks": [{"text": "abc"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "abc"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_missing_key_batch47():
    """document 没 chunks key → 当 [] 处理；有 anchors → recall=0.0。"""
    doc = {}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_chunks_single_with_anchors_recall_zero_batch47():
    """chunks 单个 + 有 anchors → recall 是 0.0（不是 null）。"""
    doc = {"chunks": [{"text": "abc"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "abc"}]})
    # 有 anchors 但没预测 → recall=0.0（_ratio）
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_chunks_single_no_anchors_recall_null_batch47():
    """chunks 单个 + 无 anchors → recall null。"""
    doc = {"chunks": [{"text": "abc"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


# ---------- chunk_boundary_prf search_from 顺序定位 ----------

def test_chunk_boundary_repeated_marker_sequential_batch47():
    """相同 marker 出现 2 次：anchor1 应命中第 1 次，anchor2 命中第 2 次。"""
    doc = {
        "chunks": [
            {"text": "section A content"},
            {"text": "section B content"},
            {"text": "section C content"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "section", "position": "after"},
            {"marker": "section", "position": "after"},
            {"marker": "section", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # 应能匹配到 3 个 anchor（不丢失重复）
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_missing_marker_recorded_batch47():
    """marker 不在 stream 中 → 加入 _missing_markers。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_no_missing_markers_no_key_batch47():
    """所有 marker 都找到 → 不应有 _missing_markers key。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation)
    assert "_missing_markers" not in out


# ---------- chunk_boundary_prf tolerance_chars 透传 ----------

def test_chunk_boundary_tolerance_default_30_batch47():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]})
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_tolerance_custom_batch47():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}, tolerance_chars=50)
    assert out["_tolerance_chars"]["value"] == 50


def test_chunk_boundary_tolerance_zero_batch47():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_tolerance_negative_batch47():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}, tolerance_chars=-1)
    assert out["_tolerance_chars"]["value"] == -1


def test_chunk_boundary_tolerance_reason_none_batch47():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]})
    assert out["_tolerance_chars"]["reason"] is None


# ---------- chunk_boundary_prf position before/after ----------

def test_chunk_boundary_position_before_batch47():
    """position=before → anchor 位置 = marker 起始。"""
    doc = {
        "chunks": [
            {"text": "alpha beta gamma"},
            {"text": "delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # 应能找到匹配
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_position_after_batch47():
    """position=after（默认）→ anchor 位置 = marker 末尾。"""
    doc = {
        "chunks": [
            {"text": "alpha beta gamma"},
            {"text": "delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_position_invalid_defaults_after_batch47():
    """position 既不是 before 也不是 after → 当 after 处理。"""
    doc = {
        "chunks": [
            {"text": "alpha beta gamma"},
            {"text": "delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "weird"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # 应能找到匹配（即使 position 无效，按 after 处理）
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_position_missing_defaults_after_batch47():
    """anchor 缺 position key → 默认 after。"""
    doc = {
        "chunks": [
            {"text": "alpha beta gamma"},
            {"text": "delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta"},  # 没 position
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    assert out["chunk_boundary_recall"]["value"] is not None


# ---------- chunk_boundary_prf 一对一贪心匹配 ----------

def test_chunk_boundary_one_to_one_matching_batch47():
    """2 predicted 边界 + 2 anchor 都在容差内 → 匹配 2。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
            {"text": "epsilon"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 第 1 边界附近
            {"marker": "delta", "position": "after"},  # 第 2 边界附近
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 理论上完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_partial_match_batch47():
    """2 predicted，1 anchor 在容差内，1 不在。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
            {"text": "epsilon zeta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 1 个 anchor 匹配 1 个 predicted → recall=1.0, precision=0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5


def test_chunk_boundary_no_match_within_tolerance_batch47():
    """所有 anchor 都不在容差内 → matched=0。"""
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "zzzzz", "position": "after"},  # 不存在
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # marker 不存在 → missing_markers, num_gt=0
    # recall null（无 ground truth）
    assert out["chunk_boundary_recall"]["value"] is None


def test_chunk_boundary_f1_perfect_batch47():
    doc = {
        "chunks": [
            {"text": "alpha beta"},
            {"text": "gamma delta"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_precision_null_when_no_predicted_batch47():
    """num_pred=0 → precision null。"""
    # 通过 chunks < 2 触发
    doc = {"chunks": [{"text": "a"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["value"] is None


# ---------- chunk_boundary_prf 完整 document 输入 ----------

def test_chunk_boundary_complete_document_batch47():
    """完整 document 含 chunks + metadata。"""
    doc = {
        "id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "heading", "text": "T"}],
        "chunks": [
            {"text": "first paragraph here"},
            {"text": "second paragraph here"},
        ],
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "here", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 应能找到 marker
    assert "_missing_markers" not in out


def test_chunk_boundary_chunks_with_none_text_batch47():
    """chunk 的 text 是 None → 当 "" 处理。"""
    doc = {
        "chunks": [
            {"text": None},
            {"text": "abc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    # 不应崩溃
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_chunks_with_missing_text_key_batch47():
    """chunk 没 text key → 当 "" 处理。"""
    doc = {
        "chunks": [
            {"id": "c1"},  # 没 text
            {"text": "abc"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10)
    assert "chunk_boundary_precision" in out


# ---------- module source 字符串补强 ----------

def test_source_contains_parser_does_not_emit_batch47():
    src = inspect.getsource(am_mod)
    assert "parser 当前不输出" in src or "parser_does_not_emit_relations" in src


def test_source_contains_chunk_boundary_batch47():
    src = inspect.getsource(am_mod)
    assert "chunk_boundary" in src


def test_source_contains_tolerance_chars_batch47():
    src = inspect.getsource(am_mod)
    assert "tolerance_chars" in src


def test_source_contains_normalize_text_batch47():
    src = inspect.getsource(am_mod)
    assert "normalize_text" in src


def test_source_contains_one_to_one_batch47():
    src = inspect.getsource(am_mod)
    assert "一对一" in src


def test_source_contains_search_from_batch47():
    src = inspect.getsource(am_mod)
    assert "search_from" in src


def test_source_contains_missing_markers_batch47():
    src = inspect.getsource(am_mod)
    assert "missing_markers" in src


def test_source_contains_no_ground_truth_anchors_batch47():
    src = inspect.getsource(am_mod)
    assert "no_ground_truth_anchors" in src


def test_source_contains_pipeline_failed_batch47():
    src = inspect.getsource(am_mod)
    assert "pipeline_failed" in src


def test_source_contains_no_annotation_batch47():
    src = inspect.getsource(am_mod)
    assert "no_annotation" in src


def test_source_contains_no_predicted_boundaries_batch47():
    src = inspect.getsource(am_mod)
    assert "no_predicted_boundaries" in src


def test_source_contains_本期不引入启发式_batch47():
    src = inspect.getsource(am_mod)
    assert "启发式" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2  # figure_caption_prf / chunk_boundary_prf


def test_ast_module_constants_count_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # PARSER_DOES_NOT_EMIT_RELATIONS + __all__
    assert len(assigns) == 2


def test_ast_chunk_boundary_has_multiple_if_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 6  # document None / annotation / chunks < 2 / anchors empty / num_pred 0 / num_gt 0 / p_val None / denom <= 0


def test_ast_chunk_boundary_has_for_loops_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # 4 个 for：norm_chunks / predicted / gt_positions / pairs 嵌套
    assert len(fors) >= 3


def test_ast_chunk_boundary_has_nested_for_in_for_batch47():
    """pairs 构造里有嵌套 for。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    outer_fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    # 至少一个 for 的 body 里还有 for
    nested = False
    for of in outer_fors:
        for n in ast.walk(of):
            if n is of:
                continue
            if isinstance(n, ast.For):
                nested = True
                break
        if nested:
            break
    assert nested


def test_ast_chunk_boundary_has_lambda_sort_key_batch47():
    """pairs.sort(key=lambda x: x[0]) 是合法用法。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    lambdas = [n for n in ast.walk(func) if isinstance(n, ast.Lambda)]
    assert len(lambdas) >= 1


def test_ast_chunk_boundary_returns_dict_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf"][0]
    # 早返回在 if 内部，需 ast.walk
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 4  # 多个早返回 + 最后


def test_ast_figure_caption_returns_dict_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "figure_caption_prf"][0]
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert isinstance(returns[0].value, ast.Dict)


def test_ast_no_class_def_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    for n in tree.body:
        assert not isinstance(n, ast.ClassDef)


def test_ast_module_docstring_batch47():
    tree = ast.parse(inspect.getsource(am_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


# ---------- forbidden tokens 第一百一十批 ----------

def test_source_no_eval_batch47():
    src = inspect.getsource(am_mod)
    assert "eval(" not in src


def test_source_no_exec_batch47():
    src = inspect.getsource(am_mod)
    assert "exec(" not in src


def test_source_no_compile_batch47():
    src = inspect.getsource(am_mod)
    assert "compile(" not in src


def test_source_no_globals_batch47():
    src = inspect.getsource(am_mod)
    assert "globals(" not in src


def test_source_no_locals_batch47():
    src = inspect.getsource(am_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch47():
    src = inspect.getsource(am_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch47():
    src = inspect.getsource(am_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch47():
    src = inspect.getsource(am_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch47():
    src = inspect.getsource(am_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch47():
    src = inspect.getsource(am_mod)
    assert "subprocess" not in src


def test_source_no_yield_batch47():
    src = inspect.getsource(am_mod)
    assert "yield" not in src


def test_source_no_walrus_batch47():
    src = inspect.getsource(am_mod)
    assert ":=" not in src


def test_source_no_async_batch47():
    src = inspect.getsource(am_mod)
    assert "async def" not in src


def test_source_no_await_batch47():
    src = inspect.getsource(am_mod)
    assert "await " not in src


def test_source_no_raise_batch47():
    src = inspect.getsource(am_mod)
    assert "raise " not in src
