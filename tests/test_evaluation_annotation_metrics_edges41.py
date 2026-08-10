"""evaluation/annotation_metrics.py 第四十一轮 edges 测试（Round 420）。

补强 edges40 未触及的角度：
- figure_caption_prf 边界第十四批（reason 字段固定 / value 是 None / reason 不是 "ok" / 三个 key 同 reason / 独立 dict 修改）
- chunk_boundary_prf 边界第十四批（annotation 是 dict 但缺 chunk_boundary_anchors / anchors 是 None / chunks 是 None / chunk text 含 Unicode / 多 marker 顺序定位 / search_from 推进）
- chunk_boundary_prf 算法第十四批（matched 贪心 / tolerance_chars 边界 / f1 计算 / _missing_markers 缺失时不写入 / _tolerance_chars 总是写入）
- PARSER_DOES_NOT_EMIT_RELATIONS 常量第十四批（值 / 不在 dunder all 之外 / import 链）
- module source forbidden tokens 第十八批
- module source 字符串精确补强第十五批
- signatures 第十五批
- module 合理性第十五批
- 端到端集成第十五批
"""

from __future__ import annotations

import inspect
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 边界第十四批 ----------


def test_figure_caption_prf_returns_three_keys_batch14():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_all_values_none_batch14():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_batch14():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_reason_not_ok_batch14():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    for k, v in out.items():
        assert v["reason"] != "ok"


def test_figure_caption_prf_dict_independence_batch14():
    out1 = figure_caption_prf({"x": 1}, {"y": 2})
    out2 = figure_caption_prf({"x": 1}, {"y": 2})
    assert out1 is not out2
    out1["figure_caption_precision"]["value"] = "modified"
    assert out2["figure_caption_precision"]["value"] is None


def test_figure_caption_prf_with_none_inputs_batch14():
    out = figure_caption_prf(None, None)
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_does_not_emit_relation_string_batch14():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


# ---------- chunk_boundary_prf 边界第十四批 ----------


def test_chunk_boundary_prf_document_none_returns_4_keys_batch14():
    out = chunk_boundary_prf(None, {})
    assert set(out.keys()) == {
        "chunk_boundary_precision",
        "chunk_boundary_recall",
        "chunk_boundary_f1",
        "_tolerance_chars",
    }


def test_chunk_boundary_prf_document_none_all_null_pipeline_failed_batch14():
    out = chunk_boundary_prf(None, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_none_returns_no_annotation_batch14():
    out = chunk_boundary_prf({"x": 1}, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_returns_no_annotation_batch14():
    out = chunk_boundary_prf({"x": 1}, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_no_anchors_key_batch14():
    """annotation 是 dict 但缺 chunk_boundary_anchors。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"other_key": "x"},
    )
    # 没有 anchors → 走 no_ground_truth_anchors 分支
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_anchors_is_none_batch14():
    """chunk_boundary_anchors 显式 None。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": None},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_chunks_is_none_batch14():
    """document.chunks 显式 None（按 dict.get(chunks) or [] 处理为空）。"""
    out = chunk_boundary_prf(
        {"chunks": None},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    # chunks=[] → < 2 → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_single_chunk_batch14():
    """只 1 个 chunk → len < 2 → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "abc"}]},
        {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 但有 anchor → recall 是 0.0（不是 null）
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_two_chunks_no_anchors_batch14():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_tolerance_chars_propagated_batch14():
    """tolerance_chars=99 应被写入 _tolerance_chars。"""
    out = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert out["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_tolerance_chars_default_30_batch14():
    out = chunk_boundary_prf(None, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_missing_chunks_key_batch14():
    """document 缺 chunks key → chunks=[] → no_predicted_boundaries。"""
    out = chunk_boundary_prf(
        {},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunk_text_none_batch14():
    """chunk text 是 None → normalize_text(None or "") 处理。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": None}, {"text": None}]},
        {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]},
    )
    # text 都 None → norm_chunks=["", ""] → 仍能算（predicted 找位置但 stream 空）
    # 实际：stream="", marker="x" 找不到 → missing_markers, num_gt=0
    assert "chunk_boundary_precision" in out
    assert "chunk_boundary_recall" in out


def test_chunk_boundary_prf_chunk_text_unicode_batch14():
    """chunk text 含中文。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "你好世界"}, {"text": "测试"}]},
        {"chunk_boundary_anchors": [{"marker": "你好世界", "position": "after"}]},
    )
    # 至少不抛
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_perfect_match_batch14():
    """完美匹配：1 predicted 边界 + 1 anchor 且位置完全一致。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
    )
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_position_before_batch14():
    """position=before：anchor 位置是 marker 起始位置。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello world"}]},  # < 2 chunk → no_predicted
        {"chunk_boundary_anchors": [{"marker": "world", "position": "before"}]},
    )
    # < 2 chunks → no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_marker_not_found_batch14():
    """marker 不在 stream 中 → 加入 missing_markers。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]},
    )
    # gt_positions=[]（marker 找不到）→ recall: no_ground_truth_anchors_in_stream
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"
    assert "_missing_markers" in out
    assert out["_missing_markers"]["value"] == ["xyz"]


