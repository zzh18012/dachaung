"""evaluation/schema.py 第五十轮 edges 测试（Round 544）。

补强 edges49 未触及的角度（第三十批）。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 第三十批 ----------


def test_eval_schema_error_default_errors_is_empty_list_batch30():
    e = EvalSchemaError("msg")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_explicit_none_errors_batch30():
    e = EvalSchemaError("msg", None)
    assert e.errors == []


def test_eval_schema_error_str_repr_batch30():
    e = EvalSchemaError("hello")
    assert str(e) == "hello"
    assert repr(e).startswith("EvalSchemaError")


def test_eval_schema_error_inherits_exception_batch30():
    e = EvalSchemaError("msg")
    assert isinstance(e, Exception)


def test_eval_schema_error_can_be_raised_and_caught_batch30():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("boom")
    assert str(exc.value) == "boom"


def test_eval_schema_error_errors_attribute_set_batch30():
    e = EvalSchemaError("msg", [{"x": 1}])
    assert hasattr(e, "errors")
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_super_init_called_batch30():
    """args 包含 message（super().__init__ 调用）。"""
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_multiple_errors_independent_batch30():
    e1 = EvalSchemaError("m1")
    e2 = EvalSchemaError("m2")
    e1.errors.append({"x": 1})
    assert e2.errors == []


# ---------- _schema_path 第三十批 ----------


def test_schema_path_returns_path_batch30():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_nonexistent_raises_filenotfound_batch30():
    with pytest.raises(FileNotFoundError):
        _schema_path("definitely_nonexistent_xyz.json")


def test_schema_path_message_contains_filename_batch30():
    try:
        _schema_path("nonexistent_schema_xxxx.json")
    except FileNotFoundError as e:
        assert "nonexistent_schema_xxxx.json" in str(e)
        return
    pytest.fail("Expected FileNotFoundError")


def test_schema_path_with_subdir_batch30():
    """name 含 / → 走 SCHEMAS_DIR 子目录（不存在 → FileNotFoundError）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.json")


def test_schema_path_call_idempotent_batch30():
    """两次调用返回相同 Path 对象（值等价）。"""
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


# ---------- load_schema 第三十批 ----------


def test_load_schema_returns_dict_batch30():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_required_key_batch30():
    s = load_schema("manifest.schema.json")
    assert "required" in s


def test_load_schema_annotation_has_required_key_batch30():
    s = load_schema("annotation.schema.json")
    assert "required" in s


def test_load_schema_evaluation_report_has_required_key_batch30():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


def test_load_schema_idempotent_batch30():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # 内容相同
    assert s1 == s2


def test_load_schema_nonexistent_raises_filenotfound_batch30():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent_xyz.json")


def test_load_schema_modification_isolated_batch30():
    """两次加载返回独立 dict。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    s1["_hack"] = True
    assert "_hack" not in s2


# ---------- validate 第三十批 ----------


def test_validate_empty_dict_for_manifest_batch30():
    """空 dict 校验 manifest → 抛 EvalSchemaError 含 errors。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_returns_none_on_success_batch30():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_message_contains_schema_name_batch30():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_message_contains_error_count_batch30():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert "处" in msg


