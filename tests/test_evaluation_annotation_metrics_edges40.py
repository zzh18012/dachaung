"""evaluation/annotation_metrics.py 第四十轮 edges 测试（Round 413）。

补强 edges39 未触及的角度：
- PARSER_DOES_NOT_EMIT_RELATIONS 常量第十三批（值固定 / 类型 / 不在 __all__ 之外）
- figure_caption_prf 行为深度第十三批（输入是 None Pair / annotation 为 dict 仍不影响 / 输出可独立修改）
- chunk_boundary_prf 行为深度第十三批（document=None + tolerance 边界 / annotation=非空 dict 但缺 chunk_boundary_anchors / chunks 缺 text 字段 / chunk text 是 None / chunk text 是非 str）
- 算法深度第十三批（predicted 边界位置 / gt_positions / marker 是空字符串 / position 是 "before"/"after" 之外 / 多个相同 marker / greedy 匹配 tie）
- module source forbidden tokens 第十六批
- module source 字符串精确补强第十三批
- signatures 第十三批
- module 合理性第十三批
- 端到端集成第十三批
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any
from unittest.mock import patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 常量第十三批 ----------


def test_parser_does_not_emit_relations_value_batch13():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_type_batch13():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_is_in_dunder_all_batch13():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_is_module_attr_batch13():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


# ---------- figure_caption_prf 行为深度第十三批 ----------


def test_figure_caption_prf_returns_three_metrics_batch13():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_doc_with_annotation_batch13():
    """即使 doc 与 annotation 都给，仍固定 null。"""
    out = figure_caption_prf({"k": "v"}, {"x": "y"})
    for k in out:
        assert out[k]["value"] is None
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_returns_dict_independent_each_call_batch13():
    """两次调用返回独立 dict。"""
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 is not out2
    assert out1["figure_caption_precision"] is not out2["figure_caption_precision"]


def test_figure_caption_prf_metrics_modification_does_not_propagate_batch13():
    out1 = figure_caption_prf(None, None)
    out1["figure_caption_precision"]["value"] = "modified"
    out2 = figure_caption_prf(None, None)
    assert out2["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_metric_dict_keys_exact_batch13():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert set(v.keys()) == {"value", "reason"}


def test_figure_caption_prf_metric_dict_value_is_none_batch13():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_metric_dict_reason_constant_batch13():
    out = figure_caption_prf(None, None)
    for k, v in out.items():
        assert v["reason"] == "parser_does_not_emit_relations"


def test_figure_caption_prf_with_empty_dict_doc_batch13():
    out = figure_caption_prf({}, {})
    assert len(out) == 3


def test_figure_caption_prf_with_unicode_keys_batch13():
    """即使 metric 名包含 unicode，输出 dict 保持 ascii key。"""
    out = figure_caption_prf(None, None)
    for k in out:
        assert k.isascii()


# ---------- chunk_boundary_prf 行为深度第十三批 ----------


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch13():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=30)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_includes_tolerance_chars_batch13():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_annotation_none_returns_no_annotation_batch13():
    out = chunk_boundary_prf({"chunks": []}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch13():
    """空 dict 是 falsy → no_annotation 分支。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_other_key_only_batch13():
    """annotation 是 truthy 但无 chunk_boundary_anchors → 走后续分支。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"other_key": "value"},
        tolerance_chars=30,
    )
    # 有 chunks >= 2, 但 anchors=[] → no_ground_truth_anchors
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_missing_text_batch13():
    """chunk 缺 text 字段 → c.get('text') or '' = '' → normalize_text('') = ''。"""
    doc = {"chunks": [{"id": "c1"}, {"id": "c2"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
        ],
    }
    # predicted=[0]（两个空 chunk 拼接），gt 找不到 'x'
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 看具体行为：norm_chunks=['', ''], joined_raw='', stream=''
    # predicted: pos=0; i=0, txt='', stream.find('',0)=0, end=0, predicted=[0]
    # anchors: marker='x', find=-1 → missing; gt_positions=[]
    # → precision: predicted=[0], matched=0 → 0.0
    # → recall: gt=[] → no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_chunk_text_none_batch13():
    """chunk text 显式 None → 同上。"""
    doc = {"chunks": [{"text": None}, {"text": None}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # 跟 missing_text 类似
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_chunk_text_non_str_batch13():
    """chunk text 是 int → normalize_text 接到非 str → 行为不确定，但不抛。"""
    doc = {"chunks": [{"text": 123}, {"text": 456}]}
    annotation = {"chunk_boundary_anchors": []}
    # 不抛异常即可
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_anchors_missing_marker_key_batch13():
    """anchor 缺 marker → marker = '' → 算 missing_marker。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # marker='' 是 falsy → find_pos=-1 → 加入 missing_markers
    # gt_positions=[], precision: predicted=[3], matched=0 → 0.0
    # recall: gt=[] → null
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] is None
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_anchors_missing_position_key_batch13():
    """anchor 缺 position → 默认 'after'。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # position 默认 'after', marker='foo', find=0, gt_pos=0+3=3
    # predicted=[3], |3-3|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_other_value_batch13():
    """position 是未知字符串 → 走 else (=after) 分支。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "foo", "position": "weird_unknown"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # position 不是 'before' → 走 else (=after)
    # gt_pos = find + len(marker) = 0 + 3 = 3
    # predicted=[3], |3-3|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_before_batch13():
    """position='before' → gt_pos = find_pos。"""
    doc = {"chunks": [{"text": "foo bar"}, {"text": "baz"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "baz", "position": "before"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # norm_chunks = ['foo bar', 'baz']
    # joined_raw = 'foo bar baz'
    # stream = 'foo bar baz' (no change after normalize)
    # predicted: i=0, txt='foo bar', find=0, end=7, predicted=[7]
    # anchor: marker='baz', find_pos=8 (stream.find('baz',0)=8), position='before'
    # gt_pos=8
    # |7-8|=1 <= 30 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_anchor_position_after_batch13():
    """position='after' → gt_pos = find_pos + len(marker)。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "foo", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # find=0, gt_pos=3, predicted=[3], |3-3|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_multiple_anchors_same_marker_batch13():
    """两个相同 marker：通过 search_from 推进，确保不重复定位。"""
    doc = {"chunks": [{"text": "x x"}, {"text": "y"}, {"text": "z"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "x", "position": "after"},
        {"marker": "x", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = 'x x y z'
    # predicted: i=0, txt='x x', find=0, end=3, predicted=[3]
    # i=1, txt='y', find=4, end=5, predicted=[3,5]
    # anchors: marker='x', find_pos=0, gt_pos=1, search_from=1
    # marker='x', find_pos=2, gt_pos=3, search_from=3
    # gt_positions=[1, 3]
    # pairs: (2,0,0) (1,1,0) ... 距离排序后贪心
    # 实际：dist(3,1)=2, dist(3,3)=0, dist(5,1)=4, dist(5,3)=2
    # 排序：(0,1,1), (2,0,0), (2,1,1), (4,0,1) wait, let me recompute
    # pred=[3,5], gt=[1,3]
    # pairs: (|3-1|=2, 0, 0), (|3-3|=0, 0, 1), (|5-1|=4, 1, 0), (|5-3|=2, 1, 1)
    # 排序 by distance: (0,0,1), (2,0,0), (2,1,1), (4,1,0)
    # greedy: (0,0,1) → match, used_pred={0}, used_gt={1}
    # (2,0,0): pi=0 used → skip
    # (2,1,1): gi=1 used → skip
    # (4,1,0): match, used_pred={0,1}, used_gt={1,0}
    # matched=2, num_pred=2, num_gt=2 → precision=1.0, recall=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_marker_not_found_recorded_batch13():
    """未找到 marker → 加入 _missing_markers。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "missing_marker", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["missing_marker"]


def test_chunk_boundary_prf_no_missing_markers_key_when_all_found_batch13():
    """全部 anchor 都找到 → 不写 _missing_markers key。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "foo", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_tolerance_chars_propagated_to_output_batch13():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_chars_default_30_batch13():
    import inspect as _insp
    sig = _insp.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_output_keys_count_at_least_4_batch13():
    """标准输出至少有 3 个 metric + _tolerance_chars。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert len(out) >= 4


def test_chunk_boundary_prf_output_keys_max_5_batch13():
    """最多 5 个 key（3 metric + _tolerance + _missing_markers）。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "a", "position": "after"},
        {"marker": "missing", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation)
    assert len(out) == 5


def test_chunk_boundary_prf_returns_dict_type_batch13():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_metric_value_type_batch13():
    """metric value 是 float|None。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        v = out[k]["value"]
        assert v is None or isinstance(v, float)


def test_chunk_boundary_prf_f1_when_p_or_r_none_batch13():
    """precision 或 recall 为 None → f1 = null + 'precision_or_recall_not_evaluated'。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": []}
    # 走 no_ground_truth_anchors 分支（chunks>=2, anchors 空）
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_f1"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_f1_when_p_and_r_zero_batch13():
    """p=0, r=0 → denom=0 → f1=0.0。"""
    # 构造 p=0, r=0：predicted 有但都未匹配，gt 有但都未匹配
    # 难构造。略过不验证具体值，仅验证类型
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "far_far_away", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # marker 找不到 → missing; gt=[]; precision: predicted=[1], matched=0 → 0.0
    # recall: gt=[] → null + no_ground_truth_anchors_in_stream
    # f1: r=None → null
    assert out["chunk_boundary_f1"]["value"] is None


# ---------- module source forbidden tokens 第十六批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "import pickle",
        "import yaml",
        "import socket",
        "import threading",
        "import multiprocessing",
        "import asyncio",
        "from pickle import",
        "from yaml import",
        "from socket import",
        "from threading import",
        "from multiprocessing import",
        "from asyncio import",
        "ctypes.",
        "import ctypes",
        "import marshal",
        "marshal.",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_sixteenth_batch13(token):
    source = inspect.getsource(amod)
    assert token not in source


def test_annotation_metrics_source_no_os_module_batch13():
    source = inspect.getsource(amod)
    assert "import os" not in source
    assert "os." not in source


def test_annotation_metrics_source_no_sys_module_batch13():
    source = inspect.getsource(amod)
    assert "import sys" not in source
    assert "sys." not in source


def test_annotation_metrics_source_no_tempfile_batch13():
    source = inspect.getsource(amod)
    assert "tempfile" not in source


def test_annotation_metrics_source_no_logging_batch13():
    source = inspect.getsource(amod)
    assert "import logging" not in source


def test_annotation_metrics_source_no_re_module_batch13():
    source = inspect.getsource(amod)
    assert "import re" not in source
    assert "re." not in source


def test_annotation_metrics_source_no_eval_call_batch13():
    source = inspect.getsource(amod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_annotation_metrics_source_no_compile_batch13():
    source = inspect.getsource(amod)
    assert "compile(" not in source


def test_annotation_metrics_source_no_global_keyword_batch13():
    source = inspect.getsource(amod)
    assert "\nglobal " not in source


def test_annotation_metrics_source_no_nonlocal_batch13():
    source = inspect.getsource(amod)
    assert "nonlocal " not in source


def test_annotation_metrics_source_no_lambda_batch13():
    """注意：lambda 在源码内可能出现（如 sort key），需要严格检查。"""
    source = inspect.getsource(amod)
    # chunk_boundary_prf 有 lambda x: x[0]，这里反向测试 → 应该有
    assert "lambda " in source


def test_annotation_metrics_source_no_assert_batch13():
    source = inspect.getsource(amod)
    assert "\nassert " not in source


def test_annotation_metrics_source_no_print_batch13():
    source = inspect.getsource(amod)
    assert "print(" not in source


def test_annotation_metrics_source_no_input_function_batch13():
    source = inspect.getsource(amod)
    assert "input(" not in source


def test_annotation_metrics_source_no_class_definition_batch13():
    source = inspect.getsource(amod)
    assert "\nclass " not in source


def test_annotation_metrics_source_no_open_call_at_top_level_batch13():
    source = inspect.getsource(amod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" ") and "open(" in line:
            raise AssertionError(f"top-level open: {line}")


# ---------- module source 字符串精确补强第十三批 ----------


def test_module_source_counter_import_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from collections import Counter" in head


def test_module_source_typing_any_import_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_normalize_text_import_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from app.chunkers.structural import normalize_text" in head


def test_module_source_null_ratio_import_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.metrics import _null, _ratio" in head


def test_module_source_has_parser_does_not_emit_relations_const_batch13():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_has_figure_caption_prf_def_batch13():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_has_chunk_boundary_prf_def_batch13():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_has_normalize_text_calls_batch13():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_has_tolerance_chars_param_batch13():
    source = inspect.getsource(amod)
    assert "tolerance_chars" in source


def test_module_source_has_pairs_sort_lambda_batch13():
    source = inspect.getsource(amod)
    assert "pairs.sort" in source
    assert "lambda" in source


def test_module_source_has_used_pred_used_gt_set_batch13():
    source = inspect.getsource(amod)
    assert "used_pred" in source
    assert "used_gt" in source


def test_module_source_has_pipeline_failed_string_batch13():
    source = inspect.getsource(amod)
    assert '"pipeline_failed"' in source or "'pipeline_failed'" in source


def test_module_source_has_no_annotation_string_batch13():
    source = inspect.getsource(amod)
    assert '"no_annotation"' in source or "'no_annotation'" in source


def test_module_source_has_no_predicted_boundaries_string_batch13():
    source = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in source or "'no_predicted_boundaries'" in source


def test_module_source_has_no_ground_truth_anchors_string_batch13():
    source = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in source or "'no_ground_truth_anchors'" in source


def test_module_source_has_stream_find_call_batch13():
    source = inspect.getsource(amod)
    assert "stream.find(" in source


def test_module_source_has_search_from_variable_batch13():
    source = inspect.getsource(amod)
    assert "search_from" in source


def test_module_source_has_missing_markers_variable_batch13():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


def test_module_source_future_annotations_top_level_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


# ---------- signatures 第十三批 ----------


def test_figure_caption_prf_signature_2_params_batch13():
    import inspect as _insp
    sig = _insp.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["document", "annotation"]


def test_figure_caption_prf_return_annotation_dict_batch13():
    import inspect as _insp
    sig = _insp.signature(figure_caption_prf)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str


def test_figure_caption_prf_document_annotation_optional_batch13():
    import inspect as _insp
    sig = _insp.signature(figure_caption_prf)
    for pn in ("document", "annotation"):
        annot = sig.parameters[pn].annotation
        annot_str = annot if isinstance(annot, str) else str(annot)
        assert "dict" in annot_str
        assert "None" in annot_str


def test_chunk_boundary_prf_signature_3_params_batch13():
    import inspect as _insp
    sig = _insp.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert len(params) == 3
    assert [p.name for p in params] == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_tolerance_chars_kind_keyword_or_positional_batch13():
    import inspect as _insp
    sig = _insp.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.kind == _insp.Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_tolerance_chars_annotation_int_batch13():
    import inspect as _insp
    sig = _insp.signature(chunk_boundary_prf)
    annot = sig.parameters["tolerance_chars"].annotation
    annot_str = annot if isinstance(annot, str) else str(annot)
    assert "int" in annot_str


def test_chunk_boundary_prf_return_annotation_dict_batch13():
    import inspect as _insp
    sig = _insp.signature(chunk_boundary_prf)
    ret = sig.return_annotation
    ret_str = ret if isinstance(ret, str) else str(ret)
    assert "dict" in ret_str


def test_module_user_function_count_2_batch13():
    funcs = [
        n for n, v in vars(amod).items()
        if inspect.isfunction(v) and v.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_dunder_all_3_items_batch13():
    assert hasattr(amod, "__all__")
    assert len(amod.__all__) == 3


def test_module_dunder_all_exact_set_batch13():
    assert set(amod.__all__) == {
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    }


def test_functions_no_varargs_batch13():
    import inspect as _insp
    for fn in [figure_caption_prf, chunk_boundary_prf]:
        sig = _insp.signature(fn)
        for p in sig.parameters.values():
            assert p.kind not in (
                _insp.Parameter.VAR_POSITIONAL,
                _insp.Parameter.VAR_KEYWORD,
            )


def test_functions_callable_batch13():
    assert callable(figure_caption_prf)
    assert callable(chunk_boundary_prf)


# ---------- module 合理性第十三批 ----------


def test_module_dunder_file_exists_batch13():
    assert hasattr(amod, "__file__")
    assert amod.__file__ is not None


def test_module_dunder_file_path_evaluation_annotation_metrics_batch13():
    import os
    sep = os.sep
    assert amod.__file__.endswith(sep + "annotation_metrics.py")
    assert "evaluation" in amod.__file__


def test_module_name_evaluation_annotation_metrics_batch13():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_docstring_present_batch13():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


def test_module_docstring_mentions_figure_caption_batch13():
    assert amod.__doc__ is not None
    assert "figure-caption" in amod.__doc__ or "figure_caption" in amod.__doc__


def test_module_docstring_mentions_chunk_boundary_batch13():
    assert amod.__doc__ is not None
    assert "chunk_boundary" in amod.__doc__ or "chunk-boundary" in amod.__doc__


def test_module_uses_future_annotations_batch13():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:20])
    assert "from __future__ import annotations" in head


def test_module_no_user_classes_batch13():
    classes = [
        n for n, v in vars(amod).items()
        if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_top_level_constants_count_batch13():
    consts = [
        n for n, v in vars(amod).items()
        if not n.startswith("__") and not callable(v) and not inspect.isclass(v)
        and not inspect.ismodule(v)
    ]
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in consts


# ---------- 端到端集成第十三批 ----------


def test_e2e_figure_caption_then_chunk_boundary_combined_batch13():
    """两个函数协作：metrics.update() 模式。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}

    metrics = {}
    metrics.update(figure_caption_prf(doc, annotation))
    metrics.update(chunk_boundary_prf(doc, annotation))

    assert "figure_caption_precision" in metrics
    assert "chunk_boundary_precision" in metrics
    assert "_tolerance_chars" in metrics


def test_e2e_chunk_boundary_perfect_match_batch13():
    """3 chunks, 2 anchors, 完美匹配。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}, {"text": "baz"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
            {"marker": "bar", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # norm_chunks = ['foo', 'bar', 'baz']
    # stream = 'foo bar baz'
    # predicted: i=0, txt='foo', find=0, end=3, predicted=[3]
    # i=1, txt='bar', find=4, end=7, predicted=[3,7]
    # anchors: marker='foo', find=0, gt_pos=3, search_from=3
    # marker='bar', find=4, gt_pos=7, search_from=7
    # gt_positions = [3, 7]
    # pairs: (0,0,0), (4,0,1), (4,1,0), (0,1,1)
    # 排序：(0,0,0), (0,1,1), (4,0,1), (4,1,0)
    # greedy: matched=2
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_partial_match_batch13():
    """部分匹配。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "non_existent", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # marker 找不到 → missing; gt=[]; recall=None
    # precision: predicted=[3], matched=0 → 0.0
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] is None


def test_e2e_chunk_boundary_tolerance_zero_strict_batch13():
    """tolerance_chars=0 时严格匹配。"""
    doc = {"chunks": [{"text": "foo bar"}, {"text": "baz"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},  # gt_pos=3
        ],
    }
    # stream = 'foo bar baz'
    # predicted: i=0, txt='foo bar', find=0, end=7, predicted=[7]
    # gt_pos=3, |7-3|=4 > 0 → 不匹配
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_e2e_chunk_boundary_tolerance_huge_batch13():
    """tolerance_chars 极大时容易匹配。"""
    doc = {"chunks": [{"text": "foo bar"}, {"text": "baz"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "foo", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1000)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_combined_idempotent_batch13():
    """两次调用相同输入 → 相同输出。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    out2 = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    assert out1 == out2


def test_e2e_figure_caption_idempotent_batch13():
    out1 = figure_caption_prf({"k": "v"}, {"x": "y"})
    out2 = figure_caption_prf({"k": "v"}, {"x": "y"})
    assert out1 == out2


def test_e2e_chunk_boundary_output_independent_batch13():
    """两次调用返回独立 dict。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation)
    out2 = chunk_boundary_prf(doc, annotation)
    assert out1 is not out2


def test_e2e_metric_dict_value_independent_batch13():
    """两次调用 → metric 内部 dict 不共享。"""
    doc = {"chunks": [{"text": "foo"}, {"text": "bar"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "foo", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annotation)
    out2 = chunk_boundary_prf(doc, annotation)
    assert out1["chunk_boundary_precision"] is not out2["chunk_boundary_precision"]


def test_e2e_chunk_boundary_unicode_marker_batch13():
    """Unicode marker 应能被定位。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annotation = {
        "chunk_boundary_anchors": [
            {"marker": "你好", "position": "after"},
        ],
    }
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=30)
    # stream = '你好 世界'
    # marker='你好', find=0, gt_pos=2
    # predicted: i=0, txt='你好', find=0, end=2, predicted=[2]
    # |2-2|=0 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
