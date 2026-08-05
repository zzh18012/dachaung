r"""evaluation/annotation_metrics.py 边角测试 - 第十二轮（Round 234）。

补强已有 base/edges/edges2-11（共 ~480 测试）未覆盖的深度：
- anchor 元素类型多样（None/str/int/list/tuple/bool）触发 AttributeError
- chunks 字段 None / chunk_boundary_anchors 字段 None 表现为空 list
- 各分支输出 dict 插入顺序精确
- 多 missing_markers 顺序保留；_missing_markers value 类型是 list
- 空 marker + before/after 都进 missing
- 空 chunk 文本生成 predicted boundary at position 0
- module __all__ 顺序精确（不是集合相等）
- 函数级 docstring 关键词
- tolerance_chars 浮点 / 0 / 1 边界匹配
- 多 chunk（> 2）predicted boundaries 数量
- 内部 _null/_ratio/Counter 在模块命名空间
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# anchor 元素类型错误（list 里的元素不是 dict）
# =========================================================================


def test_chunk_boundary_prf_anchor_element_none_raises():
    """anchor 是 None → a.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [None]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_element_str_raises():
    """anchor 是 str → str.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": ["alpha"]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_element_int_raises():
    """anchor 是 int → int.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [42]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_element_list_raises():
    """anchor 是 list → list.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [[]]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_element_tuple_raises():
    """anchor 是 tuple → tuple.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [()]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_element_set_raises():
    """anchor 是 set → set.get 抛 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [set()]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


def test_chunk_boundary_prf_anchor_second_element_none_raises():
    """anchor list 第 1 个有效、第 2 个是 None → 第 2 个 AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}, None]}
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann)


# =========================================================================
# chunks / chunk_boundary_anchors 字段值为 None
# =========================================================================


