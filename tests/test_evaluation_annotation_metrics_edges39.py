"""evaluation/annotation_metrics.py 第三十九轮 edges 测试（Round 406）。

补强 edges38 未触及的角度：
- figure_caption_prf 行为深度第十二批（更多 corner cases：keys 集合严格 / reason 严格相同 / 与所有输入独立 / dict 不共享 / null helper 行为）
- chunk_boundary_prf 行为深度第十二批（更多 branch：document=None + tolerance 透传 / annotation=None / empty chunks / 单 chunk + 多 anchor / 多 chunk + 0 anchor / 多 chunk + 多 anchor 完整匹配 / tolerance=0 严格匹配 / tolerance 极大宽松匹配 / marker 在 stream 中重复 / position before / position after / mixed position / missing all markers / 部分缺失 markers / stream 中无 marker / Unicode marker / 空 marker / predicted 边界顺序）
- module source forbidden tokens 第十五批
- module source 字符串精确补强第十二批
- signatures 第十二批
- module 合理性第十二批
- 端到端集成第十二批
"""

from __future__ import annotations

import inspect
import json
import os
from typing import Any

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 行为深度第十二批 ----------


def test_figure_caption_prf_keys_exact_set_batch12():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_keys_order_batch12():
    out = figure_caption_prf(None, None)
    assert list(out.keys()) == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_reason_constant_value_batch12():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_value_all_none_batch12():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_ignores_complex_doc_batch12():
    """复杂 doc + annotation 都不影响输出。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "img1"},
            {"type": "caption", "element_id": "cap1"},
        ],
        "chunks": [],
    }
    annot = {"figure_caption_pairs": [["img1", "cap1"]]}
    out = figure_caption_prf(doc, annot)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_dict_independence_batch12():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    # 两个 dict 应相等但不是同一个对象
    assert out1 == out2
    assert out1 is not out2
    # 修改一个不影响另一个
    out1["custom"] = "x"
    assert "custom" not in out2


def test_figure_caption_prf_with_annotation_having_chunk_anchors_batch12():
    """annotation 有 chunk_boundary_anchors，但 figure_caption 仍 null。"""
    annot = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = figure_caption_prf(None, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_non_dict_inputs_batch12():
    """传非 dict 输入（None/[]）也不抛。"""
    out1 = figure_caption_prf(None, [])
    out2 = figure_caption_prf([], None)
    out3 = figure_caption_prf("doc", "annot")
    for o in [out1, out2, out3]:
        for v in o.values():
            assert v["value"] is None


def test_figure_caption_prf_constant_value_batch12():
    """PARSER_DOES_NOT_EMIT_RELATIONS 是固定字符串。"""
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- chunk_boundary_prf 行为深度第十二批 ----------


def test_chunk_boundary_prf_document_none_3_null_keys_batch12():
    """document=None → 3 个 null metric。"""
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_document_none_preserves_tolerance_batch12():
    out = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_annotation_none_no_annotation_reason_batch12():
    """document 非 None + annotation=None → no_annotation reason。"""
    out = chunk_boundary_prf({"chunks": []}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_no_annotation_reason_batch12():
    """document 非 None + annotation={} → no_annotation reason。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_chunks_no_predicted_reason_batch12():
    """chunks=[] → no_predicted_boundaries for precision/f1。
    但当 anchors 存在时 recall = _ratio(0.0)（reason=None，value=0.0）。
    """
    out = chunk_boundary_prf({}, {"chunk_boundary_anchors": [{"marker": "x"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # anchors truthy → recall = _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_no_predicted_batch12():
    """单 chunk → 无内部边界 → no_predicted_boundaries。"""
    doc = {"chunks": [{"id": "c1", "text": "abc"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, annot)
    # chunks 长度 1 < 2 → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_recall_zero_when_anchors_batch12():
    """单 chunk + 有 anchors → recall 是 0.0（不是 null）。"""
    doc = {"chunks": [{"id": "c1", "text": "abc"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "abc"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_no_anchors_batch12():
    """2 chunks + 0 anchor → no_ground_truth_anchors reason。"""
    doc = {"chunks": [{"id": "c1", "text": "abc"}, {"id": "c2", "text": "def"}]}
    annot = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, annot)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_two_chunks_perfect_match_batch12():
    """2 chunks + 1 anchor 精确匹配 → P=R=F1=1.0。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    # stream = "hello world"，预测边界在 5
    # anchor "hello" position="after" → 5
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch12():
    """position=before → 用 marker 起始位置。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    # stream = "hello world"，预测边界在 5
    # anchor "world" position="before" → 6（"world" 起始位置）
    annot = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=1)
    # |5 - 6| = 1 ≤ 1 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_strict_batch12():
    """tolerance=0 → 必须精确匹配。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    # 预测边界 5；anchor position="after" "hello" → 5；position="before" "world" → 6
    annot = {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # |5 - 6| = 1 > 0 → 不匹配 → P=R=0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_extremely_large_batch12():
    """tolerance 极大 → 任意边界都匹配。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "z", "position": "before"}]}
    # stream = "hello world"，"z" 不在其中 → missing marker
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10**6)
    # 但 marker 不在 stream → 无 gt_positions
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_missing_marker_batch12():
    """marker 不在 stream → 加入 _missing_markers。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert "_missing_markers" in out
    assert "xyz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_partial_missing_markers_batch12():
    """部分 marker 在、部分不在。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
            {"marker": "xyz", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_unicode_marker_batch12():
    """Unicode marker 也能匹配。"""
    doc = {"chunks": [{"id": "c1", "text": "你好"}, {"id": "c2", "text": "世界"}]}
    # stream = "你好 世界"
    annot = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_empty_marker_treated_as_missing_batch12():
    """empty marker → find 返回 -1 → 加入 _missing_markers。"""
    doc = {"chunks": [{"id": "c1", "text": "hello"}, {"id": "c2", "text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    # empty marker → missing
    assert "_missing_markers" in out


def test_chunk_boundary_prf_three_chunks_two_anchors_batch12():
    """3 chunks → 2 预测边界。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "a"},
            {"id": "c2", "text": "b"},
            {"id": "c3", "text": "c"},
        ]
    }
    # stream = "a b c"
    # 预测边界：a 后 = 1，b 后 = 3
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_default_tolerance_30_batch12():
    """默认 tolerance_chars=30。"""
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_returns_dict_strict_batch12():
    out = chunk_boundary_prf(None, None)
    assert type(out) is dict


def test_chunk_boundary_prf_returns_4_keys_when_document_none_batch12():
    """document=None → 3 metric + _tolerance_chars。"""
    out = chunk_boundary_prf(None, None)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_returns_4_keys_when_no_annotation_batch12():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_returns_4_or_5_keys_with_missing_markers_batch12():
    """有 missing markers → 5 keys（含 _missing_markers）。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert "_missing_markers" in out


def test_chunk_boundary_prf_tolerance_value_always_recorded_batch12():
    """_tolerance_chars 在所有 branch 中都有。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(None, annot, tolerance_chars=5)
    out2 = chunk_boundary_prf({"chunks": []}, annot, tolerance_chars=5)
    out3 = chunk_boundary_prf(doc, None, tolerance_chars=5)
    out4 = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    for o in [out1, out2, out3, out4]:
        assert o["_tolerance_chars"]["value"] == 5


def test_chunk_boundary_prf_negative_tolerance_no_match_batch12():
    """tolerance=-1 → 所有 |d| > -1 都满足（包括 0）...

    实际：if d <= tolerance_chars → -1 也满足 d=0
    但 d=0 也满足 d<=-1? 不，0 > -1 → 不匹配
    """
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=-1)
    # 所有 d >= 0 > -1 → 无匹配
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_multi_chunks_multi_anchors_partial_match_batch12():
    """多 chunk + 多 anchor 部分匹配。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "hello"},
            {"id": "c2", "text": "world"},
            {"id": "c3", "text": "foo"},
        ]
    }
    # stream = "hello world foo"
    # 预测边界: hello 后=5, world 后=11
    # anchor 1: "hello" after → 5 (匹配 pred 5, d=0)
    # anchor 2: "missing" after → 缺失
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "hello", "position": "after"},
            {"marker": "missing", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    # num_pred=2, num_gt=1, matched=1
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_one_to_one_matching_batch12():
    """两个 pred 距离同一 gt 都很近 → 只能命中一个（一对一）。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "a"},
            {"id": "c2", "text": "x"},
            {"id": "c3", "text": "b"},
        ]
    }
    # stream = "a x b"，预测边界: a 后=1, x 后=3
    # anchor "a" after → 1，距离 pred 1 (d=0) 和 pred 3 (d=2)
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=10)
    # 匹配最近的：pred 1 (d=0)，pred 3 不能用同一个 gt
    assert out["chunk_boundary_precision"]["value"] == 0.5  # 1/2


# ---------- module source forbidden tokens 第十五批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "import socket",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_fifteenth_batch12(token):
    source = inspect.getsource(amod)
    assert token not in source


def test_annotation_metrics_source_no_top_level_lambda_batch12():
    source = inspect.getsource(amod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_annotation_metrics_source_no_class_definition_batch12():
    source = inspect.getsource(amod)
    assert "\nclass " not in source
    assert not source.startswith("class ")


def test_annotation_metrics_source_no_assert_batch12():
    source = inspect.getsource(amod)
    assert "\nassert " not in source
    assert not source.startswith("assert ")


def test_annotation_metrics_source_no_yield_batch12():
    source = inspect.getsource(amod)
    assert "yield " not in source


def test_annotation_metrics_source_no_global_batch12():
    source = inspect.getsource(amod)
    assert " global " not in source


def test_annotation_metrics_source_no_walrus_batch12():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_annotation_metrics_source_no_async_def_batch12():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_annotation_metrics_source_no_while_loop_batch12():
    source = inspect.getsource(amod)
    assert "while " not in source


def test_annotation_metrics_source_no_input_call_batch12():
    source = inspect.getsource(amod)
    assert "input(" not in source


def test_annotation_metrics_source_no_fstring_interpolation_batch12():
    """模块无 f-string 插值（"f{" 模式）。注意：函数名 figure_caption_prf 包含 f"，但那是普通字符串字面量。"""
    source = inspect.getsource(amod)
    # 真正的 f-string 一定紧跟 { 字符
    # 检测 "f'{" 或 'f"{' 模式
    assert 'f\'{' not in source
    assert 'f"{' not in source


def test_annotation_metrics_source_no_print_batch12():
    source = inspect.getsource(amod)
    assert "print(" not in source


def test_annotation_metrics_source_no_logging_batch12():
    source = inspect.getsource(amod)
    assert "logging" not in source
    assert "logger" not in source


# ---------- module source 字符串精确补强第十二批 ----------


def test_module_source_has_future_annotations_batch12():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_source_imports_counter_batch12():
    source = inspect.getsource(amod)
    assert "from collections import Counter" in source


def test_module_source_imports_typing_any_batch12():
    source = inspect.getsource(amod)
    assert "from typing import Any" in source


def test_module_source_imports_normalize_text_batch12():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_imports_null_ratio_batch12():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_has_parser_constant_batch12():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_has_figure_caption_function_batch12():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_has_chunk_boundary_function_batch12():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_has_tolerance_chars_default_30_batch12():
    source = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in source


def test_module_source_has_dunder_all_batch12():
    source = inspect.getsource(amod)
    assert "__all__" in source


def test_module_source_no_main_block_batch12():
    source = inspect.getsource(amod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch12():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


def test_module_source_docstring_mentions_chunk_boundary_batch12():
    assert amod.__doc__ is not None
    assert "chunk_boundary" in amod.__doc__ or "分块边界" in amod.__doc__


def test_module_source_docstring_mentions_figure_caption_batch12():
    assert amod.__doc__ is not None
    assert "figure" in amod.__doc__.lower() or "图表" in amod.__doc__


def test_module_source_docstring_mentions_one_to_one_batch12():
    assert amod.__doc__ is not None
    assert "一对一" in amod.__doc__ or "one-to-one" in amod.__doc__.lower()


def test_module_source_docstring_mentions_tolerance_batch12():
    """docstring 应提到 tolerance。"""
    assert amod.__doc__ is not None
    assert "容差" in amod.__doc__ or "tolerance" in amod.__doc__.lower()


def test_module_source_no_json_import_batch12():
    """本模块不直接处理 JSON。"""
    source = inspect.getsource(amod)
    assert "import json" not in source


# ---------- signatures 第十二批 ----------


def test_signature_figure_caption_prf_2_params_batch12():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_signature_figure_caption_prf_document_annotation_optional_batch12():
    sig = inspect.signature(figure_caption_prf)
    for name in ("document", "annotation"):
        annot = sig.parameters[name].annotation
        annot_str = annot if isinstance(annot, str) else str(annot)
        assert "dict" in annot_str
        assert "None" in annot_str


def test_signature_figure_caption_prf_return_dict_batch12():
    sig = inspect.signature(figure_caption_prf)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_signature_chunk_boundary_prf_3_params_batch12():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch12():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_signature_chunk_boundary_prf_tolerance_annotation_int_batch12():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    annot = p.annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "int" in annot_str


def test_signature_chunk_boundary_prf_tolerance_kind_batch12():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_return_dict_batch12():
    sig = inspect.signature(chunk_boundary_prf)
    annot = sig.return_annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "dict" in annot_str


def test_all_functions_no_var_kwargs_batch12():
    for fn in [figure_caption_prf, chunk_boundary_prf]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第十二批 ----------


def test_module_name_evaluation_annotation_metrics_batch12():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_dunder_file_endswith_annotation_metrics_py_batch12():
    sep = os.sep
    assert amod.__file__.endswith(
        "evaluation" + sep + "annotation_metrics.py"
    ) or amod.__file__.endswith("evaluation/annotation_metrics.py")


def test_module_user_function_count_2_batch12():
    funcs = [
        n for n, v in vars(amod).items()
        if inspect.isfunction(v) and v.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_no_user_classes_batch12():
    classes = [
        n for n, v in vars(amod).items()
        if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_user_constants_count_1_batch12():
    consts = [
        n for n, v in vars(amod).items()
        if not n.startswith("__")
        and not callable(v)
        and not inspect.isclass(v)
        and not inspect.ismodule(v)
        and n not in ("annotations",)  # 排除 future 注入
    ]
    assert set(consts) == {"PARSER_DOES_NOT_EMIT_RELATIONS"}


def test_module_dunder_all_exact_batch12():
    assert hasattr(amod, "__all__")
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_module_dunder_all_len_3_batch12():
    assert len(amod.__all__) == 3


def test_module_uses_future_annotations_batch12():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:25])
    assert "from __future__ import annotations" in head


def test_module_parser_constant_is_str_batch12():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


# ---------- 端到端集成第十二批 ----------


def test_e2e_full_chain_perfect_match_batch12():
    """完整链路：3 chunks + 2 anchors 精确匹配。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "alpha"},
            {"id": "c2", "text": "beta"},
            {"id": "c3", "text": "gamma"},
        ]
    }
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "alpha", "position": "after"},
            {"marker": "beta", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
    assert out["_tolerance_chars"]["value"] == 0


def test_e2e_full_chain_no_match_at_all_batch12():
    """完全无匹配：anchors 都不匹配 stream 中的边界。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    # stream = "a b"，预测边界 1
    # anchor "c" before → 找不到 → missing marker
    annot = {"chunk_boundary_anchors": [{"marker": "nonexistent", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "_missing_markers" in out


def test_e2e_combined_chain_figure_and_chunk_batch12():
    """figure_caption_prf 和 chunk_boundary_prf 同时使用。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}

    fc = figure_caption_prf(doc, annot)
    cb = chunk_boundary_prf(doc, annot, tolerance_chars=0)

    # figure_caption 全 null
    for v in fc.values():
        assert v["value"] is None
    # chunk_boundary 完美匹配
    assert cb["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_combined_chain_idempotent_batch12():
    """多次调用结果一致。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}

    out1 = chunk_boundary_prf(doc, annot)
    out2 = chunk_boundary_prf(doc, annot)
    assert out1 == out2


def test_e2e_combined_chain_full_metrics_update_pattern_batch12():
    """模拟 metrics.update() 用法：两个函数返回 dict 合并。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}

    base_metrics = {"some_other_metric": {"value": 1.0}}
    base_metrics.update(figure_caption_prf(doc, annot))
    base_metrics.update(chunk_boundary_prf(doc, annot))

    # 应包含原 key + figure_caption + chunk_boundary + _tolerance_chars
    assert "some_other_metric" in base_metrics
    assert "figure_caption_precision" in base_metrics
    assert "chunk_boundary_precision" in base_metrics
    assert "_tolerance_chars" in base_metrics


def test_e2e_combined_chain_minimal_doc_batch12():
    """最小 doc（只有空 chunks list）→ no_predicted_boundaries。"""
    doc = {"chunks": []}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_combined_chain_minimal_annotation_batch12():
    """annotation 有其他 key 但缺 chunk_boundary_anchors → 视为 []。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"other_key": "value"}  # 有 key 但无 chunk_boundary_anchors
    out = chunk_boundary_prf(doc, annot)
    # annotation truthy 但 anchors 默认 [] → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_e2e_combined_chain_dict_serializable_batch12():
    """输出可 JSON 序列化。"""
    doc = {"chunks": [{"id": "c1", "text": "a"}, {"id": "c2", "text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_full_chain_tolerant_match_batch12():
    """大容差下，预测边界距离 anchor 远也能匹配。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "abcdefghijklmnopqrstuvwxyz"},
            {"id": "c2", "text": "next"},
        ]
    }
    # stream = "abcdefghijklmnopqrstuvwxyz next"
    # 预测边界 = 26
    # anchor "next" before → 27（"next" 起始位置）
    # |26 - 27| = 1 ≤ 5 → 匹配
    annot = {"chunk_boundary_anchors": [{"marker": "next", "position": "before"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_combined_chain_with_paired_chunks_batch12():
    """模拟多 chunk + 多 anchor 一对一匹配。"""
    doc = {
        "chunks": [
            {"id": "c1", "text": "first"},
            {"id": "c2", "text": "second"},
            {"id": "c3", "text": "third"},
            {"id": "c4", "text": "fourth"},
        ]
    }
    # stream = "first second third fourth"
    # 预测边界 = 5, 12, 17
    # anchors: first after=5, second after=12, third after=17
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "first", "position": "after"},
            {"marker": "second", "position": "after"},
            {"marker": "third", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0
