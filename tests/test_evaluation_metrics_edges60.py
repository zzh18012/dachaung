"""evaluation/metrics.py 第六十一轮 edges 测试（Round 553）。

补强 edges59 未触及的角度（第三十四批）。
"""

from __future__ import annotations

import inspect
import math
from collections import Counter
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

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


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十四批


def test_null_value_is_none_batch34():
    m = _null("reason_x")
    assert m["value"] is None
    assert m["reason"] == "reason_x"


def test_null_keys_only_two_batch34():
    m = _null("x")
    assert set(m.keys()) == {"value", "reason"}


def test_ratio_value_is_float_batch34():
    m = _ratio(0.5)
    assert isinstance(m["value"], float)
    assert m["value"] == 0.5


def test_ratio_int_promoted_to_float_batch34():
    m = _ratio(1)
    assert m["value"] == 1.0
    assert isinstance(m["value"], float)


def test_ratio_reason_is_none_batch34():
    m = _ratio(0.0)
    assert m["reason"] is None


def test_bool_metric_value_is_bool_batch34():
    m = _bool_metric(1)  # truthy int
    assert m["value"] is True
    assert isinstance(m["value"], bool)


def test_bool_metric_false_batch34():
    m = _bool_metric(0)
    assert m["value"] is False


def test_int_metric_value_is_int_batch34():
    m = _int_metric(3.7)
    assert m["value"] == 3  # int(3.7) = 3
    assert isinstance(m["value"], int)


def test_int_metric_negative_batch34():
    m = _int_metric(-5)
    assert m["value"] == -5


def test_int_metric_reason_none_batch34():
    m = _int_metric(0)
    assert m["reason"] is None


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 第三十四批


def test_text_types_first_is_heading_batch34():
    assert _TEXT_TYPES[0] == "heading"


def test_text_types_last_is_footer_batch34():
    assert _TEXT_TYPES[-1] == "footer"


def test_text_types_caption_included_batch34():
    assert "caption" in _TEXT_TYPES


def test_text_types_image_not_included_batch34():
    assert "image" not in _TEXT_TYPES


def test_pdf_bbox_required_types_exact_batch34():
    assert _PDF_BBOX_REQUIRED_TYPES == ("heading", "paragraph", "caption", "list_item")


def test_pdf_bbox_required_types_in_text_types_batch34():
    for t in _PDF_BBOX_REQUIRED_TYPES:
        assert t in _TEXT_TYPES


def test_not_evaluated_value_batch34():
    assert _NOT_EVALUATED == "not_evaluated"


def test_not_evaluated_is_string_batch34():
    assert isinstance(_NOT_EVALUATED, str)


# ---------- compute_automatic_metrics 第三十四批


def test_compute_returns_dict_batch34():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert isinstance(out, dict)


def test_compute_failed_pipeline_keys_batch34():
    """pipeline 失败时返回 14 个 key。"""
    out = compute_automatic_metrics(None, {"code": "E_PARSE"}, "pdf", None)
    expected = {
        "pipeline_success", "error_code", "schema_valid",
        "element_count_total", "element_count_by_type",
        "pdf_locator_valid_ratio", "docx_locator_valid_ratio",
        "image_resource_exists_ratio", "chunk_reference_intact_ratio",
        "text_preservation_equal", "text_char_multiset_precision",
        "text_char_multiset_recall", "heading_boundary_compliance",
        "silent_drop_count",
    }
    assert expected.issubset(set(out.keys()))


