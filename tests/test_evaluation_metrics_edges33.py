"""evaluation/metrics.py 第三十四轮 edges 测试（Round 366）。

重点补强 edges32 未触及的角度：
- compute_automatic_metrics source level 字符串精确补强第三批
- _null / _ratio / _bool_metric / _int_metric source 第三批
- _pdf_locator_ratio source 第三批
- _docx_locator_ratio source 第三批
- _is_valid_bbox source 第三批
- _image_resource_ratio source 第三批
- _chunk_reference_ratio source 第三批
- _strip_unicode_whitespace source 第三批
- _text_preservation source 第三批
- _heading_boundary_ratio source 第三批
- _silent_drop_count source 第三批
- 行为深度第七批
- module source forbidden tokens 第八批
- signatures 精确补强第三批
- 模块整体合理性补强第三批
- 端到端集成补强第三批
"""

from __future__ import annotations

import inspect
import math
import types
from collections import Counter
from pathlib import Path

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
    _NOT_EVALUATED,
    _PDF_BBOX_REQUIRED_TYPES,
    _TEXT_TYPES,
    _bool_metric,
    _chunk_reference_ratio,
    _docx_locator_ratio,
    _heading_boundary_ratio,
    _image_resource_ratio,
    _int_metric,
    _is_valid_bbox,
    _null,
    _pdf_locator_ratio,
    _ratio,
    _silent_drop_count,
    _strip_unicode_whitespace,
    _text_preservation,
    compute_automatic_metrics,
)


# ---------- compute_automatic_metrics source level 字符串精确补强第三批 ----------


def test_compute_source_docstring_present():
    src = inspect.getsource(compute_automatic_metrics)
    assert '"""' in src


def test_compute_source_docstring_mentions_document():
    src = inspect.getsource(compute_automatic_metrics)
    assert "document" in src


def test_compute_source_docstring_mentions_error():
    src = inspect.getsource(compute_automatic_metrics)
    assert "error" in src


def test_compute_source_docstring_mentions_source_type():
    src = inspect.getsource(compute_automatic_metrics)
    assert "source_type" in src


def test_compute_source_docstring_mentions_expectations():
    src = inspect.getsource(compute_automatic_metrics)
    assert "expectations" in src


def test_compute_source_docstring_mentions_image_base_dir():
    src = inspect.getsource(compute_automatic_metrics)
    assert "image_base_dir" in src


def test_compute_source_uses_pipeline_success_eq():
    src = inspect.getsource(compute_automatic_metrics)
    assert "pipeline_success = error is None and document is not None" in src


def test_compute_source_pipeline_success_assignment_to_metrics():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["pipeline_success"] = _bool_metric(pipeline_success)' in src


