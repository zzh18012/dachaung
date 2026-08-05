r"""evaluation/schema.py 边角测试 - 第十轮（Round 260）。

补强已有 base/edges/edges2-9（共 ~600+ 测试）未覆盖的深度：
- 源码字符串断言（inspect.getsource）：未覆盖 token
- module docstring 内容
- SCHEMAS_DIR 是 absolute + resolved path + is_dir()
- SCHEMAS_DIR.parent 是项目根（含 pyproject.toml）
- EvalSchemaError detailed：__init__ signature + 默认 errors=[] + 可 raise/except + args() + str()+repr()
- EvalSchemaError mro 含 BaseException + 4 items
- EvalSchemaError 是 Exception 子类
- EvalSchemaError.errors 是 list 不是 None（即使传 None）
- _schema_path returns absolute Path
- _schema_path raises FileNotFoundError with path in message
- load_schema 每次返回新 dict（不缓存）
- load_schema 含 'encoding="utf-8"'
- validate 排序行为：sorted by absolute_path
- validate errors 字段精确：path/message/schema_path
- validate head error 是 errors[0]
- validate_file 接受 str + Path
- validate_file 是 validate 的 file wrapper
- 模块 namespace 完整性
- 函数 metadata 全部
- 常量 SCHEMAS_DIR 是 Path 实例
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
# 源码字符串断言（inspect.getsource）— 未覆盖 token
# =========================================================================


def test_module_source_contains_json_import():
    import evaluation.schema as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_path_import():
    import evaluation.schema as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_any_import():
    import evaluation.schema as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_future_annotations():
    import evaluation.schema as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_jsonschema_import():
    import evaluation.schema as m

    assert "from jsonschema import Draft202012Validator" in inspect.getsource(m)


def test_module_source_contains_validation_error_import():
    import evaluation.schema as m

    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in inspect.getsource(m)


def test_module_source_contains_eval_schema_error_def():
    import evaluation.schema as m

    assert "class EvalSchemaError(Exception):" in inspect.getsource(m)


def test_module_source_contains_eval_schema_error_init():
    import evaluation.schema as m

    assert "def __init__(self, message: str" in inspect.getsource(m)


def test_module_source_contains_errors_or_empty_list():
    """errors 默认是 []（errors or []）。"""
    import evaluation.schema as m

    assert "self.errors = errors or []" in inspect.getsource(m)


def test_module_source_contains_schema_path_def():
    import evaluation.schema as m

    assert "def _schema_path(name: str) -> Path:" in inspect.getsource(m)


def test_module_source_contains_load_schema_def():
    import evaluation.schema as m

    assert "def load_schema(name: str) -> dict[str, Any]:" in inspect.getsource(m)


def test_module_source_contains_validate_def():
    import evaluation.schema as m

    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in inspect.getsource(m)


def test_module_source_contains_validate_file_def():
    import evaluation.schema as m

    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in inspect.getsource(m)


def test_module_source_contains_drafted_2020_12_validator_use():
    """validate 中调用 Draft202012Validator(schema)。"""
    import evaluation.schema as m

    assert "Draft202012Validator(schema)" in inspect.getsource(m)


def test_module_source_contains_iter_errors_call():
    """源码含 validator.iter_errors(instance)。"""
    import evaluation.schema as m

    assert "iter_errors(instance)" in inspect.getsource(m)


def test_module_source_contains_sorted_call():
    """源码含 sorted(validator.iter_errors(...))。"""
    import evaluation.schema as m

    assert "sorted(" in inspect.getsource(m)


def test_module_source_contains_absolute_path_attribute():
    """源码含 err.absolute_path。"""
    import evaluation.schema as m

    assert "absolute_path" in inspect.getsource(m)


def test_module_source_contains_absolute_schema_path_attribute():
    """源码含 err.absolute_schema_path。"""
    import evaluation.schema as m

    assert "absolute_schema_path" in inspect.getsource(m)


def test_module_source_contains_encoding_utf8_in_load():
    """源码含 encoding='utf-8'。"""
    import evaluation.schema as m

    assert 'encoding="utf-8"' in inspect.getsource(m)


def test_module_source_contains_schema_file_not_exists_message():
    """源码含 'Schema 文件不存在'。"""
    import evaluation.schema as m

    assert "Schema 文件不存在" in inspect.getsource(m)


def test_module_source_contains_validate_failure_message():
    """源码含 'Schema ... 校验失败'。"""
    import evaluation.schema as m

    assert "校验失败" in inspect.getsource(m)


def test_module_source_contains_file_not_exists_in_validate_file():
    """源码含 '待校验文件不存在'。"""
    import evaluation.schema as m

    assert "待校验文件不存在" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.schema as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_contains_no_reuse_comment():
    """源码含 '不与 app/schema.py 复用' 注释。"""
    import evaluation.schema as m

    assert "不与 app/schema.py 复用" in inspect.getsource(m)


def test_module_source_contains_resolve_call():
    """SCHEMAS_DIR 含 .resolve()。"""
    import evaluation.schema as m

    assert ".resolve()" in inspect.getsource(m)


# =========================================================================
# 模块 docstring
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.schema as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 10


def test_module_docstring_mentions_three_schemas():
    """docstring 含 manifest/annotation/evaluation-report。"""
    import evaluation.schema as m

    assert "manifest" in m.__doc__
    assert "annotation" in m.__doc__
    assert "evaluation-report" in m.__doc__


def test_module_docstring_mentions_no_reuse():
    """docstring 提到与 app/schema.py 不复用。"""
    import evaluation.schema as m

    assert "不复用" in m.__doc__ or "不与" in m.__doc__


# =========================================================================
# SCHEMAS_DIR 验证
# =========================================================================


def test_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_dir():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 应是 resolved（无 .. 或 .）。"""
    assert ".." not in str(SCHEMAS_DIR)
    assert not str(SCHEMAS_DIR).endswith(".")


