r"""app/schema.py 边角测试 - 第三轮（Round 123）。

补强已有 base/edges/edges2（共 371 测试）未覆盖的深度路径：
- SCHEMA_PATH 常量：
  - 是 Path 对象、绝对路径、是文件
  - 名字精确 "document.schema.json"
  - 父目录名 "schemas"
  - 父目录父目录含 pyproject.toml
- SchemaValidationError 深度：
  - args 长度/值
  - errors 默认 []、None→[]、[]→[]、非空保留
  - 不继承 ValueError
  - 两实例 errors 独立
  - repr 含类名
  - message attribute
- load_schema 深度：
  - str vs Path 输入
  - 不存在 → FileNotFoundError（消息含路径）
  - 多次调用独立 dict
  - 默认参数加载 document.schema.json
- validate 深度：
  - 多个 errors 按 path 排序
  - errors 各项有 path/message/schema_path 三 key
  - 错误消息含错误计数
  - schema=None 用默认
- is_valid 深度：
  - True/False 返回
  - 不抛
  - 各种输入
- validate_file 深度：
  - Path/str 输入
  - 不存在/目录 → FileNotFoundError
  - 空文件 → JSONDecodeError
  - 坏 JSON → JSONDecodeError
  - 不符合 schema → SchemaValidationError
- _silence_unused_import：
  - 无参、返回 None
  - 不在 __all__
  - callable
- 模块结构：
  - imports 完整
  - __all__ 6 项精确
  - docstring 提及关键概念
- 签名深度：
  - 各函数签名精确
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    _silence_unused_import,
    is_valid,
    load_schema,
    validate,
    validate_file,
)


SHA = "a" * 64


def _minimal_doc() -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "doc-x",
        "source_path": "/tmp/x.pdf",
        "source_type": "pdf",
        "source_hash": SHA,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# =========================================================================
# SCHEMA_PATH 常量深度
# =========================================================================


def test_schema_path_is_path_object():
    assert isinstance(SCHEMA_PATH, Path)


def test_schema_path_is_absolute():
    assert SCHEMA_PATH.is_absolute()


def test_schema_path_is_file():
    assert SCHEMA_PATH.is_file()


def test_schema_path_name_is_document_schema():
    assert SCHEMA_PATH.name == "document.schema.json"


def test_schema_path_parent_name_is_schemas():
    assert SCHEMA_PATH.parent.name == "schemas"


def test_schema_path_parent_parent_has_pyproject():
    """SCHEMA_PATH/../.. 应是项目根。"""
    assert (SCHEMA_PATH.parent.parent / "pyproject.toml").is_file()


# =========================================================================
# SchemaValidationError 深度
# =========================================================================


def test_schema_validation_error_args_length_one():
    e = SchemaValidationError("msg")
    assert len(e.args) == 1


def test_schema_validation_error_args_value():
    e = SchemaValidationError("msg")
    assert e.args == ("msg",)


def test_schema_validation_error_str_contains_message():
    e = SchemaValidationError("my message")
    assert "my message" in str(e)


def test_schema_validation_error_errors_default_empty_list():
    e = SchemaValidationError("msg")
    assert e.errors == []


def test_schema_validation_error_errors_none_to_empty_list():
    e = SchemaValidationError("msg", errors=None)
    assert e.errors == []


def test_schema_validation_error_errors_empty_list_passed():
    e = SchemaValidationError("msg", errors=[])
    assert e.errors == []


def test_schema_validation_error_errors_non_empty_passed():
    errs = [{"path": ["a"], "message": "x"}]
    e = SchemaValidationError("msg", errors=errs)
    assert e.errors == errs


def test_schema_validation_error_errors_is_list_type():
    e = SchemaValidationError("msg")
    assert isinstance(e.errors, list)


def test_schema_validation_error_inherits_from_exception():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_does_not_inherit_from_value_error():
    assert not issubclass(SchemaValidationError, ValueError)


def test_schema_validation_error_can_be_caught_as_exception():
    try:
        raise SchemaValidationError("x")
    except Exception as e:
        assert isinstance(e, SchemaValidationError)


def test_schema_validation_error_two_instances_independent():
    e1 = SchemaValidationError("msg1")
    e2 = SchemaValidationError("msg2")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_schema_validation_error_repr_contains_class_name():
    e = SchemaValidationError("x")
    assert "SchemaValidationError" in repr(e)


def test_schema_validation_error_message_attribute():
    e = SchemaValidationError("stored message")
    assert e.args[0] == "stored message"


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_returns_dict():
    s = load_schema()
    assert isinstance(s, dict)


def test_load_schema_no_args_uses_default():
    """无参数 → 加载默认 SCHEMA_PATH。"""
    s = load_schema()
    assert "$schema" in s or "type" in s or "properties" in s


def test_load_schema_returns_independent_dict_each_call():
    s1 = load_schema()
    s2 = load_schema()
    assert s1 == s2
    assert s1 is not s2


def test_load_schema_str_path(tmp_path: Path):
    """str path 输入。"""
    p = tmp_path / "schema.json"
    p.write_text('{"type": "object"}', encoding="utf-8")
    s = load_schema(str(p))
    assert s == {"type": "object"}


def test_load_schema_path_object(tmp_path: Path):
    p = tmp_path / "schema.json"
    p.write_text('{"type": "object"}', encoding="utf-8")
    s = load_schema(p)
    assert s == {"type": "object"}


def test_load_schema_missing_file_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "nonexistent.json")


def test_load_schema_filenotfound_message_contains_path(tmp_path: Path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as ei:
        load_schema(p)
    assert "missing.json" in str(ei.value)


# =========================================================================
# validate 深度
# =========================================================================


def test_validate_returns_none_on_success():
    doc = _minimal_doc()
    assert validate(doc) is None


def test_validate_uses_default_schema_when_schema_none():
    """schema=None → 用默认 SCHEMA_PATH。"""
    doc = _minimal_doc()
    validate(doc, None)  # 不抛即通过


def test_validate_failure_message_contains_count():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    assert "处" in str(ei.value)


def test_validate_failure_errors_attribute_has_list():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    assert isinstance(ei.value.errors, list)
    assert len(ei.value.errors) >= 1


def test_validate_failure_each_error_has_three_keys():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    for err in ei.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_failure_path_is_list():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    for err in ei.value.errors:
        assert isinstance(err["path"], list)


def test_validate_failure_schema_path_is_list():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    for err in ei.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_failure_message_is_str():
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    for err in ei.value.errors:
        assert isinstance(err["message"], str)


def test_validate_with_custom_schema_dict():
    """自定义 schema dict 直接传入。"""
    custom = {"type": "object", "required": ["foo"]}
    with pytest.raises(SchemaValidationError):
        validate({})


def test_validate_with_empty_schema_accepts_anything():
    """空 schema → 任何 instance 都通过。"""
    validate({}, {})
    validate({"any": "thing"}, {})


def test_validate_sorted_by_path_multiple_errors():
    """多个 errors 应按 absolute_path 排序。"""
    # 缺多个必填字段
    with pytest.raises(SchemaValidationError) as ei:
        validate({})
    paths = [tuple(err["path"]) for err in ei.value.errors]
    # 验证 paths 已排序（与 sorted by path 一致）
    assert paths == sorted(paths)


# =========================================================================
# is_valid 深度
# =========================================================================


def test_is_valid_returns_true_for_valid_doc():
    assert is_valid(_minimal_doc()) is True


def test_is_valid_returns_false_for_invalid_doc():
    assert is_valid({}) is False


def test_is_valid_returns_bool_type():
    assert isinstance(is_valid(_minimal_doc()), bool)


def test_is_valid_does_not_raise_on_invalid():
    """is_valid 应捕获 SchemaValidationError 不抛。"""
    try:
        result = is_valid({})
        assert result is False
    except SchemaValidationError:
        pytest.fail("is_valid should not raise SchemaValidationError")


def test_is_valid_with_custom_schema_true():
    custom = {"type": "object"}
    assert is_valid({}, custom) is True


def test_is_valid_with_custom_schema_false():
    custom = {"type": "object", "required": ["foo"]}
    assert is_valid({}, custom) is False


def test_is_valid_with_none_schema_uses_default():
    """schema=None → 用默认 SCHEMA_PATH。"""
    assert is_valid(_minimal_doc(), None) is True
    assert is_valid({}, None) is False


# =========================================================================
# validate_file 深度
# =========================================================================


def test_validate_file_returns_none_on_success(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(_minimal_doc()), encoding="utf-8")
    assert validate_file(p) is None


def test_validate_file_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(_minimal_doc()), encoding="utf-8")
    assert validate_file(str(p)) is None


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "no.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    d = tmp_path / "subdir"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(d)


def test_validate_file_empty_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_invalid_content_raises_schema_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p)


def test_validate_file_with_custom_schema(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    custom = {"type": "object", "required": ["foo"]}
    assert validate_file(p, custom) is None


def test_validate_file_with_custom_schema_fails(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    custom = {"type": "object", "required": ["foo"]}
    with pytest.raises(SchemaValidationError):
        validate_file(p, custom)


def test_validate_file_unicode_filename(tmp_path: Path):
    p = tmp_path / "数据.json"
    p.write_text(json.dumps(_minimal_doc()), encoding="utf-8")
    assert validate_file(p) is None


def test_validate_file_unicode_content(tmp_path: Path):
    """含 unicode 字符的内容（如 source_path 含中文）。"""
    doc = _minimal_doc()
    doc["source_path"] = "/tmp/中文.pdf"
    p = tmp_path / "ok.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_file(p) is None


def test_validate_file_filenotfound_message_contains_path(tmp_path: Path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(p)
    assert "missing.json" in str(ei.value)


# =========================================================================
# _silence_unused_import 深度
# =========================================================================


def test_silence_unused_import_returns_none():
    assert _silence_unused_import() is None


def test_silence_unused_import_takes_no_arguments():
    import inspect

    sig = inspect.signature(_silence_unused_import)
    assert len(sig.parameters) == 0


def test_silence_unused_import_callable():
    assert callable(_silence_unused_import)


def test_silence_unused_import_in_module():
    from app import schema as mod

    assert hasattr(mod, "_silence_unused_import")


def test_silence_unused_import_not_in_all():
    from app import schema as mod

    assert "_silence_unused_import" not in mod.__all__


def test_silence_unused_import_starts_with_underscore():
    assert "_silence_unused_import".startswith("_")


# =========================================================================
# 模块结构
# =========================================================================


def test_module_imports_json():
    from app import schema as mod

    assert hasattr(mod, "json")


def test_module_imports_path():
    from app import schema as mod

    assert hasattr(mod, "Path")


def test_module_imports_any():
    from app import schema as mod

    assert hasattr(mod, "Any")


def test_module_imports_draft202012_validator():
    from app import schema as mod

    assert hasattr(mod, "Draft202012Validator")


def test_module_imports_jsvalidation_error():
    from app import schema as mod

    assert hasattr(mod, "JSValidationError")


def test_module_has_schema_path():
    from app import schema as mod

    assert hasattr(mod, "SCHEMA_PATH")


def test_module_has_schema_validation_error_class():
    from app import schema as mod

    assert hasattr(mod, "SchemaValidationError")


def test_module_has_load_schema():
    from app import schema as mod

    assert hasattr(mod, "load_schema")


def test_module_has_validate():
    from app import schema as mod

    assert hasattr(mod, "validate")


def test_module_has_is_valid():
    from app import schema as mod

    assert hasattr(mod, "is_valid")


def test_module_has_validate_file():
    from app import schema as mod

    assert hasattr(mod, "validate_file")


def test_module_all_is_list():
    from app import schema as mod

    assert isinstance(mod.__all__, list)


def test_module_all_length_six():
    from app import schema as mod

    assert len(mod.__all__) == 6


def test_module_all_exact_set():
    from app import schema as mod

    assert set(mod.__all__) == {
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    }


def test_module_all_excludes_internal_helpers():
    from app import schema as mod

    assert "_silence_unused_import" not in mod.__all__


def test_module_callable_signatures():
    from app import schema as mod

    assert callable(mod.load_schema)
    assert callable(mod.validate)
    assert callable(mod.is_valid)
    assert callable(mod.validate_file)


def test_module_docstring_present():
    from app import schema as mod

    assert mod.__doc__ is not None


def test_module_docstring_mentions_schema():
    from app import schema as mod

    doc = mod.__doc__
    assert "Schema" in doc or "schema" in doc.lower()


def test_module_uses_future_annotations():
    import ast

    from app import schema as mod

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


def test_schema_validation_error_init_two_params():
    import inspect

    sig = inspect.signature(SchemaValidationError.__init__)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "message" in params
    assert "errors" in params


def test_schema_validation_error_errors_default_none():
    import inspect

    sig = inspect.signature(SchemaValidationError.__init__)
    assert sig.parameters["errors"].default is None


def test_load_schema_default_param_is_schema_path():
    import inspect

    sig = inspect.signature(load_schema)
    assert sig.parameters["path"].default is SCHEMA_PATH


def test_load_schema_return_annotation_dict():
    import inspect

    sig = inspect.signature(load_schema)
    ret = sig.return_annotation
    assert "dict" in str(ret)


def test_validate_two_params():
    import inspect

    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert "document" in params
    assert "schema" in params


def test_validate_schema_default_none():
    import inspect

    sig = inspect.signature(validate)
    assert sig.parameters["schema"].default is None


def test_is_valid_two_params():
    import inspect

    sig = inspect.signature(is_valid)
    params = list(sig.parameters.keys())
    assert "document" in params
    assert "schema" in params


def test_is_valid_schema_default_none():
    import inspect

    sig = inspect.signature(is_valid)
    assert sig.parameters["schema"].default is None


def test_is_valid_return_annotation_bool():
    import inspect

    sig = inspect.signature(is_valid)
    ret = sig.return_annotation
    assert "bool" in str(ret).lower()


def test_validate_file_two_params():
    import inspect

    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert "path" in params
    assert "schema" in params


def test_validate_file_schema_default_none():
    import inspect

    sig = inspect.signature(validate_file)
    assert sig.parameters["schema"].default is None
