"""evaluation/annotation_metrics.py 第三十六轮 edges 测试（Round 385）。

补强 edges35 未触及的角度：
- figure_caption_prf 行为深度第九批（None document / None annotation / empty dict / 非 None annotation / 多个 metric key / reason 常量）
- chunk_boundary_prf 行为深度第九批（5 个 branch + 容差边界 + missing markers + Unicode marker + 字段顺序 / idempotent / no mutate）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第七批（imports + PARSER_DOES_NOT_EMIT_RELATIONS 字面量 + 算法关键调用）
- signatures 第九批（2 funcs + param kinds + return types）
- module 合理性第九批（__all__ + dunder file + docstring + 2 funcs + 1 constant）
- 端到端集成第九批（无标注场景 / 真实标注匹配 / 容差边界 / position before/after 混合）
"""

from __future__ import annotations

import inspect
import json
import types
from typing import Any

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation import annotation_metrics as amod


# ---------- figure_caption_prf 行为深度第九批 ----------


def test_figure_caption_prf_returns_dict():
    out = figure_caption_prf(None, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_three_keys():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_keys_in_order():
    out = figure_caption_prf(None, None)
    assert list(out.keys()) == [
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    ]


def test_figure_caption_prf_all_values_null():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_document_still_null():
    """即使 document 提供，figure_caption_* 仍 null（parser 不输出 caption relation）。"""
    doc = {"elements": [{"type": "image"}, {"type": "caption"}]}
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_annotation_still_null():
    """即使 annotation 提供，figure_caption_* 仍 null。"""
    annot = {"figure_caption_pairs": [["f1", "c1"]]}
    out = figure_caption_prf(None, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_with_both_args_still_null():
    doc = {"elements": [{"type": "image"}]}
    annot = {"figure_caption_pairs": [["f1", "c1"]]}
    out = figure_caption_prf(doc, annot)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_each_value_is_dict():
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert isinstance(v, dict)
        assert "value" in v
        assert "reason" in v


def test_figure_caption_prf_idempotent():
    out1 = figure_caption_prf(None, None)
    out2 = figure_caption_prf(None, None)
    assert out1 == out2


def test_figure_caption_prf_no_mutate_input_dict():
    doc = {"elements": [{"type": "image"}]}
    snapshot = json.dumps(doc)
    _ = figure_caption_prf(doc, None)
    assert json.dumps(doc) == snapshot


def test_figure_caption_prf_accepts_empty_dict_doc():
    out = figure_caption_prf({}, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_accepts_empty_dict_annot():
    out = figure_caption_prf(None, {})
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_returns_dict_with_value_reason_only():
    """figure_caption_* 每个 metric 只含 value + reason 两 key。"""
    out = figure_caption_prf(None, None)
    for v in out.values():
        assert set(v.keys()) == {"value", "reason"}


# ---------- chunk_boundary_prf 行为深度第九批 ----------


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_includes_tolerance_record():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_document_none_default_tolerance_30():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_no_annotation_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": []}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_empty_annotation_returns_no_annotation():
    out = chunk_boundary_prf({"chunks": []}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_falsy_annotation_returns_no_annotation():
    """falsy annotation（如空 dict）→ no_annotation。"""
    out = chunk_boundary_prf({"chunks": []}, {})
    assert out["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_less_than_two_chunks_no_anchors():
    """少于 2 chunks + 无 anchors → no_predicted_boundaries（recall/p/f1 都 null）。"""
    out = chunk_boundary_prf({"chunks": [{"text": "a"}]}, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_less_than_two_chunks_with_anchors():
    """少于 2 chunks + 有 anchors → precision null + recall=0.0 + f1 null。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_no_anchors_returns_no_gt():
    """≥2 chunks + 无 anchors → no_ground_truth_anchors。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": []},
    )
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_two_chunks_match_perfect():
    """两 chunks，标注 anchor 在 chunk 边界（hello 后），tolerance=5 → match。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=5,
    )
    # predicted boundary at pos len("hello") = 5；gt anchor at len("hello") = 5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_two_chunks_no_match_outside_tolerance():
    """两 chunks，标注 anchor 远离边界 → 0 match。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello world", "position": "after"}]},
        tolerance_chars=1,
    )
    # gt position = len("hello world") = 11, predicted = 5, |5-11|=6 > 1 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_negative_tolerance():
    """负容差 → abs(pv-gv) <= 负数 永远 False（除非 pv == gv）。

    实际：tolerance=-1 时，任何 |d| >= 0 > -1 → no match。
    但若 pv == gv（d=0），0 <= -1 为 False → 仍 no match。
    所以即使精确匹配，负 tolerance 也得不到。
    """
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=-1,
    )
    # |5-5|=0 <= -1 False → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_zero_tolerance_exact_match():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=0,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_three_chunks_two_internal_boundaries():
    """3 chunks → 2 个内部边界。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]},
        {
            "chunk_boundary_anchors": [
                {"marker": "a", "position": "after"},
                {"marker": "b", "position": "after"},
            ]
        },
        tolerance_chars=2,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_unknown_position_defaults_after():
    """position 不是 "before" → 当成 "after"。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "unknown"}]},
        tolerance_chars=5,
    )
    # "unknown" 走 else 分支 → 用 find_pos + len(marker)
    # 即默认 "after"：gt = 5；predicted = 5 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_before():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]},
        tolerance_chars=2,
    )
    # gt = position of "world" = 6 (5 + space); predicted = 5; |5-6|=1 <= 2 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_unicode_marker():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "中文"}, {"text": "测试"}]},
        {"chunk_boundary_anchors": [{"marker": "中文", "position": "after"}]},
        tolerance_chars=2,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_empty_marker():
    """marker="" → find returns 0（first char）→ 但 stream.find("", x) 返回 x。

    代码：find_pos = stream.find(marker, search_from) if marker else -1
    → marker="" 视为 falsy → find_pos=-1 → missing_markers.append("")
    """
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]},
        tolerance_chars=10,
    )
    # marker 为 falsy → missing → gt_positions 空 → recall null
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "_missing_markers" in out


