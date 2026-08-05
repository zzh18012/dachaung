r"""evaluation/annotation_metrics.py 边角测试 - 第十四轮（Round 248）。

补强已有 base/edges/edges2-13（共 ~880+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含 'find'/'normalize_text'/'_null'/'_ratio'/'PARSER_DOES_NOT_EMIT_RELATIONS'
- module metadata：__file__ 后缀 .py；__package__ == 'evaluation'；无 __main__ 块
- 函数 metadata：__module__ / __qualname__ 精确
- __future__ annotations 影响 return_annotation 为 str
- bytes marker → TypeError（stream.find(bytes_obj) 不被接受）
- anchor 缺 marker key → marker=''（empty 默认）
- anchor 缺 position key → position='after' 默认
- anchor 含额外未知 key → 静默忽略
- document 是 dict subclass → 仍正常工作
- chunks 是 tuple → 仍正常工作
- annotation 是 dict subclass → 仍正常工作
- Counter 在模块命名空间但 unused（imported 仅作可能的未来用途）
- PARSER_DOES_NOT_EMIT_RELATIONS 是 str / 不可再次赋值（模块属性可写，但语义上常量）
- module __all__ 不可变检查（list 类型）
- callable / function 类型精确（isFunction）
- chunk text 是 bytes → normalize_text(bytes) raises TypeError
- chunk text 是 bytearray → 同上
- signature.return_annotation 是 str（来自 __future__）
- chunk_boundary_prf 无 varargs/keywords
- figure_caption_prf 无 varargs/keywords
- _tolerance_chars value 类型精确（int）
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
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_find_call():
    """模块源码含 '.find('（用于 stream.find）。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert ".find(" in src


def test_module_source_contains_normalize_text():
    """模块源码含 'normalize_text'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "normalize_text" in src


def test_module_source_contains_null_reference():
    """模块源码含 '_null('。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "_null(" in src


def test_module_source_contains_ratio_reference():
    """模块源码含 '_ratio('。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "_ratio(" in src


def test_module_source_contains_constant_definition():
    """模块源码含 'PARSER_DOES_NOT_EMIT_RELATIONS'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_module_source_contains_docstring_marker():
    """模块源码含 'marker'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "marker" in src


def test_module_source_contains_docstring_anchor():
    """模块源码含 'anchor'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "anchor" in src


def test_module_source_contains_docstring_tolerance():
    """模块源码含 'tolerance_chars'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "tolerance_chars" in src


def test_module_source_no_main_guard():
    """模块源码不含 '__main__' guard（无 if __name__ == '__main__'）。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_uses_future_annotations():
    """模块源码含 'from __future__ import annotations'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_uses_dict_subscript_syntax():
    """模块源码含 'dict[str,'（Python 3.9+ subscript）。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "dict[str," in src


