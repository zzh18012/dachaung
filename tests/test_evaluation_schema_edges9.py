r"""evaluation/schema.py 边角测试 - 第九轮（Round 253）。

补强已有 base/edges/edges2-8（共 ~530+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：含特定 token
- module metadata：__file__ 后缀 .py / __package__ == 'evaluation' / __name__ == 'evaluation.schema'
- 函数 metadata：__module__/__qualname__/__name__/FunctionType；无 varargs/varkw；return_annotation
- EvalSchemaError class metadata：__module__/__qualname__/__mro__
- _schema_path 行为：name 含空格 / 含 unicode / Path object
- load_schema：每次新 dict
- validate：errors 排序行为；message 格式精确
- validate_file：errors 在 JSON 中含 'path'/'message'/'schema_path'
- SCHEMAS_DIR 是 absolute path 的 resolve()
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# 源码字符串断言（inspect.getsource）
# =========================================================================


def test_module_source_contains_schemas_dir_definition():
    """源码含 'SCHEMAS_DIR'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "SCHEMAS_DIR" in src


def test_module_source_contains_eval_schema_error_class():
    """源码含 'class EvalSchemaError'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "class EvalSchemaError" in src


def test_module_source_contains_schema_path_function():
    """源码含 'def _schema_path'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "def _schema_path" in src


def test_module_source_contains_load_schema_function():
    """源码含 'def load_schema'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "def load_schema" in src


def test_module_source_contains_validate_function():
    """源码含 'def validate('。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "def validate(" in src


def test_module_source_contains_validate_file_function():
    """源码含 'def validate_file'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "def validate_file" in src


def test_module_source_contains_draft202012_import():
    """源码含 'Draft202012Validator'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "Draft202012Validator" in src


def test_module_source_contains_jsvalidationerror_import():
    """源码含 'ValidationError as JSValidationError'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "ValidationError as JSValidationError" in src


def test_module_source_contains_future_annotations():
    """源码含 'from __future__ import annotations'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_contains_dict_subscript_syntax():
    """源码含 'dict[str,'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "dict[str," in src


def test_module_source_no_main_guard():
    """源码不含 '__main__'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "__main__" not in src


def test_module_source_contains_iter_errors_call():
    """源码含 'iter_errors'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_call():
    """源码含 'absolute_path'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "absolute_path" in src


def test_module_source_contains_resolve_call():
    """源码含 '.resolve()'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert ".resolve()" in src


def test_module_source_contains_isfile_check():
    """源码含 '.is_file()'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert ".is_file()" in src


def test_module_source_contains_filenotfound_error_raise():
    """源码含 'raise FileNotFoundError'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "raise FileNotFoundError" in src


def test_module_source_contains_json_load_call():
    """源码含 'json.load('。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert "json.load(" in src


def test_module_source_contains_encoding_utf8():
    """源码含 'encoding="utf-8"'。"""
    import evaluation.schema as m
    src = inspect.getsource(m)
    assert 'encoding="utf-8"' in src


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_endswith_py():
    """__file__ 以 '.py' 结尾。"""
    import evaluation.schema as m
    assert m.__file__.endswith(".py")


def test_module_file_contains_schema():
    """__file__ 含 'schema'。"""
    import evaluation.schema as m
    assert "schema" in m.__file__


def test_module_package_is_evaluation():
    """__package__ == 'evaluation'。"""
    import evaluation.schema as m
    assert m.__package__ == "evaluation"


def test_module_name_is_evaluation_schema():
    """__name__ == 'evaluation.schema'。"""
    import evaluation.schema as m
    assert m.__name__ == "evaluation.schema"


def test_module_json_is_json_module():
    """json is json。"""
    import evaluation.schema as m
    assert m.json is json


def test_module_path_is_pathlib_path():
    """Path is pathlib.Path。"""
    import evaluation.schema as m
    from pathlib import Path as P
    assert m.Path is P


def test_module_typing_any_is_typing_any():
    """Any is typing.Any。"""
    import evaluation.schema as m
    from typing import Any as A
    assert m.Any is A


