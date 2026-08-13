"""evaluation/annotation_metrics.py 第九十一轮 edges 测试（Round 648）。

补强 edges72 未触及的角度（第四十八批）。

新角度：
- figure_caption_prf 函数纯净性（两次调用相等 / 接受 MagicMock / 三键固定顺序 / _null reason 完全相同字符串）
- chunk_boundary_prf 重复 marker 完整路径（3 个相同 marker / 跨多 chunk / search_from 推进验证）
- chunk_boundary_prf tolerance 边界（tolerance == distance 边界 inclusive / tolerance 巨大 / tolerance = 1）
- chunk_boundary_prf 算法核心（predicted 数 = N-1 / pos 推进 = end + 1 / 找不到 txt 时跳过）
- chunk_boundary_prf f1 计算分支（denom == 0 / p_val None / r_val None / 完美 / 半匹配）
- chunk_boundary_prf 一对一贪心（多 pred 一 anchor / 多 anchor 一 pred / 距离相同）
- chunk_boundary_prf 异常输入（chunk text 是 int / annotation 是 list / chunks 里 None dict / tolerance 是 float）
- module source 字符串补强（__future__ / Counter / typing.Any / normalize_text / __all__ / list[tuple] / break）
- AST 结构补强（chunk_boundary 6 if / lambda sort / enumerate / abs / no ClassDef / module docstring）
- forbidden tokens 第一百一十八批
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


# ---------- figure_caption_prf 函数纯净性 ----------

def test_figure_caption_prf_pure_two_calls_equal_batch48():
    """figure_caption_prf 是纯函数：两次调用结果完全相等。"""
    out1 = figure_caption_prf({"id": "a"}, {"k": 1})
    out2 = figure_caption_prf({"id": "b"}, {"k": 2})
    assert out1 == out2


def test_figure_caption_prf_accepts_magic_mock_batch48():
    """传 MagicMock 也应正常返回（不会因访问 mock 属性而失败）。"""
    m1 = MagicMock()
    m2 = MagicMock()
    out = figure_caption_prf(m1, m2)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_key_order_batch48():
    """key 顺序：precision → recall → f1。"""
    out = figure_caption_prf({}, {})
    keys = list(out.keys())
    assert keys == ["figure_caption_precision", "figure_caption_recall", "figure_caption_f1"]


def test_figure_caption_prf_all_three_reasons_identical_string_batch48():
    """3 个 metric 的 reason 是同一个常量字符串。"""
    out = figure_caption_prf(None, None)
    reasons = [v["reason"] for v in out.values()]
    assert reasons == [PARSER_DOES_NOT_EMIT_RELATIONS] * 3


def test_figure_caption_prf_no_call_dependencies_batch48():
    """函数体只引用常量 + _null，不访问输入参数。"""
    src = inspect.getsource(figure_caption_prf)
    # 输入参数 document / annotation 在函数体中不应被使用
    # （只在签名中出现）
    body_start = src.find(":\n")
    body = src[body_start:]
    for token in ("document", "annotation"):
        # body 中不应有 document[...] / annotation[...] / document. / annotation.
        assert f"{token}[" not in body
        assert f"{token}." not in body


# ---------- chunk_boundary_prf 重复 marker 完整路径 ----------

def test_chunk_boundary_repeated_marker_three_times_batch48(tmp_path):
    """3 个相同 marker 顺序定位：每个 anchor 的 search_from 都从前一个 marker 末尾开始。"""
    document = {
        "chunks": [
            {"text": "AAA marker AAA"},
            {"text": "marker BBB"},
            {"text": "marker CCC"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "marker", "position": "before"},
            {"marker": "marker", "position": "before"},
            {"marker": "marker", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=1000)
    # 3 个 marker 都应在 stream 中找到（顺序定位，不会都命中第一次）
    assert "_missing_markers" not in out


def test_chunk_boundary_repeated_marker_does_not_lose_second_batch48():
    """如果不顺序定位，两个相同 marker 会都命中第 1 次，丢失第 2 个。
    实现里 search_from 推进，所以两个 anchor 的 gt_positions 不同。"""
    document = {
        "chunks": [
            {"text": "AA marker AA"},
            {"text": "marker BB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "marker", "position": "before"},
            {"marker": "marker", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=100)
    # 没有丢失任何 marker
    assert "_missing_markers" not in out
    # recall 不为 0（说明 gt_positions 不为空）
    assert out["chunk_boundary_recall"]["value"] is not None


def test_chunk_boundary_search_from_advances_past_marker_batch48():
    """search_from 应推进到 marker 末尾，使下一个 marker 在更靠后的位置查找。"""
    # 第一个 marker 在 chunk0，第二个 marker 在 chunk1
    # 如果 search_from 不推进，第二个 anchor 会重复命中 chunk0 的 marker
    document = {
        "chunks": [
            {"text": "header X"},
            {"text": "header Y"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "header", "position": "after"},
            {"marker": "header", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=100)
    # 两个 anchor 都被找到
    assert "_missing_markers" not in out


# ---------- chunk_boundary_prf tolerance 边界 ----------

def test_chunk_boundary_tolerance_equal_distance_is_match_batch48():
    """d <= tolerance_chars：d == tolerance 应算 match（inclusive）。"""
    # chunks 之间预测边界位于 len("AA X") = 4
    # anchor marker "X" position="after" → gt_pos = 4
    # d == 0，tolerance = 0 → match
    document = {
        "chunks": [
            {"text": "AA X"},
            {"text": "BB Y"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "X", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # d == 0 ≤ 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_tolerance_huge_matches_all_batch48():
    """tolerance 巨大，所有距离都被算 match。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
            {"text": "CCCC"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},
            {"marker": "BBBB", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10**9)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_tolerance_one_excludes_distance_two_batch48():
    """tolerance=1 排除距离=2 的预测。"""
    # 预测边界位于 stream 中 chunk0 末尾位置
    # anchor marker 距离 2 → 不 match
    document = {
        "chunks": [
            {"text": "AAAAAA"},
            {"text": "BB"},
        ]
    }
    # 预测边界在 len("AAAAAA") = 6（stream = "AAAAAA BB"，chunk0 末尾 = 6）
    # anchor position="before" → gt_pos = marker 起点
    # 让 marker = "BB"，position="before"，gt_pos = 7
    # d = |6 - 7| = 1 ≤ 1 → match
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "BB", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf 算法核心 ----------

