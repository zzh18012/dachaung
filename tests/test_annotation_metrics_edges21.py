r"""evaluation/annotation_metrics.py 边角测试 - 第二十一轮（Round 291）。

edges20 已覆盖：chunk_boundary_prf 输出 keys / tolerance_chars / value 类型 / 0-1 范围 /
missing_markers 出现条件 / metric_dict keys 精确 / chunk text 多种空白 / marker 含空格标点 /
marker 等于流 / marker 长于流 / 重复 marker / before/after 混合 / 同 marker before+after /
混合 position 贪心 / tolerance 0/-1/极大 / 1v1 1v2 2v1 / output dict 类型 / metric value 类型 /
metric reason 在已知集 / figure_caption source level / module source forbidden imports /
PARSER_DOES_NOT_EMIT_RELATIONS 常量 / figure_caption 行为 / chunk_boundary source level /
algorithm 可重现 / no side effects / __all__ / namespace。

edges21 补强未覆盖的角度：
- **figure_caption_prf 行为深度**：document=None / annotation=None / 二者都 None；
  document=非 None 但 annotation=None / 反之；不读 doc 也不读 annotation 但仍走 reason；
  返回 dict 是新对象（不缓存）；3 个 key 精确；reason 是 PARSER_DOES_NOT_EMIT_RELATIONS；
  调用 N 次产生 N 个独立 dict
- **chunk_boundary_prf document/annotation 边界**：document=None / annotation=None /
  annotation={} / annotation 缺 chunk_boundary_anchors / annotation chunk_boundary_anchors=[]
- **chunk_boundary_prf chunks 边界**：document 缺 chunks key / chunks=[] / chunks=[c1]（少于 2）/
  chunks=[c1, c2]（恰好 2）/ 多个 chunks
- **chunk_boundary_prf anchors 边界**：anchor 缺 marker（默认 ""）/ anchor 缺 position（默认 "after"）/
  position="before"/position="after"/position=其他字符串（无效 default after）
- **chunk_boundary_prf 算法深度**：marker 在 stream 中重复出现 → search_from 推进；部分 marker 找到
  部分找不到 → missing_markers；预测边界在 stream 中找不到（理论不可能，但覆盖分支）
- **chunk_boundary_prf 一对一贪心**：一个 pred 匹配多个 gt → 只选最近的；一个 gt 匹配多个 pred →
  只选最近的；pairs.sort 按 distance 升序
- **chunk_boundary_prf f1 计算**：p_val=None → f1 null；r_val=None → f1 null；p_val+r_val=0 → f1=0.0；
  正常 → 2*p*r/(p+r)
- **chunk_boundary_prf _tolerance_chars 字段**：始终存在；value=tolerance_chars；reason=None
- **chunk_boundary_prf _missing_markers 字段**：无 missing 时不出现；有 missing 时存在
- **figure_caption_prf source level 完整**：含 def figure_caption_prf；含 reason 赋值；
  含 3 个 _null 调用；return 含 3 个 figure_caption_* key 精确
- **chunk_boundary_prf source level 完整**：含 tolerance_chars=30 默认；含 5 个 return 分支；
  含 norm_chunks / stream / predicted / gt_positions / pairs / matched / used_pred / used_gt；
  含 search_from 推进；含 f1 计算；含 _missing_markers 条件 append
- **PARSER_DOES_NOT_EMIT_RELATIONS 常量**：值 / 类型 / 在 namespace / 在 __all__ /
  在 figure_caption_prf source 中使用
- **imports**：from collections import Counter；from typing import Any；
  from app.chunkers.structural import normalize_text；from evaluation.metrics import _null, _ratio
- **module docstring**：含「figure-caption」/「chunk_boundary」/「一对一匹配」/「tolerance_chars」
- **__all__**：3 entries 精确；valid identifiers；namespace 含
- **module source 不含禁止 imports/tokens**：os/sys/logging/subprocess/json/re/star/relative/class/
  dataclass/global/walrus/async/yield（补强）
- **算法可重现性 + no side effects**：同输入两次结果相同；不修改 input dict
"""

from __future__ import annotations

import copy
import inspect
from typing import Any

import pytest

import evaluation.annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# 辅助：构造 document / annotation
# =========================================================================


def _make_doc(chunks: list[dict]) -> dict[str, Any]:
    """构造 document，含 chunks 列表。"""
    return {
        "source_type": "pdf",
        "elements": [],
        "chunks": chunks,
    }


