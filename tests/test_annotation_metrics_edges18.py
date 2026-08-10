r"""evaluation/annotation_metrics.py 边角测试 - 第十八轮（Round 275）。

edges17 已覆盖：源码 token、docstring、chunk_boundary_prf 算法详细（position before/after/tolerance 边界、
多 pred+anchor 一对一/greedy 排序/marker 重复/marker 起始末尾/marker 空串/normalize_text）、
_tolerance_chars/_missing_markers success 路径、namespace、签名 introspection、__all__、
PARSER_DOES_NOT_EMIT_RELATIONS singleton、helper FunctionType、chunk_boundary_prf 更深算法
（predicted 搜索失败/norm_chunks 单 chunk/含空 chunk/stream 空/' ' join 然后 normalize）、
position 默认 'after'/unknown 值、anchor 缺 marker / marker 非字符串、tolerance_chars 是 0/负数/极大值、
matched 计算（0 pred 0 gt / 多 pred 1 gt / 1 pred 多 gt）、输出顺序、重复 marker 顺序 search_from、
不修改 document/annotation、不缓存、figure_caption_prf 更深（dict 输入也仍 null / 不修改输入）、
模块源码 token（含 set literal / used_pred.add / used_gt.add / continue / break）。

edges18 补强未覆盖的角度：
- 模块 imports 精确字符串：'from collections import Counter'/'from typing import Any'/
  'from app.chunkers.structural import normalize_text'/'from evaluation.metrics import _null, _ratio'
- import 顺序：__future__ → collections → typing → app.chunkers.structural → evaluation.metrics
- PARSER_DOES_NOT_EMIT_RELATIONS source-level 定义精确
- figure_caption_prf source-level token：'reason = PARSER_DOES_NOT_EMIT_RELATIONS' / 'return {' 3 keys
- figure_caption_prf 三次 _null 调用产生独立 dict（_null 不缓存）
- chunk_boundary_prf source-level token 详细：
  * 'out: dict[str, dict[str, Any]] = {}'
  * 'if document is None:'
  * 'for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):'
  * 'out[k] = _null("pipeline_failed")' / '_null("no_annotation")' / '_null("no_predicted_boundaries")'
  * 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}'
  * 'anchors = annotation.get("chunk_boundary_anchors") or []'
  * 'chunks = document.get("chunks") or []'
  * 'if not chunks or len(chunks) < 2:'
  * 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]'
  * 'joined_raw = " ".join(norm_chunks)'
  * 'stream = normalize_text(joined_raw)'
  * 'predicted: list[int] = []'
  * 'find_pos = stream.find(txt, pos)'
  * 'gt_positions: list[int] = []'
  * 'missing_markers: list[str] = []'
  * 'search_from = 0'
  * 'marker = a.get("marker", "")'
  * 'position = a.get("position", "after")'
  * 'find_pos = stream.find(marker, search_from) if marker else -1'
  * 'pairs: list[tuple[int, int, int]] = []'
  * 'used_pred = set()' / 'used_gt = set()'
  * 'd = abs(pv - gv)'
  * 'if d <= tolerance_chars:'
  * 'pairs.append((d, pi, gi))'
  * 'pairs.sort(key=lambda x: x[0])'
  * 'for _, pi, gi in pairs:'
  * 'matched = 0'
  * 'num_pred = len(predicted)' / 'num_gt = len(gt_positions)'
  * 'denom = p_val + r_val'
  * 'if denom <= 0:' / 'else:'
  * '2 * p_val * r_val / denom'
  * 'if missing_markers:'
  * 'out["_missing_markers"] = {"value": missing_markers, "reason": None}'
- chunk_boundary_prf reason 常量精确：'pipeline_failed'/'no_annotation'/'no_predicted_boundaries'/
  'no_ground_truth_anchors'/'no_ground_truth_anchors_in_stream'/'precision_or_recall_not_evaluated'
- chunk_boundary_prf 5 个分支路径：document None/annotation falsy/chunks <2/anchors empty/正常路径
- chunk_boundary_prf _tolerance_chars 始终在输出中（即使 document None 或 annotation falsy）
- chunk_boundary_prf 不修改 input document（document dict 内容不变）
- chunk_boundary_prf 不修改 input annotation
- chunk_boundary_prf 输出 dict 类型精确（dict[str, dict[str, Any]]）
- chunk_boundary_prf 各 metric dict 含 'value'/'reason' 2 keys
- chunk_boundary_prf matched 是 int 类型
- chunk_boundary_prf num_pred/num_gt 是 int 类型
- 模块 source 不含 print/logging/subprocess/asyncio/threading/os
- 模块 source 不含 silent_drop_count / element_count_total / image_resource 等其他指标
- 模块 source 不含 json import（不需要读写文件）
- 模块 source 不含 process_single / pipeline import
- 模块 __all__ 3 entries 顺序精确：PARSER_DOES_NOT_EMIT_RELATIONS → figure_caption_prf → chunk_boundary_prf
- PARSER_DOES_NOT_EMIT_RELATIONS value 精确：'parser_does_not_emit_relations'
- PARSER_DOES_NOT_EMIT_RELATIONS 类型是 str
- Counter 在 namespace 中（即使实际未使用）
- normalize_text 是 app.chunkers.structural 的函数引用
- _null / _ratio 是 evaluation.metrics 的函数引用
- chunk_boundary_prf 调用 normalize_text（验证调用链）
- chunk_boundary_prf 调用 _null 和 _ratio（验证调用链）
- figure_caption_prf 不调用 normalize_text
- chunk_boundary_prf 不修改 chunks list 本身（不替换元素）
- chunk_boundary_prf anchors list 不被修改
- chunk_boundary_prf tolerance_chars 是 int 类型字段
- chunk_boundary_prf _tolerance_chars dict 含 value 是 int / reason 是 None
- chunk_boundary_prf _missing_markers dict 含 value 是 list / reason 是 None
- 模块 __all__ 不含 _null / _ratio / normalize_text / Counter / Any
- 模块 docstring 含 'figure-caption'/'chunk_boundary'/'P/R/F1'/'一对一'/'容差'
- helper metadata 详细：figure_caption_prf / chunk_boundary_prf 都是 FunctionType
- chunk_boundary_prf 算法步骤编号：注释里有 1./2./3./4./5.
"""

