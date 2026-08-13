"""evaluation/annotation_metrics.py 第九十二轮 edges 测试（Round 656）。

补强 edges73 未触及的角度（第四十八批）。

新角度：
- chunk_boundary_prf anchor 多字段组合（marker+position 组合 / 多 anchor 不同 marker / 多 anchor 相同 marker 不同 position）
- chunk_boundary_prf 更深路径（chunks 长度恰好 2 / chunks 长度 10 / gt_positions 与 predicted 多对一 / stream 内 chunk 重复出现）
- chunk_boundary_prf _missing_markers 多 marker（2 个 missing / 1 missing 1 found）
- chunk_boundary_prf tolerance=0 完美匹配 / 完全不匹配
- chunk_boundary_prf stream 包含 normalize 后变化（多空格 / tab+newline）
- figure_caption_prf 不依赖任何输入字段
- 模块源码补强（_null 调用 / _ratio 调用 / 6 个 reason 字符串 / Counter 不在源码中使用）
- AST 结构补强
- forbidden tokens 第一百二十六批
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


# ---------- chunk_boundary_prf anchor 多字段组合 ----------

def test_chunk_boundary_multi_anchor_different_markers_batch48():
    """2 个 anchor 用不同 marker，分别在 chunk0 末尾和 chunk1 末尾。"""
    document = {
        "chunks": [
            {"text": "AAA marker1"},
            {"text": "marker2 BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "marker1", "position": "after"},
            {"marker": "marker2", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # marker1 after → gt_pos = 11（"AAA marker1" 长度）
    # marker2 before → gt_pos = 12（"AAA marker1 marker2 BBB"，marker2 起始位置）
    # predicted = [11]（chunk0 末尾）
    # marker1 after 的 gt=11，predicted=11，d=0
    # marker2 before 的 gt=12，predicted=11，d=1
    # tolerance=0 → 只有 (0, 0, 0) match
    # matched=1, num_pred=1, num_gt=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_same_marker_different_position_batch48():
    """同一 marker 不同 position：position before vs after 给出不同 gt_pos。"""
    document = {
        "chunks": [
            {"text": "AAA marker AAA"},
            {"text": "BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "before"},  # gt_pos = 0
            {"marker": "AAA", "position": "after"},  # gt_pos = 3
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 第一个 anchor marker="AAA" before → find("AAA", 0) = 0 → gt_pos = 0
    # search_from = 0 + 3 = 3
    # 第二个 anchor marker="AAA" after → find("AAA", 3) = 12（"AAA marker AAA" 中第二个 AAA 起始 = 12）
    # gt_pos = 12 + 3 = 15
    # stream = "AAA marker AAA BBB"
    # predicted = [15]（chunk0 末尾位置）
    # 第一个 gt=0, d=15；第二个 gt=15, d=0
    # tolerance=0 → 只 match (0, 0, 1)
    # matched=1, num_pred=1, num_gt=2 → P=1, R=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_anchor_extra_keys_ignored_batch48():
    """anchor 含额外 keys（如 id, label）不影响行为。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {
                "marker": "AAA",
                "position": "after",
                "id": "anchor-1",
                "label": "section break",
                "note": "extra",
            }
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf 更深路径 ----------