def test_validate_errors_sorted_by_path_batch30():
    """errors 已按 path 排序。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc.value.errors]
    assert paths == sorted(paths)


def test_validate_with_unknown_top_key_batch30():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "extra_unknown_field": True,
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_errors_each_has_path_message_schema_path_batch30():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_with_invalid_manifest_version_batch30():
    instance = {
        "manifest_version": "999.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_with_invalid_devset_status_batch30():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "weird",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_annotation_minimum_passes_batch30():
    annotation = {"annotation_version": "1.0", "doc_id": "d1"}
    assert validate(annotation, "annotation.schema.json") is None


def test_validate_annotation_missing_doc_id_fails_batch30():
    annotation = {"annotation_version": "1.0"}
    with pytest.raises(EvalSchemaError):
        validate(annotation, "annotation.schema.json")


def test_validate_evaluation_report_empty_fails_batch30():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


# ---------- validate_file 第三十批 ----------


def test_validate_file_valid_manifest_batch30(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_path_string_batch30(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    # 字符串 path 等价 Path
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_nonexistent_raises_filenotfound_batch30(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nonexistent.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound_batch30(tmp_path):
    """目录也 → FileNotFoundError（is_file=False）。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch30(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{not json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error_batch30(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_no_modification_batch30(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    content = json.dumps(instance)
    p = tmp_path / "m.json"
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


def test_validate_file_idempotent_batch30(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_validate_file_large_manifest_batch30(tmp_path):
    """大 manifest 不抛（合法时）。"""
    docs = [
        {
            "doc_id": f"d{i}",
            "path": f"samples/{i}.pdf",
            "source_type": "pdf",
            "sha256": "a" * 64,
        }
        for i in range(50)
    ]
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": docs,
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_annotation_batch30(tmp_path):
    annotation = {"annotation_version": "1.0", "doc_id": "d1"}
    p = tmp_path / "a.json"
    p.write_text(json.dumps(annotation), encoding="utf-8")
    assert validate_file(p, "annotation.schema.json") is None


# ---------- module source forbidden tokens 第四十八批 ----------


def test_module_source_no_subprocess_batch30():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_os_system_batch30():
    src = inspect.getsource(smod)
    assert "os.system" not in src


def test_module_source_no_eval_batch30():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec_batch30():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_pickle_batch30():
    src = inspect.getsource(smod)
    assert "pickle" not in src


def test_module_source_no_yaml_batch30():
    src = inspect.getsource(smod)
    assert "yaml" not in src


def test_module_source_no_dunder_import_batch30():
    src = inspect.getsource(smod)
    assert "__import__" not in src


def test_module_source_no_breakpoint_batch30():
    src = inspect.getsource(smod)
    assert "breakpoint(" not in src


def test_module_source_no_shutil_batch30():
    src = inspect.getsource(smod)
    assert "shutil" not in src


def test_module_source_no_requests_batch30():
    src = inspect.getsource(smod)
    assert "requests" not in src


def test_module_source_no_open_w_mode_batch30():
    src = inspect.getsource(smod)
    assert "'w'" not in src
    assert '"w"' not in src


def test_module_source_no_unlink_batch30():
    src = inspect.getsource(smod)
    assert ".unlink()" not in src


# ---------- module source 字符串精确补强第四十四批 ----------


def test_module_source_contains_module_docstring_batch30():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_schemas_dir_assignment_batch30():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_resolve_call_batch30():
    src = inspect.getsource(smod)
    assert ".resolve()" in src


def test_module_source_contains_schema_path_func_batch30():
    src = inspect.getsource(smod)
    assert "def _schema_path" in src


def test_module_source_contains_eval_schema_error_class_batch30():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_load_schema_func_batch30():
    src = inspect.getsource(smod)
    assert "def load_schema" in src


def test_module_source_contains_validate_func_batch30():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_func_batch30():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_utf_8_encoding_batch30():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_draft_2020_12_batch30():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_call_batch30():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_call_batch30():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_call_batch30():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_no_app_schema_reuse_doc_batch30():
    src = inspect.getsource(smod)
    assert "不与 app/schema.py 复用" in src


def test_module_source_contains_errors_or_empty_default_batch30():
    src = inspect.getsource(smod)
    assert "errors or []" in src


def test_module_source_contains_sorted_call_batch30():
    src = inspect.getsource(smod)
    assert "sorted" in src


# ---------- signatures 第四十四批 ----------


def test_signature_eval_schema_error_init_full_batch30():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_return_none_batch30():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_message_str_batch30():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].annotation == "str"


def test_signature_eval_schema_error_errors_default_none_batch30():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_signature_eval_schema_error_errors_optional_list_batch30():
    sig = inspect.signature(EvalSchemaError.__init__)
    ps = str(sig.parameters["errors"].annotation)
    assert "list" in ps and "None" in ps


def test_signature_schema_path_batch30():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch30():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch30():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch30():
    sig = inspect.signature(validate_file)
    assert "Path" in str(sig.parameters["path"].annotation)
    assert "str" in str(sig.parameters["path"].annotation)
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


# ---------- module 合理性第四十四批 ----------


def test_module_has_future_annotations_batch30():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_json_batch30():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_pathlib_batch30():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_typing_any_batch30():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_imports_draft_validator_batch30():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_batch30():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_schemas_dir_absolute_batch30():
    assert SCHEMAS_DIR.is_absolute()


def test_module_no_main_block_batch30():
    src = inspect.getsource(smod)
    assert 'if __name__ == "__main__"' not in src


def test_module_all_has_five_entries_batch30():
    src = inspect.getsource(smod)
    for name in [
        '"SCHEMAS_DIR"',
        '"EvalSchemaError"',
        '"load_schema"',
        '"validate"',
        '"validate_file"',
    ]:
        assert name in src


# ---------- 端到端集成第四十四批 ----------


def test_e2e_validate_full_manifest_roundtrip_batch30(tmp_path):
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {"doc_id": "d1", "path": "x.pdf", "source_type": "pdf", "sha256": "a" * 64}
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_three_schemas_exist_batch30():
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


def test_e2e_eval_schema_error_caught_batch30():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_errors_complete_batch30():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)


def test_e2e_schemas_dir_in_project_batch30():
    project_root = Path(__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == project_root


def test_e2e_validate_idempotent_batch30():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e1:
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError as e2:
            assert str(e1) == str(e2)
            assert e1.errors == e2.errors
            return
    pytest.fail("Expected EvalSchemaError")


def test_e2e_validate_with_valid_annotation_batch30():
    annotation = {"annotation_version": "1.0", "doc_id": "d1"}
    validate(annotation, "annotation.schema.json")


def test_e2e_validate_with_valid_evaluation_report_batch30(tmp_path):
    """端到端：合法 evaluation-report 通过校验。"""
    # minimal valid evaluation-report based on schema
    report = {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {},
        "per_doc": [],
        "expected_failures": [],
    }
    validate(report, "evaluation-report.schema.json")
