"""evaluation/metrics.py 第七十一轮 edges 测试（Round 596）。

补强 edges65 未触及的角度（第四十批）。
"""

from __future__ import annotations

import inspect
import json
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


# ---------- _null / _ratio / _bool_metric / _int_metric 第四十批


def test_null_with_none_reason_batch40():
    """None 作为 reason 也合法（不强制 str）。"""
    out = _null(None)  # type: ignore[arg-type]
    assert out["value"] is None
    assert out["reason"] is None


def test_null_with_int_reason_batch40():
    """int 作为 reason 也合法（不强校验类型）。"""
    out = _null(42)  # type: ignore[arg-type]
    assert out["reason"] == 42


def test_null_does_not_mutate_input_batch40():
    """_null 不接受可变输入（reason 是不可变 str/int）。"""
    out = _null("x")
    # 改 out 不影响其他
    out["extra"] = "x"
    out2 = _null("x")
    assert "extra" not in out2


def test_ratio_with_very_small_value_batch40():
    out = _ratio(1e-10)
    assert out["value"] == 1e-10


def test_ratio_with_very_large_value_batch40():
    out = _ratio(1e10)
    assert out["value"] == 1e10


def test_ratio_reason_always_none_batch40():
    """_ratio 总是 reason=None。"""
    out = _ratio(0.5)
    assert out["reason"] is None


def test_bool_metric_reason_always_none_batch40():
    out = _bool_metric(True)
    assert out["reason"] is None


def test_int_metric_reason_always_none_batch40():
    out = _int_metric(5)
    assert out["reason"] is None


def test_int_metric_with_negative_zero_batch40():
    """int(-0.0) == 0（int 截断）。"""
    out = _int_metric(-0.0)  # type: ignore[arg-type]
    assert out["value"] == 0


def test_int_metric_with_scientific_notation_string_batch40():
    """int('1e5') 会抛 ValueError（不接受科学记数法）。"""
    with pytest.raises(ValueError):
        _int_metric("1e5")  # type: ignore[arg-type]


def test_int_metric_with_hex_string_batch40():
    """int('0x10') 会抛 ValueError（需要 base=16）。"""
    with pytest.raises(ValueError):
        _int_metric("0x10")  # type: ignore[arg-type]


# ---------- _NOT_EVALUATED / _TEXT_TYPES / _PDF_BBOX_REQUIRED_TYPES 第四十批


def test_text_types_contains_list_item_batch40():
    assert "list_item" in _TEXT_TYPES


def test_text_types_contains_heading_batch40():
    assert "heading" in _TEXT_TYPES


def test_text_types_contains_paragraph_batch40():
    assert "paragraph" in _TEXT_TYPES


def test_pdf_bbox_required_types_exact_set_batch40():
    assert set(_PDF_BBOX_REQUIRED_TYPES) == {"heading", "paragraph", "caption", "list_item"}


def test_pdf_bbox_required_types_does_not_contain_header_batch40():
    """header 不需要 bbox（header/footer 是页眉页脚）。"""
    assert "header" not in _PDF_BBOX_REQUIRED_TYPES


def test_pdf_bbox_required_types_does_not_contain_footer_batch40():
    assert "footer" not in _PDF_BBOX_REQUIRED_TYPES


def test_text_types_seven_distinct_kinds_batch40():
    """heading, paragraph, list_item, table, caption, header, footer 共 7 种。"""
    expected = {"heading", "paragraph", "list_item", "table", "caption", "header", "footer"}
    assert set(_TEXT_TYPES) == expected


# ---------- _is_valid_bbox 第四十批


def test_is_valid_bbox_with_mixed_int_float_batch40():
    """int 和 float 混合也合法。"""
    assert _is_valid_bbox([0, 0.5, 1, 1.5]) is True


def test_is_valid_bbox_with_just_out_of_range_int_batch40():
    """极端 int 值也合法（不检查实际范围）。"""
    assert _is_valid_bbox([-(2**31), 0, 2**31 - 1, 100]) is True