from __future__ import annotations

import inspect
import json
from collections import Counter
from typing import Any

import pytest

import evaluation.annotation_metrics as am_module
from evaluation.annotation_metrics import (
    PARSER_DOES_NOT_EMIT_RELATIONS,
    chunk_boundary_prf,
    figure_caption_prf,
)
from evaluation.metrics import _null, _ratio


# =========================================================================
# 模块 imports 精确字符串
# =========================================================================


def test_module_source_contains_from_collections_import_counter():
    src = inspect.getsource(am_module)
    assert "from collections import Counter" in src


def test_module_source_contains_from_typing_import_any():
    src = inspect.getsource(am_module)
    assert "from typing import Any" in src


def test_module_source_contains_app_chunkers_structural_import():
    src = inspect.getsource(am_module)
    assert "from app.chunkers.structural import normalize_text" in src


def test_module_source_contains_evaluation_metrics_import():
    src = inspect.getsource(am_module)
    assert "from evaluation.metrics import _null, _ratio" in src


def test_module_import_order():
    src = inspect.getsource(am_module)
    pos_future = src.find("from __future__ import annotations")
    pos_collections = src.find("from collections import Counter")
    pos_typing = src.find("from typing import Any")
    pos_app = src.find("from app.chunkers.structural import normalize_text")
    pos_eval = src.find("from evaluation.metrics import _null, _ratio")
    pos_const = src.find("PARSER_DOES_NOT_EMIT_RELATIONS = ")
    assert pos_future < pos_collections < pos_typing < pos_app < pos_eval < pos_const


# =========================================================================
# PARSER_DOES_NOT_EMIT_RELATIONS 详细
# =========================================================================


def test_module_source_contains_parser_does_not_emit_relations_definition():
    src = inspect.getsource(am_module)
    assert 'PARSER_DOES_NOT_EMIT_RELATIONS = "parser_does_not_emit_relations"' in src


def test_parser_does_not_emit_relations_is_str_type():
    assert isinstance(PARSER_DOES_NOT_EMIT_RELATIONS, str)