def test_chunk_boundary_prf_missing_marker_recorded():
    """marker 不在 stream 中 → 加入 missing_markers。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "nonexistent", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_no_record():
    """所有 markers 都找到 → 不出 _missing_markers key。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_no_chunk_text_key():
    """chunk dict 缺 text key → c.get('text') or '' = ''。"""
    out = chunk_boundary_prf(
        {"chunks": [{"id": "c1"}, {"id": "c2"}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
        tolerance_chars=10,
    )
    # stream = normalize(" ") = ""
    # marker "x" 找不到 → missing
    assert "_missing_markers" in out


def test_chunk_boundary_prf_chunk_text_none():
    """chunk.text is None → c.get('text') or '' = ''。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": None}, {"text": None}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
        tolerance_chars=10,
    )
    assert "_missing_markers" in out


def test_chunk_boundary_prf_extra_keys_in_anchor():
    """anchor dict 含多余 keys 不影响（只用 marker + position）。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {
            "chunk_boundary_anchors": [
                {"marker": "hello", "position": "after", "extra": "ok", "id": "a1"}
            ]
        },
        tolerance_chars=5,
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predictions():
    """anchors 多于 predictions → 部分 anchor 未匹配 → recall < 1。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {
            "chunk_boundary_anchors": [
                {"marker": "a", "position": "after"},
                {"marker": "b", "position": "after"},
                {"marker": "x", "position": "after"},
            ]
        },
        tolerance_chars=2,
    )
    # predicted = [1] (after "a")
    # gt positions: 1 (after "a"), 3 (after "b"... 但 stream 是 "a b"，所以 b 在 pos 2，after=3)
    # 实际 stream: "a b"
    # gt[0]=after "a"=1, gt[1]=after "b"=3, gt[2]="x" 不存在 → missing
    # matched: predicted[0]=1 vs gt[0]=1, d=0 → match
    # 其余 gt 无对应 predicted → matched=1, num_gt=2
    assert out["chunk_boundary_recall"]["value"] == 0.5


def test_chunk_boundary_prf_more_predictions_than_anchors():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
        tolerance_chars=2,
    )
    # predicted = [1, 3] (after a, after b)
    # gt = [1] → matched=1
    # precision = 1/2
    assert out["chunk_boundary_precision"]["value"] == 0.5


def test_chunk_boundary_prf_idempotent():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    out2 = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    assert out1 == out2


def test_chunk_boundary_prf_does_not_mutate_document():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    snapshot = json.dumps(doc)
    _ = chunk_boundary_prf(
        doc,
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=5,
    )
    assert json.dumps(doc) == snapshot


def test_chunk_boundary_prf_does_not_mutate_annotation():
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    snapshot = json.dumps(annot)
    _ = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        annot,
        tolerance_chars=5,
    )
    assert json.dumps(annot) == snapshot


def test_chunk_boundary_prf_returns_dict_type():
    out = chunk_boundary_prf(None, None)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_includes_tolerance_record():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_default_tolerance_30():
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []})
    assert out["_tolerance_chars"]["value"] == 30


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
        "global ",
    ],
)
def test_annotation_metrics_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(amod)
    assert token not in source


def test_annotation_metrics_source_no_async_def():
    source = inspect.getsource(amod)
    assert "async def" not in source


def test_annotation_metrics_source_no_yield():
    source = inspect.getsource(amod)
    assert "yield" not in source


def test_annotation_metrics_source_no_walrus():
    source = inspect.getsource(amod)
    assert ":=" not in source


def test_annotation_metrics_source_no_unlink():
    source = inspect.getsource(amod)
    assert "unlink" not in source


def test_annotation_metrics_source_no_remove():
    source = inspect.getsource(amod)
    assert ".remove(" not in source


def test_annotation_metrics_source_no_logging():
    source = inspect.getsource(amod)
    assert "logging" not in source
    assert "logger" not in source


def test_annotation_metrics_source_no_sleep():
    source = inspect.getsource(amod)
    assert "time.sleep" not in source


def test_annotation_metrics_source_no_print():
    source = inspect.getsource(amod)
    assert "print(" not in source


def test_annotation_metrics_source_no_open_call():
    source = inspect.getsource(amod)
    assert "open(" not in source


def test_annotation_metrics_source_no_main_block():
    source = inspect.getsource(amod)
    assert "if __name__" not in source


# ---------- module source 字符串精确补强第七批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(amod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_counter():
    source = inspect.getsource(amod)
    assert "from collections import Counter" in source


def test_module_source_imports_typing_any():
    source = inspect.getsource(amod)
    assert "from typing import Any" in source


def test_module_source_imports_normalize_text():
    source = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in source


def test_module_source_imports_null_helpers():
    source = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in source


def test_module_source_has_PARSER_DOES_NOT_EMIT_RELATIONS_constant():
    source = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in source


def test_module_source_has_figure_caption_prf_definition():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_has_chunk_boundary_prf_definition():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_uses_normalize_text_call():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_uses_null_call():
    source = inspect.getsource(amod)
    assert "_null(" in source


def test_module_source_uses_ratio_call():
    source = inspect.getsource(amod)
    assert "_ratio(" in source


def test_module_source_no_class_def():
    source = inspect.getsource(amod)
    assert "class " not in source


def test_module_source_docstring_present():
    assert amod.__doc__ is not None


def test_module_source_docstring_mentions_caption():
    assert "caption" in amod.__doc__.lower()


def test_module_source_docstring_mentions_chunk_boundary():
    assert "chunk_boundary" in amod.__doc__ or "chunk boundary" in amod.__doc__.lower()


def test_module_source_docstring_mentions_tolerance():
    """docstring 提到容差。"""
    assert "容差" in amod.__doc__ or "tolerance" in amod.__doc__.lower()


def test_module_source_has_chunk_boundary_anchors_key():
    source = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in source


def test_module_source_has_tolerance_chars_param():
    source = inspect.getsource(amod)
    assert "tolerance_chars" in source


def test_module_source_has_pipeline_failed_reason():
    source = inspect.getsource(amod)
    assert "pipeline_failed" in source


def test_module_source_has_no_annotation_reason():
    source = inspect.getsource(amod)
    assert "no_annotation" in source


def test_module_source_has_no_predicted_boundaries_reason():
    source = inspect.getsource(amod)
    assert "no_predicted_boundaries" in source


def test_module_source_has_no_ground_truth_anchors_reason():
    source = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in source


# ---------- signatures 第九批 ----------


def test_signature_figure_caption_prf_2_params():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_signature_figure_caption_prf_param_names():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters) == ["document", "annotation"]


def test_signature_figure_caption_prf_param_kinds():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_figure_caption_prf_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_figure_caption_prf_return_annotation():
    sig = inspect.signature(figure_caption_prf)
    ra = sig.return_annotation
    assert ra == "dict[str, dict[str, Any]]" or ra == dict[str, dict[str, Any]]


def test_signature_chunk_boundary_prf_3_params():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_signature_chunk_boundary_prf_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters) == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_param_kinds():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_chunk_boundary_prf_tolerance_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    p = sig.parameters["tolerance_chars"]
    assert p.default == 30


def test_signature_chunk_boundary_prf_return_annotation():
    sig = inspect.signature(chunk_boundary_prf)
    ra = sig.return_annotation
    assert ra == "dict[str, dict[str, Any]]" or ra == dict[str, dict[str, Any]]


def test_signature_funcs_function_type():
    assert inspect.isfunction(figure_caption_prf)
    assert inspect.isfunction(chunk_boundary_prf)


def test_signature_funcs_module_eq():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


# ---------- module 合理性第九批 ----------


def test_module_all_attribute_value():
    assert amod.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list():
    assert isinstance(amod.__all__, list)


def test_module_all_entries_unique():
    assert len(amod.__all__) == len(set(amod.__all__))


def test_module_has_dunder_file():
    assert hasattr(amod, "__file__")


def test_module_dunder_file_endswith_annotation_metrics_py():
    import os
    sep = os.sep
    assert amod.__file__.endswith("evaluation" + sep + "annotation_metrics.py") or amod.__file__.endswith(
        "evaluation/annotation_metrics.py"
    )


def test_module_name_is_evaluation_annotation_metrics():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_has_PARSER_DOES_NOT_EMIT_RELATIONS_constant():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_PARSER_DOES_NOT_EMIT_RELATIONS_value():
    assert amod.PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_module_has_2_user_functions():
    funcs = [
        n for n, v in vars(amod).items()
        if inspect.isfunction(v) and v.__module__ == amod.__name__
    ]
    assert set(funcs) == {"figure_caption_prf", "chunk_boundary_prf"}


def test_module_no_user_classes():
    classes = [
        n for n, v in vars(amod).items()
        if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_no_top_level_call():
    source = inspect.getsource(amod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "class ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "PARSER_DOES_NOT_EMIT_RELATIONS",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped:
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present():
    assert amod.__doc__ is not None
    assert len(amod.__doc__) > 30


# ---------- 端到端集成第九批 ----------


def test_e2e_figure_caption_always_null_with_full_data():
    doc = {"elements": [{"type": "image"}, {"type": "caption", "text": "fig 1"}]}
    annot = {"figure_caption_pairs": [["e1", "e2"]]}
    out = figure_caption_prf(doc, annot)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_perfect_match():
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_partial_match():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "b", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_e2e_chunk_boundary_unicode_full():
    doc = {"chunks": [{"text": "中文段落一"}, {"text": "中文段落二"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "中文段落一", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_with_missing_marker():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {
        "chunk_boundary_anchors": [
            {"marker": "a", "position": "after"},
            {"marker": "nonexistent", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, annot, tolerance_chars=2)
    assert "_missing_markers" in out
    assert "nonexistent" in out["_missing_markers"]["value"]


def test_e2e_combined_metrics_no_overlap():
    """figure_caption_prf 和 chunk_boundary_prf 返回的 keys 不重叠。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    fc = figure_caption_prf(doc, annot)
    cb = chunk_boundary_prf(doc, annot)
    # 没有公共 key（除了内部 _tolerance_chars / _missing_markers）
    fc_public = {k for k in fc if not k.startswith("_")}
    cb_public = {k for k in cb if not k.startswith("_")}
    assert fc_public & cb_public == set()


def test_e2e_idempotent_combined():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    fc1 = figure_caption_prf(doc, annot)
    fc2 = figure_caption_prf(doc, annot)
    cb1 = chunk_boundary_prf(doc, annot)
    cb2 = chunk_boundary_prf(doc, annot)
    assert fc1 == fc2
    assert cb1 == cb2


def test_e2e_does_not_mutate_inputs_combined():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_snapshot = json.dumps(doc)
    annot_snapshot = json.dumps(annot)
    _ = figure_caption_prf(doc, annot)
    _ = chunk_boundary_prf(doc, annot)
    assert json.dumps(doc) == doc_snapshot
    assert json.dumps(annot) == annot_snapshot


def test_e2e_kwargs_call():
    """通过 keyword 调用。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, annot, tolerance_chars=5)
    out2 = chunk_boundary_prf(document=doc, annotation=annot, tolerance_chars=5)
    assert out1 == out2


def test_e2e_positional_call():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    annot = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, annot, 5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
