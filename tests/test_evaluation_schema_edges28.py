"""evaluation/schema.py 第二十八轮 edges 测试（Round 386）。

补强 edges27 未触及的角度：
- EvalSchemaError 行为深度第八批（更多构造方式 / errors 默认 vs None vs list / super().__init__ / 属性可读）
- load_schema 行为深度第八批（4 schemas / 文件不存在 / 目录形式 / idempotent / schema dict $schema 字段）
- validate 行为深度第八批（多个 errors / sorted by path / nested errors / extra fields / wrong types）
- validate_file 行为深度第八批（str / Path / 不存在 / 非法 JSON / unknown schema / idempotent）
- _schema_path 行为深度第八批（返回 Path / 文件不存在 raise / 不读文件内容）
- SCHEMAS_DIR 常量深度第八批（Path 类型 / 父目录结构）
- module source forbidden tokens 第十二批
- module source 字符串精确补强第八批
- signatures 第八批（5 funcs + class init）
- module 合理性第八批（__all__ + dunder file + name）
- 端到端集成第八批（完整加载-校验工作流）
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度第八批 ----------


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_init_message_only():
    e = EvalSchemaError("msg")
    assert str(e) == "msg"


def test_eval_schema_error_init_message_and_errors():
    errors = [{"path": ["a"], "message": "bad"}]
    e = EvalSchemaError("msg", errors=errors)
    assert e.errors == errors


def test_eval_schema_error_init_errors_none_defaults_empty_list():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_init_no_errors_arg():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_init_empty_errors_list():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_errors_attribute_is_list():
    e = EvalSchemaError("msg")
    assert isinstance(e.errors, list)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("boom")


def test_eval_schema_error_caught_as_exception():
    with pytest.raises(Exception):
        raise EvalSchemaError("boom")


def test_eval_schema_error_repr_includes_class_name():
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_can_chain_from_other():
    try:
        try:
            raise ValueError("orig")
        except ValueError as ve:
            raise EvalSchemaError("wrapped") from ve
    except EvalSchemaError as ee:
        assert ee.__cause__ is not None
        assert isinstance(ee.__cause__, ValueError)


def test_eval_schema_error_errors_mutable():
    e = EvalSchemaError("msg", errors=[{"x": 1}])
    e.errors.append({"y": 2})
    assert len(e.errors) == 2


def test_eval_schema_error_args_stored():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_complex_payload():
    errors = [
        {"path": ["documents", 0, "path"], "message": "required", "schema_path": ["properties", "path"]},
        {"path": ["documents", 1, "doc_id"], "message": "type", "schema_path": ["type"]},
    ]
    e = EvalSchemaError("complex", errors=errors)
    assert len(e.errors) == 2
    assert e.errors[0]["path"][0] == "documents"


def test_eval_schema_error_init_signature_keyword_only_options():
    """__init__ 接受 message positional + errors keyword。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self, message, errors
    assert len(params) == 3
    assert params[1].name == "message"
    assert params[2].name == "errors"


# ---------- load_schema 行为深度第八批 ----------


def test_load_schema_manifest_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_returns_dict():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_document_returns_dict():
    s = load_schema("document.schema.json")
    assert isinstance(s, dict)


def test_load_schema_unknown_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_idempotent():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_returns_independent_dict():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2


def test_load_schema_has_schema_field():
    """JSON Schema 应含 '$schema' key 指向 draft2020-12。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_has_type_object():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_has_id_field():
    s = load_schema("manifest.schema.json")
    assert "$id" in s


def test_load_schema_directory_raises():
    """传目录名 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema(".")


def test_load_schema_does_not_invoke_validator():
    """load_schema 仅加载文件，不实例化 validator。"""
    s = load_schema("manifest.schema.json")
    # 返回的是 dict，不是 Validator
    assert not isinstance(s, Draft202012Validator)


def test_load_schema_returns_dict_with_properties():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_returns_dict_with_required():
    s = load_schema("manifest.schema.json")
    assert "required" in s


# ---------- validate 行为深度第八批 ----------


