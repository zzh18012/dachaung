"""evaluation/annotation_metrics.py 第五十八轮 edges 测试（Round 539）。

补强 edges57 未触及的角度（第三十一批）：
- PARSER_DOES_NOT_EMIT_RELATIONS 第三十一批：在 module 顶层 / 引用相同 / 不是空 str / 含 underscore
- figure_caption_prf 第三十一批：含 caption / document 含 table / annotation 是 dict 但含 list value / 多次调用独立
- chunk_boundary_prf 第三十一批：tolerance_chars 负数 / position 任意字符串 / 5 chunks / chunk 含空 text / anchor 在 stream 起始 / chunk 无 text key / 多个 missing_markers / _tolerance_chars int
- module source forbidden tokens 第四十八批
- module source 字符串精确补强第四十四批
- signatures 第四十四批
- module 合理性第四十四批
- 端到端集成第四十四批
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluation import annotation_metrics as amod
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)


# ---------- PARSER_DOES_NOT_EMIT_RELATIONS 第三十一批 ----------


def test_parser_does_not_emit_relations_module_level_batch31():
    """PARSER_DOES_NOT_EMIT_RELATIONS 在 module 顶层（不是函数局部）。"""
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_parser_does_not_emit_relations_reference_same_batch31():
    """多次引用相同对象。"""
    import evaluation.annotation_metrics as m1
    import evaluation.annotation_metrics as m2
    assert m1.PARSER_DOES_NOT_EMIT_RELATIONS is m2.PARSER_DOES_NOT_EMIT_RELATIONS


def test_parser_does_not_emit_relations_not_empty_batch31():
    assert len(PARSER_DOES_NOT_EMIT_RELATIONS) > 0


def test_parser_does_not_emit_relations_has_underscore_batch31():
    assert "_" in PARSER_DOES_NOT_EMIT_RELATIONS


# ---------- figure_caption_prf 第三十一批 ----------


def test_figure_caption_prf_doc_with_caption_element_batch31():
    """document 含 caption 元素也 null。"""
    doc = {
        "elements": [{"type": "caption", "text": "Figure 1: x"}],
        "chunks": [],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_doc_with_table_batch31():
    """document 含 table 也 null。"""
    doc = {
        "elements": [{"type": "table", "text": "data"}],
        "chunks": [],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_annotation_with_list_value_batch31():
    """annotation 含 list value。"""
    out = figure_caption_prf(
        {"chunks": []},
        {"key": [1, 2, 3]},
    )
    for v in out.values():
        assert v["value"] is None


def test_figure_caption_prf_two_calls_independent_dict_batch31():
    out1 = figure_caption_prf({"chunks": []}, None)
    out2 = figure_caption_prf({"chunks": []}, None)
    assert out1 == out2
    assert out1 is not out2


def test_figure_caption_prf_document_dict_with_chunks_and_elements_batch31():
    """完整 dict 也不抛。"""
    doc = {
        "elements": [{"type": "image", "element_id": "i1"}],
        "chunks": [{"text": "x"}],
    }
    out = figure_caption_prf(doc, None)
    assert isinstance(out, dict)


def test_figure_caption_prf_annotation_with_figure_caption_pairs_batch31():
    """annotation 含 figure_caption_pairs → 仍 null（parser 不输出）。"""
    out = figure_caption_prf(
        {"chunks": []},
        {"figure_caption_pairs": [{"figure": "f1", "caption": "c1"}]},
    )
    for v in out.values():
        assert v["value"] is None


# ---------- chunk_boundary_prf 第三十一批 ----------


def test_chunk_boundary_prf_tolerance_negative_batch31():
    """tolerance_chars 负数 → 任何 anchor 都不匹配。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=-10)
    # |3-3|=0 > -10 不成立（距离不能 ≤ 负数）→ no match
    # 实际：d <= -10 永远 False（d >= 0）
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_position_arbitrary_string_batch31():
    """position='weird' → 走 else 分支（按 after 处理）。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "aaa", "position": "weird"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # 'weird' != 'before' → 走 else (after) → 3
    # predicted=[3] → match
    assert out["chunk_boundary_precision"]["value"] == 1.0


def test_chunk_boundary_prf_five_chunks_batch31():
    """5 chunks → 4 predicted boundaries。"""
    doc = {"chunks": [{"text": f"c{i}"} for i in range(5)]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "c0", "position": "after"},
            {"marker": "c1", "position": "after"},
            {"marker": "c2", "position": "after"},
            {"marker": "c3", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="c0 c1 c2 c3 c4", predicted=[2, 5, 8, 11]
    # anchors: c0 after→2, c1 after→5, c2 after→8, c3 after→11
    # 4 matches → P=R=1.0
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_chunk_with_empty_text_batch31():
    """chunk 含空 text。"""
    doc = {"chunks": [{"text": ""}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream=normalize_text(" abc")="abc"
    # chunk0="" → find "" at 0, end=0, predicted=[0]
    # chunk1="abc" → skip (last)
    # anchor="abc" before → find_pos=0 → gt=[0]
    # |0-0|=0 → match
    assert "chunk_boundary_precision" in out


def test_chunk_boundary_prf_chunk_no_text_key_batch31():
    """chunk 缺 text key → text 为 ''。"""
    doc = {"chunks": [{}, {"text": "abc"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    assert isinstance(out, dict)


def test_chunk_boundary_prf_multiple_missing_markers_batch31():
    """多个 missing marker。"""
    doc = {"chunks": [{"text": "aaa"}, {"text": "bbb"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "xxx", "position": "after"},
            {"marker": "yyy", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann)
    assert "_missing_markers" in out
    assert "xxx" in out["_missing_markers"]["value"]
    assert "yyy" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_tolerance_chars_int_batch31():
    """_tolerance_chars value 是 int。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert isinstance(out["_tolerance_chars"]["value"], int)
    assert out["_tolerance_chars"]["value"] == 42


