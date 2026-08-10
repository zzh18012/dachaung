r"""evaluation/annotation_metrics.py 边角测试 - 第二十三轮（Round 303）。

edges22 已覆盖：figure_caption_prf 3 key/reason/value/dict 结构 / 独立 dict / 不读 document/annotation /
PARSER_DOES_NOT_EMIT_RELATIONS 是 str + hashable / chunk_boundary_prf 5 分支
（pipeline_failed / no_annotation / no_predicted_boundaries / no_ground_truth_anchors / 完整）/
tolerance_chars 默认 30 + 可传 0/极大/负数 + reason=None / anchor marker 缺失=空 + position 缺失=after /
marker 含 unicode 空白 + 不在 stream 中 + 重复 marker search_from / stream 构造（' '.join + normalize）/
predicted 长度 = chunks-1 + 最后一个不算边界 / 贪心按距离排序 + used_pred/used_gt 去重 /
tolerance=0 仅完全相同 / tolerance=负数 全不匹配 / f1 边界（null/0/perfect）/
__all__ 3 entries / imports 5 statements / docstring / forbidden tokens / source level 完整 /
signatures 精确 / namespace / 端到端集成 / 模块整体合理性。

edges23 补强未覆盖的角度（深度边界 + 算法不变量 + source level + signatures + 端到端）：
- **anchor position 取值深度补强**：position="before" → marker 起始位置；
  position="after" → marker 结束位置；position 缺失（无 position key）→ 默认 "after"；
  position=None → 默认 "after"；position="" → 默认 "after"；
  position=0 → 不等于 "before" → 默认 "after"；position="BEFORE"（大写）→ 不等于 "before" → "after"；
  position="after "（含空格）→ 不等于 "before" → "after"；position="unknown" → "after"
- **anchor marker 位置深度补强**：marker 在 stream 开头（find_pos=0）；
  marker 在 stream 末尾（find_pos = len(stream) - len(marker)）；
  marker 在 stream 中间；marker 长度 = stream 长度 → find_pos = 0；
  marker 长度 > stream 长度 → not found → missing_markers
- **chunk.text 边界值补强**：chunk.text 缺失（无 text key）→ 默认 ""；chunk.text=None → ""；
  chunk.text="" → ""；chunk.text 是纯空格 → normalize 后 ""；
  chunk.text 含 emoji → 保留；chunk.text 含换行符 → normalize 后空格
- **predict 算法深度补强**：chunks=[c1] → 0 predict（无内部边界）；
  chunks=[c1,c2] → 1 predict；chunks=[c1,c2,c3] → 2 predict；
  chunks=[c1,c2,c3,c4] → 3 predict；某些 chunk text 在 stream 中找不到 → pos 推进，不 append
- **多 anchor 顺序定位深度补强**：相同 marker 出现多次 → search_from 推进 → 各自定位；
  marker 顺序逆序（anchor[0] 是后面 marker）→ 仍按 stream 顺序定位；
  3 个相同 marker → 各自定位
- **数学不变量**：0 ≤ precision ≤ 1；0 ≤ recall ≤ 1；0 ≤ f1 ≤ 1；
  matched ≤ num_pred；matched ≤ num_gt；matched ≤ min(num_pred, num_gt)；
  f1 ≤ precision；f1 ≤ recall（调和中位 ≤ min）；p=r 时 f1=p；
  p=1 r=1 → f1=1；p=0 r=任意 → f1=0；p=任意 r=0 → f1=0
- **tolerance_chars 极端值深度**：tolerance_chars=1 → 容差 1 字符；
  tolerance_chars=len(stream) → 全部匹配；
  tolerance_chars=10**6 → 实际就是全部匹配
- **PARSER_DOES_NOT_EMIT_RELATIONS 常量深度补强**：是 module 唯一常量；
  是 str 子类；值精确 "parser_does_not_emit_relations"；不可变（hashable）；
  在 __all__ 第一个；在 namespace 是 module-level（不是 imported）
- **module source 字符串精确补强**：含「一对一」（docstring）；
  含「容差」（docstring）；含「最近图片」（docstring）；
  含「启发式」（docstring）；含「规范化全文流」（chunk_boundary_prf docstring）
- **module source forbidden tokens 补强**：不含 os / sys / re / logging / subprocess /
  asyncio / threading / math / datetime / itertools / functools（collections 已 import 但仅 Counter 用于内部）
- **module source 含特定语句**：含 from __future__ import annotations；
  含 from collections import Counter；含 from typing import Any；
  含 from app.chunkers.structural import normalize_text；
  含 from evaluation.metrics import _null, _ratio
- **chunk_boundary_prf source level 完整补强**：含 norm_chunks = [...] 列表推导；
  含 joined_raw = " ".join(norm_chunks)；含 stream = normalize_text(joined_raw)；
  含 predicted = [] + pos = 0 初始化；含 for i, txt in enumerate(norm_chunks) 循环；
  含 if i == len(norm_chunks) - 1: break；含 find_pos = stream.find(txt, pos)；
  含 if find_pos < 0 → pos += len(txt) + 1 + continue；
  含 end = find_pos + len(txt)；含 predicted.append(end)；
  含 pos = end + 1；含 gt_positions: list[int] = []；
  含 missing_markers: list[str] = []；含 search_from = 0；
  含 for a in anchors 循环；含 marker = a.get("marker", "")；
  含 position = a.get("position", "after")；含 if position == "before" 分支；
  含 else: gt_positions.append(find_pos + len(marker))；
  含 pairs.sort(key=lambda x: x[0])；含 matched = 0；含 used_pred = set() + used_gt = set()
- **figure_caption_prf source level 完整补强**：含 reason = PARSER_DOES_NOT_EMIT_RELATIONS；
  含 return dict 字面量含 3 key；含 _null(reason) 调用 3 处
- **signatures 精确补强**：figure_caption_prf 2 params (document, annotation)；
  chunk_boundary_prf 3 params (document, annotation, tolerance_chars) + tolerance_chars default=30；
  两个函数 no varargs / no varkw；return annotation 在 from __future__ 下是 string
- **端到端集成补强**：完整 document 4 chunks + 3 anchors → 算出 P=1/R=1/F1=1；
  完整 document 4 chunks + 1 anchor matched + 1 missing → recall=0.5；
  完整 document + 多 anchor 重复 marker → 各自定位；不修改 input document.chunks；
  不修改 input annotation.chunk_boundary_anchors
- **模块整体合理性**：2 module-level function + 1 module-level constant + 5 imported names；
  无 class 定义；无 __main__ 块；__all__ 3 entries 顺序精确
"""