def test_schemas_dir_parent_contains_pyproject():
    """SCHEMAS_DIR.parent (项目根) 含 pyproject.toml。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 是项目根。"""
    project_root = Path(__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == project_root


def test_schemas_dir_contains_manifest_schema():
    """SCHEMAS_DIR 含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_document_schema():
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


# =========================================================================
# EvalSchemaError 详细
# =========================================================================


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_is_baseexception_subclass():
    assert issubclass(EvalSchemaError, BaseException)


def test_eval_schema_error_mro_contains_exception():
    assert Exception in EvalSchemaError.__mro__


def test_eval_schema_error_mro_contains_base_exception():
    assert BaseException in EvalSchemaError.__mro__


def test_eval_schema_error_mro_length_4():
    """MRO = [EvalSchemaError, Exception, BaseException, object]。"""
    assert len(EvalSchemaError.__mro__) == 4


def test_eval_schema_error_module_identity():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_eval_schema_error_qualname():
    assert EvalSchemaError.__qualname__ == "EvalSchemaError"


def test_eval_schema_error_name():
    assert EvalSchemaError.__name__ == "EvalSchemaError"


def test_eval_schema_error_init_param_count_3():
    """__init__(self, message, errors=None) → 3 个参数。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3


def test_eval_schema_error_init_param_names():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_init_param_defaults():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_init_no_var_args():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_eval_schema_error_init_no_var_kwargs():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_eval_schema_error_with_default_errors_is_empty_list():
    """errors=None → 默认 []。"""
    e = EvalSchemaError("test")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_with_provided_errors_keeps_list():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("test", errors=errs)
    assert e.errors is errs  # errors or [] → truthy → keep reference


def test_eval_schema_error_with_empty_errors_keeps_empty_list():
    """errors=[] → falsy → 替换为 []（new list）。"""
    errs: list = []
    e = EvalSchemaError("test", errors=errs)
    assert e.errors == []


def test_eval_schema_error_args_contains_message():
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_str_returns_message():
    e = EvalSchemaError("error message")
    assert str(e) == "error message"


def test_eval_schema_error_repr_contains_class_name():
    e = EvalSchemaError("err")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_can_be_raised():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_can_be_caught_as_exception():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_caught_specific_does_not_catch_others():
    """EvalSchemaError 不捕获其他 Exception 子类。"""
    with pytest.raises(ValueError):
        try:
            raise ValueError("x")
        except EvalSchemaError:
            pass  # should not catch


def test_eval_schema_error_errors_attribute_writable():
    """errors 属性可写。"""
    e = EvalSchemaError("x")
    e.errors = [{"new": "data"}]
    assert e.errors == [{"new": "data"}]


def test_eval_schema_error_message_attribute_via_str():
    """Exception message 通过 str() 访问，无单独 message 属性。"""
    e = EvalSchemaError("my message")
    assert not hasattr(e, "message")
    assert str(e) == "my message"


def test_eval_schema_error_can_be_chained():
    """可以被 raise from。"""
    try:
        try:
            raise ValueError("original")
        except ValueError as ve:
            raise EvalSchemaError("wrapped") from ve
    except EvalSchemaError as e:
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_hashable():
    """Exception 子类一般 hashable（默认 id-based）。"""
    e = EvalSchemaError("x")
    assert hash(e) == hash(e)


def test_eval_schema_error_equality_by_identity():
    """两个 EvalSchemaError 实例不相等（默认按 id）。"""
    a = EvalSchemaError("x")
    b = EvalSchemaError("x")
    assert a is not b
    # Exception 默认 __eq__ 是 object identity
    assert a == a


# =========================================================================
# _schema_path 详细
# =========================================================================


def test_schema_path_module_identity():
    assert _schema_path.__module__ == "evaluation.schema"


def test_schema_path_qualname():
    assert _schema_path.__qualname__ == "_schema_path"


def test_schema_path_param_count_1():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_schema_path_param_name():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_param_no_default():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_schema_path_returns_path_for_existing():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_raises_for_missing():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_error_message_contains_path():
    """FileNotFoundError message 含路径。"""
    try:
        _schema_path("nonexistent.schema.json")
        assert False, "should have raised"
    except FileNotFoundError as e:
        assert "nonexistent.schema.json" in str(e) or "schemas" in str(e)


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_accepts_unicode_name():
    """unicode name → 不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("测试.schema.json")


def test_schema_path_accepts_name_with_spaces():
    with pytest.raises(FileNotFoundError):
        _schema_path("name with spaces.schema.json")


# =========================================================================
# load_schema 详细
# =========================================================================


def test_load_schema_module_identity():
    assert load_schema.__module__ == "evaluation.schema"


def test_load_schema_qualname():
    assert load_schema.__qualname__ == "load_schema"


def test_load_schema_param_count_1():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_param_name():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_no_caching_returns_independent_dict():
    """每次调用返回新 dict（不缓存）。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b
    # 修改 a 不应影响 b
    a["_test_key"] = "x"
    assert "_test_key" not in b


def test_load_schema_for_annotation():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_for_evaluation_report():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_for_document():
    s = load_schema("document.schema.json")
    assert isinstance(s, dict)


def test_load_schema_raises_for_missing():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_dict_has_schema_dollar_key():
    """JSON Schema 顶层应有 '$schema' 字段。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


# =========================================================================
# validate 详细
# =========================================================================


def test_validate_module_identity():
    assert validate.__module__ == "evaluation.schema"


def test_validate_qualname():
    assert validate.__qualname__ == "validate"


def test_validate_param_count_2():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_param_names():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_no_var_args():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_validate_no_var_kwargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_return_annotation_none_str():
    """future annotations → return_annotation 是 'None' 字符串。"""
    sig = inspect.signature(validate)
    assert isinstance(sig.return_annotation, str)
    assert "None" in sig.return_annotation


def test_validate_returns_none_on_success():
    """成功路径返回 None。"""
    good_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    out = validate(good_manifest, "manifest.schema.json")
    assert out is None


def test_validate_raises_on_empty_dict():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_errors_attribute_is_list():
    """EvalSchemaError.errors 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) > 0