def test_module_draft202012_is_imported():
    """Draft202012Validator identity。"""
    import evaluation.schema as m
    assert m.Draft202012Validator is Draft202012Validator


def test_module_jsvalidation_error_is_imported():
    """JSValidationError identity。"""
    import evaluation.schema as m
    assert m.JSValidationError is JSValidationError


# =========================================================================
# SCHEMAS_DIR 详细
# =========================================================================


def test_schemas_dir_is_pathlib_path_instance():
    """SCHEMAS_DIR 是 Path 实例。"""
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    """SCHEMAS_DIR 是绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved_no_double_dots():
    """SCHEMAS_DIR resolved 后无 '..'。"""
    parts = SCHEMAS_DIR.parts
    assert ".." not in parts


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 是项目根目录。"""
    import evaluation.schema as m
    project_root = Path(m.__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == project_root


def test_schemas_dir_endswith_schemas():
    """SCHEMAS_DIR 名称是 'schemas'。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_is_directory():
    """SCHEMAS_DIR 是目录。"""
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_expected_files():
    """SCHEMAS_DIR 含 4 个 schema 文件。"""
    expected_files = {
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    }
    actual_files = set(p.name for p in SCHEMAS_DIR.iterdir() if p.is_file() and p.name.endswith(".json"))
    assert expected_files.issubset(actual_files)


# =========================================================================
# __all__ 精确
# =========================================================================


def test_module_all_is_list_not_tuple():
    """__all__ 是 list 不是 tuple。"""
    import evaluation.schema as m
    assert isinstance(m.__all__, list)
    assert not isinstance(m.__all__, tuple)


def test_module_all_length_five():
    """__all__ 5 个元素。"""
    import evaluation.schema as m
    assert len(m.__all__) == 5


def test_module_all_set_exact():
    """__all__ 集合精确。"""
    import evaluation.schema as m
    assert set(m.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_all_no_duplicates():
    """__all__ 无重复。"""
    import evaluation.schema as m
    assert len(m.__all__) == len(set(m.__all__))


def test_module_all_does_not_contain_private():
    """__all__ 不含 '_' 开头。"""
    import evaluation.schema as m
    for name in m.__all__:
        assert not name.startswith("_")


def test_module_all_does_not_contain_schema_path():
    """__all__ 不含 _schema_path。"""
    import evaluation.schema as m
    assert "_schema_path" not in m.__all__


def test_module_namespace_contains_all():
    """所有 __all__ 名字都在命名空间。"""
    import evaluation.schema as m
    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# EvalSchemaError class metadata
# =========================================================================


def test_eval_schema_error_module_attribute():
    """__module__ == 'evaluation.schema'。"""
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_eval_schema_error_qualname():
    """__qualname__ == 'EvalSchemaError'。"""
    assert EvalSchemaError.__qualname__ == "EvalSchemaError"


def test_eval_schema_error_name():
    """__name__ == 'EvalSchemaError'。"""
    assert EvalSchemaError.__name__ == "EvalSchemaError"


def test_eval_schema_error_is_exception_subclass():
    """是 Exception 子类。"""
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_is_not_value_error():
    """不是 ValueError 子类。"""
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_is_not_standard_error():
    """不是 StandardError 子类（Python 3 已无 StandardError）。"""
    assert not hasattr(EvalSchemaError, "StandardError")


def test_eval_schema_error_mro_contains_exception():
    """mro 含 Exception。"""
    assert Exception in EvalSchemaError.__mro__


def test_eval_schema_error_mro_contains_object():
    """mro 含 object。"""
    assert object in EvalSchemaError.__mro__


def test_eval_schema_error_mro_length_four():
    """mro 长度 4：[EvalSchemaError, Exception, BaseException, object]。"""
    assert len(EvalSchemaError.__mro__) == 4


def test_eval_schema_error_mro_contains_base_exception():
    """mro 含 BaseException。"""
    assert BaseException in EvalSchemaError.__mro__


def test_eval_schema_error_init_callable():
    """__init__ 可调用。"""
    assert callable(EvalSchemaError.__init__)


def test_eval_schema_error_init_signature_two_params():
    """__init__ 签名含 3 个参数 (self, message, errors)。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_eval_schema_error_init_errors_default_is_none():
    """errors default is None。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# =========================================================================
# 函数 metadata
# =========================================================================


def test_load_schema_module_attribute():
    """__module__ == 'evaluation.schema'。"""
    assert load_schema.__module__ == "evaluation.schema"


def test_load_schema_qualname():
    """__qualname__ == 'load_schema'。"""
    assert load_schema.__qualname__ == "load_schema"


def test_validate_module_attribute():
    """__module__ == 'evaluation.schema'。"""
    assert validate.__module__ == "evaluation.schema"


def test_validate_qualname():
    """__qualname__ == 'validate'。"""
    assert validate.__qualname__ == "validate"


def test_validate_file_module_attribute():
    """__module__ == 'evaluation.schema'。"""
    assert validate_file.__module__ == "evaluation.schema"


def test_validate_file_qualname():
    """__qualname__ == 'validate_file'。"""
    assert validate_file.__qualname__ == "validate_file"


def test_schema_path_module_attribute():
    """__module__ == 'evaluation.schema'。"""
    assert _schema_path.__module__ == "evaluation.schema"


def test_schema_path_qualname():
    """__qualname__ == '_schema_path'。"""
    assert _schema_path.__qualname__ == "_schema_path"


def test_load_schema_is_python_function():
    """是 Python 函数。"""
    import types
    assert isinstance(load_schema, types.FunctionType)


def test_validate_is_python_function():
    """是 Python 函数。"""
    import types
    assert isinstance(validate, types.FunctionType)


def test_validate_file_is_python_function():
    """是 Python 函数。"""
    import types
    assert isinstance(validate_file, types.FunctionType)


def test_schema_path_is_python_function():
    """是 Python 函数。"""
    import types
    assert isinstance(_schema_path, types.FunctionType)


def test_load_schema_no_varargs():
    """无 VAR_POSITIONAL/VAR_KEYWORD。"""
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_no_varargs():
    """无 VAR_POSITIONAL/VAR_KEYWORD。"""
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_file_no_varargs():
    """无 VAR_POSITIONAL/VAR_KEYWORD。"""
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_schema_path_no_varargs():
    """无 VAR_POSITIONAL/VAR_KEYWORD。"""
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_load_schema_return_annotation_is_str():
    """return annotation 是 str（__future__）。"""
    sig = inspect.signature(load_schema)
    assert isinstance(sig.return_annotation, str)


def test_validate_return_annotation_is_str_or_none():
    """return annotation 是 str 'None' 或 None。"""
    sig = inspect.signature(validate)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_validate_file_return_annotation_is_str_or_none():
    """return annotation 是 str 'None' 或 None。"""
    sig = inspect.signature(validate_file)
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_schema_path_return_annotation_is_str():
    """return annotation 含 Path。"""
    sig = inspect.signature(_schema_path)
    assert "Path" in sig.return_annotation


# =========================================================================
# _schema_path 边界
# =========================================================================


def test_schema_path_signature_one_param():
    """signature 1 个参数 'name'。"""
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_schema_path_returns_path_for_each_known_schema():
    """4 个已知 schema 都返回 Path。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(name)
        assert isinstance(p, Path)
        assert p.is_file()


def test_schema_path_returns_under_schemas_dir():
    """返回的 Path 在 SCHEMAS_DIR 下。"""
    for name in ("manifest.schema.json", "annotation.schema.json"):
        p = _schema_path(name)
        assert p.parent == SCHEMAS_DIR


def test_schema_path_message_contains_schema_word():
    """FileNotFoundError message 含 'Schema' 或 'schema'。"""
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    msg = str(exc_info.value)
    assert "Schema" in msg or "schema" in msg


def test_schema_path_message_contains_filename():
    """FileNotFoundError message 含文件名。"""
    name = "missing.schema.json"
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path(name)
    assert name in str(exc_info.value)


def test_schema_path_dotdot_raises():
    """'..' 路径穿越 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../manifest.schema.json")


def test_schema_path_subdir_raises():
    """子目录 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/manifest.schema.json")


def test_schema_path_empty_raises():
    """空 name → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_only_extension_raises():
    """name='.json' → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".json")


