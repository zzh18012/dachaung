"""evaluation/schema.py 第六轮 edges 测试（Round 601）。

补强 edges55 未触及的角度（第三十六批）。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import Draft202012Validator
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


# ---------- SCHEMAS_DIR 第三十六批


def test_schemas_dir_is_path_batch36():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_resolved_batch36():
    """SCHEMAS_DIR 是 resolve 过的绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_ends_with_schemas_batch36():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_name_batch36():
    """SCHEMAS_DIR.parent 是项目根。"""
    # 不强校验名字，但应该存在
    assert SCHEMAS_DIR.parent.is_dir()


def test_schemas_dir_in_source_batch36():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in src


def test_schemas_dir_value_writable_in_tests_batch36():
    """模块属性可被读取。"""
    assert smod.SCHEMAS_DIR is SCHEMAS_DIR


# ---------- _schema_path 第三十六批


def test_schema_path_callable_batch36():
    assert callable(_schema_path)


def test_schema_path_returns_path_batch36():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_missing_file_raises_batch36():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc.value)


def test_schema_path_absolute_batch36():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_signature_one_param_batch36():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_name_annotation_str_batch36():
    sig = inspect.signature(_schema_path)
    assert "str" in str(sig.parameters["name"].annotation)


def test_schema_path_return_annotation_path_batch36():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


# ---------- load_schema 第三十六批


def test_load_schema_callable_batch36():
    assert callable(load_schema)


def test_load_schema_returns_dict_batch36():
    out = load_schema("manifest.schema.json")
    assert isinstance(out, dict)


def test_load_schema_manifest_has_properties_batch36():
    out = load_schema("manifest.schema.json")
    # JSON Schema 顶层应该有 properties
    assert "properties" in out


def test_load_schema_missing_file_raises_batch36():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_with_annotation_batch36():
    out = load_schema("annotation.schema.json")
    assert isinstance(out, dict)


def test_load_schema_with_evaluation_report_batch36():
    out = load_schema("evaluation-report.schema.json")
    assert isinstance(out, dict)


def test_load_schema_signature_one_param_batch36():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_return_annotation_dict_batch36():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_load_schema_does_not_cache_batch36():
    """两次调用返回不同对象。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_idempotent_batch36():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True)


# ---------- validate 第三十六批


def test_validate_callable_batch36():
    assert callable(validate)


def test_validate_signature_two_params_batch36():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_instance_annotation_dict_batch36():
    sig = inspect.signature(validate)
    assert "dict" in str(sig.parameters["instance"].annotation)


def test_validate_schema_name_annotation_str_batch36():
    sig = inspect.signature(validate)
    assert "str" in str(sig.parameters["schema_name"].annotation)


def test_validate_return_annotation_none_batch36():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


def test_validate_manifest_empty_dict_raises_batch36():
    """空 dict 不符合 manifest schema（缺 required fields）。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_manifest_minimal_valid_batch36():
    """最小合法 manifest（需要 file 真实存在 + 路径合法）。

    Schema 校验只检查结构，不检查文件存在；这里只测结构合法性。
    """
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # 不抛异常即通过
    validate(data, "manifest.schema.json")


def test_validate_invalid_schema_name_raises_batch36():
    """未知 schema 名 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_validate_eval_schema_error_has_errors_list_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert isinstance(exc.value.errors, list)


def test_validate_eval_schema_error_errors_not_none_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert exc.value.errors is not None


def test_validate_eval_schema_error_errors_have_path_message_schema_path_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) > 0
    err = exc.value.errors[0]
    assert "path" in err
    assert "message" in err
    assert "schema_path" in err


def test_validate_message_contains_schema_name_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_message_contains_error_count_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "处" in str(exc.value)


def test_validate_message_contains_first_error_path_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        validate({"unknown_key": "x"}, "manifest.schema.json")
    # 应该包含 path 信息
    assert "path=" in str(exc.value)


def test_validate_does_not_raise_on_valid_instance_batch36():
    """合法 instance 不抛。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # 无异常


def test_validate_returns_none_on_success_batch36():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


# ---------- validate_file 第三十六批


def test_validate_file_callable_batch36():
    assert callable(validate_file)


