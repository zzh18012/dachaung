r"""evaluation/metrics.py 边角测试 - 第十八轮（Round 277）。

edges17 已覆盖：源码 token、docstring、签名 introspection、helper metadata、
常量 namespace 完整性、_is_valid_bbox 各种边界、_pdf_locator_ratio 每 text type、
_docx_locator_ratio 每 structural key、_image_resource_ratio 各种边界、_chunk_reference_ratio 各种边界、
_heading_boundary_ratio、_silent_drop_count、_text_preservation、compute_automatic_metrics、
namespace identity、helper no-caching、_null/_ratio/_bool_metric/_int_metric value 类型强制转换、
源码 token 补强（含 strip_unicode_whitespace/isspace/isfinite/isinstance）。

edges18 补强未覆盖的角度：
- 模块 imports 精确字符串：'import math'/'from collections import Counter'/'from pathlib import Path'/'from typing import Any'
- import 顺序：__future__ → math → collections → pathlib → typing
- _null source：'return {"value": None, "reason": reason}' 单行
- _ratio source：'return {"value": float(value), "reason": None}'
- _bool_metric source：'return {"value": bool(value), "reason": None}'
- _int_metric source：'return {"value": int(value), "reason": None}'
- 常量精确：_TEXT_TYPES == ('heading', 'paragraph', 'list_item', 'table', 'caption', 'header', 'footer')
  7 items tuple；_PDF_BBOX_REQUIRED_TYPES == ('heading', 'paragraph', 'caption', 'list_item') 4 items tuple；
  _NOT_EVALUATED == 'not_evaluated'
- compute_automatic_metrics source 详尽：metrics dict init/pipeline_success 表达式/14 metric 名称/
  schema_check_exception 路径/elements+chunks 获取/各 sub-function 调用
- _pdf_locator_ratio source：'if not elements:'/'return _null("no_elements")'/
  'loc = e.get("source_locator") or {}'/'page = loc.get("page")'/
  'if not isinstance(page, int) or page < 1:'/'continue'/
  'if e.get("type") in _PDF_BBOX_REQUIRED_TYPES:'/'bbox = loc.get("bbox")'/
  'if not _is_valid_bbox(bbox):'/'continue'/'valid += 1'/'return _ratio(valid / len(elements))'
- _docx_locator_ratio source：structural_keys tuple 7 items 精确
- _is_valid_bbox source：'if not isinstance(bbox, list) or len(bbox) != 4:'/'return False'/
  'for v in bbox:'/'if isinstance(v, bool):'/'return False'/
  'if not isinstance(v, (int, float)):'/'return False'/
  'if not math.isfinite(v):'/'return False'/'return True'
- _image_resource_ratio source：images list comprehension/'if not images:'/'return _null("no_image_elements")'/
  'rp = img.get("resource_path")'/'if not rp:'/'continue'/
  'candidates: list[Path] = [Path(rp)]'/'if image_base_dir is not None:'/
  'image_base_dir / Path(rp).name'/'for p in candidates:'/
  'if p.is_file() and p.stat().st_size > 0:'/'except OSError:'/'continue'/'valid += 1'
- _chunk_reference_ratio source：'if not chunks:'/'return _null("no_chunks")'/
  'elem_ids = {e.get("element_id") for e in elements}'/'for c in chunks:'/
  'ids = c.get("source_element_ids") or []'/'if ids and all(sid in elem_ids for sid in ids):'/'valid += 1'
- _strip_unicode_whitespace source：'return "".join(ch for ch in s if not ch.isspace())'
- _text_preservation source：'expected_raw = "".join(' 含 'e.get("content") or ""'/'if e.get("type") != "image"'/
  'actual_raw = "".join(c.get("text") or "" for c in chunks)'/
  'expected = _strip_unicode_whitespace(expected_raw)'/'actual = _strip_unicode_whitespace(actual_raw)'/
  'equal = expected == actual'/'if not expected and not actual:'/'c_expected = Counter(expected)'/
  'c_actual = Counter(actual)'/'common = sum((c_expected & c_actual).values())'/
  'precision = common / sum(c_actual.values())'/'recall = common / sum(c_expected.values())'/
  return 3 keys
- _heading_boundary_ratio source：'headings = [e for e in elements if e.get("type") == "heading"]'/
  'if not headings:'/'return _null("no_heading_elements")'/
  'chunk_first_ids = set()'/'for c in chunks:'/'ids = c.get("source_element_ids") or []'/
  'if ids:'/'chunk_first_ids.add(ids[0])'/
  'matched = sum(1 for h in headings if h.get("element_id") in chunk_first_ids)'/
  'return _ratio(matched / len(headings))'
- _silent_drop_count source：'if not expectations:'/'return _null("no_expectations")'/
  'expected_counts = expectations.get("element_count_by_type") or {}'/
  'if not expected_counts:'/'return _null("no_expectations_element_count")'/
  'drops = 0'/'for t, exp in expected_counts.items():'/'actual = by_type.get(t, 0)'/
  'if actual < exp:'/'drops += (exp - actual)'/'return _int_metric(drops)'
- __all__ 精确：m.__all__ == ['compute_automatic_metrics']
- 模块 namespace 完整：4 helpers + compute_automatic_metrics + _TEXT_TYPES/_PDF_BBOX_REQUIRED_TYPES/_NOT_EVALUATED
- 模块 source 不含 print/logging/json/subprocess/asyncio/threading
- 模块 docstring 含 '纯函数'/'不修改'/'text_preservation'/'不丢不重'/'Counter'/'v1.1'/'空格'
- 常量 _TEXT_TYPES 不含 'image'（image 不参与文本比对）
- _PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES
- compute_automatic_metrics 不修改 document（doc dict 内容不变）
- compute_automatic_metrics 不修改 expectations
- compute_automatic_metrics 两次调用独立 dict
- 常量是 tuple 类型不可变
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

import evaluation.metrics as metrics_module
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


# =========================================================================
# 模块 imports 精确字符串
# =========================================================================


def test_module_source_contains_import_math():
    src = inspect.getsource(metrics_module)
    assert "import math" in src


def test_module_source_contains_from_collections_import_counter():
    src = inspect.getsource(metrics_module)
    assert "from collections import Counter" in src


def test_module_source_contains_from_pathlib_import_path():
    src = inspect.getsource(metrics_module)
    assert "from pathlib import Path" in src


def test_module_source_contains_from_typing_import_any():
    src = inspect.getsource(metrics_module)
    assert "from typing import Any" in src


def test_module_import_order():
    src = inspect.getsource(metrics_module)
    pos_future = src.find("from __future__ import annotations")
    pos_math = src.find("import math")
    pos_collections = src.find("from collections import Counter")
    pos_pathlib = src.find("from pathlib import Path")
    pos_typing = src.find("from typing import Any")
    assert pos_future < pos_math < pos_collections < pos_pathlib < pos_typing


# =========================================================================
# _null source-level
# =========================================================================


def test_null_source_contains_return_dict():
    src = inspect.getsource(_null)
    assert 'return {"value": None, "reason": reason}' in src


def test_null_source_does_not_contain_print():
    src = inspect.getsource(_null)
    assert "print(" not in src


def test_null_source_signature_param_count_1():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1
    assert "reason" in sig.parameters


# =========================================================================
# _ratio source-level
# =========================================================================


def test_ratio_source_contains_float_conversion():
    src = inspect.getsource(_ratio)
    assert 'return {"value": float(value), "reason": None}' in src


def test_ratio_source_does_not_contain_int_conversion():
    """_ratio 用 float 不是 int。"""
    src = inspect.getsource(_ratio)
    # 不应有 int(value)
    assert "int(value)" not in src


def test_ratio_source_signature_param_count_1():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1
    assert "value" in sig.parameters


# =========================================================================
# _bool_metric source-level
# =========================================================================


def test_bool_metric_source_contains_bool_conversion():
    src = inspect.getsource(_bool_metric)
    assert 'return {"value": bool(value), "reason": None}' in src


def test_bool_metric_source_signature_param_count_1():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


# =========================================================================
# _int_metric source-level
# =========================================================================


def test_int_metric_source_contains_int_conversion():
    src = inspect.getsource(_int_metric)
    assert 'return {"value": int(value), "reason": None}' in src


def test_int_metric_source_signature_param_count_1():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


# =========================================================================
# 常量精确
# =========================================================================


def test_text_types_value_exact():
    assert _TEXT_TYPES == ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")


def test_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_text_types_length_7():
    assert len(_TEXT_TYPES) == 7


def test_text_types_does_not_contain_image():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_value_exact():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_pdf_bbox_required_types_length_4():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_pdf_bbox_required_types_is_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES ⊂ _TEXT_TYPES。"""
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_pdf_bbox_required_types_does_not_contain_table():
    """table 不需要 bbox（与 list_item/caption 等区分）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_header_footer():
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_value_exact():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_text_types_source_definition_exact():
    src = inspect.getsource(metrics_module)
    assert (
        '_TEXT_TYPES = ("heading", "paragraph", "list_item", "table", "caption", "header", "footer")'
        in src
    )


def test_pdf_bbox_required_types_source_definition_exact():
    src = inspect.getsource(metrics_module)
    assert (
        '_PDF_BBOX_REQUIRED_TYPES = ("heading", "paragraph", "caption", "list_item")'
        in src
    )


def test_not_evaluated_source_definition_exact():
    src = inspect.getsource(metrics_module)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


# =========================================================================
# compute_automatic_metrics source-level
# =========================================================================


def test_compute_automatic_metrics_source_contains_metrics_init():
    src = inspect.getsource(compute_automatic_metrics)
    assert "metrics: dict[str, Any] = {}" in src


def test_compute_automatic_metrics_source_contains_pipeline_success_expression():
    src = inspect.getsource(compute_automatic_metrics)
    assert "pipeline_success = error is None and document is not None" in src


def test_compute_automatic_metrics_source_contains_bool_metric_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["pipeline_success"] = _bool_metric(pipeline_success)' in src


def test_compute_automatic_metrics_source_contains_error_code_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["error_code"] = (' in src


def test_compute_automatic_metrics_source_contains_document_none_check():
    src = inspect.getsource(compute_automatic_metrics)
    assert "if document is None:" in src


def test_compute_automatic_metrics_source_contains_pipeline_failed_reason():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics[name] = _null("pipeline_failed")' in src


def test_compute_automatic_metrics_source_contains_11_metric_names_in_loop():
    """pipeline_failed loop 含 11 个 metric 名。"""
    src = inspect.getsource(compute_automatic_metrics)
    expected_names = [
        '"element_count_total"',
        '"element_count_by_type"',
        '"pdf_locator_valid_ratio"',
        '"docx_locator_valid_ratio"',
        '"image_resource_exists_ratio"',
        '"chunk_reference_intact_ratio"',
        '"text_preservation_equal"',
        '"text_char_multiset_precision"',
        '"text_char_multiset_recall"',
        '"heading_boundary_compliance"',
        '"silent_drop_count"',
    ]
    for name in expected_names:
        assert name in src


def test_compute_automatic_metrics_source_contains_schema_valid_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["schema_valid"] = _null("pipeline_failed")' in src


def test_compute_automatic_metrics_source_contains_lazy_schema_import():
    """延迟 import schema_validation 避免循环依赖。"""
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_compute_automatic_metrics_source_contains_try_except_for_schema():
    src = inspect.getsource(compute_automatic_metrics)
    assert "try:" in src
    assert "ok = document_passes_schema(document)" in src
    assert 'metrics["schema_valid"] = _bool_metric(ok)' in src


def test_compute_automatic_metrics_source_contains_exception_catch():
    src = inspect.getsource(compute_automatic_metrics)
    assert "except Exception as e:" in src


def test_compute_automatic_metrics_source_contains_schema_check_exception_message():
    src = inspect.getsource(compute_automatic_metrics)
    assert '"schema_check_exception:{type(e).__name__}"' in src or "schema_check_exception:" in src


def test_compute_automatic_metrics_source_contains_elements_get():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'elements = document.get("elements", [])' in src


def test_compute_automatic_metrics_source_contains_chunks_get():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'chunks = document.get("chunks", [])' in src


def test_compute_automatic_metrics_source_contains_int_metric_for_element_count():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["element_count_total"] = _int_metric(len(elements))' in src


def test_compute_automatic_metrics_source_contains_by_type_loop():
    src = inspect.getsource(compute_automatic_metrics)
    assert "by_type: dict[str, int] = {}" in src
    assert "for e in elements:" in src
    assert 't = e.get("type", "unknown")' in src
    assert "by_type[t] = by_type.get(t, 0) + 1" in src


def test_compute_automatic_metrics_source_contains_element_count_by_type_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["element_count_by_type"] = {"value": by_type, "reason": None}' in src


def test_compute_automatic_metrics_source_contains_pdf_locator_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'if source_type == "pdf":' in src
    assert 'metrics["pdf_locator_valid_ratio"] = _pdf_locator_ratio(elements)' in src
    assert 'metrics["pdf_locator_valid_ratio"] = _null("not_pdf_document")' in src


def test_compute_automatic_metrics_source_contains_docx_locator_branch():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'if source_type == "docx":' in src
    assert 'metrics["docx_locator_valid_ratio"] = _docx_locator_ratio(elements)' in src
    assert 'metrics["docx_locator_valid_ratio"] = _null("not_docx_document")' in src


def test_compute_automatic_metrics_source_contains_image_resource_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["image_resource_exists_ratio"] = _image_resource_ratio(' in src
    assert "elements, image_base_dir" in src


def test_compute_automatic_metrics_source_contains_chunk_reference_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["chunk_reference_intact_ratio"] = _chunk_reference_ratio(elements, chunks)' in src


def test_compute_automatic_metrics_source_contains_text_preservation_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert "text_metrics = _text_preservation(elements, chunks)" in src


def test_compute_automatic_metrics_source_contains_text_preservation_keys_assignment():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["text_preservation_equal"] = text_metrics["equal"]' in src
    assert 'metrics["text_char_multiset_precision"] = text_metrics["precision"]' in src
    assert 'metrics["text_char_multiset_recall"] = text_metrics["recall"]' in src


def test_compute_automatic_metrics_source_contains_heading_boundary_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["heading_boundary_compliance"] = _heading_boundary_ratio(elements, chunks)' in src


def test_compute_automatic_metrics_source_contains_silent_drop_call():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'metrics["silent_drop_count"] = _silent_drop_count(by_type, expectations)' in src


def test_compute_automatic_metrics_source_contains_return_metrics():
    src = inspect.getsource(compute_automatic_metrics)
    assert "return metrics" in src


# =========================================================================
# _pdf_locator_ratio source-level
# =========================================================================


def test_pdf_locator_ratio_source_contains_empty_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not elements:" in src
    assert 'return _null("no_elements")' in src


def test_pdf_locator_ratio_source_contains_locator_get():
    src = inspect.getsource(_pdf_locator_ratio)
    assert 'loc = e.get("source_locator") or {}' in src


def test_pdf_locator_ratio_source_contains_page_get():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "page = loc.get(\"page\")" in src


def test_pdf_locator_ratio_source_contains_page_int_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not isinstance(page, int) or page < 1:" in src


def test_pdf_locator_ratio_source_contains_continue():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "continue" in src


def test_pdf_locator_ratio_source_contains_pdf_bbox_required_types_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if e.get(\"type\") in _PDF_BBOX_REQUIRED_TYPES:" in src


def test_pdf_locator_ratio_source_contains_bbox_get():
    src = inspect.getsource(_pdf_locator_ratio)
    assert 'bbox = loc.get("bbox")' in src


def test_pdf_locator_ratio_source_contains_is_valid_bbox_call():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not _is_valid_bbox(bbox):" in src


def test_pdf_locator_ratio_source_contains_return_ratio():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "return _ratio(valid / len(elements))" in src


# =========================================================================
# _docx_locator_ratio source-level
# =========================================================================


def test_docx_locator_ratio_source_contains_structural_keys_tuple():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"section"' in src
    assert '"paragraph_index"' in src
    assert '"run_index"' in src
    assert '"table_index"' in src
    assert '"row_index"' in src
    assert '"col_index"' in src
    assert '"relationship_id"' in src


def test_docx_locator_ratio_source_contains_page_or_bbox_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert 'if "page" in loc or "bbox" in loc:' in src


def test_docx_locator_ratio_source_contains_structural_key_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert "if not any(k in loc for k in structural_keys):" in src


# =========================================================================
# _is_valid_bbox source-level
# =========================================================================


def test_is_valid_bbox_source_contains_list_and_length_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "if not isinstance(bbox, list) or len(bbox) != 4:" in src
    assert "return False" in src


def test_is_valid_bbox_source_contains_for_v_in_bbox():
    src = inspect.getsource(_is_valid_bbox)
    assert "for v in bbox:" in src


def test_is_valid_bbox_source_contains_bool_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "if isinstance(v, bool):" in src


def test_is_valid_bbox_source_contains_int_float_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "if not isinstance(v, (int, float)):" in src


def test_is_valid_bbox_source_contains_isfinite_check():
    src = inspect.getsource(_is_valid_bbox)
    assert "if not math.isfinite(v):" in src


def test_is_valid_bbox_source_contains_return_true():
    src = inspect.getsource(_is_valid_bbox)
    assert "return True" in src


# =========================================================================
# _image_resource_ratio source-level
# =========================================================================


def test_image_resource_ratio_source_contains_images_comprehension():
    src = inspect.getsource(_image_resource_ratio)
    assert 'images = [e for e in elements if e.get("type") == "image"]' in src


def test_image_resource_ratio_source_contains_no_images_check():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not images:" in src
    assert 'return _null("no_image_elements")' in src


def test_image_resource_ratio_source_contains_rp_get():
    src = inspect.getsource(_image_resource_ratio)
    assert 'rp = img.get("resource_path")' in src


def test_image_resource_ratio_source_contains_not_rp_check():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not rp:" in src


def test_image_resource_ratio_source_contains_candidates_list():
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates: list[Path] = [Path(rp)]" in src


def test_image_resource_ratio_source_contains_image_base_dir_check():
    src = inspect.getsource(_image_resource_ratio)
    assert "if image_base_dir is not None:" in src
    assert "image_base_dir / Path(rp).name" in src


def test_image_resource_ratio_source_contains_is_file_and_size_check():
    src = inspect.getsource(_image_resource_ratio)
    assert "if p.is_file() and p.stat().st_size > 0:" in src


def test_image_resource_ratio_source_contains_oserror_catch():
    src = inspect.getsource(_image_resource_ratio)
    assert "except OSError:" in src


# =========================================================================
# _chunk_reference_ratio source-level
# =========================================================================


def test_chunk_reference_ratio_source_contains_no_chunks_check():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "if not chunks:" in src
    assert 'return _null("no_chunks")' in src


def test_chunk_reference_ratio_source_contains_elem_ids_set_comprehension():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "elem_ids = {e.get(\"element_id\") for e in elements}" in src


def test_chunk_reference_ratio_source_contains_ids_get():
    src = inspect.getsource(_chunk_reference_ratio)
    assert 'ids = c.get("source_element_ids") or []' in src


def test_chunk_reference_ratio_source_contains_all_check():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "if ids and all(sid in elem_ids for sid in ids):" in src


# =========================================================================
# _strip_unicode_whitespace source-level
# =========================================================================


def test_strip_unicode_whitespace_source_contains_join_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert 'return "".join(ch for ch in s if not ch.isspace())' in src


def test_strip_unicode_whitespace_source_does_not_contain_strip_call():
    """不用 str.strip()，用 isspace() 判定。"""
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "s.strip(" not in src


def test_strip_unicode_whitespace_source_does_not_contain_replace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert ".replace(" not in src


# =========================================================================
# _text_preservation source-level
# =========================================================================


def test_text_preservation_source_contains_expected_raw_join():
    src = inspect.getsource(_text_preservation)
    assert "expected_raw = \"\".join(" in src


def test_text_preservation_source_contains_content_get():
    src = inspect.getsource(_text_preservation)
    assert 'e.get("content") or ""' in src


def test_text_preservation_source_contains_image_filter():
    src = inspect.getsource(_text_preservation)
    assert 'if e.get("type") != "image"' in src


def test_text_preservation_source_contains_actual_raw_join():
    src = inspect.getsource(_text_preservation)
    assert 'actual_raw = "".join(c.get("text") or "" for c in chunks)' in src


def test_text_preservation_source_contains_strip_call():
    src = inspect.getsource(_text_preservation)
    assert "expected = _strip_unicode_whitespace(expected_raw)" in src
    assert "actual = _strip_unicode_whitespace(actual_raw)" in src


def test_text_preservation_source_contains_equal_check():
    src = inspect.getsource(_text_preservation)
    assert "equal = expected == actual" in src


def test_text_preservation_source_contains_empty_both_check():
    src = inspect.getsource(_text_preservation)
    assert "if not expected and not actual:" in src


def test_text_preservation_source_contains_empty_expected_and_actual_reason():
    src = inspect.getsource(_text_preservation)
    assert '_null("empty_expected_and_actual")' in src


def test_text_preservation_source_contains_counter_intersection():
    src = inspect.getsource(_text_preservation)
    assert "c_expected = Counter(expected)" in src
    assert "c_actual = Counter(actual)" in src
    assert "common = sum((c_expected & c_actual).values())" in src


def test_text_preservation_source_contains_empty_actual_check():
    src = inspect.getsource(_text_preservation)
    assert "if sum(c_actual.values()) == 0:" in src
    assert '_null("empty_actual")' in src


def test_text_preservation_source_contains_empty_expected_check():
    src = inspect.getsource(_text_preservation)
    assert "if sum(c_expected.values()) == 0:" in src
    assert '_null("empty_expected")' in src


def test_text_preservation_source_contains_return_3_keys():
    src = inspect.getsource(_text_preservation)
    assert '"equal": equal_metric' in src
    assert '"precision": precision_metric' in src
    assert '"recall": recall_metric' in src


# =========================================================================
# _heading_boundary_ratio source-level
# =========================================================================


def test_heading_boundary_ratio_source_contains_headings_comprehension():
    src = inspect.getsource(_heading_boundary_ratio)
    assert 'headings = [e for e in elements if e.get("type") == "heading"]' in src


def test_heading_boundary_ratio_source_contains_no_headings_check():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "if not headings:" in src
    assert 'return _null("no_heading_elements")' in src


def test_heading_boundary_ratio_source_contains_chunk_first_ids_set():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids = set()" in src


def test_heading_boundary_ratio_source_contains_ids_zero_index():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "chunk_first_ids.add(ids[0])" in src


def test_heading_boundary_ratio_source_contains_matched_sum():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "matched = sum(1 for h in headings if h.get(\"element_id\") in chunk_first_ids)" in src


def test_heading_boundary_ratio_source_contains_return_ratio():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "return _ratio(matched / len(headings))" in src


# =========================================================================
# _silent_drop_count source-level
# =========================================================================


def test_silent_drop_count_source_contains_no_expectations_check():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expectations:" in src
    assert 'return _null("no_expectations")' in src


def test_silent_drop_count_source_contains_expected_counts_get():
    src = inspect.getsource(_silent_drop_count)
    assert 'expected_counts = expectations.get("element_count_by_type") or {}' in src


def test_silent_drop_count_source_contains_no_expected_counts_check():
    src = inspect.getsource(_silent_drop_count)
    assert "if not expected_counts:" in src
    assert 'return _null("no_expectations_element_count")' in src


def test_silent_drop_count_source_contains_drops_init():
    src = inspect.getsource(_silent_drop_count)
    assert "drops = 0" in src


def test_silent_drop_count_source_contains_items_loop():
    src = inspect.getsource(_silent_drop_count)
    assert "for t, exp in expected_counts.items():" in src


def test_silent_drop_count_source_contains_actual_lt_exp_check():
    src = inspect.getsource(_silent_drop_count)
    assert "if actual < exp:" in src
    assert "drops += (exp - actual)" in src


def test_silent_drop_count_source_contains_return_int_metric():
    src = inspect.getsource(_silent_drop_count)
    assert "return _int_metric(drops)" in src


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_value_exact():
    assert metrics_module.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list_type():
    assert isinstance(metrics_module.__all__, list)


def test_module_all_single_entry():
    assert len(metrics_module.__all__) == 1


def test_module_all_does_not_contain_null_or_ratio():
    assert "_null" not in metrics_module.__all__
    assert "_ratio" not in metrics_module.__all__


def test_module_all_does_not_contain_helpers():
    for name in [
        "_bool_metric",
        "_int_metric",
        "_is_valid_bbox",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    ]:
        assert name not in metrics_module.__all__


def test_module_all_does_not_contain_constants():
    for name in ["_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"]:
        assert name not in metrics_module.__all__


# =========================================================================
# namespace 完整性
# =========================================================================


def test_module_namespace_has_4_helpers():
    for name in ["_null", "_ratio", "_bool_metric", "_int_metric"]:
        assert hasattr(metrics_module, name)


def test_module_namespace_has_compute_automatic_metrics():
    assert hasattr(metrics_module, "compute_automatic_metrics")


def test_module_namespace_has_sub_metrics_helpers():
    for name in [
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    ]:
        assert hasattr(metrics_module, name)


def test_module_namespace_has_constants():
    for name in ["_TEXT_TYPES", "_PDF_BBOX_REQUIRED_TYPES", "_NOT_EVALUATED"]:
        assert hasattr(metrics_module, name)


def test_module_namespace_has_math_attr():
    assert hasattr(metrics_module, "math")


def test_module_namespace_has_counter_attr():
    assert hasattr(metrics_module, "Counter")


def test_module_namespace_has_path_attr():
    assert hasattr(metrics_module, "Path")


def test_module_namespace_has_any_attr():
    assert hasattr(metrics_module, "Any")


def test_module_namespace_does_not_have_subprocess():
    assert not hasattr(metrics_module, "subprocess")


def test_module_namespace_does_not_have_logging():
    assert not hasattr(metrics_module, "logging")


def test_module_namespace_does_not_have_json():
    assert not hasattr(metrics_module, "json")


def test_module_namespace_does_not_have_os():
    assert not hasattr(metrics_module, "os")


def test_module_namespace_does_not_have_asyncio():
    assert not hasattr(metrics_module, "asyncio")


def test_module_namespace_does_not_have_threading():
    assert not hasattr(metrics_module, "threading")


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_print():
    src = inspect.getsource(metrics_module)
    assert "print(" not in src


def test_module_source_does_not_contain_logging():
    src = inspect.getsource(metrics_module)
    assert "logging" not in src


def test_module_source_does_not_contain_subprocess():
    src = inspect.getsource(metrics_module)
    assert "subprocess" not in src


def test_module_source_does_not_contain_async():
    src = inspect.getsource(metrics_module)
    assert "async " not in src
    assert "await " not in src


def test_module_source_does_not_contain_threading():
    src = inspect.getsource(metrics_module)
    assert "import threading" not in src


def test_module_source_does_not_contain_json_import():
    src = inspect.getsource(metrics_module)
    assert "import json" not in src


def test_module_source_does_not_contain_os_import():
    src = inspect.getsource(metrics_module)
    assert "import os" not in src


def test_module_source_does_not_contain_process_single_call():
    """metrics.py 不实际调用 process_single（只在 docstring 中提到）。"""
    src = inspect.getsource(metrics_module)
    # 不应有 import 或调用
    assert "from app.pipeline" not in src
    assert "process_single(" not in src  # 函数调用
    assert "import process_single" not in src


def test_module_source_does_not_contain_image_caption():
    src = inspect.getsource(metrics_module)
    assert "figure_caption" not in src


def test_module_source_does_not_contain_chunk_boundary():
    src = inspect.getsource(metrics_module)
    assert "chunk_boundary" not in src


# =========================================================================
# compute_automatic_metrics 行为
# =========================================================================


def test_compute_automatic_metrics_does_not_modify_document():
    doc = {
        "elements": [{"type": "paragraph", "content": "hello", "element_id": "e1"}],
        "chunks": [{"text": "hello", "source_element_ids": ["e1"]}],
    }
    import copy

    doc_copy = copy.deepcopy(doc)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert doc == doc_copy


def test_compute_automatic_metrics_does_not_modify_expectations():
    doc = {"elements": [], "chunks": []}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    import copy

    exp_copy = copy.deepcopy(expectations)
    compute_automatic_metrics(doc, None, "pdf", expectations)
    assert expectations == exp_copy


def test_compute_automatic_metrics_two_calls_independent_dict():
    doc = {"elements": [], "chunks": []}
    a = compute_automatic_metrics(doc, None, "pdf", None)
    b = compute_automatic_metrics(doc, None, "pdf", None)
    assert a is not b
    # 但内容相等
    assert a == b


def test_compute_automatic_metrics_returns_dict_type():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_automatic_metrics_keys_count_when_failed():
    """document=None + error=None → 13 keys（pipeline_failed 路径）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    # pipeline_success + error_code + schema_valid + 11 null metrics = 14 keys
    assert len(out.keys()) == 14