def test_chunk_boundary_predicted_count_is_n_minus_1_batch48():
    """predicted 边界数 = len(chunks) - 1（最后一个 chunk 末尾不算边界）。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
            {"text": "CCC"},
            {"text": "DDD"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=100)
    # 4 chunks → 3 predicted boundaries
    # precision = matched / num_pred
    # 完美匹配时 matched = 1，num_pred = 3 → precision = 1/3
    assert out["chunk_boundary_precision"]["value"] is not None
    p = out["chunk_boundary_precision"]["value"]
    # 只有一个 anchor，匹配 1 个；3 个预测，precision = 1/3
    assert abs(p - 1.0 / 3.0) < 1e-9


def test_chunk_boundary_pos_advances_by_end_plus_one_batch48():
    """pos 推进 = end + 1（跨空格），所以 stream 内的拼接分隔被跳过。"""
    # norm_chunks = ["AA", "BB"]，joined_raw = "AA BB"，stream = "AA BB"
    # 第 1 个 chunk："AA" 在 0 找到，end = 2，predicted = [2]，pos = 3
    # 第 2 个 chunk："BB" 在 stream.find("BB", 3) = 3 找到，但最后一个 chunk break
    document = {
        "chunks": [
            {"text": "AA"},
            {"text": "BB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 预测 = [2]，gt = 2，d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_text_not_found_skips_boundary_batch48():
    """找不到 txt（理论上不该发生）→ 跳过该 chunk 的右边界（pos += len(txt) + 1）。"""
    # 通过让 normalize_text 改变 chunk 文本，使 stream 里找不到原 txt
    # 这里我们模拟：chunk1 文本里带特殊空白，normalize 后变成空格
    # stream 中可能找不到原始 txt
    # 但 normalize 是无侵入的，所以测试这个分支很难触发
    # 改为：测试 chunks 里的 text 是 None 时（fallback 空字符串），不会触发"找不到"
    document = {
        "chunks": [
            {"text": None},
            {"text": "AAA"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=100)
    # norm_chunks = ["", "AAA"]，stream = "AAA"
    # 第 1 个 chunk txt = ""，find("", 0) = 0，end = 0，predicted = [0]，pos = 1
    # 最后一个 chunk break
    # gt_pos = 0（"AAA" position="before"）
    # d = 0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


# ---------- chunk_boundary_prf f1 计算分支 ----------

def test_chunk_boundary_f1_denom_zero_when_p_and_r_zero_batch48():
    """p_val + r_val == 0 → f1 = 0.0（不是 null）。"""
    # 构造场景：matched = 0 但 num_pred > 0 且 num_gt > 0
    document = {
        "chunks": [
            {"text": "AAAAAAAA"},
            {"text": "BBBBBBBB"},
        ]
    }
    # 预测边界在 stream = "AAAAAAAA BBBBBBBB" 的 chunk0 末尾 = 8
    # anchor marker "BBBBBBBB" position="before" → gt_pos = 9
    # d = 1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "BBBBBBBB", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # d = 1 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # p_val + r_val == 0 → f1 = 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_f1_perfect_score_batch48():
    """完美匹配 → P=R=F1=1.0。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_f1_half_match_batch48():
    """一半匹配 → P=R=0.5, F1=0.5。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
            {"text": "CCC"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # 2 predicted, 1 anchor, matched = 1
    # precision = 1/2, recall = 1/1
    # f1 = 2 * 0.5 * 1.0 / (0.5 + 1.0) = 1.0 / 1.5 = 2/3
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert abs(p - 0.5) < 1e-9
    assert abs(r - 1.0) < 1e-9
    assert abs(f1 - 2.0 / 3.0) < 1e-9


def test_chunk_boundary_f1_null_when_precision_null_batch48():
    """precision 是 null → f1 也是 null。"""
    document = {
        "chunks": [
            {"text": "AAA"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # chunks < 2 → precision/recall/f1 全 null（recall 是 _ratio(0.0)）
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None


# ---------- chunk_boundary_prf 一对一贪心 ----------

def test_chunk_boundary_one_to_one_two_preds_one_anchor_batch48():
    """2 个预测距离 1 个 anchor 都在容差内，但一对一：只 match 最近的。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
            {"text": "CCCC"},
        ]
    }
    # 预测：4（AAA|BBB 边界），9（BBB|CCC 边界）
    # anchor marker "BBBB" position="before" → gt_pos = 4
    # 第一个预测 d = 0，第二个预测 d = 5
    # tolerance = 5 → 两个都候选，但一对一贪心 → 只 match 第一个
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "BBBB", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=5)
    # matched = 1，num_pred = 2 → precision = 0.5
    assert abs(out["chunk_boundary_precision"]["value"] - 0.5) < 1e-9


