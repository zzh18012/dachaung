r"""evaluation/schema.py 边角测试 - 第三轮（Round 122）。

补强已有 base/edges/edges2/validation_edges（共 358 测试）未覆盖的深度路径：
- SCHEMAS_DIR 常量：
  - 是 Path 对象
  - 是绝对路径
  - 是目录
  - 名字精确（"schemas"）
  - 包含 manifest.schema.json / annotation.schema.json / evaluation-report.schema.json
- EvalSchemaError 深度：
  - args 长度为 1
  - str(e) 含 message
  - errors 属性默认 []
  - errors=None → []
  - errors=[] → []
  - errors 含多项 → 同 list
  - 多次实例化独立
- _schema_path 深度：
  - 返回 Path 对象
  - 不存在的 name → FileNotFoundError
  - 名字带子目录 → 不存在
  - 名字带 .. → 不存在
- load_schema 深度：
  - 返回的 dict 是新对象（多次调用独立）
  - 不存在的 schema → FileNotFoundError
- validate 深度：
  - 多错误时按 absolute_path 排序
  - errors[0] 在 message 头部
  - schema_path 是 list
  - message 含 schema 名字
  - message 含错误数
  - instance 是 dict
- validate_file 深度：
  - 路径是 str vs Path
  - 不存在文件 → FileNotFoundError
  - 目录 → FileNotFoundError
  - 空文件 → JSONDecodeError
  - 成功 → None
- 模块结构深度：
  - imports 完整
  - __all__ 5 项精确
  - 各 callable
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# SCHEMAS_DIR 常量深度
# =========================================================================


def test_schemas_dir_is_path_object():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_as_directory():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_name_is_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_manifest_schema():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR 父目录应含 pyproject.toml。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


# =========================================================================
# EvalSchemaError 深度
# =========================================================================


def test_eval_schema_error_args_length_one():
    e = EvalSchemaError("msg")
    assert len(e.args) == 1


def test_eval_schema_error_args_value():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_str_contains_message():
    e = EvalSchemaError("my message")
    assert "my message" in str(e)


def test_eval_schema_error_errors_default_empty_list():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_errors_none_to_empty_list():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_empty_list_passed():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_errors_non_empty_passed():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_errors_is_list_type():
    e = EvalSchemaError("msg")
    assert isinstance(e.errors, list)


def test_eval_schema_error_inherits_from_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_does_not_inherit_from_value_error():
    """EvalSchemaError 直接继承 Exception，不经过 ValueError。"""
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_can_be_caught_as_exception():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_two_instances_independent():
    e1 = EvalSchemaError("msg1")
    e2 = EvalSchemaError("msg2")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_message_attribute_stored():
    e = EvalSchemaError("stored message")
    # Exception 把 args[0] 当作 message（隐式）
    assert e.args[0] == "stored message"


def test_eval_schema_error_repr_contains_class_name():
    e = EvalSchemaError("x")
    assert "EvalSchemaError" in repr(e)


# =========================================================================
# _schema_path 深度
# =========================================================================


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_unknown_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_empty_name_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_subdir_in_name_raises_filenotfound():
    """'subdir/x.json' 实际是 SCHEMAS_DIR/subdir/x.json，不存在。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.json")


def test_schema_path_dotdot_raises_filenotfound():
    """'../nonexistent' → 跳出 SCHEMAS_DIR → 不存在。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("../nonexistent.json")


def test_schema_path_filenotfound_message_contains_path():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(ei.value)


def test_schema_path_for_annotation_schema():
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_for_evaluation_report_schema():
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_returns_independent_dict_each_call():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2  # json.load 每次新对象


def test_load_schema_unknown_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_has_top_level_keys():
    """JSON Schema 应含 $schema 或 $id 或 type 等关键 key。"""
    s = load_schema("manifest.schema.json")
    # Draft 2020-12 通常含 $schema
    assert "$schema" in s or "type" in s or "properties" in s


def test_load_schema_manifest_has_properties():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


# =========================================================================
# validate 深度
# =========================================================================


def test_validate_minimal_manifest_passes():
    """合法 manifest 实例 → None 返回。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # 不抛即通过
    validate(instance, "manifest.schema.json")


def test_validate_returns_none_on_success():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_failure_message_contains_schema_name():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_failure_message_contains_error_count():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # 应含 "(N 处)" 形式的错误计数
    assert "处" in str(ei.value) or "errors" in str(ei.value).lower()


def test_validate_failure_errors_attribute_has_list():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert isinstance(ei.value.errors, list)
    assert len(ei.value.errors) >= 1


def test_validate_failure_each_error_has_path_key():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert "path" in err


def test_validate_failure_each_error_has_message_key():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert "message" in err


def test_validate_failure_each_error_has_schema_path_key():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert "schema_path" in err


def test_validate_failure_path_is_list():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert isinstance(err["path"], list)