def test_is_valid_bbox_with_list_of_lists_batch40():
    """嵌套 list 不合法（元素必须是数字）。"""
    assert _is_valid_bbox([[0, 0], [1, 1]]) is False


def test_is_valid_bbox_with_dict_inside_batch40():
    assert _is_valid_bbox([{"x": 0}, 0, 1, 1]) is False


def test_is_valid_bbox_with_bool_true_only_batch40():
    """[True, True, True, True] → 全是 bool → False。"""
    assert _is_valid_bbox([True, True, True, True]) is False


def test_is_valid_bbox_with_one_bool_batch40():
    """含一个 bool → False。"""
    assert _is_valid_bbox([True, 0, 1, 1]) is False


# ---------- _strip_unicode_whitespace 第四十批


def test_strip_whitespace_preserves_emoji_batch40():
    """emoji 不是 isspace。"""
    assert _strip_unicode_whitespace("😀 🎉") == "😀🎉"


def test_strip_whitespace_preserves_digits_and_punctuation_batch40():
    assert _strip_unicode_whitespace("1 + 2 = 3") == "1+2=3"


def test_strip_whitespace_preserves_chinese_punctuation_batch40():
    """中文标点不是 isspace。"""
    assert _strip_unicode_whitespace("你，好。") == "你，好。"


def test_strip_whitespace_with_long_text_batch40():
    text = "a" * 1000 + " " * 100 + "b" * 1000
    out = _strip_unicode_whitespace(text)
    assert out == "a" * 1000 + "b" * 1000


def test_strip_whitespace_returns_str_batch40():
    out = _strip_unicode_whitespace("x")
    assert isinstance(out, str)


# ---------- _pdf_locator_ratio 第四十批