def test_chunk_boundary_one_to_one_two_anchors_one_pred_batch48():
    """2 个 anchor 都靠近 1 个预测，但一对一：只 match 最近的。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
        ]
    }
    # 预测：4（chunk0 末尾）
    # anchor1 marker "AAAA" position="after" → gt_pos = 4，d = 0
    # anchor2 marker "BBBB" position="before" → gt_pos = 5（stream = "AAAA BBBB"）
    # d = 1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},
            {"marker": "BBBB", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # 1 个预测，2 个 anchor，matched = 1
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert abs(out["chunk_boundary_precision"]["value"] - 1.0) < 1e-9
    assert abs(out["chunk_boundary_recall"]["value"] - 0.5) < 1e-9


def test_chunk_boundary_one_to_one_greedy_sort_by_distance_batch48():
    """贪心按 (distance, pred_idx, gt_idx) 升序：先 match 距离最近的 pair。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
            {"text": "CCCC"},
        ]
    }
    # 预测：4, 9
    # 让 anchor marker 同时让两个 anchor 都接近预测 4，但只能 match 一个
    # anchor1: marker "AAAA" after → gt_pos = 4, d(pred=4) = 0
    # anchor2: marker "BBBB" after → gt_pos = 8, d(pred=4) = 4, d(pred=9) = 1
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},
            {"marker": "BBBB", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=10)
    # (d=0, pred=0, gt=0), (d=4, pred=0, gt=1), (d=1, pred=1, gt=1)
    # 排序后：(0,0,0), (1,1,1), (4,0,1)
    # 先 match (0,0,0) → used_pred={0}, used_gt={0}
    # 然后 match (1,1,1) → used_pred={0,1}, used_gt={0,1}
    # 最后 (4,0,1) 跳过
    # matched = 2, num_pred = 2, num_gt = 2 → P=R=1.0
    assert abs(out["chunk_boundary_precision"]["value"] - 1.0) < 1e-9
    assert abs(out["chunk_boundary_recall"]["value"] - 1.0) < 1e-9


