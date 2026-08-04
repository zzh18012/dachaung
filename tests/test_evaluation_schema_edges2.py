"""Round 87 — evaluation/schema.py 边角覆盖（第二轮）。

互补于已有：
- tests/test_evaluation_schema.py（55 测试）
- tests/test_evaluation_schema_edges.py（80 测试）

第二轮重点：每个 Schema 的字段语义、EvalSchemaError 类的深度、
validate 与 validate_file 的边界（非 dict 实例、空 dict、各种 JSON 类型）。
不修改 evaluation/schema.py。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as eval_schema
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    __all__ as schema_all,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =============================================================================
# SCHEMAS_DIR 常量深度
# =============================================================================


def test_schemas_dir_is_pathlib_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_absolute_resolved():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_on_filesystem():
    assert SCHEMAS_DIR.exists()


def test_schemas_dir_is_directory():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_named_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR 的父目录应包含 app/、evaluation/。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "app").is_dir()
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_contains_four_known_schemas():
    files = {p.name for p in SCHEMAS_DIR.iterdir() if p.suffix == ".json"}
    assert {
        "annotation.schema.json",
        "manifest.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    }.issubset(files)


def test_schemas_dir_module_constant_is_path_not_str():
    assert not isinstance(SCHEMAS_DIR, str)


# =============================================================================
# _schema_path 函数深度
# =============================================================================


def test_schema_path_returns_path_for_known_schema():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returned_path_is_absolute():
    p = _schema_path("annotation.schema.json")
    assert p.is_absolute()


def test_schema_path_returned_path_is_file():
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


def test_schema_path_unknown_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        _schema_path("does-not-exist.schema.json")


def test_schema_path_empty_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_name_raises_filenotfound():
    """schemas/ 下没有子目录，传目录名应失败。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir")


def test_schema_path_error_message_contains_filename():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("missing.schema.json")
    assert "missing.schema.json" in str(exc.value)


def test_schema_path_no_extension_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest")


def test_schema_path_subpath_does_not_sandbox():
    """_schema_path 不过滤 ../，传相对路径会解析到 SCHEMAS_DIR 之外。

    这是已知行为（不是安全沙箱）；测试记录现状，提示调用者传可信输入。
    """
    p = _schema_path("../app/schema.py")
    # SCHEMAS_DIR / '../app/schema.py' 解析到项目根的 app/schema.py，文件存在
    assert p.is_file()


# =============================================================================
# load_schema 函数深度
# =============================================================================


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_dollar_key():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        s = load_schema(name)
        assert s.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_each_has_id_key():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        s = load_schema(name)
        assert "$id" in s
        assert isinstance(s["$id"], str)


def test_load_schema_each_has_title_key():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        s = load_schema(name)
        assert "title" in s


def test_load_schema_each_has_type_object():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        s = load_schema(name)
        assert s.get("type") == "object"


def test_load_schema_manifest_has_required_field():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    assert "manifest_version" in s["required"]
    assert "devset_status" in s["required"]
    assert "documents" in s["required"]


def test_load_schema_annotation_has_required_field():
    s = load_schema("annotation.schema.json")
    assert "annotation_version" in s["required"]
    assert "doc_id" in s["required"]


def test_load_schema_report_has_required_field():
    s = load_schema("evaluation-report.schema.json")
    for field in ("report_version", "provenance", "devset", "summary", "per_doc"):
        assert field in s["required"]


def test_load_schema_manifest_const_manifest_version():
    s = load_schema("manifest.schema.json")
    mv = s["properties"]["manifest_version"]
    assert mv.get("const") == "1.0"


def test_load_schema_annotation_const_annotation_version():
    s = load_schema("annotation.schema.json")
    av = s["properties"]["annotation_version"]
    assert av.get("const") == "1.0"


def test_load_schema_report_const_report_version():
    s = load_schema("evaluation-report.schema.json")
    rv = s["properties"]["report_version"]
    assert rv.get("const") == "1.1"


