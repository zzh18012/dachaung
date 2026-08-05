r"""evaluation/schema.py 边角测试 - 第五轮（Round 180）。

补强已有 base/edges/edges2/edges3/edges4（共 472 测试）未覆盖的深度：
- SCHEMAS_DIR 路径精确（resolve 后无 ..、is_dir、父目录是项目根）
- EvalSchemaError 深度（args、str、super 调用、errors 各 None/[]/[err]）
- _schema_path 错误消息含路径
- load_schema 三个 known schema 文件都可加载、每次新 dict
- validate 错误聚合 path/message/schema_path 类型与排序
- validate_file 错误优先级（FileNotFoundError > JSONDecodeError > EvalSchemaError）
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# SCHEMAS_DIR 路径精确
# =========================================================================


def test_schemas_dir_value():
    expected = Path(__file__).resolve().parent.parent / "schemas"
    assert SCHEMAS_DIR == expected


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_resolved():
    """resolve() 后无 .. 段。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_is_dir():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_is_project_root():
    """父目录应包含 pyproject.toml（项目根）。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_parent_name():
    """父目录名应是 dachuang-autonomous 或类似（不是 schemas 自身）。"""
    assert SCHEMAS_DIR.parent.name != "schemas"


def test_schemas_dir_contains_manifest_schema():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_constant_in_module_all():
    import evaluation.schema as mod
    assert "SCHEMAS_DIR" in mod.__all__


# =========================================================================
# EvalSchemaError 深度
# =========================================================================


def test_eval_schema_error_init_signature():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert set(sig.parameters) == {"self", "message", "errors"}


def test_eval_schema_error_errors_default_none_in_signature():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_message_annotation_str():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert "str" in str(sig.parameters["message"].annotation)


def test_eval_schema_error_errors_annotation_optional_list():
    sig = inspect.signature(EvalSchemaError.__init__)
    annotation = str(sig.parameters["errors"].annotation)
    assert "list" in annotation
    assert "None" in annotation


def test_eval_schema_error_no_errors_defaults_to_empty_list():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_explicit_none_errors():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_explicit_empty_list():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_with_errors():
    errs = [{"path": ["x"], "message": "y"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs
    assert e.errors is errs  # 透传同一 list


def test_eval_schema_error_str_returns_message():
    e = EvalSchemaError("my message")
    assert str(e) == "my message"


def test_eval_schema_error_args_only_message():
    """super().__init__(message) → args == (message,)。"""
    e = EvalSchemaError("m", errors=[{"k": "v"}])
    assert e.args == ("m",)


def test_eval_schema_error_inherits_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_value_error():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_not_key_error():
    assert not issubclass(EvalSchemaError, KeyError)


def test_eval_schema_error_caught_specifically():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_caught_as_exception():
    try:
        raise EvalSchemaError("x")
    except Exception:
        pass


def test_eval_schema_error_caught_as_filenotfound_does_not_catch():
    """EvalSchemaError 不是 FileNotFoundError 子类。"""
    try:
        try:
            raise EvalSchemaError("x")
        except FileNotFoundError:
            pytest.fail("EvalSchemaError should not be caught by FileNotFoundError")
    except EvalSchemaError:
        pass


def test_eval_schema_error_docstring_present():
    assert EvalSchemaError.__doc__ is not None


def test_eval_schema_error_two_instances_independent():
    """两个 instance 的 errors list 互不影响。"""
    a = EvalSchemaError("a")
    b = EvalSchemaError("b")
    a.errors.append({"x": 1})
    assert b.errors == []


# =========================================================================
# _schema_path 错误消息
# =========================================================================


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_nonexistent_raises_filenotfound():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc.value)


def test_schema_path_directory_raises_filenotfound():
    """目录不是 file → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".")


def test_schema_path_error_message_contains_path():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc.value)


def test_schema_path_signature():
    sig = inspect.signature(_schema_path)
    assert set(sig.parameters) == {"name"}


def test_schema_path_returns_absolute():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# =========================================================================
# load_schema 三个 known schema
# =========================================================================


def test_load_schema_manifest():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    assert s.get("type") == "object"


def test_load_schema_annotation():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)
    assert s.get("type") == "object"


def test_load_schema_evaluation_report():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)
    assert s.get("type") == "object"