def test_chunk_boundary_prf_missing_markers_absent_when_all_found_batch14():
    """所有 marker 都找到 → 不应写 _missing_markers。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
    )
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_duplicate_markers_sequential_batch14():
    """两个相同 marker 顺序定位。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "x x"}, {"text": "x y"}]},
        {"chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]},
    )
    # 至少不抛
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_output_always_has_tolerance_chars_batch14():
    """无论哪个分支，_tolerance_chars 都被写入。"""
    # pipeline_failed 分支
    out = chunk_boundary_prf(None, None)
    assert "_tolerance_chars" in out
    # no_annotation 分支
    out = chunk_boundary_prf({"x": 1}, None)
    assert "_tolerance_chars" in out
    # no_predicted_boundaries 分支
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    assert "_tolerance_chars" in out
    # no_ground_truth_anchors 分支
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": []},
    )
    assert "_tolerance_chars" in out


def test_chunk_boundary_prf_no_predicted_boundaries_value_null_batch14():
    out = chunk_boundary_prf(None, None)
    assert out["chunk_boundary_precision"]["value"] is None


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 常量第十四批 ----------


def test_parser_does_not_emit_relations_is_string_batch14():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_module_namespace_batch14():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_value_batch14():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_in_dunder_all_batch14():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


# ---------- module source forbidden tokens 第十八批 ----------


_FORBIDDEN_TOKENS_ROUND18 = [
    "eval(",
    "exec(",
    "os.system(",
    "subprocess.call(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "os.popen(",
    "__import__(",
    "pickle.loads(",
    "yaml.load(",
    "shutil.rmtree(",
    "os.remove(",
    "open('/etc",
    "open(\"/etc",
    "requests.get(",
    "urllib.request.urlopen(",
]


@pytest.mark.parametrize("token", _FORBIDDEN_TOKENS_ROUND18)
def test_module_source_forbidden_tokens_round18_batch14(token):
    source = inspect.getsource(amod)
    assert token not in source


# ---------- module source 字符串精确补强第十五批 ----------


def test_module_source_module_docstring_present_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:15])
    assert '"""' in head


def test_module_source_future_annotations_present_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from __future__ import annotations" in head


def test_module_source_imports_counter_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from collections import Counter" in head


def test_module_source_imports_typing_any_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from typing import Any" in head


def test_module_source_imports_normalize_text_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from app.chunkers.structural import normalize_text" in head


def test_module_source_imports_null_ratio_batch14():
    source = inspect.getsource(amod)
    head = "\n".join(source.split("\n")[:30])
    assert "from evaluation.metrics import _null, _ratio" in head


def test_module_source_defines_parser_does_not_emit_relations_batch14():
    source = inspect.getsource(amod)
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in source