def test_compute_automatic_metrics_keys_count_when_succeeded():
    """document 存在 + error=None → 14 keys（成功路径）。"""
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    # pipeline_success + error_code + schema_valid + element_count_total +
    # element_count_by_type + pdf_locator + docx_locator + image_resource +
    # chunk_reference + text_preservation_equal + text_char_multiset_precision +
    # text_char_multiset_recall + heading_boundary + silent_drop = 14
    assert len(out.keys()) == 14


def test_compute_automatic_metrics_keys_exact_when_succeeded():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
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
    assert set(out.keys()) == expected_keys


def test_compute_automatic_metrics_keys_exact_when_failed():
    out = compute_automatic_metrics(None, None, "pdf", None)
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
    assert set(out.keys()) == expected_keys


# =========================================================================
# helper metadata
# =========================================================================


def test_all_helpers_are_function_type():
    import types

    for fn in [
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
        compute_automatic_metrics,
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _strip_unicode_whitespace,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
    ]:
        assert isinstance(fn, types.FunctionType)


def test_all_helpers_module_identity():
    """所有 helper __module__ == 'evaluation.metrics'。"""
    for fn in [
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
        compute_automatic_metrics,
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _image_resource_ratio,
        _chunk_reference_ratio,
        _strip_unicode_whitespace,
        _text_preservation,
        _heading_boundary_ratio,
        _silent_drop_count,
    ]:
        assert fn.__module__ == "evaluation.metrics"


