"""evaluation/schema.py 与 evaluation/schema_validation.py 的单元测试。

这两个模块与 app/schema.py 不同：
- app/schema.py：业务 Document 模型校验（document.schema.json）
- evaluation/schema.py：评测元数据校验（manifest/annotation/evaluation-report）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)
from evaluation.schema_validation import document_passes_schema


# ---------- load_schema ----------


def test_load_schema_returns_dict_for_each_known_schema():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert s["$id"].endswith(name)
        assert "title" in s


def test_load_schema_missing_raises():
    with pytest.raises(FileNotFoundError) as exc:
        load_schema("does-not-exist.schema.json")
    assert "Schema" in str(exc.value) or "schema" in str(exc.value).lower()


def test_schemas_dir_constant_points_to_project_schemas():
    assert SCHEMAS_DIR.is_dir()
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


# ---------- validate (manifest) ----------


def _valid_manifest() -> dict:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "DC-1", "path": "samples/x.docx", "source_type": "docx"}
        ],
    }


def test_validate_manifest_passes_silently():
    """validate 在合法时返回 None（不抛异常）。"""
    assert validate(_valid_manifest(), "manifest.schema.json") is None


def test_validate_manifest_invalid_returns_error_with_details():
    bad = _valid_manifest()
    bad["manifest_version"] = "9.9"  # const 不符
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    # message 包含 schema 名与错误数
    msg = str(exc.value)
    assert "manifest.schema.json" in msg
    # errors 列表非空
    assert len(exc.value.errors) >= 1
    err0 = exc.value.errors[0]
    assert "path" in err0
    assert "message" in err0
    assert "schema_path" in err0


def test_validate_collects_multiple_errors():
    """同时有多个错误时，errors 列表应包含多个项。"""
    bad = {
        "manifest_version": "9.9",  # const 不符
        "devset_status": "bad-status",  # enum 不符
        "documents": "should-be-array",  # type 不符
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    assert len(exc.value.errors) >= 3


# ---------- validate (annotation) ----------


def _valid_annotation() -> dict:
    return {
        "annotation_version": "1.0",
        "doc_id": "DC-1",
        "annotator": "initials",
        "chunk_boundary_anchors": [
            {"marker": "Section 1", "position": "after", "reason": "test"},
        ],
    }


def test_validate_annotation_passes():
    validate(_valid_annotation(), "annotation.schema.json")


def test_validate_annotation_invalid_position_rejected():
    bad = _valid_annotation()
    bad["chunk_boundary_anchors"][0]["position"] = "wrong"
    with pytest.raises(EvalSchemaError):
        validate(bad, "annotation.schema.json")


def test_validate_annotation_marker_min_length():
    bad = _valid_annotation()
    bad["chunk_boundary_anchors"][0]["marker"] = ""
    with pytest.raises(EvalSchemaError):
        validate(bad, "annotation.schema.json")


def test_validate_annotation_top_level_extra_field_rejected():
    bad = _valid_annotation()
    bad["unknown_field"] = "disallowed"
    with pytest.raises(EvalSchemaError):
        validate(bad, "annotation.schema.json")


def test_validate_annotation_missing_required_doc_id():
    bad = _valid_annotation()
    del bad["doc_id"]
    with pytest.raises(EvalSchemaError):
        validate(bad, "annotation.schema.json")


# ---------- validate (evaluation-report) ----------


def _valid_report() -> dict:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc1234",
            "git_dirty": False,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": "1.0",
            "dependencies": {"python": "3.12.10"},
            "max_chars": 800,
            "run_timestamp_iso": "2026-08-04T12:00:00Z",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 1,
            "content_group_count": 1,
            "pdf_count": 0,
            "docx_count": 1,
            "categories_covered": ["report"],
        },
        "summary": {},
        "per_doc": [],
    }


def test_validate_report_passes():
    validate(_valid_report(), "evaluation-report.schema.json")


def test_validate_report_wrong_version_rejected():
    bad = _valid_report()
    bad["report_version"] = "9.9"
    with pytest.raises(EvalSchemaError):
        validate(bad, "evaluation-report.schema.json")


def test_validate_report_missing_required_field_rejected():
    bad = _valid_report()
    del bad["provenance"]
    with pytest.raises(EvalSchemaError):
        validate(bad, "evaluation-report.schema.json")


def test_validate_report_missing_provenance_subfield_rejected():
    bad = _valid_report()
    del bad["provenance"]["git_dirty"]
    with pytest.raises(EvalSchemaError):
        validate(bad, "evaluation-report.schema.json")


# ---------- validate_file ----------


def test_validate_file_accepts_valid(tmp_path: Path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_missing_raises():
    with pytest.raises(FileNotFoundError):
        validate_file("/tmp/does-not-exist-manifest.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises():
    """非法 JSON → json.JSONDecodeError（未在 validate_file 内捕获）。"""
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        f.write("{not valid json")
        path = f.name
    with pytest.raises(json.JSONDecodeError):
        validate_file(path, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_accepts_str_path(tmp_path: Path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(_valid_manifest()), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # 不抛


# ---------- document_passes_schema (schema_validation) ----------


def _valid_document_dict() -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [
            {
                "element_id": "e1",
                "type": "paragraph",
                "content": "hi",
                "parent_id": None,
                "source_locator": {"paragraph_index": 0},
                "confidence": 1.0,
                "metadata": {},
            }
        ],
        "chunks": [
            {"chunk_id": "c1", "text": "hi", "source_element_ids": ["e1"], "metadata": {}}
        ],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_document_passes_schema_returns_true_for_valid():
    assert document_passes_schema(_valid_document_dict()) is True


def test_document_passes_schema_returns_false_for_invalid():
    bad = _valid_document_dict()
    del bad["source_hash"]
    assert document_passes_schema(bad) is False


def test_document_passes_schema_returns_bool_type():
    """返回值是 bool 而不是 None / truthy。"""
    result = document_passes_schema(_valid_document_dict())
    assert isinstance(result, bool)


def test_document_passes_schema_rejects_wrong_schema_version():
    bad = _valid_document_dict()
    bad["schema_version"] = "9.9"
    assert document_passes_schema(bad) is False


def test_document_passes_schema_rejects_element_missing_required():
    bad = _valid_document_dict()
    # 删 element 必填字段
    del bad["elements"][0]["element_id"]
    assert document_passes_schema(bad) is False