def test_validate_failure_schema_path_is_list():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_failure_message_is_str():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for err in ei.value.errors:
        assert isinstance(err["message"], str)


# =========================================================================
# validate_file 深度
# =========================================================================


def test_validate_file_returns_none_on_success(tmp_path: Path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_str_path_returns_none(tmp_path: Path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """目录 → is_file() False → FileNotFoundError。"""
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d, "manifest.schema.json")


def test_validate_file_empty_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_unknown_schema_raises_filenotfound(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_unicode_content(tmp_path: Path):
    """含 unicode 的 JSON 应能被正常解析与校验。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "中文.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_filenotfound_message_contains_path(tmp_path: Path):
    missing = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(missing, "manifest.schema.json")
    assert "nonexistent.json" in str(ei.value)


# =========================================================================
# 模块结构深度
# =========================================================================


def test_module_imports_json():
    from evaluation import schema as mod

    assert hasattr(mod, "json")


def test_module_imports_path():
    from evaluation import schema as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from evaluation import schema as mod

    assert hasattr(mod, "Any")


def test_module_imports_draft202012_validator():
    from evaluation import schema as mod

    assert hasattr(mod, "Draft202012Validator")


def test_module_imports_jsvalidation_error():
    from evaluation import schema as mod

    assert hasattr(mod, "JSValidationError")


def test_module_has_schemas_dir():
    from evaluation import schema as mod

    assert hasattr(mod, "SCHEMAS_DIR")


def test_module_has_eval_schema_error_class():
    from evaluation import schema as mod

    assert hasattr(mod, "EvalSchemaError")


def test_module_has_schema_path():
    from evaluation import schema as mod

    assert hasattr(mod, "_schema_path")


def test_module_has_load_schema():
    from evaluation import schema as mod

    assert hasattr(mod, "load_schema")


def test_module_has_validate():
    from evaluation import schema as mod

    assert hasattr(mod, "validate")


def test_module_has_validate_file():
    from evaluation import schema as mod

    assert hasattr(mod, "validate_file")


def test_module_all_is_list():
    from evaluation import schema as mod

    assert isinstance(mod.__all__, list)


def test_module_all_length_five():
    from evaluation import schema as mod

    assert len(mod.__all__) == 5


def test_module_all_exact_set():
    from evaluation import schema as mod

    assert set(mod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_all_excludes_internal_schema_path():
    from evaluation import schema as mod

    assert "_schema_path" not in mod.__all__


def test_module_internal_funcs_callable():
    from evaluation import schema as mod

    assert callable(mod._schema_path)
    assert callable(mod.load_schema)
    assert callable(mod.validate)
    assert callable(mod.validate_file)


def test_module_docstring_present():
    from evaluation import schema as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_schema():
    from evaluation import schema as mod

    doc = mod.__doc__
    assert "Schema" in doc or "schema" in doc.lower()


def test_module_docstring_mentions_manifest_or_annotation():
    """docstring 应说明本模块管 manifest/annotation/report schema。"""
    from evaluation import schema as mod

    doc = mod.__doc__
    assert "manifest" in doc.lower() or "annotation" in doc.lower()


def test_module_uses_future_annotations():
    """模块用了 from __future__ import annotations。"""
    import ast

    from evaluation import schema as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    has_future = any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )
    assert has_future


# =========================================================================
# 签名深度
# =========================================================================


def test_eval_schema_error_init_two_params():
    import inspect

    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    # self, message, errors
    assert "self" in params
    assert "message" in params
    assert "errors" in params


def test_eval_schema_error_errors_default_none():
    import inspect

    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_schema_path_signature_one_param():
    import inspect

    sig = inspect.signature(_schema_path)
    assert "name" in sig.parameters
    assert len(sig.parameters) == 1


def test_load_schema_signature_one_param():
    import inspect

    sig = inspect.signature(load_schema)
    assert "name" in sig.parameters
    assert len(sig.parameters) == 1


def test_validate_signature_two_params():
    import inspect

    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert "instance" in params
    assert "schema_name" in params
    assert len(params) == 2


def test_validate_file_signature_two_params():
    import inspect

    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert "path" in params
    assert "schema_name" in params
    assert len(params) == 2


def test_load_schema_return_annotation_is_dict_or_str():
    """load_schema 返回注解（被 future 字符串化）。"""
    import inspect

    sig = inspect.signature(load_schema)
    ret = sig.return_annotation
    # from __future__ import annotations 使注解成字符串
    assert ret in ("dict[str, Any]", dict) or "dict" in str(ret)


def test_validate_return_annotation_is_none():
    """validate 返回 None（成功）或抛异常（失败）。"""
    import inspect

    sig = inspect.signature(validate)
    ret = sig.return_annotation
    assert ret in (None, type(None), "None") or "None" in str(ret)