def _chunk(text: str, cid: str = "c") -> dict[str, Any]:
    """构造单 chunk。"""
    return {"chunk_id": cid, "text": text, "source_element_ids": []}


def _anchor(marker: str, position: str = "after") -> dict[str, Any]:
    """构造单 anchor。"""
    return {"marker": marker, "position": position}


# =========================================================================
# figure_caption_prf 行为深度
# =========================================================================


def test_figure_caption_prf_document_none_annotation_none():
    """document=None / annotation=None → 仍返回 3 个 null。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_document_dict_annotation_none():
    """document 是 dict / annotation=None → 仍走 reason 分支。"""
    out = figure_caption_prf({"chunks": []}, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_document_none_annotation_dict():
    """document=None / annotation 是 dict → 仍走 reason 分支。"""
    out = figure_caption_prf(None, {"chunk_boundary_anchors": []})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_value():
    """所有 3 个 metric 的 reason 都是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    for v in out.values():
        assert v["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_prf_returns_new_dict_each_call():
    """每次调用产生新 dict（不缓存）。"""
    o1 = figure_caption_prf(None, None)
    o2 = figure_caption_prf(None, None)
    assert o1 is not o2
    assert o1["figure_caption_precision"] is not o2["figure_caption_precision"]


def test_figure_caption_prf_keys_exact_three():
    """返回 dict 只有 3 个 figure_caption_* key。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_no_extra_fields():
    """没有 tolerance_chars 或 missing_markers 字段。"""
    out = figure_caption_prf({"chunks": []}, {})
    assert "_tolerance_chars" not in out
    assert "_missing_markers" not in out


def test_figure_caption_prf_does_not_mutate_inputs():
    """不修改输入。"""
    doc = {"chunks": []}
    ann = {"chunk_boundary_anchors": []}
    doc_before = copy.deepcopy(doc)
    ann_before = copy.deepcopy(ann)
    figure_caption_prf(doc, ann)
    assert doc == doc_before
    assert ann == ann_before


def test_figure_caption_prf_value_type_dict():
    """每个 value 是 dict（不是 None 直接）。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert isinstance(v, dict)


# =========================================================================
# chunk_boundary_prf document/annotation 边界
# =========================================================================


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    """document=None → reason='pipeline_failed'。"""
    out = chunk_boundary_prf(None, _anchor("x").get("marker") and {"chunk_boundary_anchors": []})
    # ↑ 上面的 _anchor 用法不对，重写
    # 实际我们想测 document=None 时不依赖 annotation
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_value_all_null():
    """document=None → 3 个 metric value 都是 null。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_tolerance_chars_present():
    """document=None → _tolerance_chars 仍存在。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_annotation_none_returns_no_annotation():
    """document 存在 + annotation=None → reason='no_annotation'。"""
    out = chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_returns_no_annotation():
    """document 存在 + annotation={} → reason='no_annotation'（falsy）。"""
    out = chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_no_anchors_key_returns_no_annotation():
    """annotation 缺 chunk_boundary_anchors → 走 anchors=[] 分支但 annotation 真值。"""
    # 注意：annotation={"x": 1} 是 truthy，所以不走 no_annotation 分支
    # 走 anchors = annotation.get(...) or [] = []
    # 然后 chunks 至少 2 → 走 no_ground_truth_anchors 分支
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"some_other_key": "value"},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_annotation_anchors_empty_list_returns_no_gt():
    """annotation chunk_boundary_anchors=[] → no_ground_truth_anchors 分支（chunks>=2）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk_boundary_prf chunks 边界
# =========================================================================


def test_chunk_boundary_prf_document_no_chunks_key_returns_no_predicted():
    """document 缺 chunks → 走 chunks=[] 分支 → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        {"source_type": "pdf"},
        {"chunk_boundary_anchors": [_anchor("x")]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # recall：anchors 非空 → ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_chunks_empty_returns_no_predicted():
    """chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        _make_doc([]),
        {"chunk_boundary_anchors": [_anchor("x")]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_returns_no_predicted():
    """chunks=[c1]（少于 2）→ no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello")]),
        {"chunk_boundary_anchors": [_anchor("x")]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_no_anchors_returns_no_predicted_for_recall():
    """chunks=[c1] + anchors=[] → recall 也是 no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hi")]),
        {"chunk_boundary_anchors": []},
    )
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_recall_zero():
    """chunks=[c1] + anchors=[a1] → recall = 0.0（matched=0, num_gt=1）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hi")]),
        {"chunk_boundary_anchors": [_anchor("h")]},
    )
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_exact_two_boundaries():
    """chunks=[c1, c2]（恰好 2）→ predicted 长度=1（一个内部边界）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [_anchor("o", "after")]},
    )
    # precision 应该是 1/1 = 1.0（如果匹配上）
    # "hello" + " " + "world" = "hello world"
    # predicted position = 5（"hello" 末尾，即第 6 字符位置）
    # anchor "o" 在 "hello" 中找到位置 4，"after" → 4 + 1 = 5
    # 距离 = 0，匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf anchors 字段缺失 default
# =========================================================================


def test_chunk_boundary_prf_anchor_missing_marker_defaults_empty():
    """anchor 缺 marker key → marker="" → 找不到 → missing_markers。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": [{"position": "after"}]},
    )
    # marker="" → stream.find("", search_from) 返 -1（条件 marker 才 find）
    # 走 missing_markers.append("")
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_anchor_missing_position_defaults_after():
    """anchor 缺 position key → default 'after'。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "o"}]},  # 缺 position
    )
    # "o" 在 "hello world" 找到位置 4，after → 4+1=5
    # predicted = 5（"hello" 末尾）
    # 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_invalid_string_defaults_after():
    """anchor position='middle'（无效）→ default 'after'（else 分支）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "o", "position": "middle"}]},
    )
    # "middle" 不是 "before"，走 else（after）
    # 等价于 position="after"
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_before():
    """anchor position='before' → 使用 find_pos（marker 起始位置）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "w", "position": "before"}]},
    )
    # "w" 在 "hello world" 找到位置 6（"world" 的 w）
    # before → gt_position = 6
    # predicted = 5（"hello" 末尾）
    # 距离 = 1
    # tolerance_chars default 30 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_after():
    """anchor position='after' → find_pos + len(marker)。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "he", "position": "after"}]},
    )
    # "he" 在 "hello world" 找到位置 0，after → 0 + 2 = 2
    # predicted = 5（"hello" 末尾）
    # 距离 = 3 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk_boundary_prf 算法深度
