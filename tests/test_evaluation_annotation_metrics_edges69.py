"""evaluation/annotation_metrics.py 第八十轮 edges 测试（Round 616）。

补强 edges68 未触及的角度（第四十三批）。

新角度：
- PARSER_DOES_NOT_EMIT_RELATIONS 常量
- figure_caption_prf 签名 / 返回 dict 结构 / reason 全部相同
- figure_caption_prf 不读 document（即使 document=None 也返回相同 reason）
- chunk_boundary_prf 签名 / keyword-only tolerance_chars
- chunk_boundary_prf pipeline_failed 路径
- chunk_boundary_prf no_annotation 路径（None / 空 dict / 0 / {}）
- chunk_boundary_prf no_predicted_boundaries 路径（< 2 chunks）
- chunk_boundary_prf no_ground_truth_anchors 路径
- chunk_boundary_prf 一对一匹配（贪心 + used_pred/used_gt）
- chunk_boundary_prf 容差 tolerance_chars 实际生效
- chunk_boundary_prf 重复 marker 顺序定位
- chunk_boundary_prf missing_markers 在报告里
- chunk_boundary_prf position="before" / "after" 区别
- chunk_boundary_prf f1 计算（p/r null / denom=0 / 正常）
- chunk_boundary_prf _tolerance_chars 始终在
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第八十六批
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


# ---------- 常量 ----------

def test_parser_does_not_emit_relations_value_batch43():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_batch43():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_all_batch43():
    """__all__ 里是 identifier 名 "PARSER_DOES_NOT_EMIT_RELATIONS"，不是它的字符串值。"""
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in anno_mod.__all__
    assert PARSER_DOES_NOT_EMIT_RELATIONS not in anno_mod.__all__


def test_parser_does_not_emit_relations_is_module_attr_batch43():
    assert anno_mod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- figure_caption_prf 签名 ----------

def test_figure_caption_prf_signature_batch43():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_figure_caption_prf_param_kinds_batch43():
    sig = inspect.signature(figure_caption_prf)
    for name in ["document", "annotation"]:
        assert sig.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_no_defaults_batch43():
    sig = inspect.signature(figure_caption_prf)
    for name in ["document", "annotation"]:
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_figure_caption_prf_return_annotation_batch43():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- figure_caption_prf 行为 ----------

def test_figure_caption_prf_returns_3_keys_batch43():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_reason_all_same_batch43():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_value_all_none_batch43():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_ignores_document_batch43():
    """document 即使非 None 也不读。"""
    doc = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = figure_caption_prf(doc, {"chunk_boundary_anchors": []})
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_read_annotation_batch43():
    """annotation 也忽略。"""
    out = figure_caption_prf({"x": 1}, {"y": 2})
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_prf_idempotent_batch43():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_no_internal_markers_batch43():
    out = figure_caption_prf(None, None)
    assert "_tolerance_chars" not in out
    assert "_missing_markers" not in out


# ---------- chunk_boundary_prf 签名 ----------

def test_chunk_boundary_prf_signature_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_param_kinds_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["annotation"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert sig.parameters["tolerance_chars"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_default_tolerance_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_return_annotation_batch43():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


# ---------- chunk_boundary_prf 路径：pipeline_failed ----------

def test_chunk_boundary_prf_document_none_batch43():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_with_tolerance_batch43():
    out = chunk_boundary_prf(None, None, tolerance_chars=50)
    assert out["_tolerance_chars"]["value"] == 50


# ---------- chunk_boundary_prf 路径：no_annotation ----------

def test_chunk_boundary_prf_annotation_none_batch43():
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = chunk_boundary_prf(document, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch43():
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = chunk_boundary_prf(document, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_zero_batch43():
    """0 是 falsy → no_annotation。"""
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = chunk_boundary_prf(document, 0)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


# ---------- chunk_boundary_prf 路径：no_predicted_boundaries ----------

def test_chunk_boundary_prf_no_chunks_batch43():
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall 在 anchors 存在时返回 0.0（不是 null）
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_one_chunk_no_anchors_batch43():
    """1 chunk + 0 anchors → no_predicted_boundaries（recall 也是 null）。"""
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(document, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_batch43():
    """1 chunk + anchors → recall=0.0（不是 null，因为有 ground truth）。"""
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_two_chunks_no_anchors_batch43():
    document = {
        "chunks": [
            {"text": "abc", "source_element_ids": ["e1"]},
            {"text": "def", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(document, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


# ---------- chunk_boundary_prf 一对一匹配 ----------

def test_chunk_boundary_prf_one_match_batch43():
    """2 chunks, 1 anchor in stream at correct position → precision=1.0 recall=1.0。"""
    document = {
        "chunks": [
            {"text": "hello world", "source_element_ids": ["e1"]},
            {"text": "foo bar", "source_element_ids": ["e2"]},
        ]
    }
    # normalize 后 stream = "hello world foo bar"
    # 边界 11（"hello world" 末尾）+ 容差 5
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},  # 位置 11
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_outside_tolerance_batch43():
    """anchor 不在任何预测边界 tolerance 内 → 0 匹配。"""
    document = {
        "chunks": [
            {"text": "hello world foo bar", "source_element_ids": ["e1"]},
            {"text": "baz", "source_element_ids": ["e2"]},
        ]
    }
    # 边界 = 19（"hello world foo bar" 末尾）
    # anchor = "world" 之后 = 11；distance = 8
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},  # 位置 11
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_50_batch43():
    """tolerance=50 时允许更大距离。"""
    document = {
        "chunks": [
            {"text": "hello world foo bar", "source_element_ids": ["e1"]},
            {"text": "baz", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},  # 位置 11
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=50)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_two_chunks_two_anchors_batch43():
    """3 chunks, 2 anchors → 2 matches。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma delta", "source_element_ids": ["e2"]},
            {"text": "epsilon", "source_element_ids": ["e3"]},
        ]
    }
    # stream = "alpha beta gamma delta epsilon"
    # 边界 11（"alpha beta" 末尾）+ 23（"alpha beta gamma delta" 末尾）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},   # 位置 11
            {"marker": "delta", "position": "after"},  # 位置 23
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_to_one_greedy_batch43():
    """2 predictions, 1 anchor → only 1 match (greedy)."""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
            {"text": "delta", "source_element_ids": ["e3"]},
        ]
    }
    # 2 predicted boundaries (after chunk 1 and chunk 2)
    # 1 anchor
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},  # 位置 11
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert out["chunk_boundary_recall"]["value"] == 1.0    # 1/1


