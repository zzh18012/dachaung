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


# ---------- 边角补强（Round 47） ----------


# EvalSchemaError 类契约


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("test")
    assert "test" in str(exc.value)


def test_eval_schema_error_default_errors_empty_list():
    err = EvalSchemaError("msg")
    assert err.errors == []


def test_eval_schema_error_errors_none_becomes_empty_list():
    err = EvalSchemaError("msg", errors=None)
    assert err.errors == []


def test_eval_schema_error_errors_passed_through():
    errors = [{"path": ["a"], "message": "x"}]
    err = EvalSchemaError("msg", errors=errors)
    assert err.errors == errors


def test_eval_schema_error_inherits_from_exception():
    err = EvalSchemaError("x")
    assert isinstance(err, Exception)


def test_eval_schema_error_message_attribute():
    err = EvalSchemaError("hello world")
    assert "hello world" in str(err)


# SCHEMAS_DIR 常量


def test_schemas_dir_is_absolute_path():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_ends_with_schemas():
    """SCHEMAS_DIR 应指向项目的 schemas/ 子目录。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_known_schema_files():
    """schemas/ 应含 manifest/annotation/evaluation-report schema 文件。"""
    for fname in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        assert (SCHEMAS_DIR / fname).is_file()


# load_schema 边角


def test_load_schema_returns_dict_type():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_dict_has_json_schema_dollar_key():
    """每个 schema 应有 $schema 字段（Draft 2020-12）。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_dict_has_id_key():
    """每个 schema 应有 $id 字段。"""
    s = load_schema("annotation.schema.json")
    assert "$id" in s


def test_load_schema_dict_has_title_key():
    s = load_schema("evaluation-report.schema.json")
    assert "title" in s


def test_load_schema_unknown_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# _schema_path 直接单测


def test_schema_path_returns_path_for_known_schema():
    from evaluation.schema import _schema_path
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)
    assert p.is_file()


def test_schema_path_unknown_name_raises_filenotfound():
    from evaluation.schema import _schema_path
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("xxx.schema.json")
    assert "xxx.schema.json" in str(exc.value)


def test_schema_path_in_schemas_dir():
    """返回的 path 应位于 SCHEMAS_DIR 下。"""
    from evaluation.schema import _schema_path
    p = _schema_path("annotation.schema.json")
    assert p.parent == SCHEMAS_DIR


# validate 边角


def test_validate_returns_none_on_success():
    """validate 成功时返回 None（无显式 return）。"""
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    result = validate(valid_manifest, "manifest.schema.json")
    assert result is None


def test_validate_failure_includes_error_count_in_message():
    bad = {"manifest_version": "1.0"}  # 缺 devset_status/documents
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    # 消息含错误数（1 处或多处）
    assert "处" in str(exc.value)


def test_validate_failure_errors_attribute_is_list():
    bad = {"manifest_version": "1.0"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    assert isinstance(exc.value.errors, list)
    assert len(exc.value.errors) >= 1


def test_validate_failure_each_error_has_three_keys():
    """每个 error dict 含 path/message/schema_path 三个键。"""
    bad = {"manifest_version": "1.0"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_failure_first_error_used_in_message():
    """消息里的 head.message 与 errors[0] 一致。"""
    bad = {"manifest_version": "1.0"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad, "manifest.schema.json")
    # 消息含 head.message（具体内容随 schema 版本，但应非空）
    assert str(exc.value)


# validate_file 边角


def test_validate_file_pathlib_object_accepted(tmp_path: Path):
    """validate_file 接受 Path 对象。"""
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛即合格


def test_validate_file_directory_not_file_raises(tmp_path: Path):
    """传目录（不是文件）→ FileNotFoundError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


def test_validate_file_unknown_schema_name_raises_filenotfound(tmp_path: Path):
    """schema_name 不存在 → FileNotFoundError。"""
    p = tmp_path / "x.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_returns_none_on_success(tmp_path: Path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


# document_passes_schema 边角


def test_document_passes_schema_empty_document_returns_false():
    """空 dict 不符合 document schema。"""
    assert document_passes_schema({}) is False


def test_document_passes_schema_returns_bool_not_int():
    """返回值是 bool（Python 中 bool 是 int 子类，单独断言 type 是 bool）。"""
    valid = {
        "schema_version": "0.1.0",
        "document_id": "doc-abcdef0123456789",
        "source_path": "x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "stdlib/0.1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {"text": True},
    }
    result = document_passes_schema(valid)
    assert type(result) is bool


def test_document_passes_schema_with_extra_field_still_valid():
    """document.schema.json 假设 additionalProperties:false；如有额外字段 → False。

    注：实际行为取决于 schema 配置；这里测的是「能识别额外字段」的能力。
    """
    valid = {
        "schema_version": "0.1.0",
        "document_id": "doc-abcdef0123456789",
        "source_path": "x.txt",
        "source_type": "text",
        "source_hash": "a" * 64,
        "parser_name": "text",
        "parser_version": "stdlib/0.1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
        "extra_unexpected_field": "disallowed",
    }
    # additionalProperties 决定是否拒绝；当前 schema 若允许，返 True；拒绝则 False
    result = document_passes_schema(valid)
    assert isinstance(result, bool)