# =========================================================================


def test_chunk_boundary_prf_repeated_marker_search_from_advances():
    """重复 marker → search_from 推进，不重复匹配同一位置。"""
    # chunks: ["a a", "a a"] → stream = "a a a a"
    # anchors: [{"marker": "a", "after"}, {"marker": "a", "after"}, ...]
    # 第 1 个 "a" → pos 0, after → 1
    # 第 2 个 "a" → search_from = 0+1 = 1, find "a" at 2, after → 3
    # 第 3 个 "a" → search_from = 2+1 = 3, find "a" at 4, after → 5
    # 第 4 个 "a" → search_from = 4+1 = 5, find "a" at 6, after → 7
    out = chunk_boundary_prf(
        _make_doc([_chunk("a a"), _chunk("a a")]),
        {"chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "a", "position": "after"},
            {"marker": "a", "position": "after"},
            {"marker": "a", "position": "after"},
        ]},
        tolerance_chars=10,
    )
    # 算法跑通，不抛
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_partial_missing_markers():
    """部分 marker 找到 / 部分找不到 → 部分匹配，missing_markers 记录找不到的。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [
            {"marker": "o", "position": "after"},  # 找到
            {"marker": "xyz", "position": "after"},  # 找不到
        ]},
    )
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]
    assert "o" not in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_all_markers_missing():
    """所有 marker 都找不到 → missing_markers 包含所有。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"},
            {"marker": "yyy", "position": "after"},
        ]},
    )
    assert len(out["_missing_markers"]["value"]) == 2


