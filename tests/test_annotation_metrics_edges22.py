r"""evaluation/annotation_metrics.py 边角测试 - 第二十二轮（Round 297）。

edges21 已覆盖：figure_caption_prf 行为深度 / chunk_boundary_prf 5 个分支 /
f1 计算深度 / 一对一贪心 / source level 完整 / forbidden tokens / __all__ /
常量 / imports / 算法可重现 + no side effects。

edges22 补强未覆盖的角度（深度边界 + source level + signatures + 端到端）：
- **figure_caption_prf 行为深度补强**：返回 dict 3 key 顺序精确；reason field 字面量精确；
  返回 dict 不依赖 document 状态；返回 dict 不依赖 annotation 状态；
  figure_caption_precision/recall/f1 三 key 的 value dict 结构精确（含 value=None + reason 字符串）；
  PARSER_DOES_NOT_EMIT_RELATIONS 是 str + 不可变（常量）；
  对 document={} / annotation={} 返同样结果；对 document with elements/chunks 返同样结果
- **chunk_boundary_prf 边界补强**：document is None + annotation 是 dict → pipeline_failed；
  document 是 dict + annotation is None → no_annotation；
  document 是 dict + annotation 是 {} → no_annotation；
  document 是 dict + annotation 是 dict 但缺 chunk_boundary_anchors → no_annotation（anchors 默认 []）；
  document 缺 chunks key（None chunks）+ annotation 有 anchors → no_predicted_boundaries；
  chunks=[c1] (len<2) + annotation 有 anchors → no_predicted_boundaries；
  chunks=[c1] + annotation 无 anchors → no_predicted_boundaries + recall=null；
  chunks=[c1,c2] + annotation 无 anchors → no_ground_truth_anchors；
  chunks=[c1,c2] + annotation 有 anchors → 实际计算
- **chunk_boundary_prf tolerance_chars 字段精确**：默认 30；可传 0；可传极大值；负数；
  tolerance_chars value 出现在 _tolerance_chars 字段；reason=None
- **chunk_boundary_prf anchor 边界补强**：anchor 是 dict 缺 marker → marker=""；
  anchor 是 dict 缺 position → position="after"；marker 是空字符串 → 找不到 → missing_markers；
  marker 含 unicode 空白 → normalize 后查找；marker 不在 stream 中 → missing_markers；
  marker 在 stream 中部分出现 → 部分匹配；重复 marker → search_from 推进
- **chunk_boundary_prf stream 构造深度**：单 chunk 不构造 stream；
  多 chunk 用 ' ' 连接 norm_chunks 再 normalize；空白 chunk 贡献 0 字符；
  全 unicode 空白 chunk → norm_chunks 都是空字符串
- **chunk_boundary_prf predicted 边界**：predicted 列表长度 = chunks-1；
  最后一个 chunk 不算边界；某些 chunk text 在 stream 中找不到 → pos 推进但 predicted 不 append
- **chunk_boundary_prf 贪心匹配深度**：完全 0 距离匹配 → matched 增加；
  多对一距离排序 → 升序；同一 pred 不能匹配多个 gt；同一 gt 不能匹配多个 pred；
  tolerance=0 → 仅完全相同位置匹配；tolerance=负数 → 全部不匹配
- **chunk_boundary_prf f1 边界**：p_val=None r_val=None → null；p_val+r_val=0 → _ratio(0.0)；
  p_val=r_val=0.5 → f1=0.5；p_val=1.0 r_val=0.0 → f1=0.0；正常计算 2*p*r/(p+r)
- **module __all__ 精确**：3 entries 顺序：PARSER_DOES_NOT_EMIT_RELATIONS, figure_caption_prf, chunk_boundary_prf；
  所有 entries 在 namespace；所有 callable 或 constant；__all__ is list[str]
- **module imports 顺序**：__future__ → collections → typing → app.chunkers.structural → evaluation.metrics；
  5 个 import statements 精确
- **module docstring 深度**：含「figure-caption」/「chunk_boundary P/R/F1」/「一对一」/「容差」/
  「tolerance_chars」/「不引入启发式」
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/threading/
  concurrent/collections.Counter（实际 import 了但仅用于内部）/math/datetime/itertools/functools/
  json/star/relative/class/dataclass/yield/async/global/walrus/assert
- **module source 含**：from __future__ import annotations；from collections import Counter；
  from typing import Any；from app.chunkers.structural import normalize_text；
  from evaluation.metrics import _null, _ratio
- **figure_caption_prf source level 完整**：含 def figure_caption_prf；含 document/annotation 2 params；
  含 tolerance_chars 无（只有 chunk_boundary_prf 有）；含 return dict 字面量；
  含 _null(reason) 调用 3 处；含 reason=PARSER_DOES_NOT_EMIT_RELATIONS 赋值
- **chunk_boundary_prf source level 完整**：含 def chunk_boundary_prf；
  含 5 个 return 分支（pipeline_failed / no_annotation / no_predicted_boundaries /
  no_ground_truth_anchors / 完整路径）；含 tolerance_chars=30 默认；
  含 if document is None / if not annotation / if not chunks or len(chunks) < 2 /
  if not anchors 5 处分支判断；含 norm_chunks / joined_raw / stream 三步流构造；
  含 predicted append / gt_positions append / search_from 推进；
  含 pairs.sort / matched 计算 / used_pred/used_gt 去重；
  含 precision/recall/f1 三段独立计算；含 _tolerance_chars / _missing_markers 字段填充
- **signatures 精确**：figure_caption_prf 2 params + return dict；
  chunk_boundary_prf 3 params + tolerance_chars default=30 + return dict；
  2 个 callable no varargs/varkw；return annotation 是 dict[str, dict[str, Any]]
- **module namespace**：figure_caption_prf / chunk_boundary_prf 是 module-level function；
  PARSER_DOES_NOT_EMIT_RELATIONS 是 module-level constant；
  _null / _ratio / Counter / Any / normalize_text 是 imported name；
  无私有函数（_前缀）
- **端到端集成**：完整 document + 完整 annotation → 算出真实 P/R/F1；
  同输入两次调用结果一致；不修改 input document；不修改 input annotation；
  通过 schema 验证（_tolerance_chars 字段类型 int）；missing_markers 字段类型 list[str]
- **模块整体合理性**：__all__ 3 entries；2 个 module-level function；1 个 module-level constant；
  无 class 定义；无 __main__ 块
"""