def test_compute_source_error_code_uses_dict_literal():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["error_code"] = (' in src
    assert '{"value": error["code"] if error else None, "reason": None}' in src


def test_compute_source_schema_valid_branch_document_none():
    src = inspect.getsource(compute_automatic_metrics)
    assert "if document is None:" in src
    assert 'metrics["schema_valid"] = _null("pipeline_failed")' in src


def test_compute_source_schema_valid_else_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert "else:" in src
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_compute_source_try_except_for_schema():
    src = inspect.getsource(compute_automatic_metrics)
    assert "try:" in src
    assert "ok = document_passes_schema(document)" in src
    assert 'metrics["schema_valid"] = _bool_metric(ok)' in src


def test_compute_source_exception_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert "except Exception as e:" in src
    assert '"value": False' in src
    assert '"reason": f"schema_check_exception:{type(e).__name__}"' in src


def test_compute_source_second_document_none_check():
    """第二次 document None 检查（用于早返回）."""
    src = inspect.getsource(compute_automatic_metrics)
    # 第一次是 schema_valid 分支，第二次是早返回
    assert src.count("if document is None:") == 2


def test_compute_source_11_metric_for_none_loop():
    src = inspect.getsource(compute_automatic_metrics)
    assert '"element_count_total"' in src
    assert '"element_count_by_type"' in src
    assert '"pdf_locator_valid_ratio"' in src
    assert '"docx_locator_valid_ratio"' in src
    assert '"image_resource_exists_ratio"' in src
    assert '"chunk_reference_intact_ratio"' in src
    assert '"text_preservation_equal"' in src
    assert '"text_char_multiset_precision"' in src
    assert '"text_char_multiset_recall"' in src
    assert '"heading_boundary_compliance"' in src
    assert '"silent_drop_count"' in src


def test_compute_source_returns_metrics_for_none_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert "metrics[name] = _null(\"pipeline_failed\")" in src
    assert "return metrics" in src


def test_compute_source_uses_get_elements_chunks():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'elements = document.get("elements", [])' in src
    assert 'chunks = document.get("chunks", [])' in src


def test_compute_source_int_metric_for_count():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["element_count_total"] = _int_metric(len(elements))' in src


def test_compute_source_by_type_dict_init():
    src = inspect.getsource(compute_automatic_metrics)
    assert "by_type: dict[str, int] = {}" in src


def test_compute_source_by_type_loop():
    src = inspect.getsource(compute_automatic_metrics)
    assert "for e in elements:" in src
    assert 't = e.get("type", "unknown")' in src
    assert "by_type[t] = by_type.get(t, 0) + 1" in src


def test_compute_source_by_type_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["element_count_by_type"] = {"value": by_type, "reason": None}' in src


def test_compute_source_pdf_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'if source_type == "pdf":' in src
    assert 'metrics["pdf_locator_valid_ratio"] = _pdf_locator_ratio(elements)' in src


def test_compute_source_pdf_else_not_pdf():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["pdf_locator_valid_ratio"] = _null("not_pdf_document")' in src


def test_compute_source_docx_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'if source_type == "docx":' in src
    assert 'metrics["docx_locator_valid_ratio"] = _docx_locator_ratio(elements)' in src


def test_compute_source_docx_else_not_docx():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["docx_locator_valid_ratio"] = _null("not_docx_document")' in src


def test_compute_source_image_resource_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["image_resource_exists_ratio"] = _image_resource_ratio(' in src
    assert "elements, image_base_dir" in src


def test_compute_source_chunk_reference_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["chunk_reference_intact_ratio"] = _chunk_reference_ratio(elements, chunks)' in src


def test_compute_source_text_preservation_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert "text_metrics = _text_preservation(elements, chunks)" in src


def test_compute_source_text_preservation_metrics_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["text_preservation_equal"] = text_metrics["equal"]' in src
    assert 'metrics["text_char_multiset_precision"] = text_metrics["precision"]' in src
    assert 'metrics["text_char_multiset_recall"] = text_metrics["recall"]' in src


def test_compute_source_heading_boundary_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["heading_boundary_compliance"] = _heading_boundary_ratio(elements, chunks)' in src


def test_compute_source_silent_drop_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["silent_drop_count"] = _silent_drop_count(by_type, expectations)' in src


def test_compute_source_final_return():
    src = inspect.getsource(compute_automatic_metrics)
    assert "return metrics" in src


def test_compute_source_no_yield():
    src = inspect.getsource(compute_automatic_metrics)
    assert "yield" not in src


def test_compute_source_no_async():
    src = inspect.getsource(compute_automatic_metrics)
    assert "async " not in src


def test_compute_source_no_walrus():
    src = inspect.getsource(compute_automatic_metrics)
    assert ":=" not in src


def test_compute_source_no_class():
    src = inspect.getsource(compute_automatic_metrics)
    assert "class " not in src


# ---------- _null / _ratio / _bool_metric / _int_metric source 第三批 ----------


def test_null_source_returns_dict_literal():
    src = inspect.getsource(_null)
    assert "return {" in src
    assert '"value": None' in src
    assert '"reason": reason' in src


def test_null_source_no_class():
    src = inspect.getsource(_null)
    assert "class " not in src


def test_null_source_no_yield():
    src = inspect.getsource(_null)
    assert "yield" not in src


def test_ratio_source_returns_dict_literal():
    src = inspect.getsource(_ratio)
    assert "return {" in src
    assert '"value": float(value)' in src
    assert '"reason": None' in src


def test_ratio_source_no_class():
    src = inspect.getsource(_ratio)
    assert "class " not in src


def test_bool_metric_source_returns_dict_literal():
    src = inspect.getsource(_bool_metric)
    assert "return {" in src
    assert '"value": bool(value)' in src
    assert '"reason": None' in src


def test_bool_metric_source_one_line():
    src = inspect.getsource(_bool_metric)
    # one-liner
    lines = [l for l in src.strip().split("\n") if l.strip()]
    # def + return = 2 lines
    assert len(lines) == 2


def test_int_metric_source_returns_dict_literal():
    src = inspect.getsource(_int_metric)
    assert "return {" in src
    assert '"value": int(value)' in src
    assert '"reason": None' in src


def test_int_metric_source_one_line():
    src = inspect.getsource(_int_metric)
    lines = [l for l in src.strip().split("\n") if l.strip()]
    assert len(lines) == 2


# ---------- _pdf_locator_ratio source 第三批 ----------


def test_pdf_locator_source_docstring_present():
    src = inspect.getsource(_pdf_locator_ratio)
    assert '"""' in src


def test_pdf_locator_source_docstring_mentions_page():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "page" in src


def test_pdf_locator_source_docstring_mentions_bbox():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "bbox" in src


def test_pdf_locator_source_uses_valid_init():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "valid = 0" in src


def test_pdf_locator_source_uses_for_e_in_elements():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "for e in elements:" in src


def test_pdf_locator_source_uses_loc_assignment():
    src = inspect.getsource(_pdf_locator_ratio)
    assert 'loc = e.get("source_locator") or {}' in src


def test_pdf_locator_source_uses_page_get():
    src = inspect.getsource(_pdf_locator_ratio)
    assert 'page = loc.get("page")' in src


def test_pdf_locator_source_uses_isinstance_int():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src


def test_pdf_locator_source_uses_page_lt_1():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "page < 1" in src


def test_pdf_locator_source_uses_pdf_bbox_required_types():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "e.get(\"type\") in _PDF_BBOX_REQUIRED_TYPES" in src


def test_pdf_locator_source_calls_is_valid_bbox():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not _is_valid_bbox(bbox):" in src


def test_pdf_locator_source_valid_increment():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "valid += 1" in src


def test_pdf_locator_source_return_ratio_calc():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_ratio(valid / len(elements))" in src


def test_pdf_locator_source_no_class():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "class " not in src


def test_pdf_locator_source_no_yield():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "yield" not in src


# ---------- _docx_locator_ratio source 第三批 ----------


def test_docx_locator_source_docstring_present():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"""' in src


def test_docx_locator_source_docstring_mentions_locator():
    src = inspect.getsource(_docx_locator_ratio)
    assert "locator" in src.lower()


def test_docx_locator_source_uses_structural_keys_tuple_full():
    src = inspect.getsource(_docx_locator_ratio)
    expected_keys = (
        '"section"',
        '"paragraph_index"',
        '"run_index"',
        '"table_index"',
        '"row_index"',
        '"col_index"',
        '"relationship_id"',
    )
    for k in expected_keys:
        assert k in src


def test_docx_locator_source_uses_page_in_loc_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"page" in loc' in src


def test_docx_locator_source_uses_bbox_in_loc_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"bbox" in loc' in src


def test_docx_locator_source_uses_any_structural_keys():
    src = inspect.getsource(_docx_locator_ratio)
    assert "not any(k in loc for k in structural_keys)" in src


def test_docx_locator_source_no_class():
    src = inspect.getsource(_docx_locator_ratio)
    assert "class " not in src


def test_docx_locator_source_no_yield():
    src = inspect.getsource(_docx_locator_ratio)
    assert "yield" not in src


# ---------- _is_valid_bbox source 第三批 ----------


def test_is_valid_bbox_source_no_docstring_or_present():
    """_is_valid_bbox 可能无 docstring，验证关键内容."""
    src = inspect.getsource(_is_valid_bbox)
    # 至少有 def
    assert "def _is_valid_bbox(" in src


def test_is_valid_bbox_source_uses_len_4():
    src = inspect.getsource(_is_valid_bbox)
    assert "len(bbox) != 4" in src


def test_is_valid_bbox_source_uses_isinstance_bool_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "if isinstance(v, bool):" in src
    assert "return False" in src


def test_is_valid_bbox_source_uses_isinstance_int_float():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(v, (int, float))" in src


def test_is_valid_bbox_source_uses_math_isfinite():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite(v)" in src


def test_is_valid_bbox_source_uses_for_v_in_bbox():
    src = inspect.getsource(_is_valid_bbox)
    assert "for v in bbox:" in src


def test_is_valid_bbox_source_returns_true_at_end():
    src = inspect.getsource(_is_valid_bbox)
    assert "return True" in src


def test_is_valid_bbox_source_no_class():
    src = inspect.getsource(_is_valid_bbox)
    assert "class " not in src


# ---------- _image_resource_ratio source 第三批 ----------


def test_image_resource_source_docstring_present():
    src = inspect.getsource(_image_resource_ratio)
    assert '"""' in src


def test_image_resource_source_docstring_mentions_image():
    src = inspect.getsource(_image_resource_ratio)
    assert "image" in src.lower()


def test_image_resource_source_uses_list_comprehension():
    src = inspect.getsource(_image_resource_ratio)
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src


def test_image_resource_source_uses_no_images_branch():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not images:" in src
    assert 'return _null("no_image_elements")' in src


def test_image_resource_source_uses_valid_zero_init():
    src = inspect.getsource(_image_resource_ratio)
    assert "valid = 0" in src


def test_image_resource_source_uses_for_img_in_images():
    src = inspect.getsource(_image_resource_ratio)
    assert "for img in images:" in src


def test_image_resource_source_uses_get_resource_path():
    src = inspect.getsource(_image_resource_ratio)
    assert 'rp = img.get("resource_path")' in src


def test_image_resource_source_uses_if_not_rp():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not rp:" in src
    assert "continue" in src


def test_image_resource_source_uses_candidates_list():
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates: list[Path] = [Path(rp)]" in src


def test_image_resource_source_uses_image_base_dir_concat():
    src = inspect.getsource(_image_resource_ratio)
    assert "if image_base_dir is not None:" in src
    assert "candidates.append(image_base_dir / Path(rp).name)" in src


def test_image_resource_source_uses_ok_bool():
    src = inspect.getsource(_image_resource_ratio)
    assert "ok = False" in src


def test_image_resource_source_uses_for_p_in_candidates():
    src = inspect.getsource(_image_resource_ratio)
    assert "for p in candidates:" in src


def test_image_resource_source_uses_try_except_oserror():
    src = inspect.getsource(_image_resource_ratio)
    assert "try:" in src
    assert "if p.is_file() and p.stat().st_size > 0:" in src
    assert "ok = True" in src
    assert "break" in src
    assert "except OSError:" in src


def test_image_resource_source_uses_valid_increment():
    src = inspect.getsource(_image_resource_ratio)
    assert "if ok:" in src
    assert "valid += 1" in src


def test_image_resource_source_return_ratio():
    src = inspect.getsource(_image_resource_ratio)
    assert "_ratio(valid / len(images))" in src


# ---------- _chunk_reference_ratio source 第三批 ----------


def test_chunk_reference_source_uses_elem_ids_set():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "elem_ids = {e.get(\"element_id\") for e in elements}" in src


def test_chunk_reference_source_uses_for_c_in_chunks():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "for c in chunks:" in src


def test_chunk_reference_source_uses_ids_or_empty():
    src = inspect.getsource(_chunk_reference_ratio)
    assert 'ids = c.get("source_element_ids") or []' in src


def test_chunk_reference_source_uses_all_check():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "all(sid in elem_ids for sid in ids)" in src


def test_chunk_reference_source_return_ratio():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "_ratio(valid / len(chunks))" in src


def test_chunk_reference_source_no_class():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "class " not in src


# ---------- _strip_unicode_whitespace source 第三批 ----------


def test_strip_unicode_source_docstring_present():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert '"""' in src


def test_strip_unicode_source_docstring_mentions_Unicode():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "Unicode" in src or "unicode" in src


def test_strip_unicode_source_uses_join_with_generator():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert '"".join(ch for ch in s' in src


def test_strip_unicode_source_uses_not_ch_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "not ch.isspace()" in src


def test_strip_unicode_source_no_re_sub():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "re.sub" not in src


def test_strip_unicode_source_no_strip_call():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert ".strip()" not in src


def test_strip_unicode_source_no_replace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert ".replace(" not in src


# ---------- _text_preservation source 第三批 ----------


def test_text_preservation_source_docstring_present():
    src = inspect.getsource(_text_preservation)
    assert '"""' in src


def test_text_preservation_source_uses_expected_raw_join():
    src = inspect.getsource(_text_preservation)
    assert 'expected_raw = "".join(' in src
    assert 'e.get("content") or ""' in src
    assert 'for e in elements' in src
    assert 'if e.get("type") != "image"' in src


def test_text_preservation_source_uses_actual_raw_join():
    src = inspect.getsource(_text_preservation)
    assert 'actual_raw = "".join(c.get("text") or "" for c in chunks)' in src


def test_text_preservation_source_uses_strip_unicode_for_expected():
    src = inspect.getsource(_text_preservation)
    assert "expected = _strip_unicode_whitespace(expected_raw)" in src


def test_text_preservation_source_uses_strip_unicode_for_actual():
    src = inspect.getsource(_text_preservation)
    assert "actual = _strip_unicode_whitespace(actual_raw)" in src


def test_text_preservation_source_equal_assignment():
    src = inspect.getsource(_text_preservation)
    assert "equal = expected == actual" in src
    assert "equal_metric = _bool_metric(equal)" in src


def test_text_preservation_source_counter_init_expected():
    src = inspect.getsource(_text_preservation)
    assert "c_expected = Counter(expected)" in src


def test_text_preservation_source_counter_init_actual():
    src = inspect.getsource(_text_preservation)
    assert "c_actual = Counter(actual)" in src


def test_text_preservation_source_uses_intersection():
    src = inspect.getsource(_text_preservation)
    assert "common = sum((c_expected & c_actual).values())" in src


def test_text_preservation_source_empty_both_check():
    src = inspect.getsource(_text_preservation)
    assert "if not expected and not actual:" in src
    assert 'precision_metric = _null("empty_expected_and_actual")' in src


def test_text_preservation_source_precision_div_zero():
    src = inspect.getsource(_text_preservation)
    assert 'if sum(c_actual.values()) == 0:' in src
    assert 'precision_metric = _null("empty_actual")' in src


def test_text_preservation_source_precision_else():
    src = inspect.getsource(_text_preservation)
    assert "precision_metric = _ratio(common / sum(c_actual.values()))" in src


def test_text_preservation_source_recall_div_zero():
    src = inspect.getsource(_text_preservation)
    assert 'if sum(c_expected.values()) == 0:' in src
    assert 'recall_metric = _null("empty_expected")' in src


def test_text_preservation_source_recall_else():
    src = inspect.getsource(_text_preservation)
    assert "recall_metric = _ratio(common / sum(c_expected.values()))" in src


def test_text_preservation_source_returns_3_keys():
    src = inspect.getsource(_text_preservation)
    assert '"equal": equal_metric' in src
    assert '"precision": precision_metric' in src
    assert '"recall": recall_metric' in src


# ---------- _heading_boundary_ratio source 第三批 ----------


def test_heading_boundary_source_docstring_present():
    src = inspect.getsource(_heading_boundary_ratio)
    assert '"""' in src


def test_heading_boundary_source_uses_list_comprehension_for_headings():
    src = inspect.getsource(_heading_boundary_ratio)
    assert 'headings = [e for e in elements if e.get("type") == "heading"]' in src


def test_heading_boundary_source_uses_no_heading_branch():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "if not headings:" in src
    assert 'return _null("no_heading_elements")' in src


def test_heading_boundary_source_uses_chunk_first_ids_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids = set()" in src


def test_heading_boundary_source_uses_for_c_in_chunks():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "for c in chunks:" in src


def test_heading_boundary_source_uses_ids_or_empty():
    src = inspect.getsource(_heading_boundary_ratio)
    assert 'ids = c.get("source_element_ids") or []' in src


def test_heading_boundary_source_uses_if_ids():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "if ids:" in src
    assert "chunk_first_ids.add(ids[0])" in src


def test_heading_boundary_source_uses_matched_sum():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "matched = sum(1 for h in headings if h.get(\"element_id\") in chunk_first_ids)" in src


def test_heading_boundary_source_return_ratio():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "_ratio(matched / len(headings))" in src


# ---------- _silent_drop_count source 第三批 ----------


def test_silent_drop_source_docstring_present():
    src = inspect.getsource(_silent_drop_count)
    assert '"""' in src


def test_silent_drop_source_uses_if_not_expectations():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expectations:" in src
    assert 'return _null("no_expectations")' in src


def test_silent_drop_source_uses_get_element_count_by_type():
    src = inspect.getsource(_silent_drop_count)
    assert 'expected_counts = expectations.get("element_count_by_type") or {}' in src


def test_silent_drop_source_uses_if_not_expected_counts():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expected_counts:" in src
    assert 'return _null("no_expectations_element_count")' in src


def test_silent_drop_source_uses_drops_zero():
    src = inspect.getsource(_silent_drop_count)
    assert "drops = 0" in src


def test_silent_drop_source_uses_for_t_exp_in_items():
    src = inspect.getsource(_silent_drop_count)
    assert "for t, exp in expected_counts.items():" in src


def test_silent_drop_source_uses_actual_get():
    src = inspect.getsource(_silent_drop_count)
    assert "actual = by_type.get(t, 0)" in src


def test_silent_drop_source_uses_actual_lt_exp_check():
    src = inspect.getsource(_silent_drop_count)
    assert "if actual < exp:" in src
    assert "drops += (exp - actual)" in src


def test_silent_drop_source_return_int_metric():
    src = inspect.getsource(_silent_drop_count)
    assert "return _int_metric(drops)" in src


# ---------- 行为深度第七批 ----------


def test_null_returns_dict_with_none_value():
    r = _null("reason_x")
    assert r == {"value": None, "reason": "reason_x"}


def test_null_with_empty_reason():
    r = _null("")
    assert r["value"] is None
    assert r["reason"] == ""


def test_null_with_unicode_reason():
    r = _null("无标注")
    assert r["reason"] == "无标注"


def test_ratio_returns_dict_with_float():
    r = _ratio(0.5)
    assert r == {"value": 0.5, "reason": None}


def test_ratio_with_int_input():
    r = _ratio(1)
    assert r["value"] == 1.0
    assert isinstance(r["value"], float)


def test_ratio_with_zero():
    r = _ratio(0)
    assert r["value"] == 0.0


def test_ratio_with_negative():
    r = _ratio(-0.5)
    assert r["value"] == -0.5


def test_bool_metric_with_true():
    r = _bool_metric(True)
    assert r == {"value": True, "reason": None}


def test_bool_metric_with_false():
    r = _bool_metric(False)
    assert r == {"value": False, "reason": None}


def test_bool_metric_with_truthy_int():
    r = _bool_metric(1)
    assert r["value"] is True


def test_bool_metric_with_falsy_int():
    r = _bool_metric(0)
    assert r["value"] is False


def test_int_metric_with_int():
    r = _int_metric(42)
    assert r == {"value": 42, "reason": None}


def test_int_metric_with_float():
    r = _int_metric(3.7)
    assert r["value"] == 3


def test_int_metric_with_negative():
    r = _int_metric(-5)
    assert r["value"] == -5


def test_int_metric_with_string_digit():
    r = _int_metric("10")
    assert r["value"] == 10


# ---------- 行为深度第七批 - 子函数 ----------


def test_pdf_locator_ratio_empty_elements():
    r = _pdf_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_pdf_locator_ratio_simple_text_elements():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        },
        {
            "type": "paragraph",
            "source_locator": {"page": 2, "bbox": [0, 0, 100, 100]},
        },
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_invalid_page():
    elements = [
        {"type": "image", "source_locator": {"page": 0}},
    ]
    r = _pdf_locator_ratio(elements)
    # image 不需要 bbox，但 page=0 invalid
    assert r["value"] == 0.0


def test_pdf_locator_ratio_negative_page():
    elements = [
        {"type": "image", "source_locator": {"page": -1}},
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_text_missing_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1}},  # 缺 bbox
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_text_with_invalid_bbox():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [1, 2, 3]}},  # len 3
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_image_no_bbox_needed():
    elements = [
        {"type": "image", "source_locator": {"page": 1}},  # image 不需 bbox
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 1.0


def test_pdf_locator_ratio_mixed_valid_invalid():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},  # valid
        {"type": "paragraph", "source_locator": {"page": 0}},  # invalid page
        {"type": "image", "source_locator": {"page": 2}},  # valid (image)
    ]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 2 / 3


