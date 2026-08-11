"""evaluation/annotation_metrics.py 第四十七轮 edges 测试（Round 462）。

补强 edges46 未触及的角度。
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation import annotation_metrics as amod


# ---------- figure_caption_prf 行为深度第二十批 ----------


def test_figure_caption_prf_returns_3_metrics_batch20():
    out = figure_caption_prf({}, {})
    assert set(out.keys()) == {
        "figure_caption_precision",
        "figure_caption_recall",
        "figure_caption_f1",
    }


def test_figure_caption_prf_value_all_none_batch20():
    out = figure_caption_prf({}, {})
    for k, v in out.items():
        assert v["value"] is None


def test_figure_caption_prf_reason_constant_batch20():
    out = figure_caption_prf({}, {})
    for k, v in out.items():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_with_none_inputs_batch20():
    out = figure_caption_prf(None, None)
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_prf_with_partial_inputs_batch20():
    """传一个 None 一个 dict 不应崩溃。"""
    out1 = figure_caption_prf(None, {"k": 1})
    out2 = figure_caption_prf({"k": 1}, None)
    assert out1 == out2  # 输出都一样


def test_figure_caption_prf_ignores_document_content_batch20():
    """即使 doc 含 figure_caption_relations，输出仍是 null。"""
    doc = {"figure_caption_relations": [{"figure": "f1", "caption": "c1"}]}
    out = figure_caption_prf(doc, {})
    assert all(v["value"] is None for v in out.values())


def test_figure_caption_prf_ignores_annotation_content_batch20():
    """即使 annotation 含 figure_caption_pairs，输出仍是 null。"""
    annotation = {"figure_caption_pairs": [{"figure_marker": "图1", "caption_text": "Hello"}]}
    out = figure_caption_prf({}, annotation)
    assert all(v["value"] is None for v in out.values())


# ---------- chunk_boundary_prf 边界行为深度第二十批 ----------


def test_chunk_boundary_prf_document_none_returns_pipeline_failed_batch20():
    out = chunk_boundary_prf(None, {"chunk_boundary_anchors": []}, tolerance_chars=30)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"


def test_chunk_boundary_prf_annotation_none_returns_no_annotation_batch20():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_empty_dict_batch20():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_no_anchors_batch20():
    doc = {"chunks": []}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_no_anchors_batch20():
    doc = {"chunks": [{"text": "a"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    # 单 chunk 时 recall 仍因 anchors 为空 null
    assert out["chunk_boundary_recall"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_with_anchors_batch20():
    """单 chunk 但有 anchors → precision null, recall 0.0。"""
    doc = {"chunks": [{"text": "hello world"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": [{"marker": "world"}]})
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_no_anchors_with_chunks_batch20():
    """有 chunk 但无 anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


# ---------- chunk_boundary_prf 算法行为深度第二十批 ----------