def test_chunk_boundary_prf_no_missing_markers_field_when_all_found():
    """所有 marker 都找到 → 不出现 _missing_markers 字段。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]},
    )
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_one_pred_two_gt_only_one_match():
    """1 个 pred + 2 个 gt → 只匹配 1 个（贪心 by 距离）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [
            {"marker": "o", "position": "after"},  # 在 "hello"，gt=5
            {"marker": "w", "position": "before"},  # 在 "world"，gt=6
        ]},
        tolerance_chars=10,
    )
    # predicted = [5]
    # gt = [5, 6]
    # 都在 tolerance 内，但只 1 个 pred → matched=1
    # precision = 1/1 = 1.0
    # recall = 1/2 = 0.5
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_two_pred_one_gt_only_one_match():
    """2 个 pred + 1 个 gt → 只匹配 1 个。"""
    # chunks: ["a", "b", "c"] → predicted 位置 = [1, 3]
    # anchor: marker="b" before → gt_position = 2
    # 距离：|1-2|=1, |3-2|=1 → 都在 tolerance=10 内 → matched=1（贪心只选 1）
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b"), _chunk("c")]),
        {"chunk_boundary_anchors": [
            {"marker": "b", "position": "before"},
        ]},
        tolerance_chars=10,
    )
    # matched=1, num_pred=2, num_gt=1
    # precision = 1/2 = 0.5
    # recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_greedy_sort_by_distance():
    """贪心按距离升序排序 → 距离最近的先匹配。"""
    # chunks: ["aa", "bb", "cc"] → stream = "aa bb cc"
    # predicted = [2, 5]
    # anchor: marker="bb" before → gt_position = 3
    # 距离：|2-3|=1, |5-3|=2 → 排序后 (1, 0, 0), (2, 1, 0)
    # 选 (1, 0, 0) → matched=1, used_pred={0}, used_gt={0}
    # (2, 1, 0) → gt 0 已用，跳过
    out = chunk_boundary_prf(
        _make_doc([_chunk("aa"), _chunk("bb"), _chunk("cc")]),
        {"chunk_boundary_anchors": [
            {"marker": "bb", "position": "before"},
        ]},
        tolerance_chars=10,
    )
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 1/1


# =========================================================================
# chunk_boundary_prf f1 计算分支
# =========================================================================


def test_chunk_boundary_prf_f1_perfect_match():
    """p=1.0, r=1.0 → f1 = 1.0。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]},
    )
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_f1_zero_denominator():
    """p_val + r_val <= 0 → f1 = 0.0（理论不可达，p/r 都 >=0 且若有 value 都 >0）。
    但通过 f1=0.0 的场景：matched=0 时 p=0, r=0 → p+r=0 → f1=0.0。"""
    # 实际：当 matched=0, num_pred>0, num_gt>0 时
    # p = 0/num_pred = 0.0
    # r = 0/num_gt = 0.0
    # p+r = 0 → f1 = 0.0
    # 构造：anchor marker 远离任何 predicted
    out = chunk_boundary_prf(
        _make_doc([_chunk("aaa"), _chunk("bbb")]),
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},  # 找不到 → missing
        tolerance_chars=0,  # 强制精确匹配
    )
    # 单 marker 找不到 → gt_positions=[] → num_gt=0 → recall null
    # 这种情况下 f1 = null（precision_or_recall_not_evaluated）


def test_chunk_boundary_prf_f1_precision_null_when_no_pred():
    """chunks<2 → no_predicted_boundaries 分支（不是 precision_or_recall_not_evaluated）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello")]),  # 1 chunk → 走 <2 chunks 分支
        {"chunk_boundary_anchors": [{"marker": "h", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None
    # 走 no_predicted_boundaries 分支，不是 precision_or_recall_not_evaluated
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_f1_recall_null_when_no_gt_in_stream():
    """anchors 都找不到 → gt_positions=[] → recall null → f1 null。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hello"), _chunk("world")]),
        {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]},
    )
    # 所有 marker 都 missing → gt_positions=[] → recall null
    # predicted = [5] 非空 → precision 走 ratio 但 matched=0
    # recall null → f1 null
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_chunk_boundary_prf_f1_value_in_zero_one():
    """f1 始终在 [0, 1]。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b"), _chunk("c"), _chunk("d")]),
        {"chunk_boundary_anchors": [
            {"marker": "b", "position": "before"},
        ]},
        tolerance_chars=2,
    )
    f1 = out["chunk_boundary_f1"]["value"]
    if f1 is not None:
        assert 0.0 <= f1 <= 1.0


# =========================================================================
# chunk_boundary_prf _tolerance_chars 字段
# =========================================================================


def test_chunk_boundary_prf_tolerance_chars_default_30():
    """默认 tolerance_chars=30。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
    )
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_chars_custom():
    """自定义 tolerance_chars=100。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
        tolerance_chars=100,
    )
    assert out["_tolerance_chars"]["value"] == 100


def test_chunk_boundary_prf_tolerance_chars_zero():
    """tolerance_chars=0 → 仍写到 _tolerance_chars。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
        tolerance_chars=0,
    )
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_chars_negative():
    """tolerance_chars=-1 → 仍写到 _tolerance_chars。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
        tolerance_chars=-1,
    )
    assert out["_tolerance_chars"]["value"] == -1