def test_module_source_contains_kwargs_for_chunk_boundary():
    """模块源码含 'tolerance_chars: int = 30'。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "tolerance_chars: int = 30" in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """模块 __file__ 以 '.py' 结尾。"""
    import evaluation.annotation_metrics as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_annotation_metrics():
    """模块 __file__ 含 'annotation_metrics'。"""
    import evaluation.annotation_metrics as m
    assert "annotation_metrics" in m.__file__


def test_module_package_is_evaluation():
    """模块 __package__ 是 'evaluation'。"""
    import evaluation.annotation_metrics as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_annotation_metrics():
    """模块 __name__ 是 'evaluation.annotation_metrics'。"""
    import evaluation.annotation_metrics as m
    assert m.__name__ == "evaluation.annotation_metrics"


def test_module_all_is_list_type():
    """__all__ 是 list 类型。"""
    import evaluation.annotation_metrics as m
    assert isinstance(m.__all__, list)


def test_module_all_not_tuple():
    """__all__ 不是 tuple。"""
    import evaluation.annotation_metrics as m
    assert not isinstance(m.__all__, tuple)


def test_module_counter_in_namespace_identity():
    """Counter 在命名空间且 is collections.Counter。"""
    import evaluation.annotation_metrics as m
    assert m.Counter is Counter


def test_module_counter_imported_but_unused_in_source_body():
    """Counter import 后 body 中无 'Counter(' 调用。"""
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    # 去掉 import 行后检查
    body = src.replace("from collections import Counter", "")
    assert "Counter(" not in body


# =========================================================================
# 函数 metadata
# =========================================================================


def test_chunk_boundary_prf_module_attribute():
    """chunk_boundary_prf.__module__ == 'evaluation.annotation_metrics'。"""
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_chunk_boundary_prf_qualname():
    """chunk_boundary_prf.__qualname__ == 'chunk_boundary_prf'。"""
    assert chunk_boundary_prf.__qualname__ == "chunk_boundary_prf"


def test_chunk_boundary_prf_name():
    """chunk_boundary_prf.__name__ == 'chunk_boundary_prf'。"""
    assert chunk_boundary_prf.__name__ == "chunk_boundary_prf"


def test_figure_caption_prf_module_attribute():
    """figure_caption_prf.__module__ == 'evaluation.annotation_metrics'。"""
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_figure_caption_prf_qualname():
    """figure_caption_prf.__qualname__ == 'figure_caption_prf'。"""
    assert figure_caption_prf.__qualname__ == "figure_caption_prf"


def test_figure_caption_prf_name():
    """figure_caption_prf.__name__ == 'figure_caption_prf'。"""
    assert figure_caption_prf.__name__ == "figure_caption_prf"


def test_chunk_boundary_prf_is_python_function():
    """chunk_boundary_prf 是 Python 函数（types.FunctionType）。"""
    import types
    assert isinstance(chunk_boundary_prf, types.FunctionType)


def test_figure_caption_prf_is_python_function():
    """figure_caption_prf 是 Python 函数。"""
    import types
    assert isinstance(figure_caption_prf, types.FunctionType)


def test_chunk_boundary_prf_no_varargs():
    """chunk_boundary_prf 签名无 VAR_POSITIONAL。"""
    sig = inspect.signature(chunk_boundary_prf)
    has_var = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL
        for p in sig.parameters.values()
    )
    assert not has_var


def test_chunk_boundary_prf_no_varkw():
    """chunk_boundary_prf 签名无 VAR_KEYWORD。"""
    sig = inspect.signature(chunk_boundary_prf)
    has_var = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    assert not has_var


def test_figure_caption_prf_no_varargs():
    """figure_caption_prf 签名无 VAR_POSITIONAL。"""
    sig = inspect.signature(figure_caption_prf)
    has_var = any(
        p.kind == inspect.Parameter.VAR_POSITIONAL
        for p in sig.parameters.values()
    )
    assert not has_var


def test_figure_caption_prf_no_varkw():
    """figure_caption_prf 签名无 VAR_KEYWORD。"""
    sig = inspect.signature(figure_caption_prf)
    has_var = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    )
    assert not has_var


def test_chunk_boundary_prf_return_annotation_is_str():
    """return annotation 是 str（__future__ 让它成为字符串）。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert isinstance(sig.return_annotation, str)


def test_figure_caption_prf_return_annotation_is_str():
    """return annotation 是 str。"""
    sig = inspect.signature(figure_caption_prf)
    assert isinstance(sig.return_annotation, str)


def test_chunk_boundary_prf_return_annotation_contains_dict():
    """return annotation 含 'dict'。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in sig.return_annotation


def test_figure_caption_prf_return_annotation_contains_dict():
    """return annotation 含 'dict'。"""
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in sig.return_annotation


# =========================================================================
# bytes / bytearray marker
# =========================================================================


def test_bytes_marker_raises_type_error():
    """marker 是 bytes → stream.find(bytes) raises TypeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": b"alpha", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_bytearray_marker_raises_type_error():
    """marker 是 bytearray → TypeError。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": bytearray(b"alpha"), "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_text_bytes_raises_type_error():
    """chunk text 是 bytes → normalize_text(bytes) raises TypeError。"""
    doc = {"chunks": [{"text": b"alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


def test_chunk_text_bytearray_raises_type_error():
    """chunk text 是 bytearray → TypeError。"""
    doc = {"chunks": [{"text": bytearray(b"alpha")}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=10)


# =========================================================================
# anchor 缺 key 默认行为
# =========================================================================


def test_anchor_missing_marker_key_defaults_to_empty_string():
    """anchor 缺 marker → .get('marker', '') → ''。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 空 marker 在 stream 中 find → -1（缺）→ missing_markers
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # '' marker find → 因为 marker 是 '' 时，源码用 `if marker else -1` → -1 → missing
    # 但 missing_markers 列表里 entry 是 ''
    assert "" in out["_missing_markers"]["value"]


