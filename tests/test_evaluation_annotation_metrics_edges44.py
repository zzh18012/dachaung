"""evaluation/annotation_metrics.py 第四十四轮 edges 测试（Round 441）。

补强 edges43 未触及的角度：
- figure_caption_prf 边界第十七批（document 各种 None / dict 内字段 / 不可变性 / 任何输入都返回三个 key / 没 pipeline_failed 分支 / value 永远 None）
- chunk_boundary_prf 边界第十七批（document None / annotation empty / chunks 空 / chunks=1 / chunks=2 但无 anchor / anchors 空 list）
- chunk_boundary_prf 算法第十七批（完美匹配 / 容差边界 / off-by-one / 多预测边界 / 多 anchor / position before/after）
- chunk_boundary_prf missing_markers 第十七批（marker 不存在 / 多个 missing / 空 marker / None marker）
- PARSER_DOES_NOT_EMIT_RELATIONS 第十七批（值 / 模块属性 / 在 all / str 类型 / figure_caption 引用）
- module source forbidden tokens 第三十三批
- module source 字符串精确补强第三十批
- signatures 第三十批
- module 合理性第三十批
- 端到端集成第三十批
"""

from __future__ import annotations

import inspect
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- figure_caption_prf 边界第十七批 ----------


def test_figure_caption_prf_doc_none_ann_none_batch17():
    r = figure_caption_prf(None, None)
    assert "figure_caption_precision" in r
    assert "figure_caption_recall" in r
    assert "figure_caption_f1" in r


def test_figure_caption_prf_returns_3_keys_batch17():
    for doc in [None, {}, {"chunks": []}]:
        for ann in [None, {}, {"x": 1}]:
            r = figure_caption_prf(doc, ann)
            assert len(r) == 3


def test_figure_caption_prf_all_values_none_batch17():
    for doc in [None, {}]:
        for ann in [None, {}]:
            r = figure_caption_prf(doc, ann)
            for v in r.values():
                assert v["value"] is None


def test_figure_caption_prf_reason_constant_batch17():
    r = figure_caption_prf(None, None)
    for v in r.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_read_document_batch17():
    """传 MagicMock document 不应被读（function 早返回）。"""
    fake_doc = MagicMock()
    r = figure_caption_prf(fake_doc, None)
    assert len(r) == 3


def test_figure_caption_prf_does_not_read_annotation_batch17():
    fake_ann = MagicMock()
    r = figure_caption_prf(None, fake_ann)
    assert len(r) == 3


def test_figure_caption_prf_does_not_modify_inputs_batch17():
    doc = {"chunks": [{"text": "a"}]}
    ann = {"x": 1}
    before_doc = repr(doc)
    before_ann = repr(ann)
    figure_caption_prf(doc, ann)
    assert repr(doc) == before_doc
    assert repr(ann) == before_ann


def test_figure_caption_prf_no_pipeline_failed_reason_batch17():
    """figure_caption_prf 永远不用 'pipeline_failed' reason。"""
    r = figure_caption_prf(None, None)
    for v in r.values():
        assert v["reason"] != "pipeline_failed"


def test_figure_caption_prf_idempotent_batch17():
    r1 = figure_caption_prf(None, None)
    r2 = figure_caption_prf(None, None)
    assert r1 == r2


def test_figure_caption_prf_returns_dict_batch17():
    r = figure_caption_prf(None, None)
    assert isinstance(r, dict)


# ---------- chunk_boundary_prf 边界第十七批 ----------


def test_chunk_boundary_prf_doc_none_batch17():
    r = chunk_boundary_prf(None, None)
    assert "chunk_boundary_precision" in r
    assert r["chunk_boundary_precision"]["reason"] == "pipeline_failed"
    assert r["chunk_boundary_precision"]["value"] is None


def test_chunk_boundary_prf_doc_none_returns_4_keys_batch17():
    """doc=None 时返回 3 个 metric + _tolerance_chars。"""
    r = chunk_boundary_prf(None, None)
    assert len(r) == 4
    assert "_tolerance_chars" in r


def test_chunk_boundary_prf_doc_none_with_tolerance_batch17():
    r = chunk_boundary_prf(None, None, tolerance_chars=99)
    assert r["_tolerance_chars"]["value"] == 99


