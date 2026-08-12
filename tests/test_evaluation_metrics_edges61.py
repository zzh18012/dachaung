"""evaluation/metrics.py 第六十二轮 edges 测试（Round 560）。

补强 edges60 未触及的角度（第三十五批）。
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第三十五批


def test_null_with_unicode_reason_batch35():
    m = _null("中文原因")
    assert m["value"] is None
    assert m["reason"] == "中文原因"


def test_null_with_long_reason_batch35():
    long_reason = "x" * 200
    m = _null(long_reason)
    assert m["reason"] == long_reason


def test_ratio_negative_batch35():
    """_ratio 接受负数（不强制 0..1）。"""
    m = _ratio(-0.5)
    assert m["value"] == -0.5


def test_ratio_huge_value_batch35():
    m = _ratio(1e10)
    assert m["value"] == 1e10


def test_ratio_int_zero_batch35():
    m = _ratio(0)
    assert m["value"] == 0.0
    assert isinstance(m["value"], float)


def test_bool_metric_with_string_batch35():
    """truthy str → True。"""
    m = _bool_metric("hello")
    assert m["value"] is True


def test_bool_metric_with_empty_string_batch35():
    m = _bool_metric("")
    assert m["value"] is False


def test_int_metric_with_bool_batch35():
    """int(True) = 1, int(False) = 0。"""
    assert _int_metric(True)["value"] == 1
    assert _int_metric(False)["value"] == 0


def test_int_metric_with_float_negative_batch35():
    m = _int_metric(-3.7)
    assert m["value"] == -3


# ---------- _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES / _NOT_EVALUATED 第三十五批


def test_text_types_tuple_immutable_batch35():
    """tuple 是不可变的。"""
    with pytest.raises(TypeError):
        # type: ignore
        _TEXT_TYPES[0] = "x"  # type: ignore


def test_pdf_bbox_required_tuple_immutable_batch35():
    with pytest.raises(TypeError):
        # type: ignore
        _PDF_BBOX_REQUIRED_TYPES[0] = "x"  # type: ignore


def test_text_types_caption_in_pdf_bbox_batch35():
    """caption 同时在 _TEXT_TYPES 和 _PDF_BBOX_REQUIRED_TYPES。"""
    assert "caption" in _TEXT_TYPES
    assert "caption" in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_table_included_batch35():
    assert "table" in _TEXT_TYPES


def test_text_types_header_footer_included_batch35():
    assert "header" in _TEXT_TYPES
    assert "footer" in _TEXT_TYPES


def test_pdf_bbox_required_types_no_table_batch35():
    """table 不在 _PDF_BBOX_REQUIRED_TYPES（table 用 cell bbox）。"""
    assert "table" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_no_header_footer_batch35():
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_not_evaluated_value_const_batch35():
    """_NOT_EVALUATED 是字符串字面量。"""
    assert _NOT_EVALUATED == "not_evaluated"


# ---------- compute_automatic_metrics 第三十五批


def test_compute_no_doc_no_error_no_source_type_batch35():
    out = compute_automatic_metrics(None, None, "unknown", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_with_image_base_dir_none_batch35(tmp_path):
    """image_base_dir=None → 直接用 resource_path。"""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "image", "resource_path": str(img)}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=None)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_with_image_base_dir_batch35(tmp_path):
    sub = tmp_path / "imgs"
    sub.mkdir()
    img = sub / "x.png"
    img.write_bytes(b"\x89PNG")
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "image", "resource_path": "x.png"}],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None, image_base_dir=sub)
    assert out["image_resource_exists_ratio"]["value"] == 1.0


def test_compute_docx_source_type_batch35():
    doc = {
        "source_type": "docx",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1",
                      "source_locator": {"paragraph_index": 0}}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_with_error_code_only_batch35():
    """error dict 只含 code 字段也接受。"""
    out = compute_automatic_metrics(None, {"code": "E_X"}, "pdf", None)
    assert out["error_code"]["value"] == "E_X"


def test_compute_error_no_code_batch35():
    """error dict 没有 code 字段 → KeyError（不静默吞错）。"""
    with pytest.raises(KeyError):
        compute_automatic_metrics(None, {"message": "broken"}, "pdf", None)


# ---------- _pdf_locator_ratio 第三十五批


def test_pdf_locator_list_item_requires_bbox_batch35():
    elements = [{"type": "list_item", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_list_item_with_bbox_batch35():
    elements = [{"type": "list_item", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_caption_requires_bbox_batch35():
    elements = [{"type": "caption", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_caption_with_bbox_batch35():
    elements = [{"type": "caption", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_negative_page_batch35():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_float_batch35():
    """page 是 float 而不是 int → 视为 invalid。"""
    elements = [{"type": "image", "source_locator": {"page": 1.5}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_string_batch35():
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_no_source_locator_batch35():
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _docx_locator_ratio 第三十五批


def test_docx_locator_with_bbox_invalid_batch35():
    """DOCX 不能含 bbox。"""
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 10, 10]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_relationship_id_batch35():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_run_index_batch35():
    elements = [{"type": "paragraph", "source_locator": {"run_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_row_col_batch35():
    elements = [{"type": "table_cell", "source_locator": {"row_index": 0, "col_index": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_empty_locator_batch35():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_no_locator_batch35():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_page_and_paragraph_batch35():
    """既含 page 又含 paragraph_index → page 触发不合规。"""
    elements = [{"type": "paragraph", "source_locator": {"page": 1, "paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- _is_valid_bbox 第三十五批


def test_is_valid_bbox_negative_numbers_batch35():
    assert _is_valid_bbox([-1, -2, 10, 10]) is True


def test_is_valid_bbox_very_large_batch35():
    assert _is_valid_bbox([1e10, 1e10, 2e10, 2e10]) is True


def test_is_valid_bbox_mixed_int_float_batch35():
    assert _is_valid_bbox([0, 0.5, 10, 10.5]) is True


def test_is_valid_bbox_list_with_none_batch35():
    assert _is_valid_bbox([0, 0, None, 10]) is False


def test_is_valid_bbox_zero_zero_zero_zero_batch35():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


# ---------- _image_resource_ratio 第三十五批


def test_image_ratio_resource_path_empty_string_batch35():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_none_batch35():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_resource_path_dir_batch35(tmp_path):
    """resource_path 指向目录 → is_file False → 0.0。"""
    elements = [{"type": "image", "resource_path": str(tmp_path)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_ratio_two_images_one_missing_batch35(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [
        {"type": "image", "resource_path": str(img)},
        {"type": "image", "resource_path": str(tmp_path / "missing.png")},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


# ---------- _chunk_reference_ratio 第三十五批


def test_chunk_ref_chunk_no_ids_field_batch35():
    elements = [{"element_id": "e1"}]
    chunks = [{"text": "abc"}]  # no source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_chunk_ids_empty_list_batch35():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_elements_empty_ids_valid_batch35():
    """elements 为空，chunk 引用任何 id 都不合规。"""
    elements = []
    chunks = [{"source_element_ids": ["e1"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_chunk_ref_all_chunks_valid_batch35():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [
        {"source_element_ids": ["e1"]},
        {"source_element_ids": ["e2"]},
    ]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


# ---------- _strip_unicode_whitespace 第三十五批


def test_strip_unicode_line_separator_batch35():
    """U+2028 LINE SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_paragraph_separator_batch35():
    """U+2029 PARAGRAPH SEPARATOR。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_vertical_tab_batch35():
    assert _strip_unicode_whitespace("a\x0bb") == "ab"


def test_strip_unicode_form_feed_batch35():
    assert _strip_unicode_whitespace("a\x0cb") == "ab"


def test_strip_unicode_carriage_return_batch35():
    assert _strip_unicode_whitespace("a\rb") == "ab"


def test_strip_unicode_only_digits_batch35():
    assert _strip_unicode_whitespace("12345") == "12345"


def test_strip_unicode_special_chars_batch35():
    assert _strip_unicode_whitespace("!@#$%") == "!@#$%"


def test_strip_unicode_chinese_batch35():
    """中文字符不算空白。"""
    assert _strip_unicode_whitespace("中文 测试") == "中文测试"


# ---------- _text_preservation 第三十五批


def test_text_preservation_image_only_batch35():
    """只有 image element → expected 为空。"""
    elements = [{"type": "image", "content": None}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected empty, actual non-empty → recall=empty_expected
    assert out["recall"]["reason"] == "empty_expected"
    # actual 有内容 → precision 不是 null
    assert out["precision"]["value"] is not None


def test_text_preservation_text_only_with_empty_chunks_batch35():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = []
    out = _text_preservation(elements, chunks)
    # actual empty → precision=empty_actual
    assert out["precision"]["reason"] == "empty_actual"


def test_text_preservation_unicode_batch35():
    elements = [{"type": "paragraph", "content": "中文内容"}]
    chunks = [{"text": "中文内容"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0


def test_text_preservation_chunk_only_batch35():
    """chunk 有内容但 element 没有 → precision=0.0（common=0），recall=empty_expected。"""
    elements = []
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # expected empty → common=0, precision = 0/3 = 0.0
    assert out["precision"]["value"] == 0.0
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_content_none_batch35():
    """element content=None 视为 ""。"""
    elements = [{"type": "paragraph", "content": None}]
    chunks = [{"text": ""}]
    out = _text_preservation(elements, chunks)
    # 都空 → empty_expected_and_actual
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


# ---------- _heading_boundary_ratio 第三十五批


def test_heading_boundary_multiple_chunks_match_batch35():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [
        {"source_element_ids": ["h1"]},
        {"source_element_ids": ["h2"]},
    ]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_only_non_heading_elements_batch35():
    elements = [{"type": "paragraph", "element_id": "p1"}]
    out = _heading_boundary_ratio(elements, [])
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_chunks_no_ids_batch35():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"text": "abc"}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_chunks_empty_ids_batch35():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": []}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


# ---------- _silent_drop_count 第三十五批


def test_silent_drop_with_other_keys_in_expectations_batch35():
    """expectations 含其他无关 key 也不影响。"""
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 5}, "other_key": "value"},
    )
    assert out["value"] == 0


def test_silent_drop_actual_exceeds_expected_batch35():
    out = _silent_drop_count(
        {"paragraph": 100},
        {"element_count_by_type": {"paragraph": 1}},
    )
    assert out["value"] == 0


def test_silent_drop_expected_zero_batch35():
    out = _silent_drop_count(
        {"paragraph": 5},
        {"element_count_by_type": {"paragraph": 0}},
    )
    assert out["value"] == 0


def test_silent_drop_multi_type_partial_drop_batch35():
    out = _silent_drop_count(
        {"paragraph": 1, "heading": 2, "list_item": 3},
        {"element_count_by_type": {"paragraph": 5, "heading": 2, "list_item": 1}},
    )
    # paragraph: 5-1=4, heading: 0, list_item: 0 (实际 3 > 期望 1)
    assert out["value"] == 4


def test_silent_drop_returns_int_metric_batch35():
    out = _silent_drop_count({"a": 1}, {"element_count_by_type": {"a": 5}})
    assert out["reason"] is None
    assert isinstance(out["value"], int)


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
    "pty.",
    "ctypes",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第四十九批


def test_module_source_contains_docstring_batch35():
    src = inspect.getsource(mmod)
    assert "自动指标" in src


def test_module_source_contains_future_annotations_batch35():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_counter_import_batch35():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_source_contains_math_import_batch35():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_source_contains_text_types_definition_batch35():
    src = inspect.getsource(mmod)
    assert '_TEXT_TYPES = ("heading"' in src


def test_module_source_contains_pdf_bbox_definition_batch35():
    src = inspect.getsource(mmod)
    assert '_PDF_BBOX_REQUIRED_TYPES = ("heading"' in src


def test_module_source_contains_not_evaluated_definition_batch35():
    src = inspect.getsource(mmod)
    assert '_NOT_EVALUATED = "not_evaluated"' in src


def test_module_source_contains_all_only_compute_batch35():
    """__all__ 只导出 compute_automatic_metrics（私有 helper 不导出）。"""
    src = inspect.getsource(mmod)
    assert '__all__ = ["compute_automatic_metrics"]' in src


# ---------- signatures 第四十九批


def test_signature_null_returns_dict_batch35():
    sig = inspect.signature(_null)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_ratio_returns_dict_batch35():
    sig = inspect.signature(_ratio)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_bool_metric_returns_dict_batch35():
    sig = inspect.signature(_bool_metric)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_int_metric_returns_dict_batch35():
    sig = inspect.signature(_int_metric)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_strip_unicode_returns_str_batch35():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert sig.return_annotation == "str"


def test_signature_is_valid_bbox_returns_bool_batch35():
    sig = inspect.signature(_is_valid_bbox)
    assert sig.return_annotation == "bool"


def test_signature_pdf_locator_returns_dict_batch35():
    sig = inspect.signature(_pdf_locator_ratio)
    assert sig.return_annotation == "dict[str, Any]"


# ---------- module 合理性第四十九批


def test_module_imports_math_batch35():
    src = inspect.getsource(mmod)
    assert "import math" in src


def test_module_imports_counter_batch35():
    src = inspect.getsource(mmod)
    assert "from collections import Counter" in src


def test_module_imports_pathlib_batch35():
    src = inspect.getsource(mmod)
    assert "from pathlib import Path" in src


def test_module_has_text_types_batch35():
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_has_pdf_bbox_required_batch35():
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_has_compute_automatic_metrics_batch35():
    assert callable(mmod.compute_automatic_metrics)


def test_module_has_all_only_compute_batch35():
    assert mmod.__all__ == ["compute_automatic_metrics"]


# ---------- 端到端集成第四十九批


def test_e2e_complete_doc_with_all_metrics_batch35():
    """完整 doc + expectations → 全部指标有合理值。"""
    doc = {
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "Title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 30]}},
            {"type": "paragraph", "content": "Hello world", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 50]}},
            {"type": "list_item", "content": "item", "element_id": "l1",
             "source_locator": {"page": 1, "bbox": [0, 0, 100, 20]}},
        ],
        "chunks": [
            {"text": "Title", "source_element_ids": ["h1"]},
            {"text": "Hello world", "source_element_ids": ["e1"]},
            {"text": "item", "source_element_ids": ["l1"]},
        ],
    }
    exp = {"element_count_by_type": {"heading": 1, "paragraph": 1, "list_item": 1}}
    out = compute_automatic_metrics(doc, None, "pdf", exp)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 3
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0
    assert out["text_preservation_equal"]["value"] is True
    assert out["heading_boundary_compliance"]["value"] == 1.0
    assert out["silent_drop_count"]["value"] == 0


def test_e2e_idempotent_batch35():
    doc = {"source_type": "pdf", "elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_does_not_mutate_doc_batch35():
    import json
    doc = {
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "x", "element_id": "e1"}],
        "chunks": [{"text": "x", "source_element_ids": ["e1"]}],
    }
    doc_before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == doc_before


def test_e2e_failed_pipeline_returns_correct_metrics_batch35():
    """pipeline 失败 → 14 个 metrics，其中 11 个是 pipeline_failed null。"""
    out = compute_automatic_metrics(None, {"code": "E_PARSE"}, "pdf", None)
    null_metrics = [
        k for k, v in out.items() if v.get("reason") == "pipeline_failed"
    ]
    assert len(null_metrics) >= 11