def test_chunk_boundary_prf_chunks_value_none_treated_as_empty():
    """document['chunks'] = None → `or []` 走空 list 分支。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    # chunks=None → len < 2 path → 有 anchors → recall = _ratio(0.0)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_value_none_no_anchors():
    """document['chunks'] = None + 无 anchors → 三指标都 null。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_anchors_value_none_treated_as_empty():
    """annotation['chunk_boundary_anchors'] = None → `or []` 走空 list 分支。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann)
    # 有 chunks 但 anchors 空 → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_none_and_anchors_none():
    """document['chunks']=None + annotation['chunk_boundary_anchors']=None → no_predicted_boundaries。"""
    doc = {"chunks": None}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


# =========================================================================
# dict 插入顺序精确（各分支）
# =========================================================================


def test_chunk_boundary_prf_doc_none_dict_insertion_order():
    """doc=None 分支：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_annotation_empty_dict_insertion_order():
    """annotation={} 分支：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {})
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_annotation_none_dict_insertion_order():
    """annotation=None 分支：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_zero_chunks_dict_insertion_order():
    """chunks=[] 分支：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "x"}]})
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_no_anchors_dict_insertion_order():
    """chunks>=2 但无 anchors：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_success_no_missing_dict_insertion_order():
    """成功路径，无 missing_markers：keys 顺序 [precision, recall, f1, _tolerance_chars]。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    ]


def test_chunk_boundary_prf_success_with_missing_dict_insertion_order():
    """成功路径 + 有 missing：keys 顺序 [precision, recall, f1, _tolerance_chars, _missing_markers]。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"},
                                       {"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    keys = list(out.keys())
    assert keys == [
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    ]


def test_figure_caption_prf_dict_insertion_order():
    """figure_caption_prf：keys 顺序 [precision, recall, f1]。"""
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    keys = list(out.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


# =========================================================================
# _missing_markers 结构与多 missing 顺序
# =========================================================================


def test_missing_markers_value_is_list():
    """_missing_markers value 必须是 list（即使只 1 个 missing）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, ann)
    assert isinstance(out["_missing_markers"]["value"], list)


def test_missing_markers_value_reason_none():
    """_missing_markers reason 永远是 None。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["reason"] is None


def test_missing_markers_multiple_preserve_order():
    """多个 missing markers 按输入顺序记录。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "zzz", "position": "after"},
        {"marker": "alpha", "position": "after"},
        {"marker": "yyy", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_missing_markers"]["value"] == ["zzz", "yyy"]


def test_missing_markers_all_missing():
    """全部 anchor 都 missing → _missing_markers 含全部；recall = null(no_ground_truth_anchors_in_stream)。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "xxx", "position": "after"},
        {"marker": "yyy", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann)
    assert set(out["_missing_markers"]["value"]) == {"xxx", "yyy"}
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_missing_markers_empty_string_marker():
    """空字符串 marker → find returns -1（per `if marker else -1`）→ missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "" in out["_missing_markers"]["value"]


def test_missing_markers_empty_string_marker_position_before():
    """空字符串 marker + position=before → 仍 missing。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "" in out["_missing_markers"]["value"]


def test_missing_markers_anchor_dict_empty():
    """空 dict anchor → marker=""（默认）→ missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{}]}
    out = chunk_boundary_prf(doc, ann)
    assert "" in out["_missing_markers"]["value"]


# =========================================================================
# predicted boundaries 数量与位置
# =========================================================================


def test_predicted_boundaries_count_2_chunks_gives_1():
    """2 chunks → 1 predicted boundary。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # predicted=1, anchors=1, matched depends on positions
    # alpha 长度=5, so boundary at position 5; marker 'alpha' after → 5; matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_predicted_boundaries_count_3_chunks_gives_2():
    """3 chunks → 2 predicted boundaries。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    # 2 predicted, 2 anchors, all matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_predicted_boundaries_count_4_chunks_gives_3():
    """4 chunks → 3 predicted boundaries。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "b", "position": "after"},
        {"marker": "c", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_empty_first_chunk_predicted_boundary_at_zero():
    """第 1 个 chunk 文本空 → predicted boundary at position 0。"""
    doc = {"chunks": [{"text": ""}, {"text": "hello"}]}
    # joined_raw = " hello"; stream = "hello"
    # for chunk 0 (not last): find("", 0) = 0, end=0, predicted=[0]
    # for chunk 1 (last): break
    ann = {"chunk_boundary_anchors": [{"marker": "hello", "position": "before"}]}
    # 'hello' starts at 0 → gt_positions=[0]
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_empty_middle_chunk_creates_zero_length_match():
    """中间 chunk 文本空 → predicted boundary 在前一 chunk 末尾位置。"""
    doc = {"chunks": [{"text": "abc"}, {"text": ""}, {"text": "def"}]}
    # joined_raw = "abc  def"; stream = "abc def"
    # chunk 0: find("abc", 0)=0, end=3, predicted=[3], pos=4
    # chunk 1 (not last): find("", 4)=4, end=4, predicted=[3,4], pos=5
    # chunk 2 (last): break
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": " ", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # abc after → position 3; space after → position 4
    # predicted = [3, 4]; both match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# tolerance_chars 边界
# =========================================================================


def test_tolerance_chars_float_value_preserved():
    """tolerance_chars=15.5 → value 字段保留 float。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=15.5)
    assert out["_tolerance_chars"]["value"] == 15.5


def test_tolerance_chars_zero_no_match_distance_one():
    """tolerance_chars=0 + 距离=1 → 不匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # predicted boundary at position 5 (after 'alpha')
    ann = {"chunk_boundary_anchors": [{"marker": "alph", "position": "after"}]}
    # 'alph' after → position 4; predicted=5; distance=1, > 0 → no match
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_tolerance_chars_one_match_distance_one():
    """tolerance_chars=1 + 距离=1 → 匹配。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alph", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_tolerance_chars_propagated_when_anchor_missing():
    """即使 anchor 全 missing，_tolerance_chars 仍透传。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_tolerance_chars_propagated_doc_none():
    """doc=None 时 _tolerance_chars 仍透传。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_tolerance_chars_propagated_annotation_empty():
    """annotation={} 时 _tolerance_chars 仍透传。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {}, tolerance_chars=77)
    assert out["_tolerance_chars"]["value"] == 77