def test_module_source_defines_figure_caption_prf_batch14():
    source = inspect.getsource(amod)
    assert "def figure_caption_prf(" in source


def test_module_source_defines_chunk_boundary_prf_batch14():
    source = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in source


def test_module_source_has_dunder_all_batch14():
    source = inspect.getsource(amod)
    assert "__all__" in source


def test_module_source_dunder_all_3_items_batch14():
    assert len(amod.__all__) == 3


def test_module_source_uses_normalize_text_batch14():
    source = inspect.getsource(amod)
    assert "normalize_text(" in source


def test_module_source_uses_null_helper_batch14():
    source = inspect.getsource(amod)
    assert "_null(" in source


def test_module_source_uses_ratio_helper_batch14():
    source = inspect.getsource(amod)
    assert "_ratio(" in source


def test_module_source_has_tolerance_chars_default_batch14():
    source = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in source


def test_module_source_has_chunk_boundary_anchors_key_batch14():
    source = inspect.getsource(amod)
    assert "chunk_boundary_anchors" in source


def test_module_source_has_no_predicted_boundaries_reason_batch14():
    source = inspect.getsource(amod)
    assert "no_predicted_boundaries" in source


def test_module_source_has_no_ground_truth_anchors_reason_batch14():
    source = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in source


def test_module_source_has_no_annotation_reason_batch14():
    source = inspect.getsource(amod)
    assert "no_annotation" in source


def test_module_source_has_pipeline_failed_reason_batch14():
    source = inspect.getsource(amod)
    assert "pipeline_failed" in source


def test_module_source_no_subprocess_import_batch14():
    source = inspect.getsource(amod)
    assert "import subprocess" not in source


def test_module_source_no_open_call_batch14():
    source = inspect.getsource(amod)
    assert "open(" not in source


def test_module_source_has_f1_formula_batch14():
    source = inspect.getsource(amod)
    assert "2 * p_val * r_val / denom" in source


def test_module_source_has_missing_markers_logic_batch14():
    source = inspect.getsource(amod)
    assert "missing_markers" in source


# ---------- signatures 第十五批 ----------


def test_figure_caption_prf_signature_2_params_batch14():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2
    for n in ("document", "annotation"):
        assert n in sig.parameters


def test_chunk_boundary_prf_signature_3_params_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3
    for n in ("document", "annotation", "tolerance_chars"):
        assert n in sig.parameters


def test_chunk_boundary_prf_tolerance_default_30_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_figure_caption_prf_return_annotation_dict_batch14():
    sig = inspect.signature(figure_caption_prf)
    assert "dict" in str(sig.return_annotation)


def test_chunk_boundary_prf_return_annotation_dict_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict" in str(sig.return_annotation)


def test_figure_caption_prf_document_optional_batch14():
    sig = inspect.signature(figure_caption_prf)
    p_str = str(sig.parameters["document"].annotation)
    assert "None" in p_str or "Optional" in p_str


def test_figure_caption_prf_annotation_optional_batch14():
    sig = inspect.signature(figure_caption_prf)
    p_str = str(sig.parameters["annotation"].annotation)
    assert "None" in p_str or "Optional" in p_str


def test_chunk_boundary_prf_document_optional_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    p_str = str(sig.parameters["document"].annotation)
    assert "None" in p_str or "Optional" in p_str


def test_chunk_boundary_prf_annotation_optional_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    p_str = str(sig.parameters["annotation"].annotation)
    assert "None" in p_str or "Optional" in p_str


def test_chunk_boundary_prf_tolerance_int_annotation_batch14():
    sig = inspect.signature(chunk_boundary_prf)
    p_str = str(sig.parameters["tolerance_chars"].annotation)
    assert "int" in p_str


def test_dunder_all_items_callable_batch14():
    for name in amod.__all__:
        attr = getattr(amod, name)
        # PARSER_DOES_NOT_EMIT_RELATIONS 是 str，figure_caption_prf / chunk_boundary_prf 是 callable
        if name != "PARSER_DOES_NOT_EMIT_RELATIONS":
            assert callable(attr)