def test_pdf_locator_ratio_missing_source_locator():
    elements = [{"type": "image"}]  # no source_locator
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_pdf_locator_ratio_missing_page():
    elements = [{"type": "image", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    r = _pdf_locator_ratio(elements)
    # page is None → not int → invalid
    assert r["value"] == 0.0


def test_docx_locator_ratio_empty_elements():
    r = _docx_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_docx_locator_ratio_valid():
    elements = [
        {"type": "paragraph", "source_locator": {"paragraph_index": 1}},
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 1.0


def test_docx_locator_ratio_with_page_in_loc():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 1}},
    ]
    r = _docx_locator_ratio(elements)
    # 含 page → invalid
    assert r["value"] == 0.0


def test_docx_locator_ratio_with_bbox_in_loc():
    elements = [
        {"type": "paragraph", "source_locator": {"bbox": [1, 2, 3, 4], "paragraph_index": 1}},
    ]
    r = _docx_locator_ratio(elements)
    # 含 bbox → invalid
    assert r["value"] == 0.0


def test_docx_locator_ratio_no_structural_keys():
    elements = [
        {"type": "paragraph", "source_locator": {"other_key": "value"}},
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_docx_locator_ratio_missing_locator():
    elements = [{"type": "paragraph"}]
    r = _docx_locator_ratio(elements)
    # loc = {} → no structural keys → invalid
    assert r["value"] == 0.0


def test_docx_locator_ratio_mixed():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},  # valid
        {"type": "paragraph", "source_locator": {"page": 1}},  # invalid
        {"type": "paragraph", "source_locator": {"run_index": 0}},  # valid
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 2 / 3