# =========================================================================
# module 结构
# =========================================================================


def test_module_all_order_exact():
    """__all__ 顺序精确（不是集合相等）。"""
    import evaluation.annotation_metrics as m
    assert m.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_first_element_constant():
    """__all__ 第 1 个是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    import evaluation.annotation_metrics as m
    assert m.__all__[0] == "PARSER_DOES_NOT_EMIT_RELATIONS"


def test_module_all_last_element_function():
    """__all__ 最后一个是 chunk_boundary_prf。"""
    import evaluation.annotation_metrics as m
    assert m.__all__[-1] == "chunk_boundary_prf"


def test_module_counter_in_namespace():
    """Counter 已导入到模块命名空间。"""
    import evaluation.annotation_metrics as m
    from collections import Counter
    assert m.Counter is Counter


def test_module_null_in_namespace():
    """_null 已从 evaluation.metrics 导入。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_null")
    assert callable(m._null)


def test_module_ratio_in_namespace():
    """_ratio 已从 evaluation.metrics 导入。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_ratio")
    assert callable(m._ratio)


def test_module_normalize_text_in_namespace():
    """normalize_text 已从 app.chunkers.structural 导入。"""
    import evaluation.annotation_metrics as m
    from app.chunkers.structural import normalize_text
    assert m.normalize_text is normalize_text


def test_module_any_in_namespace():
    """Any 已从 typing 导入。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Any")


# =========================================================================
# 函数级 docstring 关键词
# =========================================================================


def test_figure_caption_prf_docstring_present():
    """figure_caption_prf 有 docstring。"""
    assert figure_caption_prf.__doc__ is not None
    assert len(figure_caption_prf.__doc__) > 0


def test_figure_caption_prf_docstring_mentions_null():
    """figure_caption_prf docstring 提到 null（固定 null 语义）。"""
    assert "null" in figure_caption_prf.__doc__.lower()


def test_figure_caption_prf_docstring_mentions_caption():
    """figure_caption_prf docstring 提到 caption 或 关联（中文）。"""
    doc_lower = figure_caption_prf.__doc__.lower()
    assert "caption" in doc_lower or "关联" in figure_caption_prf.__doc__


def test_chunk_boundary_prf_docstring_present():
    """chunk_boundary_prf 有 docstring。"""
    assert chunk_boundary_prf.__doc__ is not None
    assert len(chunk_boundary_prf.__doc__) > 0


def test_chunk_boundary_prf_docstring_mentions_normalize():
    """chunk_boundary_prf docstring 提到 normalize。"""
    assert "normaliz" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_tolerance():
    """chunk_boundary_prf docstring 提到 tolerance。"""
    assert "tolerance" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_precision():
    """chunk_boundary_prf docstring 提到 precision。"""
    assert "precision" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_recall():
    """chunk_boundary_prf docstring 提到 recall。"""
    assert "recall" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_anchor():
    """chunk_boundary_prf docstring 提到 anchor。"""
    assert "anchor" in chunk_boundary_prf.__doc__.lower()


def test_chunk_boundary_prf_docstring_mentions_args():
    """chunk_boundary_prf docstring 含 Args 段。"""
    assert "args" in chunk_boundary_prf.__doc__.lower() or "参数" in chunk_boundary_prf.__doc__


# =========================================================================
# _tolerance_chars 结构精确
# =========================================================================


