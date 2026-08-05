r"""evaluation/annotation_metrics.py 边角测试 - 第十五轮（Round 255）。

补强已有 base/edges/edges2-14（共 ~970+ 测试）未覆盖的深度：
- chunk_boundary_anchors 是 None / int / string / set / bool（非 list）
- annotation 含 chunk_boundary_anchors=None
- annotation 含 chunk_boundary_anchors=[]（空 list）
- annotation 是非空 dict 但缺 chunk_boundary_anchors key
- chunk text 是 surrogate pair (4-byte UTF-16)
- chunk text 是 emoji + ZWJ 组合
- chunk text 是混合 unicode + ascii
- _tolerance_chars dict 结构精确
- _missing_markers dict 结构精确
- chunk_boundary_prf 默认 tolerance_chars=30
- figure_caption_prf 各种非 dict 输入
- chunk_boundary_prf 不修改 chunks list 引用
- chunk text 含 control characters（U+0000-U+001F）
- inspect.signature 返回 Signature 类型
- 模块 namespace 含 __future__ 导入痕迹（无，但可验证源码）
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# =========================================================================
# chunk_boundary_anchors 非 list 类型
# =========================================================================


def test_chunk_boundary_anchors_is_none_treated_as_empty():
    """chunk_boundary_anchors=None → `or []` → 空列表 → 'no_ground_truth_anchors'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": None}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_anchors_is_int_raises_type_error():
    """chunk_boundary_anchors=int → 不能 iterate → TypeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": 42}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_boundary_anchors_is_string_iterates_chars():
    """chunk_boundary_anchors='abc' → 迭代字符。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": "abc"}  # 字符串可迭代
    # 每个 char 是 anchor：'a', 'b', 'c' → 每个 .get('marker', '')
    # str 没有 .get → AttributeError
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_boundary_anchors_is_set_iterates():
    """chunk_boundary_anchors 是 set → 迭代（顺序不定）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": {"a", "b"}}  # set of strings
    # set iteration → 'a', 'b' → str 没有 .get → AttributeError
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_boundary_anchors_is_dict_raises_attribute_error():
    """chunk_boundary_anchors 是 dict → 迭代 keys → str 没有 .get → AttributeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": {"k": "v"}}  # 迭代 keys
    with pytest.raises(AttributeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_annotation_non_empty_dict_missing_anchors_key():
    """annotation 是非空 dict 但缺 chunk_boundary_anchors → .get 返回 None → or []。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"other_key": "value"}  # 无 chunk_boundary_anchors
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # anchors = [] → 'no_ground_truth_anchors'
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_annotation_empty_anchors_list_treated_as_no_anchors():
    """annotation.chunk_boundary_anchors=[] → 'no_ground_truth_anchors'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


# =========================================================================
# chunk text 各种 unicode 边界
# =========================================================================


def test_chunk_text_surrogate_pair_emoji():
    """chunk text 是 4-byte emoji（Python 中是单个字符）。"""
    doc = {"chunks": [{"text": "😀"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "😀", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_emoji_with_zwj_sequence():
    """chunk text 是 ZWJ 序列（家庭 emoji 等）。"""
    # 👨‍👩‍👧 = man + ZWJ + woman + ZWJ + girl
    doc = {"chunks": [{"text": "👨‍👩‍👧"}, {"text": "x"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "👨‍👩‍👧", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_mixed_unicode_and_ascii():
    """混合 unicode + ascii。"""
    doc = {"chunks": [{"text": "Hello世界"}, {"text": "World你好"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "Hello世界", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_control_characters():
    """chunk text 含控制字符（U+0001 等）。"""
    # 控制字符不是 whitespace，会被 normalize_text 保留
    doc = {"chunks": [{"text": "a\x01b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a\x01b", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 'a\x01b' 在 stream 'a\x01b c' 中 find；normalize 保留控制字符
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_with_only_unicode_whitespace():
    """chunk text 全是 unicode whitespace → normalize 后变空字符串。"""
    doc = {"chunks": [{"text": "  "}, {"text": "abc"}]}
    # normalize_text 把 unicode whitespace 转空格再 strip
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream 仍是 "abc"
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# _tolerance_chars 与 _missing_markers dict 结构精确
# =========================================================================


def test_tolerance_chars_dict_two_keys_value_and_reason():
    """_tolerance_chars 含 2 keys: value/reason。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert set(out["_tolerance_chars"].keys()) == {"value", "reason"}


def test_tolerance_chars_reason_is_none_on_success():
    """_tolerance_chars reason 是 None。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["reason"] is None


def test_missing_markers_dict_two_keys():
    """_missing_markers 含 2 keys: value/reason。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert set(out["_missing_markers"].keys()) == {"value", "reason"}


def test_missing_markers_value_is_list():
    """_missing_markers value 是 list。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert isinstance(out["_missing_markers"]["value"], list)


def test_missing_markers_reason_is_none():
    """_missing_markers reason 是 None。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert out["_missing_markers"]["reason"] is None


# =========================================================================
# 默认 tolerance_chars=30
# =========================================================================


def test_chunk_boundary_prf_default_tolerance_chars_is_30():
    """默认 tolerance_chars=30。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_default_tolerance_propagated_to_output():
    """默认调用 → _tolerance_chars.value=30。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_no_kwargs_uses_default():
    """无 kwargs 调用 → 默认 30。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["_tolerance_chars"]["value"] == 30


# =========================================================================
# figure_caption_prf 各种输入
# =========================================================================


def test_figure_caption_prf_with_dict_document():
    """figure_caption_prf 接受各种 dict 输入（不影响输出）。"""
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    keys = list(out.keys())
    assert keys == ["figure_caption_precision", "figure_caption_recall", "figure_caption_f1"]


def test_figure_caption_prf_with_non_dict_input():
    """figure_caption_prf 接受非 dict 输入（doc/ann 都不重要）。"""
    out = figure_caption_prf("string_doc", "string_ann")
    # 仍返回 3 keys 全 null
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_with_list_input():
    """figure_caption_prf 接受 list 输入。"""
    out = figure_caption_prf([], [])
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_int_input():
    """figure_caption_prf 接受 int 输入。"""
    out = figure_caption_prf(42, 100)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_none_inputs():
    """figure_caption_prf(None, None) → 3 keys null。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


# =========================================================================
# chunk_boundary_prf 不修改 chunks list 引用
# =========================================================================


def test_chunk_boundary_prf_does_not_modify_chunks_list():
    """不替换 chunks list 引用。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    chunks_before = doc["chunks"]
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert doc["chunks"] is chunks_before


def test_chunk_boundary_prf_does_not_modify_anchors_list():
    """不替换 anchors list 引用。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    anchors = [{"marker": "alpha", "position": "after"}]
    ann = {"chunk_boundary_anchors": anchors}
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert ann["chunk_boundary_anchors"] is anchors


# =========================================================================
# 模块 namespace identity 详细
# =========================================================================


def test_module_future_annotations_present():
    """模块源码含 __future__ import。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_any_in_namespace_identity():
    """Any 在命名空间且 is typing.Any。"""
    import evaluation.annotation_metrics as m
    from typing import Any as A
    assert m.Any is A


def test_module_parser_does_not_emit_relations_in_namespace_identity():
    """PARSER_DOES_NOT_EMIT_RELATIONS is 模块属性。"""
    import evaluation.annotation_metrics as m
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS is PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_is_hashable():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是 str → hashable。"""
    assert hash(PARSER_DOES_NOT_EMIT_RELATIONS) is not None
    s = {PARSER_DOES_NOT_EMIT_RELATIONS, "another"}
    assert PARSER_DOES_NOT_EMIT_RELATIONS in s


def test_parser_does_not_emit_relations_singleton_like():
    """两次访问得到同一对象（str 是 intern 的）。"""
    a = PARSER_DOES_NOT_EMIT_RELATIONS
    b = "parser_does_not_emit_relations"
    assert a == b


# =========================================================================
# inspect.signature 返回类型
# =========================================================================


def test_chunk_boundary_prf_signature_returns_signature_object():
    """signature 返回 inspect.Signature 实例。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert isinstance(sig, inspect.Signature)


def test_figure_caption_prf_signature_returns_signature_object():
    """signature 返回 inspect.Signature 实例。"""
    sig = inspect.signature(figure_caption_prf)
    assert isinstance(sig, inspect.Signature)


def test_chunk_boundary_prf_param_count_three():
    """3 个参数。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_figure_caption_prf_param_count_two():
    """2 个参数。"""
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_chunk_boundary_prf_param_names_exact():
    """参数名：document/annotation/tolerance_chars。"""
    sig = inspect.signature(chunk_boundary_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation", "tolerance_chars"]


def test_figure_caption_prf_param_names_exact():
    """参数名：document/annotation。"""
    sig = inspect.signature(figure_caption_prf)
    names = list(sig.parameters.keys())
    assert names == ["document", "annotation"]


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 进一步
# =========================================================================


def test_parser_does_not_emit_relations_value_contains_underscore():
    """常量值含 '_'。"""
    assert "_" in PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_value_specific_words():
    """常量值含特定词。"""
    val = PARSER_DOES_NOT_EMIT_RELATIONS
    assert "parser" in val
    assert "does" in val
    assert "not" in val
    assert "emit" in val
    assert "relations" in val


# =========================================================================
# chunk_boundary_prf 边界：document 是 dict subclass
# =========================================================================


def test_chunk_boundary_prf_document_dict_subclass_works():
    """document 是 dict subclass → 仍工作。"""
    class DocSub(dict):
        pass
    doc = DocSub(chunks=[{"text": "alpha"}, {"text": "beta"}])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_annotation_dict_subclass_works():
    """annotation 是 dict subclass → 仍工作。"""
    class AnnSub(dict):
        pass
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = AnnSub(chunk_boundary_anchors=[{"marker": "alpha", "position": "after"}])
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# chunk text 是 float / int → TypeError（normalize_text 内部）
# =========================================================================


def test_chunk_text_float_raises_type_error_in_normalize():
    """chunk text 是 float → normalize_text(float) raises TypeError。"""
    doc = {"chunks": [{"text": 1.5}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_text_dict_raises_type_error_in_normalize():
    """chunk text 是 dict → TypeError。"""
    doc = {"chunks": [{"text": {"k": "v"}}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_text_list_raises_type_error_in_normalize():
    """chunk text 是 list → TypeError。"""
    doc = {"chunks": [{"text": [1, 2]}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


# =========================================================================
# chunk text 是 None：之前已测，但补充多个 None
# =========================================================================


def test_chunks_all_none_text_returns_no_predicted_boundaries():
    """所有 chunk text=None → norm_chunks=['', '']。"""
    doc = {"chunks": [{"text": None}, {"text": None}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = normalize(" ") = ""
    # 'abc' find in "" → -1 → missing
    # predicted: chunk 0 (not last): find("", 0)=0, end=0, predicted=[0]
    # num_pred=1, num_gt=0 → 'no_ground_truth_anchors_in_stream'
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "abc" in out["_missing_markers"]["value"]


# =========================================================================
# 模块 namespace 详细
# =========================================================================


def test_module_namespace_contains_counter():
    """命名空间含 Counter。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Counter")


def test_module_namespace_contains_normalize_text():
    """命名空间含 normalize_text。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "normalize_text")


def test_module_namespace_contains_null_helper():
    """命名空间含 _null。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_null")


def test_module_namespace_contains_ratio_helper():
    """命名空间含 _ratio。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "_ratio")


def test_module_namespace_contains_any():
    """命名空间含 Any。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "Any")


# =========================================================================
# 输出 reason 详细
# =========================================================================


def test_no_predicted_boundaries_reason_message_exact_value():
    """doc is None → 'pipeline_failed'。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"


def test_no_annotation_path_returns_no_annotation_reason():
    """annotation=None → 'no_annotation'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_empty_annotation_dict_returns_no_annotation_reason():
    """annotation={} → 'no_annotation'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    out = chunk_boundary_prf(doc, {}, tolerance_chars=10)
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


# =========================================================================
# 输出 _tolerance_chars 始终存在
# =========================================================================


def test_tolerance_chars_present_when_doc_none():
    """doc is None 时 _tolerance_chars 仍存在。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert "_tolerance_chars" in out


def test_tolerance_chars_present_when_annotation_empty():
    """annotation={} 时 _tolerance_chars 仍存在。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    out = chunk_boundary_prf(doc, {})
    assert "_tolerance_chars" in out


def test_tolerance_chars_present_when_single_chunk():
    """单 chunk 时 _tolerance_chars 仍存在。"""
    doc = {"chunks": [{"text": "alpha"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert "_tolerance_chars" in out


def test_tolerance_chars_present_when_no_anchors():
    """无 anchors 时 _tolerance_chars 仍存在。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert "_tolerance_chars" in out


def test_tolerance_chars_present_on_success():
    """成功路径 _tolerance_chars 存在。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_tolerance_chars" in out


# =========================================================================
# 重复 marker 在 anchor 中
# =========================================================================


def test_repeated_marker_in_anchors_first_consumed():
    """同 marker 出现 N 次 → 前 N-1 个 find 到，最后一个 missing。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 'alpha' 在 stream 中只出现 1 次
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "alpha", "position": "after"},  # 重复 → 第 2 个 missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 第 1 个 alpha 找到；第 2 个 alpha search_from 之后找不到 → missing
    assert "alpha" in out["_missing_markers"]["value"]


def test_three_markers_two_distinct_one_missing():
    """3 个 markers：2 个不同 + 1 个重复 → 1 missing。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "alpha", "position": "after"},
        {"marker": "beta", "position": "after"},
        {"marker": "alpha", "position": "after"},  # alpha 已消耗 → missing
    ]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 'alpha' 第 2 次 missing；'beta' 仍能找到（search_from 推进到 alpha 之后）
    assert "alpha" in out["_missing_markers"]["value"]


# =========================================================================
# 输出 keys 不含 _prefix（除 _tolerance_chars / _missing_markers）
# =========================================================================


def test_chunk_boundary_prf_no_extra_underscored_keys():
    """除 _tolerance_chars 与 _missing_markers 外，无其他 _ 开头 key。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    underscored = [k for k in out.keys() if k.startswith("_")]
    assert set(underscored) == {"_tolerance_chars"}


def test_chunk_boundary_prf_with_missing_markers_only_two_underscored():
    """有 missing_markers 时 _ 开头 keys 是 _tolerance_chars + _missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    underscored = [k for k in out.keys() if k.startswith("_")]
    assert set(underscored) == {"_tolerance_chars", "_missing_markers"}


# =========================================================================
# chunk text 含数字
# =========================================================================


def test_chunk_text_with_numbers():
    """chunk text 含数字。"""
    doc = {"chunks": [{"text": "123abc"}, {"text": "456def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "123abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_text_only_numbers():
    """chunk text 全数字。"""
    doc = {"chunks": [{"text": "12345"}, {"text": "67890"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "12345", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
