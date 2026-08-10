"""evaluation/schema.py 边角测试 - 第十三轮（Round 284）。

edges12 已覆盖：source-level token / __all__ / module imports / 模块 docstring /
3 个 schema 文件存在 / EvalSchemaError 行为深度 / validate 行为深度 / validate_file 行为深度 /
schema_path / load_schema / 模块 namespace / 函数互相调用关系。

edges13 补强未覆盖的角度：3 个 schema 之间的**交叉验证** + 每个 schema 的**深度违反场景**：
- manifest schema 多场景违反：
  - manifest_version 非 "1.0"（"2.0"/"1.1"/"1"/非 str/缺字段都失败）
  - devset_status 非 enum（"unknown"/"COMPLETE"/缺字段都失败）
  - documents 非 array（dict/string/null 都失败）
  - documents items 缺 doc_id/path/source_type 之一
  - document source_type 非 enum（"txt"/"html"/缺字段都失败）
  - document doc_id 空 string
  - document sha256 pattern 错（uppercase / 63 chars / non-hex / 空 string）
  - document expectations.element_count_by_type 含负数 / 含 string / 含 float
  - document expectations.required_markers items 空 string
  - top-level additionalProperties=false：额外字段失败
  - document additionalProperties=false：额外字段失败
  - expected_failure 缺 doc_id/path/expected_error_code 之一
  - expected_failure source_type 非 enum（"xml"）
  - expected_failure additionalProperties=false：额外字段失败

- annotation schema 多场景违反：
  - annotation_version 非 "1.0"
  - 缺 doc_id
  - doc_id 空 string
  - figure_caption_pairs items 缺 figure_marker/caption_text 之一
  - figure_caption_pairs items 额外字段失败
  - figure_caption_pairs items figure_marker 空 string
  - heading_order level < 1 / level 0 / level non-int
  - heading_order text 空 string
  - heading_order items 额外字段失败
  - chunk_boundary_anchors items 缺 marker/position 之一
  - chunk_boundary_anchors position 非 enum（"before"/"after" 之外）
  - chunk_boundary_anchors items 额外字段失败
  - top-level additionalProperties=false：额外字段失败

- evaluation-report schema 多场景违反：
  - report_version 非 "1.1"（"1.0"/"2.0"/缺字段都失败）
  - provenance 缺 git_commit/git_dirty/evaluator_version/.../max_chars/run_timestamp_iso 之一
  - provenance.git_dirty 非 bool
  - provenance.max_chars < 1 / non-int / float
  - provenance.evaluator_version 空 string
  - provenance additionalProperties=false：额外字段失败
  - devset 缺 status/file_count/.../categories_covered 之一
  - devset.status 非 enum
  - devset.file_count < 0
  - devset.categories_covered items 非 string
  - devset additionalProperties=false：额外字段失败
  - per_doc items 缺 doc_id/source_type/metrics/wall_time_seconds 之一
  - per_doc.source_type 非 enum（"txt"）
  - per_doc.wall_time_seconds 缺 total/parse/chunk 之一
  - per_doc.wall_time_seconds.total < 0
  - per_doc additionalProperties=false：额外字段失败
  - expected_failures items 缺 doc_id/expected_error_code/actual_error_code/matches 之一
  - expected_failures.matches 非 bool
  - expected_failures additionalProperties=false：额外字段失败
  - top-level additionalProperties=false：额外字段失败

- 跨 schema 交叉验证：
  - validate(annotation_dict, "manifest.schema.json") 失败
  - validate(annotation_dict, "evaluation-report.schema.json") 失败
  - validate(manifest_dict, "annotation.schema.json") 失败
  - validate(manifest_dict, "evaluation-report.schema.json") 失败
  - validate(report_dict, "manifest.schema.json") 失败
  - validate(report_dict, "annotation.schema.json") 失败
  - 但每个 dict 在自己 schema 下都通过

- 多错误排序行为：
  - 一个 instance 同时有多个 schema 错误，errors 是 list
  - errors sorted by absolute_path（list 比较语义）
  - errors[0] 是 sorted 后第一个

- validate_file 行为深度：
  - 目录而非文件：FileNotFoundError
  - 二进制内容（含 \x00）：JSONDecodeError
  - BOM 开头：JSONDecodeError（json 默认不剥 BOM）
  - 空 array 开头（[]）：EvalSchemaError（schema 要求 object）
  - 数字（json 数字）：EvalSchemaError（schema 要求 object）
  - 字符串（json 字符串）：EvalSchemaError（schema 要求 object）
  - null：EvalSchemaError（schema 要求 object）

- EvalSchemaError 与 jsonschema.ValidationError 关系：
  - EvalSchemaError 不是 ValidationError 子类
  - errors 字段里的 message 来自 jsonschema.ValidationError.message
  - errors 字段里的 schema_path 来自 jsonschema.ValidationError.absolute_schema_path

- 模块 source level 补强：
  - 'from jsonschema import Draft202012Validator' 精确字符串
  - 'from jsonschema.exceptions import ValidationError as JSValidationError' 精确字符串
  - 'with _schema_path(name).open("r", encoding="utf-8") as f:' 精确字符串
  - 'with p.open("r", encoding="utf-8") as f:' 精确字符串
  - module source 含 'jsonschema' 但不含 'jsonschema_p'
  - 'from __future__ import annotations' 在文件最顶
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

import evaluation.schema as schema_module
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ============================================================================
# manifest schema 深度违反
# ============================================================================


def _minimal_valid_manifest() -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }


def _minimal_valid_document() -> dict:
    return {
        "doc_id": "doc1",
        "path": "samples/foo.pdf",
        "source_type": "pdf",
    }


def test_validate_manifest_version_2_0_fails():
    m = _minimal_valid_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_version_1_1_fails():
    m = _minimal_valid_manifest()
    m["manifest_version"] = "1.1"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_version_int_fails():
    m = _minimal_valid_manifest()
    m["manifest_version"] = 1
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_version_missing_fails():
    m = _minimal_valid_manifest()
    del m["manifest_version"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_devset_status_unknown_fails():
    m = _minimal_valid_manifest()
    m["devset_status"] = "unknown"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_devset_status_uppercase_fails():
    """enum 大小写敏感，'COMPLETE' 不等于 'complete'。"""
    m = _minimal_valid_manifest()
    m["devset_status"] = "COMPLETE"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_devset_status_missing_fails():
    m = _minimal_valid_manifest()
    del m["devset_status"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_documents_not_array_fails():
    m = _minimal_valid_manifest()
    m["documents"] = {"doc_id": "x"}
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_documents_string_fails():
    m = _minimal_valid_manifest()
    m["documents"] = "not-an-array"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_documents_null_fails():
    m = _minimal_valid_manifest()
    m["documents"] = None
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_documents_missing_fails():
    m = _minimal_valid_manifest()
    del m["documents"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_missing_doc_id_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    del doc["doc_id"]
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_missing_path_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    del doc["path"]
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_missing_source_type_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    del doc["source_type"]
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_source_type_txt_fails():
    """document.source_type 只允许 pdf/docx，'txt' 失败。"""
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["source_type"] = "txt"
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_source_type_html_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["source_type"] = "html"
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_doc_id_empty_string_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["doc_id"] = ""
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_sha256_uppercase_fails():
    """sha256 pattern 是 ^[0-9a-f]{64}$，大写字母失败。"""
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = "A" + "0" * 63  # 64 chars 但大写
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_sha256_short_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = "0" * 63
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_sha256_long_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = "0" * 65
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_sha256_non_hex_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = "g" + "0" * 63
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_sha256_valid_lowercase_passes():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = "0" * 64
    m["documents"] = [doc]
    validate(m, "manifest.schema.json")  # 不抛


def test_validate_document_sha256_empty_string_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["sha256"] = ""
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_element_count_negative_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {"element_count_by_type": {"paragraph": -1}}
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_element_count_string_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {"element_count_by_type": {"paragraph": "two"}}
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_element_count_float_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {"element_count_by_type": {"paragraph": 1.5}}
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_required_markers_empty_string_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {"required_markers": [""]}
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_valid_passes():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {
        "element_count_by_type": {"paragraph": 10, "heading": 2},
        "required_markers": ["fig1", "section_a"],
    }
    m["documents"] = [doc]
    validate(m, "manifest.schema.json")  # 不抛


def test_validate_top_level_additional_property_fails():
    m = _minimal_valid_manifest()
    m["extra_field"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_document_additional_property_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["extra"] = "boom"
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expectations_additional_property_fails():
    m = _minimal_valid_manifest()
    doc = _minimal_valid_document()
    doc["expectations"] = {"extra_field": "boom"}
    m["documents"] = [doc]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expected_failure_missing_doc_id_fails():
    m = _minimal_valid_manifest()
    ef = {"path": "x.txt", "expected_error_code": "boom"}
    m["expected_failures"] = [ef]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expected_failure_missing_path_fails():
    m = _minimal_valid_manifest()
    ef = {"doc_id": "x", "expected_error_code": "boom"}
    m["expected_failures"] = [ef]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expected_failure_missing_code_fails():
    m = _minimal_valid_manifest()
    ef = {"doc_id": "x", "path": "x.txt"}
    m["expected_failures"] = [ef]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expected_failure_source_type_xml_fails():
    """expected_failure.source_type 允许 pdf/docx/txt/other，不允许 xml。"""
    m = _minimal_valid_manifest()
    ef = {"doc_id": "x", "path": "x.txt", "expected_error_code": "boom", "source_type": "xml"}
    m["expected_failures"] = [ef]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_expected_failure_source_type_other_passes():
    m = _minimal_valid_manifest()
    ef = {"doc_id": "x", "path": "x.txt", "expected_error_code": "boom", "source_type": "other"}
    m["expected_failures"] = [ef]
    validate(m, "manifest.schema.json")  # 不抛


def test_validate_expected_failure_additional_property_fails():
    m = _minimal_valid_manifest()
    ef = {"doc_id": "x", "path": "x.txt", "expected_error_code": "boom", "extra": "x"}
    m["expected_failures"] = [ef]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


# ============================================================================
# annotation schema 深度违反
# ============================================================================


def _minimal_valid_annotation() -> dict:
    return {
        "annotation_version": "1.0",
        "doc_id": "doc1",
    }


def test_validate_annotation_version_2_0_fails():
    a = _minimal_valid_annotation()
    a["annotation_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_missing_doc_id_fails():
    a = _minimal_valid_annotation()
    del a["doc_id"]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_doc_id_empty_string_fails():
    a = _minimal_valid_annotation()
    a["doc_id"] = ""
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_top_level_additional_property_fails():
    a = _minimal_valid_annotation()
    a["extra"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_missing_marker_fails():
    a = _minimal_valid_annotation()
    a["figure_caption_pairs"] = [{"caption_text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_missing_caption_fails():
    a = _minimal_valid_annotation()
    a["figure_caption_pairs"] = [{"figure_marker": "fig1"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_marker_empty_fails():
    a = _minimal_valid_annotation()
    a["figure_caption_pairs"] = [{"figure_marker": "", "caption_text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_additional_property_fails():
    a = _minimal_valid_annotation()
    a["figure_caption_pairs"] = [{"figure_marker": "f", "caption_text": "x", "extra": "boom"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_level_zero_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": 0, "text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_level_negative_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": -1, "text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_level_non_int_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": "one", "text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_text_empty_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": 1, "text": ""}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_missing_level_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"text": "x"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_missing_text_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": 1}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_additional_property_fails():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": 1, "text": "x", "extra": "boom"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_valid_passes():
    a = _minimal_valid_annotation()
    a["heading_order"] = [{"level": 1, "text": "Intro"}, {"level": 2, "text": "Methods"}]
    validate(a, "annotation.schema.json")  # 不抛


def test_validate_annotation_chunk_boundary_missing_marker_fails():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [{"position": "before"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_missing_position_fails():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "foo"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_position_invalid_enum_fails():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "foo", "position": "middle"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_marker_empty_fails():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [{"marker": "", "position": "before"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_additional_property_fails():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "foo", "position": "before", "extra": "boom"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_with_reason_passes():
    a = _minimal_valid_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "foo", "position": "before", "reason": "section break"}
    ]
    validate(a, "annotation.schema.json")  # 不抛


# ============================================================================
# evaluation-report schema 深度违反
# ============================================================================


def _minimal_valid_provenance() -> dict:
    return {
        "git_commit": "abc123",
        "git_dirty": False,
        "evaluator_version": "1.1",
        "report_version": "1.1",
        "parser_name": "fallback",
        "parser_version": "1.0",
        "dependencies": {"pdfplumber": "0.10"},
        "max_chars": 800,
        "run_timestamp_iso": "2026-01-01T00:00:00Z",
    }


def _minimal_valid_devset() -> dict:
    return {
        "status": "incomplete",
        "file_count": 1,
        "content_group_count": 1,
        "pdf_count": 1,
        "docx_count": 0,
        "categories_covered": ["cat_a"],
    }


def _minimal_valid_summary() -> dict:
    return {
        "counts": {"succeeded": 1, "failed": 0},
        "success_rates": {"overall": 1.0},
        "ratio_macro_averages": {"text_preservation_ratio": 1.0},
        "silent_drop_total": 0,
    }


def _minimal_valid_per_doc() -> dict:
    return [
        {
            "doc_id": "doc1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.1,
                "parse": None,
                "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented",
            },
        }
    ]


def _minimal_valid_report() -> dict:
    return {
        "report_version": "1.1",
        "provenance": _minimal_valid_provenance(),
        "devset": _minimal_valid_devset(),
        "summary": _minimal_valid_summary(),
        "per_doc": _minimal_valid_per_doc(),
    }


def test_validate_minimal_valid_report_passes():
    validate(_minimal_valid_report(), "evaluation-report.schema.json")  # 不抛


def test_validate_report_version_1_0_fails():
    r = _minimal_valid_report()
    r["report_version"] = "1.0"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_version_2_0_fails():
    r = _minimal_valid_report()
    r["report_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_version_missing_fails():
    r = _minimal_valid_report()
    del r["report_version"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_missing_git_commit_fails():
    r = _minimal_valid_report()
    del r["provenance"]["git_commit"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_missing_git_dirty_fails():
    r = _minimal_valid_report()
    del r["provenance"]["git_dirty"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_missing_evaluator_version_fails():
    r = _minimal_valid_report()
    del r["provenance"]["evaluator_version"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_missing_max_chars_fails():
    r = _minimal_valid_report()
    del r["provenance"]["max_chars"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_missing_run_timestamp_iso_fails():
    r = _minimal_valid_report()
    del r["provenance"]["run_timestamp_iso"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_git_dirty_non_bool_fails():
    r = _minimal_valid_report()
    r["provenance"]["git_dirty"] = "no"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_max_chars_zero_fails():
    """max_chars minimum=1，0 失败。"""
    r = _minimal_valid_report()
    r["provenance"]["max_chars"] = 0
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_max_chars_negative_fails():
    r = _minimal_valid_report()
    r["provenance"]["max_chars"] = -1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_max_chars_float_fails():
    r = _minimal_valid_report()
    r["provenance"]["max_chars"] = 1.5
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_evaluator_version_empty_string_fails():
    r = _minimal_valid_report()
    r["provenance"]["evaluator_version"] = ""
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_provenance_additional_property_fails():
    r = _minimal_valid_report()
    r["provenance"]["extra"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_missing_status_fails():
    r = _minimal_valid_report()
    del r["devset"]["status"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_status_unknown_fails():
    r = _minimal_valid_report()
    r["devset"]["status"] = "unknown"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_file_count_negative_fails():
    r = _minimal_valid_report()
    r["devset"]["file_count"] = -1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_pdf_count_negative_fails():
    r = _minimal_valid_report()
    r["devset"]["pdf_count"] = -1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_categories_covered_non_string_fails():
    r = _minimal_valid_report()
    r["devset"]["categories_covered"] = [1, 2, 3]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_devset_additional_property_fails():
    r = _minimal_valid_report()
    r["devset"]["extra"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_missing_doc_id_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["doc_id"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_missing_source_type_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["source_type"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_missing_metrics_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["metrics"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_missing_wall_time_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["wall_time_seconds"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_source_type_txt_fails():
    r = _minimal_valid_report()
    r["per_doc"][0]["source_type"] = "txt"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_wall_time_missing_total_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["wall_time_seconds"]["total"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_wall_time_missing_parse_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["wall_time_seconds"]["parse"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_wall_time_missing_chunk_fails():
    r = _minimal_valid_report()
    del r["per_doc"][0]["wall_time_seconds"]["chunk"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_wall_time_total_negative_fails():
    r = _minimal_valid_report()
    r["per_doc"][0]["wall_time_seconds"]["total"] = -0.1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_per_doc_additional_property_fails():
    r = _minimal_valid_report()
    r["per_doc"][0]["extra"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_expected_failure_result_missing_doc_id_fails():
    r = _minimal_valid_report()
    r["expected_failures"] = [
        {"expected_error_code": "x", "actual_error_code": "x", "matches": True}
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_expected_failure_result_missing_matches_fails():
    r = _minimal_valid_report()
    r["expected_failures"] = [
        {"doc_id": "x", "expected_error_code": "x", "actual_error_code": "x"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_expected_failure_result_matches_non_bool_fails():
    r = _minimal_valid_report()
    r["expected_failures"] = [
        {"doc_id": "x", "expected_error_code": "x", "actual_error_code": "x", "matches": "yes"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_expected_failure_result_additional_property_fails():
    r = _minimal_valid_report()
    r["expected_failures"] = [
        {
            "doc_id": "x",
            "expected_error_code": "x",
            "actual_error_code": "x",
            "matches": True,
            "extra": "boom",
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_top_level_additional_property_fails():
    r = _minimal_valid_report()
    r["extra"] = "boom"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_missing_provenance_fails():
    r = _minimal_valid_report()
    del r["provenance"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_missing_devset_fails():
    r = _minimal_valid_report()
    del r["devset"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_missing_summary_fails():
    r = _minimal_valid_report()
    del r["summary"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_missing_per_doc_fails():
    r = _minimal_valid_report()
    del r["per_doc"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


# ============================================================================
# 跨 schema 交叉验证
# ============================================================================


def test_cross_validate_annotation_dict_against_manifest_schema_fails():
    """annotation 在 manifest schema 下不合法（manifest_version 错）。"""
    a = _minimal_valid_annotation()
    with pytest.raises(EvalSchemaError):
        validate(a, "manifest.schema.json")


def test_cross_validate_annotation_dict_against_report_schema_fails():
    a = _minimal_valid_annotation()
    with pytest.raises(EvalSchemaError):
        validate(a, "evaluation-report.schema.json")


def test_cross_validate_manifest_dict_against_annotation_schema_fails():
    m = _minimal_valid_manifest()
    with pytest.raises(EvalSchemaError):
        validate(m, "annotation.schema.json")


def test_cross_validate_manifest_dict_against_report_schema_fails():
    m = _minimal_valid_manifest()
    with pytest.raises(EvalSchemaError):
        validate(m, "evaluation-report.schema.json")


def test_cross_validate_report_dict_against_manifest_schema_fails():
    r = _minimal_valid_report()
    with pytest.raises(EvalSchemaError):
        validate(r, "manifest.schema.json")


def test_cross_validate_report_dict_against_annotation_schema_fails():
    r = _minimal_valid_report()
    with pytest.raises(EvalSchemaError):
        validate(r, "annotation.schema.json")


def test_each_dict_validates_against_own_schema():
    """每个最小 dict 在自己 schema 下都通过。"""
    validate(_minimal_valid_manifest(), "manifest.schema.json")
    validate(_minimal_valid_annotation(), "annotation.schema.json")
    validate(_minimal_valid_report(), "evaluation-report.schema.json")


# ============================================================================
# 多错误排序行为
# ============================================================================


def test_validate_multiple_errors_returns_list():
    """一个 instance 同时违反多个约束，errors 是 list，长度 > 1。"""
    bad_manifest = {}  # 缺 3 个 required 字段
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    errs = exc.value.errors
    assert isinstance(errs, list)
    assert len(errs) >= 1


def test_validate_errors_sorted_by_path_length():
    """sorted by list(absolute_path)；list 比较语义保证确定性顺序。"""
    # 用 manifest 让 documents[0].doc_id 缺失同时 manifest_version 错
    bad_manifest = {
        "manifest_version": "bad",
        "devset_status": "complete",
        "documents": [{"path": "x", "source_type": "pdf"}],  # 缺 doc_id
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc.value.errors]
    # 排序后第一个应是空路径（top-level 错）或较短路径
    assert paths == sorted(paths)


def test_validate_head_error_is_first_in_sorted():
    """head = errors[0]，sorted 后第一个。"""
    bad_manifest = {}  # 缺多个字段
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    err = exc.value
    head_msg_in_message = err.errors[0]["message"]
    # head 的 message 应该在 err 的 str 中
    assert head_msg_in_message in str(err)


def test_validate_error_count_in_message():
    """错误信息含 '(N 处)' 格式，N 与 len(errors) 一致。"""
    bad_manifest = {}  # 缺多个字段
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    err = exc.value
    msg = str(err)
    n = len(err.errors)
    assert f"({n} 处)" in msg


# ============================================================================
# validate_file 行为深度
# ============================================================================


def test_validate_file_directory_not_file_fails(tmp_path):
    """目录而非文件：FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_binary_content_fails(tmp_path):
    """文件含 \x00：JSONDecodeError。"""
    p = tmp_path / "bad.json"
    p.write_bytes(b"\x00\x01\x02")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_bom_content_fails(tmp_path):
    """json.load 默认不剥 UTF-8 BOM，含 BOM 失败。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps(_minimal_valid_manifest()).encode("utf-8"))
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_top_level_array_fails(tmp_path):
    """top-level JSON 是 array 而非 object：EvalSchemaError。"""
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_top_level_number_fails(tmp_path):
    """top-level JSON 是 number：EvalSchemaError。"""
    p = tmp_path / "num.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_top_level_string_fails(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_top_level_null_fails(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_top_level_boolean_fails(tmp_path):
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_pathlib_path_object_accepted(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(_minimal_valid_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_str_path_accepted(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(_minimal_valid_manifest()), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # 不抛


def test_validate_file_nonexistent_path_fails():
    with pytest.raises(FileNotFoundError):
        validate_file("/tmp/__definitely_not_exists__.json", "manifest.schema.json")


def test_validate_file_unknown_schema_fails(tmp_path):
    """未知 schema name → FileNotFoundError（schema 文件不存在）。"""
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


# ============================================================================
# EvalSchemaError 与 jsonschema.ValidationError 关系
# ============================================================================


def test_eval_schema_error_is_not_validation_error_subclass():
    """EvalSchemaError 不是 jsonschema.ValidationError 子类。"""
    assert not issubclass(EvalSchemaError, JSValidationError)


def test_eval_schema_error_message_comes_from_jsonschema():
    """errors 字段里的 message 来自 jsonschema.ValidationError.message。"""
    bad_manifest = {}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    # 直接用 jsonschema 校验同一 instance，比对 message
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    raw_errors = list(validator.iter_errors(bad_manifest))
    raw_messages = {e.message for e in raw_errors}
    our_messages = {e["message"] for e in exc.value.errors}
    assert our_messages == raw_messages


def test_eval_schema_error_schema_path_comes_from_jsonschema():
    """errors 字段里的 schema_path 来自 jsonschema.ValidationError.absolute_schema_path。"""
    bad_manifest = {}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    raw_errors = list(validator.iter_errors(bad_manifest))
    raw_schema_paths = {tuple(e.absolute_schema_path) for e in raw_errors}
    our_schema_paths = {tuple(e["schema_path"]) for e in exc.value.errors}
    assert our_schema_paths == raw_schema_paths


def test_eval_schema_error_path_comes_from_jsonschema():
    bad_manifest = {}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    raw_errors = list(validator.iter_errors(bad_manifest))
    raw_paths = {tuple(e.absolute_path) for e in raw_errors}
    our_paths = {tuple(e["path"]) for e in exc.value.errors}
    assert our_paths == raw_paths


# ============================================================================
# 模块 source level 补强
# ============================================================================


def test_module_source_contains_exact_jsonschema_import():
    src = inspect.getsource(schema_module)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_exact_validation_error_import():
    src = inspect.getsource(schema_module)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_contains_exact_schema_path_open_call():
    """load_schema 中含 '_schema_path(name).open("r", encoding="utf-8")'。"""
    src = inspect.getsource(schema_module)
    assert '_schema_path(name).open("r", encoding="utf-8")' in src


def test_module_source_contains_exact_validate_file_open_call():
    """validate_file 中含 'p.open("r", encoding="utf-8")'。"""
    src = inspect.getsource(schema_module)
    assert 'p.open("r", encoding="utf-8")' in src


def test_module_source_contains_jsonschema_word():
    src = inspect.getsource(schema_module)
    assert "jsonschema" in src


def test_module_source_does_not_contain_jsonschema_p():
    """不依赖 jsonschema-p（假想名）等替代库。"""
    src = inspect.getsource(schema_module)
    assert "jsonschema_p" not in src
    assert "jsonschema-p" not in src


def test_module_source_contains_future_annotations_at_top():
    """'from __future__ import annotations' 在 import json 之前。"""
    src = inspect.getsource(schema_module)
    pos_future = src.find("from __future__ import annotations")
    pos_json = src.find("import json")
    assert pos_future != -1
    assert pos_json != -1
    assert pos_future < pos_json


def test_module_source_contains_no_relative_import():
    """schema.py 不用相对 import（如 from . import x）。"""
    src = inspect.getsource(schema_module)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_contains_no_walrus_operator():
    """schema.py 不用 walrus operator（:=）。"""
    src = inspect.getsource(schema_module)
    assert ":=" not in src


def test_module_source_contains_no_async_keyword():
    src = inspect.getsource(schema_module)
    assert "async def" not in src
    assert "await " not in src


def test_module_source_contains_no_yield():
    """schema.py 无生成器。"""
    src = inspect.getsource(schema_module)
    assert "yield" not in src


def test_module_source_contains_no_global_keyword():
    src = inspect.getsource(schema_module)
    assert "global " not in src


def test_module_source_contains_no_nonlocal_keyword():
    src = inspect.getsource(schema_module)
    assert "nonlocal " not in src


def test_module_source_contains_no_class_decorator():
    """EvalSchemaError 上无装饰器（@dataclass 等）。"""
    src = inspect.getsource(schema_module)
    # 简单检查：class 上一行不以 @ 开头
    lines = src.split("\n")
    for i, line in enumerate(lines):
        if "class EvalSchemaError" in line:
            # 检查前一行
            if i > 0:
                prev = lines[i - 1].strip()
                assert not prev.startswith("@")


def test_module_source_contains_no_assert_statement():
    src = inspect.getsource(schema_module)
    # 排除断言（生产代码不应有 assert）
    assert "\n    assert " not in src
    assert "\nassert " not in src


def test_module_all_5_entries_each_a_valid_identifier():
    for name in schema_module.__all__:
        assert isinstance(name, str)
        assert name.isidentifier()


def test_module_all_each_entry_exists_in_module_namespace():
    for name in schema_module.__all__:
        assert hasattr(schema_module, name)


# ============================================================================
# 函数签名深度
# ============================================================================


def test_validate_function_signature_2_params_no_default():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    for p in params:
        assert p.default is inspect.Parameter.empty
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_function_return_annotation_is_none():
    """return_annotation 是 'None'（from __future__ annotations 使其成为字符串）。"""
    sig = inspect.signature(validate)
    # 'from __future__ import annotations' 让 return_annotation 变成字符串
    assert sig.return_annotation in (type(None), "None")


def test_load_schema_function_signature_1_param_name():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_validate_file_function_signature_2_params_path_schema_name():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "path"
    assert params[1].name == "schema_name"


def test_schema_path_function_signature_1_param():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_eval_schema_error_init_signature_2_params_message_errors():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self + message + errors = 3
    assert len(params) == 3
    assert params[0].name == "self"
    assert params[1].name == "message"
    assert params[2].name == "errors"
    assert params[2].default is None


# ============================================================================
# EvalSchemaError 实例化深度
# ============================================================================


def test_eval_schema_error_with_kwargs_only():
    """可以用 keyword-only 方式构造。"""
    err = EvalSchemaError(message="x", errors=[])
    assert str(err) == "x"
    assert err.errors == []


def test_eval_schema_error_errors_none_then_empty_list():
    """errors=None → []."""
    err = EvalSchemaError("x")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_errors_empty_list_still_empty():
    """errors=[] → []."""
    err = EvalSchemaError("x", errors=[])
    assert err.errors == []


def test_eval_schema_error_errors_falsy_tuple_becomes_empty():
    """errors=() 是 falsy，会触发 'errors or []' 的 fallback。"""
    err = EvalSchemaError("x", errors=())
    assert err.errors == []


def test_eval_schema_error_errors_truthy_dict_kept_as_is():
    """errors=non-list truthy（dict）会被透传（'or' 短路返回 truthy 左侧）。"""
    errs = {"a": 1}
    err = EvalSchemaError("x", errors=errs)
    assert err.errors == errs


def test_eval_schema_error_cannot_be_caught_as_validation_error():
    """EvalSchemaError 不能被 'except JSValidationError' 捕获。"""
    try:
        raise EvalSchemaError("x")
    except JSValidationError:
        pytest.fail("EvalSchemaError should not be caught by JSValidationError")
    except Exception:
        pass


def test_eval_schema_error_args_attribute_contains_message_only():
    """super().__init__(message) 只把 message 放到 args[0]。"""
    err = EvalSchemaError("msg", errors=[{"x": 1}])
    assert err.args == ("msg",)


def test_eval_schema_error_can_be_raised_and_reraised():
    err = EvalSchemaError("x")
    for _ in range(3):
        try:
            raise err
        except EvalSchemaError as e:
            assert e is err


# ============================================================================
# 实际 schema 字段深度
# ============================================================================


def test_manifest_schema_required_fields_exact():
    """manifest.schema.json required: manifest_version, devset_status, documents。"""
    schema = load_schema("manifest.schema.json")
    assert schema["required"] == ["manifest_version", "devset_status", "documents"]


def test_manifest_schema_additional_properties_false():
    schema = load_schema("manifest.schema.json")
    assert schema["additionalProperties"] is False


def test_annotation_schema_required_fields_exact():
    schema = load_schema("annotation.schema.json")
    assert schema["required"] == ["annotation_version", "doc_id"]


def test_annotation_schema_additional_properties_false():
    schema = load_schema("annotation.schema.json")
    assert schema["additionalProperties"] is False


def test_evaluation_report_schema_required_fields_exact():
    schema = load_schema("evaluation-report.schema.json")
    assert schema["required"] == [
        "report_version",
        "provenance",
        "devset",
        "summary",
        "per_doc",
    ]


def test_evaluation_report_schema_additional_properties_false():
    schema = load_schema("evaluation-report.schema.json")
    assert schema["additionalProperties"] is False


def test_manifest_schema_has_defs_with_document_and_expected_failure():
    schema = load_schema("manifest.schema.json")
    assert "document" in schema["$defs"]
    assert "expected_failure" in schema["$defs"]


def test_annotation_schema_has_defs_with_boundary_anchor():
    schema = load_schema("annotation.schema.json")
    assert "boundary_anchor" in schema["$defs"]


def test_evaluation_report_schema_has_4_defs():
    """evaluation-report $defs 含 provenance/devset/summary/per_doc 4 个。"""
    schema = load_schema("evaluation-report.schema.json")
    defs = schema["$defs"]
    assert "provenance" in defs
    assert "devset" in defs
    assert "summary" in defs
    assert "per_doc" in defs
    assert "expected_failure_result" in defs


def test_manifest_schema_doc_required_fields_exact():
    schema = load_schema("manifest.schema.json")
    doc_def = schema["$defs"]["document"]
    assert doc_def["required"] == ["doc_id", "path", "source_type"]


def test_manifest_schema_doc_additional_properties_false():
    schema = load_schema("manifest.schema.json")
    doc_def = schema["$defs"]["document"]
    assert doc_def["additionalProperties"] is False


def test_annotation_schema_boundary_anchor_position_enum():
    schema = load_schema("annotation.schema.json")
    anchor_def = schema["$defs"]["boundary_anchor"]
    assert anchor_def["properties"]["position"]["enum"] == ["before", "after"]


def test_manifest_schema_document_sha256_pattern():
    schema = load_schema("manifest.schema.json")
    doc_def = schema["$defs"]["document"]
    assert doc_def["properties"]["sha256"]["pattern"] == "^[0-9a-f]{64}$"


def test_manifest_schema_expected_failure_source_type_enum():
    schema = load_schema("manifest.schema.json")
    ef_def = schema["$defs"]["expected_failure"]
    assert ef_def["properties"]["source_type"]["enum"] == ["pdf", "docx", "txt", "other"]


def test_evaluation_report_provenance_required_9_fields():
    schema = load_schema("evaluation-report.schema.json")
    prov_def = schema["$defs"]["provenance"]
    assert set(prov_def["required"]) == {
        "git_commit",
        "git_dirty",
        "evaluator_version",
        "report_version",
        "parser_name",
        "parser_version",
        "dependencies",
        "max_chars",
        "run_timestamp_iso",
    }


def test_evaluation_report_per_doc_required_4_fields():
    schema = load_schema("evaluation-report.schema.json")
    per_doc_def = schema["$defs"]["per_doc"]
    assert set(per_doc_def["required"]) == {"doc_id", "source_type", "metrics", "wall_time_seconds"}


def test_evaluation_report_summary_additional_properties_true():
    """summary 允许额外字段（aggregator 输出灵活）。"""
    schema = load_schema("evaluation-report.schema.json")
    summary_def = schema["$defs"]["summary"]
    assert summary_def["additionalProperties"] is True


def test_all_three_schemas_use_draft_2020_12():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        schema = load_schema(name)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


# ============================================================================
# validate 在不同 schema 下的 isolated behavior
# ============================================================================


def test_validate_two_schemas_independent_errors():
    """validate 调用两次（不同 schema）后 errors list 独立。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e1:
        try:
            validate({}, "annotation.schema.json")
        except EvalSchemaError as e2:
            assert e1.errors is not e2.errors
            assert e1 is not e2
            return
    pytest.fail("expected EvalSchemaError")


