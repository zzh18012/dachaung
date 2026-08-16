"""evaluation/annotation_metrics.py 第九十八轮 edges 测试（Round 700）。

补强 edges79 未触及的角度（第六十五批）。

新角度：
- _tolerance_chars 五条返回路径全部携带（document None / no annotation / chunks<2 / no anchors / 正常路径）
- _missing_markers 缺失键语义（无缺失时不出现 / 缺 marker 先于命中不阻塞后续 / 超出出现次数的重复 marker 第二次记 missing）
- 贪心匹配细节（两 pred 争一 gt 只中一个（距离排序）/ 等距 tie 按 pred 顺序取第一个）
- normalize_text 生效（chunk 内多空格收敛 / 未规范化的 marker 找不到进 missing / 大小写敏感）
- annotation 缺 chunk_boundary_anchors 键 → no_ground_truth_anchors
- document 缺 chunks 键 → no_predicted_boundaries
- marker 显式空串 → missing [""]；figure_caption_prf None/None 同 3 nulls
- 常量（PARSER_DOES_NOT_EMIT_RELATIONS 值 / __all__ 3 项）
- 源码补强（两个守卫 / 两个 or [] / chunks<2 条件 / norm 列表推导 / joined_raw 空格连接 / stream 二次规范化 / break 注释 / pairs.sort / search_from 推进 / 空_marker 短路 / f1 not_evaluated reason / missing 条件 / _tolerance_chars 出现 5 次 / Counter import）
- AST 补强（5 个 Return / 7 个 For / figure_caption_prf 单 Return 3 键 / __all__ 精确）
- forbidden tokens 第一百七十批
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


# ---------- _tolerance_chars 五条路径 ----------

def test_tolerance_record_document_none_batch52():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}


def test_tolerance_record_no_annotation_batch52():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, None, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_tolerance_record_chunks_lt_2_batch52():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]},
                             {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}


def test_tolerance_record_no_anchors_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_tolerance_record_normal_path_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"] == {"value": 42, "reason": None}
    assert "_missing_markers" not in out


# ---------- missing markers 语义 ----------

def test_missing_first_does_not_block_later_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "zz"},
        {"marker": "aa", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_missing_markers"]["value"] == ["zz"]
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_duplicate_marker_beyond_occurrences_batch52():
    """第二个 "aa" 从 search_from=2 起找不到 → 记 missing。"""
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "zz"},
        {"marker": "aa", "position": "after"},
        {"marker": "aa", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_missing_markers"]["value"] == ["zz", "aa"]
    # 只有第一个 aa 的 after=2 命中 pred 2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_all_markers_missing_recall_null_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xx"}, {"marker": "yy"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_explicit_empty_marker_missing_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == [""]


# ---------- 贪心匹配细节 ----------

def test_two_preds_one_gt_closest_wins_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}, {"text": "cc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "cc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream "aa bb cc"；preds 2,5；gt 6 → 5 胜（d=1），2 弃（d=4）
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(0.5)
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == pytest.approx(2 / 3)


def test_tie_distance_first_pred_wins_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "b"}, {"text": "cc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "b", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    # stream "aa b cc"；preds 2,4；gt 3 → 双 tie d=1；sort 稳定 → pred0 中
    assert out["chunk_boundary_precision"]["value"] == pytest.approx(0.5)
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- normalize_text 生效 ----------

def test_chunk_internal_spaces_normalized_batch52():
    doc = {"chunks": [{"text": "aa   bb"}, {"text": "cc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "bb", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # norm "aa bb"+"cc" → stream "aa bb cc"；bb after = 3+2 = 5 = pred
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_unnormalized_marker_not_found_batch52():
    doc = {"chunks": [{"text": "aa   bb"}, {"text": "cc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aa   bb", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_missing_markers"]["value"] == ["aa   bb"]


def test_marker_case_sensitive_batch52():
    doc = {"chunks": [{"text": "aa"}, {"text": "bb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "AA", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == ["AA"]


# ---------- 缺键语义 ----------

def test_annotation_missing_anchors_key_batch52():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"other": 1})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_document_missing_chunks_key_batch52():
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [
        {"marker": "x", "position": "after"},
    ]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


# ---------- figure_caption / 常量 ----------

def test_figure_caption_none_none_batch52():
    out = figure_caption_prf(None, None)
    assert list(out.keys()) == [
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    ]
    assert all(v == {"value": None, "reason": PARSER_DOES_NOT_EMIT_RELATIONS}
               for v in out.values())


def test_parser_does_not_emit_constant_value_batch52():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_all_3_entries_batch52():
    tree = ast.parse(inspect.getsource(ann_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert ast.unparse(all_assign) == (
        "__all__ = ['PARSER_DOES_NOT_EMIT_RELATIONS', "
        "'figure_caption_prf', 'chunk_boundary_prf']"
    )


# ---------- 源码补强 ----------

def _src() -> str:
    return inspect.getsource(ann_mod)


def test_source_two_guards_batch52():
    src = _src()
    assert "if document is None:" in src
    assert "if not annotation:" in src


def test_source_or_empty_lists_batch52():
    src = _src()
    assert 'anchors = annotation.get("chunk_boundary_anchors") or []' in src
    assert 'chunks = document.get("chunks") or []' in src


def test_source_chunks_lt_2_batch52():
    assert "if not chunks or len(chunks) < 2:" in _src()


def test_source_norm_list_comp_batch52():
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in _src()


def test_source_joined_raw_space_join_batch52():
    assert 'joined_raw = " ".join(norm_chunks)' in _src()


def test_source_stream_renormalize_batch52():
    assert "stream = normalize_text(joined_raw)" in _src()


def test_source_break_comment_batch52():
    assert "break  # 最后一个 chunk 后面不算边界" in _src()


def test_source_pairs_sort_batch52():
    assert "pairs.sort(key=lambda x: x[0])" in _src()


def test_source_search_from_advance_batch52():
    assert "search_from = find_pos + len(marker)" in _src()


def test_source_empty_marker_short_circuit_batch52():
    assert "if marker else -1" in _src() or "stream.find(marker, search_from) if marker else -1" in _src()


def test_source_f1_not_evaluated_reason_batch52():
    assert '"precision_or_recall_not_evaluated"' in _src()


def test_source_missing_condition_batch52():
    assert "if missing_markers:" in _src()


def test_source_tolerance_record_5_times_batch52():
    assert _src().count('out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}') == 5


def test_source_counter_import_batch52():
    assert "from collections import Counter" in _src()


# ---------- AST 补强 ----------

def _tree():
    return ast.parse(inspect.getsource(ann_mod))


def test_ast_chunk_boundary_5_returns_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) == 5


def test_ast_chunk_boundary_7_fors_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    # 2 个早期 k 循环 + chunks 循环 + anchors 循环 + 双层 pred/gt + pairs 循环
    assert len([n for n in ast.walk(func) if isinstance(n, ast.For)]) == 7


def test_ast_local_assign_names_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    for var in ("gt_positions", "missing_markers", "search_from", "pairs",
                "used_pred", "used_gt", "num_pred", "num_gt", "matched"):
        assert var in src


def test_ast_figure_caption_single_return_3_keys_batch52():
    tree = _tree()
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "figure_caption_prf")
    returns = [n for n in func.body if isinstance(n, ast.Return)]
    assert len(returns) == 1
    assert [k.value for k in returns[0].value.keys] == [
        "figure_caption_precision", "figure_caption_recall", "figure_caption_f1",
    ]


def test_ast_module_functions_2_batch52():
    tree = _tree()
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["figure_caption_prf", "chunk_boundary_prf"]


# ---------- forbidden tokens 第一百七十批 ----------

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