def test_pdf_locator_with_string_page_batch40():
    elements = [{"type": "table", "source_locator": {"page": "1"}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_float_page_batch40():
    elements = [{"type": "table", "source_locator": {"page": 1.0}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_with_bool_true_page_batch40():
    """page=True → bool is int subclass, True == 1 → valid。"""
    elements = [{"type": "table", "source_locator": {"page": True}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 1.0


def test_pdf_locator_with_bool_false_page_batch40():
    """page=False == 0 → False < 1 → invalid。"""
    elements = [{"type": "table", "source_locator": {"page": False}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_negative_page_batch40():
    elements = [{"type": "table", "source_locator": {"page": -5}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_paragraph_no_bbox_invalid_batch40():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert m["value"] == 0.0


def test_pdf_locator_returns_dict_instance_batch40():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert isinstance(m, dict)


def test_pdf_locator_dict_has_value_reason_batch40():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    m = _pdf_locator_ratio(elements)
    assert "value" in m
    assert "reason" in m


def test_pdf_locator_does_not_mutate_elements_batch40():
    elements = [{"type": "table", "source_locator": {"page": 1}}]
    before = str(elements)
    _pdf_locator_ratio(elements)
    assert str(elements) == before


# ---------- _docx_locator_ratio 第四十批


def test_docx_locator_empty_elements_returns_null_batch40():
    m = _docx_locator_ratio([])
    assert m["value"] is None
    assert m["reason"] == "no_elements"


def test_docx_locator_all_invalid_returns_zero_batch40():
    elements = [{"type": "paragraph", "source_locator": {"unknown": "x"}}]
    m = _docx_locator_ratio(elements)
    assert m["value"] == 0.0


def test_docx_locator_does_not_mutate_input_batch40():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    before = str(elements)
    _docx_locator_ratio(elements)
    assert str(elements) == before


def test_docx_locator_dict_has_value_reason_batch40():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    m = _docx_locator_ratio(elements)
    assert "value" in m
    assert "reason" in m


# ---------- _image_resource_ratio 第四十批


def test_image_resource_callable_batch40():
    assert callable(_image_resource_ratio)


def test_image_resource_no_images_returns_null_batch40():
    m = _image_resource_ratio([{"type": "paragraph"}], None)
    assert m["value"] is None
    assert m["reason"] == "no_image_elements"


def test_image_resource_does_not_mutate_input_batch40():
    elements = [{"type": "image", "resource_path": "x.png"}]
    before = str(elements)
    _image_resource_ratio(elements, None)
    assert str(elements) == before


def test_image_resource_dict_has_value_reason_batch40(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"data")
    elements = [{"type": "image", "resource_path": str(img)}]
    m = _image_resource_ratio(elements, None)
    assert "value" in m
    assert "reason" in m


# ---------- _chunk_reference_ratio 第四十批


def test_chunk_reference_callable_batch40():
    assert callable(_chunk_reference_ratio)


def test_chunk_reference_does_not_mutate_inputs_batch40():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    e_before = str(elements)
    c_before = str(chunks)
    _chunk_reference_ratio(elements, chunks)
    assert str(elements) == e_before
    assert str(chunks) == c_before


def test_chunk_reference_dict_has_value_reason_batch40():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert "value" in m
    assert "reason" in m


def test_chunk_reference_value_zero_when_no_valid_chunks_batch40():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["unknown"]}]
    m = _chunk_reference_ratio(elements, chunks)
    assert m["value"] == 0.0


# ---------- _text_preservation 第四十批


def test_text_preservation_callable_batch40():
    assert callable(_text_preservation)


def test_text_preservation_does_not_mutate_inputs_batch40():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    e_before = str(elements)
    c_before = str(chunks)
    _text_preservation(elements, chunks)
    assert str(elements) == e_before
    assert str(chunks) == c_before


def test_text_preservation_with_image_only_batch40():
    elements = [{"type": "image", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    # image 排除 → expected empty, actual non-empty
    assert out["recall"]["reason"] == "empty_expected"


def test_text_preservation_returns_dict_with_three_keys_batch40():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_each_metric_dict_has_value_reason_batch40():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    for k, v in out.items():
        assert "value" in v
        assert "reason" in v


def test_text_preservation_precision_value_float_or_none_batch40():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    v = out["precision"]["value"]
    assert v is None or isinstance(v, float)


# ---------- _heading_boundary_ratio 第四十批


def test_heading_boundary_callable_batch40():
    assert callable(_heading_boundary_ratio)


def test_heading_boundary_returns_dict_batch40():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert isinstance(m, dict)


def test_heading_boundary_dict_has_value_reason_batch40():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert "value" in m
    assert "reason" in m


def test_heading_boundary_value_zero_when_no_match_batch40():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["unknown"]}]
    m = _heading_boundary_ratio(elements, chunks)
    assert m["value"] == 0.0


# ---------- _silent_drop_count 第四十批


def test_silent_drop_count_callable_batch40():
    assert callable(_silent_drop_count)


def test_silent_drop_count_returns_dict_batch40():
    m = _silent_drop_count({}, None)
    assert isinstance(m, dict)


def test_silent_drop_count_dict_has_value_reason_batch40():
    m = _silent_drop_count({"a": 1}, {"element_count_by_type": {"a": 5}})
    assert "value" in m
    assert "reason" in m


def test_silent_drop_count_value_zero_when_no_drop_batch40():
    m = _silent_drop_count({"a": 5}, {"element_count_by_type": {"a": 5}})
    assert m["value"] == 0


def test_silent_drop_count_does_not_mutate_input_batch40():
    by_type = {"a": 1}
    expectations = {"element_count_by_type": {"a": 5}}
    b_before = str(by_type)
    e_before = str(expectations)
    _silent_drop_count(by_type, expectations)
    assert str(by_type) == b_before
    assert str(expectations) == e_before


# ---------- compute_automatic_metrics 第四十批


def test_compute_metrics_minimal_doc_no_elements_no_chunks_batch40():
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["pipeline_success"]["value"] is True
    assert m["element_count_total"]["value"] == 0


def test_compute_metrics_with_image_element_batch40(tmp_path):
    """image 不参与 text_preservation。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "image", "element_id": "e1", "content": "ignored",
             "source_locator": {"page": 1}},
        ],
        "chunks": [],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    # image 排除 + chunks 空 → expected/actual 都空
    assert m["text_char_multiset_recall"]["reason"] == "empty_expected_and_actual"


def test_compute_metrics_with_mixed_elements_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "T", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
            {"type": "image", "element_id": "e2",
             "source_locator": {"page": 1}},
            {"type": "paragraph", "content": "P", "element_id": "e3",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [
            {"text": "TP", "source_element_ids": ["e1", "e3"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["element_count_total"]["value"] == 3
    assert m["pipeline_success"]["value"] is True


def test_compute_metrics_with_patched_document_passes_schema_true_batch40():
    """patch document_passes_schema 让 schema_valid=True。"""
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=True):
        m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["schema_valid"]["value"] is True


def test_compute_metrics_with_patched_document_passes_schema_false_batch40():
    doc = {"document_id": "d1", "source_type": "pdf", "elements": [], "chunks": []}
    with patch("evaluation.schema_validation.document_passes_schema", return_value=False):
        m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["schema_valid"]["value"] is False


def test_compute_metrics_idempotent_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_compute_metrics_with_expectations_no_drop_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "abc", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["silent_drop_count"]["value"] == 0


def test_compute_metrics_with_expectations_has_drop_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "paragraph", "content": "abc", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    expectations = {"element_count_by_type": {"paragraph": 5}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["silent_drop_count"]["value"] == 4


def test_compute_metrics_signature_five_params_batch40():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.keys())
    assert params == ["document", "error", "source_type", "expectations", "image_base_dir"]


def test_compute_metrics_image_base_dir_default_none_batch40():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_compute_metrics_doc_annotation_batch40():
    """document 参数 annotation 含 dict 和 None。"""
    sig = inspect.signature(compute_automatic_metrics)
    ann = str(sig.parameters["document"].annotation)
    assert "dict" in ann
    assert "None" in ann


def test_compute_metrics_error_annotation_batch40():
    sig = inspect.signature(compute_automatic_metrics)
    ann = str(sig.parameters["error"].annotation)
    assert "dict" in ann
    assert "None" in ann


def test_compute_metrics_source_type_annotation_str_batch40():
    sig = inspect.signature(compute_automatic_metrics)
    ann = str(sig.parameters["source_type"].annotation)
    assert "str" in ann


def test_compute_metrics_returns_dict_annotation_batch40():
    sig = inspect.signature(compute_automatic_metrics)
    assert "dict" in str(sig.return_annotation)


# ---------- module source forbidden tokens 第六十九批


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
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch40(token):
    src = inspect.getsource(mmod)
    assert token not in src


# ---------- module source 字符串精确补强第六十五批


def test_module_source_contains_text_types_definition_batch40():
    src = inspect.getsource(mmod)
    assert "_TEXT_TYPES = " in src


def test_module_source_contains_pdf_bbox_required_definition_batch40():
    src = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES = " in src


def test_module_source_contains_not_evaluated_definition_batch40():
    src = inspect.getsource(mmod)
    assert "_NOT_EVALUATED = " in src


def test_module_source_contains_silent_drop_count_helper_batch40():
    src = inspect.getsource(mmod)
    assert "def _silent_drop_count(" in src


def test_module_source_contains_heading_boundary_helper_batch40():
    src = inspect.getsource(mmod)
    assert "def _heading_boundary_ratio(" in src


def test_module_source_contains_normalize_text_v11_comment_batch40():
    """metrics.py 文档提到 normalize_text v1.0 历史口径（但代码不再 import）。"""
    src = inspect.getsource(mmod)
    assert "normalize_text" in src


def test_module_source_contains_strip_unicode_whitespace_definition_batch40():
    src = inspect.getsource(mmod)
    assert "def _strip_unicode_whitespace(" in src


def test_module_source_contains_counter_intersection_call_batch40():
    """precision/recall 用 Counter 交集。"""
    src = inspect.getsource(mmod)
    assert "c_expected & c_actual" in src


def test_module_source_contains_pure_function_comment_batch40():
    src = inspect.getsource(mmod)
    assert "纯函数" in src


def test_module_source_contains_silent_drop_count_formula_batch40():
    """silent_drop 公式在 docstring 或代码。"""
    src = inspect.getsource(mmod)
    assert "expected - actual" in src or "exp - actual" in src


def test_module_source_contains_no_image_in_text_types_comment_batch40():
    """注释解释 image 不参与 text。"""
    src = inspect.getsource(mmod)
    assert "image" in src.lower()


def test_module_source_contains_future_annotations_batch40():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_path_is_file_call_batch40():
    """image_resource 检查文件存在。"""
    src = inspect.getsource(mmod)
    assert "is_file()" in src or ".is_file()" in src


def test_module_source_contains_stat_st_size_call_batch40():
    """image_resource 检查 size > 0。"""
    src = inspect.getsource(mmod)
    assert "st_size" in src


def test_module_source_contains_oserror_handler_batch40():
    """image_resource 处理 OSError。"""
    src = inspect.getsource(mmod)
    assert "OSError" in src


def test_module_source_contains_not_evaluated_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "not_evaluated" in src


def test_module_source_contains_no_elements_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "no_elements" in src


def test_module_source_contains_no_chunks_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "no_chunks" in src


def test_module_source_contains_pipeline_failed_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "pipeline_failed" in src


def test_module_source_contains_empty_expected_and_actual_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "empty_expected_and_actual" in src


def test_module_source_contains_empty_actual_keyword_batch40():
    src = inspect.getsource(mmod)
    assert "empty_actual" in src


# ---------- signatures 第六十五批


def test_signature_null_one_param_batch40():
    sig = inspect.signature(_null)
    assert list(sig.parameters.keys()) == ["reason"]


def test_signature_null_return_dict_batch40():
    sig = inspect.signature(_null)
    assert "dict" in str(sig.return_annotation)


def test_signature_ratio_return_dict_batch40():
    sig = inspect.signature(_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_int_metric_one_param_batch40():
    sig = inspect.signature(_int_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_bool_metric_one_param_batch40():
    sig = inspect.signature(_bool_metric)
    assert list(sig.parameters.keys()) == ["value"]


def test_signature_strip_unicode_whitespace_one_param_batch40():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert list(sig.parameters.keys()) == ["s"]


def test_signature_strip_unicode_whitespace_return_str_batch40():
    sig = inspect.signature(_strip_unicode_whitespace)
    assert "str" in str(sig.return_annotation)


def test_signature_is_valid_bbox_one_param_batch40():
    sig = inspect.signature(_is_valid_bbox)
    assert list(sig.parameters.keys()) == ["bbox"]


def test_signature_is_valid_bbox_return_bool_batch40():
    sig = inspect.signature(_is_valid_bbox)
    assert "bool" in str(sig.return_annotation)


def test_signature_pdf_locator_return_dict_batch40():
    sig = inspect.signature(_pdf_locator_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_docx_locator_return_dict_batch40():
    sig = inspect.signature(_docx_locator_ratio)
    assert "dict" in str(sig.return_annotation)


def test_signature_image_resource_two_params_batch40():
    sig = inspect.signature(_image_resource_ratio)
    assert list(sig.parameters.keys()) == ["elements", "image_base_dir"]


def test_signature_chunk_reference_two_params_batch40():
    sig = inspect.signature(_chunk_reference_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


def test_signature_heading_boundary_two_params_batch40():
    sig = inspect.signature(_heading_boundary_ratio)
    assert list(sig.parameters.keys()) == ["elements", "chunks"]


# ---------- module 合理性 第六十五批


def test_module_has_all_attribute_batch40():
    assert hasattr(mmod, "__all__")


def test_module_all_is_list_batch40():
    assert isinstance(mmod.__all__, list)


def test_module_all_only_compute_automatic_metrics_batch40():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_does_not_define_class_batch40():
    src = inspect.getsource(mmod)
    assert "\nclass " not in src


def test_module_top_level_no_side_effect_code_batch40():
    """顶层无 print / 非 __all__ / 非常量赋值。"""
    import ast
    src = inspect.getsource(mmod)
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef,
                             ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assert target.id.startswith("_") or target.id == "__all__", \
                        f"unexpected assignment: {target.id}"
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        pytest.fail(f"unexpected top-level node: {type(node).__name__}")


def test_module_has_future_annotations_batch40():
    src = inspect.getsource(mmod)
    assert "from __future__ import annotations" in src


def test_module_has_text_types_attribute_batch40():
    assert hasattr(mmod, "_TEXT_TYPES")


def test_module_has_pdf_bbox_required_types_attribute_batch40():
    assert hasattr(mmod, "_PDF_BBOX_REQUIRED_TYPES")


def test_module_has_not_evaluated_attribute_batch40():
    assert hasattr(mmod, "_NOT_EVALUATED")


def test_module_normalize_text_not_imported_batch40():
    src = inspect.getsource(mmod)
    assert "import normalize_text" not in src
    assert "from app.chunkers" not in src


# ---------- 端到端集成 第六十五批


def test_e2e_compute_metrics_with_unicode_text_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "你好世界", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "你好世界", "source_element_ids": ["e1"]}],
    }
    m = compute_automatic_metrics(doc, None, "pdf", None)
    assert m["text_preservation_equal"]["value"] is True


def test_e2e_compute_metrics_with_pdf_only_batch40(tmp_path):
    """全 PDF elements + chunks + expectations 完整。"""
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [
            {"type": "heading", "content": "T", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
            {"type": "paragraph", "content": "P", "element_id": "e2",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
            {"type": "list_item", "content": "L", "element_id": "e3",
             "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}},
        ],
        "chunks": [
            {"text": "TPL", "source_element_ids": ["e1", "e2", "e3"]},
        ],
    }
    expectations = {"element_count_by_type": {"heading": 1, "paragraph": 1, "list_item": 1}}
    m = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert m["pdf_locator_valid_ratio"]["value"] == 1.0
    assert m["chunk_reference_intact_ratio"]["value"] == 1.0
    assert m["heading_boundary_compliance"]["value"] == 1.0
    assert m["silent_drop_count"]["value"] == 0


def test_e2e_compute_metrics_docx_full_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "docx",
        "elements": [
            {"type": "paragraph", "content": "P", "element_id": "e1",
             "source_locator": {"paragraph_index": 0}},
            {"type": "table", "content": "T", "element_id": "e2",
             "source_locator": {"table_index": 0}},
        ],
        "chunks": [
            {"text": "PT", "source_element_ids": ["e1", "e2"]},
        ],
    }
    m = compute_automatic_metrics(doc, None, "docx", None)
    assert m["docx_locator_valid_ratio"]["value"] == 1.0
    assert m["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_e2e_compute_metrics_idempotent_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    m1 = compute_automatic_metrics(doc, None, "pdf", None)
    m2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert m1 == m2


def test_e2e_compute_metrics_does_not_mutate_doc_batch40():
    doc = {
        "document_id": "d1",
        "source_type": "pdf",
        "elements": [{"type": "paragraph", "content": "abc", "element_id": "e1",
                      "source_locator": {"page": 1, "bbox": [0, 0, 1, 1]}}],
        "chunks": [{"text": "abc", "source_element_ids": ["e1"]}],
    }
    before = json.dumps(doc, sort_keys=True)
    compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == before