def test_validate_file_signature_two_params_batch36():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_missing_file_raises_batch36(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_invalid_json_raises_batch36(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_valid_minimal_batch36(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    # 不抛
    validate_file(p, "manifest.schema.json")


def test_validate_file_str_path_input_batch36(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_returns_none_on_success_batch36(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_path_annotation_path_or_str_batch36():
    sig = inspect.signature(validate_file)
    ann = str(sig.parameters["path"].annotation)
    assert "Path" in ann
    assert "str" in ann


def test_validate_file_return_annotation_none_batch36():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


def test_validate_file_calls_validate_batch36(tmp_path):
    """validate_file 内部调用 validate。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with patch("evaluation.schema.validate") as mock:
        validate_file(p, "manifest.schema.json")
    mock.assert_called_once()


# ---------- EvalSchemaError 第三十六批


def test_eval_schema_error_is_exception_batch36():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_default_errors_empty_batch36():
    err = EvalSchemaError("boom")
    assert err.errors == []


def test_eval_schema_error_with_errors_batch36():
    errs = [{"path": ["a"], "message": "x"}]
    err = EvalSchemaError("boom", errors=errs)
    assert err.errors == errs


def test_eval_schema_error_with_none_errors_batch36():
    err = EvalSchemaError("boom", errors=None)
    assert err.errors == []


def test_eval_schema_error_message_passthrough_batch36():
    err = EvalSchemaError("test message")
    assert str(err) == "test message"


def test_eval_schema_error_can_be_raised_batch36():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("x")
    assert "x" in str(exc.value)


def test_eval_schema_error_caught_as_exception_batch36():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_errors_attribute_writable_batch36():
    err = EvalSchemaError("x")
    err.errors = [{"new": True}]
    assert err.errors == [{"new": True}]


def test_eval_schema_error_signature_init_batch36():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_none_batch36():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_message_no_default_batch36():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty


def test_eval_schema_error_module_level_batch36():
    assert hasattr(smod, "EvalSchemaError")


# ---------- module source forbidden tokens 第六十批


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
def test_module_source_no_forbidden_tokens_batch36(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第五十六批


def test_module_source_contains_design_doc_batch36():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_future_annotations_batch36():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch36():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_path_import_batch36():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch36():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_contains_jsonschema_import_batch36():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsonschema_validation_error_import_batch36():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_contains_schemas_dir_definition_batch36():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_eval_schema_error_class_batch36():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_source_contains_schema_path_function_batch36():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_function_batch36():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_function_batch36():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_function_batch36():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_draft_2020_12_batch36():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_call_batch36():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_encoding_utf8_batch36():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_file_not_found_keyword_batch36():
    src = inspect.getsource(smod)
    assert "FileNotFoundError" in src


def test_module_source_contains_absolute_path_keyword_batch36():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_keyword_batch36():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_all_export_batch36():
    src = inspect.getsource(smod)
    assert "__all__" in src


# ---------- signatures 第五十六批


def test_signature_validate_params_batch36():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_params_batch36():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_load_schema_params_batch36():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_schema_path_params_batch36():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_no_default_for_instance_batch36():
    sig = inspect.signature(validate)
    assert sig.parameters["instance"].default is inspect.Parameter.empty


def test_signature_validate_no_default_for_schema_name_batch36():
    sig = inspect.signature(validate)
    assert sig.parameters["schema_name"].default is inspect.Parameter.empty


def test_signature_validate_file_no_default_for_path_batch36():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_signature_validate_file_no_default_for_schema_name_batch36():
    sig = inspect.signature(validate_file)
    assert sig.parameters["schema_name"].default is inspect.Parameter.empty


# ---------- module 合理性 第五十六批


def test_module_has_all_attribute_batch36():
    assert hasattr(smod, "__all__")


def test_module_all_is_list_batch36():
    assert isinstance(smod.__all__, list)


def test_module_all_five_entries_batch36():
    assert len(smod.__all__) == 5


def test_module_all_contains_schemas_dir_batch36():
    assert "SCHEMAS_DIR" in smod.__all__


def test_module_all_contains_eval_schema_error_batch36():
    assert "EvalSchemaError" in smod.__all__


def test_module_all_contains_load_schema_batch36():
    assert "load_schema" in smod.__all__


def test_module_all_contains_validate_batch36():
    assert "validate" in smod.__all__


def test_module_all_contains_validate_file_batch36():
    assert "validate_file" in smod.__all__


def test_module_does_not_export_private_batch36():
    assert "_schema_path" not in smod.__all__


def test_module_does_not_define_other_class_batch36():
    """只有 EvalSchemaError 一个类。"""
    import ast
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_module_has_future_annotations_batch36():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_has_schemas_dir_attr_batch36():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_has_eval_schema_error_attr_batch36():
    assert hasattr(smod, "EvalSchemaError")


def test_module_has_load_schema_attr_batch36():
    assert hasattr(smod, "load_schema")


def test_module_has_validate_attr_batch36():
    assert hasattr(smod, "validate")


def test_module_has_validate_file_attr_batch36():
    assert hasattr(smod, "validate_file")


def test_module_functions_callable_batch36():
    assert callable(smod.load_schema)
    assert callable(smod.validate)
    assert callable(smod.validate_file)


# ---------- 端到端集成 第五十六批


def test_e2e_validate_minimal_valid_manifest_batch36():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


def test_e2e_validate_invalid_manifest_batch36():
    """version 不对 → 校验失败。"""
    data = {
        "manifest_version": "0.0",  # 不符合 const
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_e2e_validate_file_full_round_trip_batch36(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_eval_schema_error_with_full_info_batch36():
    """EvalSchemaError 含 errors list + message 字符串。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({"unknown": "x"}, "manifest.schema.json")
    err = exc.value
    assert isinstance(str(err), str)
    assert isinstance(err.errors, list)
    assert len(err.errors) > 0
    # 第一个 error 含三个 keys
    first = err.errors[0]
    assert set(first.keys()) == {"path", "message", "schema_path"}


def test_e2e_load_then_validate_idempotent_batch36():
    """先 load_schema 再 validate 等价于直接 validate。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    assert errors == []