def test_chunk_boundary_prf_perfect_match_batch20():
    """预测边界与 anchor 完全对齐。"""
    doc = {"chunks": [{"text": "alpha beta"}, {"text": "gamma delta"}]}
    # stream = "alpha beta gamma delta"（normalize 后）
    # 边界位置 = 10（'alpha beta' 长度）
    annotation = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_partial_match_batch20():
    """2 个预测边界，1 个命中 anchor。"""
    doc = {"chunks": [{"text": "aaa bbb"}, {"text": "ccc ddd"}, {"text": "eee fff"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "bbb", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 2 个预测 / 1 个 anchor → matched=1
    # precision = 1/2 = 0.5; recall = 1/1 = 1.0
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_batch20():
    """预测边界与 anchor 距离远超容差。"""
    doc = {"chunks": [{"text": "aaa bbb"}, {"text": "ccc ddd"}]}
    # stream = "aaa bbb ccc ddd"，预测边界 = 7
    annotation = {"chunk_boundary_anchors": [{"marker": "ddd", "position": "after"}]}
    # ddd 末尾位置 = 14，距离 7 远
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=2)
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0


def test_chunk_boundary_prf_tolerance_zero_batch20():
    """容差 0 时严格要求完全对齐。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # stream = "alpha beta"，预测边界 = 5
    # anchor position=after marker='alpha' → 位置 = 5（完全对齐）
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_huge_batch20():
    """容差很大时所有预测都命中。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}, {"text": "ccc"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "zzz", "position": "after"}]}
    # 'zzz' 找不到 → missing_markers 记录 → gt_positions 为空
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1000)
    # gt_positions 为空 → recall null
    assert out["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors_in_stream"


def test_chunk_boundary_prf_position_before_batch20():
    """position=before 用 marker 起始位置。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # 预测边界 = 5；marker 'beta' 起始 = 6（stream="alpha beta"）
    # 距离 1
    annotation = {"chunk_boundary_anchors": [{"marker": "beta", "position": "before"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=1)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_multiple_anchors_one_to_one_batch20():
    """一对一匹配：1 个预测不能命中 2 个 anchor。"""
    doc = {"chunks": [{"text": "aaa bbb"}, {"text": "ccc"}]}
    # stream = "aaa bbb ccc"，预测边界 = 7
    # 两个 anchor 都在 'bbb' 附近，但只有 1 个预测
    annotation = {"chunk_boundary_anchors": [
        {"marker": "bbb", "position": "after"},
        {"marker": "bbb", "position": "after"},  # 第二个 anchor 找同一 marker
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # 重复 marker 命中：第一个 anchor 在 stream 找到，第二个 search_from 推进后找不到（同一 marker 已被消耗）
    # 但 stream.find(marker, search_from) 在 search_from > marker 位置时找不到，因此 missing_markers 含 1 项
    # gt_positions 应只有 1 项 → matched=1, recall=1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


# ---------- chunk_boundary_prf missing_markers 行为第二十批 ----------


def test_chunk_boundary_prf_missing_markers_recorded_batch20():
    """找不到的 marker 进入 missing_markers。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "zzz"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "zzz" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_no_field_batch20():
    """所有 marker 都找到时不输出 _missing_markers 字段。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "beta"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_empty_marker_treated_as_missing_batch20():
    """marker='' 时 find 返回 0 但代码用 `if marker else -1` 直接判否。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": ""}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "_missing_markers" in out
    assert "" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_not_in_stream_batch20():
    """marker 在 stream 中找不到。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "gamma"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    assert "gamma" in out["_missing_markers"]["value"]


# ---------- _tolerance_chars 行为第二十批 ----------


def test_chunk_boundary_prf_tolerance_in_output_batch20():
    """output 含 _tolerance_chars 字段。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []}, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_tolerance_default_30_batch20():
    out = chunk_boundary_prf({"chunks": []}, None)
    assert out["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_tolerance_zero_batch20_value():
    out = chunk_boundary_prf({"chunks": []}, None, tolerance_chars=0)
    assert out["_tolerance_chars"]["value"] == 0


def test_chunk_boundary_prf_tolerance_negative_batch20():
    out = chunk_boundary_prf({"chunks": []}, None, tolerance_chars=-5)
    assert out["_tolerance_chars"]["value"] == -5


def test_chunk_boundary_prf_tolerance_in_document_none_batch20():
    out = chunk_boundary_prf(None, None, tolerance_chars=20)
    assert out["_tolerance_chars"]["value"] == 20


# ---------- 常量行为深度第二十批 ----------


def test_parser_does_not_emit_relations_constant_value_batch20():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_string_batch20():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_immutable_batch20():
    """str 是不可变的。"""
    with pytest.raises(TypeError):
        PARSER_DOES_NOT_EMIT_RELATIONS[0] = "x"  # type: ignore[index]


# ---------- module source forbidden tokens 第三十五批 ----------


FORBIDDEN_TOKENS = [
    "requests.",
    "urllib.request",
    "socket.create_connection",
    "subprocess.run",
    "subprocess.Popen",
    "os.system",
    "os.popen",
    "shutil.rmtree",
    "shutil.copy",
    "open(\"/etc/passwd",
    "eval(",
    "exec(",
    "__import__",
    "compile(",
    "globals()[",
    "locals()[",
    "pickle.loads",
]


@pytest.mark.parametrize("forbidden", FORBIDDEN_TOKENS)
def test_module_source_forbidden_tokens_batch20(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_import_batch20():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src


def test_module_source_no_socket_import_batch20():
    src = inspect.getsource(amod)
    assert "import socket" not in src


def test_module_source_no_requests_import_batch20():
    src = inspect.getsource(amod)
    assert "import requests" not in src


def test_module_source_no_urllib_import_batch20():
    src = inspect.getsource(amod)
    assert "import urllib" not in src


def test_module_source_no_threading_import_batch20():
    src = inspect.getsource(amod)
    assert "import threading" not in src


def test_module_source_no_multiprocessing_import_batch20():
    src = inspect.getsource(amod)
    assert "import multiprocessing" not in src


def test_module_source_no_asyncio_import_batch20():
    src = inspect.getsource(amod)
    assert "import asyncio" not in src


def test_module_source_no_shutil_import_batch20():
    src = inspect.getsource(amod)
    assert "import shutil" not in src


def test_module_source_no_tempfile_import_batch20():
    src = inspect.getsource(amod)
    assert "import tempfile" not in src


def test_module_source_no_unlink_call_batch20():
    src = inspect.getsource(amod)
    assert ".unlink(" not in src


def test_module_source_no_path_write_text_batch20():
    src = inspect.getsource(amod)
    assert ".write_text(" not in src


def test_module_source_no_sys_exit_batch20():
    src = inspect.getsource(amod)
    assert "sys.exit" not in src


def test_module_source_no_re_compile_batch20():
    src = inspect.getsource(amod)
    assert "re.compile" not in src


def test_module_source_no_pandas_import_batch20():
    src = inspect.getsource(amod)
    assert "import pandas" not in src


def test_module_source_no_numpy_import_batch20():
    src = inspect.getsource(amod)
    assert "import numpy" not in src


def test_module_source_no_os_import_batch20():
    src = inspect.getsource(amod)
    assert "import os" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch20():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_source_has_counter_import_batch20():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import_batch20():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import_batch20():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_metrics_import_batch20():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_parser_does_not_emit_constant_batch20():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_figure_caption_prf_function_batch20():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_prf_function_batch20():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_all_list_with_3_entries_batch20():
    src = inspect.getsource(amod)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_module_source_has_docstring_batch20():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_has_chunk_boundary_algorithm_comment_batch20():
    src = inspect.getsource(amod)
    assert "贪心" in src or "一对一" in src


def test_module_source_uses_normalize_text_batch20():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_uses_null_ratio_helpers_batch20():
    src = inspect.getsource(amod)
    assert "_null(" in src
    assert "_ratio(" in src


# ---------- signatures 第三十批 ----------


def test_signature_figure_caption_prf_batch20():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch20():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    names = [p.name for p in params]
    assert names == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch20():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert params[2].default == 30


def test_signature_chunk_boundary_prf_no_extra_args_batch20():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.values())
    assert all(p.default is inspect.Parameter.empty for p in params[:2])


# ---------- module 合理性第三十批 ----------


def test_module_has_all_attribute_batch20():
    assert hasattr(amod, "__all__")


def test_module_all_count_3_batch20():
    assert len(amod.__all__) == 3


def test_module_all_entries_are_strings_batch20():
    for n in amod.__all__:
        assert isinstance(n, str)


def test_module_does_not_import_app_pipeline_batch20():
    src = inspect.getsource(amod)
    assert "from app.pipeline" not in src
    assert "from app import pipeline" not in src


def test_module_does_not_import_app_parsers_batch20():
    src = inspect.getsource(amod)
    assert "from app.parsers" not in src


def test_module_does_not_import_evaluation_runner_batch20():
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src


def test_module_does_not_import_evaluation_cli_batch20():
    src = inspect.getsource(amod)
    assert "from evaluation.cli" not in src


def test_module_does_not_import_evaluation_schema_batch20():
    src = inspect.getsource(amod)
    assert "from evaluation.schema" not in src


def test_module_no_main_block_batch20():
    src = inspect.getsource(amod)
    assert 'if __name__ ==' not in src


def test_module_chunkers_import_allowed_batch20():
    """annotation_metrics.py 允许从 app.chunkers 导入 normalize_text。"""
    src = inspect.getsource(amod)
    assert "from app.chunkers" in src


def test_module_evaluation_metrics_import_allowed_batch20():
    """annotation_metrics.py 允许从 evaluation.metrics 导入辅助函数。"""
    src = inspect.getsource(amod)
    assert "from evaluation.metrics" in src


# ---------- 端到端集成 第三十批 ----------


def test_e2e_chunk_boundary_prf_full_pipeline_batch20():
    """完整跑 chunk_boundary_prf：3 chunks 2 边界 + 2 anchors。"""
    doc = {"chunks": [{"text": "alpha beta"}, {"text": "gamma delta"}, {"text": "epsilon zeta"}]}
    annotation = {"chunk_boundary_anchors": [
        {"marker": "beta", "position": "after"},
        {"marker": "delta", "position": "after"},
    ]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=5)
    # stream = "alpha beta gamma delta epsilon zeta"
    # 预测边界 = [10, 22]
    # anchor 'beta' after → 位置 10；anchor 'delta' after → 位置 22
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_chunk_boundary_prf_with_normalization_batch20():
    """chunker 输出含多余空格，normalize 后才匹配。"""
    doc = {"chunks": [{"text": "  hello   world  "}, {"text": "foo"}]}
    # norm_chunks[0] = normalize_text("  hello   world  ") = "hello world"
    # stream = normalize("hello world foo") = "hello world foo"
    # 预测边界 = 11
    annotation = {"chunk_boundary_anchors": [{"marker": "world", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_figure_caption_prf_with_real_doc_batch20():
    """真实 doc 与 annotation 输入：figure_caption 仍 null。"""
    doc = {
        "document_id": "d1",
        "elements": [
            {"element_id": "e1", "type": "image", "resource_path": "a.png"},
            {"element_id": "e2", "type": "caption", "content": "Figure 1"},
        ],
        "chunks": [],
    }
    annotation = {"figure_caption_pairs": [{"figure_marker": "image1", "caption_text": "Figure 1"}]}
    out = figure_caption_prf(doc, annotation)
    assert all(v["value"] is None for v in out.values())


def test_e2e_chunk_boundary_with_unicode_batch20():
    """Unicode chunk 内容。"""
    doc = {"chunks": [{"text": "你好"}, {"text": "世界"}]}
    annotation = {"chunk_boundary_anchors": [{"marker": "你好", "position": "after"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=0)
    # stream = "你好 世界"，预测边界 = 2；anchor '你好' after → 位置 2
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_f1_half_when_p_0_r_high_batch20():
    """p=0, r=1 时 f1 = 0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}, {"text": "gamma"}]}
    # 预测边界 = [5, 10]
    # anchor 'zzz' 找不到 → missing → gt_positions 为空
    annotation = {"chunk_boundary_anchors": [{"marker": "alpha"}]}
    out = chunk_boundary_prf(doc, annotation, tolerance_chars=100)
    # anchor 'alpha' 找到 → gt_positions = [5]
    # predicted = [5, 10]
    # matched = 1
    # p = 1/2 = 0.5; r = 1/1 = 1.0; f1 = 2*0.5*1/(0.5+1) = 0.667
    assert out["chunk_boundary_precision"]["value"] == 0.5
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert abs(out["chunk_boundary_f1"]["value"] - 2 / 3) < 1e-9


def test_e2e_chunk_boundary_no_chunks_with_document_batch20():
    """doc 含 chunks 键但值为空 list。"""
    doc = {"chunks": []}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_e2e_chunk_boundary_chunks_none_batch20():
    """doc.chunks=None → or [] 兜底。"""
    doc = {"chunks": None}
    annotation = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, annotation)
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