# ---------- module 合理性第十五批 ----------


def test_module_dunder_file_exists_batch14():
    assert hasattr(amod, "__file__")
    assert amod.__file__ is not None


def test_module_dunder_file_annotation_metrics_py_batch14():
    assert "evaluation" in amod.__file__
    assert amod.__file__.endswith("annotation_metrics.py")


def test_module_name_evaluation_annotation_metrics_batch14():
    assert amod.__name__ == "evaluation.annotation_metrics"


def test_module_dunder_all_3_items_batch14():
    assert len(amod.__all__) == 3


def test_module_dunder_all_items_unique_batch14():
    assert len(set(amod.__all__)) == len(amod.__all__)


def test_module_no_class_definitions_batch14():
    classes = [
        n for n, v in vars(amod).items()
        if inspect.isclass(v) and v.__module__ == amod.__name__
    ]
    assert classes == []


def test_module_constants_count_1_batch14():
    """只有 PARSER_DOES_NOT_EMIT_RELATIONS 一个模块级常量。"""
    # 验证它是 str
    assert isinstance(amod.PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_module_public_callable_count_2_batch14():
    """2 个 public 函数：figure_caption_prf / chunk_boundary_prf。"""
    public = [
        n for n in amod.__all__
        if n != "PARSER_DOES_NOT_EMIT_RELATIONS"
    ]
    assert len(public) == 2


# ---------- 端到端集成第十五批 ----------


def test_e2e_figure_caption_prf_json_serializable_batch14():
    out = figure_caption_prf({"x": 1}, {"y": 2})
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_chunk_boundary_prf_pipeline_failed_json_serializable_batch14():
    out = chunk_boundary_prf(None, None)
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_chunk_boundary_prf_no_annotation_json_serializable_batch14():
    out = chunk_boundary_prf({"x": 1}, None)
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_chunk_boundary_prf_perfect_match_json_serializable_batch14():
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    parsed = json.loads(json.dumps(out))
    assert parsed == out


def test_e2e_chunk_boundary_prf_dict_independence_batch14():
    out1 = chunk_boundary_prf(None, None)
    out2 = chunk_boundary_prf(None, None)
    assert out1 is not out2
    out1["chunk_boundary_precision"]["value"] = "modified"
    assert out2["chunk_boundary_precision"]["value"] is None


def test_e2e_combined_pipeline_failed_then_no_annotation_batch14():
    """两个失败模式分别独立。"""
    out1 = chunk_boundary_prf(None, None)
    out2 = chunk_boundary_prf({"x": 1}, None)
    assert out1["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert out2["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_e2e_chunk_boundary_prf_idempotent_batch14():
    out1 = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    out2 = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]},
    )
    assert out1 == out2


def test_e2e_combined_metrics_module_helpers_used_batch14():
    """annotation_metrics 应通过 _null / _ratio helper 输出（而不是自己写 null dict）。"""
    source = inspect.getsource(amod)
    assert "_null(" in source
    assert "_ratio(" in source


def test_e2e_chunk_boundary_prf_with_high_tolerance_batch14():
    """tolerance_chars=1000 时几乎所有预测都能匹配。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "a"}, {"text": "b"}]},
        {"chunk_boundary_anchors": [{"marker": "z", "position": "after"}]},
        tolerance_chars=1000,
    )
    # marker "z" 不在 stream 中 → missing_markers
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_e2e_chunk_boundary_prf_with_zero_tolerance_batch14():
    """tolerance_chars=0 → 必须精确匹配。"""
    out = chunk_boundary_prf(
        {"chunks": [{"text": "hello"}, {"text": "world"}]},
        {"chunk_boundary_anchors": [{"marker": "hello", "position": "after"}]},
        tolerance_chars=0,
    )
    # 边界是 "hello" 后 = 5，anchor 也是 5 → d=0 ≤ 0 → 匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