def test_compute_failed_pipeline_success_false_batch34():
    out = compute_automatic_metrics(None, {"code": "E_X"}, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_failed_pipeline_error_code_present_batch34():
    out = compute_automatic_metrics(None, {"code": "E_X"}, "pdf", None)
    assert out["error_code"]["value"] == "E_X"


def test_compute_no_error_no_doc_batch34():
    """error=None + document=None → success=False（document 是 None）。"""
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_success_no_elements_no_chunks_batch34():
    """最小合法 document → success=True。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 0


def test_compute_pdf_source_not_evaluated_docx_ratio_batch34():
    """source_type=pdf → docx_locator_valid_ratio reason=not_docx_document。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["reason"] == "not_docx_document"


def test_compute_docx_source_not_evaluated_pdf_ratio_batch34():
    doc = {"source_type": "docx", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_no_image_elements_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["image_resource_exists_ratio"]["reason"] == "no_image_elements"


def test_compute_no_chunks_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["chunk_reference_intact_ratio"]["reason"] == "no_chunks"


def test_compute_no_headings_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["heading_boundary_compliance"]["reason"] == "no_heading_elements"


def test_compute_no_expectations_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_empty_expectations_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", {})
    assert out["silent_drop_count"]["reason"] == "no_expectations"


def test_compute_empty_expectations_count_batch34():
    """expectations={} 也算 no_expectations。"""
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", {})
    assert out["silent_drop_count"]["value"] is None


def test_compute_with_expectations_zero_drop_batch34():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 0


def test_compute_with_expectations_drop_batch34():
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
        "chunks": [],
    }
    exp = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["silent_drop_count"]["value"] == 4


# ---------- _pdf_locator_ratio 第三十四批


def test_pdf_locator_no_elements_batch34():
    out = _pdf_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_pdf_locator_text_no_bbox_batch34():
    """text type 但没 bbox → 不 valid。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_valid_bbox_batch34():
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_image_no_bbox_required_batch34():
    """image type 不需要 bbox（不在 _PDF_BBOX_REQUIRED_TYPES）。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_page_zero_batch34():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_no_page_batch34():
    elements = [{"type": "image", "source_locator": {}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第三十四批


def test_docx_locator_no_elements_batch34():
    out = _docx_locator_ratio([])
    assert out["reason"] == "no_elements"


def test_docx_locator_with_page_invalid_batch34():
    """locator 含 page → 不合规。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_paragraph_index_batch34():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_table_index_batch34():
    elements = [{"type": "table", "source_locator": {"table_index": 0, "row_index": 0, "col_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_section_batch34():
    elements = [{"type": "paragraph", "source_locator": {"section": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_mixed_batch34():
    elements = [
        {"type": "paragraph", "source_locator": {"section": 1}},
        {"type": "paragraph", "source_locator": {"page": 1}},
    ]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.5


# ---------- _is_valid_bbox 第三十四批


def test_is_valid_bbox_correct_batch34():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_floats_batch34():
    assert _is_valid_bbox([0.0, 0.5, 10.2, 99.9]) is True


def test_is_valid_bbox_too_short_batch34():
    assert _is_valid_bbox([0, 0, 10]) is False


def test_is_valid_bbox_too_long_batch34():
    assert _is_valid_bbox([0, 0, 0, 0, 0]) is False


def test_is_valid_bbox_bool_inside_batch34():
    """bbox 含 bool → 无效（bool 是 int 子类但显式排除）。"""
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_string_batch34():
    assert _is_valid_bbox(["0", "0", "10", "10"]) is False


def test_is_valid_bbox_none_batch34():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_tuple_batch34():
    """非 list → 无效。"""
    assert _is_valid_bbox((0, 0, 10, 10)) is False


def test_is_valid_bbox_nan_batch34():
    assert _is_valid_bbox([float("nan"), 0, 10, 10]) is False


def test_is_valid_bbox_inf_batch34():
    assert _is_valid_bbox([float("inf"), 0, 10, 10]) is False


# ---------- _image_resource_ratio 第三十四批


def test_image_ratio_no_images_batch34():
    out = _image_resource_ratio([], None)
    assert out["reason"] == "no_image_elements"


def test_image_ratio_no_resource_path_batch34():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_resource_exists_batch34(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_ratio_resource_missing_batch34(tmp_path):
    elements = [{"type": "image", "resource_path": str(tmp_path / "missing.png")}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_mixed_batch34(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_ratio_base_dir_filename_only_batch34(tmp_path):
    """resource_path 是文件名（无目录），image_base_dir 提供位置。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_ratio_empty_file_batch34(tmp_path):
    """size=0 文件视为不存在。"""
    img = tmp_path / "empty.png"
    img.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


# ---------- _chunk_reference_ratio 第三十四批


def test_chunk_ref_no_chunks_batch34():
    out = _chunk_reference_ratio([], [])
    assert out["reason"] == "no_chunks"


def test_chunk_ref_empty_source_ids_batch34():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_no_source_ids_field_batch34():
    elements = [{"element_id": "e1"}]
    chunks = [{}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_valid_batch34():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_ref_invalid_id_batch34():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e_nonexistent"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_partial_valid_batch34():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e_nonexistent"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_chunk_ref_multi_ids_all_valid_batch34():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_ref_multi_ids_partial_batch34():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _strip_unicode_whitespace 第三十四批


def test_strip_unicode_empty_batch34():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_no_whitespace_batch34():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_all_whitespace_batch34():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_nbsp_batch34():
    """NBSP \\x0A0 是 Unicode 空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_em_space_batch34():
    """em space U+2003 是空白。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ideographic_space_batch34():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_preserves_order_batch34():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_mixed_batch34():
    assert _strip_unicode_whitespace("\ta\nb\tc\r") == "abc"


# ---------- _text_preservation 第三十四批


def test_text_preservation_returns_three_keys_batch34():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_empty_both_batch34():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"
    assert out["recall"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_perfect_batch34():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_ignores_whitespace_batch34():
    elements = [{"type": "paragraph", "content": "a b c"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_excludes_image_content_batch34():
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "should_be_ignored"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_missing_chunk_partial_recall_batch34():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "ab"}]  # 漏掉 c
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 1.0
    assert abs(out["recall"]["value"] - 2/3) < 1e-9


def test_text_preservation_extra_chars_batch34():
    elements = [{"type": "paragraph", "content": "ab"}]
    chunks = [{"text": "abc"}]  # 多 c
    out = _text_preservation(elements, chunks)
    assert out["precision"]["value"] == 2/3
    assert out["recall"]["value"] == 1.0


# ---------- _heading_boundary_ratio 第三十四批


def test_heading_boundary_no_headings_batch34():
    out = _heading_boundary_ratio([], [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_no_chunks_batch34():
    elements = [{"type": "heading", "element_id": "h1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["value"] == 0.0


def test_heading_boundary_chunk_first_id_matches_batch34():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_chunk_first_id_not_match_batch34():
    """heading_id 不是 chunk 首元素 → 不合规。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_partial_batch34():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["other"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


# ---------- _silent_drop_count 第三十四批


def test_silent_drop_no_expectations_batch34():
    out = _silent_drop_count({}, None)
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expectations_batch34():
    out = _silent_drop_count({}, {})
    assert out["reason"] == "no_expectations"


def test_silent_drop_empty_expected_counts_batch34():
    out = _silent_drop_count({}, {"element_count_by_type": {}})
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_zero_batch34():
    out = _silent_drop_count({"paragraph": 5}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_excess_batch34():
    """actual > expected → 不算 drop（max(0, ...)）。"""
    out = _silent_drop_count({"paragraph": 10}, {"element_count_by_type": {"paragraph": 5}})
    assert out["value"] == 0


def test_silent_drop_missing_type_batch34():
    """expected 含 type X 但 by_type 不含 → 全部算 drop。"""
    out = _silent_drop_count({"paragraph": 1}, {"element_count_by_type": {"paragraph": 1, "heading": 3}})
    assert out["value"] == 3


def test_silent_drop_multi_type_batch34():
    out = _silent_drop_count(
        {"paragraph": 1, "heading": 2},
        {"element_count_by_type": {"paragraph": 5, "heading": 3}},
    )
    assert out["value"] == (5 - 1) + (3 - 2)


# ---------- module source forbidden tokens 第五十三批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch34(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch34():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_future_annotations_batch34():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_math_import_batch34():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_counter_import_batch34():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_contains_pathlib_import_batch34():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_import_batch34():
    src = inspect.getsource(mmod)
    assert "from typing import Any" in src


def test_module_source_contains_text_types_const_batch34():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in src


def test_module_source_contains_pdf_bbox_const_batch34():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in src


def test_module_source_contains_not_evaluated_const_batch34():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in src


def test_module_source_contains_compute_func_batch34():
    src = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in src


def test_module_source_contains_null_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _null(" in src


def test_module_source_contains_ratio_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _ratio(" in src


def test_module_source_contains_bool_metric_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _bool_metric(" in src


def test_module_source_contains_int_metric_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _int_metric(" in src


def test_module_source_contains_pdf_locator_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in src


def test_module_source_contains_docx_locator_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in src


def test_module_source_contains_is_valid_bbox_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _is_valid_bbox(" in src


def test_module_source_contains_image_resource_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _image_resource_ratio(" in src


def test_module_source_contains_chunk_ref_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _chunk_reference_ratio(" in src


def test_module_source_contains_strip_unicode_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_text_preservation_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _text_preservation(" in src


def test_module_source_contains_heading_boundary_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_silent_drop_func_batch34():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_contains_all_batch34():
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第四十九批


def test_signature_null_one_param_batch34():
    sig = inspect.signature(_null)
    params = list(sig.parameters.keys())
    assert params == ["reason"]


def test_signature_ratio_one_param_batch34():
    sig = inspect.signature(_ratio)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_bool_metric_one_param_batch34():
    sig = inspect.signature(_bool_metric)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_int_metric_one_param_batch34():
    sig = inspect.signature(_int_metric)
    params = list(sig.parameters.keys())
    assert params == ["value"]


def test_signature_compute_params_batch34():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_signature_compute_image_base_dir_default_none_batch34():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_pdf_locator_params_batch34():
    sig = inspect.signature(_pdf_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_docx_locator_params_batch34():
    sig = inspect.signature(_docx_locator_ratio)
    assert list(sig.parameters.keys()) == ["elements"]


def test_signature_is_valid_bbox_params_batch34():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_signature_image_resource_params_batch34():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_ref_params_batch34():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_strip_unicode_params_batch34():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_signature_text_preservation_params_batch34():
    sig = inspect.signature(_text_preservation)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_params_batch34():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_silent_drop_params_batch34():
    sig = inspect.signature(_silent_drop_count)
    assert list(sig.parameters.keys()) == ["by_type", "expectations"]


def test_signature_compute_return_dict_batch34():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.return_annotation == "dict[str, Any]"


# ---------- module 合理性第四十九批


def test_module_has_future_annotations_batch34():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_imports_math_batch34():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_has_compute_func_batch34():
    assert callable(mmod.compute_automatic_metrics)


def test_module_has_text_types_const_batch34():
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_has_pdf_bbox_const_batch34():
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_has_all_batch34():
    assert hasattr(mmod, "__all__")
    assert "compute_automatic_metrics" in mmod.__all__


# ---------- 端到端集成第四十九批


def test_e2e_full_pdf_doc_batch34():
    """完整 PDF doc → 全部指标有合理值。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]}},
            {"type": "paragraph", "content": "Hello", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Hello", "source_element_ids": ["e1"]},
        ],
    }
    exp = {"element_count_by_type": {"heading": 1, "paragraph": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_idempotent_batch34():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_does_not_mutate_input_batch34():
    import json
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "a", "element_id": "e1"}],
        "chunks": [{"text": "a", "source_element_ids": ["e1"]}],
    }
    doc_before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_e2e_full_docx_doc_batch34():
    """完整 DOCX doc → docx_locator_valid_ratio 计算。"""
    doc = {
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "x", "element_id": "e1",
             "source_locator": {"paragraph_index": 0, "section": 1}},
        ],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_failed_pipeline_all_null_batch34():
    """pipeline 失败 → 后续指标全是 pipeline_failed。"""
    out = compute_automatic_metrics(None, {"code": "E_PARSE"}, "pdf", None)
    for key in (
        "element_count_total",
        "pdf_locator_valid_ratio",
        "image_resource_exists_ratio",
        "chunk_reference_intact_ratio",
    ):
        assert out[key]["reason"] == "pipeline_failed"