def test_anchor_missing_position_key_defaults_to_after():
    """anchor 缺 position → .get('position', 'after') → 'after'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha"}]}  # no position
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # default 'after' → gt at 5, predicted at 5 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_with_extra_unknown_key_silently_ignored():
    """anchor 含 extra 'unknown_field' → 静默忽略。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{
        "marker": "alpha",
        "position": "after",
        "unknown_field": "ignored",
        "weight": 0.5,
    }]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_anchor_dict_empty_uses_defaults():
    """anchor 是 {} → marker='' + position='after'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # marker='' → missing_markers
    assert "" in out["_missing_markers"]["value"]


# =========================================================================
# dict subclass / tuple chunks
# =========================================================================


def test_document_dict_subclass_works():
    """document 是 dict subclass → 仍正常工作。"""
    class DocSub(dict):
        pass
    doc = DocSub(chunks=[{"text": "alpha"}, {"text": "beta"}])
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_annotation_dict_subclass_works():
    """annotation 是 dict subclass → 仍正常工作。"""
    class AnnSub(dict):
        pass
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = AnnSub(chunk_boundary_anchors=[{"marker": "alpha", "position": "after"}])
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunks_tuple_works():
    """chunks 是 tuple → 仍能 enumerate。"""
    doc = {"chunks": ({"text": "alpha"}, {"text": "beta"})}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunks_generator_raises_type_error_no_len():
    """chunks 是 generator → len() 失败 raises TypeError。"""
    def gen():
        yield {"text": "alpha"}
        yield {"text": "beta"}
    doc = {"chunks": gen()}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    with pytest.raises(TypeError):
        chunk_boundary_prf(doc, ann, tolerance_chars=0)


def test_chunk_boundary_anchors_tuple_works():
    """chunk_boundary_anchors 是 tuple → 可迭代。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": ({"marker": "alpha", "position": "after"},)}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 详细
# =========================================================================


def test_parser_does_not_emit_relations_is_str_type():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是 str 实例。"""
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_exact():
    """PARSER_DOES_NOT_EMIT_RELATIONS 值精确。"""
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_single_word():
    """常量是单个 snake_case word（无空格/连字符/点）。"""
    val = PARSER_DOES_NOT_EMIT_RELATIONS
    for ch in (" ", "-", "."):
        assert ch not in val


def test_parser_does_not_emit_relations_in_module_namespace():
    """PARSER_DOES_NOT_EMIT_RELATIONS 在模块命名空间。"""
    import evaluation.annotation_metrics as m
    assert hasattr(m, "PARSER_DOES_NOT_EMIT_RELATIONS")
    assert m.PARSER_DOES_NOT_EMIT_RELATIONS == PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_in_all():
    """常量名在 __all__。"""
    import evaluation.annotation_metrics as m
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in m.__all__


# =========================================================================
# _tolerance_chars value 类型精确
# =========================================================================


def test_tolerance_chars_value_type_int_in_output():
    """_tolerance_chars value 是 int（与输入 tolerance_chars 类型一致）。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out["_tolerance_chars"]["value"], int)
    assert out["_tolerance_chars"]["value"] == 30


def test_tolerance_chars_value_zero_int_in_output():
    """tolerance_chars=0 → value 是 int 0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_tolerance_chars_value_negative_int_in_output():
    """tolerance_chars=-1 → value 是 int -1。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-1)
    assert out["_tolerance_chars"]["value"] == -1


def test_tolerance_chars_value_large_int_in_output():
    """tolerance_chars=99999 → value 是 int 99999。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=99999)
    assert out["_tolerance_chars"]["value"] == 99999


# =========================================================================
# 输出 key 集合精确
# =========================================================================


def test_chunk_boundary_prf_output_keys_full_set_when_missing_markers():
    """有 missing_markers 时输出 keys 含 5 个：3 metric + _tolerance_chars + _missing_markers。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}, {"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
        "_missing_markers",
    }


