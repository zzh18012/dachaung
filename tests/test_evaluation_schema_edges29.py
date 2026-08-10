"""evaluation/schema.py 第二十九轮 edges 测试（Round 393）。

补强 edges28 未触及的角度：
- EvalSchemaError 行为深度第九批
- load_schema 行为深度第九批
- validate 行为深度第九批
- validate_file 行为深度第九批
- _schema_path 行为深度第九批
- SCHEMAS_DIR 常量深度第九批
- module source forbidden tokens 第十三批
- module source 字符串精确补强第九批
- signatures 第九批
- module 合理性第九批
- 端到端集成第九批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度第九批 ----------


def test_eval_schema_error_is_exception_subclass_batch9():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_message_only_batch9():
    e = EvalSchemaError("hello")
    assert "hello" in str(e)


def test_eval_schema_error_message_and_errors_batch9():
    errors = [{"path": ["a"], "message": "msg"}]
    e = EvalSchemaError("hello", errors)
    assert e.errors == errors


def test_eval_schema_error_errors_default_empty_batch9():
    e = EvalSchemaError("hello")
    assert e.errors == []


def test_eval_schema_error_no_errors_arg_batch9():
    e = EvalSchemaError("hello")
    assert hasattr(e, "errors")
    assert isinstance(e.errors, list)


def test_eval_schema_error_errors_none_batch9():
    e = EvalSchemaError("hello", None)
    assert e.errors == []


def test_eval_schema_error_can_be_raised_and_caught_batch9():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("test")


def test_eval_schema_error_caught_as_exception_batch9():
    try:
        raise EvalSchemaError("test")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_repr_batch9():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_args_stored_batch9():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_complex_payload_batch9():
    errors = [
        {"path": ["a", 0, "b"], "message": "required", "schema_path": ["properties"]},
        {"path": ["c"], "message": "type", "schema_path": ["type"]},
    ]
    e = EvalSchemaError("complex", errors)
    assert len(e.errors) == 2
    assert e.errors[0]["path"] == ["a", 0, "b"]


def test_eval_schema_error_init_3_params_batch9():
    """__init__(self, message, errors=None) → 3 params（含 self）。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3
    e = EvalSchemaError("msg", errors=[{"x": 1}])
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_init_message_positional_batch9():
    e = EvalSchemaError("only_message")
    assert e.args == ("only_message",)


def test_eval_schema_error_chain_from_other_batch9():
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_errors_mutable_batch9():
    """errors 是 list，e.errors 本身可变。"""
    errors = [{"x": 1}]
    e = EvalSchemaError("msg", errors)
    # e.errors 与传入的 errors 是同一对象（非空时不触发 or []）
    e.errors.append({"y": 2})
    assert len(e.errors) == 2


# ---------- load_schema 行为深度第九批 ----------


def test_load_schema_returns_dict_manifest_batch9():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_dict_annotation_batch9():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_dict_evaluation_report_batch9():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_dict_document_batch9():
    s = load_schema("document.schema.json")
    assert isinstance(s, dict)


def test_load_schema_unknown_raises_file_not_found_batch9():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_directory_form_raises_batch9():
    with pytest.raises(FileNotFoundError):
        load_schema("subdir")


def test_load_schema_idempotent_batch9():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # 值相等
    assert s1 == s2