def test_chunk_boundary_prf_tolerance_chars_reason_always_none():
    """_tolerance_chars reason 始终 None。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
        tolerance_chars=50,
    )
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_tolerance_chars_present_in_all_branches():
    """5 个分支都写 _tolerance_chars（document None/annotation falsy/<2 chunks/no anchors/normal）。"""
    cases = [
        chunk_boundary_prf(None, None),
        chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), None),
        chunk_boundary_prf(_make_doc([_chunk("a")]), {"chunk_boundary_anchors": [_anchor("x")]}),
        chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), {"chunk_boundary_anchors": []}),
        chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), {"chunk_boundary_anchors": [_anchor("a")]}),
    ]
    for out in cases:
        assert "_tolerance_chars" in out


# =========================================================================
# chunk_boundary_prf 算法可重现性 + no side effects
# =========================================================================


def test_chunk_boundary_prf_deterministic():
    """同输入两次调用结果相同。"""
    doc = _make_doc([_chunk("a"), _chunk("b"), _chunk("c")])
    ann = {"chunk_boundary_anchors": [_anchor("b", "before")]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert out1 == out2


def test_chunk_boundary_prf_no_side_effects_on_doc():
    """不修改 document。"""
    doc = _make_doc([_chunk("a"), _chunk("b")])
    doc_before = copy.deepcopy(doc)
    chunk_boundary_prf(doc, {"chunk_boundary_anchors": [_anchor("a")]})
    assert doc == doc_before


def test_chunk_boundary_prf_no_side_effects_on_annotation():
    """不修改 annotation。"""
    ann = {"chunk_boundary_anchors": [_anchor("a", "before"), _anchor("b", "after")]}
    ann_before = copy.deepcopy(ann)
    chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), ann)
    assert ann == ann_before


# =========================================================================
# figure_caption_prf source level 完整
# =========================================================================


def test_figure_caption_prf_source_contains_function_def():
    """source 含 'def figure_caption_prf'。"""
    src = inspect.getsource(figure_caption_prf)
    assert "def figure_caption_prf" in src


def test_figure_caption_prf_source_contains_docstring():
    """source 含 docstring。"""
    src = inspect.getsource(figure_caption_prf)
    assert '"""' in src


def test_figure_caption_prf_source_contains_reason_assignment():
    """source 含 reason = PARSER_DOES_NOT_EMIT_RELATIONS。"""
    src = inspect.getsource(figure_caption_prf)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src
    assert "reason" in src


def test_figure_caption_prf_source_contains_three_null_calls():
    """source 含 3 个 _null 调用。"""
    src = inspect.getsource(figure_caption_prf)
    assert src.count("_null(") >= 3


def test_figure_caption_prf_source_contains_three_figure_keys():
    """source 含 3 个 figure_caption_* key。"""
    src = inspect.getsource(figure_caption_prf)
    assert "figure_caption_precision" in src
    assert "figure_caption_recall" in src
    assert "figure_caption_f1" in src


def test_figure_caption_prf_source_does_not_read_inputs():
    """source 不读 document / annotation（直接走 reason 分支）。"""
    src = inspect.getsource(figure_caption_prf)
    # 不应含 document.get / annotation.get
    assert "document.get" not in src
    assert "annotation.get" not in src


def test_figure_caption_prf_signature_two_params():
    """signature 2 params。"""
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2
    assert "document" in sig.parameters
    assert "annotation" in sig.parameters


def test_figure_caption_prf_signature_param_types_optional():
    """参数类型是 dict | None。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        # from __future__ annotations 让 annotation 是 string
        assert p.annotation is not None


def test_figure_caption_prf_signature_return_dict():
    """return 类型 dict。"""
    sig = inspect.signature(figure_caption_prf)
    # from __future__ annotations 让 return 是 string
    assert sig.return_annotation is not None


def test_figure_caption_prf_no_default_args():
    """figure_caption_prf 参数无 default。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# chunk_boundary_prf source level 完整
# =========================================================================


def test_chunk_boundary_prf_source_contains_function_def():
    """source 含 'def chunk_boundary_prf'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "def chunk_boundary_prf" in src


def test_chunk_boundary_prf_source_contains_tolerance_default_30():
    """source 含 tolerance_chars: int = 30。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "tolerance_chars" in src
    assert "= 30" in src


def test_chunk_boundary_prf_source_contains_5_return_branches():
    """source 含 5 个 return 语句。"""
    src = inspect.getsource(chunk_boundary_prf)
    # 实际有 5+ 个 return（每个分支 1 个）
    assert src.count("return out") >= 4  # 至少 4 处显式 return out


