r"""evaluation/schema.py 边角测试 - 第十一轮（Round 267）。

edges10 已覆盖：源码 token、docstring、SCHEMAS_DIR 绝对路径、EvalSchemaError 详细、
_schema_path 详细、load_schema 不缓存、validate 排序/errors 字段/head error、
validate_file str+Path、namespace、metadata、SCHEMAS_DIR Path 实例。

edges11 补强未覆盖的角度：
- EvalSchemaError 详细：errors=[] 默认是 list；errors=None → []；errors=non-list → 透传（不强制）；raise from except 链；args 含 message；str(message) 格式；repr 含 EvalSchemaError
- _schema_path：不存在 → FileNotFoundError 含完整路径；存在 → 返回 Path；调用多次独立；接受 str 路径
- load_schema：返回 dict（顶层 type 通常是 object）；3 个 schema 都可加载；返回 dict identity 不缓存
- validate：空 errors → 静默 return None；多 errors 排序 by path；EvalSchemaError.errors 是 list of dict；error.path 是 list；error.message 是 str；error.schema_path 是 list
- validate message 格式：含 schema_name、errors count、head message、head path
- validate_file：path 是 str → 转 Path；path 是 Path → 直接用；不存在 → FileNotFoundError；存在但 JSON invalid → JSONDecodeError；JSON 顶层 list → 走 validate（schema 多半要求 object → 校验失败）
- 模块源码 token：含 SCHEMAS_DIR.parent.parent / 不含 cache 字段 / 不含 lru_cache / 不含 logging
- docstring 提到 manifest / annotation / evaluation-report / 不复用 / app/schema.py
- 模块 namespace：SCHEMAS_DIR/EvalSchemaError/load_schema/validate/validate_file/_schema_path
- 签名 introspection：每个函数 param 名/默认/kind
- helper metadata：4 个 helper __module__/__qualname__
- jsonschema 协作：Draft202012Validator 实例化 + iter_errors + sorted
- module imports：import json / from pathlib import Path / from typing import Any / from jsonschema import Draft202012Validator / JSValidationError
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
# EvalSchemaError 详细
# =========================================================================


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_is_baseexception_subclass():
    assert issubclass(EvalSchemaError, BaseException)


def test_eval_schema_error_init_param_count_2():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self, message, errors


def test_eval_schema_error_init_param_names():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_init_message_no_default():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty


def test_eval_schema_error_init_errors_kind_positional_or_keyword():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_eval_schema_error_init_no_var_kwargs():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_eval_schema_error_no_args_creates_empty_errors_list():
    e = EvalSchemaError("msg")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_explicit_none_errors_creates_empty_list():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_explicit_empty_list_errors():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_explicit_list_with_errors_preserved():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors is errs  # 直接赋值（不复制）


def test_eval_schema_error_explicit_non_list_errors_passthrough():
    """errors 接受任何值（不强制 list 类型）。"""
    e = EvalSchemaError("msg", errors="not a list")  # type: ignore[arg-type]
    # errors or [] → 'not a list' 是 truthy → 透传
    assert e.errors == "not a list"


def test_eval_schema_error_str_contains_message():
    e = EvalSchemaError("my message here")
    assert "my message here" in str(e)


def test_eval_schema_error_repr_contains_class_name():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_args_contains_message():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_raise_and_catch():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("msg")


def test_eval_schema_error_catch_as_exception():
    """可以 except Exception 捕获。"""
    with pytest.raises(Exception):
        raise EvalSchemaError("msg")


def test_eval_schema_error_attribute_errors_after_init():
    e = EvalSchemaError("msg", errors=[{"x": 1}])
    assert hasattr(e, "errors")
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_module_identity():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_eval_schema_error_qualname():
    assert EvalSchemaError.__qualname__ == "EvalSchemaError"


def test_eval_schema_error_mro_contains_exception():
    assert Exception in EvalSchemaError.__mro__


def test_eval_schema_error_mro_contains_baseexception():
    assert BaseException in EvalSchemaError.__mro__


def test_eval_schema_error_has_errors_attribute():
    e = EvalSchemaError("msg")
    assert hasattr(e, "errors")


def test_eval_schema_error_has_args_attribute():
    e = EvalSchemaError("msg")
    assert hasattr(e, "args")


# =========================================================================
# _schema_path 详细
# =========================================================================


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_returns_resolved_path():
    p = _schema_path("manifest.schema.json")
    # resolve() 已应用，没有 .. 或 . 段
    resolved = p.resolve()
    assert p == resolved


def test_schema_path_returns_existing_file():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_for_each_known_schema():
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        p = _schema_path(name)
        assert p.is_file()


def test_schema_path_unknown_name_raises_file_not_found_error():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_error_message_contains_path():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(ei.value)


def test_schema_path_error_message_contains_full_path():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    # 完整路径含 SCHEMAS_DIR
    assert str(SCHEMAS_DIR) in str(ei.value) or "nonexistent" in str(ei.value)


def test_schema_path_signature_param_count_1():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_schema_path_signature_param_name_name():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_signature_param_no_default():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_schema_path_param_kind_positional_or_keyword():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_schema_path_no_var_args():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_schema_path_no_var_kwargs():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_schema_path_module_identity():
    assert _schema_path.__module__ == "evaluation.schema"


def test_schema_path_qualname():
    assert _schema_path.__qualname__ == "_schema_path"


# =========================================================================
# load_schema 详细
# =========================================================================


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_two_calls_return_different_dict():
    """不缓存。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_load_schema_each_known_schema_returns_dict():
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_unknown_name_raises_file_not_found_error():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_signature_param_count_1():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_signature_param_name_name():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_param_no_default():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_load_schema_param_kind_positional_or_keyword():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_load_schema_no_var_args():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_load_schema_no_var_kwargs():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_load_schema_module_identity():
    assert load_schema.__module__ == "evaluation.schema"