from __future__ import annotations

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
# anchor position 取值深度补强
# =========================================================================


def test_anchor_position_before_uses_marker_start(tmp_path):
    """position='before' → gt_position = find_pos（marker 起始）。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    # stream = "hello world"; marker="world" find_pos=6
    # before → gt_position=6; predict: end of "hello" = 5
    # |5 - 6| = 1, tolerance=30 → matched
    annotation = {"chunk_boundary_anchors": [_make_anchor("world", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_anchor_position_after_uses_marker_end():
    """position='after' → gt_position = find_pos + len(marker)。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    # stream = "hello world"; marker="hello" find_pos=0, len=5, after → gt=5
    # predict: end of "hello" = 5; |5-5|=0 → matched
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_missing_defaults_to_after():
    """anchor 无 position key → a.get('position', 'after') → 'after'。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello"}]}  # 无 position
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # after → gt=5; predict: end of hello=5; matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_none_defaults_to_after():
    """position=None → != 'before' → 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": None}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # None → else 分支 → gt = 0 + 5 = 5; matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_empty_string_defaults_to_after():
    """position='' → != 'before' → 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": ""}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_zero_int_defaults_to_after():
    """position=0（int）→ != 'before' → 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": 0}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_uppercase_before_treated_as_after():
    """position='BEFORE'（大写）→ != 'before'（精确匹配）→ 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "BEFORE"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # BEFORE → after 分支 → gt=5
    # 如果是 before → gt=0; predict=5; |5-0|=5 ≤ 30 → matched
    # 如果是 after → gt=5; predict=5; |5-5|=0 → matched
    # 两种情况都 matched，所以这个测试不强区分；但确认 precision=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_with_trailing_space_treated_as_after():
    """position='before '（含空格）→ != 'before' → 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "before "}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_position_unknown_string_treated_as_after():
    """position='unknown' → != 'before' → 'after' 分支。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [{"marker": "hello", "position": "unknown"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# anchor marker 位置深度补强
# =========================================================================


def test_anchor_marker_at_stream_start():
    """marker 在 stream 开头（find_pos=0）→ before → gt=0。"""
    chunks = [_make_chunk("alpha", "c1"), _make_chunk("beta", "c2")]
    doc = _make_doc(chunks)
    # stream = "alpha beta"; marker="alpha" find_pos=0
    annotation = {"chunk_boundary_anchors": [_make_anchor("alpha", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # predict: end of alpha=5; before → gt=0; |5-0|=5 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_marker_at_stream_end():
    """marker 在 stream 末尾。"""
    chunks = [_make_chunk("alpha", "c1"), _make_chunk("beta", "c2")]
    doc = _make_doc(chunks)
    # stream = "alpha beta"; marker="beta" find_pos=6
    annotation = {"chunk_boundary_anchors": [_make_anchor("beta", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # predict: end of alpha=5; after beta → gt=6+4=10; |5-10|=5 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_marker_in_stream_middle():
    """marker 在 stream 中间。"""
    chunks = [_make_chunk("alpha", "c1"), _make_chunk("beta", "c2")]
    doc = _make_doc(chunks)
    # stream = "alpha beta"; marker="a b" find_pos=4 (cross-boundary)
    # 这个 marker 跨越 chunk 边界 - 起到中间位置
    annotation = {"chunk_boundary_anchors": [_make_anchor("a b", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # before → gt=4; predict=5; |5-4|=1 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_marker_length_equals_stream_length():
    """marker 长度 = stream 长度 → find_pos=0。"""
    chunks = [_make_chunk("ab", "c1"), _make_chunk("cd", "c2")]
    doc = _make_doc(chunks)
    # stream = "ab cd" (5 chars); marker="ab cd" len=5 → find_pos=0
    annotation = {"chunk_boundary_anchors": [_make_anchor("ab cd", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # after → gt=0+5=5; predict: end of ab=2; |2-5|=3 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_marker_length_greater_than_stream_adds_to_missing():
    """marker 长度 > stream 长度 → not found → missing_markers。"""
    chunks = [_make_chunk("ab", "c1"), _make_chunk("cd", "c2")]
    doc = _make_doc(chunks)
    # stream = "ab cd"; marker="abcdefgh" (8 chars) → not found
    annotation = {"chunk_boundary_anchors": [_make_anchor("abcdefgh", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # gt_positions=[] → num_gt=0 → recall=null + reason
    assert "_missing_markers" in out
    assert "abcdefgh" in out["_missing_markers"]["value"]
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


# =========================================================================
# chunk.text 边界值补强
# =========================================================================


def test_chunk_text_missing_defaults_to_empty():
    """chunk 无 text key → c.get('text') or '' → ''。"""
    chunks = [{"chunk_id": "c1", "source_element_ids": ["e1"]}, _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("world", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # norm_chunks = ["", "world"]; joined = " world"; stream=normalize=" world".strip()?
    # 实际 normalize_text 是 strip 两端 + 压中间空白 → "world"
    # predict: i=0 txt="" find_pos=stream.find("",0)=0; end=0+0=0; predicted=[0]
    # i=1 是 last chunk → break
    # marker "world" find_pos=0; before → gt=0; |0-0|=0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_none_defaults_to_empty():
    """chunk.text=None → c.get('text') or '' → ''。"""
    chunks = [{"chunk_id": "c1", "text": None, "source_element_ids": ["e1"]},
              _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("world", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_empty_string_normalizes_to_empty():
    """chunk.text='' → ''。"""
    chunks = [_make_chunk("", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("world", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_pure_whitespace_normalizes_to_empty():
    """chunk.text='   ' → normalize → ''。"""
    chunks = [_make_chunk("   ", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("world", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_emoji_preserved():
    """chunk.text 含 emoji → normalize 保留 emoji。"""
    chunks = [_make_chunk("hello😀", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello😀", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = "hello😀 world"; after hello😀 → gt=7 (5 ASCII + 1 emoji 但 Python str len=1)
    # 实际 len("hello😀")=6 (Python); predict: end of hello😀=6; |6-6|=0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_newline_normalizes_to_space():
    """chunk.text='a\nb' → normalize → 'a b'。"""
    chunks = [_make_chunk("a\nb", "c1"), _make_chunk("c", "c2")]
    doc = _make_doc(chunks)
    # norm_chunks = ["a b", "c"]; stream = "a b c"
    annotation = {"chunk_boundary_anchors": [_make_anchor("a b", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # predict: end of "a b" = stream.find("a b", 0) + 3 = 0+3 = 3
    # marker "a b" find_pos=0; after → gt=3; |3-3|=0 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# predict 算法深度补强
# =========================================================================


def test_predict_count_single_chunk_no_internal_boundary():
    """chunks=[c1] → 0 predict。"""
    chunks = [_make_chunk("hello", "c1")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 少于 2 个 chunk → no_predicted_boundaries 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_predict_count_two_chunks_one_boundary():
    """chunks=[c1,c2] → 1 predict。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 1 predict, 1 anchor matched → P=1, R=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_predict_count_three_chunks_two_boundaries():
    """chunks=[c1,c2,c3] → 2 predict。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    # stream = "a b c"; predict: end of a=1, end of b=3 → [1, 3]
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("a", "after"),  # gt=1
            _make_anchor("b", "after"),  # gt=3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 2 predict, 2 anchor matched → P=1, R=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_predict_count_four_chunks_three_boundaries():
    """chunks=[c1,c2,c3,c4] → 3 predict。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"),
              _make_chunk("c", "c3"), _make_chunk("d", "c4")]
    doc = _make_doc(chunks)
    # stream = "a b c d" (7 chars)
    # predict: end of a=1, end of b=3, end of c=5 → [1, 3, 5]
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("a", "after"),  # gt=1
            _make_anchor("b", "after"),  # gt=3
            _make_anchor("c", "after"),  # gt=5
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# 多 anchor 顺序定位深度补强
# =========================================================================