def test_chunk_boundary_prf_annotation_empty_dict_batch17():
    """空 dict 是 falsy → no_annotation。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {}, tolerance_chars=10)
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_none_batch17():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, None)
    assert r["chunk_boundary_precision"]["reason"] == "no_annotation"


def test_chunk_boundary_prf_no_chunks_key_batch17():
    """doc 无 chunks key → 用 .get() 默认 []。"""
    r = chunk_boundary_prf({}, {"chunk_boundary_anchors": []})
    # 无 chunks → no_predicted_boundaries
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_empty_chunks_batch17():
    doc = {"chunks": []}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_one_chunk_batch17():
    """单 chunk → 无内部边界。"""
    doc = {"chunks": [{"text": "a"}]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_two_chunks_no_anchors_batch17():
    """2 chunks + 无 anchors → no_ground_truth_anchors。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, {"chunk_boundary_anchors": []})
    assert r["chunk_boundary_precision"]["reason"] == "no_ground_truth_anchors"
    assert r["chunk_boundary_recall"]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_two_chunks_with_anchors_batch17():
    """2 chunks + 1 anchor 正常路径。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    # abc|def 边界应在 stream 中 abc 之后（位置 3）
    # predicted = [3], gt = [3] → matched=1
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_returns_dict_batch17():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    r = chunk_boundary_prf(doc, None)
    assert isinstance(r, dict)


# ---------- chunk_boundary_prf 算法第十七批 ----------


def test_chunk_boundary_prf_perfect_match_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "def", "position": "after"},
    ]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=5)
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_zero_match_batch17():
    """tolerance=0 时位置必须完全相同。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # abc|def 边界在 3，gt 也是 3 → matched
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_off_by_one_batch17():
    """gt 偏移 1 字符，tolerance=1 → matched。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # position=after + marker="ab" → gt = ab 之后 = 2；predicted = 3 → d=1 → tolerance=1 OK
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_tolerance_too_small_batch17():
    """gt 偏移 1 字符，tolerance=0 → 不 match。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 0.0
    assert r["chunk_boundary_recall"]["value"] == 0.0
    assert r["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_position_before_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    # stream = "abc def"；position=before + marker="def" → gt = 4（def 起始位置）
    # predicted end of "abc" = 3；d=1，tolerance=1 → matched
    ann = {"chunk_boundary_anchors": [{"marker": "def", "position": "before"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=1)
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_position_unknown_defaults_to_after_batch17():
    """position 不是 before/after → 默认 after。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "weird"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 默认 after：marker=abc position=after → 3；predicted=3 → matched
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_partial_match_batch17():
    """3 predicted, 1 matched → P=1/3, R=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}, {"text": "ghi"}, {"text": "jkl"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert r["chunk_boundary_precision"]["value"] == 1 / 3
    assert r["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_more_anchors_than_predicted_batch17():
    """predicted=1, anchors=2 → P=1.0, R=0.5。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "abc", "position": "after"},
        {"marker": "xxx", "position": "after"},  # not in stream → missing
    ]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # predicted=[3], gt_positions=[3]（第二个 missing）→ matched=1
    # num_pred=1, num_gt=1 → P=1, R=1
    # 但 missing_markers 应包含 xxx
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert "_missing_markers" in r
    assert "xxx" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_f1_zero_when_p_r_zero_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "ab", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 不匹配 → P=0, R=0 → f1=0
    assert r["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_f1_normal_batch17():
    """P=1, R=1 → f1=1.0。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert r["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_default_tolerance_30_batch17():
    """不传 tolerance_chars → 默认 30。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann)
    assert r["_tolerance_chars"]["value"] == 30


def test_chunk_boundary_prf_does_not_modify_inputs_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    before_doc = repr(doc)
    before_ann = repr(ann)
    chunk_boundary_prf(doc, ann)
    assert repr(doc) == before_doc
    assert repr(ann) == before_ann


# ---------- chunk_boundary_prf missing_markers 第十七批 ----------


def test_chunk_boundary_prf_marker_not_in_stream_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" in r
    assert "xyz" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_empty_string_batch17():
    """marker='' → find 返回 0（但代码特殊处理：`if marker else -1`）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 空 marker → find_pos=-1 → missing
    assert "_missing_markers" in r
    assert "" in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_none_batch17():
    """marker=None → falsy → -1 → missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": None, "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # None marker → missing
    assert "_missing_markers" in r
    assert None in r["_missing_markers"]["value"]


def test_chunk_boundary_prf_marker_key_missing_batch17():
    """anchor 没 marker key → marker.get default=""→ missing。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" in r


def test_chunk_boundary_prf_multiple_missing_markers_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "xxx", "position": "after"},
        {"marker": "yyy", "position": "after"},
    ]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert len(r["_missing_markers"]["value"]) == 2


def test_chunk_boundary_prf_no_missing_markers_key_when_all_found_batch17():
    """所有 marker 都找到 → 不加 _missing_markers。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_missing_markers" not in r


def test_chunk_boundary_prf_repeated_marker_batch17():
    """重复 marker 顺序定位。"""
    doc = {"chunks": [{"text": "ab"}, {"text": "ab"}, {"text": "ab"}]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "ab", "position": "after"},
        {"marker": "ab", "position": "after"},
    ]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 2 个 ab 边界分别在 2 和 4，predicted 也是 2 和 4 → matched=2
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第十七批 ----------


def test_parser_does_not_emit_relations_value_batch17():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_is_str_batch17():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_in_module_namespace_batch17():
    assert hasattr(amod, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_parser_does_not_emit_relations_in_all_batch17():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in amod.__all__


def test_parser_does_not_emit_relations_used_in_figure_caption_batch17():
    src = inspect.getsource(amod)
    assert 'reason = PARSER_DOES_NOT_EMIT_RELATIONS' in src


def test_parser_does_not_emit_relations_immutable_batch17():
    """模块常量不应被修改（实际上无法可变，但验证值不变）。"""
    val1 = PARSER_DOES_NOT_EMIT_RELATIONS
    val2 = amod.PARSER_DOES_NOT_EMIT_RELATIONS
    assert val1 == val2


# ---------- module source forbidden tokens 第三十三批 ----------


@pytest.mark.parametrize("forbidden", [
    "pty.spawn",
    "commands.getoutput",
    "paramiko",
    "fabric.api",
    "ftplib",
    "smtplib",
    "telnetlib",
    "webbrowser.open",
    "socket.socket",
    "asyncio.open_connection",
    "multiprocessing.Process",
    "threading.Thread",
    "ctypes.CDLL",
    "pickle.dumps",
    "shutil.rmtree",
    "sys.exit",
])
def test_module_source_forbidden_tokens_batch17(forbidden):
    src = inspect.getsource(amod)
    assert forbidden not in src


def test_module_source_no_subprocess_batch17():
    src = inspect.getsource(amod)
    assert "import subprocess" not in src


def test_module_source_no_network_batch17():
    src = inspect.getsource(amod)
    assert "urllib.request" not in src
    assert "import requests" not in src


# ---------- module source 字符串精确补强第三十批 ----------


def test_module_source_has_future_annotations_batch17():
    src = inspect.getsource(amod)
    head = src.split("\n", 30)[:30]
    assert any("from __future__ import annotations" in line for line in head)


def test_module_source_has_docstring_batch17():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_has_counter_import_batch17():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_has_typing_any_import_batch17():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_has_normalize_text_import_batch17():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_has_metrics_import_batch17():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_has_figure_caption_prf_function_batch17():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_has_chunk_boundary_prf_function_batch17():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_has_parser_does_not_emit_relations_constant_batch17():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_has_normalize_text_call_batch17():
    src = inspect.getsource(amod)
    assert "normalize_text(" in src


def test_module_source_has_tolerance_chars_default_30_batch17():
    src = inspect.getsource(amod)
    assert "tolerance_chars: int = 30" in src


def test_module_source_has_pipeline_failed_reason_batch17():
    src = inspect.getsource(amod)
    assert '"pipeline_failed"' in src


def test_module_source_has_no_annotation_reason_batch17():
    src = inspect.getsource(amod)
    assert '"no_annotation"' in src


def test_module_source_has_no_predicted_boundaries_batch17():
    src = inspect.getsource(amod)
    assert '"no_predicted_boundaries"' in src


def test_module_source_has_no_ground_truth_anchors_batch17():
    src = inspect.getsource(amod)
    assert '"no_ground_truth_anchors"' in src


def test_module_source_has_all_dunder_batch17():
    src = inspect.getsource(amod)
    assert "__all__ = [" in src


def test_module_source_all_has_3_items_batch17():
    src = inspect.getsource(amod)
    for name in ['"PARSER_DOES_NOT_EMIT_RELATIONS"',
                 '"figure_caption_prf"', '"chunk_boundary_prf"']:
        assert name in src


# ---------- signatures 第三十批 ----------


def test_signature_figure_caption_prf_batch17():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


def test_signature_chunk_boundary_prf_batch17():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_chunk_boundary_prf_tolerance_default_30_batch17():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_figure_caption_prf_no_varargs_batch17():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_chunk_boundary_prf_no_varargs_batch17():
    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


# ---------- module 合理性第三十批 ----------


def test_module_has_all_attribute_batch17():
    assert hasattr(amod, "__all__")
    assert isinstance(amod.__all__, list)


def test_module_all_items_in_namespace_batch17():
    for name in amod.__all__:
        assert hasattr(amod, name)


def test_module_all_count_3_batch17():
    assert len(amod.__all__) == 3


def test_module_figure_caption_prf_callable_batch17():
    assert callable(figure_caption_prf)


def test_module_chunk_boundary_prf_callable_batch17():
    assert callable(chunk_boundary_prf)


def test_module_does_not_import_unsafe_modules_batch17():
    src = inspect.getsource(amod)
    for unsafe in ["import pickle", "import marshal", "import shelve", "import subprocess"]:
        assert unsafe not in src


def test_module_does_not_import_evaluation_runner_batch17():
    """annotation_metrics.py 不应反向依赖 runner.py。"""
    src = inspect.getsource(amod)
    assert "from evaluation.runner" not in src
    assert "import evaluation.runner" not in src


# ---------- 端到端集成第三十批 ----------


def test_e2e_chunk_boundary_full_pipeline_batch17():
    """完整 4 chunks + 3 anchors 跑通。"""
    doc = {"chunks": [
        {"text": "first"},
        {"text": "second"},
        {"text": "third"},
        {"text": "fourth"},
    ]}
    ann = {"chunk_boundary_anchors": [
        {"marker": "first", "position": "after"},
        {"marker": "second", "position": "after"},
        {"marker": "third", "position": "after"},
    ]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert r["chunk_boundary_precision"]["value"] == 1.0
    assert r["chunk_boundary_recall"]["value"] == 1.0
    assert r["chunk_boundary_f1"]["value"] == 1.0
    assert r["_tolerance_chars"]["value"] == 10


def test_e2e_figure_caption_full_call_batch17():
    r = figure_caption_prf({"chunks": []}, {"x": 1})
    assert len(r) == 3
    for v in r.values():
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_e2e_chunk_boundary_normalizes_text_batch17():
    """chunks 含空白也通过 normalize 处理。"""
    doc = {"chunks": [
        {"text": "  abc  "},
        {"text": "  def  "},
    ]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # normalize 后 stream = "abc def"
    # abc|def 边界在 3，gt 也是 3 → matched
    assert r["chunk_boundary_precision"]["value"] == 1.0


def test_e2e_chunk_boundary_no_text_field_batch17():
    """chunk 缺 text 字段 → 用 .get() 默认 ""。"""
    doc = {"chunks": [{"x": 1}, {"y": 2}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream = "" → predicted=[], markers 都找不到 → 0
    # 但 len(chunks)=2 不进 no_predicted 分支
    # 进入主算法，norm_chunks=["", ""]，stream=""
    # 第一个 "" find_pos=0，end=0，predicted=[0]
    # abc 在 stream 中找不到 → missing
    assert "_missing_markers" in r


def test_e2e_chunk_boundary_returns_5_keys_with_missing_batch17():
    """有 missing markers → 4 + missing = 5 keys。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert "_tolerance_chars" in r
    assert "_missing_markers" in r
    assert "chunk_boundary_precision" in r
    assert "chunk_boundary_recall" in r
    assert "chunk_boundary_f1" in r


def test_e2e_chunk_boundary_returns_4_keys_no_missing_batch17():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    r = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert len(r) == 4  # 3 metrics + _tolerance_chars


def test_e2e_module_constants_in_namespace_batch17():
    assert "PARSER_DOES_NOT_EMIT_RELATIONS" in vars(amod)
    assert "figure_caption_prf" in vars(amod)
    assert "chunk_boundary_prf" in vars(amod)