def test_is_valid_bbox_with_valid_list():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_with_negative_values():
    assert _is_valid_bbox([-10, -10, 10, 10]) is True


def test_is_valid_bbox_with_floats():
    assert _is_valid_bbox([0.5, 1.5, 2.5, 3.5]) is True


def test_is_valid_bbox_invalid_len_3():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_invalid_len_5():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_tuple_not_list():
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_with_bool():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_with_nan():
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_is_valid_bbox_with_inf():
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_is_valid_bbox_with_none():
    assert _is_valid_bbox([None, 0, 0, 0]) is False


def test_is_valid_bbox_with_string():
    assert _is_valid_bbox(["a", "b", "c", "d"]) is False


def test_is_valid_bbox_none_input():
    assert _is_valid_bbox(None) is False


def test_image_resource_ratio_no_images():
    elements = [{"type": "paragraph"}]
    r = _image_resource_ratio(elements, None)
    assert r["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path():
    elements = [{"type": "image"}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_empty_resource_path():
    elements = [{"type": "image", "resource_path": ""}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_nonexistent_file(tmp_path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "missing.png")}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_existing_file(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(p)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1.0


def test_image_resource_ratio_existing_zero_size_file(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(p)}]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 0.0


def test_image_resource_ratio_mixed(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(p)},  # valid
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},  # invalid
        {"type": "image"},  # missing
    ]
    r = _image_resource_ratio(elements, None)
    assert r["value"] == 1 / 3