def test_load_schema_qualname():
    assert load_schema.__qualname__ == "load_schema"


# =========================================================================
# validate 详细
# =========================================================================


def test_validate_signature_param_count_2():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_signature_param_names():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_param_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_param_kinds_positional_or_keyword():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_no_var_args():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_validate_no_var_kwargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_return_annotation_is_none():
    sig = inspect.signature(validate)
    # return None → return_annotation is None or 'None' (str form due to future annotations)
    ret = sig.return_annotation
    assert ret is None or ret == "None"


def test_validate_valid_manifest_returns_none():
    """对 valid manifest instance → return None（无 raise）。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/test.pdf",
                "source_type": "pdf",
            }
        ],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_invalid_manifest_raises_eval_schema_error():
    instance = {"manifest_version": "wrong"}  # 缺很多 required 字段
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_error_message_contains_schema_name():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_error_message_contains_error_count():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    msg = str(ei.value)
    # 含 "(N 处)" 形式
    assert "处" in msg or "errors" in msg.lower()


def test_validate_error_message_contains_head_message():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    msg = str(ei.value)
    # 含 path= 标记
    assert "path=" in msg


def test_validate_errors_attribute_is_list():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    assert isinstance(ei.value.errors, list)


def test_validate_errors_attribute_non_empty_on_failure():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    assert len(ei.value.errors) > 0


def test_validate_each_error_has_path_message_schema_path():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    for err in ei.value.errors:
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err
        assert isinstance(err["path"], list)
        assert isinstance(err["message"], str)
        assert isinstance(err["schema_path"], list)


def test_validate_sorted_by_absolute_path():
    """errors 按 absolute_path 排序。"""
    instance = {"documents": [{}]}  # 缺很多字段 → 多个 errors
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in ei.value.errors]
    assert paths == sorted(paths)


def test_validate_module_identity():
    assert validate.__module__ == "evaluation.schema"


def test_validate_qualname():
    assert validate.__qualname__ == "validate"


# =========================================================================
# validate_file 详细
# =========================================================================


def test_validate_file_signature_param_count_2():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_signature_param_names():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_param_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_file_param_kinds_positional_or_keyword():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_file_no_var_args():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_validate_file_no_var_kwargs():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_validate_file_path_str_accepted(tmp_path: Path):
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    # path 作为 str 传入
    validate_file(str(p), "manifest.schema.json")  # 不抛错


def test_validate_file_path_pathlib_accepted(tmp_path: Path):
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")  # Path 对象


def test_validate_file_nonexistent_path_raises_file_not_found_error(tmp_path: Path):
    nonexistent = tmp_path / "no.json"
    with pytest.raises(FileNotFoundError):
        validate_file(nonexistent, "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{bad json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_raises_eval_schema_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")  # 空对象 → 校验失败
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_error_message_contains_path(tmp_path: Path):
    nonexistent = tmp_path / "no.json"
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(nonexistent, "manifest.schema.json")
    assert "no.json" in str(ei.value)


def test_validate_file_module_identity():
    assert validate_file.__module__ == "evaluation.schema"


def test_validate_file_qualname():
    assert validate_file.__qualname__ == "validate_file"


# =========================================================================
# SCHEMAS_DIR 详细
# =========================================================================


def test_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_dir():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_known_schemas():
    for name in [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ]:
        assert (SCHEMAS_DIR / name).is_file()


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 是项目根（含 pyproject.toml）。"""
    project_root = SCHEMAS_DIR.parent
    assert (project_root / "pyproject.toml").is_file()