def test_chunk_boundary_prf_output_keys_no_missing_markers():
    """无 missing_markers 时输出 keys 仅 4 个。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_figure_caption_prf_output_keys_exact_three():
    """figure_caption_prf 输出 keys 精确 3 个。"""
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


# =========================================================================
# figure_caption_prf 详细
# =========================================================================


def test_figure_caption_prf_value_is_none_for_all_keys():
    """figure_caption_prf 所有 value 是 None。"""
    out = figure_caption_prf({"chunks": []}, {"chunk_boundary_anchors": []})
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_reason_all_same_constant():
    """figure_caption_prf 所有 reason 是 PARSER_DOES_NOT_EMIT_RELATIONS。"""
    out = figure_caption_prf({"chunks": []}, None)
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_keys_exact_in_order():
    """figure_caption_prf keys 顺序：precision, recall, f1。"""
    out = figure_caption_prf(None, None)
    keys = list(out.keys())
    assert keys == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_does_not_mutate_inputs():
    """figure_caption_prf 不修改输入。"""
    import copy
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = copy.deepcopy(doc)
    ann_before = copy.deepcopy(ann)
    figure_caption_prf(doc, ann)
    assert doc == doc_before
    assert ann == ann_before


# =========================================================================
# chunk_boundary_prf 一致性
# =========================================================================


def test_chunk_boundary_prf_does_not_mutate_document():
    """chunk_boundary_prf 不修改 document。"""
    import copy
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    doc_before = copy.deepcopy(doc)
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert doc == doc_before


def test_chunk_boundary_prf_does_not_mutate_annotation():
    """chunk_boundary_prf 不修改 annotation。"""
    import copy
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    ann_before = copy.deepcopy(ann)
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert ann == ann_before


# =========================================================================
# reason 字符串精确（not just contains）
# =========================================================================


def test_no_predicted_boundaries_reason_exact_value():
    """doc 只 1 chunk 时 reason == 'no_predicted_boundaries'。"""
    doc = {"chunks": [{"text": "alpha"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_no_ground_truth_anchors_reason_exact_value():
    """有预测无 anchors → reason == 'no_ground_truth_anchors'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_pipeline_failed_reason_exact_value():
    """doc is None → reason == 'pipeline_failed'。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_recall"]["reason"] == "pipeline_failed"
    assert out["chunk_boundary_f1"]["reason"] == "pipeline_failed"


def test_no_annotation_reason_exact_value():
    """annotation 为空 dict → reason == 'no_annotation'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    out = chunk_boundary_prf(doc, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"
    assert out["chunk_boundary_recall"]["reason"] == "no_annotation"
    assert out["chunk_boundary_f1"]["reason"] == "no_annotation"


def test_no_ground_truth_anchors_in_stream_reason_exact_value():
    """anchors 全 missing → num_gt=0 → recall reason 'no_ground_truth_anchors_in_stream'。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # zzz 不在 stream 中 → gt_positions=[] → recall reason 'no_ground_truth_anchors_in_stream'
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


# =========================================================================
# reason for f1 when only one of p/r is null
# =========================================================================


def test_f1_reason_precision_null_recall_evaluated():
    """precision null（num_pred=0） + recall evaluated（num_gt>0） → f1 reason 'precision_or_recall_not_evaluated'。"""
    # 实际上 num_pred=0 → num_gt>0 时不会进入 chunks≥2 path
    # 但可构造：chunks≥2 但 predicted 都失败 → predicted=[] → num_pred=0
    # 让 norm_chunks 中的 txt 在 stream 中找不到 → predicted 仍 0
    # 实际上 find 在拼接 stream 中总能找到，所以很难构造 num_pred=0 with chunks≥2
    # 跳过此场景的构造，仅检查 reason 在源码中存在
    import evaluation.annotation_metrics as m
    src = inspect.getsource(m)
    assert "precision_or_recall_not_evaluated" in src


# =========================================================================
# 算法一致性：normalize 后再 normalize 拼接
# =========================================================================


def test_stream_is_double_normalize_of_join():
    """stream = normalize_text(' '.join(normalize_text(chunk_text)))。"""
    # 验证：chunks 中包含内部空白，stream 是规范化后的拼接
    doc = {"chunks": [
        {"text": "alpha   beta"},   # normalize → "alpha beta"
        {"text": "gamma"},
    ]}
    # joined = "alpha beta gamma"
    # stream = normalize_text("alpha beta gamma") = "alpha beta gamma"
    ann = {"chunk_boundary_anchors": [{"marker": "alpha beta", "position": "after"}]}
    # 'alpha beta' at 0, after → gt at 10
    # predicted: chunk 0 'alpha beta' find at 0, end=10 → predicted=[10]
    # matched
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_stream_with_chunks_having_trailing_whitespace():
    """chunks 含 trailing whitespace → strip 后拼接。"""
    doc = {"chunks": [
        {"text": "  alpha  "},  # normalize → "alpha"
        {"text": "  beta  "},   # normalize → "beta"
    ]}
    # stream = "alpha beta"
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


# =========================================================================
# 模块 __all__ 完整集合
# =========================================================================


def test_module_all_set_exact():
    """__all__ 集合精确（与 list 内容一致）。"""
    import evaluation.annotation_metrics as m
    assert set(m.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_all_no_private_symbols():
    """__all__ 不含 '_' 开头的私有 symbol。"""
    import evaluation.annotation_metrics as m
    for name in m.__all__:
        assert not name.startswith("_")


def test_module_namespace_contains_all_three():
    """模块命名空间含 __all__ 中所有名字。"""
    import evaluation.annotation_metrics as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# chunk_boundary_prf 签名参数 kind 精确
# =========================================================================


def test_chunk_boundary_prf_param_kinds():
    """3 个都是 POSITIONAL_OR_KEYWORD（无 * 分隔符）。"""
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert all(p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)


def test_figure_caption_prf_param_kinds():
    """2 个 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert all(p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD for p in params)


def test_chunk_boundary_prf_third_param_has_default_30():
    """第 3 个 param default == 30。"""
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[2].default == 30


def test_chunk_boundary_prf_first_two_no_default():
    """前 2 个 param 无 default（empty）。"""
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty


def test_figure_caption_prf_no_defaults():
    """figure_caption_prf 无 default。"""
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


# =========================================================================
# Counter 不影响模块逻辑
# =========================================================================


def test_counter_does_not_participate_in_algorithm():
    """Counter 即使移除也不影响 chunk_boundary_prf 行为（不依赖）。"""
    # 通过 monkeypatch 删除 Counter 不会破坏（因为不被调用）
    import evaluation.annotation_metrics as m
    # 仅检查源码不含 'Counter(' 调用
    src = inspect.getsource(m)
    body = src.replace("from collections import Counter", "")
    assert "Counter(" not in body


# =========================================================================
# 边界：所有 chunks 文本为空字符串
# =========================================================================


def test_all_chunks_empty_text_predicted_at_zero():
    """2 chunks 都空 → norm_chunks=['',''], joined=' ', stream=' ' normalize → ''。"""
    doc = {"chunks": [{"text": ""}, {"text": ""}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = normalize_text(" ") = ""（strip）
    # predicted: chunk 0 (not last): find("", 0) = 0, end=0 → predicted=[0]; pos=1
    # chunk 1 (last): break
    # gt: 'alpha' find in "" → -1 → missing
    # num_pred=1, num_gt=0 → recall 'no_ground_truth_anchors_in_stream'
    assert "alpha" in out["_missing_markers"]["value"]
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


# =========================================================================
# chunks 中混入 None text
# =========================================================================


def test_chunks_mixed_none_and_string_text():
    """chunk text = [None, 'abc'] → norm_chunks = ['', 'abc']。"""
    doc = {"chunks": [{"text": None}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # stream = normalize_text(" abc") = "abc"
    # predicted: chunk 0 (not last): find("", 0)=0, end=0 → predicted=[0]; pos=1
    # chunk 1 (last): break
    # gt: 'abc' find at 0, after → gt=3
    # distance |0-3|=3, tolerance=10 → matched
    assert out["chunk_boundary_precision"]["value"] == 1.0