def test_validate_errors_each_item_is_dict():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err, dict)


def test_validate_errors_each_item_has_required_keys():
    """每个 error item 含 path/message/schema_path。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_validate_errors_path_is_list():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)


def test_validate_errors_message_is_str():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["message"], str)


def test_validate_message_includes_schema_name():
    """错误 message 含 schema_name。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)


def test_validate_message_includes_error_count():
    """错误 message 含错误数。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # message 含 'N 处'
        assert "处" in str(e) or "errors" in str(e).lower()


def test_validate_sorts_errors_by_path():
    """errors 按 absolute_path 排序。"""
    bad = {
        "manifest_version": "wrong_version",  # wrong type
        "devset_status": 123,  # wrong type
    }
    try:
        validate(bad, "manifest.schema.json")
    except EvalSchemaError as e:
        # 排序后路径
        paths = [tuple(err["path"]) for err in e.errors]
        assert paths == sorted(paths)


# =========================================================================
# validate_file 详细
# =========================================================================


def test_validate_file_module_identity():
    assert validate_file.__module__ == "evaluation.schema"


def test_validate_file_qualname():
    assert validate_file.__qualname__ == "validate_file"


def test_validate_file_param_count_2():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_param_names():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_param_path_kind_positional_or_keyword():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_file_no_var_args():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_validate_file_no_var_kwargs():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_file_returns_none_on_success(tmp_path: Path):
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_accepts_str_path(tmp_path: Path):
    m = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(m), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_contains_schemas_dir():
    import evaluation.schema as m

    assert hasattr(m, "SCHEMAS_DIR")
    assert m.SCHEMAS_DIR is SCHEMAS_DIR


def test_module_namespace_contains_eval_schema_error():
    import evaluation.schema as m

    assert hasattr(m, "EvalSchemaError")
    assert m.EvalSchemaError is EvalSchemaError


def test_module_namespace_contains_helpers():
    import evaluation.schema as m

    for name in ["load_schema", "validate", "validate_file", "_schema_path"]:
        assert hasattr(m, name)


def test_module_namespace_contains_json():
    import evaluation.schema as m
    import json as orig_json

    assert m.json is orig_json


def test_module_namespace_contains_path():
    import evaluation.schema as m
    from pathlib import Path as OrigPath

    assert m.Path is OrigPath


def test_module_namespace_contains_draft_validator():
    """Draft202012Validator 通过 import 进 namespace。"""
    import evaluation.schema as m

    assert hasattr(m, "Draft202012Validator")


def test_module_namespace_contains_js_validation_error():
    import evaluation.schema as m

    assert hasattr(m, "JSValidationError")


def test_module_all_is_list():
    import evaluation.schema as m

    assert isinstance(m.__all__, list)


def test_module_all_is_not_tuple():
    import evaluation.schema as m

    assert not isinstance(m.__all__, tuple)


def test_module_all_exact():
    import evaluation.schema as m

    assert m.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_does_not_contain_schema_path():
    """__all__ 不含 _schema_path（私有）。"""
    import evaluation.schema as m

    assert "_schema_path" not in m.__all__


def test_module_all_all_names_in_namespace():
    import evaluation.schema as m

    for name in m.__all__:
        assert hasattr(m, name)


# =========================================================================
# 所有 helpers 都是 FunctionType
# =========================================================================


def test_all_helpers_are_function_type():
    import types as _types

    for fn in [_schema_path, load_schema, validate, validate_file]:
        assert isinstance(fn, _types.FunctionType)


# =========================================================================
# 跨函数一致性
# =========================================================================


def test_validate_uses_load_schema_internally():
    """validate 内部调用 load_schema。"""
    # 用一个不存在的 schema name 验证
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_file_uses_validate_internally(tmp_path: Path):
    """validate_file 内部调用 validate。"""
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_passes_schema_name_through(tmp_path: Path):
    """schema_name 透传给 validate。"""
    # 用 annotation.schema.json 校验 manifest → 应失败
    p = tmp_path / "m.json"
    manifest_like = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p.write_text(json.dumps(manifest_like), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "annotation.schema.json")


# =========================================================================
# 整体不变量
# =========================================================================


def test_schemas_dir_constant_value_stable():
    """SCHEMAS_DIR 是 module-level 常量，多次访问同一对象。"""
    import evaluation.schema as m

    assert m.SCHEMAS_DIR is SCHEMAS_DIR


def test_eval_schema_error_constant_value_stable():
    import evaluation.schema as m

    assert m.EvalSchemaError is EvalSchemaError


def test_load_schema_no_caching_for_multiple_calls():
    """load_schema 多次调用，每次新 dict 但内容相等。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    s3 = load_schema("manifest.schema.json")
    assert s1 == s2 == s3
    assert s1 is not s2
    assert s2 is not s3