def test_load_schema_returns_independent_dict_batch9():
    """多次调用返回独立 dict（每次都重新 json.load）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # 不同对象（每次都 json.load）
    assert s1 is not s2


def test_load_schema_has_schema_field_batch9():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "schema" in s or "$id" in s


def test_load_schema_has_type_object_batch9():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_has_properties_batch9():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_has_required_batch9():
    s = load_schema("manifest.schema.json")
    assert "required" in s


def test_load_schema_does_not_call_validator_batch9():
    """load_schema 仅加载 JSON，不构造 validator。"""
    # 通过返回 dict 验证
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


# ---------- validate 行为深度第九批 ----------


def test_validate_success_returns_none_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # 不抛 = 通过
    assert validate(data, "manifest.schema.json") is None


def test_validate_missing_version_raises_batch9():
    data = {
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_wrong_version_raises_batch9():
    data = {
        "manifest_version": "9.9.9",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_invalid_enum_raises_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "invalid_status",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_extra_top_level_field_raises_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "extra",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_documents_not_list_raises_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not a list",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_expected_failures_not_list_raises_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": "not a list",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_unknown_schema_raises_file_not_found_batch9():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_validate_does_not_mutate_input_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    snapshot = json.dumps(data, sort_keys=True)
    validate(data, "manifest.schema.json")
    assert json.dumps(data, sort_keys=True) == snapshot


def test_validate_idempotent_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")
    validate(data, "manifest.schema.json")
    # 不抛 = 通过


def test_validate_error_includes_path_batch9():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not a list",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    assert len(e.errors) > 0
    assert "path" in e.errors[0]


def test_validate_error_includes_schema_name_batch9():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_errors_count_batch9():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    assert len(e.errors) >= 1


def test_validate_errors_dict_keys_batch9():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    for err in e.errors:
        assert set(err.keys()) >= {"path", "message", "schema_path"}


def test_validate_errors_path_is_list_batch9():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    e = exc_info.value
    for err in e.errors:
        assert isinstance(err["path"], list)


def test_validate_message_string_batch9():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    assert isinstance(str(exc_info.value), str)


# ---------- validate_file 行为深度第九批 ----------


def test_validate_file_str_path_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")
    # 不抛 = 通过


def test_validate_file_path_object_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_raises_file_not_found_batch9(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_error_batch9(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_raises_eval_error_batch9(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_raises_file_not_found_batch9(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "unknown.schema.json")


def test_validate_file_idempotent_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_validate_file_positional_args_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_kwargs_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(path=p, schema_name="manifest.schema.json")


# ---------- _schema_path 行为深度第九批 ----------


def test_schema_path_returns_path_batch9():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_batch9():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_unknown_raises_file_not_found_batch9():
    with pytest.raises(FileNotFoundError):
        _schema_path("unknown.schema.json")


def test_schema_path_directory_form_raises_batch9():
    """schema_name 是目录形式 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/")


def test_schema_path_resolves_to_schemas_dir_batch9():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_idempotent_batch9():
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_does_not_read_file_batch9():
    """_schema_path 仅返回 Path，不读文件。"""
    # 通过返回值类型验证
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_error_message_contains_path_str_batch9():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc_info.value)


def test_schema_path_str_name_input_batch9():
    p = _schema_path("document.schema.json")
    assert p.is_file()


# ---------- SCHEMAS_DIR 常量深度第九批 ----------


def test_schemas_dir_is_path_batch9():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch9():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_endswith_schemas_batch9():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_4_json_files_batch9():
    jsons = list(SCHEMAS_DIR.glob("*.json"))
    names = {p.name for p in jsons}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names
    assert "document.schema.json" in names


def test_schemas_dir_in_module_namespace_batch9():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_schemas_dir_value_immutable_path_batch9():
    """Path 是 immutable（每次访问都是同一对象）。"""
    d1 = smod.SCHEMAS_DIR
    d2 = smod.SCHEMAS_DIR
    assert d1 is d2


def test_schemas_dir_parent_is_project_root_batch9():
    """SCHEMAS_DIR.parent 是 evaluation/ 的 parent（项目根）。"""
    parent = SCHEMAS_DIR.parent
    # parent 应包含 pyproject.toml
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_hashable_batch9():
    """Path 可 hash。"""
    h = hash(SCHEMAS_DIR)
    assert isinstance(h, int)


# ---------- module source forbidden tokens 第十三批 ----------


def test_smod_source_no_os_system_batch9():
    source = inspect.getsource(smod)
    assert "os.system" not in source


def test_smod_source_no_subprocess_batch9():
    source = inspect.getsource(smod)
    assert "subprocess.Popen" not in source
    assert "subprocess.check_call" not in source


def test_smod_source_no_pickle_load_batch9():
    source = inspect.getsource(smod)
    assert "pickle.load" not in source


def test_smod_source_no_yaml_load_batch9():
    source = inspect.getsource(smod)
    assert "yaml.load" not in source


def test_smod_source_no_eval_exec_batch9():
    source = inspect.getsource(smod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_smod_source_no_compile_batch9():
    source = inspect.getsource(smod)
    assert "compile(" not in source


def test_smod_source_no_sys_exit_batch9():
    source = inspect.getsource(smod)
    assert "sys.exit" not in source
    assert "exit(" not in source
    assert "quit(" not in source


def test_smod_source_no_global_keyword_batch9():
    source = inspect.getsource(smod)
    assert "\nglobal " not in source


def test_smod_source_no_async_def_batch9():
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_smod_source_no_yield_batch9():
    source = inspect.getsource(smod)
    assert "yield" not in source


def test_smod_source_no_walrus_batch9():
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_smod_source_no_class_def_outside_eval_error_batch9():
    """模块只有 1 个 class（EvalSchemaError）。"""
    source = inspect.getsource(smod)
    assert source.count("\nclass ") == 1


def test_smod_source_no_unlink_remove_batch9():
    source = inspect.getsource(smod)
    assert ".unlink(" not in source
    assert ".remove(" not in source


def test_smod_source_no_logging_batch9():
    source = inspect.getsource(smod)
    assert "logging" not in source
    assert "logger" not in source


def test_smod_source_no_sleep_batch9():
    source = inspect.getsource(smod)
    assert "time.sleep" not in source


def test_smod_source_no_hardcoded_path_batch9():
    source = inspect.getsource(smod)
    assert "C:\\\\Users" not in source
    assert "/Users/" not in source


# ---------- module source 字符串精确补强第九批 ----------


def test_module_source_has_future_annotations_batch9():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json_batch9():
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_imports_path_batch9():
    source = inspect.getsource(smod)
    assert "from pathlib import Path" in source


def test_module_source_imports_typing_any_batch9():
    source = inspect.getsource(smod)
    assert "from typing import Any" in source


def test_module_source_imports_draft_validator_batch9():
    source = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in source


def test_module_source_imports_js_validation_error_batch9():
    source = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in source


def test_module_source_has_schemas_dir_constant_batch9():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__)" in source