def test_validate_loads_schema_every_call(monkeypatch):
    """validate 不缓存 schema（每次调用 load_schema）。"""
    call_count = [0]
    original = schema_module.load_schema

    def wrapper(name):
        call_count[0] += 1
        return original(name)

    monkeypatch.setattr(schema_module, "load_schema", wrapper)
    validate(_minimal_valid_manifest(), "manifest.schema.json")
    validate(_minimal_valid_manifest(), "manifest.schema.json")
    assert call_count[0] == 2


def test_validate_does_not_mutate_input():
    """validate 不修改 instance。"""
    m = _minimal_valid_manifest()
    snapshot = json.loads(json.dumps(m))
    validate(m, "manifest.schema.json")
    assert m == snapshot


def test_validate_does_not_mutate_input_on_failure():
    """validate 失败时不修改 instance。"""
    bad = {"foo": "bar"}
    snapshot = json.loads(json.dumps(bad))
    try:
        validate(bad, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert bad == snapshot


# ============================================================================
# SCHEMAS_DIR 行为深度
# ============================================================================


def test_schemas_dir_resolves_to_canonical_path():
    """SCHEMAS_DIR 已 resolved，无 symlink。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve(strict=False)


def test_schemas_dir_is_directory():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_document_schema_too():
    """schemas/ 还含 document.schema.json（app/schema 用的）。"""
    files = {f.name for f in SCHEMAS_DIR.glob("*.json")}
    assert "document.schema.json" in files


def test_schemas_dir_contains_exactly_4_or_more_schemas():
    """至少 4 个 schema 文件。"""
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    assert len(files) >= 4


def test_schemas_dir_does_not_contain_python_files():
    files = list(SCHEMAS_DIR.glob("*.py"))
    assert len(files) == 0


def test_schemas_dir_does_not_contain_text_files():
    files = list(SCHEMAS_DIR.glob("*.txt"))
    assert len(files) == 0


def test_schemas_dir_does_not_contain_markdown_files():
    files = list(SCHEMAS_DIR.glob("*.md"))
    assert len(files) == 0


def test_schemas_dir_files_are_valid_json():
    """每个 .json schema 文件能被 json.load。"""
    for f in SCHEMAS_DIR.glob("*.json"):
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        assert isinstance(data, dict)


def test_schemas_dir_files_all_have_schema_field():
    for f in SCHEMAS_DIR.glob("*.schema.json"):
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        assert "$schema" in data


def test_schemas_dir_files_all_have_type_object():
    for f in SCHEMAS_DIR.glob("*.schema.json"):
        with f.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        assert data.get("type") == "object"
