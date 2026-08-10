"""evaluation/metrics.py 第三十三轮 edges 测试（Round 359）。

重点补强 edges31 未触及的角度：
- 4 helper source level 字符串精确补强第二批
- _pdf_locator_ratio/_docx_locator_ratio source level 字符串精确补强第二批
- _is_valid_bbox source level 字符串精确补强第二批
- _image_resource_ratio/_chunk_reference_ratio source level 字符串精确补强第二批
- _strip_unicode_whitespace source level 字符串精确补强第二批
- _text_preservation source level 字符串精确补强第二批
- _heading_boundary_ratio/_silent_drop_count source level 字符串精确补强第二批
- compute_automatic_metrics source level 字符串精确补强第二批
- module source forbidden tokens 第七批
- module source 字符串精确补强
- signatures 精确补强
- 模块整体合理性补强
- 端到端集成补强
"""

from __future__ import annotations

import inspect
import math
import types
from collections import Counter
from pathlib import Path
from typing import Any

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


# ---------- 4 helper source level 字符串精确补强第二批 ----------


def test_null_source_starts_with_def():
    src = inspect.getsource(_null)
    assert src.lstrip().startswith("def _null(")


def test_null_source_one_param():
    src = inspect.getsource(_null)
    assert "reason: str" in src


def test_null_source_returns_dict():
    src = inspect.getsource(_null)
    assert "-> dict[str, Any]" in src


def test_null_source_uses_none_value():
    src = inspect.getsource(_null)
    assert '"value": None' in src


def test_null_source_uses_reason_param():
    src = inspect.getsource(_null)
    assert '"reason": reason' in src


def test_null_source_no_eval():
    src = inspect.getsource(_null)
    assert "eval(" not in src


def test_ratio_source_starts_with_def():
    src = inspect.getsource(_ratio)
    assert src.lstrip().startswith("def _ratio(")


def test_ratio_source_one_param():
    src = inspect.getsource(_ratio)
    assert "value: float" in src


def test_ratio_source_returns_dict():
    src = inspect.getsource(_ratio)
    assert "-> dict[str, Any]" in src


def test_ratio_source_uses_float_conversion():
    src = inspect.getsource(_ratio)
    assert "float(value)" in src


def test_ratio_source_uses_none_reason():
    src = inspect.getsource(_ratio)
    assert '"reason": None' in src


def test_bool_metric_source_starts_with_def():
    src = inspect.getsource(_bool_metric)
    assert src.lstrip().startswith("def _bool_metric(")


def test_bool_metric_source_one_param():
    src = inspect.getsource(_bool_metric)
    assert "value: bool" in src


def test_bool_metric_source_uses_bool_conversion():
    src = inspect.getsource(_bool_metric)
    assert "bool(value)" in src


def test_int_metric_source_starts_with_def():
    src = inspect.getsource(_int_metric)
    assert src.lstrip().startswith("def _int_metric(")


def test_int_metric_source_one_param():
    src = inspect.getsource(_int_metric)
    assert "value: int" in src


def test_int_metric_source_uses_int_conversion():
    src = inspect.getsource(_int_metric)
    assert "int(value)" in src


# ---------- _pdf_locator_ratio source level 字符串精确补强第二批 ----------


def test_pdf_locator_source_starts_with_def():
    src = inspect.getsource(_pdf_locator_ratio)
    assert src.lstrip().startswith("def _pdf_locator_ratio(")


def test_pdf_locator_source_one_param():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "elements: list[dict]" in src


def test_pdf_locator_source_returns_dict():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "-> dict[str, Any]" in src


def test_pdf_locator_source_uses_no_elements_branch():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "if not elements:" in src
    assert '_null("no_elements")' in src


def test_pdf_locator_source_uses_get_source_locator():
    src = inspect.getsource(_pdf_locator_ratio)
    assert 'e.get("source_locator")' in src


def test_pdf_locator_source_uses_page_check():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "isinstance(page, int)" in src
    assert "page < 1" in src