def test_tolerance_chars_structure_value_reason():
    """_tolerance_chars 结构：{'value': int, 'reason': None}。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=30)
    tc = out["_tolerance_chars"]
    assert set(tc.keys()) == {"value", "reason"}
    assert tc["value"] == 30
    assert tc["reason"] is None


def test_tolerance_chars_default_value_30():
    """_tolerance_chars 默认 value=30。"""
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_tolerance_chars_in_all_paths():
    """所有路径都有 _tolerance_chars。"""
    doc_full = {"chunks": [{"text": "a"}, {"text": "b"}]}
    doc_no_chunks = {"chunks": []}
    ann_full = {"chunk_boundary_anchors": [{"marker": "a"}]}
    ann_empty = {}
    paths = [
        chunk_boundary_prf(None, None),
        chunk_boundary_prf(doc_full, None),
        chunk_boundary_prf(doc_full, ann_empty),
        chunk_boundary_prf(doc_no_chunks, ann_full),
        chunk_boundary_prf(doc_full, {"chunk_boundary_anchors": []}),
        chunk_boundary_prf(doc_full, ann_full),
    ]
    for r in paths:
        assert "_tolerance_chars" in r
        assert isinstance(r["_tolerance_chars"], dict)


# =========================================================================
# _null 输出结构（_null 是 from evaluation.metrics import 的）
# =========================================================================


def test_null_output_structure_value_reason():
    """figure_caption_prf 输出每项 = {'value': None, 'reason': str}。"""
    out = figure_caption_prf({"chunks": []}, None)
    for key in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        v = out[key]
        assert set(v.keys()) == {"value", "reason"}
        assert v["value"] is None
        assert isinstance(v["reason"], str)


def test_ratio_output_structure_value_reason():
    """_ratio 路径输出 = {'value': float, 'reason': None}。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    for key in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[key]
        assert set(v.keys()) == {"value", "reason"}
        assert isinstance(v["value"], float)
        assert v["reason"] is None


# =========================================================================
# f1 计算路径补强
# =========================================================================


def test_f1_perfect_match_value_one():
    """完全匹配时 f1=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_f1_half_match_value():
    """半匹配（precision=0.5, recall=1.0）时 f1 = 2*0.5*1/(0.5+1) = 1/1.5。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # predicted boundaries: after 'a' (pos 1), after 'b' (pos 3 in "a b c")
    # actually joined_raw = "a b c"; predicted = [1, 3]
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    # gt_positions = [1]; matched=1; precision=1/2=0.5; recall=1/1=1.0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    expected_f1 = 2 * 0.5 * 1.0 / (0.5 + 1.0)
    assert abs(out["chunk_boundary_f1"]["value"] - expected_f1) < 1e-9


def test_f1_zero_match_when_anchors_found_but_no_match():
    """匹配=0、但 num_pred>0, num_gt>0 → f1=0.0（denom=0 路径）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "before"}]}
    # marker 'alpha' before → gt_position = 0; predicted=5; distance=5
    # tolerance_chars=1 → no match → matched=0
    out = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_f1_reason_precision_or_recall_not_evaluated_when_all_anchors_missing():
    """全部 anchor missing → recall=null(no_ground_truth_anchors_in_stream) → f1=null。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


def test_f1_reason_when_recall_null_but_precision_evaluated():
    """precision 有值，recall null → f1 null。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # num_pred > 0, all anchors missing → recall null
    ann = {"chunk_boundary_anchors": [{"marker": "zzz"}, {"marker": "yyy"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] is not None  # 0.0 (matched=0/1)
    assert out["chunk_boundary_recall"]["value"] is None
    assert out["chunk_boundary_f1"]["value"] is None
    assert out["chunk_boundary_f1"]["reason"] == "precision_or_recall_not_evaluated"


# =========================================================================
# figure_caption_prf 不依赖输入
# =========================================================================


def test_figure_caption_prf_same_output_for_various_inputs():
    """figure_caption_prf 对各种输入都返回相同结构。"""
    inputs = [
        (None, None),
        ({}, {}),
        ({"chunks": []}, {"chunk_boundary_anchors": []}),
        ({"chunks": [{"text": "a"}]}, {"figure_caption": "x"}),
        (42, 42),  # 非 dict 但仍正常返回（不读输入）
    ]
    base = figure_caption_prf(None, None)
    for doc, ann in inputs:
        out = figure_caption_prf(doc, ann)
        assert out == base


def test_figure_caption_prf_callable_with_no_args_raises():
    """figure_caption_prf 必须两个参数。"""
    with pytest.raises(TypeError):
        figure_caption_prf()
    with pytest.raises(TypeError):
        figure_caption_prf(None)


# =========================================================================
# 一对一约束补强
# =========================================================================


def test_one_to_one_two_anchors_same_position():
    """两个 anchor 都在同一位置 → 只匹配一个 predicted boundary。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # predicted boundary at 3
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "abc", "position": "after"},
    ]}
    # First anchor find 'abc' at 0, after → 3. search_from=3.
    # Second anchor find 'abc' from 3 → -1 (no more 'abc') → missing!
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 第二个 marker 重复 → missing
    assert "abc" in out.get("_missing_markers", {}).get("value", [])