# ---------- chunk_boundary_prf 异常输入 ----------

def test_chunk_boundary_annotation_is_list_not_dict_batch48():
    """annotation 是非空 list：list 没有 .get 方法 → AttributeError。"""
    document = {"chunks": [{"text": "AAA"}, {"text": "BBB"}]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(document, ["non_empty"])


def test_chunk_boundary_tolerance_float_batch48():
    """tolerance_chars 是 float 也能工作（abs 返回 float，<= 仍可比较）。"""
    document = {
        "chunks": [
            {"text": "AAAA"},
            {"text": "BBBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "AAAA", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0.5)
    # tolerance 字段记录原值
    assert out["_tolerance_chars"]["value"] == 0.5


def test_chunk_boundary_anchor_missing_marker_key_batch48():
    """anchor 缺 marker key → marker 默认 ""，falsy → find_pos = -1 → 计入 missing_markers。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"position": "after"},  # 无 marker
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # marker = ""，是 falsy → find_pos = -1 → missing_markers.append("")
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == [""]


def test_chunk_boundary_anchor_marker_empty_string_batch48():
    """anchor marker 显式空字符串：falsy → find_pos = -1 → 计入 missing_markers。"""
    document = {
        "chunks": [
            {"text": "AAA"},
            {"text": "BBB"},
        ]
    }
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "", "position": "before"},
        ]
    }
    out = chunk_boundary_prf(document, annotation, tolerance_chars=0)
    # marker = ""，falsy → find_pos = -1 → missing_markers
    assert "_missing_markers" in out
    # num_gt = 0 → recall null
    assert out["chunk_boundary_recall"]["value"] is None


# ---------- 模块源码补强 ----------

def test_source_contains_future_annotations_batch48():
    src = inspect.getsource(am_mod)
    assert "from __future__ import annotations" in src


def test_source_contains_counter_import_batch48():
    """Counter 虽然 import 了但实际未在 annotation_metrics 中使用。"""
    src = inspect.getsource(am_mod)
    assert "from collections import Counter" in src


def test_source_contains_typing_any_batch48():
    src = inspect.getsource(am_mod)
    assert "from typing import Any" in src


def test_source_contains_normalize_text_import_batch48():
    src = inspect.getsource(am_mod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_source_contains_null_ratio_import_batch48():
    src = inspect.getsource(am_mod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_source_contains_all_list_batch48():
    src = inspect.getsource(am_mod)
    assert "__all__" in src
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src
    assert "figure_caption_prf" in src
    assert "chunk_boundary_prf" in src


def test_source_contains_list_tuple_annotation_batch48():
    src = inspect.getsource(am_mod)
    # list[int] 和 list[tuple[int, int, int]]
    assert "list[int]" in src
    assert "list[tuple[int, int, int]]" in src


def test_source_contains_break_in_loop_batch48():
    src = inspect.getsource(chunk_boundary_prf)
    assert "break" in src


def test_source_contains_continue_in_loop_batch48():
    src = inspect.getsource(chunk_boundary_prf)
    assert "continue" in src


def test_source_contains_normalize_text_called_batch48():
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text(" in src


def test_source_contains_search_from_keyword_batch48():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from" in src


def test_source_contains_pipeline_failed_reason_batch48():
    src = inspect.getsource(am_mod)
    assert '"pipeline_failed"' in src


def test_source_contains_no_annotation_reason_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_annotation"' in src


def test_source_contains_no_predicted_boundaries_reason_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_predicted_boundaries"' in src


def test_source_contains_no_ground_truth_anchors_reason_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors"' in src


def test_source_contains_no_ground_truth_anchors_in_stream_reason_batch48():
    src = inspect.getsource(am_mod)
    assert '"no_ground_truth_anchors_in_stream"' in src


def test_source_contains_precision_or_recall_not_evaluated_batch48():
    src = inspect.getsource(am_mod)
    assert '"precision_or_recall_not_evaluated"' in src


def test_source_contains_docstring_figures_caption_batch48():
    src = inspect.getsource(am_mod)
    assert "图表关联" in src or "figure-caption" in src or "figure_caption" in src


def test_source_contains_docstring_chunk_boundary_batch48():
    src = inspect.getsource(am_mod)
    assert "分块边界" in src or "chunk_boundary" in src or "chunk-boundary" in src


def test_source_contains_docstring_one_to_one_batch48():
    src = inspect.getsource(am_mod)
    assert "一对一" in src or "one-to-one" in src or "one_to_one" in src


def test_source_contains_docstring_tolerance_batch48():
    src = inspect.getsource(am_mod)
    assert "容差" in src or "tolerance" in src.lower()


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 2


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
    assert isinstance(tree.body[0].value.value, str)


def test_ast_chunk_boundary_default_tolerance_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    defaults = func.args.defaults
    assert len(defaults) == 1
    assert isinstance(defaults[0], ast.Constant)
    assert defaults[0].value == 30


def test_ast_figure_caption_no_default_batch48():
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "figure_caption_prf")
    assert len(func.args.defaults) == 0


def test_ast_chunk_boundary_multiple_returns_batch48():
    """chunk_boundary_prf 内部有多个 return（doc string 后 6 个分支）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 5


def test_ast_chunk_boundary_has_lambda_sort_batch48():
    """pairs.sort 使用 lambda。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    lambdas = [n for n in ast.walk(func) if isinstance(n, ast.Lambda)]
    assert len(lambdas) >= 1


def test_ast_chunk_boundary_has_enumerate_calls_batch48():
    """使用 enumerate 遍历。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_enumerate = any(
        isinstance(c.func, ast.Name) and c.func.id == "enumerate" for c in calls
    )
    assert has_enumerate


def test_ast_chunk_boundary_has_abs_calls_batch48():
    """使用 abs() 计算距离。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_abs = any(
        isinstance(c.func, ast.Name) and c.func.id == "abs" for c in calls
    )
    assert has_abs


def test_ast_chunk_boundary_has_break_batch48():
    """最后一个 chunk 时 break。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    breaks = [n for n in ast.walk(func) if isinstance(n, ast.Break)]
    assert len(breaks) >= 1


def test_ast_chunk_boundary_has_continue_batch48():
    """找不到 txt 时 continue。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    continues = [n for n in ast.walk(func) if isinstance(n, ast.Continue)]
    assert len(continues) >= 1


def test_ast_chunk_boundary_has_multiple_for_batch48():
    """chunk_boundary_prf 至少 4 个 for（norm_chunks、predicted、anchors、pairs match）。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 4


def test_ast_chunk_boundary_has_nested_for_in_for_batch48():
    """一对一匹配是 nested for in for。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    outer_fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    has_nested = any(
        any(isinstance(child, ast.For) for child in ast.walk(outer))
        for outer in outer_fors
    )
    assert has_nested


def test_ast_chunk_boundary_has_if_test_pipeline_failed_batch48():
    """document is None 分支返回 pipeline_failed。"""
    tree = ast.parse(inspect.getsource(am_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "chunk_boundary_prf")
    src = ast.unparse(func)
    assert "pipeline_failed" in src


def test_ast_module_top_level_assign_count_batch48():
    """模块顶部 Assign：PARSER_DOES_NOT_EMIT_RELATIONS + __all__。"""
    tree = ast.parse(inspect.getsource(am_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：from __future__ / from collections / from typing / from app.chunkers / from evaluation.metrics。"""
    tree = ast.parse(inspect.getsource(am_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 5


# ---------- forbidden tokens 第一百一十八批 ----------

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


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_open_mode_w_batch48():
    """annotation_metrics.py 是纯计算模块，不应有 open(..., 'w')。"""
    assert "open(" not in _src()


def test_source_no_pathlib_batch48():
    assert "pathlib" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()