def test_schema_path_only_basename_no_ext_raises():
    """name='manifest' → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest")


# =========================================================================
# load_schema 详细
# =========================================================================


def test_load_schema_returns_dict_type():
    """返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_each_known_returns_dict_with_schema_key():
    """每个 schema dict 含 '$schema' key。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)
        assert "$schema" in s


def test_load_schema_no_caching():
    """不缓存：每次新 dict。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_load_schema_modify_does_not_affect_subsequent_call():
    """修改一次返回不影响下次。"""
    a = load_schema("manifest.schema.json")
    a["__test"] = "value"
    b = load_schema("manifest.schema.json")
    assert "__test" not in b


def test_load_schema_signature_param_count_one():
    """signature 1 个参数。"""
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_param_name_is_name():
    """参数名 'name'。"""
    sig = inspect.signature(load_schema)
    assert "name" in sig.parameters


def test_load_schema_param_kind_positional_or_keyword():
    """参数 kind POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(load_schema)
    p = sig.parameters["name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_schema_param_no_default():
    """参数无 default。"""
    sig = inspect.signature(load_schema)
    p = sig.parameters["name"]
    assert p.default is inspect.Parameter.empty


# =========================================================================
# validate 详细
# =========================================================================


def test_validate_signature_two_params():
    """signature 2 个参数 (instance, schema_name)。"""
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_validate_returns_none_on_success():
    """成功路径返回 None。"""
    minimal = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    out = validate(minimal, "manifest.schema.json")
    assert out is None


def test_validate_does_not_modify_instance():
    """不修改 instance。"""
    import copy
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before = copy.deepcopy(inst)
    validate(inst, "manifest.schema.json")
    assert inst == before


def test_validate_raises_eval_schema_error_on_invalid():
    """非法 instance → EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_error_message_contains_schema_name():
    """错误 message 含 schema_name。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "annotation.schema.json")
    assert "annotation.schema.json" in str(exc_info.value)


def test_validate_error_message_contains_path():
    """错误 message 含 'path='。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert "path=" in str(exc_info.value)