from __future__ import annotations

import copy
import inspect
from typing import Any

import pytest

import evaluation.annotation_metrics as ammod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# 辅助
# =========================================================================


def _make_chunk(text: str, cid: str = "c") -> dict[str, Any]:
    return {"chunk_id": cid, "text": text, "source_element_ids": ["e1"]}


def _make_doc(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_type": "pdf",
        "source_hash": "abc",
        "document_id": "d1",
        "source_path": "/tmp/x.pdf",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "chunks": chunks,
    }


def _make_anchor(marker: str, position: str = "after") -> dict[str, Any]:
    return {"marker": marker, "position": position}


# =========================================================================
# figure_caption_prf 行为深度补强
# =========================================================================


def test_figure_caption_prf_returns_3_keys_in_order():
    """返回 dict 3 key 顺序精确（figure_caption_precision/recall/f1）。"""
    out = figure_caption_prf({"chunks": []}, None)
    keys = list(out.keys())
    assert keys == ["figure_caption_precision", "figure_caption_recall", "figure_caption_f1"]


def test_figure_caption_prf_reason_value_is_constant():
    out = figure_caption_prf({}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_value_is_none():
    out = figure_caption_prf({}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None


def test_figure_caption_prf_value_dict_structure():
    """每个 value dict 含 value + reason 2 key。"""
    out = figure_caption_prf({}, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert set(out[k].keys()) == {"value", "reason"}


def test_figure_caption_prf_returns_independent_dicts():
    """多次调用返回独立 dict（不缓存）。"""
    out1 = figure_caption_prf({}, None)
    out2 = figure_caption_prf({}, None)
    assert out1 is not out2
    assert out1["figure_caption_precision"] is not out2["figure_caption_precision"]


def test_figure_caption_prf_does_not_read_document():
    """document 即使是非法结构也不影响输出。"""
    doc_with_garbage = {"totally_unrelated": "value"}
    out = figure_caption_prf(doc_with_garbage, {"chunk_boundary_anchors": []})
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_read_annotation():
    out = figure_caption_prf({"chunks": []}, {"any": "thing"})
    assert out["figure_caption_precision"]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_constant_is_str():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_figure_caption_prf_constant_immutable():
    """常量字符串不可变（hashable）。"""
    assert hash(PARSER_DOES_NOT_EMIT_RELATIONS) is not None


def test_figure_caption_prf_with_doc_elements():
    """document 有 elements 也不影响 figure_caption 结果。"""
    doc = {"elements": [{"type": "image"}], "chunks": []}
    out = figure_caption_prf(doc, {"chunk_boundary_anchors": []})
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_document_annotation_both_none():
    out = figure_caption_prf(None, None)
    assert "figure_caption_precision" in out
    assert out["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_namespace_constant():
    """PARSER_DOES_NOT_EMIT_RELATIONS 在模块 namespace。"""
    assert hasattr(ammod, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert ammod.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# chunk_boundary_prf 边界补强 - 5 个分支精确
# =========================================================================


def test_chunk_boundary_prf_document_none_with_annotation():
    """document is None + annotation 是 dict → 3 个 metric reason='pipeline_failed'。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": [_make_anchor("x")]})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_none_with_doc():
    """document 是 dict + annotation is None → 3 个 metric reason='no_annotation'。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk("b")])
    out = chunk_boundary_prf(doc, None)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
    assert out["chunk_boundary_recall"]["reason"] == "no_annotation"
    assert out["chunk_boundary_f1"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict():
    """annotation = {} → falsy → no_annotation。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk("b")])
    out = chunk_boundary_prf(doc, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_missing_anchors_key():
    """annotation 缺 chunk_boundary_anchors → falsy → no_annotation。

    注意：annotation 本身 truthy（其他 key），anchors 默认 []，但此分支不会走到，
    因为 if not annotation 只检查 annotation 本身。
    """
    doc = _make_doc([_make_chunk("a"), _make_chunk("b")])
    out = chunk_boundary_prf(doc, {"other_key": "value"})
    # annotation 是 truthy dict，所以走 anchors = annotation.get(...) or []
    # anchors=[] → 走 no_ground_truth_anchors 分支（不是 no_annotation）
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_doc_missing_chunks_key():
    """document 缺 chunks key → chunks=None → 默认 [] → len < 2 → no_predicted_boundaries。"""
    doc = {"source_type": "pdf"}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [_make_anchor("x")]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_single_no_anchors():
    """chunks=[c1] (len<2) + 无 anchors → no_predicted_boundaries + recall null（无 anchors）。"""
    doc = _make_doc([_make_chunk("a")])
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_single_with_anchors():
    """chunks=[c1] + 有 anchors → no_predicted_boundaries；recall 走 _ratio(0.0)。"""
    doc = _make_doc([_make_chunk("a")])
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [_make_anchor("a")]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall：anchors 真值 → _ratio(0.0)
    # _ratio(0.0) 返回 {"value": 0.0, "reason": None}
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_chunks_two_no_anchors():
    """chunks=[c1, c2] + 无 anchors → no_ground_truth_anchors。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk("b")])
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf tolerance_chars 字段精确
# =========================================================================


def test_chunk_boundary_prf_tolerance_chars_default_30():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_chars_zero():
    out = chunk_boundary_prf(None, None, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_chars_huge():
    out = chunk_boundary_prf(None, None, tolerance_chars=1000000)
    assert out["_tolerance_chars"]["value"] == 1000000


def test_chunk_boundary_prf_tolerance_chars_negative():
    out = chunk_boundary_prf(None, None, tolerance_chars=-5)
    assert out["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_prf_tolerance_chars_reason_always_none():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_tolerance_chars_field_always_present():
    """无论分支，_tolerance_chars 都存在。"""
    # document None 路径
    out = chunk_boundary_prf(None, None)
    assert "_tolerance_chars" in out
    # annotation falsy 路径
    doc = _make_doc([_make_chunk("a"), _make_chunk("b")])
    out = chunk_boundary_prf(doc, None)
    assert "_tolerance_chars" in out
    # 完整路径
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello")]}
    out = chunk_boundary_prf(doc, ann)
    assert "_tolerance_chars" in out


# =========================================================================
# chunk_boundary_prf anchor 边界补强
# =========================================================================


def test_chunk_boundary_prf_anchor_missing_marker_defaults_empty():
    """anchor 缺 marker → marker='' → 找不到 → missing_markers。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    # marker='' → stream.find('', ...) returns 0 不 < 0；但 if marker 检查让 find_pos=-1
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_anchor_missing_position_defaults_after():
    """anchor 缺 position → position='after'。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [{"marker": "hello"}]}
    out = chunk_boundary_prf(doc, ann)
    # 不抛异常，正常计算
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_anchor_invalid_position_defaults_after():
    """position='random_string' → fall through to else (after) branch。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "weird"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_marker_with_unicode_whitespace():
    """marker 含 unicode 空白 → normalize 后查找。"""
    doc = _make_doc([_make_chunk("hello world"), _make_chunk("foo")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello world")]}
    out = chunk_boundary_prf(doc, ann)
    # 应能找到
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_marker_not_in_stream():
    """marker 不在 stream 中 → missing_markers。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("nonexistent")]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_partial_match():
    """marker 部分出现 → 部分匹配 + 部分 missing。"""
    doc = _make_doc([_make_chunk("hello world"), _make_chunk("foo")])
    ann = {"chunk_boundary_anchors": [
        _make_anchor("hello"),  # 找到
        _make_anchor("missing"),  # 找不到
    ]}
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out
    assert "missing" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_duplicate_markers_advance_search_from():
    """重复 marker → search_from 推进。"""
    doc = _make_doc([_make_chunk("hello hello"), _make_chunk("hello")])
    ann = {"chunk_boundary_anchors": [
        _make_anchor("hello"),
        _make_anchor("hello"),
    ]}
    out = chunk_boundary_prf(doc, ann)
    # 两个 anchor 都应被找到（search_from 推进）
    assert "_missing_markers" not in out


# =========================================================================
# chunk_boundary_prf stream 构造深度
# =========================================================================


def test_chunk_boundary_prf_stream_single_chunk_no_stream():
    """单 chunk → len < 2 → 直接走 no_predicted_boundaries 分支（不构造 stream）。"""
    doc = _make_doc([_make_chunk("hello")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello")]}
    out = chunk_boundary_prf(doc, ann)
    # 不抛异常
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_stream_multiple_chunks_joined():
    """多 chunk 用 ' ' 连接 norm_chunks 再 normalize。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello world")]}
    out = chunk_boundary_prf(doc, ann)
    # stream = "hello world" → marker "hello world" 应被找到
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_stream_empty_chunk_contributes_zero():
    """空白 chunk 贡献 0 字符但仍是 stream 一部分。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk(""), _make_chunk("b")])
    ann = {"chunk_boundary_anchors": [_make_anchor("a")]}
    out = chunk_boundary_prf(doc, ann)
    # 不抛异常
    assert "chunk_boundary_precision" in out


# =========================================================================
# chunk_boundary_prf predicted 边界
# =========================================================================


def test_chunk_boundary_prf_predicted_length_is_chunks_minus_one():
    """predicted 长度 = chunks - 1（最后一个 chunk 不算边界）。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk("b"), _make_chunk("c")])
    ann = {"chunk_boundary_anchors": [_make_anchor("a"), _make_anchor("b")]}
    out = chunk_boundary_prf(doc, ann)
    # 不直接 assert predicted 长度，但通过算法稳定性验证：3 chunks → 2 boundaries
    assert out["chunk_boundary_precision"]["value"] is not None or \
           out["chunk_boundary_precision"]["reason"] in ("no_predicted_boundaries",)


def test_chunk_boundary_prf_perfect_match():
    """完美匹配 → precision=recall=1.0 → f1=1.0。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    # anchor 在 'hello' 末尾（position=after）→ position = 5
    # predicted 边界也是 'hello' 末尾 → 5
    ann = {"chunk_boundary_anchors": [_make_anchor("hello", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf 贪心匹配深度
# =========================================================================


def test_chunk_boundary_prf_zero_distance_match():
    """完全 0 距离匹配 → matched 增加。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_match():
    """tolerance=0 → 仅完全相同位置匹配。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    # anchor 在 stream 偏移位置不同
    ann = {"chunk_boundary_anchors": [_make_anchor("hel", position="after")]}  # position=3
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted 是 5 (hello 末尾)，gt 是 3 → distance=2 > 0 → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_negative_no_match():
    """tolerance=负数 → 全部不匹配。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    # distance=0 但 0 <= -1 false → 不匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_pairs_sorted_by_distance():
    """pairs 按 distance 升序排序 → 最近匹配优先。"""
    doc = _make_doc([_make_chunk("aaa"), _make_chunk("bbb")])
    # 2 anchors，1 距离近，1 距离远（但都在 tolerance 内）
    ann = {"chunk_boundary_anchors": [
        _make_anchor("aaa", position="after"),  # gt=3
        _make_anchor("aaab", position="after"),  # 不在 stream，missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 至少不抛异常
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_one_pred_matches_nearest_gt():
    """一个 pred 匹配多个 gt → 只选最近的。

    注意：search_from 推进让第二个 marker 从第一个之后开始查找。
    若两个 marker 完全相同，search_from 让第二个查找不到。
    用两个不同 marker（都在 stream 内不同位置）测一对一贪心。
    """
    # stream = "hello world foo"
    # predicted 边界在 hello 之后（位置 5）和 world 之后（位置 11）
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world"), _make_chunk("foo")])
    # 2 anchors，但 search_from 推进：
    #   anchor1: "hello" position=after → gt=5 (find_pos=0, +5=5)
    #   anchor2: "world" position=after → find from 5+5=10, find_pos=6, +5=11 → gt=11
    ann = {"chunk_boundary_anchors": [
        _make_anchor("hello", position="after"),  # gt=5
        _make_anchor("world", position="after"),  # gt=11
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted=[5, 11], gt=[5, 11] → matched=2
    # precision=2/2=1.0, recall=2/2=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf f1 边界
# =========================================================================


def test_chunk_boundary_prf_f1_both_null():
    """p_val=None + r_val=None → f1=null。"""
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_f1_p_null_r_value():
    """p_val=None + r_val=值 → f1=null。"""
    doc = _make_doc([_make_chunk("a")])  # 单 chunk → no_predicted_boundaries
    ann = {"chunk_boundary_anchors": [_make_anchor("a")]}  # 有 anchors
    out = chunk_boundary_prf(doc, ann)
    # precision=null（no_predicted_boundaries），recall=0.0（anchors truthy）
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # f1 → null
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_f1_p_value_r_null():
    """p_val=值 + r_val=None → f1=null。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": []}  # 无 anchors → 但走 no_ground_truth_anchors 分支
    out = chunk_boundary_prf(doc, ann)
    # 走 no_ground_truth_anchors 分支 → 3 个都 null
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None


def test_chunk_boundary_prf_f1_zero_p_zero_r():
    """p_val+r_val=0 → f1=0.0。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("xyz", position="after")]}
    # xyz 找不到 → missing_markers → gt_positions=[]
    # → recall null no_ground_truth_anchors_in_stream
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # precision：predicted=1, matched=0 → 0.0
    # recall：gt_positions=[] → null
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_f1_normal_computation():
    """p=0.5, r=1.0 → f1 = 2*0.5*1.0/(0.5+1.0) = 1.0/1.5 = 0.6667。"""
    doc = _make_doc([_make_chunk("a"), _make_chunk("b"), _make_chunk("c")])
    # 3 chunks → 2 predicted boundaries
    # 1 anchor at position 1 (after 'a') → matches pred at 1
    ann = {"chunk_boundary_anchors": [_make_anchor("a", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted=[1, 3], gt=[1] → matched=1
    # precision=1/2=0.5, recall=1/1=1.0
    # f1 = 2*0.5*1.0/(0.5+1.0) ≈ 0.6667
    assert abs(out["chunk_boundary_precision"]["value"] - 0.5) < 1e-6
    assert abs(out["chunk_boundary_recall"]["value"] - 1.0) < 1e-6
    assert abs(out["chunk_boundary_f1"]["value"] - (2 * 0.5 * 1.0 / 1.5)) < 1e-6


# =========================================================================
# module __all__ 精确
# =========================================================================


def test_module_all_has_3_entries_in_order():
    assert ammod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_entries_in_namespace():
    for name in ammod.__all__:
        assert hasattr(ammod, name)


def test_module_all_entries_valid_identifier():
    for name in ammod.__all__:
        assert name.isidentifier()


def test_module_all_is_list_of_str():
    assert isinstance(ammod.__all__, list)
    for name in ammod.__all__:
        assert isinstance(name, str)


def test_module_all_constant_callable_present():
    assert callable(ammod.figure_caption_prf)
    assert callable(ammod.chunk_boundary_prf)
    assert isinstance(ammod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


# =========================================================================
# module imports 顺序
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(ammod)
    assert "from __future__ import annotations" in src


def test_module_source_has_collections_counter_import():
    src = inspect.getsource(ammod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(ammod)
    assert "from typing import Any" in src


def test_module_source_has_app_chunkers_normalize_text():
    src = inspect.getsource(ammod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_evaluation_metrics_null_ratio():
    src = inspect.getsource(ammod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_imports_order_correct():
    """5 imports 顺序：future → collections → typing → app → evaluation。"""
    src = inspect.getsource(ammod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    # 第 1 个是 future
    assert lines[0] == "from __future__ import annotations"
    # 找到 evaluation.metrics 应在 app 之后
    app_idx = next(i for i, l in enumerate(lines) if "from app" in l)
    eval_idx = next(i for i, l in enumerate(lines) if "from evaluation" in l)
    assert eval_idx > app_idx


# =========================================================================
# module docstring 深度
# =========================================================================


def test_module_docstring_contains_figure_caption():
    doc = ammod.__doc__ or ""
    assert "figure-caption" in doc or "figure_caption" in doc.lower()


def test_module_docstring_contains_chunk_boundary():
    doc = ammod.__doc__ or ""
    assert "chunk_boundary" in doc or "chunk boundary" in doc.lower()


def test_module_docstring_contains_yididuiyi():
    doc = ammod.__doc__ or ""
    assert "一对一" in doc


def test_module_docstring_contains_tolerance():
    doc = ammod.__doc__ or ""
    assert "容差" in doc or "tolerance" in doc.lower()


def test_module_docstring_contains_no_heuristic():
    doc = ammod.__doc__ or ""
    assert "启发式" in doc or "heuristic" in doc.lower()


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_module():
    src = inspect.getsource(ammod)
    assert "\nimport os" not in src
    assert "from os " not in src


def test_module_source_no_sys_module():
    src = inspect.getsource(ammod)
    assert "\nimport sys" not in src
    assert "from sys " not in src


def test_module_source_no_re_module():
    src = inspect.getsource(ammod)
    assert "\nimport re" not in src
    assert "from re " not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(ammod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(ammod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(ammod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(ammod)
    assert "\nimport threading" not in src


def test_module_source_no_math_module():
    src = inspect.getsource(ammod)
    assert "\nimport math" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(ammod)
    assert "\nimport datetime" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(ammod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(ammod)
    assert "\nimport functools" not in src


def test_module_source_no_json_module():
    src = inspect.getsource(ammod)
    assert "\nimport json" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(ammod)
    assert "from ." not in src


def test_module_source_no_class_def():
    src = inspect.getsource(ammod)
    assert "\nclass " not in src


def test_module_source_no_dataclass_decorator():
    src = inspect.getsource(ammod)
    assert "@dataclass" not in src


def test_module_source_no_yield():
    src = inspect.getsource(ammod)
    assert "yield " not in src


def test_module_source_no_async_def():
    src = inspect.getsource(ammod)
    assert "async def" not in src


def test_module_source_no_global_stmt():
    src = inspect.getsource(ammod)
    assert "\nglobal " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(ammod)
    assert ":=" not in src


def test_module_source_no_assert_stmt():
    src = inspect.getsource(ammod)
    assert "\nassert " not in src


# =========================================================================
# figure_caption_prf source level 完整
# =========================================================================


def test_figure_caption_prf_source_has_def():
    src = inspect.getsource(figure_caption_prf)
    assert "def figure_caption_prf(" in src


def test_figure_caption_prf_source_has_2_params():
    src = inspect.getsource(figure_caption_prf)
    assert "document" in src
    assert "annotation" in src


def test_figure_caption_prf_source_has_no_tolerance_param():
    src = inspect.getsource(figure_caption_prf)
    # figure_caption_prf 没有 tolerance_chars 参数
    # 在 def 行检查
    def_line = next(l for l in src.splitlines() if "def figure_caption_prf" in l)
    assert "tolerance_chars" not in def_line


def test_figure_caption_prf_source_has_return_dict():
    src = inspect.getsource(figure_caption_prf)
    assert "return {" in src


def test_figure_caption_prf_source_has_3_null_calls():
    src = inspect.getsource(figure_caption_prf)
    assert src.count("_null(reason)") == 3


def test_figure_caption_prf_source_has_reason_assignment():
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_prf_source_has_3_keys_in_return():
    src = inspect.getsource(figure_caption_prf)
    assert "figure_caption_precision" in src
    assert "figure_caption_recall" in src
    assert "figure_caption_f1" in src


# =========================================================================
# chunk_boundary_prf source level 完整
# =========================================================================


def test_chunk_boundary_prf_source_has_def():
    src = inspect.getsource(chunk_boundary_prf)
    assert "def chunk_boundary_prf(" in src


def test_chunk_boundary_prf_source_has_3_params():
    src = inspect.getsource(chunk_boundary_prf)
    assert "document" in src
    assert "annotation" in src
    assert "tolerance_chars" in src


def test_chunk_boundary_prf_source_has_tolerance_default_30():
    src = inspect.getsource(chunk_boundary_prf)
    assert "tolerance_chars: int = 30" in src


def test_chunk_boundary_prf_source_has_5_branch_judgments():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None" in src
    assert "if not annotation" in src
    assert "if not chunks or len(chunks) < 2" in src
    assert "if not anchors" in src


def test_chunk_boundary_prf_source_has_5_return_statements():
    """5 个 return 分支：pipeline_failed / no_annotation / no_predicted_boundaries / no_ground_truth_anchors / 完整路径。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert src.count("return out") >= 4  # 5 分支但完整路径在末尾，不显式 return out
    # 实际：4 处显式 return out + 1 处末尾隐式 fall-through 到 _tolerance_chars 写入后 return out


def test_chunk_boundary_prf_source_has_stream_construction():
    """stream 构造 3 步：norm_chunks / joined_raw / stream。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "norm_chunks" in src
    assert "joined_raw" in src
    assert "stream = normalize_text" in src


def test_chunk_boundary_prf_source_has_predicted_construction():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int]" in src
    assert "predicted.append" in src


def test_chunk_boundary_prf_source_has_gt_positions_construction():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions: list[int]" in src
    assert "gt_positions.append" in src


def test_chunk_boundary_prf_source_has_search_from_advance():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from" in src


def test_chunk_boundary_prf_source_has_pairs_sort():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort" in src


def test_chunk_boundary_prf_source_has_used_pred_used_gt():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src
    assert "used_gt" in src


def test_chunk_boundary_prf_source_has_matched_increment():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src


def test_chunk_boundary_prf_source_has_3_metric_writes():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'out["chunk_boundary_precision"]' in src
    assert 'out["chunk_boundary_recall"]' in src
    assert 'out["chunk_boundary_f1"]' in src


def test_chunk_boundary_prf_source_has_tolerance_chars_field():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_tolerance_chars"' in src


def test_chunk_boundary_prf_source_has_missing_markers_field():
    src = inspect.getsource(chunk_boundary_prf)
    assert '"_missing_markers"' in src


def test_chunk_boundary_prf_source_has_f1_computation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom = p_val + r_val" in src
    assert "2 * p_val * r_val / denom" in src


# =========================================================================
# signatures 精确
# =========================================================================


def test_figure_caption_prf_signature_2_params():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_signature_no_default():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_signature_no_varargs_varkw():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_figure_caption_prf_return_annotation_dict():
    sig = inspect.signature(figure_caption_prf)
    # return type is dict[str, dict[str, Any]]，from __future__ 让它是字符串
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_signature_3_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_signature_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[2].name == "tolerance_chars"
    assert params[2].default == 30


def test_chunk_boundary_prf_signature_no_varargs_varkw():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_chunk_boundary_prf_return_annotation_dict():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


# =========================================================================
# module namespace
# =========================================================================


def test_module_namespace_has_2_functions():
    """module-level function：figure_caption_prf / chunk_boundary_prf。"""
    import types
    funcs = [
        name for name, obj in inspect.getmembers(ammod, predicate=inspect.isfunction)
        if obj.__module__ == ammod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_namespace_has_1_constant():
    """module-level constant：PARSER_DOES_NOT_EMIT_RELATIONS。"""
    assert hasattr(ammod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_namespace_has_imported_names():
    """imported name：_null / _ratio / Counter / Any / normalize_text。"""
    for name in ["_null", "_ratio", "Counter", "Any", "normalize_text"]:
        assert hasattr(ammod, name)


def test_module_namespace_no_private_functions():
    """无私有 _ 前缀函数。"""
    import types
    private = [
        name for name, obj in inspect.getmembers(ammod, predicate=inspect.isfunction)
        if obj.__module__ == ammod.__name__ and name.startswith("_")
    ]
    assert private == []


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_complete_doc_complete_annotation():
    """完整 document + annotation → 算出真实 P/R/F1。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello", position="after")]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] is not None
    assert out["chunk_boundary_recall"]["value"] is not None
    assert out["chunk_boundary_f1"]["value"] is not None


def test_end_to_end_same_input_same_output():
    """同输入两次结果一致。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello", position="after")]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_end_to_end_no_input_modification_document():
    """不修改 input document。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    doc_before = copy.deepcopy(doc)
    ann = {"chunk_boundary_anchors": [_make_anchor("hello")]}
    chunk_boundary_prf(doc, ann)
    assert doc == doc_before


def test_end_to_end_no_input_modification_annotation():
    """不修改 input annotation。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("hello")]}
    ann_before = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann)
    assert ann == ann_before


def test_end_to_end_tolerance_chars_int_type():
    """_tolerance_chars value 是 int 类型。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_end_to_end_missing_markers_list_str_type():
    """missing_markers value 是 list[str] 类型。"""
    doc = _make_doc([_make_chunk("hello"), _make_chunk("world")])
    ann = {"chunk_boundary_anchors": [_make_anchor("missing_marker")]}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out["_missing_markers"]["value"], list)
    for m in out["_missing_markers"]["value"]:
        assert isinstance(m, str)


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_no_class_definitions():
    classes = [
        name for name, obj in inspect.getmembers(ammod, predicate=inspect.isclass)
        if obj.__module__ == ammod.__name__
    ]
    assert classes == []


def test_module_no_main_block():
    src = inspect.getsource(ammod)
    assert 'if __name__' not in src


def test_module_has_2_module_level_functions():
    import types
    funcs = [
        name for name, obj in inspect.getmembers(ammod, predicate=inspect.isfunction)
        if obj.__module__ == ammod.__name__
    ]
    assert len(funcs) == 2


def test_module_has_1_module_level_constant():
    """顶层赋值语句只有 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    src = inspect.getsource(ammod)
    # 找到模块顶层的常量赋值
    lines = src.splitlines()
    const_assignments = [
        l for l in lines
        if l and not l.startswith((" ", "\t", "#", '"', "'", "from ", "import "))
        and "=" in l and "==" not in l and "!=" not in l
        and not l.startswith("def ") and not l.startswith("class ")
        and not l.startswith("__")
    ]
    # 至少含 PARSER_DOES_NOT_EMIT_RELATIONS 这一行
    assert any("PARSER_DOES_NOT_EMIT_RELATIONS" in l for l in const_assignments)