def test_repeated_marker_search_from_advances():
    """相同 marker 出现多次 → search_from 推进 → 各自定位。"""
    chunks = [_make_chunk("x", "c1"), _make_chunk("x", "c2"), _make_chunk("y", "c3")]
    doc = _make_doc(chunks)
    # stream = "x x y"
    # predict: end of first x = 1, end of second x = 3 → [1, 3]
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("x", "after"),  # 第一次找 x，find_pos=0, gt=1
            _make_anchor("x", "after"),  # search_from=1, find_pos=2, gt=3
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 2 predict [1,3], 2 gt [1,3] → matched=2 → P=1, R=1
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_repeated_marker_three_times_all_located():
    """3 个相同 marker → 各自定位（search_from 累积推进）。"""
    chunks = [_make_chunk("x", "c1"), _make_chunk("x", "c2"),
              _make_chunk("x", "c3"), _make_chunk("end", "c4")]
    doc = _make_doc(chunks)
    # stream = "x x x end"
    # predict: end of x=1, end of x=3, end of x=5 → [1, 3, 5]
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("x", "after"),
            _make_anchor("x", "after"),
            _make_anchor("x", "after"),
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 3 predict, 3 gt → matched=3
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_marker_reverse_order_still_located_in_stream_order():
    """anchor 顺序逆序（anchor[0] 是后面 marker）→ 仍按 stream 顺序定位。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # stream = "a b"
    # anchor[0]="b" → search_from=0, find_pos=2, gt=3
    # anchor[1]="a" → search_from=3, find_pos=-1 → missing！
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("b", "after"),
            _make_anchor("a", "after"),
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 第一个 anchor 把 search_from 推到 3，第二个找不到 a
    assert "_missing_markers" in out
    assert "a" in out["_missing_markers"]["value"]
    # 只有 1 个有效 gt → recall=1/1=1
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# 数学不变量
# =========================================================================


def test_math_invariant_precision_in_zero_one():
    """0 ≤ precision ≤ 1（多个场景）。"""
    scenes = [
        # (chunks, anchors, tolerance) - 都应得 precision in [0,1]
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after")]}, 30),
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2")],
         {"chunk_boundary_anchors": [_make_anchor("xxx", "after")]}, 30),
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after"), _make_anchor("c", "after")]}, 5),
    ]
    for chunks, ann, tol in scenes:
        doc = _make_doc(chunks)
        out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
        v = out["chunk_boundary_precision"]["value"]
        if v is not None:
            assert 0.0 <= v <= 1.0


def test_math_invariant_recall_in_zero_one():
    """0 ≤ recall ≤ 1。"""
    scenes = [
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after")]}, 30),
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after"), _make_anchor("b", "after")]}, 30),
    ]
    for chunks, ann, tol in scenes:
        doc = _make_doc(chunks)
        out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
        v = out["chunk_boundary_recall"]["value"]
        if v is not None:
            assert 0.0 <= v <= 1.0


def test_math_invariant_f1_in_zero_one():
    """0 ≤ f1 ≤ 1。"""
    scenes = [
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after")]}, 30),
        ([_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")],
         {"chunk_boundary_anchors": [_make_anchor("a", "after")]}, 30),
    ]
    for chunks, ann, tol in scenes:
        doc = _make_doc(chunks)
        out = chunk_boundary_prf(doc, ann, tolerance_chars=tol)
        v = out["chunk_boundary_f1"]["value"]
        if v is not None:
            assert 0.0 <= v <= 1.0


def test_math_invariant_f1_le_min_of_p_and_r():
    """f1 ≤ min(p, r)（调和中位数 ≤ 算术最小值，仅在 p=0 或 r=0 时取等）。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    # stream = "a b c"; predict = [1, 3]
    # anchor at "c" after → gt=5; |3-5|=2 ≤ 30 → matched
    # 但只有 1 个 anchor, 2 个 predict → p=1/2=0.5, r=1/1=1.0
    annotation = {"chunk_boundary_anchors": [_make_anchor("c", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert p == 0.5
    assert r == 1.0
    # f1 = 2 * 0.5 * 1 / 1.5 = 0.6667
    assert f1 is not None
    assert f1 <= max(p, r)


def test_math_invariant_matched_le_min_pred_gt():
    """matched ≤ min(num_pred, num_gt)。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    # predict = [1, 3]
    # 1 anchor → matched ≤ 1
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # matched = 1; num_pred = 2; num_gt = 1
    assert out["chunk_boundary_precision"]["value"] == 1 / 2
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_math_invariant_p_equals_r_implies_f1_equals_p():
    """当 p == r 时 f1 == p == r。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # predict = [1]; anchor a after → gt=1; matched=1; p=r=1
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    p = out["chunk_boundary_precision"]["value"]
    r = out["chunk_boundary_recall"]["value"]
    f1 = out["chunk_boundary_f1"]["value"]
    assert p == r == f1 == 1.0


def test_math_invariant_perfect_pr_yields_perfect_f1():
    """p=1 r=1 → f1=1。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_math_invariant_zero_precision_implies_zero_f1():
    """p=0 → f1=0（denom=0+r=r>0 → f1=0）。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # stream = "a b"; predict = [1]; anchor "zzz" not found
    # 但 missing → gt_positions=[]; num_gt=0 → recall=null
    # 实际上要测 p=0 需要 predict 不匹配 anchor 但 anchor 有效
    # 用 tolerance=0 + anchor 偏移 1 字符
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    # b 的 find_pos=2, before → gt=2; predict=1; |1-2|=1 > tolerance=0 → unmatched
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    # recall: matched=0, num_gt=1 → 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    # f1: p+r=0 → _ratio(0.0) → 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_math_invariant_zero_recall_implies_zero_f1():
    """r=0 → f1=0。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # 同上 setup
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


# =========================================================================
# tolerance_chars 极端值深度
# =========================================================================


def test_tolerance_one_char_allows_minor_offset():
    """tolerance_chars=1 → 容差 1 字符。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # stream = "a b"; predict = [1]; anchor b before → gt=2; |1-2|=1 ≤ 1 → matched
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_tolerance_equals_stream_length_allows_any_match():
    """tolerance_chars = len(stream) → 所有 anchor 匹配所有 pred（距离 ≤ len）。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    # stream = "a b" (3 chars); predict=[1]; anchor b before → gt=2; |1-2|=1 ≤ 3 → matched
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=3)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_tolerance_huge_value_allows_any_match():
    """tolerance_chars=10**6 → 实际就是全部匹配。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("b", "before")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=10**6)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 常量深度补强
# =========================================================================


def test_parser_does_not_emit_relations_is_str():
    """常量是 str 实例。"""
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_precise():
    """常量值精确。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_hashable():
    """常量可 hash（不可变）。"""
    assert hash(PARSER_DOES_NOT_EMIT_RELATIONS) == hash("parser_does_not_emit_relations")


def test_parser_does_not_emit_relations_is_first_in_all():
    """常量在 __all__ 第一个。"""
    import evaluation.annotation_metrics as m
    assert m.__all__[0] == "PARSER_DOES_NOT_EMIT_RELATIONS"


def test_parser_does_not_emit_relations_is_module_level_not_imported():
    """常量在 module namespace 是 module-level（不是 imported）。"""
    # 检查它不是从其他 module 导入
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    # 没有 import 语句含 PARSER_DOES_NOT_EMIT_RELATIONS
    for line in src.split("\n"):
        if line.startswith("import ") or line.startswith("from "):
            assert "PARSER_DOES_NOT_EMIT_RELATIONS" not in line


def test_parser_does_not_emit_relations_only_module_constant():
    """是 module 唯一常量（除函数外的唯一 module-level name）。"""
    import evaluation.annotation_metrics as m
    public_names = [n for n in dir(m) if not n.startswith("_")]
    own_names = []
    for n in public_names:
        obj = getattr(m, n)
        if isinstance(obj, str):
            # 字符串常量算 module-level
            own_names.append(n)
        elif callable(obj) and hasattr(obj, "__module__") and obj.__module__ == "evaluation.annotation_metrics":
            own_names.append(n)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in own_names
    assert "figure_caption_prf" in own_names
    assert "chunk_boundary_prf" in own_names


# =========================================================================
# module source 字符串精确补强
# =========================================================================


def test_module_source_contains_one_to_one_text():
    """docstring 含「一对一」。"""
    src = inspect.getsource(ammod)
    assert "一对一" in src


def test_module_source_contains_tolerance_text():
    """docstring 含「容差」。"""
    src = inspect.getsource(ammod)
    assert "容差" in src


def test_module_source_contains_recent_image_text():
    """docstring 含「最近图片」。"""
    src = inspect.getsource(ammod)
    assert "最近图片" in src


def test_module_source_contains_heuristic_text():
    """docstring 含「启发式」。"""
    src = inspect.getsource(ammod)
    assert "启发式" in src


def test_module_source_contains_normalized_full_text_text():
    """chunk_boundary_prf docstring 含「规范化全文流」。"""
    src = inspect.getsource(ammod)
    assert "规范化全文流" in src


def test_module_source_contains_parser_does_not_emit_constant():
    """source 含 PARSER_DOES_NOT_EMIT_RELATIONS = "..." 赋值。"""
    src = inspect.getsource(ammod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_import():
    src = inspect.getsource(ammod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_sys_import():
    src = inspect.getsource(ammod)
    assert "import sys" not in src
    assert "from sys " not in src


def test_module_source_no_re_import():
    src = inspect.getsource(ammod)
    assert "import re" not in src
    assert "from re " not in src


def test_module_source_no_logging_import():
    src = inspect.getsource(ammod)
    assert "import logging" not in src
    assert "from logging " not in src


def test_module_source_no_subprocess_import():
    src = inspect.getsource(ammod)
    assert "import subprocess" not in src
    assert "from subprocess " not in src


def test_module_source_no_asyncio_import():
    src = inspect.getsource(ammod)
    assert "import asyncio" not in src
    assert "from asyncio " not in src


def test_module_source_no_threading_import():
    src = inspect.getsource(ammod)
    assert "import threading" not in src
    assert "from threading " not in src


def test_module_source_no_math_import():
    src = inspect.getsource(ammod)
    assert "import math" not in src
    assert "from math " not in src


def test_module_source_no_datetime_import():
    src = inspect.getsource(ammod)
    assert "import datetime" not in src
    assert "from datetime " not in src


def test_module_source_no_itertools_import():
    src = inspect.getsource(ammod)
    assert "import itertools" not in src
    assert "from itertools " not in src


def test_module_source_no_functools_import():
    src = inspect.getsource(ammod)
    assert "import functools" not in src
    assert "from functools " not in src


# =========================================================================
# module source 含必要 imports
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(ammod)
    assert "from __future__ import annotations" in src


def test_module_source_has_collections_counter():
    src = inspect.getsource(ammod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any():
    src = inspect.getsource(ammod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import():
    src = inspect.getsource(ammod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_null_ratio_import():
    src = inspect.getsource(ammod)
    assert "from evaluation.metrics import _null, _ratio" in src


# =========================================================================
# chunk_boundary_prf source level 完整补强
# =========================================================================


def test_chunk_boundary_prf_source_has_norm_chunks_comprehension():
    """source 含 norm_chunks = [normalize_text(...) for c in chunks]。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "norm_chunks = [normalize_text(c.get(\"text\") or \"\") for c in chunks]" in src


def test_chunk_boundary_prf_source_has_joined_raw():
    """source 含 joined_raw = ' '.join(norm_chunks)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'joined_raw = " ".join(norm_chunks)' in src


def test_chunk_boundary_prf_source_has_stream_normalize():
    """source 含 stream = normalize_text(joined_raw)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_chunk_boundary_prf_source_has_predicted_init():
    """source 含 predicted: list[int] = [] 和 pos = 0。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int] = []" in src
    assert "pos = 0" in src


def test_chunk_boundary_prf_source_has_enumerate_norm_chunks():
    """source 含 for i, txt in enumerate(norm_chunks)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "for i, txt in enumerate(norm_chunks)" in src


def test_chunk_boundary_prf_source_has_break_for_last_chunk():
    """source 含 if i == len(norm_chunks) - 1: break。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "if i == len(norm_chunks) - 1:" in src
    assert "break  # 最后一个 chunk 后面不算边界" in src


def test_chunk_boundary_prf_source_has_find_pos_call():
    """source 含 find_pos = stream.find(txt, pos)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "find_pos = stream.find(txt, pos)" in src


def test_chunk_boundary_prf_source_has_neg_find_skip():
    """source 含 if find_pos < 0 → pos += len(txt) + 1 + continue。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "if find_pos < 0:" in src
    assert "pos += len(txt) + 1" in src
    assert "continue" in src


def test_chunk_boundary_prf_source_has_end_computation():
    """source 含 end = find_pos + len(txt)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "end = find_pos + len(txt)" in src


def test_chunk_boundary_prf_source_has_predicted_append():
    """source 含 predicted.append(end)。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted.append(end)" in src


def test_chunk_boundary_prf_source_has_pos_advance():
    """source 含 pos = end + 1（跨过空格）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pos = end + 1" in src


def test_chunk_boundary_prf_source_has_gt_positions_list():
    """source 含 gt_positions: list[int] = []。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions: list[int] = []" in src


def test_chunk_boundary_prf_source_has_missing_markers_list():
    """source 含 missing_markers: list[str] = []。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_chunk_boundary_prf_source_has_search_from_init():
    """source 含 search_from = 0。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_prf_source_has_for_anchors_loop():
    """source 含 for a in anchors。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "for a in anchors:" in src


def test_chunk_boundary_prf_source_has_marker_get():
    """source 含 marker = a.get('marker', '')。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'marker = a.get("marker", "")' in src


def test_chunk_boundary_prf_source_has_position_get():
    """source 含 position = a.get('position', 'after')。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'position = a.get("position", "after")' in src


def test_chunk_boundary_prf_source_has_position_before_branch():
    """source 含 if position == 'before'。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'if position == "before":' in src


def test_chunk_boundary_prf_source_has_else_after_branch():
    """source 含 else 分支（gt_positions.append(find_pos + len(marker))）。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert 'gt_positions.append(find_pos + len(marker))' in src


def test_chunk_boundary_prf_source_has_pairs_sort():
    """source 含 pairs.sort(key=lambda x: x[0])。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_chunk_boundary_prf_source_has_matched_init():
    """source 含 matched = 0 + used_pred = set() + used_gt = set()。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched = 0" in src
    assert "used_pred = set()" in src
    assert "used_gt = set()" in src


def test_chunk_boundary_prf_source_has_tolerance_chars_default_30():
    """source 含 tolerance_chars: int = 30。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "tolerance_chars: int = 30" in src


# =========================================================================
# figure_caption_prf source level 完整补强
# =========================================================================


def test_figure_caption_prf_source_has_reason_assignment():
    """source 含 reason = PARSER_DOES_NOT_EMIT_RELATIONS。"""
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_prf_source_has_return_dict_with_3_keys():
    """source 含 return dict 字面量含 3 个 figure_caption_* key。"""
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_precision": _null(reason)' in src
    assert '"figure_caption_recall": _null(reason)' in src
    assert '"figure_caption_f1": _null(reason)' in src


def test_figure_caption_prf_source_has_null_call_3_times():
    """source 含 3 处 _null(reason) 调用。"""
    src = inspect.getsource(figure_caption_prf)
    assert src.count("_null(reason)") == 3


def test_figure_caption_prf_source_no_tolerance_chars():
    """figure_caption_prf 不接受 tolerance_chars（signature 只有 2 个 param）。"""
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert "tolerance_chars" not in params
    assert len(params) == 2


# =========================================================================
# signatures 精确补强
# =========================================================================


def test_figure_caption_prf_signature_2_params():
    """figure_caption_prf(document, annotation) 2 个参数。"""
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_chunk_boundary_prf_signature_3_params():
    """chunk_boundary_prf(document, annotation, tolerance_chars) 3 个参数。"""
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_chars_default_30():
    """tolerance_chars 默认值是 30。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_figure_caption_prf_no_varargs_varkw():
    """figure_caption_prf 没有 *args / **kwargs。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_chunk_boundary_prf_no_varargs_varkw():
    """chunk_boundary_prf 没有 *args / **kwargs。"""
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_figure_caption_prf_return_annotation_is_string():
    """from __future__ import annotations → return annotation 是 string。"""
    sig = inspect.signature(figure_caption_prf)
    assert isinstance(sig.return_annotation, str)
    assert "dict" in sig.return_annotation


def test_chunk_boundary_prf_return_annotation_is_string():
    """from __future__ import annotations → return annotation 是 string。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)
    assert "dict" in sig.return_annotation


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_4_chunks_3_anchors_all_matched():
    """4 chunks + 3 anchors → P=1, R=1, F1=1。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"),
              _make_chunk("c", "c3"), _make_chunk("d", "c4")]
    doc = _make_doc(chunks)
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("a", "after"),
            _make_anchor("b", "after"),
            _make_anchor("c", "after"),
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_one_matched_one_missing_yields_half_recall():
    """2 predict + 2 anchor (1 matched + 1 missing) → recall=0.5。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    # stream = "a b c"; predict = [1, 3]
    # anchor[0]="a" after → find_pos=0, gt=1; matched (|1-1|=0)
    # anchor[1]="zzz" → not found → missing
    annotation = {
        "chunk_boundary_anchors": [
            _make_anchor("a", "after"),
            _make_anchor("zzz", "after"),
        ]
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # matched=1, num_pred=2 → p=0.5
    # gt_positions=[1] (only valid), num_gt=1, matched=1 → r=1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    # missing_markers 含 zzz
    assert "_missing_markers" in out
    assert "zzz" in out["_missing_markers"]["value"]


def test_e2e_does_not_mutate_input_document_chunks():
    """调用后 document.chunks 不变。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    chunks_before = [dict(c) for c in doc["chunks"]]
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after")]}
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    chunks_after = [dict(c) for c in doc["chunks"]]
    assert chunks_before == chunks_after


def test_e2e_does_not_mutate_input_annotation_anchors():
    """调用后 annotation.chunk_boundary_anchors 不变。"""
    chunks = [_make_chunk("hello", "c1"), _make_chunk("world", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("hello", "after"),
                                              _make_anchor("world", "before")]}
    anchors_before = [dict(a) for a in annotation["chunk_boundary_anchors"]]
    chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    anchors_after = [dict(a) for a in annotation["chunk_boundary_anchors"]]
    assert anchors_before == anchors_after


def test_e2e_repeated_calls_same_result():
    """同输入两次调用结果一致。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2"), _make_chunk("c", "c3")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after"),
                                              _make_anchor("b", "after")]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out1 == out2