def test_load_schema_each_passes_draft202012():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        Draft202012Validator.check_schema(load_schema(name))


def test_load_schema_each_has_dollar_schema():
    """JSON Schema 标准的 $schema key。"""
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "$schema" in s


def test_load_schema_each_has_properties():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "properties" in s


def test_load_schema_returns_new_dict_each_call():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b
    assert a is not b


def test_load_schema_unknown_raises():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_signature():
    sig = inspect.signature(load_schema)
    assert set(sig.parameters) == {"name"}


def test_load_schema_no_default():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


# =========================================================================
# validate 错误聚合细节
# =========================================================================


def test_validate_no_errors_returns_none():
    """合法 manifest → validate 不抛。"""
    manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # 不抛即过
    validate(manifest, "manifest.schema.json")


def test_validate_invalid_raises_eval_schema_error():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_error_message_contains_schema_name():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_error_message_contains_count():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "处" in str(exc.value)


def test_validate_errors_collected():
    """多个错误都聚合到 errors 字段。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) >= 1


def test_validate_errors_each_has_path_message_schema_path():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert "path" in err
        assert "message" in err
        assert "schema_path" in err


def test_validate_errors_path_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_errors_message_is_str():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["message"], str)


def test_validate_does_not_modify_instance():
    instance = {"manifest_version": "wrong"}
    before = json.loads(json.dumps(instance))
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert instance == before


def test_validate_signature():
    sig = inspect.signature(validate)
    assert set(sig.parameters) == {"instance", "schema_name"}


def test_validate_no_defaults():
    sig = inspect.signature(validate)
    for name in sig.parameters:
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# validate_file 错误优先级
# =========================================================================


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    # 不抛即过
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """目录不是 file → FileNotFoundError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


def test_validate_file_unknown_schema_raises_filenotfound(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_priority_missing_first(tmp_path: Path):
    """FileNotFoundError（文件不存在）优先于其他错误。"""
    # 文件不存在 + schema 不存在 → FileNotFoundError（文件）先抛
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "nonexistent.schema.json")
    # 错误消息应是"待校验文件不存在"
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_priority_jsondecode_before_schema(tmp_path: Path):
    """JSONDecodeError 在 EvalSchemaError 之前。"""
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_signature():
    sig = inspect.signature(validate_file)
    assert set(sig.parameters) == {"path", "schema_name"}


def test_validate_file_no_defaults():
    sig = inspect.signature(validate_file)
    for name in sig.parameters:
        assert sig.parameters[name].default is inspect.Parameter.empty


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import evaluation.schema as mod
    assert mod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_is_list():
    import evaluation.schema as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import evaluation.schema as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_imports_json():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_path():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_draft202012():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "Draft202012Validator" in src


def test_module_imports_jsvalidation_error():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "JSValidationError" in src


def test_module_docstring_present():
    import evaluation.schema as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_separation_from_app_schema():
    """docstring 提及不与 app/schema.py 复用。"""
    import evaluation.schema as mod
    doc = mod.__doc__
    assert "app/schema" in doc.lower() or "不复用" in doc or "分开" in doc


def test_module_no_silence_unused():
    import evaluation.schema as mod
    assert not hasattr(mod, "_silence_unused")


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_idempotent():
    """同输入多次 validate 一致。"""
    for _ in range(3):
        with pytest.raises(EvalSchemaError):
            validate({}, "manifest.schema.json")


def test_load_schema_idempotent():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b


def test_schemas_dir_constant_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_validate_then_validate_file_consistent(tmp_path: Path):
    """validate 与 validate_file 对同输入应一致（都抛或都不抛）。"""
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    # 直接 validate：抛 EvalSchemaError
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")
    # validate_file：同样抛 EvalSchemaError
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_eval_schema_error_with_multiple_errors():
    """构造含多个错误的 EvalSchemaError → errors 列表保留所有。"""
    errs = [
        {"path": ["a"], "message": "err1", "schema_path": ["properties", "a"]},
        {"path": ["b"], "message": "err2", "schema_path": ["properties", "b"]},
    ]
    e = EvalSchemaError("multi", errors=errs)
    assert len(e.errors) == 2
    assert e.errors[0]["path"] == ["a"]
    assert e.errors[1]["path"] == ["b"]