def test_pdf_locator_source_uses_pdf_bbox_required_types():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_pdf_locator_source_uses_is_valid_bbox():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_is_valid_bbox(" in src


def test_pdf_locator_source_returns_ratio():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "_ratio(valid / len(elements))" in src


def test_pdf_locator_source_no_eval():
    src = inspect.getsource(_pdf_locator_ratio)
    assert "eval(" not in src


# ---------- _docx_locator_ratio source level 字符串精确补强第二批 ----------


def test_docx_locator_source_starts_with_def():
    src = inspect.getsource(_docx_locator_ratio)
    assert src.lstrip().startswith("def _docx_locator_ratio(")


def test_docx_locator_source_one_param():
    src = inspect.getsource(_docx_locator_ratio)
    assert "elements: list[dict]" in src


def test_docx_locator_source_returns_dict():
    src = inspect.getsource(_docx_locator_ratio)
    assert "-> dict[str, Any]" in src


def test_docx_locator_source_uses_no_elements():
    src = inspect.getsource(_docx_locator_ratio)
    assert "if not elements:" in src
    assert '_null("no_elements")' in src


def test_docx_locator_source_uses_structural_keys_tuple():
    src = inspect.getsource(_docx_locator_ratio)
    assert "structural_keys = " in src
    assert "section" in src
    assert "paragraph_index" in src
    assert "run_index" in src
    assert "table_index" in src
    assert "row_index" in src
    assert "col_index" in src
    assert "relationship_id" in src


def test_docx_locator_source_uses_page_in_loc_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"page" in loc' in src


def test_docx_locator_source_uses_bbox_in_loc_check():
    src = inspect.getsource(_docx_locator_ratio)
    assert '"bbox" in loc' in src


def test_docx_locator_source_uses_any_structural_keys():
    src = inspect.getsource(_docx_locator_ratio)
    assert "any(k in loc for k in structural_keys)" in src


def test_docx_locator_source_returns_ratio():
    src = inspect.getsource(_docx_locator_ratio)
    assert "_ratio(valid / len(elements))" in src


# ---------- _is_valid_bbox source level 字符串精确补强第二批 ----------


def test_is_valid_bbox_source_starts_with_def():
    src = inspect.getsource(_is_valid_bbox)
    assert src.lstrip().startswith("def _is_valid_bbox(")


def test_is_valid_bbox_source_one_param_any():
    src = inspect.getsource(_is_valid_bbox)
    assert "bbox: Any" in src


def test_is_valid_bbox_source_returns_bool():
    src = inspect.getsource(_is_valid_bbox)
    assert "-> bool" in src


def test_is_valid_bbox_source_uses_isinstance_list():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(bbox, list)" in src


def test_is_valid_bbox_source_uses_len_4():
    src = inspect.getsource(_is_valid_bbox)
    assert "len(bbox) != 4" in src


def test_is_valid_bbox_source_uses_isinstance_bool():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(v, bool)" in src


def test_is_valid_bbox_source_uses_isinstance_int_float():
    src = inspect.getsource(_is_valid_bbox)
    assert "isinstance(v, (int, float))" in src


def test_is_valid_bbox_source_uses_math_isfinite():
    src = inspect.getsource(_is_valid_bbox)
    assert "math.isfinite(v)" in src


# ---------- _image_resource_ratio source level 字符串精确补强第二批 ----------


def test_image_resource_source_starts_with_def():
    src = inspect.getsource(_image_resource_ratio)
    assert src.lstrip().startswith("def _image_resource_ratio(")


def test_image_resource_source_two_params():
    src = inspect.getsource(_image_resource_ratio)
    assert "elements: list[dict]" in src
    assert "image_base_dir: Path | None" in src


def test_image_resource_source_returns_dict():
    src = inspect.getsource(_image_resource_ratio)
    assert "-> dict[str, Any]" in src


def test_image_resource_source_uses_no_images_branch():
    src = inspect.getsource(_image_resource_ratio)
    assert "if not images:" in src
    assert '_null("no_image_elements")' in src


def test_image_resource_source_uses_get_resource_path():
    src = inspect.getsource(_image_resource_ratio)
    assert '.get("resource_path")' in src


def test_image_resource_source_uses_path():
    src = inspect.getsource(_image_resource_ratio)
    assert "Path(rp)" in src


def test_image_resource_source_uses_image_base_dir():
    src = inspect.getsource(_image_resource_ratio)
    assert "image_base_dir is not None" in src


def test_image_resource_source_uses_is_file():
    src = inspect.getsource(_image_resource_ratio)
    assert ".is_file()" in src


def test_image_resource_source_uses_stat_size():
    src = inspect.getsource(_image_resource_ratio)
    assert ".stat().st_size > 0" in src


def test_image_resource_source_uses_oserror():
    src = inspect.getsource(_image_resource_ratio)
    assert "except OSError" in src


def test_image_resource_source_uses_candidates_list():
    src = inspect.getsource(_image_resource_ratio)
    assert "candidates: list[Path]" in src


def test_image_resource_source_returns_ratio():
    src = inspect.getsource(_image_resource_ratio)
    assert "_ratio(valid / len(images))" in src


# ---------- _chunk_reference_ratio source level 字符串精确补强第二批 ----------


def test_chunk_reference_source_starts_with_def():
    src = inspect.getsource(_chunk_reference_ratio)
    assert src.lstrip().startswith("def _chunk_reference_ratio(")


def test_chunk_reference_source_two_params():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "elements: list[dict]" in src
    assert "chunks: list[dict]" in src


def test_chunk_reference_source_returns_dict():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "-> dict[str, Any]" in src


def test_chunk_reference_source_uses_no_chunks():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "if not chunks:" in src
    assert '_null("no_chunks")' in src


def test_chunk_reference_source_uses_elem_ids_set():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "elem_ids = " in src
    assert "for e in elements" in src


def test_chunk_reference_source_uses_get_element_id():
    src = inspect.getsource(_chunk_reference_ratio)
    assert 'e.get("element_id")' in src


def test_chunk_reference_source_uses_get_source_element_ids():
    src = inspect.getsource(_chunk_reference_ratio)
    assert 'c.get("source_element_ids")' in src


def test_chunk_reference_source_uses_all_check():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "all(sid in elem_ids for sid in ids)" in src


def test_chunk_reference_source_returns_ratio():
    src = inspect.getsource(_chunk_reference_ratio)
    assert "_ratio(valid / len(chunks))" in src


# ---------- _strip_unicode_whitespace source level 字符串精确补强第二批 ----------


def test_strip_unicode_source_starts_with_def():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert src.lstrip().startswith("def _strip_unicode_whitespace(")


def test_strip_unicode_source_one_param():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "s: str" in src


def test_strip_unicode_source_returns_str():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "-> str" in src


def test_strip_unicode_source_uses_join():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "join(" in src


def test_strip_unicode_source_uses_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert ".isspace()" in src


def test_strip_unicode_source_uses_not_ch_isspace():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "not ch.isspace()" in src


def test_strip_unicode_source_no_re_sub():
    src = inspect.getsource(_strip_unicode_whitespace)
    assert "re.sub" not in src


# ---------- _text_preservation source level 字符串精确补强第二批 ----------


def test_text_preservation_source_starts_with_def():
    src = inspect.getsource(_text_preservation)
    assert src.lstrip().startswith("def _text_preservation(")


def test_text_preservation_source_two_params():
    src = inspect.getsource(_text_preservation)
    assert "elements: list[dict]" in src
    assert "chunks: list[dict]" in src


def test_text_preservation_source_returns_dict():
    src = inspect.getsource(_text_preservation)
    assert "-> dict[str, Any]" in src


def test_text_preservation_source_uses_strip_unicode_whitespace():
    src = inspect.getsource(_text_preservation)
    assert "_strip_unicode_whitespace(" in src


def test_text_preservation_source_uses_counter():
    src = inspect.getsource(_text_preservation)
    assert "Counter(" in src


def test_text_preservation_source_uses_intersection():
    src = inspect.getsource(_text_preservation)
    assert "intersection(" in src or "&" in src


def test_text_preservation_source_uses_join():
    src = inspect.getsource(_text_preservation)
    assert ".join(" in src


def test_text_preservation_source_3_keys():
    src = inspect.getsource(_text_preservation)
    assert '"equal"' in src
    assert '"precision"' in src
    assert '"recall"' in src


def test_text_preservation_source_returns_3_keys_dict():
    src = inspect.getsource(_text_preservation)
    assert '"equal":' in src
    assert '"precision":' in src
    assert '"recall":' in src


# ---------- _heading_boundary_ratio source level 字符串精确补强第二批 ----------


def test_heading_boundary_source_starts_with_def():
    src = inspect.getsource(_heading_boundary_ratio)
    assert src.lstrip().startswith("def _heading_boundary_ratio(")


def test_heading_boundary_source_two_params():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "elements: list[dict]" in src
    assert "chunks: list[dict]" in src


def test_heading_boundary_source_returns_dict():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "-> dict[str, Any]" in src


def test_heading_boundary_source_uses_get_type_heading():
    src = inspect.getsource(_heading_boundary_ratio)
    assert '"heading"' in src


def test_heading_boundary_source_uses_no_heading_branch():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "no_heading_elements" in src


def test_heading_boundary_source_returns_ratio():
    src = inspect.getsource(_heading_boundary_ratio)
    assert "_ratio(matched / len(headings))" in src


# ---------- _silent_drop_count source level 字符串精确补强第二批 ----------


def test_silent_drop_source_starts_with_def():
    src = inspect.getsource(_silent_drop_count)
    assert src.lstrip().startswith("def _silent_drop_count(")


def test_silent_drop_source_two_params():
    src = inspect.getsource(_silent_drop_count)
    assert "by_type: dict[str, int]" in src
    assert "expectations" in src


def test_silent_drop_source_returns_dict():
    src = inspect.getsource(_silent_drop_count)
    assert "-> dict[str, Any]" in src


def test_silent_drop_source_uses_no_expectations_branch():
    src = inspect.getsource(_silent_drop_count)
    assert "no_expectations" in src


def test_silent_drop_source_uses_int_metric():
    src = inspect.getsource(_silent_drop_count)
    assert "_int_metric(" in src


# ---------- compute_automatic_metrics source level 字符串精确补强第二批 ----------


def test_compute_source_starts_with_def():
    src = inspect.getsource(compute_automatic_metrics)
    assert src.lstrip().startswith("def compute_automatic_metrics(")


def test_compute_source_5_params():
    src = inspect.getsource(compute_automatic_metrics)
    assert "document: dict[str, Any] | None" in src
    assert "error: dict[str, Any] | None" in src
    assert "source_type: str" in src
    assert "expectations: dict[str, Any] | None" in src
    assert "image_base_dir: Path | None = None" in src


def test_compute_source_returns_dict():
    src = inspect.getsource(compute_automatic_metrics)
    assert "-> dict[str, Any]" in src


def test_compute_source_uses_pipeline_success():
    src = inspect.getsource(compute_automatic_metrics)
    assert "pipeline_success = " in src
    assert "error is None and document is not None" in src


def test_compute_source_uses_bool_metric_for_success():
    src = inspect.getsource(compute_automatic_metrics)
    assert '_bool_metric(pipeline_success)' in src


def test_compute_source_uses_error_code_dict():
    src = inspect.getsource(compute_automatic_metrics)
    assert '"error_code"' in src
    assert 'error["code"]' in src


def test_compute_source_handles_document_none():
    src = inspect.getsource(compute_automatic_metrics)
    assert "if document is None:" in src
    assert 'pipeline_failed' in src


def test_compute_source_lazy_import_schema_validation():
    src = inspect.getsource(compute_automatic_metrics)
    assert "from evaluation.schema_validation import document_passes_schema" in src


def test_compute_source_uses_try_except_exception():
    src = inspect.getsource(compute_automatic_metrics)
    assert "try:" in src
    assert "except Exception" in src


def test_compute_source_uses_schema_check_exception_reason():
    src = inspect.getsource(compute_automatic_metrics)
    assert "schema_check_exception:" in src


def test_compute_source_uses_get_elements_chunks():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'document.get("elements", [])' in src
    assert 'document.get("chunks", [])' in src


def test_compute_source_calls_all_helpers():
    src = inspect.getsource(compute_automatic_metrics)
    assert "_pdf_locator_ratio(" in src
    assert "_docx_locator_ratio(" in src
    assert "_image_resource_ratio(" in src
    assert "_chunk_reference_ratio(" in src
    assert "_text_preservation(" in src
    assert "_heading_boundary_ratio(" in src
    assert "_silent_drop_count(" in src


def test_compute_source_uses_pdf_docx_branches():
    src = inspect.getsource(compute_automatic_metrics)
    assert 'source_type == "pdf"' in src
    assert 'source_type == "docx"' in src
    assert "not_pdf_document" in src
    assert "not_docx_document" in src


def test_compute_source_returns_metrics_var():
    src = inspect.getsource(compute_automatic_metrics)
    assert "return metrics" in src


def test_compute_source_initializes_metrics_dict():
    src = inspect.getsource(compute_automatic_metrics)
    assert "metrics: dict[str, Any] = {}" in src or "metrics = {}" in src


def test_compute_source_uses_int_metric_for_count():
    src = inspect.getsource(compute_automatic_metrics)
    assert "_int_metric(len(elements))" in src


def test_compute_source_uses_by_type_dict():
    src = inspect.getsource(compute_automatic_metrics)
    assert "by_type: dict[str, int]" in src


def test_compute_source_uses_11_metric_keys_for_none():
    src = inspect.getsource(compute_automatic_metrics)
    # 当 document 是 None 时，写入 11 个 metric（element_count_total 等）
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


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio", "threading", "concurrent", "multiprocessing",
        "queue", "socket", "select", "subprocess",
        "re.match", "re.sub", "re.compile",
        "datetime.datetime",
        "time.time", "time.sleep",
        "os.system", "os.popen",
        "logging.getLogger",
        "urllib.request", "http.client",
        "ctypes", "pickle.loads",
        "shutil.rmtree",
        "tempfile.mkdtemp",
        "glob.glob",
        "unittest.TestCase",
        "pytest.fixture",
        "sys.exit",
        "copy.deepcopy",
        "weakref.ref",
        "abc.ABC",
        "contextlib.contextmanager",
        "operator.add",
        "functools.reduce",
        "itertools.chain",
        "collections.OrderedDict",
        "collections.deque",
        "collections.defaultdict",
        "importlib.import_module",
        "platform.system",
    ],
)
def test_metrics_source_no_forbidden_token(token):
    src = inspect.getsource(mmod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module source 字符串精确补强 ----------


def test_module_source_docstring_present():
    src = inspect.getsource(mmod)
    assert src.startswith('"""')


def test_module_source_docstring_mentions_自动指标():
    assert "自动指标" in mmod.__doc__ or "automatic" in mmod.__doc__.lower()


def test_module_source_docstring_mentions_text_preservation():
    assert "text_preservation" in mmod.__doc__


def test_module_source_docstring_mentions_unicode_whitespace():
    assert "Unicode 空白" in mmod.__doc__ or "Unicode" in mmod.__doc__


def test_module_source_docstring_mentions_counter():
    assert "Counter" in mmod.__doc__


def test_module_source_docstring_mentions_v1_1():
    assert "v1.1" in mmod.__doc__


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
    assert '_TEXT_TYPES = (' in src
    assert '"heading"' in src
    assert '"paragraph"' in src
    assert '"list_item"' in src
    assert '"table"' in src
    assert '"caption"' in src
    assert '"header"' in src
    assert '"footer"' in src


def test_module_source_pdf_bbox_required_types_constant():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = (' in src


def test_module_source_not_evaluated_constant():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_no_relative_above_root():
    src = inspect.getsource(mmod)
    assert "from .." not in src


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
    classes = [
        name for name, val in vars(mmod).items()
        if isinstance(val, type) and val.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_source_11_user_functions():
    funcs = [
        name for name, val in vars(mmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_null", "_ratio", "_bool_metric", "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio", "_docx_locator_ratio", "_is_valid_bbox",
        "_image_resource_ratio", "_chunk_reference_ratio",
        "_strip_unicode_whitespace", "_text_preservation",
        "_heading_boundary_ratio", "_silent_drop_count",
    }


def test_module_source_all_1_entry():
    src = inspect.getsource(mmod)
    assert '__all__ = [' in src
    assert '"compute_automatic_metrics"' in src


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
    assert ".unlink(" not in src


def test_module_source_no_write():
    src = inspect.getsource(mmod)
    assert ".write(" not in src


# ---------- signatures 精确补强 ----------


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
    assert [p.name for p in params] == ["elements", "image_base_dir"]


def test_signature_chunk_reference():
    sig = inspect.signature(_chunk_reference_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["elements", "chunks"]


def test_signature_strip_unicode_whitespace():
    sig = inspect.signature(_strip_unicode_whitespace)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "s"


def test_signature_text_preservation():
    sig = inspect.signature(_text_preservation)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["elements", "chunks"]


def test_signature_heading_boundary():
    sig = inspect.signature(_heading_boundary_ratio)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["elements", "chunks"]


def test_signature_silent_drop_count():
    sig = inspect.signature(_silent_drop_count)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["by_type", "expectations"]


def test_signature_compute_automatic_metrics():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    assert len(params) == 5
    assert [p.name for p in params] == [
        "document", "error", "source_type", "expectations", "image_base_dir",
    ]


def test_signature_compute_image_base_dir_default_none():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_document_no_default():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_signature_compute_no_varargs():
    sig = inspect.signature(compute_automatic_metrics)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- 模块整体合理性补强 ----------


def test_module_has_docstring():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 50


def test_module_has_all_attribute():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list():
    assert isinstance(mmod.__all__, list)


def test_module_all_length_1():
    assert len(mmod.__all__) == 1


def test_module_all_entries_unique():
    assert len(set(mmod.__all__)) == len(mmod.__all__)


def test_module_all_entries_are_str():
    for entry in mmod.__all__:
        assert isinstance(entry, str)


def test_module_all_only_compute_automatic_metrics():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_namespace_14_callables():
    funcs = [
        name for name, val in vars(mmod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == mmod.__name__
    ]
    assert len(funcs) == 14


def test_module_namespace_3_constants():
    """3 个 module-level 常量：_TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED。"""
    assert hasattr(mmod, "_TEXT_TYPES")
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_no_user_classes():
    classes = [
        name for name, val in vars(mmod).items()
        if isinstance(val, type) and val.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_name_is_evaluation_metrics():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_file_ends_with_metrics_py():
    assert mmod.__file__.endswith("metrics.py")


def test_module_text_types_is_tuple():
    assert isinstance(_TEXT_TYPES, tuple)


def test_module_text_types_length_7():
    assert len(_TEXT_TYPES) == 7


def test_module_pdf_bbox_required_types_is_tuple():
    assert isinstance(_PDF_BBOX_REQUIRED_TYPES, tuple)


def test_module_pdf_bbox_required_types_length_4():
    assert len(_PDF_BBOX_REQUIRED_TYPES) == 4


def test_module_not_evaluated_is_str():
    assert isinstance(_NOT_EVALUATED, str)


def test_module_not_evaluated_value():
    assert _NOT_EVALUATED == "not_evaluated"


def test_module_pdf_bbox_subset_of_text_types():
    """_PDF_BBOX_REQUIRED_TYPES 是 _TEXT_TYPES 的子集。"""
    assert set(_PDF_BBOX_REQUIRED_TYPES).issubset(set(_TEXT_TYPES))


def test_module_function_module_eq_mmod():
    assert compute_automatic_metrics.__module__ == "evaluation.metrics"
    assert _null.__module__ == "evaluation.metrics"
    assert _ratio.__module__ == "evaluation.metrics"


def test_module_constants_module_builtins():
    """常量的 __module__ 是 builtins（str/tuple 都是 builtins）。"""
    assert _TEXT_TYPES.__class__.__module__ == "builtins"


# ---------- 端到端集成补强 ----------


def test_e2e_compute_metrics_minimal_pdf_doc():
    """最简 PDF 文档。"""
    doc = {
        "source_type": "pdf",
        "elements": [],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 0


def test_e2e_compute_metrics_document_none():
    m = compute_automatic_metrics(None, None, "pdf", None)
    assert m["pipeline_success"]["value"] is False
    # document None 时所有其他指标 reason=pipeline_failed
    for k in (
        "element_count_total", "pdf_locator_valid_ratio",
        "text_preservation_equal", "silent_drop_count",
    ):
        assert m[k]["reason"] == "pipeline_failed"


def test_e2e_compute_metrics_error_dict():
    m = compute_automatic_metrics(
        None, {"code": "x"}, "pdf", None,
    )
    assert m["pipeline_success"]["value"] is False
    assert m["error_code"]["value"] == "x"


def test_e2e_compute_metrics_does_not_mutate_doc():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    import json as _json
    before = _json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert _json.dumps(doc, sort_keys=True) == before


def test_e2e_compute_metrics_idempotent():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_e2e_compute_metrics_positional_args():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None, None)
    assert m["pipeline_success"]["value"] is True


def test_e2e_compute_metrics_kwargs():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    m = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf",
        expectations=None, image_base_dir=None,
    )
    assert m["pipeline_success"]["value"] is True


def test_e2e_compute_metrics_docx_source_type():
    doc = {"source_type": "docx", "elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "docx", None)
    # source_type=docx → pdf_locator_valid_ratio 是 not_pdf_document
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_compute_metrics_unknown_source_type():
    doc = {"source_type": "unknown", "elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "unknown", None)
    # 既不是 pdf 也不是 docx → 两个 locator 都 not_*_document
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"
    assert m["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_e2e_compute_metrics_with_pdf_elements():
    doc = {
        "source_type": "pdf",
        "elements": [
            {
                "element_id": "e1", "type": "paragraph",
                "content": "hello",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            },
        ],
        "chunks": [
            {"source_element_ids": ["e1"], "text": "hello"},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 1
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_text_preservation_with_text():
    elements = [
        {"type": "paragraph", "content": "hello"},
    ]
    chunks = [{"text": "hello"}]
    tm = _text_preservation(elements, chunks)
    assert tm["equal"]["value"] is True
    assert tm["precision"]["value"] == 1.0
    assert tm["recall"]["value"] == 1.0


def test_e2e_text_preservation_with_loss():
    elements = [
        {"type": "paragraph", "content": "hello world"},
    ]
    chunks = [{"text": "hello"}]  # 丢了 " world"
    tm = _text_preservation(elements, chunks)
    assert tm["equal"]["value"] is False
    # precision = 5/5 = 1.0（actual 全在 expected 中）
    # recall = 5/11
    assert tm["precision"]["value"] == 1.0
    assert tm["recall"]["value"] < 1.0


def test_e2e_strip_unicode_whitespace_with_nbsp():
    s = "hello world"  # NBSP
    assert _strip_unicode_whitespace(s) == "helloworld"


def test_e2e_strip_unicode_whitespace_with_em_space():
    s = "hello world"  # EM SPACE
    assert _strip_unicode_whitespace(s) == "helloworld"


def test_e2e_strip_unicode_whitespace_with_ideographic_space():
    s = "hello　world"  # IDEOGRAPHIC SPACE
    assert _strip_unicode_whitespace(s) == "helloworld"


def test_e2e_is_valid_bbox_valid():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_e2e_is_valid_bbox_with_negative():
    assert _is_valid_bbox([-10, -10, 100, 100]) is True


def test_e2e_is_valid_bbox_with_floats():
    assert _is_valid_bbox([0.0, 0.0, 1.5, 2.5]) is True


def test_e2e_is_valid_bbox_invalid_len():
    assert _is_valid_bbox([0, 0, 100]) is False  # len=3


def test_e2e_is_valid_bbox_invalid_type_tuple():
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_e2e_is_valid_bbox_with_bool():
    assert _is_valid_bbox([True, 0, 100, 100]) is False


def test_e2e_is_valid_bbox_with_nan():
    assert _is_valid_bbox([0, 0, float("nan"), 100]) is False


def test_e2e_is_valid_bbox_with_inf():
    assert _is_valid_bbox([0, 0, float("inf"), 100]) is False


def test_e2e_pdf_locator_no_elements():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_e2e_pdf_locator_with_invalid_page():
    elements = [{"type": "paragraph", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_e2e_pdf_locator_with_negative_page():
    elements = [{"type": "paragraph", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_e2e_docx_locator_no_elements():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_e2e_docx_locator_with_page_in_loc():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_e2e_chunk_reference_no_chunks():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_e2e_chunk_reference_all_valid():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_e2e_chunk_reference_partial_unknown():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "unknown"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # all() → 一个 unknown 就整 chunk 不 valid
    assert out["value"] == 0.0


def test_e2e_image_resource_no_images():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["reason"] == "no_image_elements"


def test_e2e_silent_drop_no_expectations():
    out = _silent_drop_count({"paragraph": 5}, None)
    assert out["reason"] == "no_expectations"


def test_e2e_silent_drop_zero_drops():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_e2e_silent_drop_some_drops():
    out = _silent_drop_count({"paragraph": 3}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 2


def test_e2e_silent_drop_more_actual_than_expected():
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    # actual > expected → 0 drops
    assert out["value"] == 0


def test_e2e_heading_boundary_no_chunks():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    # 没有 chunks → chunk_first_ids 是空集 → matched=0 → ratio 0.0
    assert out["value"] == 0.0


def test_e2e_heading_boundary_no_headings():
    elements = [{"type": "paragraph"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"