def test_chunk_boundary_prf_position_before_batch43():
    """position="before" → marker 起始位置。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    # stream = "alpha beta gamma"
    # 边界 = 11（"alpha beta" 末尾）
    # anchor = "gamma" before → 位置 11（恰好匹配）
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "gamma", "position": "before"},  # 位置 11
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf missing_markers ----------

def test_chunk_boundary_prf_missing_markers_batch43():
    """marker 在 stream 中找不到 → 加入 missing_markers。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_key_when_all_found_batch43():
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
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert "_missing_markers" not in out


# ---------- chunk_boundary_prf _tolerance_chars 始终在 ----------

def test_chunk_boundary_prf_pipeline_failed_has_tolerance_batch43():
    out = chunk_boundary_prf(None, None)
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_no_annotation_has_tolerance_batch43():
    document = {"chunks": [{"text": "abc", "source_element_ids": ["e1"]}]}
    out = chunk_boundary_prf(document, None)
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_no_pred_has_tolerance_batch43():
    document = {"chunks": []}
    annotation = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(document, annotation)
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_default_tolerance_30_batch43():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


# ---------- chunk_boundary_prf 重复 marker 顺序定位 ----------

def test_chunk_boundary_prf_repeated_marker_sequential_batch43():
    """2 个相同 marker 各自匹配 stream 中的第 1 / 第 2 次出现。"""
    document = {
        "chunks": [
            {"text": "abc def", "source_element_ids": ["e1"]},
            {"text": "abc ghi", "source_element_ids": ["e2"]},
            {"text": "jkl", "source_element_ids": ["e3"]},
        ]
    }
    # stream = "abc def abc ghi jkl"
    # 边界 7 (after "abc def") + 15 (after "abc ghi")
    # anchor 1 = "abc" after → 位置 3
    # anchor 2 = "abc" after → 位置 11
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"},
            {"marker": "abc", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # anchor1 距 boundary1 = 7-3 = 4 ≤ 5 ✓
    # anchor2 距 boundary2 = 15-11 = 4 ≤ 5 ✓
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf f1 计算 ----------

def test_chunk_boundary_prf_f1_zero_when_both_zero_batch43():
    document = {
        "chunks": [
            {"text": "hello world foo bar", "source_element_ids": ["e1"]},
            {"text": "baz", "source_element_ids": ["e2"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "world", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # f1 = 2*0*0/(0+0) → denom=0 → 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_half_when_precision_half_batch43():
    """2 predictions, 1 match → P=0.5, R=1.0 → F1 = 2*0.5*1/1.5 = 0.667。"""
    document = {
        "chunks": [
            {"text": "alpha beta", "source_element_ids": ["e1"]},
            {"text": "gamma", "source_element_ids": ["e2"]},
            {"text": "delta", "source_element_ids": ["e3"]},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    f1 = out["chunk_boundary_f1"]["value"]
    assert f1 is not None
    assert abs(f1 - (2 * 0.5 * 1.0 / 1.5)) < 1e-6


# ---------- 模块源码字符串 ----------

def test_module_source_contains_parser_does_not_batch43():
    src = inspect.getsource(anno_mod)
    assert "parser_does_not_emit_relations" in src


def test_module_source_contains_normalize_text_batch43():
    src = inspect.getsource(anno_mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_batch43():
    src = inspect.getsource(anno_mod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_greedy_batch43():
    src = inspect.getsource(anno_mod)
    assert "贪心" in src or "greedy" in src.lower()


def test_module_source_contains_tolerance_batch43():
    src = inspect.getsource(anno_mod)
    assert "tolerance_chars" in src


def test_module_source_contains_no_predicted_boundaries_batch43():
    src = inspect.getsource(anno_mod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_batch43():
    src = inspect.getsource(anno_mod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_pipeline_failed_batch43():
    src = inspect.getsource(anno_mod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_batch43():
    src = inspect.getsource(anno_mod)
    assert "no_annotation" in src


def test_module_source_contains_missing_markers_batch43():
    src = inspect.getsource(anno_mod)
    assert "missing_markers" in src


# ---------- __all__ ----------

def test_all_exact_batch43():
    assert set(anno_mod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_all_count_3_batch43():
    assert len(anno_mod.__all__) == 3


def test_all_entries_are_str_batch43():
    for e in anno_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch43():
    for e in anno_mod.__all__:
        assert hasattr(anno_mod, e)


# ---------- AST 结构 ----------

def test_ast_top_level_no_class_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert classes == []


def test_ast_top_level_function_count_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2


def test_ast_top_level_function_names_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["figure_caption_prf", "chunk_boundary_prf"]


def test_ast_top_level_assign_count_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    # PARSER_DOES_NOT_EMIT_RELATIONS, __all__
    assert len(assigns) == 2


def test_ast_no_try_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_has_imports_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 3


def test_ast_from_future_first_batch43():
    tree = ast.parse(inspect.getsource(anno_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第八十六批 ----------

def test_source_no_eval_batch43():
    src = inspect.getsource(anno_mod)
    assert "eval(" not in src


def test_source_no_exec_batch43():
    src = inspect.getsource(anno_mod)
    assert "exec(" not in src


def test_source_no_compile_batch43():
    src = inspect.getsource(anno_mod)
    assert "compile(" not in src


def test_source_no_globals_batch43():
    src = inspect.getsource(anno_mod)
    assert "globals(" not in src


def test_source_no_locals_batch43():
    src = inspect.getsource(anno_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch43():
    src = inspect.getsource(anno_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch43():
    src = inspect.getsource(anno_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch43():
    src = inspect.getsource(anno_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch43():
    src = inspect.getsource(anno_mod)
    assert "pickle.load(" not in src


def test_source_no_open_batch43():
    src = inspect.getsource(anno_mod)
    assert "open(" not in src