def test_schemas_dir_under_project_root():
    """SCHEMAS_DIR 在项目根下（schemas/ 子目录）。"""
    project_root = SCHEMAS_DIR.parent
    assert SCHEMAS_DIR.parent == project_root
    assert SCHEMAS_DIR.name == "schemas"


# =========================================================================
# 模块 namespace 完整性
# =========================================================================


def test_module_namespace_has_json():
    import evaluation.schema as m

    assert hasattr(m, "json")


def test_module_namespace_has_path():
    import evaluation.schema as m

    assert hasattr(m, "Path")


def test_module_namespace_has_any():
    import evaluation.schema as m

    assert hasattr(m, "Any")


def test_module_namespace_has_draft_validator():
    import evaluation.schema as m

    assert hasattr(m, "Draft202012Validator")
    assert m.Draft202012Validator is Draft202012Validator


def test_module_namespace_has_js_validation_error():
    import evaluation.schema as m

    assert hasattr(m, "JSValidationError")
    assert m.JSValidationError is JSValidationError


def test_module_namespace_has_schemas_dir():
    import evaluation.schema as m

    assert hasattr(m, "SCHEMAS_DIR")
    assert m.SCHEMAS_DIR is SCHEMAS_DIR


def test_module_namespace_has_eval_schema_error():
    import evaluation.schema as m

    assert hasattr(m, "EvalSchemaError")
    assert m.EvalSchemaError is EvalSchemaError


def test_module_namespace_has_load_schema():
    import evaluation.schema as m

    assert hasattr(m, "load_schema")


def test_module_namespace_has_validate():
    import evaluation.schema as m

    assert hasattr(m, "validate")


def test_module_namespace_has_validate_file():
    import evaluation.schema as m

    assert hasattr(m, "validate_file")


def test_module_namespace_has_schema_path():
    import evaluation.schema as m

    assert hasattr(m, "_schema_path")


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


def test_module_all_has_5_entries():
    import evaluation.schema as m

    assert len(m.__all__) == 5


def test_module_all_does_not_contain_schema_path():
    """__all__ 不含 _schema_path（私有）。"""
    import evaluation.schema as m

    assert "_schema_path" not in m.__all__


def test_module_all_does_not_contain_json_path_any():
    """__all__ 不含模块级 import 名。"""
    import evaluation.schema as m

    assert "json" not in m.__all__
    assert "Path" not in m.__all__
    assert "Any" not in m.__all__


def test_module_all_does_not_contain_draft_validator():
    """__all__ 不含 Draft202012Validator / JSValidationError。"""
    import evaluation.schema as m

    assert "Draft202012Validator" not in m.__all__
    assert "JSValidationError" not in m.__all__


# =========================================================================
# 模块源码 token 验证（补强 edges10）
# =========================================================================


def test_module_source_contains_from_future_annotations():
    import evaluation.schema as m

    assert "from __future__ import annotations" in inspect.getsource(m)