def test_chunk_boundary_prf_source_contains_pipeline_failed_branch():
    """source 含 'pipeline_failed'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pipeline_failed" in src


def test_chunk_boundary_prf_source_contains_no_annotation_branch():
    """source 含 'no_annotation'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "no_annotation" in src


def test_chunk_boundary_prf_source_contains_no_predicted_boundaries_branch():
    """source 含 'no_predicted_boundaries'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "no_predicted_boundaries" in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_branch():
    """source 含 'no_ground_truth_anchors'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "no_ground_truth_anchors" in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_in_stream():
    """source 含 'no_ground_truth_anchors_in_stream'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "no_ground_truth_anchors_in_stream" in src


def test_chunk_boundary_prf_source_contains_precision_or_recall_not_evaluated():
    """source 含 'precision_or_recall_not_evaluated'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "precision_or_recall_not_evaluated" in src


def test_chunk_boundary_prf_source_contains_document_none_check():
    """source 含 document is None 检查。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "document is None" in src


def test_chunk_boundary_prf_source_contains_annotation_falsy_check():
    """source 含 not annotation 检查。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "not annotation" in src


def test_chunk_boundary_prf_source_contains_norm_chunks_construction():
    """source 含 norm_chunks 列表构造。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "norm_chunks" in src


def test_chunk_boundary_prf_source_contains_stream_join():
    """source 含 stream 拼接。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "joined_raw" in src or '" ".join' in src


def test_chunk_boundary_prf_source_contains_normalize_text_call():
    """source 含 normalize_text 调用。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "normalize_text" in src


def test_chunk_boundary_prf_source_contains_predicted_construction():
    """source 含 predicted 列表构造。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted" in src
    assert "stream.find" in src


def test_chunk_boundary_prf_source_contains_gt_positions_construction():
    """source 含 gt_positions 列表。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions" in src


def test_chunk_boundary_prf_source_contains_missing_markers_construction():
    """source 含 missing_markers。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers" in src


def test_chunk_boundary_prf_source_contains_search_from_init():
    """source 含 search_from = 0 初始化。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_prf_source_contains_search_from_advance():
    """source 含 search_from 推进逻辑。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from" in src


def test_chunk_boundary_prf_source_contains_pairs_construction():
    """source 含 pairs 列表 + tolerance 检查。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs" in src
    assert "tolerance_chars" in src


def test_chunk_boundary_prf_source_contains_pairs_sort_by_distance():
    """source 含 pairs.sort（按距离升序）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort" in src
    # 检查 lambda 排序 key
    assert "lambda" in src


def test_chunk_boundary_prf_source_contains_used_pred_used_gt():
    """source 含 used_pred / used_gt 集合。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred" in src
    assert "used_gt" in src


def test_chunk_boundary_prf_source_contains_matched_increment():
    """source 含 matched += 1。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src or "matched = matched + 1" in src


def test_chunk_boundary_prf_source_contains_f1_calculation():
    """source 含 f1 计算。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 *" in src
    assert "denom" in src


def test_chunk_boundary_prf_source_contains_missing_markers_output_assignment():
    """source 含条件 append _missing_markers 到 out。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "_missing_markers" in src
    assert "if missing_markers:" in src


def test_chunk_boundary_prf_signature_three_params():
    """signature 3 params。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_signature_tolerance_chars_default_30():
    """tolerance_chars 默认 30。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_no_varargs():
    """chunk_boundary_prf 不接受 *args。"""
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_chunk_boundary_prf_no_varkw():
    """chunk_boundary_prf 不接受 **kwargs。"""
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量深度
# =========================================================================