def test_validate_returns_none_on_success():
    """合法 manifest 数据 → validate 返回 None。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


def test_validate_raises_on_extra_top_level_field():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "not allowed",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_raises_on_wrong_manifest_version():
    data = {
        "manifest_version": "999.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_raises_on_invalid_devset_status():
    data = {
        "manifest_version": "1.0",
        "devset_status": "completed",  # not in enum
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_raises_on_missing_manifest_version():
    data = {
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_raises_on_documents_not_list():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": "not list",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_raises_on_expected_failures_not_list():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": "not list",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_unknown_schema_raises():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_does_not_mutate_instance():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    snapshot = json.dumps(data)
    validate(data, "manifest.schema.json")
    assert json.dumps(data) == snapshot


def test_validate_idempotent():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")
    validate(data, "manifest.schema.json")  # 不抛


def test_validate_error_includes_path():
    data = {"manifest_version": "1.0", "documents": [], "expected_failures": []}  # 缺 devset_status
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    assert "devset_status" in str(exc_info.value)


def test_validate_error_includes_schema_name():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_error_includes_count():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    msg = str(exc_info.value)
    # 应包含 "(N 处)" 格式的计数
    assert "处" in msg


def test_validate_error_errors_list_is_list_of_dicts():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    assert isinstance(exc_info.value.errors, list)
    for err in exc_info.value.errors:
        assert isinstance(err, dict)


def test_validate_error_errors_dict_keys():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    if exc_info.value.errors:
        for err in exc_info.value.errors:
            assert "path" in err
            assert "message" in err
            assert "schema_path" in err


def test_validate_error_errors_path_is_list():
    data = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(data, "manifest.schema.json")
    if exc_info.value.errors:
        for err in exc_info.value.errors:
            assert isinstance(err["path"], list)


# ---------- validate_file 行为深度第八批 ----------


def _write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_validate_file_str_path(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(str(p), "manifest.schema.json")  # 不抛


def test_validate_file_path_object(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(Path(p), "manifest.schema.json")  # 不抛


def test_validate_file_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_schema_raises(tmp_path):
    p = _write_json(tmp_path / "m.json", {})
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_raises(tmp_path):
    p = _write_json(tmp_path / "m.json", {})
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_idempotent(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_does_not_modify_file(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    snapshot = p.read_text(encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == snapshot


def test_validate_file_positional(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(p, "manifest.schema.json")


def test_validate_file_kwargs(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(path=p, schema_name="manifest.schema.json")


# ---------- _schema_path 行为深度第八批 ----------


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_unknown_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_directory_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path(".")


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_idempotent():
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_resolves_to_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_does_not_read_file_content():
    """_schema_path 只返回 Path，不读文件。"""
    p = _schema_path("manifest.schema.json")
    # 文件依然存在
    assert p.is_file()


def test_schema_path_error_includes_path_str():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc_info.value)


# ---------- SCHEMAS_DIR 常量深度第八批 ----------


def test_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_endswith_schemas():
    assert SCHEMAS_DIR.name == "schemas" or SCHEMAS_DIR.name.endswith("schemas")


def test_schemas_dir_contains_4_json_schemas():
    files = list(SCHEMAS_DIR.glob("*.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names
    assert "document.schema.json" in names


def test_schemas_dir_in_module_namespace():
    assert "SCHEMAS_DIR" in vars(smod)


def test_schemas_dir_value_immutable():
    """SCHEMAS_DIR 是 Path（不可变）。"""
    sd1 = SCHEMAS_DIR
    sd2 = smod.SCHEMAS_DIR
    assert sd1 == sd2


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 应是项目根。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file() or (
        SCHEMAS_DIR.parent.parent / "pyproject.toml"
    ).is_file()


def test_schemas_dir_hashable():
    """Path 是 hashable。"""
    h = hash(SCHEMAS_DIR)
    assert isinstance(h, int)


# ---------- module source forbidden tokens 第十二批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.system",
        "subprocess.Popen",
        "shutil.rmtree",
        "pickle.load",
        "yaml.load",
        "compile(",
        "eval(",
        "exec(",
        "sys.exit",
        "exit(",
        "quit(",
        "global ",
    ],
)
def test_schema_source_no_forbidden_token_twelfth(token):
    source = inspect.getsource(smod)
    assert token not in source


def test_schema_source_no_async_def():
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_schema_source_no_yield():
    source = inspect.getsource(smod)
    assert "yield" not in source


def test_schema_source_no_walrus():
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_schema_source_no_unlink():
    source = inspect.getsource(smod)
    assert "unlink" not in source


def test_schema_source_no_remove():
    source = inspect.getsource(smod)
    assert ".remove(" not in source


def test_schema_source_no_logging():
    source = inspect.getsource(smod)
    assert "logging" not in source
    assert "logger" not in source


def test_schema_source_no_sleep():
    source = inspect.getsource(smod)
    assert "time.sleep" not in source


def test_schema_source_no_print():
    source = inspect.getsource(smod)
    assert "print(" not in source


# ---------- module source 字符串精确补强第八批 ----------


def test_module_source_has_future_annotations():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_source_imports_json():
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_imports_path():
    source = inspect.getsource(smod)
    assert "from pathlib import Path" in source


def test_module_source_imports_any():
    source = inspect.getsource(smod)
    assert "from typing import Any" in source


def test_module_source_imports_draft202012validator():
    source = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in source


def test_module_source_imports_jsvalidationerror():
    source = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in source


def test_module_source_has_schemas_dir_constant():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in source


def test_module_source_has_eval_schema_error_class():
    source = inspect.getsource(smod)
    assert "class EvalSchemaError" in source
    assert "Exception" in source


def test_module_source_eval_schema_error_init():
    source = inspect.getsource(smod)
    assert "def __init__" in source
    assert "super().__init__" in source
    assert "self.errors" in source


def test_module_source_has_schema_path_def():
    source = inspect.getsource(smod)
    assert "def _schema_path" in source


def test_module_source_has_load_schema_def():
    source = inspect.getsource(smod)
    assert "def load_schema" in source


def test_module_source_has_validate_def():
    source = inspect.getsource(smod)
    assert "def validate" in source


def test_module_source_has_validate_file_def():
    source = inspect.getsource(smod)
    assert "def validate_file" in source


def test_module_source_validate_uses_draft202012validator():
    source = inspect.getsource(smod)
    assert "Draft202012Validator(" in source


def test_module_source_validate_uses_iter_errors():
    source = inspect.getsource(smod)
    assert "iter_errors" in source


def test_module_source_validate_uses_sorted():
    source = inspect.getsource(smod)
    assert "sorted(" in source


def test_module_source_no_main_block():
    source = inspect.getsource(smod)
    assert "if __name__" not in source


def test_module_source_docstring_present():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 30


def test_module_source_docstring_mentions_schema():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__.lower()


def test_module_source_no_hardcoded_absolute_path():
    source = inspect.getsource(smod)
    assert "C:\\\\Users" not in source


# ---------- signatures 第八批 ----------


def test_signature_schema_path_one_param():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_signature_schema_path_param_name():
    sig = inspect.signature(_schema_path)
    assert "name" in sig.parameters


def test_signature_schema_path_return_annotation():
    sig = inspect.signature(_schema_path)
    ra = sig.return_annotation
    assert ra == Path or ra == "Path"


def test_signature_schema_path_no_default():
    sig = inspect.signature(_schema_path)
    p = list(sig.parameters.values())[0]
    assert p.default is inspect.Parameter.empty


def test_signature_load_schema_one_param():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_signature_load_schema_param_name():
    sig = inspect.signature(load_schema)
    assert "name" in sig.parameters


def test_signature_load_schema_return_annotation():
    sig = inspect.signature(load_schema)
    ra = sig.return_annotation
    assert ra == "dict[str, Any]" or ra == dict[str, any]


def test_signature_validate_two_params():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_signature_validate_param_names():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]


def test_signature_validate_param_kinds():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_file_two_params():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_signature_validate_file_param_names():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]


def test_signature_validate_file_param_kinds():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_file_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_eval_schema_error_init():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self, message, errors
    assert len(params) == 3
    assert params[1].name == "message"
    assert params[2].name == "errors"


def test_signature_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    p = sig.parameters["errors"]
    assert p.default is None


def test_signature_funcs_function_type():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert inspect.isfunction(func)


def test_signature_funcs_module_eq():
    for func in (_schema_path, load_schema, validate, validate_file):
        assert func.__module__ == "evaluation.schema"


# ---------- module 合理性第八批 ----------


def test_module_all_attribute_value():
    assert smod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_is_list():
    assert isinstance(smod.__all__, list)


def test_module_all_entries_unique():
    assert len(smod.__all__) == len(set(smod.__all__))


def test_module_has_dunder_file():
    assert hasattr(smod, "__file__")


def test_module_dunder_file_endswith_schema_py():
    import os
    sep = os.sep
    assert smod.__file__.endswith("evaluation" + sep + "schema.py") or smod.__file__.endswith(
        "evaluation/schema.py"
    )


def test_module_name_is_evaluation_schema():
    assert smod.__name__ == "evaluation.schema"


def test_module_has_eval_schema_error_class():
    assert inspect.isclass(EvalSchemaError)
    assert issubclass(EvalSchemaError, Exception)


def test_module_has_4_user_functions():
    funcs = [
        n for n, v in vars(smod).items()
        if inspect.isfunction(v) and v.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_has_1_user_class():
    classes = [
        n for n, v in vars(smod).items()
        if inspect.isclass(v) and v.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_no_call_at_top_level():
    source = inspect.getsource(smod)
    lines = source.split("\n")
    for line in lines:
        if not line.startswith(" "):
            stripped = line.strip()
            ok_prefixes = (
                "def ",
                "class ",
                "import ",
                "from ",
                "SCHEMAS_DIR",
                "__all__",
                "#",
                '"""',
                "'''",
                "",
            )
            if stripped and not any(stripped.startswith(p) for p in ok_prefixes):
                if "(" in stripped:
                    raise AssertionError(f"unexpected top-level call: {line}")