def test_one_to_one_two_predictions_one_anchor():
    """2 predicted + 1 anchor → matched=1, precision=0.5, recall=1.0。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    # predicted boundaries: after 'a' (1), after 'b' (3 in "a b c")
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2
    assert out["chunk_boundary_recall"]["value"] == 1.0  # 1/1


def test_one_to_one_predicted_consumed_by_closest():
    """2 predicted + 2 anchors，距离 [1, 5] 和 [10, 12]：贪心按距离匹配。"""
    # 构造场景：predicted=[5, 20], anchors 在 4 和 22
    # alpha=5 chars; beta=3 chars; gamma=5 chars
    # chunks: [{"text": "alpha"}, {"text": "bbb"}, {"text": "gamma"}]
    # joined_raw = "alpha bbb gamma"; stream = "alpha bbb gamma"
    # predicted: after 'alpha' = 5; after 'bbb' = 5+1+3=9
    doc = {"chunks": [{"text": "alpha"}, {"text": "bbb"}, {"text": "gamma"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},  # gt at 5
        {"marker": "bbb", "position": "after"},    # gt at 9
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# =========================================================================
# 模块函数签名精确
# =========================================================================


def test_chunk_boundary_prf_signature_param_count():
    """chunk_boundary_prf 有 3 个参数（document, annotation, tolerance_chars）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_signature_param_names():
    """参数名精确。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_figure_caption_prf_signature_param_count():
    """figure_caption_prf 有 2 个参数。"""
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_signature_param_names():
    """参数名精确。"""
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_chunk_boundary_prf_default_only_tolerance():
    """只有 tolerance_chars 有默认值。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty
    assert sig.parameters["annotation"].default is inspect.Parameter.empty
    assert sig.parameters["tolerance_chars"].default == 30


def test_figure_caption_prf_no_defaults():
    """figure_caption_prf 无默认值。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# 一致性：所有 null 路径的 reason 都是 PARSER_DOES_NOT_EMIT_RELATIONS（figure_caption）
# =========================================================================


def test_figure_caption_prf_reason_constant_value():
    """figure_caption_prf 所有 reason 等于 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    out = figure_caption_prf({"chunks": []}, None)
    for key in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[key]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_reasons_all_equal():
    """三个指标的 reason 完全相同。"""
    out = figure_caption_prf({"chunks": []}, None)
    reasons = [out[k]["reason"] for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1")]
    assert len(set(reasons)) == 1


# =========================================================================
# 副作用检查
# =========================================================================


def test_chunk_boundary_prf_no_mutation_of_tolerance_chars_param():
    """tolerance_chars 是 int（不可变），但确认输出 value 等于传入值。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=55)
    assert out["_tolerance_chars"]["value"] == 55
    # 重新调用，确认没被缓存
    out2 = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=66)
    assert out2["_tolerance_chars"]["value"] == 66


def test_chunk_boundary_prf_returns_new_dict_each_call():
    """每次调用返回新的 dict（不缓存）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a"}]}
    out1 = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    out2 = chunk_boundary_prf(doc, ann, tolerance_chars=100)
    assert out1 is not out2
    assert out1 == out2


def test_figure_caption_prf_returns_new_dict_each_call():
    """figure_caption_prf 每次调用返回新 dict。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 is not out2
    assert out1 == out2