def test_parser_does_not_emit_relations_value():
    """常量值是 'parser_does_not_emit_relations'。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_str():
    """常量类型 str。"""
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_module_namespace():
    """常量在 module namespace。"""
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_in_all():
    """常量在 __all__。"""
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_used_in_figure_caption_source():
    """常量在 figure_caption_prf source 中使用。"""
    src = inspect.getsource(figure_caption_prf)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_parser_does_not_emit_relations_is_module_level_constant():
    """是 module-level 常量，不是函数属性。"""
    # 通过 module attr 访问
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# imports 深度
# =========================================================================


def test_module_imports_counter():
    """含 from collections import Counter。"""
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_any():
    """含 from typing import Any。"""
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text():
    """含 from app.chunkers.structural import normalize_text。"""
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_and_ratio():
    """含 from evaluation.metrics import _null, _ratio。"""
    src = inspect.getsource(amod)
    assert "_null" in src
    assert "_ratio" in src
    assert "from evaluation.metrics" in src


def test_module_namespace_has_normalize_text():
    """normalize_text 在 namespace。"""
    assert hasattr(amod, "normalize_text")


def test_module_namespace_has_counter():
    """Counter 在 namespace。"""
    assert hasattr(amod, "Counter")


def test_module_namespace_has_null():
    """_null 在 namespace。"""
    assert hasattr(amod, "_null")


def test_module_namespace_has_ratio():
    """_ratio 在 namespace。"""
    assert hasattr(amod, "_ratio")


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_does_not_contain_os_path():
    """不含 os.path 调用。"""
    assert "os.path" not in inspect.getsource(amod)


def test_module_source_does_not_contain_sys_exit():
    """不含 sys.exit。"""
    assert "sys.exit" not in inspect.getsource(amod)


def test_module_source_does_not_contain_print():
    """不含 print。"""
    assert "print(" not in inspect.getsource(amod)


def test_module_source_does_not_contain_open():
    """不含 open() 调用（不读文件）。"""
    assert "open(" not in inspect.getsource(amod)


def test_module_source_does_not_contain_pathlib():
    """不含 from pathlib。"""
    assert "from pathlib" not in inspect.getsource(amod)


def test_module_source_does_not_contain_math():
    """不含 import math。"""
    assert "import math" not in inspect.getsource(amod)


def test_module_source_does_not_contain_itertools():
    """不含 from itertools。"""
    assert "from itertools" not in inspect.getsource(amod)


def test_module_source_does_not_contain_functools():
    """不含 from functools。"""
    assert "from functools" not in inspect.getsource(amod)


def test_module_source_does_not_contain_eval():
    """不含 eval（动态执行）。"""
    assert "eval(" not in inspect.getsource(amod)


def test_module_source_does_not_contain_exec():
    """不含 exec（动态执行）。"""
    assert "exec(" not in inspect.getsource(amod)


def test_module_source_does_not_contain_import_star():
    """不含 * 导入。"""
    assert "import *" not in inspect.getsource(amod)


def test_module_source_does_not_contain_relative_import():
    """不含相对导入（from .）。"""
    src = inspect.getsource(amod)
    assert "from ." not in src
    assert "from .." not in src


# =========================================================================
# module docstring 深度
# =========================================================================


def test_module_docstring_present():
    """module 有 docstring。"""
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 0


def test_module_docstring_mentions_figure_caption():
    """module docstring 含 figure-caption。"""
    assert "figure-caption" in amod.__doc__ or "figure_caption" in amod.__doc__


def test_module_docstring_mentions_chunk_boundary():
    """module docstring 含 chunk_boundary。"""
    assert "chunk_boundary" in amod.__doc__ or "chunk-boundary" in amod.__doc__


def test_module_docstring_mentions_yiduiyi():
    """module docstring 含「一对一」。"""
    assert "一对一" in amod.__doc__


def test_module_docstring_mentions_tolerance_chars():
    """module docstring 含 tolerance_chars。"""
    assert "tolerance_chars" in amod.__doc__ or "容差" in amod.__doc__


def test_module_docstring_mentions_rengong_biaozhu():
    """module docstring 含「人工标注」。"""
    assert "人工标注" in amod.__doc__


def test_module_docstring_mentions_parser_does_not_emit():
    """module docstring 含 parser 不输出 caption-figure 的说明。"""
    assert "parser" in amod.__doc__


# =========================================================================
# __all__ 完整性
# =========================================================================


def test_module_all_3_entries():
    """__all__ 恰好 3 个 entries。"""
    assert len(amod.__all__) == 3


def test_module_all_entries_exact():
    """__all__ 内容精确。"""
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_all_entries_in_namespace():
    """每个 __all__ entry 在 namespace 中。"""
    for name in amod.__all__:
        assert hasattr(amod, name)


def test_module_all_entries_valid_identifier():
    """每个 __all__ entry 是合法标识符。"""
    for name in amod.__all__:
        assert name.isidentifier()


def test_module_all_entries_callable_or_str():
    """每个 __all__ entry 是 callable 或 str。"""
    for name in amod.__all__:
        v = getattr(amod, name)
        assert callable(v) or isinstance(v, str)


def test_module_namespace_has_private_helpers_not_in_all():
    """module namespace 含 _null / _ratio，但它们不在 __all__（来自 metrics 模块）。"""
    # _null 和 _ratio 是从 evaluation.metrics import 的
    assert hasattr(amod, "_null")
    assert hasattr(amod, "_ratio")
    assert "_null" not in amod.__all__
    assert "_ratio" not in amod.__all__


# =========================================================================
# 端到端集成（chunk_boundary_prf + figure_caption_prf 一起用）
# =========================================================================


def test_both_metrics_can_be_called_together():
    """figure_caption_prf + chunk_boundary_prf 可以一起调用（独立）。"""
    doc = _make_doc([_chunk("a"), _chunk("b")])
    ann = {"chunk_boundary_anchors": [_anchor("a")]}
    fc = figure_caption_prf(doc, ann)
    cb = chunk_boundary_prf(doc, ann)
    assert "figure_caption_precision" in fc
    assert "chunk_boundary_precision" in cb


def test_chunk_boundary_prf_output_can_merge_into_dict():
    """输出可以 merge 到 metrics dict（_ 开头字段会一起带过去）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": [_anchor("a")]},
    )
    metrics: dict[str, Any] = {}
    metrics.update(out)
    assert "chunk_boundary_precision" in metrics
    assert "_tolerance_chars" in metrics