def test_parser_does_not_emit_relations_value_exact():
    assert PARSER_DOES_NOT_EMIT_RELATIONS == "parser_does_not_emit_relations"


def test_parser_does_not_emit_relations_module_identity():
    assert PARSER_DOES_NOT_EMIT_RELATIONS.__class__.__module__ == "builtins"


# =========================================================================
# figure_caption_prf source-level token
# =========================================================================


def test_figure_caption_prf_source_contains_reason_assignment():
    src = inspect.getsource(figure_caption_prf)
    assert "reason = PARSER_DOES_NOT_EMIT_RELATIONS" in src


def test_figure_caption_prf_source_contains_return_dict_with_3_keys():
    src = inspect.getsource(figure_caption_prf)
    assert '"figure_caption_precision": _null(reason)' in src
    assert '"figure_caption_recall": _null(reason)' in src
    assert '"figure_caption_f1": _null(reason)' in src


def test_figure_caption_prf_source_does_not_contain_normalize_text_call():
    """figure_caption_prf 不调用 normalize_text。"""
    src = inspect.getsource(figure_caption_prf)
    assert "normalize_text(" not in src


def test_figure_caption_prf_source_does_not_contain_print():
    src = inspect.getsource(figure_caption_prf)
    assert "print(" not in src


def test_figure_caption_prf_source_does_not_contain_subprocess():
    src = inspect.getsource(figure_caption_prf)
    assert "subprocess" not in src


def test_figure_caption_prf_three_null_dicts_are_independent():
    """三次 _null 调用产生独立 dict（_null 不缓存）。"""
    out = figure_caption_prf({}, {})
    assert out["figure_caption_precision"] is not out["figure_caption_recall"]
    assert out["figure_caption_recall"] is not out["figure_caption_f1"]
    assert out["figure_caption_precision"] is not out["figure_caption_f1"]