def test_chunk_boundary_exactly_two_chunks_batch48():
    """chunks 长度恰好 2：1 个预测边界。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_ten_chunks_batch48():
    """10 个 chunk：9 个预测边界。"""
    document = {"chunks": [{"text": f"chunk{i}"} for i in range(10)]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": f"chunk{i}", "position": "after"} for i in range(9)
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 9 个预测，9 个 anchor，完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_stream_with_extra_whitespace_batch48():
    """chunk 文本含 tab 和多空格，normalize 后 stream 是 "AAA BBB"。"""
    document = {
        "chunks": [
            {"text": "AAA\t"},  # tab 会被 normalize 成空格
            {"text": "  BBB"},  # 前导空格会被 normalize
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_gt_more_than_pred_batch48():
    """3 个 anchor 对应 1 个预测。第 3 个 anchor marker 在 search_from 之后找不到（顺序定位）。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},
            {"marker": "BBBB", "position": "before"},
            {"marker": "BBBB", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # predicted = [4]
    # anchor1: AAAA after → find("AAAA", 0)=0 → gt=4, search_from=4
    # anchor2: BBBB before → find("BBBB", 4)=5 → gt=5, search_from=9
    # anchor3: BBBB after → find("BBBB", 9)=-1 → missing_markers
    # gt_positions = [4, 5]，num_gt=2，num_pred=1
    # 一对一：predicted=4 与 gt=4 d=0, 与 gt=5 d=1
    # tolerance=10 → 都在容差内，按距离排序：先 match (0,0,0)
    # matched=1
    # P=1/1=1.0, R=1/2=0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert abs(out["chunk_boundary_recall"]["value"] - 0.5) < 1e-9
    # 第 3 个 marker 在 missing_markers
    assert "_missing_markers" in out
    assert "BBBB" in out["_missing_markers"]["value"]


# ---------- chunk_boundary_prf _missing_markers 多 marker ----------

def test_chunk_boundary_two_missing_markers_batch48():
    """2 个 marker 都不在 stream → 都记入 missing_markers。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "XXX", "position": "after"},
            {"marker": "YYY", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    assert set(out["_missing_markers"]["value"]) == {"XXX", "YYY"}


def test_chunk_boundary_one_missing_one_found_batch48():
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},  # 找到
            {"marker": "XXX", "position": "after"},  # 找不到
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["XXX"]


def test_chunk_boundary_missing_marker_position_after_batch48():
    """position=after 的 marker 找不到也计入 missing。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "XXX", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["XXX"]


# ---------- chunk_boundary_prf tolerance=0 完美匹配 / 完全不匹配 ----------

def test_chunk_boundary_tolerance_zero_perfect_match_batch48():
    document = {"chunks": [{"text": "AAAA"}, {"text": "BBBB"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # d=0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_tolerance_zero_complete_mismatch_batch48():
    """tolerance=0 + d=2 → 完全不匹配。"""
    document = {"chunks": [{"text": "AAAAAAAAAA"}, {"text": "BBBBBBBBBB"}]}
    # predicted = 10
    # marker "AAAA" after → gt = 4
    # d = 6
    annotation = {"chunk_boundary_anchors": [{"marker": "AAAA", "position": "after"}]}
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


# ---------- figure_caption_prf 不依赖任何输入字段 ----------

def test_figure_caption_prf_accepts_arbitrary_dict_batch48():
    out = figure_caption_prf({"any": "thing", "we": "want"}, {"also": "any"})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_does_not_read_document_keys_batch48():
    """函数体不读 document 任何 key。"""
    src = inspect.getsource(figure_caption_prf)
    body_start = src.find(":\n")
    body = src[body_start:]
    # body 中不应有 document[...] 或 document.
    assert "document[" not in body
    assert "document." not in body
    assert "annotation[" not in body
    assert "annotation." not in body


def test_figure_caption_prf_does_not_call_normalize_batch48():
    """figure_caption_prf 不调用 normalize_text（纯 null）。"""
    src = inspect.getsource(figure_caption_prf)
    assert "normalize_text" not in src


# ---------- 模块源码补强 ----------

def test_source_contains_null_call_batch48():
    """_null 在源码中被调用。"""
    src = inspect.getsource(am_mod)
    assert "_null(" in src


def test_source_contains_ratio_call_batch48():
    """_ratio 在源码中被调用。"""
    src = inspect.getsource(am_mod)
    assert "_ratio(" in src


def test_source_contains_pipeline_failed_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"pipeline_failed"' in src


def test_source_contains_no_annotation_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_annotation"' in src


def test_source_contains_no_predicted_boundaries_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_predicted_boundaries"' in src


def test_source_contains_no_ground_truth_anchors_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors"' in src


def test_source_contains_no_ground_truth_anchors_in_stream_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_source_contains_precision_or_recall_not_evaluated_string_batch48():
    src = inspect.getsource(am_mod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_source_no_counter_usage_batch48():
    """annotation_metrics 不直接用 Counter（import 了但没用）。"""
    src = inspect.getsource(am_mod)
    # 应当 import 但函数体不调用
    assert "from collections import Counter" in src
    # 不应有 Counter(...) 调用
    assert "Counter(" not in src


def test_source_contains_denom_calculation_batch48():
    """f1 计算：denom = p_val + r_val。"""
    src = inspect.getsource(am_mod)
    assert "p_val + r_val" in src


def test_source_contains_2_p_r_divide_denom_batch48():
    src = inspect.getsource(am_mod)
    assert "2 * p_val * r_val / denom" in src


def test_source_contains_pairs_sort_lambda_batch48():
    """pairs.sort 用 lambda。"""
    src = inspect.getsource(am_mod)
    assert "pairs.sort" in src


def test_source_contains_predicted_append_batch48():
    """predicted.append(end)。"""
    src = inspect.getsource(am_mod)
    assert "predicted.append" in src


def test_source_contains_gt_positions_append_batch48():
    src = inspect.getsource(am_mod)
    assert "gt_positions.append" in src


def test_source_contains_missing_markers_append_batch48():
    src = inspect.getsource(am_mod)
    assert "missing_markers.append" in src


def test_source_contains_used_pred_used_gt_batch48():
    src = inspect.getsource(am_mod)
    assert "used_pred" in src
    assert "used_gt" in src


def test_source_docstring_mentions_parser_does_not_emit_batch48():
    """docstring 解释 figure_caption_* 为何固定 null。"""
    src = inspect.getsource(am_mod)
    assert "parser" in src.lower()


# ---------- AST 结构补强 ----------

def test_ast_chunk_boundary_has_gt_positions_init_batch48():
    """gt_positions 初始化为 list。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "gt_positions: list[int]" in src or "gt_positions = []" in src


def test_ast_chunk_boundary_has_predicted_init_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "predicted: list[int]" in src or "predicted = []" in src


def test_ast_chunk_boundary_has_pairs_init_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "pairs: list[tuple" in src or "pairs = []" in src


def test_ast_chunk_boundary_has_multiple_assign_batch48():
    """chunk_boundary_prf 至少 5 个 Assign（out / norm_chunks / joined_raw / stream / predicted 等）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    assigns = [n for n in ast.walk(func) if isinstance(n, ast.Assign)]
    assert len(assigns) >= 5


def test_ast_chunk_boundary_has_aug_assign_pos_batch48():
    """pos += 是 AugAssign。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    aug_assigns = [n for n in ast.walk(func) if isinstance(n, ast.AugAssign)]
    assert len(aug_assigns) >= 2  # pos += 和 search_from =


def test_ast_chunk_boundary_search_from_assign_batch48():
    """search_from = find_pos + len(marker) 是 Assign。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "search_from = " in src


def test_ast_chunk_boundary_matched_increment_batch48():
    """matched += 1 是 AugAssign。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "matched += 1" in src


def test_ast_chunk_boundary_has_used_pred_used_gt_set_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_ast_no_class_def_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.ClassDef) for n in tree.body)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_top_level_assigns_count_batch48():
    """模块顶部 Assign：PARSER_DOES_NOT_EMIT_RELATIONS + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(am_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_top_level_imports_count_batch48():
    """模块顶部 import：__future__ / Counter / Any / normalize_text / _null,_ratio = 5。"""
    tree = ast.parse(inspect.getsource(am_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


# ---------- forbidden tokens 第一百二十六批 ----------

def _src() -> str:
    return inspect.getsource(am_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_locals_batch48():
    assert "locals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()