# =========================================================================
# 签名 introspection 详细
# =========================================================================


def test_compute_automatic_metrics_signature_param_count_5():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_compute_automatic_metrics_signature_param_names():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters.keys()) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_compute_automatic_metrics_signature_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_automatic_metrics_signature_document_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_compute_automatic_metrics_signature_error_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["error"].default is inspect.Parameter.empty


def test_compute_automatic_metrics_signature_no_var_args():
    from inspect import Parameter

    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_POSITIONAL


def test_compute_automatic_metrics_signature_no_var_kwargs():
    from inspect import Parameter

    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind != Parameter.VAR_KEYWORD


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_is_nonempty_string():
    assert isinstance(metrics_module.__doc__, str)
    assert len(metrics_module.__doc__) > 0


def test_module_docstring_mentions_chun_han_shu_or_pure_function():
    """docstring 提到 '纯函数'。"""
    doc = metrics_module.__doc__
    assert "纯函数" in doc


def test_module_docstring_mentions_bu_xiu_gai_or_no_modify():
    """docstring 提到 '不修改'。"""
    doc = metrics_module.__doc__
    assert "不修改" in doc


def test_module_docstring_mentions_text_preservation():
    doc = metrics_module.__doc__
    assert "text_preservation" in doc.lower() or "文本保留" in doc


def test_module_docstring_mentions_bu_diu_bu_zhong():
    """docstring 提到 '不丢不重'。"""
    doc = metrics_module.__doc__
    assert "不丢不重" in doc


def test_module_docstring_mentions_counter():
    doc = metrics_module.__doc__
    assert "Counter" in doc


def test_module_docstring_mentions_v1_1():
    doc = metrics_module.__doc__
    assert "v1.1" in doc


def test_module_docstring_mentions_kong_bai_or_whitespace():
    """docstring 提到 '空白'。"""
    doc = metrics_module.__doc__
    assert "空白" in doc