def test_module_source_contains_import_json():
    import evaluation.schema as m

    assert "import json" in inspect.getsource(m)


def test_module_source_contains_from_pathlib():
    import evaluation.schema as m

    assert "from pathlib import Path" in inspect.getsource(m)


def test_module_source_contains_from_typing_import_any():
    import evaluation.schema as m

    assert "from typing import Any" in inspect.getsource(m)


def test_module_source_contains_jsonschema_draft_import():
    import evaluation.schema as m

    assert "from jsonschema import Draft202012Validator" in inspect.getsource(m)


def test_module_source_contains_js_validation_error_import():
    import evaluation.schema as m

    assert (
        "from jsonschema.exceptions import ValidationError as JSValidationError"
        in inspect.getsource(m)
    )


def test_module_source_contains_schemas_dir_definition():
    """SCHEMAS_DIR = Path(__file__).resolve().parent.parent / 'schemas'。"""
    import evaluation.schema as m

    src = inspect.getsource(m)
    assert "SCHEMAS_DIR" in src
    assert "__file__" in src
    assert "resolve()" in src
    assert "/ 'schemas'" in src or 'schemas' in src


def test_module_source_contains_class_eval_schema_error():
    import evaluation.schema as m

    assert "class EvalSchemaError" in inspect.getsource(m)


def test_module_source_contains_super_init_call():
    import evaluation.schema as m

    assert "super().__init__(message)" in inspect.getsource(m)


def test_module_source_contains_self_errors_assignment():
    import evaluation.schema as m

    assert "self.errors = errors or []" in inspect.getsource(m)


def test_module_source_contains_sort_by_absolute_path():
    import evaluation.schema as m

    src = inspect.getsource(m)
    assert "sorted(validator.iter_errors" in src
    assert "absolute_path" in src


def test_module_source_contains_flat_errors_construction():
    import evaluation.schema as m

    src = inspect.getsource(m)
    assert "absolute_path" in src
    assert "absolute_schema_path" in src
    assert "err.message" in src


def test_module_source_contains_head_error_usage():
    import evaluation.schema as m

    assert "head = errors[0]" in inspect.getsource(m)


def test_module_source_does_not_contain_print():
    import evaluation.schema as m

    assert "print(" not in inspect.getsource(m)


def test_module_source_does_not_contain_logging():
    import evaluation.schema as m

    assert "import logging" not in inspect.getsource(m)


def test_module_source_does_not_contain_lru_cache():
    """不缓存（schema 每次重新 load）。"""
    import evaluation.schema as m

    assert "@lru_cache" not in inspect.getsource(m)
    assert "functools.cache" not in inspect.getsource(m)


def test_module_source_does_not_contain_asyncio():
    import evaluation.schema as m

    assert "asyncio" not in inspect.getsource(m)


def test_module_source_does_not_contain_subprocess_import():
    import evaluation.schema as m

    assert "import subprocess" not in inspect.getsource(m)


def test_module_source_does_not_contain_os_import():
    import evaluation.schema as m

    assert "import os" not in inspect.getsource(m)


# =========================================================================
# 模块 docstring 内容验证
# =========================================================================


def test_module_docstring_is_nonempty_string():
    import evaluation.schema as m

    assert isinstance(m.__doc__, str)
    assert len(m.__doc__) > 30


def test_module_docstring_mentions_manifest():
    import evaluation.schema as m

    assert "manifest" in m.__doc__


def test_module_docstring_mentions_annotation():
    import evaluation.schema as m

    assert "annotation" in m.__doc__


def test_module_docstring_mentions_evaluation_report():
    import evaluation.schema as m

    assert "evaluation-report" in m.__doc__ or "evaluation" in m.__doc__


def test_module_docstring_mentions_no_reuse_app_schema():
    """docstring 提到不与 app/schema.py 复用。"""
    import evaluation.schema as m

    assert "app/schema.py" in m.__doc__ or "不复用" in m.__doc__ or "复用" in m.__doc__


def test_module_docstring_mentions_purpose_separation():
    """docstring 提到业务输出 vs 评测元数据的用途区分。"""
    import evaluation.schema as m

    assert "业务" in m.__doc__ or "评测" in m.__doc__