def test_chunk_boundary_prf_anchor_at_stream_start_batch31():
    """anchor 'before' 在 stream 起始（pos=0）。"""
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "before"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="abc def", predicted=[3]
    # anchor="abc" before → 0
    # |3-0|=3 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0


def test_chunk_boundary_prf_two_identical_anchors_batch31():
    """两个相同 anchor + 2 个对应 chunk → 都匹配。"""
    doc = {"chunks": [{"text": "x"}, {"text": "x"}, {"text": "y"}]}
    ann = {
        "chunk_boundary_anchors": [
            {"marker": "x", "position": "after"},
            {"marker": "x", "position": "after"},
        ]
    }
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)
    # stream="x x y"
    # chunk0="x" at 0, end=1, predicted=[1]
    # chunk1="x" at 2 (search from 2), end=3, predicted=[1, 3]
    # chunk2 skip
    # anchors: "x" after from search_from=0 → find "x" at 0, end=1, search_from=1
    # 第二个 "x" after from search_from=1 → find "x" at 2, end=3, search_from=3
    # gt=[1, 3]
    # matches: |1-1|=0, |3-3|=0 → 2 matches
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0


def test_chunk_boundary_prf_no_input_modification_batch31():
    """不修改输入。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch31():
    src = inspect.getsource(amod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch31():
    src = inspect.getsource(amod)
    assert "os.system" not in src


def test_module_source_no_eval_batch31():
    src = inspect.getsource(amod)
    assert "eval(" not in src


def test_module_source_no_exec_batch31():
    src = inspect.getsource(amod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch31():
    src = inspect.getsource(amod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch31():
    src = inspect.getsource(amod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch31():
    src = inspect.getsource(amod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch31():
    src = inspect.getsource(amod)
    assert "breakpoint(" not in src


def test_module_source_no_open_w_mode_batch31():
    src = inspect.getsource(amod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_shutil_batch31():
    src = inspect.getsource(amod)
    assert "shutil" not in src


def test_module_source_no_requests_batch31():
    src = inspect.getsource(amod)
    assert "requests" not in src


def test_module_source_no_unlink_batch31():
    src = inspect.getsource(amod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch31():
    src = inspect.getsource(amod)
    assert "人工标注指标" in src


def test_module_source_contains_parser_does_not_emit_relations_const_batch31():
    src = inspect.getsource(amod)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_module_source_contains_figure_caption_func_batch31():
    src = inspect.getsource(amod)
    assert "def figure_caption_prf(" in src


def test_module_source_contains_chunk_boundary_func_batch31():
    src = inspect.getsource(amod)
    assert "def chunk_boundary_prf(" in src


def test_module_source_contains_normalize_text_import_batch31():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_null_ratio_import_batch31():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_source_contains_counter_import_batch31():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_source_contains_typing_any_import_batch31():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_source_contains_pipeline_failed_reason_batch31():
    src = inspect.getsource(amod)
    assert "pipeline_failed" in src


def test_module_source_contains_no_annotation_reason_batch31():
    src = inspect.getsource(amod)
    assert "no_annotation" in src


def test_module_source_contains_no_predicted_boundaries_reason_batch31():
    src = inspect.getsource(amod)
    assert "no_predicted_boundaries" in src


def test_module_source_contains_no_ground_truth_anchors_reason_batch31():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors" in src


def test_module_source_contains_no_ground_truth_anchors_in_stream_reason_batch31():
    src = inspect.getsource(amod)
    assert "no_ground_truth_anchors_in_stream" in src


def test_module_source_contains_precision_or_recall_not_evaluated_batch31():
    src = inspect.getsource(amod)
    assert "precision_or_recall_not_evaluated" in src


def test_module_source_contains_search_from_local_batch31():
    src = inspect.getsource(amod)
    assert "search_from" in src


def test_module_source_contains_missing_markers_local_batch31():
    src = inspect.getsource(amod)
    assert "missing_markers" in src


# ---------- signatures 第四十四批 ----------


def test_signature_figure_caption_prf_return_dict_batch31():
    sig = inspect.signature(figure_caption_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_chunk_boundary_prf_return_dict_batch31():
    sig = inspect.signature(chunk_boundary_prf)
    assert "dict[str, dict[str, Any]]" in str(sig.return_annotation)


def test_signature_figure_caption_prf_document_annotation_batch31():
    sig = inspect.signature(figure_caption_prf)
    for p_name in ("document", "annotation"):
        a = sig.parameters[p_name].annotation
        assert "dict" in str(a)
        assert "None" in str(a)


def test_signature_chunk_boundary_prf_document_annotation_batch31():
    sig = inspect.signature(chunk_boundary_prf)
    for p_name in ("document", "annotation"):
        a = sig.parameters[p_name].annotation
        assert "dict" in str(a)
        assert "None" in str(a)


def test_signature_chunk_boundary_prf_tolerance_default_30_batch31():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_signature_chunk_boundary_prf_tolerance_annotation_int_batch31():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].annotation == "int"


def test_signature_chunk_boundary_prf_params_count_batch31():
    sig = inspect.signature(chunk_boundary_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation", "tolerance_chars"]


def test_signature_figure_caption_prf_params_count_batch31():
    sig = inspect.signature(figure_caption_prf)
    params = list(sig.parameters.keys())
    assert params == ["document", "annotation"]


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch31():
    src = inspect.getsource(amod)
    assert "from __future__ import annotations" in src


def test_module_imports_counter_batch31():
    src = inspect.getsource(amod)
    assert "from collections import Counter" in src


def test_module_imports_typing_any_batch31():
    src = inspect.getsource(amod)
    assert "from typing import Any" in src


def test_module_imports_normalize_text_batch31():
    src = inspect.getsource(amod)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_imports_null_ratio_batch31():
    src = inspect.getsource(amod)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_has_all_export_batch31():
    src = inspect.getsource(amod)
    assert "__all__" in src


def test_module_all_has_three_entries_batch31():
    src = inspect.getsource(amod)
    for name in [
        '"PARSER_DOES_NOT_EMIT_RELATIONS"',
        '"figure_caption_prf"',
        '"chunk_boundary_prf"',
    ]:
        assert name in src


def test_module_no_main_block_batch31():
    src = inspect.getsource(amod)
    assert 'if __name__ == "__main__"' not in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_chunk_boundary_perfect_match_with_tolerance_batch31():
    """端到端：含容差的完美匹配。"""
    doc = {"chunks": [{"text": "hello"}, {"text": "world"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "hell", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=2)
    # stream="hello world", predicted=[5]
    # anchor="hell" after → 4, |5-4|=1 ≤ 2 → match
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_e2e_figure_caption_returns_three_keys_batch31():
    """端到端：figure_caption 始终返回 3 key。"""
    out = figure_caption_prf({"chunks": []}, None)
    assert len(out) == 3


def test_e2e_chunk_boundary_no_input_modification_batch31():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    doc_before = json.dumps(doc, sort_keys=True)
    ann_before = json.dumps(ann, sort_keys=True)
    chunk_boundary_prf(doc, ann)
    assert json.dumps(doc, sort_keys=True) == doc_before
    assert json.dumps(ann, sort_keys=True) == ann_before


def test_e2e_chunk_boundary_idempotent_batch31():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out1 = chunk_boundary_prf(doc, ann)
    out2 = chunk_boundary_prf(doc, ann)
    assert out1 == out2


def test_e2e_chunk_boundary_all_reasons_used_batch31():
    """端到端：测各种 reason 都可能出现。"""
    reasons = set()
    # pipeline_failed
    out = chunk_boundary_prf(None, None)
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_annotation
    out = chunk_boundary_prf({"chunks": []}, None)
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_predicted_boundaries
    out = chunk_boundary_prf({"chunks": []}, {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]})
    reasons.add(out["chunk_boundary_precision"]["reason"])
    # no_ground_truth_anchors
    out = chunk_boundary_prf({"chunks": [{"text": "a"}, {"text": "b"}]}, {"chunk_boundary_anchors": []})
    reasons.add(out["chunk_boundary_precision"]["reason"])
    assert reasons == {
        "pipeline_failed",
        "no_annotation",
        "no_predicted_boundaries",
        "no_ground_truth_anchors",
    }


def test_e2e_chunk_boundary_tolerance_recorded_batch31():
    """端到端：tolerance 在输出中记录。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_e2e_figure_caption_with_real_document_with_figures_batch31():
    """端到端：含 figures 的真实 document → figure_caption null。"""
    doc = {
        "elements": [
            {"type": "image", "element_id": "i1"},
            {"type": "caption", "text": "Fig 1"},
        ],
        "chunks": [{"text": "Fig 1"}],
    }
    out = figure_caption_prf(doc, None)
    for v in out.values():
        assert v["value"] is None
        assert v["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS
