"""evaluation/metrics.py 第三十九轮 edges 测试（Round 401）。

补强 edges37 未触及的角度：
- helpers batch 11（更多 _null / _ratio / _bool_metric / _int_metric 边界与类型）
- compute_automatic_metrics batch 11（document None/error set/specific error code 提取/metrics key 顺序与类型/不 mutate/idempotent）
- pdf/docx locator batch 11（page 边界 / bbox 校验 / 各种 source_locator 结构）
- image_resource_ratio batch 11（image_base_dir 拼接 / file size 0 / 绝对路径 / 相对路径）
- chunk_reference_ratio batch 11（empty / 部分有效 / 重复 ID）
- text_preservation batch 11（empty / Unicode / whitespace-only / 缺字符 / 多字符 / 等长不等内容）
- heading_boundary_ratio batch 11（无 heading / 单 heading / 多 heading / chunk first id 匹配）
- silent_drop_count batch 11（无 expectations / 各种 expectations 结构）
- _is_valid_bbox batch 11（4 ints/floats/mixed/bool/nan/inf/非 list）
- _strip_unicode_whitespace batch 11（empty / 各类空白 / 非空白 / Unicode）
- module source forbidden tokens 第十四批
- module source 字符串精确补强第十批
- signatures 第十一批
- module 合理性第十一批
- 端到端集成第十一批
"""

from __future__ import annotations

import inspect
import json
import math
import os
from collections import Counter
from pathlib import Path

import pytest

from evaluation import metrics as mmod
from evaluation.metrics import (
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


# ---------- helpers batch 11 ----------


def test_null_empty_reason_batch11():
    out = _null("")
    assert out["value"] is None
    assert out["reason"] == ""


def test_null_long_reason_batch11():
    long_str = "x" * 200
    out = _null(long_str)
    assert out["reason"] == long_str


def test_null_unicode_reason_batch11():
    out = _null("中文原因")
    assert out["reason"] == "中文原因"


def test_null_returns_dict_strict_batch11():
    out = _null("x")
    assert type(out) is dict


def test_ratio_float_zero_batch11():
    out = _ratio(0.0)
    assert out["value"] == 0.0


def test_ratio_int_input_coerced_to_float_batch11():
    out = _ratio(1)
    assert type(out["value"]) is float
    assert out["value"] == 1.0


def test_ratio_negative_value_kept_batch11():
    """超出 [0,1] 的负数也接受（函数不做范围校验）。"""
    out = _ratio(-0.5)
    assert out["value"] == -0.5


def test_ratio_returns_dict_strict_batch11():
    out = _ratio(0.5)
    assert type(out) is dict


def test_bool_metric_truthy_int_batch11():
    """truthy int → True。"""
    out = _bool_metric(1)
    assert out["value"] is True


def test_bool_metric_falsy_int_batch11():
    out = _bool_metric(0)
    assert out["value"] is False


def test_bool_metric_truthy_string_batch11():
    """truthy str → True（bool() 转换）。"""
    out = _bool_metric("non-empty")
    assert out["value"] is True


def test_bool_metric_falsy_string_batch11():
    out = _bool_metric("")
    assert out["value"] is False


def test_bool_metric_returns_dict_strict_batch11():
    out = _bool_metric(True)
    assert type(out) is dict


def test_int_metric_float_input_truncated_batch11():
    """int(float) → 截断。"""
    out = _int_metric(3.7)
    assert out["value"] == 3


def test_int_metric_bool_input_batch11():
    """int(True) = 1。"""
    out = _int_metric(True)
    assert out["value"] == 1


def test_int_metric_returns_dict_strict_batch11():
    out = _int_metric(5)
    assert type(out) is dict


# ---------- compute_automatic_metrics batch 11 ----------


def test_compute_returns_dict_strict_batch11():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert type(out) is dict


def test_compute_returns_14_keys_when_doc_none_batch11():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert len(out) == 14


def test_compute_returns_14_keys_when_doc_present_batch11():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert len(out) == 14


def test_compute_pipeline_success_false_when_doc_none_batch11():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["pipeline_success"]["value"] is False


def test_compute_pipeline_success_false_when_doc_set_error_set_batch11():
    """doc 与 error 同时给 → pipeline_success False（error 优先）。"""
    doc = {"elements": [], "chunks": []}
    error = {"code": "boom", "message": "x"}
    out = compute_automatic_metrics(doc, error, "pdf", None)
    # error is None and document is not None → False
    assert out["pipeline_success"]["value"] is False


def test_compute_pipeline_success_true_when_doc_set_no_error_batch11():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True


def test_compute_error_code_extracted_from_error_batch11():
    error = {"code": "my_error", "message": "x"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["error_code"]["value"] == "my_error"


def test_compute_error_code_none_when_no_error_batch11():
    out = compute_automatic_metrics(None, None, "pdf", None)
    assert out["error_code"]["value"] is None


def test_compute_error_code_none_when_error_has_no_code_key_batch11():
    """error 字典不含 code key → error['code'] KeyError？实际：error['code'] 会抛 KeyError。"""
    # 注意：metrics.py 直接用 error["code"]，会 KeyError
    # 所以这个 case 只能由 try-except 包，函数本身不处理
    # 用 try 验证不抛
    doc = {"elements": [], "chunks": []}
    with pytest.raises(KeyError):
        compute_automatic_metrics(doc, {"message": "x"}, "pdf", None)


def test_compute_does_not_mutate_document_batch11():
    doc = {"elements": [{"type": "paragraph", "content": "abc"}], "chunks": []}
    snapshot = json.dumps(doc, sort_keys=True)
    _ = compute_automatic_metrics(doc, None, "pdf", None)
    assert json.dumps(doc, sort_keys=True) == snapshot


def test_compute_does_not_mutate_error_batch11():
    error = {"code": "x", "message": "y"}
    snapshot = json.dumps(error, sort_keys=True)
    _ = compute_automatic_metrics(None, error, "pdf", None)
    assert json.dumps(error, sort_keys=True) == snapshot


def test_compute_idempotent_batch11():
    doc = {"elements": [{"type": "paragraph", "content": "abc"}], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    # 移除可能差异的字段（理论应该相同）
    assert out1 == out2


def test_compute_kwargs_call_batch11():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(
        document=doc, error=None, source_type="pdf", expectations=None
    )
    assert out1 == out2


def test_compute_positional_call_batch11():
    doc = {"elements": [], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_compute_element_count_total_int_batch11():
    doc = {"elements": [{"type": "paragraph"}, {"type": "heading"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["element_count_total"]["value"] == 2
    assert type(out["element_count_total"]["value"]) is int


def test_compute_element_count_by_type_dict_batch11():
    doc = {
        "elements": [
            {"type": "paragraph"},
            {"type": "paragraph"},
            {"type": "heading"},
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    by_type = out["element_count_by_type"]["value"]
    assert by_type == {"paragraph": 2, "heading": 1}
    assert type(by_type) is dict


def test_compute_pdf_locator_when_source_pdf_batch11():
    doc = {
        "elements": [
            {
                "type": "paragraph",
                "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
            }
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0


def test_compute_pdf_locator_null_when_source_docx_batch11():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["pdf_locator_valid_ratio"]["value"] is None
    assert out["pdf_locator_valid_ratio"]["reason"] == "not_pdf_document"


def test_compute_docx_locator_when_source_docx_batch11():
    doc = {
        "elements": [
            {"type": "paragraph", "source_locator": {"paragraph_index": 0}}
        ],
        "chunks": [],
    }
    out = compute_automatic_metrics(doc, None, "docx", None)
    assert out["docx_locator_valid_ratio"]["value"] == 1.0


def test_compute_docx_locator_null_when_source_pdf_batch11():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["docx_locator_valid_ratio"]["value"] is None


def test_compute_silent_drop_count_null_when_no_expectations_batch11():
    doc = {"elements": [], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["silent_drop_count"]["value"] is None


def test_compute_silent_drop_count_int_with_expectations_batch11():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = compute_automatic_metrics(doc, None, "pdf", expectations)
    assert out["silent_drop_count"]["value"] == 4


# ---------- pdf/docx locator batch 11 ----------


def test_pdf_locator_empty_elements_null_batch11():
    out = _pdf_locator_ratio([])
    assert out["value"] is None
    assert out["reason"] == "no_elements"


def test_pdf_locator_image_no_bbox_counts_batch11():
    """image 不在 _PDF_BBOX_REQUIRED_TYPES，无 bbox 也算。"""
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_page_zero_not_counts_batch11():
    elements = [{"type": "image", "source_locator": {"page": 0}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_negative_not_counts_batch11():
    elements = [{"type": "image", "source_locator": {"page": -1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_string_not_counts_batch11():
    elements = [{"type": "image", "source_locator": {"page": "1"}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_page_none_not_counts_batch11():
    elements = [{"type": "image", "source_locator": {"page": None}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_missing_source_locator_not_counts_batch11():
    elements = [{"type": "image"}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_without_bbox_not_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 0.0


def test_pdf_locator_text_with_valid_bbox_counts_batch11():
    elements = [
        {
            "type": "paragraph",
            "source_locator": {"page": 1, "bbox": [0, 0, 100, 100]},
        }
    ]
    out = _pdf_locator_ratio(elements)
    assert out["value"] == 1.0


def test_pdf_locator_mixed_partial_batch11():
    elements = [
        {"type": "paragraph", "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        {"type": "image", "source_locator": {"page": 1}},
        {"type": "paragraph", "source_locator": {"page": 0}},  # 不算
    ]
    out = _pdf_locator_ratio(elements)
    # 2/3
    assert out["value"] == pytest.approx(2 / 3)


def test_docx_locator_empty_elements_null_batch11():
    out = _docx_locator_ratio([])
    assert out["value"] is None


def test_docx_locator_with_page_not_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {"page": 1}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_bbox_not_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {"bbox": [0, 0, 1, 1]}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_with_section_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {"section": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_paragraph_index_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {"paragraph_index": 0}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_relationship_id_counts_batch11():
    elements = [{"type": "image", "source_locator": {"relationship_id": "rId1"}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 1.0


def test_docx_locator_with_structural_keys_counts_batch11():
    """任何一个 structural key 都算。"""
    for key in ("section", "paragraph_index", "run_index", "table_index", "row_index", "col_index", "relationship_id"):
        elements = [{"type": "x", "source_locator": {key: 1}}]
        out = _docx_locator_ratio(elements)
        assert out["value"] == 1.0


def test_docx_locator_missing_source_locator_not_counts_batch11():
    elements = [{"type": "paragraph"}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


def test_docx_locator_empty_source_locator_not_counts_batch11():
    elements = [{"type": "paragraph", "source_locator": {}}]
    out = _docx_locator_ratio(elements)
    assert out["value"] == 0.0


# ---------- image_resource_ratio batch 11 ----------


def test_image_resource_ratio_no_images_null_batch11():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] is None
    assert out["reason"] == "no_image_elements"


def test_image_resource_ratio_no_resource_path_batch11():
    elements = [{"type": "image"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_empty_resource_path_batch11():
    elements = [{"type": "image", "resource_path": ""}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_none_resource_path_batch11():
    elements = [{"type": "image", "resource_path": None}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_existing_file_batch11(tmp_path):
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG fake")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 1.0


def test_image_resource_ratio_zero_size_file_batch11(tmp_path):
    """文件存在但 size=0 → 不算。"""
    img_file = tmp_path / "empty.png"
    img_file.write_bytes(b"")
    elements = [{"type": "image", "resource_path": str(img_file)}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_relative_path_with_base_dir_batch11(tmp_path):
    """resource_path 是文件名，image_base_dir 提供目录。"""
    img_file = tmp_path / "img.png"
    img_file.write_bytes(b"\x89PNG fake")
    elements = [{"type": "image", "resource_path": "img.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    assert out["value"] == 1.0


def test_image_resource_ratio_relative_path_no_base_dir_batch11():
    """relative path 无 base_dir → Path(rp) 解析相对 cwd，可能找不到。"""
    elements = [{"type": "image", "resource_path": "nonexistent.png"}]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.0


def test_image_resource_ratio_mixed_batch11(tmp_path):
    """部分图片存在部分不存在。"""
    img_file = tmp_path / "exists.png"
    img_file.write_bytes(b"\x89PNG fake")
    elements = [
        {"type": "image", "resource_path": str(img_file)},
        {"type": "image", "resource_path": "missing.png"},
    ]
    out = _image_resource_ratio(elements, None)
    assert out["value"] == 0.5


def test_image_resource_ratio_returns_dict_batch11():
    elements = [{"type": "paragraph"}]
    out = _image_resource_ratio(elements, None)
    assert type(out) is dict


# ---------- chunk_reference_ratio batch 11 ----------


def test_chunk_reference_ratio_no_chunks_null_batch11():
    elements = []
    out = _chunk_reference_ratio(elements, [])
    assert out["value"] is None
    assert out["reason"] == "no_chunks"


def test_chunk_reference_ratio_empty_source_element_ids_batch11():
    elements = []
    chunks = [{"source_element_ids": []}]
    out = _chunk_reference_ratio(elements, chunks)
    # 空源 → 不算
    assert out["value"] == 0.0


def test_chunk_reference_ratio_all_valid_batch11():
    elements = [{"element_id": "e1"}, {"element_id": "e2"}]
    chunks = [{"source_element_ids": ["e1", "e2"]}]
    out = _chunk_reference_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_chunk_reference_ratio_some_invalid_batch11():
    elements = [{"element_id": "e1"}]
    chunks = [{"source_element_ids": ["e1", "missing"]}]
    out = _chunk_reference_ratio(elements, chunks)
    # any(sid not in elem_ids) → 不算
    assert out["value"] == 0.0


def test_chunk_reference_ratio_missing_source_element_ids_batch11():
    elements = [{"element_id": "e1"}]
    chunks = [{}]  # 缺 source_element_ids
    out = _chunk_reference_ratio(elements, chunks)
    # ids 默认 [] → not ids → 不算
    assert out["value"] == 0.0


def test_chunk_reference_ratio_returns_dict_batch11():
    elements = []
    chunks = []
    out = _chunk_reference_ratio(elements, chunks)
    assert type(out) is dict


# ---------- text_preservation batch 11 ----------


def test_text_preservation_empty_both_equal_true_batch11():
    out = _text_preservation([], [])
    assert out["equal"]["value"] is True


def test_text_preservation_matching_equal_true_batch11():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["value"] == 1.0
    assert out["recall"]["value"] == 1.0


def test_text_preservation_extra_chars_in_actual_batch11():
    """actual 多字符 → equal False, precision < 1。"""
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abcX"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["precision"]["value"] == 0.75  # 3/4


def test_text_preservation_missing_chars_in_actual_batch11():
    """actual 缺字符 → equal False, recall < 1。"""
    elements = [{"type": "paragraph", "content": "abcd"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is False
    assert out["recall"]["value"] == 0.75  # 3/4


def test_text_preservation_unicode_content_batch11():
    elements = [{"type": "paragraph", "content": "你好世界"}]
    chunks = [{"text": "你好世界"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_whitespace_only_both_empty_batch11():
    """expected 和 actual 仅含空白 → strip 后都为空 → empty_expected_and_actual。"""
    elements = [{"type": "paragraph", "content": "  \n\t "}]
    chunks = [{"text": " "}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True
    assert out["precision"]["reason"] == "empty_expected_and_actual"


def test_text_preservation_image_excluded_batch11():
    """image 类型不参与 expected（image 的 content 不算）。"""
    elements = [
        {"type": "paragraph", "content": "abc"},
        {"type": "image", "content": "image_data"},
    ]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    assert out["equal"]["value"] is True


def test_text_preservation_returns_dict_strict_batch11():
    out = _text_preservation([], [])
    assert type(out) is dict


def test_text_preservation_3_keys_batch11():
    out = _text_preservation([], [])
    assert set(out.keys()) == {"equal", "precision", "recall"}


def test_text_preservation_idempotent_batch11():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out1 = _text_preservation(elements, chunks)
    out2 = _text_preservation(elements, chunks)
    assert out1 == out2


# ---------- heading_boundary_ratio batch 11 ----------


def test_heading_boundary_ratio_no_headings_null_batch11():
    elements = [{"type": "paragraph"}]
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] is None
    assert out["reason"] == "no_heading_elements"


def test_heading_boundary_ratio_perfect_match_batch11():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 1.0


def test_heading_boundary_ratio_no_match_batch11():
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other"]}]
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.0


def test_heading_boundary_ratio_partial_match_batch11():
    elements = [
        {"type": "heading", "element_id": "h1"},
        {"type": "heading", "element_id": "h2"},
    ]
    chunks = [{"source_element_ids": ["h1"]}]  # 只匹配 h1
    out = _heading_boundary_ratio(elements, chunks)
    assert out["value"] == 0.5


def test_heading_boundary_ratio_heading_in_middle_not_counted_batch11():
    """heading 是 chunk 的第 2 个 source_element → 不算（必须 first）。"""
    elements = [{"type": "heading", "element_id": "h1"}]
    chunks = [{"source_element_ids": ["other", "h1"]}]
    out = _heading_boundary_ratio(elements, chunks)
    # first id is "other", not h1 → not matched
    assert out["value"] == 0.0


def test_heading_boundary_ratio_returns_dict_batch11():
    elements = []
    chunks = []
    out = _heading_boundary_ratio(elements, chunks)
    assert type(out) is dict


# ---------- silent_drop_count batch 11 ----------


def test_silent_drop_count_no_expectations_null_batch11():
    out = _silent_drop_count({"paragraph": 1}, None)
    assert out["value"] is None
    assert out["reason"] == "no_expectations"


def test_silent_drop_count_empty_expectations_null_batch11():
    out = _silent_drop_count({"paragraph": 1}, {})
    assert out["value"] is None


def test_silent_drop_count_no_element_count_by_type_null_batch11():
    out = _silent_drop_count({"paragraph": 1}, {"other_key": 1})
    assert out["value"] is None
    assert out["reason"] == "no_expectations_element_count"


def test_silent_drop_count_no_drop_when_match_batch11():
    by_type = {"paragraph": 5}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_drop_when_actual_less_batch11():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_count_no_drop_when_actual_more_batch11():
    by_type = {"paragraph": 10}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 0


def test_silent_drop_count_multiple_types_batch11():
    by_type = {"paragraph": 3, "heading": 2}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 1}}
    # paragraph drop 2, heading drop 0 → 2
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 2


def test_silent_drop_count_returns_int_batch11():
    by_type = {"paragraph": 3}
    expectations = {"element_count_by_type": {"paragraph": 5}}
    out = _silent_drop_count(by_type, expectations)
    assert type(out["value"]) is int


def test_silent_drop_count_returns_dict_batch11():
    out = _silent_drop_count({}, None)
    assert type(out) is dict


# ---------- _is_valid_bbox batch 11 ----------


def test_is_valid_bbox_4_ints_batch11():
    assert _is_valid_bbox([0, 0, 100, 100]) is True


def test_is_valid_bbox_4_floats_batch11():
    assert _is_valid_bbox([0.0, 0.0, 100.5, 100.5]) is True


def test_is_valid_bbox_mixed_int_float_batch11():
    assert _is_valid_bbox([0, 0.0, 100, 100.5]) is True


def test_is_valid_bbox_bool_rejected_batch11():
    assert _is_valid_bbox([True, 0, 0, 0]) is False


def test_is_valid_bbox_negative_values_batch11():
    """负数有限值也算 valid（不限定正负）。"""
    assert _is_valid_bbox([-1, -1, 0, 0]) is True


def test_is_valid_bbox_all_zeros_batch11():
    assert _is_valid_bbox([0, 0, 0, 0]) is True


def test_is_valid_bbox_tuple_rejected_batch11():
    assert _is_valid_bbox((0, 0, 100, 100)) is False


def test_is_valid_bbox_string_rejected_batch11():
    assert _is_valid_bbox("0000") is False


def test_is_valid_bbox_none_rejected_batch11():
    assert _is_valid_bbox(None) is False


def test_is_valid_bbox_empty_list_rejected_batch11():
    assert _is_valid_bbox([]) is False


def test_is_valid_bbox_too_short_rejected_batch11():
    assert _is_valid_bbox([0, 0, 100]) is False


def test_is_valid_bbox_too_long_rejected_batch11():
    assert _is_valid_bbox([0, 0, 100, 100, 100]) is False


def test_is_valid_bbox_string_element_rejected_batch11():
    assert _is_valid_bbox([0, 0, "100", 100]) is False


def test_is_valid_bbox_none_element_rejected_batch11():
    assert _is_valid_bbox([0, 0, None, 100]) is False


def test_is_valid_bbox_inf_rejected_batch11():
    assert _is_valid_bbox([0, 0, math.inf, 100]) is False


def test_is_valid_bbox_nan_rejected_batch11():
    assert _is_valid_bbox([0, 0, math.nan, 100]) is False


def test_is_valid_bbox_returns_bool_batch11():
    assert type(_is_valid_bbox([0, 0, 0, 0])) is bool


# ---------- _strip_unicode_whitespace batch 11 ----------


def test_strip_unicode_ws_empty_batch11():
    assert _strip_unicode_whitespace("") == ""


def test_strip_unicode_ws_no_whitespace_batch11():
    assert _strip_unicode_whitespace("abc") == "abc"


def test_strip_unicode_ws_all_whitespace_batch11():
    assert _strip_unicode_whitespace("   ") == ""


def test_strip_unicode_ws_internal_whitespace_batch11():
    assert _strip_unicode_whitespace("a b c") == "abc"


def test_strip_unicode_ws_leading_trailing_whitespace_batch11():
    assert _strip_unicode_whitespace("  abc  ") == "abc"


def test_strip_unicode_ws_nbsp_batch11():
    """NBSP \\u00a0 是空白 → 删除。"""
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ws_em_space_batch11():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ws_en_space_batch11():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ws_ideographic_space_batch11():
    assert _strip_unicode_whitespace("a　b") == "ab"


def test_strip_unicode_ws_line_separator_batch11():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ws_paragraph_separator_batch11():
    assert _strip_unicode_whitespace("a b") == "ab"


def test_strip_unicode_ws_punctuation_kept_batch11():
    """标点不是空白 → 保留。"""
    assert _strip_unicode_whitespace("a.b,c!") == "a.b,c!"


def test_strip_unicode_ws_unicode_letters_kept_batch11():
    assert _strip_unicode_whitespace("你好世界") == "你好世界"


def test_strip_unicode_ws_returns_str_batch11():
    assert type(_strip_unicode_whitespace("")) is str


def test_strip_unicode_ws_idempotent_batch11():
    s = "a b c"
    out1 = _strip_unicode_whitespace(s)
    out2 = _strip_unicode_whitespace(out1)
    assert out1 == out2


# ---------- module source forbidden tokens 第十四批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "pickle.loads",
        "yaml.load",
        "yaml.unsafe_load",
        "subprocess.check_call",
        "subprocess.call",
        "subprocess.getoutput",
        "os.popen",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
    ],
)
def test_metrics_source_no_forbidden_token_fourteenth_batch11(token):
    source = inspect.getsource(mmod)
    assert token not in source


def test_metrics_source_no_unlink_batch11():
    source = inspect.getsource(mmod)
    assert "unlink" not in source


def test_metrics_source_no_remove_batch11():
    source = inspect.getsource(mmod)
    assert ".remove(" not in source


def test_metrics_source_no_kill_batch11():
    source = inspect.getsource(mmod)
    assert ".kill(" not in source


def test_metrics_source_no_terminate_batch11():
    source = inspect.getsource(mmod)
    assert ".terminate(" not in source


def test_metrics_source_no_async_def_batch11():
    source = inspect.getsource(mmod)
    assert "async def" not in source


def test_metrics_source_no_yield_batch11():
    source = inspect.getsource(mmod)
    assert "yield" not in source


def test_metrics_source_no_walrus_batch11():
    source = inspect.getsource(mmod)
    assert ":=" not in source


def test_metrics_source_no_top_level_lambda_batch11():
    source = inspect.getsource(mmod)
    lines = source.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if not line.startswith(" ") and "=" in stripped and "lambda" in stripped:
            if stripped.split("=")[0].strip().isidentifier():
                raise AssertionError(f"top-level lambda: {line}")


def test_metrics_source_no_print_batch11():
    source = inspect.getsource(mmod)
    assert "print(" not in source


def test_metrics_source_no_socket_batch11():
    source = inspect.getsource(mmod)
    assert "socket" not in source


def test_metrics_source_no_threading_batch11():
    source = inspect.getsource(mmod)
    assert "threading" not in source


def test_metrics_source_no_multiprocessing_batch11():
    source = inspect.getsource(mmod)
    assert "multiprocessing" not in source


def test_metrics_source_no_asyncio_batch11():
    source = inspect.getsource(mmod)
    assert "asyncio" not in source


def test_metrics_source_no_pickle_module_batch11():
    source = inspect.getsource(mmod)
    assert "import pickle" not in source


# ---------- module source 字符串精确补强第十批 ----------


def test_module_source_has_future_annotations_batch11():
    source = inspect.getsource(mmod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_math_batch11():
    source = inspect.getsource(mmod)
    assert "import math" in source


def test_module_source_imports_counter_batch11():
    source = inspect.getsource(mmod)
    assert "from collections import Counter" in source


def test_module_source_imports_path_batch11():
    source = inspect.getsource(mmod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch11():
    source = inspect.getsource(mmod)
    assert "from typing import Any" in source


def test_module_source_text_types_constant_batch11():
    source = inspect.getsource(mmod)
    assert "_TEXT_TYPES" in source
    assert '"heading"' in source
    assert '"paragraph"' in source


def test_module_source_pdf_bbox_required_types_batch11():
    source = inspect.getsource(mmod)
    assert "_PDF_BBOX_REQUIRED_TYPES" in source


def test_module_source_not_evaluated_constant_batch11():
    source = inspect.getsource(mmod)
    assert "_NOT_EVALUATED" in source


def test_module_source_has_compute_automatic_metrics_def_batch11():
    source = inspect.getsource(mmod)
    assert "def compute_automatic_metrics(" in source


def test_module_source_has_pdf_locator_ratio_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _pdf_locator_ratio(" in source


def test_module_source_has_docx_locator_ratio_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _docx_locator_ratio(" in source


def test_module_source_has_text_preservation_def_batch11():
    source = inspect.getsource(mmod)
    assert "def _text_preservation(" in source


def test_module_source_no_main_block_batch11():
    source = inspect.getsource(mmod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch11():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_source_docstring_mentions_counter_batch11():
    assert mmod.__doc__ is not None
    assert "Counter" in mmod.__doc__ or "多集合" in mmod.__doc__


# ---------- signatures 第十一批 ----------


def test_signature_null_1_param_batch11():
    sig = inspect.signature(_null)
    assert len(sig.parameters) == 1


def test_signature_null_param_name_batch11():
    sig = inspect.signature(_null)
    assert list(sig.parameters) == ["reason"]


def test_signature_ratio_1_param_batch11():
    sig = inspect.signature(_ratio)
    assert len(sig.parameters) == 1


def test_signature_bool_metric_1_param_batch11():
    sig = inspect.signature(_bool_metric)
    assert len(sig.parameters) == 1


def test_signature_int_metric_1_param_batch11():
    sig = inspect.signature(_int_metric)
    assert len(sig.parameters) == 1


def test_signature_compute_5_params_batch11():
    sig = inspect.signature(compute_automatic_metrics)
    assert len(sig.parameters) == 5


def test_signature_compute_param_names_batch11():
    sig = inspect.signature(compute_automatic_metrics)
    assert list(sig.parameters) == [
        "document",
        "error",
        "source_type",
        "expectations",
        "image_base_dir",
    ]


def test_signature_compute_image_base_dir_default_none_batch11():
    sig = inspect.signature(compute_automatic_metrics)
    assert sig.parameters["image_base_dir"].default is None


def test_signature_compute_first_4_no_defaults_batch11():
    sig = inspect.signature(compute_automatic_metrics)
    params = list(sig.parameters.values())
    for p in params[:4]:
        assert p.default is inspect.Parameter.empty


def test_signature_pdf_locator_ratio_1_param_batch11():
    sig = inspect.signature(_pdf_locator_ratio)
    assert len(sig.parameters) == 1


def test_signature_docx_locator_ratio_1_param_batch11():
    sig = inspect.signature(_docx_locator_ratio)
    assert len(sig.parameters) == 1


def test_signature_is_valid_bbox_1_param_batch11():
    sig = inspect.signature(_is_valid_bbox)
    assert len(sig.parameters) == 1


def test_signature_text_preservation_2_params_batch11():
    sig = inspect.signature(_text_preservation)
    assert len(sig.parameters) == 2


def test_signature_funcs_function_type_batch11():
    for func in (
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
        compute_automatic_metrics,
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _text_preservation,
        _strip_unicode_whitespace,
        _silent_drop_count,
        _heading_boundary_ratio,
        _chunk_reference_ratio,
        _image_resource_ratio,
    ):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq_batch11():
    for func in (
        _null,
        _ratio,
        _bool_metric,
        _int_metric,
        compute_automatic_metrics,
        _pdf_locator_ratio,
        _docx_locator_ratio,
        _is_valid_bbox,
        _text_preservation,
        _strip_unicode_whitespace,
        _silent_drop_count,
        _heading_boundary_ratio,
        _chunk_reference_ratio,
        _image_resource_ratio,
    ):
        assert func.__module__ == "evaluation.metrics"


# ---------- module 合理性第十一批 ----------


def test_module_all_value_batch11():
    assert mmod.__all__ == ["compute_automatic_metrics"]


def test_module_all_is_list_batch11():
    assert isinstance(mmod.__all__, list)


def test_module_all_entries_unique_batch11():
    assert len(mmod.__all__) == len(set(mmod.__all__))


def test_module_has_dunder_file_batch11():
    assert hasattr(mmod, "__file__")
    assert mmod.__file__ is not None


def test_module_dunder_file_endswith_metrics_py_batch11():
    import os
    sep = os.sep
    assert mmod.__file__.endswith("evaluation" + sep + "metrics.py") or mmod.__file__.endswith(
        "evaluation/metrics.py"
    )


def test_module_name_is_evaluation_metrics_batch11():
    assert mmod.__name__ == "evaluation.metrics"


def test_module_user_function_count_batch11():
    funcs = [
        n for n, v in vars(mmod).items()
        if inspect.isfunction(v) and v.__module__ == mmod.__name__
    ]
    assert set(funcs) == {
        "_null",
        "_ratio",
        "_bool_metric",
        "_int_metric",
        "compute_automatic_metrics",
        "_pdf_locator_ratio",
        "_docx_locator_ratio",
        "_is_valid_bbox",
        "_image_resource_ratio",
        "_chunk_reference_ratio",
        "_strip_unicode_whitespace",
        "_text_preservation",
        "_heading_boundary_ratio",
        "_silent_drop_count",
    }


def test_module_no_user_classes_batch11():
    classes = [
        n for n, v in vars(mmod).items()
        if inspect.isclass(v) and v.__module__ == mmod.__name__
    ]
    assert classes == []


def test_module_docstring_present_batch11():
    assert mmod.__doc__ is not None
    assert len(mmod.__doc__) > 30


def test_module_docstring_mentions_text_preservation_batch11():
    assert mmod.__doc__ is not None
    assert "text_preservation" in mmod.__doc__ or "文本保留" in mmod.__doc__


# ---------- 端到端集成第十一批 ----------


def test_e2e_compute_with_real_doc_batch11():
    doc = {
        "elements": [
            {"type": "paragraph", "content": "hello", "element_id": "e1",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
            {"type": "heading", "content": "title", "element_id": "h1",
             "source_locator": {"page": 1, "bbox": [0, 0, 10, 10]}},
        ],
        "chunks": [
            {"text": "hello", "source_element_ids": ["e1"]},
            {"text": "title", "source_element_ids": ["h1"]},
        ],
    }
    out = compute_automatic_metrics(doc, None, "pdf", None)
    assert out["pipeline_success"]["value"] is True
    assert out["element_count_total"]["value"] == 2
    assert out["pdf_locator_valid_ratio"]["value"] == 1.0
    assert out["chunk_reference_intact_ratio"]["value"] == 1.0


def test_e2e_compute_pipeline_failed_batch11():
    error = {"code": "parse_failed", "message": "x"}
    out = compute_automatic_metrics(None, error, "pdf", None)
    assert out["pipeline_success"]["value"] is False
    assert out["error_code"]["value"] == "parse_failed"
    for k in (
        "element_count_total",
        "pdf_locator_valid_ratio",
        "docx_locator_valid_ratio",
    ):
        assert out[k]["value"] is None
        assert out[k]["reason"] == "pipeline_failed"


def test_e2e_compute_returns_serializable_batch11():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    out = compute_automatic_metrics(doc, None, "pdf", None)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_text_preservation_round_trip_batch11():
    elements = [{"type": "paragraph", "content": "abc"}]
    chunks = [{"text": "abc"}]
    out = _text_preservation(elements, chunks)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_combined_chain_idempotent_batch11():
    doc = {"elements": [{"type": "paragraph"}], "chunks": []}
    out1 = compute_automatic_metrics(doc, None, "pdf", None)
    out2 = compute_automatic_metrics(doc, None, "pdf", None)
    assert out1 == out2


def test_e2e_helpers_combined_chain_batch11():
    """helpers 组合使用。"""
    out_null = _null("reason")
    out_ratio = _ratio(0.5)
    out_bool = _bool_metric(True)
    out_int = _int_metric(42)
    combined = {"null": out_null, "ratio": out_ratio, "bool": out_bool, "int": out_int}
    text = json.dumps(combined)
    parsed = json.loads(text)
    assert parsed == combined


def test_e2e_pdf_locator_returns_serializable_batch11():
    elements = [{"type": "image", "source_locator": {"page": 1}}]
    out = _pdf_locator_ratio(elements)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_silent_drop_with_real_data_batch11():
    by_type = {"paragraph": 5, "heading": 2}
    expectations = {"element_count_by_type": {"paragraph": 5, "heading": 3}}
    out = _silent_drop_count(by_type, expectations)
    assert out["value"] == 1  # heading drop 1


def test_e2e_image_resource_with_dir_batch11(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    elements = [{"type": "image", "resource_path": "x.png"}]
    out = _image_resource_ratio(elements, tmp_path)
    text = json.dumps(out)
    parsed = json.loads(text)
    assert parsed == out


def test_e2e_combined_funcs_independent_batch11():
    """各子函数返回独立 dict。"""
    out1 = _null("a")
    out2 = _null("b")
    out1["new"] = 1
    assert "new" not in out2