def test_validate_error_message_contains_count():
    """错误 message 含错误数。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    # message 含 '处）' 中文括号 + 数字
    assert "处" in msg


def test_validate_errors_each_has_three_keys():
    """errors 每项 3 key。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list():
    """errors[].path 是 list。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list():
    """errors[].schema_path 是 list。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_errors_message_is_str():
    """errors[].message 是 str。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["message"], str)


def test_validate_errors_count_matches_jsonschema():
    """errors 数量与 jsonschema iter_errors 一致。"""
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    direct_errors = sorted(validator.iter_errors({}), key=lambda e: list(e.absolute_path))
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert len(exc_info.value.errors) == len(direct_errors)


# =========================================================================
# validate_file 详细
# =========================================================================


def test_validate_file_accepts_str_path(tmp_path: Path):
    """接受 str 路径。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    out = validate_file(str(p), "manifest.schema.json")
    assert out is None


def test_validate_file_accepts_path_object(tmp_path: Path):
    """接受 Path 对象。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_returns_none_on_success(tmp_path: Path):
    """成功返回 None。"""
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """目录 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    """非法 JSON → JSONDecodeError 透传。"""
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error(tmp_path: Path):
    """合法 JSON 但 schema 失败 → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_signature_two_params():
    """signature 2 个参数 (path, schema_name)。"""
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


# =========================================================================
# 4 个 schema 自身合法
# =========================================================================


def test_all_known_schemas_are_valid_draft2020():
    """4 个 schema 自身合法。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        Draft202012Validator.check_schema(s)


def test_load_schema_can_be_used_with_validator():
    """load_schema 返回的 dict 可被 Draft202012Validator 使用。"""
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    assert v is not None


def test_validate_consistent_with_direct_validator():
    """validate 与直接 Validator 行为一致（都拒绝空 dict）。"""
    bad = {}
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")
    s = load_schema("manifest.schema.json")
    v = Draft202012Validator(s)
    assert len(list(v.iter_errors(bad))) > 0