def test_load_schema_returns_fresh_dict_each_call():
    """load_schema 不缓存，每次返回新 dict。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_modifications_do_not_persist():
    """修改返回 dict 不影响下次调用。"""
    s1 = load_schema("manifest.schema.json")
    s1["$test_mod"] = "x"
    s2 = load_schema("manifest.schema.json")
    assert "$test_mod" not in s2


def test_load_schema_unknown_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# =============================================================================
# validate — Schema 校验深度（每个 Schema 字段语义）
# =============================================================================


def _minimal_manifest():
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
            }
        ],
    }


def _minimal_annotation():
    return {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }


def _minimal_report():
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-05T00:00:00+08:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 1,
            "docx_count": 0,
            "categories_covered": ["a"],
        },
        "summary": {},
        "per_doc": [],
    }


# --- manifest 字段深度 ---


def test_validate_manifest_minimal_passes():
    validate(_minimal_manifest(), "manifest.schema.json")


def test_validate_manifest_const_version_rejects_other_value():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_devset_status_only_complete_or_incomplete():
    m = _minimal_manifest()
    m["devset_status"] = "ready"  # 非法 enum
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_devset_status_complete_accepts():
    m = _minimal_manifest()
    m["devset_status"] = "complete"
    validate(m, "manifest.schema.json")


def test_validate_manifest_extra_top_level_field_rejected():
    m = _minimal_manifest()
    m["unexpected_field"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_missing_doc_id_rejected():
    m = _minimal_manifest()
    del m["documents"][0]["doc_id"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_empty_doc_id_rejected():
    m = _minimal_manifest()
    m["documents"][0]["doc_id"] = ""
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_missing_path_rejected():
    m = _minimal_manifest()
    del m["documents"][0]["path"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_empty_path_rejected():
    m = _minimal_manifest()
    m["documents"][0]["path"] = ""
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_missing_source_type_rejected():
    m = _minimal_manifest()
    del m["documents"][0]["source_type"]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_source_type_invalid_rejected():
    m = _minimal_manifest()
    m["documents"][0]["source_type"] = "txt"  # documents 不允许 txt
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_source_type_docx_accepts():
    m = _minimal_manifest()
    m["documents"][0]["source_type"] = "docx"
    validate(m, "manifest.schema.json")


def test_validate_manifest_document_sha256_invalid_short_rejected():
    m = _minimal_manifest()
    m["documents"][0]["sha256"] = "abc"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_sha256_invalid_non_hex_rejected():
    m = _minimal_manifest()
    m["documents"][0]["sha256"] = "z" * 64
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_sha256_valid_hex_accepts():
    m = _minimal_manifest()
    m["documents"][0]["sha256"] = "a" * 64
    validate(m, "manifest.schema.json")


def test_validate_manifest_document_sha256_uppercase_rejected():
    m = _minimal_manifest()
    m["documents"][0]["sha256"] = "A" * 64
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_paired_with_must_be_string():
    m = _minimal_manifest()
    m["documents"][0]["paired_with"] = 5
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_document_paired_with_string_accepts():
    m = _minimal_manifest()
    m["documents"][0]["paired_with"] = "other_doc"
    validate(m, "manifest.schema.json")


def test_validate_manifest_document_extra_field_rejected():
    m = _minimal_manifest()
    m["documents"][0]["extra"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_expectations_empty_object_accepts():
    m = _minimal_manifest()
    m["documents"][0]["expectations"] = {}
    validate(m, "manifest.schema.json")


def test_validate_manifest_expectations_extra_field_rejected():
    m = _minimal_manifest()
    m["documents"][0]["expectations"] = {"unknown_key": 1}
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_expectations_element_count_by_type_negative_rejected():
    m = _minimal_manifest()
    m["documents"][0]["expectations"] = {
        "element_count_by_type": {"paragraph": -1}
    }
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_expectations_element_count_by_type_zero_accepts():
    m = _minimal_manifest()
    m["documents"][0]["expectations"] = {
        "element_count_by_type": {"paragraph": 0}
    }
    validate(m, "manifest.schema.json")


def test_validate_manifest_expectations_required_markers_empty_string_rejected():
    m = _minimal_manifest()
    m["documents"][0]["expectations"] = {
        "required_markers": [""]
    }
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_expected_failures_source_type_allows_txt():
    """expected_failure 的 source_type 允许 txt（与 document.source_type 不同）。"""
    m = _minimal_manifest()
    m["expected_failures"] = [
        {
            "doc_id": "fail1",
            "path": "samples/private/bad.txt",
            "expected_error_code": "unsupported_input_type",
            "source_type": "txt",
        }
    ]
    validate(m, "manifest.schema.json")


def test_validate_manifest_expected_failures_source_type_allows_other():
    m = _minimal_manifest()
    m["expected_failures"] = [
        {
            "doc_id": "fail1",
            "path": "samples/private/bad.xyz",
            "expected_error_code": "unsupported_input_type",
            "source_type": "other",
        }
    ]
    validate(m, "manifest.schema.json")


def test_validate_manifest_expected_failures_source_type_pdf_accepts():
    m = _minimal_manifest()
    m["expected_failures"] = [
        {
            "doc_id": "fail1",
            "path": "samples/private/bad.pdf",
            "expected_error_code": "parse_failed",
            "source_type": "pdf",
        }
    ]
    validate(m, "manifest.schema.json")


def test_validate_manifest_expected_failures_source_type_invalid_rejected():
    m = _minimal_manifest()
    m["expected_failures"] = [
        {
            "doc_id": "fail1",
            "path": "samples/private/bad.xyz",
            "expected_error_code": "parse_failed",
            "source_type": "html",  # 不在 enum
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


def test_validate_manifest_expected_failures_missing_code_rejected():
    m = _minimal_manifest()
    m["expected_failures"] = [
        {
            "doc_id": "fail1",
            "path": "samples/private/bad.pdf",
            "source_type": "pdf",
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")


# --- annotation 字段深度 ---


def test_validate_annotation_minimal_accepts():
    validate(_minimal_annotation(), "annotation.schema.json")


def test_validate_annotation_const_version_rejects_other():
    a = _minimal_annotation()
    a["annotation_version"] = "2.0"
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_empty_doc_id_rejected():
    a = _minimal_annotation()
    a["doc_id"] = ""
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_extra_top_level_rejected():
    a = _minimal_annotation()
    a["unknown"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_annotator_string_accepts():
    a = _minimal_annotation()
    a["annotator"] = "reviewer_a"
    validate(a, "annotation.schema.json")


def test_validate_annotation_annotator_non_string_rejected():
    a = _minimal_annotation()
    a["annotator"] = 5
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_date_string_accepts():
    a = _minimal_annotation()
    a["date"] = "2026-08-05"
    validate(a, "annotation.schema.json")


def test_validate_annotation_date_empty_rejected():
    a = _minimal_annotation()
    a["date"] = ""
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_valid():
    a = _minimal_annotation()
    a["figure_caption_pairs"] = [
        {"figure_marker": "Figure 1", "caption_text": "Caption A"}
    ]
    validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_missing_required():
    a = _minimal_annotation()
    a["figure_caption_pairs"] = [
        {"figure_marker": "Figure 1"}  # 缺 caption_text
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_extra_field():
    a = _minimal_annotation()
    a["figure_caption_pairs"] = [
        {"figure_marker": "Figure 1", "caption_text": "X", "extra": 1}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_figure_caption_pairs_empty_marker():
    a = _minimal_annotation()
    a["figure_caption_pairs"] = [
        {"figure_marker": "", "caption_text": "X"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_valid():
    a = _minimal_annotation()
    a["heading_order"] = [
        {"level": 1, "text": "Introduction"},
        {"level": 2, "text": "Background"},
    ]
    validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_level_zero_rejected():
    a = _minimal_annotation()
    a["heading_order"] = [{"level": 0, "text": "X"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_level_negative_rejected():
    a = _minimal_annotation()
    a["heading_order"] = [{"level": -1, "text": "X"}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_missing_text_rejected():
    a = _minimal_annotation()
    a["heading_order"] = [{"level": 1}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_empty_text_rejected():
    a = _minimal_annotation()
    a["heading_order"] = [{"level": 1, "text": ""}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_heading_order_extra_field_rejected():
    a = _minimal_annotation()
    a["heading_order"] = [{"level": 1, "text": "X", "extra": 0}]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_valid():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "abc", "position": "after"},
        {"marker": "xyz", "position": "before", "reason": "section break"},
    ]
    validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_invalid_position():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "abc", "position": "middle"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_empty_marker_rejected():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "", "position": "after"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_missing_marker_rejected():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"position": "after"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_missing_position_rejected():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "abc"}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


def test_validate_annotation_chunk_boundary_anchors_extra_field_rejected():
    a = _minimal_annotation()
    a["chunk_boundary_anchors"] = [
        {"marker": "abc", "position": "after", "weight": 0.5}
    ]
    with pytest.raises(EvalSchemaError):
        validate(a, "annotation.schema.json")


# --- evaluation-report 字段深度 ---


def test_validate_report_minimal_accepts():
    validate(_minimal_report(), "evaluation-report.schema.json")


def test_validate_report_const_version_rejects_other():
    r = _minimal_report()
    r["report_version"] = "1.0"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_extra_top_level_rejected():
    r = _minimal_report()
    r["unknown"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_missing_provenance_rejected():
    r = _minimal_report()
    del r["provenance"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_missing_field_rejected():
    r = _minimal_report()
    del r["provenance"]["git_commit"]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_extra_field_rejected():
    r = _minimal_report()
    r["provenance"]["extra"] = "x"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_git_dirty_must_be_bool():
    r = _minimal_report()
    r["provenance"]["git_dirty"] = "yes"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_max_chars_minimum_one():
    r = _minimal_report()
    r["provenance"]["max_chars"] = 0
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_max_chars_one_accepts():
    r = _minimal_report()
    r["provenance"]["max_chars"] = 1
    validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_max_chars_negative_rejected():
    r = _minimal_report()
    r["provenance"]["max_chars"] = -1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_dependencies_value_can_be_null():
    r = _minimal_report()
    r["provenance"]["dependencies"] = {"kreuzberg": None}
    validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_dependencies_value_can_be_string():
    r = _minimal_report()
    r["provenance"]["dependencies"] = {"kreuzberg": "4.10.2"}
    validate(r, "evaluation-report.schema.json")


def test_validate_report_provenance_dependencies_value_non_string_non_null_rejected():
    r = _minimal_report()
    r["provenance"]["dependencies"] = {"kreuzberg": 5}
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_devset_status_enum():
    r = _minimal_report()
    r["devset"]["status"] = "pending"
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_devset_negative_file_count_rejected():
    r = _minimal_report()
    r["devset"]["file_count"] = -1
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_devset_zero_file_count_accepts():
    r = _minimal_report()
    r["devset"]["file_count"] = 0
    validate(r, "evaluation-report.schema.json")


def test_validate_report_devset_extra_field_rejected():
    r = _minimal_report()
    r["devset"]["extra"] = 0
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_summary_additional_properties_allowed():
    """summary 显式允许 additionalProperties:true。"""
    r = _minimal_report()
    r["summary"]["custom_aggregate"] = {"x": 1}
    validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_empty_array_accepts():
    r = _minimal_report()
    r["per_doc"] = []
    validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_minimal_entry_accepts():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.5,
                "parse": None,
                "chunk": None,
            },
        }
    ]
    validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_missing_wall_time_rejected():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_wall_time_missing_total_rejected():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "parse": None,
                "chunk": None,
            },
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_wall_time_negative_total_rejected():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": -0.1,
                "parse": None,
                "chunk": None,
            },
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_wall_time_total_null_accepts():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": None,
                "parse": None,
                "chunk": None,
            },
        }
    ]
    validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_wall_time_with_reasons_accepts():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.5,
                "parse": None,
                "chunk": None,
                "parse_reason": "not_instrumented",
                "chunk_reason": "not_instrumented",
            },
        }
    ]
    validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_source_type_invalid_rejected():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "d1",
            "source_type": "html",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.5,
                "parse": None,
                "chunk": None,
            },
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_per_doc_empty_doc_id_rejected():
    r = _minimal_report()
    r["per_doc"] = [
        {
            "doc_id": "",
            "source_type": "pdf",
            "metrics": {},
            "wall_time_seconds": {
                "total": 0.5,
                "parse": None,
                "chunk": None,
            },
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_expected_failure_result_valid():
    r = _minimal_report()
    r["expected_failures"] = [
        {
            "doc_id": "fail1",
            "expected_error_code": "unsupported_input_type",
            "actual_error_code": "unsupported_input_type",
            "matches": True,
        }
    ]
    validate(r, "evaluation-report.schema.json")


def test_validate_report_expected_failure_result_actual_null_accepts():
    r = _minimal_report()
    r["expected_failures"] = [
        {
            "doc_id": "fail1",
            "expected_error_code": "unsupported_input_type",
            "actual_error_code": None,
            "matches": False,
        }
    ]
    validate(r, "evaluation-report.schema.json")


def test_validate_report_expected_failure_result_missing_matches_rejected():
    r = _minimal_report()
    r["expected_failures"] = [
        {
            "doc_id": "fail1",
            "expected_error_code": "unsupported_input_type",
            "actual_error_code": None,
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


def test_validate_report_expected_failure_result_matches_non_bool_rejected():
    r = _minimal_report()
    r["expected_failures"] = [
        {
            "doc_id": "fail1",
            "expected_error_code": "unsupported_input_type",
            "actual_error_code": None,
            "matches": "true",
        }
    ]
    with pytest.raises(EvalSchemaError):
        validate(r, "evaluation-report.schema.json")


# =============================================================================
# validate — 算法与不变量
# =============================================================================


def test_validate_returns_none_on_success():
    assert validate(_minimal_manifest(), "manifest.schema.json") is None


def test_validate_does_not_mutate_instance_on_success():
    m = _minimal_manifest()
    import copy
    before = copy.deepcopy(m)
    validate(m, "manifest.schema.json")
    assert m == before


def test_validate_does_not_mutate_instance_on_failure():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    import copy
    before = copy.deepcopy(m)
    with pytest.raises(EvalSchemaError):
        validate(m, "manifest.schema.json")
    assert m == before


def test_validate_failure_message_contains_schema_name():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_failure_message_contains_error_count():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert "1 处" in str(exc.value)


def test_validate_failure_multiple_errors_count_correct():
    """构造多个错误，验证消息中"X 处"的计数。"""
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    m["devset_status"] = "invalid"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert "2 处" in str(exc.value)


def test_validate_failure_errors_is_list():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert isinstance(exc.value.errors, list)


def test_validate_failure_each_error_has_three_keys():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_failure_path_is_list():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert isinstance(exc.value.errors[0]["path"], list)


def test_validate_failure_schema_path_is_list():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert isinstance(exc.value.errors[0]["schema_path"], list)


def test_validate_failure_message_is_string():
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    with pytest.raises(EvalSchemaError) as exc:
        validate(m, "manifest.schema.json")
    assert isinstance(exc.value.errors[0]["message"], str)


def test_validate_empty_dict_instance_fails_manifest():
    """空 dict 缺所有 required 字段。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_non_dict_instance_list_rejected_by_jsonschema():
    """list 实例不符合 type:object。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_validate_non_dict_instance_none_rejected_by_jsonschema():
    """None 实例不符合 type:object。"""
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")


def test_validate_non_dict_instance_string_rejected_by_jsonschema():
    with pytest.raises(EvalSchemaError):
        validate("string", "manifest.schema.json")


def test_validate_unknown_schema_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_empty_dict_instance_fails_annotation():
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_empty_dict_instance_fails_report():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


# =============================================================================
# validate_file 函数深度
# =============================================================================


def test_validate_file_str_path_accepts(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_pathlib_path_accepts(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound(tmp_path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path):
    """目录 not is_file → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_empty_file_raises_jsondecodeerror(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error(tmp_path):
    p = tmp_path / "bad.json"
    m = _minimal_manifest()
    m["manifest_version"] = "2.0"
    p.write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_returns_none_on_success(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_unknown_schema_raises_filenotfound(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_with_unicode_content(tmp_path):
    m = _minimal_manifest()
    m["documents"][0]["doc_id"] = "测试文档"
    p = tmp_path / "unicode.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_with_bom(tmp_path):
    """UTF-8 BOM 应能被 json.load 处理（encoding='utf-8' 不去 BOM，但 JSON 解析允许多余空白？）。

    实际上 json.load 对 BOM 不容忍；但 _minimal_manifest 是合法 JSON，BOM 会触发
    JSONDecodeError。本测试验证：含 BOM 的文件不通过 json.load。
    """
    p = tmp_path / "bom.json"
    content = json.dumps(_minimal_manifest()).encode("utf-8")
    p.write_bytes(b"\xef\xbb\xbf" + content)
    # 实际行为：json.JSONDecoder 对 BOM 报错
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unicode_filename(tmp_path):
    p = tmp_path / "测试.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_nested_directory_path(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    p = nested / "valid.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


# =============================================================================
# EvalSchemaError 类深度
# =============================================================================


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_default_errors_empty_list():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_errors_none_becomes_empty_list():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_passed_through():
    errs = [{"path": [], "message": "x", "schema_path": []}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors is errs


def test_eval_schema_error_message_attribute():
    e = EvalSchemaError("hello")
    assert str(e) == "hello"


def test_eval_schema_error_args_stored():
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("msg")


def test_eval_schema_error_caught_as_exception():
    try:
        raise EvalSchemaError("msg")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_caught_does_not_leak_to_value_error():
    with pytest.raises(EvalSchemaError):
        try:
            raise EvalSchemaError("msg")
        except ValueError:
            pytest.fail("EvalSchemaError should not be ValueError")


def test_eval_schema_error_errors_attribute_writable():
    e = EvalSchemaError("msg")
    e.errors = [{"x": 1}]
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_repr_contains_class_name():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


# =============================================================================
# __all__ 与模块结构
# =============================================================================


def test_all_is_list():
    assert isinstance(schema_all, list)


def test_all_contains_five_items():
    assert len(schema_all) == 5


def test_all_exact_set():
    assert set(schema_all) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_all_match_module_attributes():
    for name in schema_all:
        assert hasattr(eval_schema, name)


def test_all_items_not_internal():
    """__all__ 不含下划线前缀的内部名字。"""
    for name in schema_all:
        assert not name.startswith("_")


def test_module_internal_schema_path_exists():
    """_schema_path 是内部函数，存在但不在 __all__。"""
    assert hasattr(eval_schema, "_schema_path")
    assert "_schema_path" not in schema_all


def test_module_imports_draft202012_validator():
    """模块从 jsonschema 引入 Draft202012Validator。"""
    assert hasattr(eval_schema, "Draft202012Validator")
    assert eval_schema.Draft202012Validator is Draft202012Validator


def test_module_imports_json_module():
    import evaluation.schema as es
    assert hasattr(es, "json")


def test_module_imports_path_class():
    assert hasattr(eval_schema, "Path")


def test_module_scemas_dir_constant_in_all():
    assert "SCHEMAS_DIR" in schema_all


def test_module_callable_signatures():
    import inspect
    assert callable(load_schema)
    assert callable(validate)
    assert callable(validate_file)
    assert callable(_schema_path)


def test_load_schema_signature_one_param():
    import inspect
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_validate_signature_two_params():
    import inspect
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_file_signature_two_params():
    import inspect
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_schema_path_signature_one_param():
    import inspect
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]