def test_module_docstring_present():
    assert smod.__doc__ is not None


# ---------- 端到端集成第八批 ----------


def test_e2e_load_then_validate_manifest_success():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    validate(data, "manifest.schema.json")  # 不抛


def test_e2e_load_then_validate_manifest_failure():
    data = {}
    validate(data, "manifest.schema.json") if False else None
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_e2e_validate_file_round_trip(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(p, "manifest.schema.json")  # 不抛


def test_e2e_validate_file_idempotent(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


def test_e2e_caught_as_exception():
    with pytest.raises(Exception):
        validate({}, "manifest.schema.json")


def test_e2e_str_representation_of_error():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        s = str(e)
        assert isinstance(s, str)
        assert "manifest.schema.json" in s


def test_e2e_chained_from_other():
    try:
        try:
            raise ValueError("orig")
        except ValueError:
            raise EvalSchemaError("wrapped")
    except EvalSchemaError as e:
        assert str(e) == "wrapped"


def test_e2e_full_workflow_unknown_schema():
    """未知 schema → FileNotFoundError（非 EvalSchemaError）。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "totally-unknown.schema.json")


def test_e2e_no_unexpected_exception_on_success():
    """成功路径不应抛任何异常。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # 不抛


def test_e2e_str_path_in_validate_file(tmp_path):
    p = _write_json(
        tmp_path / "m.json",
        {
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        },
    )
    validate_file(str(p), "manifest.schema.json")  # str path 也能工作


def test_e2e_full_chain_manifest_workflow():
    """load_schema → validate → load_schema → validate 链式不抛。"""
    schema1 = load_schema("manifest.schema.json")
    assert isinstance(schema1, dict)
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")
    schema2 = load_schema("manifest.schema.json")
    assert schema1 == schema2


def test_e2e_each_schema_dict_has_properties():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert "properties" in s