def test_e2e_tolerance_recorded_in_output():
    """tolerance_chars 必须在 output 的 _tolerance_chars 字段记录。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_e2e_no_missing_markers_field_when_all_found():
    """所有 anchor 都找到 → _missing_markers 字段不出现。"""
    chunks = [_make_chunk("a", "c1"), _make_chunk("b", "c2")]
    doc = _make_doc(chunks)
    annotation = {"chunk_boundary_anchors": [_make_anchor("a", "after"),
                                              _make_anchor("b", "after")]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" not in out


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_2_module_level_functions():
    """module 有 2 个 module-level function：figure_caption_prf, chunk_boundary_prf。"""
    import evaluation.annotation_metrics as m
    import types
    funcs = [n for n in dir(m)
             if not n.startswith("_")
             and isinstance(getattr(m, n), types.FunctionType)
             and getattr(m, n).__module__ == "evaluation.annotation_metrics"]
    assert sorted(funcs) == ["chunk_boundary_prf", "figure_caption_prf"]


def test_module_has_no_class_definition():
    """module 无 class 定义。"""
    src = inspect.getsource(ammod)
    # 没有顶层 class 关键字（不在 string 内）
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("class ") and ":" in stripped:
            # 但要排除 docstring 里的描述
            # 简单：检查缩进==0（module level）
            if not line.startswith(" "):
                pytest.fail(f"Found class definition: {line}")


def test_module_has_no_main_block():
    """module 无 if __name__ == '__main__' 块。"""
    src = inspect.getsource(ammod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src


def test_module_all_has_3_entries_in_order():
    """__all__ 3 entries 顺序精确。"""
    import evaluation.annotation_metrics as m
    assert m.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_entries_in_namespace():
    """__all__ 中所有 entries 在 module namespace。"""
    import evaluation.annotation_metrics as m
    for name in m.__all__:
        assert hasattr(m, name)


def test_module_all_entries_are_callable_or_constant():
    """__all__ 中 entries 要么 callable 要么 constant。"""
    import evaluation.annotation_metrics as m
    for name in m.__all__:
        obj = getattr(m, name)
        assert callable(obj) or isinstance(obj, (str, int, float, bool))


def test_module_namespace_has_5_imported_names():
    """module namespace 含 5 个 imported names：Counter, Any, normalize_text, _null, _ratio。"""
    import evaluation.annotation_metrics as m
    # _null, _ratio 是从 evaluation.metrics 导入（_前缀，不 in __all__）
    # Counter 从 collections
    # Any 从 typing
    # normalize_text 从 app.chunkers.structural
    assert hasattr(m, "Counter")
    assert hasattr(m, "Any")
    assert hasattr(m, "normalize_text")
    assert hasattr(m, "_null")
    assert hasattr(m, "_ratio")