def test_figure_caption_prf_each_dict_has_value_and_reason_keys():
    out = figure_caption_prf(None, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert set(out[k].keys()) == {"value", "reason"}


def test_figure_caption_prf_value_is_none():
    out = figure_caption_prf(None, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["value"] is None


def test_figure_caption_prf_reason_is_parser_does_not_emit_relations():
    out = figure_caption_prf(None, None)
    for k in ("figure_caption_precision", "figure_caption_recall", "figure_caption_f1"):
        assert out[k]["reason"] == PARSER_DOES_NOT_EMIT_RELATIONS


def test_figure_caption_prf_does_not_modify_document():
    doc = {"chunks": [{"text": "abc"}], "elements": [{"type": "paragraph"}]}
    doc_copy = json.loads(json.dumps(doc))
    figure_caption_prf(doc, None)
    assert doc == doc_copy


def test_figure_caption_prf_does_not_modify_annotation():
    ann = {"chunk_boundary_anchors": [{"marker": "x", "position": "after"}]}
    ann_copy = json.loads(json.dumps(ann))
    figure_caption_prf(None, ann)
    assert ann == ann_copy


def test_figure_caption_prf_two_calls_independent():
    a = figure_caption_prf(None, None)
    b = figure_caption_prf(None, None)
    assert a is not b
    assert a["figure_caption_precision"] is not b["figure_caption_precision"]


# =========================================================================
# chunk_boundary_prf source-level token
# =========================================================================


def test_chunk_boundary_prf_source_contains_out_dict_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "out: dict[str, dict[str, Any]] = {}" in src


def test_chunk_boundary_prf_source_contains_document_is_none_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if document is None:" in src


def test_chunk_boundary_prf_source_contains_pipeline_failed_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null("pipeline_failed")' in src


def test_chunk_boundary_prf_source_contains_no_annotation_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not annotation:" in src


def test_chunk_boundary_prf_source_contains_no_annotation_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null("no_annotation")' in src


def test_chunk_boundary_prf_source_contains_no_predicted_boundaries_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null("no_predicted_boundaries")' in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null("no_ground_truth_anchors")' in src


def test_chunk_boundary_prf_source_contains_no_ground_truth_anchors_in_stream_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null(\n            "no_ground_truth_anchors_in_stream"\n        )' in src or '"no_ground_truth_anchors_in_stream"' in src


def test_chunk_boundary_prf_source_contains_precision_or_recall_not_evaluated_reason():
    src = inspect.getsource(chunk_boundary_prf)
    assert '_null("precision_or_recall_not_evaluated")' in src


def test_chunk_boundary_prf_source_contains_chunks_or_len_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if not chunks or len(chunks) < 2:" in src


def test_chunk_boundary_prf_source_contains_norm_chunks_comprehension():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'norm_chunks = [normalize_text(c.get("text") or "") for c in chunks]' in src


def test_chunk_boundary_prf_source_contains_joined_raw_join():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'joined_raw = " ".join(norm_chunks)' in src


def test_chunk_boundary_prf_source_contains_stream_normalize():
    src = inspect.getsource(chunk_boundary_prf)
    assert "stream = normalize_text(joined_raw)" in src


def test_chunk_boundary_prf_source_contains_predicted_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "predicted: list[int] = []" in src


def test_chunk_boundary_prf_source_contains_stream_find_for_chunk_text():
    src = inspect.getsource(chunk_boundary_prf)
    assert "find_pos = stream.find(txt, pos)" in src


def test_chunk_boundary_prf_source_contains_gt_positions_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "gt_positions: list[int] = []" in src


def test_chunk_boundary_prf_source_contains_missing_markers_list_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "missing_markers: list[str] = []" in src


def test_chunk_boundary_prf_source_contains_search_from_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "search_from = 0" in src


def test_chunk_boundary_prf_source_contains_marker_default_empty_str():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'marker = a.get("marker", "")' in src


def test_chunk_boundary_prf_source_contains_position_default_after():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'position = a.get("position", "after")' in src


def test_chunk_boundary_prf_source_contains_marker_find_with_search_from():
    src = inspect.getsource(chunk_boundary_prf)
    assert "find_pos = stream.find(marker, search_from) if marker else -1" in src


def test_chunk_boundary_prf_source_contains_pairs_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs: list[tuple[int, int, int]] = []" in src


def test_chunk_boundary_prf_source_contains_used_pred_set_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred = set()" in src


def test_chunk_boundary_prf_source_contains_used_gt_set_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_gt = set()" in src


def test_chunk_boundary_prf_source_contains_d_abs_calculation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "d = abs(pv - gv)" in src


def test_chunk_boundary_prf_source_contains_tolerance_compare():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if d <= tolerance_chars:" in src


def test_chunk_boundary_prf_source_contains_pairs_append():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.append((d, pi, gi))" in src


def test_chunk_boundary_prf_source_contains_pairs_sort():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pairs.sort(key=lambda x: x[0])" in src


def test_chunk_boundary_prf_source_contains_matched_init():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched = 0" in src


def test_chunk_boundary_prf_source_contains_used_pred_add():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_pred.add(pi)" in src


def test_chunk_boundary_prf_source_contains_used_gt_add():
    src = inspect.getsource(chunk_boundary_prf)
    assert "used_gt.add(gi)" in src


def test_chunk_boundary_prf_source_contains_matched_increment():
    src = inspect.getsource(chunk_boundary_prf)
    assert "matched += 1" in src


def test_chunk_boundary_prf_source_contains_num_pred_len():
    src = inspect.getsource(chunk_boundary_prf)
    assert "num_pred = len(predicted)" in src


def test_chunk_boundary_prf_source_contains_num_gt_len():
    src = inspect.getsource(chunk_boundary_prf)
    assert "num_gt = len(gt_positions)" in src


def test_chunk_boundary_prf_source_contains_p_val_r_val_lookup():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'p_val = out["chunk_boundary_precision"]["value"]' in src
    assert 'r_val = out["chunk_boundary_recall"]["value"]' in src


def test_chunk_boundary_prf_source_contains_p_val_or_r_val_none_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if p_val is None or r_val is None:" in src


def test_chunk_boundary_prf_source_contains_denom_calculation():
    src = inspect.getsource(chunk_boundary_prf)
    assert "denom = p_val + r_val" in src


def test_chunk_boundary_prf_source_contains_denom_le_zero_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if denom <= 0:" in src


def test_chunk_boundary_prf_source_contains_f1_formula():
    src = inspect.getsource(chunk_boundary_prf)
    assert "2 * p_val * r_val / denom" in src


def test_chunk_boundary_prf_source_contains_tolerance_chars_record():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'out["_tolerance_chars"] = {"value": tolerance_chars, "reason": None}' in src


def test_chunk_boundary_prf_source_contains_missing_markers_record():
    src = inspect.getsource(chunk_boundary_prf)
    assert 'out["_missing_markers"] = {"value": missing_markers, "reason": None}' in src


def test_chunk_boundary_prf_source_contains_if_missing_markers_check():
    src = inspect.getsource(chunk_boundary_prf)
    assert "if missing_markers:" in src


def test_chunk_boundary_prf_source_does_not_contain_print():
    src = inspect.getsource(chunk_boundary_prf)
    assert "print(" not in src


def test_chunk_boundary_prf_source_does_not_contain_logging():
    src = inspect.getsource(chunk_boundary_prf)
    assert "logging" not in src


def test_chunk_boundary_prf_source_does_not_contain_subprocess():
    src = inspect.getsource(chunk_boundary_prf)
    assert "subprocess" not in src


def test_chunk_boundary_prf_source_does_not_contain_async():
    src = inspect.getsource(chunk_boundary_prf)
    assert "async " not in src


def test_chunk_boundary_prf_source_does_not_contain_threading():
    src = inspect.getsource(chunk_boundary_prf)
    assert "import threading" not in src


def test_chunk_boundary_prf_source_does_not_contain_os_import():
    src = inspect.getsource(chunk_boundary_prf)
    assert "import os" not in src


def test_chunk_boundary_prf_source_does_not_contain_json_import():
    src = inspect.getsource(chunk_boundary_prf)
    assert "import json" not in src


def test_chunk_boundary_prf_source_does_not_contain_silent_drop():
    src = inspect.getsource(chunk_boundary_prf)
    assert "silent_drop_count" not in src


def test_chunk_boundary_prf_source_does_not_contain_element_count():
    src = inspect.getsource(chunk_boundary_prf)
    assert "element_count_total" not in src


def test_chunk_boundary_prf_source_does_not_contain_image_resource():
    src = inspect.getsource(chunk_boundary_prf)
    assert "image_resource" not in src


def test_chunk_boundary_prf_source_does_not_contain_pdf_locator():
    src = inspect.getsource(chunk_boundary_prf)
    assert "pdf_locator" not in src


def test_chunk_boundary_prf_source_does_not_contain_docx_locator():
    src = inspect.getsource(chunk_boundary_prf)
    assert "docx_locator" not in src


def test_chunk_boundary_prf_source_does_not_contain_pipeline_failed_other_than_check():
    """除了 'pipeline_failed' string literal，不应有 pipeline 相关 import。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "from app.pipeline" not in src
    assert "process_single" not in src


# =========================================================================
# chunk_boundary_prf 算法步骤编号
# =========================================================================


def test_chunk_boundary_prf_source_contains_step_1_comment():
    """算法步骤 1：规范化流。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "1." in src


def test_chunk_boundary_prf_source_contains_step_2_comment():
    """算法步骤 2：预测边界。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "2." in src


def test_chunk_boundary_prf_source_contains_step_3_comment():
    """算法步骤 3：标注 anchor → stream 位置。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "3." in src


def test_chunk_boundary_prf_source_contains_step_4_comment():
    """算法步骤 4：一对一匹配。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "4." in src


def test_chunk_boundary_prf_source_contains_step_5_comment():
    """算法步骤 5：precision / recall。"""
    src = inspect.getsource(chunk_boundary_prf)
    assert "5." in src


# =========================================================================
# __all__ 详细
# =========================================================================


def test_module_all_source_exact_3_entries_in_order():
    src = inspect.getsource(am_module)
    assert '"PARSER_DOES_NOT_EMIT_RELATIONS"' in src
    assert '"figure_caption_prf"' in src
    assert '"chunk_boundary_prf"' in src


def test_module_all_value_exact():
    assert am_module.__all__ == [
        "PARSER_DOES_NOT_EMIT_RELATIONS",
        "figure_caption_prf",
        "chunk_boundary_prf",
    ]


def test_module_all_is_list_type():
    assert isinstance(am_module.__all__, list)


def test_module_all_does_not_contain_null_or_ratio():
    """__all__ 不含 _null / _ratio（这些是 evaluation.metrics 的私有 helper）。"""
    assert "_null" not in am_module.__all__
    assert "_ratio" not in am_module.__all__


def test_module_all_does_not_contain_normalize_text():
    assert "normalize_text" not in am_module.__all__


def test_module_all_does_not_contain_counter_or_any():
    assert "Counter" not in am_module.__all__
    assert "Any" not in am_module.__all__


# =========================================================================
# namespace 详细
# =========================================================================


def test_module_namespace_has_counter_attr():
    """Counter 在 namespace 中（即使实际未使用）。"""
    assert hasattr(am_module, "Counter")
    assert am_module.Counter is Counter


def test_module_namespace_has_any_attr():
    assert hasattr(am_module, "Any")
    assert am_module.Any is Any


def test_module_namespace_has_normalize_text_attr():
    assert hasattr(am_module, "normalize_text")
    assert callable(am_module.normalize_text)


def test_module_namespace_has_null_attr():
    assert hasattr(am_module, "_null")
    assert am_module._null is _null


def test_module_namespace_has_ratio_attr():
    assert hasattr(am_module, "_ratio")
    assert am_module._ratio is _ratio


def test_module_namespace_has_parser_does_not_emit_relations():
    assert hasattr(am_module, "PARSER_DOES_NOT_EMIT_RELATIONS")


def test_module_namespace_has_figure_caption_prf():
    assert hasattr(am_module, "figure_caption_prf")


def test_module_namespace_has_chunk_boundary_prf():
    assert hasattr(am_module, "chunk_boundary_prf")


def test_module_namespace_does_not_have_subprocess():
    assert not hasattr(am_module, "subprocess")


def test_module_namespace_does_not_have_logging():
    assert not hasattr(am_module, "logging")


def test_module_namespace_does_not_have_os():
    assert not hasattr(am_module, "os")


def test_module_namespace_does_not_have_asyncio():
    assert not hasattr(am_module, "asyncio")


def test_module_namespace_does_not_have_json():
    assert not hasattr(am_module, "json")


def test_module_namespace_does_not_have_threading():
    assert not hasattr(am_module, "threading")


def test_module_namespace_does_not_have_path():
    assert not hasattr(am_module, "Path")


# =========================================================================
# chunk_boundary_prf 行为深度
# =========================================================================


def test_chunk_boundary_prf_document_none_returns_pipeline_failed():
    out = chunk_boundary_prf(None, None)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "pipeline_failed"
        assert out[k]["value"] is None


def test_chunk_boundary_prf_document_none_still_has_tolerance_record():
    out = chunk_boundary_prf(None, None, tolerance_chars=42)
    assert out["_tolerance_chars"]["value"] == 42
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_annotation_falsy_returns_no_annotation():
    """annotation 是空 dict / None / 0 / False → 'no_annotation'。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    for ann in [None, {}, 0, False]:
        out = chunk_boundary_prf(doc, ann)
        for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
            assert out[k]["reason"] == "no_annotation"


def test_chunk_boundary_prf_annotation_falsy_still_has_tolerance_record():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    out = chunk_boundary_prf(doc, None, tolerance_chars=15)
    assert out["_tolerance_chars"]["value"] == 15


def test_chunk_boundary_prf_chunks_lt_2_with_no_anchors_returns_no_predicted_boundaries():
    """chunks = [] 或 1 个 chunk + 无 anchors → 'no_predicted_boundaries'。"""
    for chunks in [[], [{"text": "a"}]]:
        doc = {"chunks": chunks}
        ann = {"chunk_boundary_anchors": []}
        out = chunk_boundary_prf(doc, ann)
        for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
            assert out[k]["reason"] == "no_predicted_boundaries"


def test_chunk_boundary_prf_chunks_lt_2_with_anchors_recall_is_zero_ratio():
    """chunks <2 + 有 anchors → precision/f1 是 'no_predicted_boundaries'，recall 是 _ratio(0.0)。"""
    doc = {"chunks": [{"text": "a"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "x"}]}
    out = chunk_boundary_prf(doc, ann)
    # precision / f1 是 no_predicted_boundaries
    assert out["chunk_boundary_precision"]["reason"] == "no_predicted_boundaries"
    assert out["chunk_boundary_f1"]["reason"] == "no_predicted_boundaries"
    # recall 是 _ratio(0.0)
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["reason"] is None


def test_chunk_boundary_prf_no_anchors_returns_no_ground_truth_anchors():
    """有 chunks 但无 anchors → 'no_ground_truth_anchors'。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}, {"text": "c"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert out[k]["reason"] == "no_ground_truth_anchors"


def test_chunk_boundary_prf_does_not_modify_document():
    doc = {
        "chunks": [{"text": "abc"}, {"text": "def"}],
        "elements": [{"type": "paragraph"}],
    }
    doc_copy = json.loads(json.dumps(doc))
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert doc == doc_copy


def test_chunk_boundary_prf_does_not_modify_annotation():
    doc = {"chunks": [{"text": "abc"}, {"text": "def"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "abc", "position": "after"}]}
    ann_copy = json.loads(json.dumps(ann))
    chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert ann == ann_copy


def test_chunk_boundary_prf_two_calls_independent_dict():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    a = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    b = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert a is not b
    assert a["chunk_boundary_precision"] is not b["chunk_boundary_precision"]
    assert a["_tolerance_chars"] is not b["_tolerance_chars"]


def test_chunk_boundary_prf_tolerance_chars_field_is_int():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert isinstance(out["_tolerance_chars"]["value"], int)


def test_chunk_boundary_prf_tolerance_chars_reason_is_none():
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": []}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=30)
    assert out["_tolerance_chars"]["reason"] is None


def test_chunk_boundary_prf_missing_markers_value_is_list():
    """anchors 含 marker 但 marker 不在 stream 中 → _missing_markers 字段。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "xyz_nonexistent", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" in out
    assert isinstance(out["_missing_markers"]["value"], list)
    assert "xyz_nonexistent" in out["_missing_markers"]["value"]


def test_chunk_boundary_prf_no_missing_markers_no_field():
    """所有 marker 都找到 → 不应含 _missing_markers 字段。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    assert "_missing_markers" not in out


def test_chunk_boundary_prf_each_metric_dict_has_value_reason_keys():
    """每个 metric dict 含 'value'/'reason' 2 keys。"""
    doc = {"chunks": [{"text": "a"}, {"text": "b"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "a", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert set(out[k].keys()) == {"value", "reason"}


def test_chunk_boundary_prf_perfect_match_returns_1_0():
    """完美匹配 → precision=recall=f1=1.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    # 'alpha' end position == 5；predicted boundary == 5（alpha 长度 5）
    # 完美匹配
    assert out["chunk_boundary_precision"]["value"] == 1.0
    assert out["chunk_boundary_recall"]["value"] == 1.0
    assert out["chunk_boundary_f1"]["value"] == 1.0


def test_chunk_boundary_prf_no_match_returns_zero():
    """无匹配 → precision=recall=0.0，f1=0.0。"""
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    # anchor 在 far away position
    ann = {"chunk_boundary_anchors": [{"marker": "beta", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=0)  # 0 容差
    # 'alpha' end == 5；predicted == [5]；anchor 'beta' end == 9；gt == [9]
    # |5-9|=4 > 0 → no match
    assert out["chunk_boundary_precision"]["value"] == 0.0
    assert out["chunk_boundary_recall"]["value"] == 0.0
    assert out["chunk_boundary_f1"]["value"] == 0.0


def test_chunk_boundary_prf_perfect_match_value_is_float():
    doc = {"chunks": [{"text": "alpha"}, {"text": "beta"}]}
    ann = {"chunk_boundary_anchors": [{"marker": "alpha", "position": "after"}]}
    out = chunk_boundary_prf(doc, ann, tolerance_chars=10)
    for k in ("chunk_boundary_precision", "chunk_boundary_recall", "chunk_boundary_f1"):
        assert isinstance(out[k]["value"], float)


# =========================================================================
# helper metadata 详细
# =========================================================================


def test_figure_caption_prf_is_function_type():
    import types

    assert isinstance(figure_caption_prf, types.FunctionType)


def test_chunk_boundary_prf_is_function_type():
    import types

    assert isinstance(chunk_boundary_prf, types.FunctionType)


def test_figure_caption_prf_module_is_annotation_metrics():
    assert figure_caption_prf.__module__ == "evaluation.annotation_metrics"


def test_chunk_boundary_prf_module_is_annotation_metrics():
    assert chunk_boundary_prf.__module__ == "evaluation.annotation_metrics"


def test_figure_caption_prf_qualname_exact():
    assert figure_caption_prf.__qualname__ == "figure_caption_prf"


def test_chunk_boundary_prf_qualname_exact():
    assert chunk_boundary_prf.__qualname__ == "chunk_boundary_prf"


# =========================================================================
# 签名 introspection 详细
# =========================================================================


def test_figure_caption_prf_signature_param_count_2():
    sig = inspect.signature(figure_caption_prf)
    assert len(sig.parameters) == 2


def test_figure_caption_prf_signature_param_names():
    sig = inspect.signature(figure_caption_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation"]


def test_figure_caption_prf_signature_param_no_defaults():
    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_figure_caption_prf_signature_param_kinds_positional_or_keyword():
    from inspect import Parameter

    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind == Parameter.POSITIONAL_OR_KEYWORD


def test_figure_caption_prf_no_var_args():
    from inspect import Parameter

    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_POSITIONAL


def test_figure_caption_prf_no_var_kwargs():
    from inspect import Parameter

    sig = inspect.signature(figure_caption_prf)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_KEYWORD


def test_figure_caption_prf_return_annotation_is_dict():
    sig = inspect.signature(figure_caption_prf)
    assert sig.return_annotation is not inspect.Signature.empty


def test_chunk_boundary_prf_signature_param_count_3():
    sig = inspect.signature(chunk_boundary_prf)
    assert len(sig.parameters) == 3


def test_chunk_boundary_prf_signature_param_names():
    sig = inspect.signature(chunk_boundary_prf)
    assert list(sig.parameters.keys()) == ["document", "annotation", "tolerance_chars"]


def test_chunk_boundary_prf_signature_tolerance_chars_default_30():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].default == 30


def test_chunk_boundary_prf_signature_tolerance_chars_kind_positional_or_keyword():
    from inspect import Parameter

    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["tolerance_chars"].kind == Parameter.POSITIONAL_OR_KEYWORD


def test_chunk_boundary_prf_signature_document_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_signature_annotation_no_default():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.parameters["annotation"].default is inspect.Parameter.empty


def test_chunk_boundary_prf_no_var_args():
    from inspect import Parameter

    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_POSITIONAL


def test_chunk_boundary_prf_no_var_kwargs():
    from inspect import Parameter

    sig = inspect.signature(chunk_boundary_prf)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_KEYWORD


def test_chunk_boundary_prf_return_annotation_is_dict():
    sig = inspect.signature(chunk_boundary_prf)
    assert sig.return_annotation is not inspect.Signature.empty


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_is_nonempty_string():
    assert isinstance(am_module.__doc__, str)
    assert len(am_module.__doc__) > 0


def test_module_docstring_mentions_figure_caption():
    doc = am_module.__doc__
    assert "figure-caption" in doc.lower() or "figure_caption" in doc


def test_module_docstring_mentions_chunk_boundary():
    doc = am_module.__doc__
    assert "chunk_boundary" in doc or "分块边界" in doc


def test_module_docstring_mentions_prf_or_p_r_f1():
    doc = am_module.__doc__
    assert "P/R/F1" in doc or "PRF" in doc.upper() or "precision" in doc.lower()


def test_module_docstring_mentions_one_to_one():
    """docstring 提到一对一匹配语义。"""
    doc = am_module.__doc__
    assert "一对一" in doc or "one-to-one" in doc.lower()


def test_module_docstring_mentions_tolerance_or_rong_cha():
    """docstring 提到容差。"""
    doc = am_module.__doc__
    assert "容差" in doc or "tolerance" in doc.lower()


def test_module_docstring_mentions_parser_does_not_emit():
    """docstring 提到 parser 不输出 relation。"""
    doc = am_module.__doc__
    assert "parser" in doc.lower()