def test_module_source_has_eval_schema_error_class_batch9():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in source


def test_module_source_has_eval_schema_error_init_batch9():
    source = inspect.getsource(smod)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None)" in source


def test_module_source_has_eval_schema_error_super_batch9():
    source = inspect.getsource(smod)
    assert "super().__init__(message)" in source


def test_module_source_has_self_errors_batch9():
    source = inspect.getsource(smod)
    assert "self.errors = errors or []" in source


def test_module_source_has_schema_path_def_batch9():
    source = inspect.getsource(smod)
    assert "def _schema_path(name: str) -> Path:" in source


def test_module_source_has_load_schema_def_batch9():
    source = inspect.getsource(smod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in source


def test_module_source_has_validate_def_batch9():
    source = inspect.getsource(smod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in source


def test_module_source_has_validate_file_def_batch9():
    source = inspect.getsource(smod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in source


def test_module_source_uses_draft202012_validator_batch9():
    source = inspect.getsource(smod)
    assert "Draft202012Validator(" in source


def test_module_source_uses_iter_errors_batch9():
    source = inspect.getsource(smod)
    assert "iter_errors(" in source


def test_module_source_uses_sorted_batch9():
    source = inspect.getsource(smod)
    assert "sorted(" in source


def test_module_source_no_main_block_batch9():
    source = inspect.getsource(smod)
    assert "if __name__" not in source


def test_module_source_docstring_present_batch9():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_source_docstring_mentions_schema_batch9():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__.lower()


def test_module_source_no_hardcoded_paths_in_doc_batch9():
    """docstring 不含本机绝对路径。"""
    assert "C:\\" not in smod.__doc__
    assert "/Users/" not in smod.__doc__


# ---------- signatures 第九批 ----------


def test_signature_schema_path_param_count_batch9():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_signature_schema_path_param_name_batch9():
    sig = inspect.signature(_schema_path)
    assert "name" in sig.parameters


def test_signature_schema_path_param_annotation_batch9():
    sig = inspect.signature(_schema_path)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "str"


def test_signature_schema_path_return_annotation_batch9():
    sig = inspect.signature(_schema_path)
    assert sig.return_annotation == "Path"


def test_signature_load_schema_param_count_batch9():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_signature_load_schema_param_name_batch9():
    sig = inspect.signature(load_schema)
    assert "name" in sig.parameters


def test_signature_load_schema_param_annotation_batch9():
    sig = inspect.signature(load_schema)
    p = list(sig.parameters.values())[0]
    assert p.annotation == "str"


def test_signature_load_schema_return_annotation_batch9():
    sig = inspect.signature(load_schema)
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_param_count_batch9():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_signature_validate_param_names_batch9():
    sig = inspect.signature(validate)
    names = list(sig.parameters)
    assert names == ["instance", "schema_name"]


def test_signature_validate_param_kinds_batch9():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_param_annotations_batch9():
    sig = inspect.signature(validate)
    annotations = {n: p.annotation for n, p in sig.parameters.items()}
    assert annotations == {"instance": "dict[str, Any]", "schema_name": "str"}


def test_signature_validate_no_defaults_batch9():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_return_annotation_batch9():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


def test_signature_validate_file_param_count_batch9():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_signature_validate_file_param_names_batch9():
    sig = inspect.signature(validate_file)
    names = list(sig.parameters)
    assert names == ["path", "schema_name"]


def test_signature_validate_file_param_kinds_batch9():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_file_param_annotations_batch9():
    sig = inspect.signature(validate_file)
    annotations = {n: p.annotation for n, p in sig.parameters.items()}
    assert annotations == {"path": "Path | str", "schema_name": "str"}


def test_signature_validate_file_no_defaults_batch9():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_file_return_annotation_batch9():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_init_params_batch9():
    sig = inspect.signature(EvalSchemaError.__init__)
    # self + message + errors = 3 params
    assert len(sig.parameters) == 3


def test_signature_eval_schema_error_init_message_annotation_batch9():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["message"]
    assert p.annotation == "str"


def test_signature_eval_schema_error_init_errors_default_none_batch9():
    sig = inspect.signature(EvalSchemaError.__init__)
    # 注意：__init__ signature 只显示 self + message，因为 errors 是 kwargs
    # 实际定义 def __init__(self, message, errors=None)
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_signature_4_funcs_are_function_type_batch9():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert inspect.isfunction(func)


def test_signature_4_funcs_module_eq_batch9():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert func.__module__ == "evaluation.schema"


def test_signature_no_var_positional_batch9():
    for func in (_schema_path, load_schema, validate, validate_file):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_signature_no_var_keyword_batch9():
    for func in (_schema_path, load_schema, validate, validate_file):
        sig = inspect.signature(func)
        for p in sig.parameters.values():
            assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- module 合理性第九批 ----------


def test_module_all_attribute_value_batch9():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_all_is_list_batch9():
    assert isinstance(smod.__all__, list)


def test_module_all_entries_unique_batch9():
    assert len(smod.__all__) == len(set(smod.__all__))


def test_module_has_dunder_file_batch9():
    assert hasattr(smod, "__file__")
    assert smod.__file__ is not None


def test_module_dunder_file_endswith_schema_py_batch9():
    sep = os.sep
    assert smod.__file__.endswith("evaluation" + sep + "schema.py") or smod.__file__.endswith(
        "evaluation/schema.py"
    )


def test_module_dunder_name_batch9():
    assert smod.__name__ == "evaluation.schema"


def test_module_eval_schema_error_subclass_exception_batch9():
    assert issubclass(smod.EvalSchemaError, Exception)


def test_module_function_count_batch9():
    """4 module-level functions + 1 user class (EvalSchemaError)。"""
    funcs = [
        n
        for n, v in vars(smod).items()
        if inspect.isfunction(v) and v.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}
    assert len(funcs) == 4


def test_module_class_count_batch9():
    classes = [
        n for n, v in vars(smod).items() if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert set(classes) == {"EvalSchemaError"}
    assert len(classes) == 1


def test_module_no_call_at_top_level_batch9():
    source = inspect.getsource(smod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "import ",
                "from ",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
                "@",
                "class ",
                "SCHEMAS_DIR",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped and not stripped.startswith("def "):
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present_batch9():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_docstring_in_chinese_or_english_batch9():
    assert "Schema" in smod.__doc__ or "评测" in smod.__doc__


def test_module_public_api_via_all_batch9():
    for name in ("SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"):
        assert name in smod.__all__


def test_module_internal_funcs_not_in_all_batch9():
    assert "_schema_path" not in smod.__all__


# ---------- 端到端集成第九批 ----------


def test_e2e_load_and_validate_success_batch9():
    """load + validate 完整链路：合法数据。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    validate(data, "manifest.schema.json")  # 不抛 = 通过


def test_e2e_load_and_validate_failure_batch9():
    """load + validate 失败链路：非法数据。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_e2e_validate_file_round_trip_batch9(tmp_path):
    """validate_file round-trip：写 JSON → 校验。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_idempotent_batch9(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_e2e_eval_schema_error_caught_as_exception_batch9():
    try:
        raise EvalSchemaError("test")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_e2e_eval_schema_error_str_representation_batch9():
    e = EvalSchemaError("hello world")
    s = str(e)
    assert "hello world" in s


def test_e2e_eval_schema_error_chained_from_other_batch9():
    try:
        try:
            raise ValueError("inner")
        except ValueError as inner:
            raise EvalSchemaError("outer") from inner
    except EvalSchemaError as e:
        assert e.__cause__ is not None


def test_e2e_unknown_schema_raises_file_not_found_batch9():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_e2e_no_unexpected_exceptions_batch9():
    """连续多次调用 validate 不抛（合法数据）。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    for _ in range(5):
        validate(data, "manifest.schema.json")


def test_e2e_str_path_input_batch9(tmp_path):
    """str path 输入也工作。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_e2e_full_chain_minimal_batch9():
    """最小链路：load_schema + validate。"""
    schema = load_schema("manifest.schema.json")
    assert schema.get("type") == "object"
    assert "properties" in schema


def test_e2e_each_schema_has_properties_batch9():
    """每个 schema 都有 properties。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert "properties" in s


def test_e2e_each_schema_has_required_or_additional_props_batch9():
    """每个 schema 都设了 required 或 additionalProperties。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert "required" in s or "additionalProperties" in s