def test_image_resource_ratio_with_image_base_dir(tmp_path):
    p = tmp_path / "img.png"
    p.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "img.png"}]  # only filename
    r = _image_resource_ratio(elements, tmp_path)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_no_chunks():
    r = _chunk_reference_ratio([], [])
    assert r["reason"] == "no_chunks"


def test_chunk_reference_ratio_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_chunk_reference_ratio_partial_unknown():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "unknown"]}]  # unknown → invalid
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_empty_source_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]  # empty → not valid
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_missing_source_element_ids():
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # missing key → None or [] → not valid
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_chunk_reference_ratio_mixed():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},  # valid
        {"source_element_ids": ["unknown"]},  # invalid
    ]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_strip_unicode_whitespace_ascii_only():
    assert _strip_unicode_whitespace("hello world") == "helloworld"


def test_strip_unicode_whitespace_with_tabs():
    assert _strip_unicode_whitespace("a\tb\tc") == "abc"


def test_strip_unicode_whitespace_with_newlines():
    assert _strip_unicode_whitespace("a\nb\nc") == "abc"


def test_strip_unicode_whitespace_nbsp():
    #   is non-breaking space
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_em_space():
    #   is em space
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_whitespace_ideographic_space():
    # 　 is ideographic space
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_whitespace_empty():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_whitespace_all_whitespace():
    assert _strip_unicode_whitespace(" \t\n\r") == ""


def test_strip_unicode_whitespace_no_whitespace():
    assert _strip_unicode_whitespace("hello") == "hello"


def test_strip_unicode_whitespace_emoji_preserved():
    assert _strip_unicode_whitespace("😀hello") == "😀hello"