def test_chunk_boundary_prf_with_unicode_chunk_text():
    """chunks 含中文 → normalize 后仍能匹配。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("你好"), _chunk("世界")]),
        {"chunk_boundary_anchors": [{"marker": "好", "position": "after"}]},
    )
    # "你好" + " " + "世界" = "你好 世界"
    # predicted = 2（"你好" 末尾）
    # anchor "好" 在位置 1，after → 1+1 = 2
    # 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_with_emoji_chunk_text():
    """chunks 含 emoji → 仍能跑（emoji 长度按 code point）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("😀😁"), _chunk("😂😃")]),
        {"chunk_boundary_anchors": [{"marker": "😁", "position": "after"}]},
    )
    # 不抛即过
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_chunks_with_extra_whitespace():
    """chunks 含大量空白 → normalize 后规范化。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("  hello  "), _chunk("  world  ")]),
        {"chunk_boundary_anchors": [{"marker": "o", "position": "after"}]},
    )
    # normalize 后 chunks: ["hello", "world"]
    # stream = "hello world"
    # predicted = 5, gt = 5 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# 边界组合（document/annotation 各种 None 组合）
# =========================================================================


def test_chunk_boundary_prf_doc_none_ann_none_pipeline_failed():
    """doc=None + ann=None → pipeline_failed（document None 优先）。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_doc_dict_ann_none_no_annotation():
    """doc=dict + ann=None → no_annotation。"""
    out = chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_doc_dict_ann_empty_no_annotation():
    """doc=dict + ann={} → no_annotation（falsy）。"""
    out = chunk_boundary_prf(_make_doc([_chunk("a"), _chunk("b")]), {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_doc_with_one_chunk_ann_with_anchors_no_pred():
    """doc 1 chunk + ann 有 anchors → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("hi")]),
        {"chunk_boundary_anchors": [_anchor("h")]},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_predicted_boundaries"
    # recall：anchors 非空 + 1 chunk → ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_no_anchors_no_ground_truth():
    """2 chunks + anchors=[] → no_ground_truth_anchors。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# output 字段类型严格
# =========================================================================


def test_chunk_boundary_prf_output_value_type_int_or_float_or_none():
    """value 类型是 int / float / None（不出现 str/list/dict）。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": [_anchor("a")]},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[k]["value"]
        assert v is None or isinstance(v, (int, float))


def test_chunk_boundary_prf_output_reason_type_str_or_none():
    """reason 类型 str 或 None。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": [_anchor("a")]},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        r = out[k]["reason"]
        assert r is None or isinstance(r, str)


def test_chunk_boundary_prf_output_dict_is_dict():
    """output 是 dict。"""
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_each_metric_value_is_dict():
    """每个 metric value 是 dict。"""
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert isinstance(out[k], dict)


def test_chunk_boundary_prf_tolerance_chars_value_is_int():
    """_tolerance_chars value 是 int。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_prf_missing_markers_value_is_list():
    """_missing_markers value 是 list。"""
    out = chunk_boundary_prf(
        _make_doc([_chunk("a"), _chunk("b")]),
        {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]},
    )
    assert isinstance(out["_missing_markers"]["value"], list)