def test_strip_unicode_whitespace_chinese_preserved():
    assert _strip_unicode_whitespace("中文 测试") == "中文测试"


def test_strip_unicode_whitespace_punctuation_preserved():
    assert _strip_unicode_whitespace("hello, world!") == "hello,world!"


def test_strip_unicode_whitespace_numbers_preserved():
    assert _strip_unicode_whitespace("1 2 3") == "123"


def test_text_preservation_equal_simple():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True
    assert r["precision"]["value"] == 1.0
    assert r["recall"]["value"] == 1.0


def test_text_preservation_with_whitespace_diff():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello  world"}]  # extra space, but stripped equal
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_with_loss():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello"}]  # lost "world"
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    # 空白被剥离：expected = "helloworld" (10); actual = "hello" (5)
    # common = "hello" 5 chars
    assert r["precision"]["value"] == 1.0  # 5/5
    assert r["recall"]["value"] == 0.5  # 5/10


def test_text_preservation_empty_both():
    r = _text_preservation([], [])
    assert r["equal"]["value"] is True
    assert r["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_empty_actual_only():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = []
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["reason"] == "empty_actual"
    assert r["recall"]["value"] == 0.0  # 0 / 5


def test_text_preservation_empty_expected_only():
    elements = [{"type": "image", "content": ""}]  # image filtered out
    chunks = [{"text": "hello"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False
    assert r["precision"]["value"] == 0.0  # 0 / 5
    assert r["recall"]["reason"] == "empty_expected"


def test_text_preservation_image_filtered():
    elements = [
        {"type": "paragraph", "content": "hello"},
        {"type": "image", "content": "image_data"},  # filtered
    ]
    chunks = [{"text": "hello"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_text_preservation_3_keys():
    r = _text_preservation([], [])
    assert set(r.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_does_not_mutate_inputs():
    elements = [{"type": "paragraph", "content": "hello"}]
    chunks = [{"text": "hello"}]
    e_before = repr(elements)
    c_before = repr(chunks)
    _text_preservation(elements, chunks)
    assert repr(elements) == e_before
    assert repr(chunks) == c_before


def test_heading_boundary_ratio_no_headings():
    elements = [{"type": "paragraph"}]
    chunks = [{"source_element_ids": ["e1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    # No chunks → chunk_first_ids is empty → matched = 0
    assert r["value"] == 0.0


def test_heading_boundary_ratio_full_match():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1", "p1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_heading_boundary_ratio_partial_match():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1", "p1"]}]  # only h1 matched
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.5


def test_heading_boundary_ratio_heading_not_first():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["p1", "h1"]}]  # h1 is not first
    r = _heading_boundary_ratio(elements, chunks)
    # only ids[0] is checked
    assert r["value"] == 0.0


def test_heading_boundary_ratio_empty_ids():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["value"] == 0.0


def test_silent_drop_count_no_expectations():
    r = _silent_drop_count({}, None)
    assert r["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations():
    r = _silent_drop_count({}, {})
    assert r["reason"] == "no_expectations"


def test_silent_drop_count_no_element_count_key():
    r = _silent_drop_count({}, {"other": "value"})
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_count_empty_element_count():
    r = _silent_drop_count({}, {"element_count_by_type": {}})
    assert r["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drops():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 0


def test_silent_drop_count_some_drops():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 2


def test_silent_drop_count_more_actual_than_expected():
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    # actual > expected → 0 drops
    assert r["value"] == 0


def test_silent_drop_count_missing_type_in_actual():
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count({}, expectations)
    # by_type doesn't have "paragraph" → actual = 0 → drop = 5
    assert r["value"] == 5


def test_silent_drop_count_multi_type():
    by_type = {"paragraph": 3, "heading": 2}
    expectations = {
        "element_count_by_type": {"paragraph": 5, "heading": 2, "table": 1}
    }
    r = _silent_drop_count(by_type, expectations)
    # paragraph: max(0, 5-3)=2; heading: 0; table: max(0, 1-0)=1 → 3
    assert r["value"] == 3


# ---------- module source forbidden tokens 第八批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "importlib",
        "platform",
        "subprocess",
        "argparse",
        "sys",
    ],
)
def test_metrics_source_no_forbidden_token_eighth(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第三批 ----------


def test_module_source_docstring_present():
    assert mmod.__doc__ is not None


def test_module_source_docstring_mentions_自动指标():
    assert "自动指标" in mmod.__doc__


def test_module_source_docstring_mentions_text_preservation():
    assert "text_preservation" in mmod.__doc__ or "text_preservation" in mmod.__doc__


def test_module_source_docstring_mentions_unicode_whitespace():
    assert "Unicode 空白" in mmod.__doc__ or "Unicode" in mmod.__doc__


def test_module_source_docstring_mentions_counter():
    assert "Counter" in mmod.__doc__


def test_module_source_docstring_mentions_v1_1():
    assert "v1.1" in mmod.__doc__ or "v1.0" in mmod.__doc__


def test_module_source_has_future_annotations():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_math():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_imports_counter():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_imports_path():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_text_types_constant():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")' in src


def test_module_source_pdf_bbox_required_types_constant():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")' in src


def test_module_source_not_evaluated_constant():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_no_relative_above_root():
    src = inspect.getsource(mmod)
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from ."):
            assert "evaluation" in stripped or "app" in stripped


def test_module_source_no_star_import():
    src = inspect.getsource(mmod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(mmod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(mmod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(mmod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(mmod)
    assert 'if __name__' not in src


def test_module_source_no_user_class():
    src = inspect.getsource(mmod)
    lines = src.split("\n")
    has_class = any(line.lstrip().startswith("class ") for line in lines)
    assert not has_class


def test_module_source_11_user_functions():
    """compute_automatic_metrics + 10 helpers."""
    src = inspect.getsource(mmod)
    assert "def _null(" in src
    assert "def _ratio(" in src
    assert "def _bool_metric(" in src
    assert "def _int_metric(" in src
    assert "def compute_automatic_metrics(" in src
    assert "def _pdf_locator_ratio(" in src
    assert "def _docx_locator_ratio(" in src
    assert "def _is_valid_bbox(" in src
    assert "def _image_resource_ratio(" in src
    assert "def _chunk_reference_ratio(" in src
    assert "def _strip_unicode_whitespace(" in src
    assert "def _text_preservation(" in src
    assert "def _heading_boundary_ratio(" in src
    assert "def _silent_drop_count(" in src


def test_module_source_all_1_entry():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


def test_module_source_no_eval():
    src = inspect.getsource(mmod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(mmod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(mmod)
    assert "compile(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(mmod)
    assert "unlink" not in src


def test_module_source_no_write():
    src = inspect.getsource(mmod)
    assert ".write(" not in src


def test_module_source_no_print():
    src = inspect.getsource(mmod)
    assert "print(" not in src


# ---------- signatures 精确补强第三批 ----------


def test_signature_null():
    sig = inspect.signature(_null)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "reason"


def test_signature_ratio():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_bool_metric():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_int_metric():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "value"


def test_signature_pdf_locator():
    sig = inspect.signature(_pdf_locator_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "elements"


def test_signature_docx_locator():
    sig = inspect.signature(_docx_locator_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "elements"


def test_signature_is_valid_bbox():
    sig = inspect.signature(_is_valid_bbox)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "bbox"


def test_signature_image_resource():
    sig = inspect.signature(_image_resource_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "elements"
    assert params[1].name == "image_base_dir"


def test_signature_chunk_reference():
    sig = inspect.signature(_chunk_reference_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "elements"
    assert params[1].name == "chunks"


def test_signature_strip_unicode_whitespace():
    sig = inspect.signature(_strip_unicode_whitespace)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "s"


def test_signature_text_preservation():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "elements"
    assert params[1].name == "chunks"


def test_signature_heading_boundary():
    sig = inspect.signature(_heading_boundary_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "elements"
    assert params[1].name == "chunks"


def test_signature_silent_drop_count():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "by_type"
    assert params[1].name == "expectations"


def test_signature_compute_automatic_metrics():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert params[0].name == "document"
    assert params[1].name == "error"
    assert params[2].name == "source_type"
    assert params[3].name == "expectations"
    assert params[4].name == "image_base_dir"


def test_signature_compute_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert params[4].default is None


def test_signature_compute_document_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_compute_no_varargs():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_pdf_locator_no_varargs():
    sig = inspect.signature(_pdf_locator_ratio)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_text_preservation_no_varargs():
    sig = inspect.signature(_text_preservation)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


# ---------- 模块整体合理性补强第三批 ----------


def test_module_has_docstring():
    assert mmod.__doc__ is not None


def test_module_has_all_attribute():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_length_1():
    assert len(mmod.__all__) == 1


def test_module_all_entries_unique():
    assert len(set(mmod.__all__)) == 1


def test_module_all_entries_are_str():
    for entry in mmod.__all__:
        assert isinstance(entry, str)


def test_module_all_only_compute_automatic_metrics():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_namespace_14_callables():
    callables = [
        (name, obj) for name, obj in vars(mmod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == mmod.__name__
    ]
    # 14 个: _null, _ratio, _bool_metric, _int_metric, compute_automatic_metrics,
    # _pdf_locator_ratio, _docx_locator_ratio, _is_valid_bbox, _image_resource_ratio,
    # _chunk_reference_ratio, _strip_unicode_whitespace, _text_preservation,
    # _heading_boundary_ratio, _silent_drop_count
    assert len(callables) == 14


def test_module_namespace_3_constants():
    """3 个 module-level 常量：_TEXT_TYPES, _PDF_BBOX_REQUIRED_TYPES, _NOT_EVALUATED."""
    assert hasattr(mmod, "_TEXT_TYPES")
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_no_user_classes():
    classes = [
        (name, obj) for name, obj in vars(mmod).items()
        if isinstance(obj, type) and obj.__module__ == mmod.__name__
    ]
    assert len(classes) == 0


def test_module_name_is_evaluation_metrics():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_file_ends_with_metrics_py():
    assert mmod.__file__.endswith("metrics.py")


def test_module_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_text_types_length_7():
    assert len(_TEXT_TYPES) == 7


def test_module_text_types_correct_entries():
    assert set(_TEXT_TYPES) == {
        "heading", "paragraph", "list_item", "table",
        "caption", "header", "footer",
    }


def test_module_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_pdf_bbox_required_types_length_4():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_pdf_bbox_required_types_correct_entries():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {"heading", "paragraph", "caption", "list_item"}


def test_module_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_module_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_pdf_bbox_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES 必须是 _TEXT_TYPES 的子集."""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_module_function_module_eq_mmod():
    assert _null.__module__ == "evaluation.metrics"
    assert _ratio.__module__ == "evaluation.metrics"
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"


def test_module_constants_module_builtins():
    """tuple 和 str 的 __module__ 是 builtins."""
    assert isinstance(_TEXT_TYPES, tuple)
    assert isinstance(_NOT_EVALUATED, str)


# ---------- 端到端集成补强第三批 ----------


def test_e2e_compute_metrics_minimal_pdf_doc():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            }
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pipeline_success" in metrics
    assert metrics["pipeline_success"]["value"] is True
    assert "schema_valid" in metrics
    assert "element_count_total" in metrics
    assert metrics["element_count_total"]["value"] == 1


def test_e2e_compute_metrics_document_none():
    metrics = compute_automatic_metrics(None, None, "pdf", None)
    assert metrics["pipeline_success"]["value"] is False
    assert metrics["schema_valid"]["reason"] == "pipeline_failed"
    assert metrics["element_count_total"]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_error_dict():
    error = {"code": "PARSE_FAILED", "message": "x"}
    metrics = compute_automatic_metrics(None, error, "pdf", None)
    assert metrics["pipeline_success"]["value"] is False
    assert metrics["error_code"]["value"] == "PARSE_FAILED"


def test_e2e_compute_metrics_does_not_mutate_doc():
    doc = {
        "elements": [{"type": "paragraph", "content": "hello"}],
        "chunks": [{"text": "hello"}],
    }
    before = repr(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert repr(doc) == before


def test_e2e_compute_metrics_idempotent():
    doc = {"elements": [], "chunks": []}
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_e2e_compute_metrics_positional_args():
    doc = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(doc, None, "pdf", None)
    assert "pipeline_success" in metrics


def test_e2e_compute_metrics_kwargs():
    doc = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(
        document=doc,
        error=None,
        source_type="pdf",
        expectations=None,
        image_base_dir=None,
    )
    assert "pipeline_success" in metrics


def test_e2e_compute_metrics_docx_source_type():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "hello", "source_locator": {"paragraph_index": 1}}
        ],
        "chunks": [{"text": "hello"}],
    }
    metrics = compute_automatic_metrics(doc, None, "docx", None)
    assert metrics["pipeline_success"]["value"] is True
    assert metrics["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert metrics["docx_locator_valid_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_unknown_source_type():
    doc = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(doc, None, "unknown", None)
    assert metrics["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert metrics["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_e2e_compute_metrics_with_pdf_elements():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
            {
                "type": "heading",
                "content": "title",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]},
            },
        ],
        "chunks": [{"text": "title hello"}],
    }
    metrics = compute_automatic_metrics(doc, None, "pdf", None)
    assert metrics["element_count_total"]["value"] == 2
    assert metrics["pdf_locator_valid_ratio"]["value"] == 1.0


def test_e2e_text_preservation_with_text():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello world"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is True


def test_e2e_text_preservation_with_loss():
    elements = [{"type": "paragraph", "content": "hello world"}]
    chunks = [{"text": "hello"}]
    r = _text_preservation(elements, chunks)
    assert r["equal"]["value"] is False


def test_e2e_strip_unicode_whitespace_with_nbsp():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_e2e_strip_unicode_whitespace_with_em_space():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_e2e_strip_unicode_whitespace_with_ideographic_space():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_e2e_is_valid_bbox_valid():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_e2e_is_valid_bbox_with_negative():
    assert _is_valid_bbox([-10, -10, 10, 10]) is True


def test_e2e_is_valid_bbox_with_floats():
    assert _is_valid_bbox([0.5, 1.5, 2.5, 3.5]) is True


def test_e2e_is_valid_bbox_invalid_len():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_e2e_is_valid_bbox_invalid_type_tuple():
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_e2e_is_valid_bbox_with_bool():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_e2e_is_valid_bbox_with_nan():
    assert _is_valid_bbox([float("nan"), 0, 0, 0]) is False


def test_e2e_is_valid_bbox_with_inf():
    assert _is_valid_bbox([float("inf"), 0, 0, 0]) is False


def test_e2e_pdf_locator_no_elements():
    r = _pdf_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_e2e_pdf_locator_with_invalid_page():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    r = _pdf_locator_ratio(elements)
    assert r["value"] == 0.0


def test_e2e_docx_locator_no_elements():
    r = _docx_locator_ratio([])
    assert r["reason"] == "no_elements"


def test_e2e_docx_locator_with_page_in_loc():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 1}}
    ]
    r = _docx_locator_ratio(elements)
    assert r["value"] == 0.0


def test_e2e_chunk_reference_no_chunks():
    r = _chunk_reference_ratio([], [])
    assert r["reason"] == "no_chunks"


def test_e2e_chunk_reference_all_valid():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    r = _chunk_reference_ratio(elements, chunks)
    assert r["value"] == 1.0


def test_e2e_image_resource_no_images():
    elements = [{"type": "paragraph"}]
    r = _image_resource_ratio(elements, None)
    assert r["reason"] == "no_image_elements"


def test_e2e_silent_drop_no_expectations():
    r = _silent_drop_count({}, None)
    assert r["reason"] == "no_expectations"


def test_e2e_silent_drop_zero_drops():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 0


def test_e2e_silent_drop_some_drops():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 2


def test_e2e_silent_drop_more_actual_than_expected():
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    r = _silent_drop_count(by_type, expectations)
    assert r["value"] == 0


def test_e2e_heading_boundary_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    r = _heading_boundary_ratio(elements, [])
    assert r["value"] == 0.0


def test_e2e_heading_boundary_no_headings():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    chunks = [{"source_element_ids": ["p1"]}]
    r = _heading_boundary_ratio(elements, chunks)
    assert r["reason"] == "no_heading_elements"


def test_e2e_compute_metrics_full_pdf_doc_with_image(tmp_path):
    img = tmp_path / "test.png"
    img.write_bytes(b"\x89PNG")
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
            {
                "type": "image",
                "resource_path": str(img),
                "source_locator": {"page": 1},
            },
        ],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    metrics = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=tmp_path)
    assert metrics["pipeline_success"]["value"] is True
    assert metrics["image_resource_exists_ratio"]["value"] == 1.0


def test_e2e_compute_metrics_does_not_mutate_error():
    error = {"code": "FAIL", "message": "x"}
    before = repr(error)
    compute_automatic_metrics(None, error, "pdf", None)
    assert repr(error) == before


def test_e2e_compute_metrics_returns_dict_with_13_keys():
    """document is not None → 13 metric keys."""
    doc = {"elements": [], "chunks": []}
    metrics = compute_automatic_metrics(doc, None, "pdf", None)
    expected_keys = {
        "pipeline_success",
        "error_code",
        "schema_valid",
        "element_count_total",
        "element_count_by_type",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected_keys.issubset(set(metrics.keys()))


def test_e2e_compute_metrics_document_none_returns_14_keys():
    """document None → 13 null metrics + error_code = 14 total."""
    metrics = compute_automatic_metrics(None, None, "pdf", None)
    expected_keys = {
        "pipeline_success",
        "error_code",
        "schema_valid",
        "element_count_total",
        "element_count_by_type",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
        "text_preservation_equal",
        "text_char_multiset_precision",
        "text_char_multiset_recall",
        "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert set(metrics.keys()) == expected_keys
