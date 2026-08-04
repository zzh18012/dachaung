r"""app/schema.py 边角测试 - 第五轮（Round 141）。

补强已有 base/edges/edges2/edges3（共 464 测试）未覆盖的深度：
- SchemaValidationError 类行为（errors 默认空、message 透传）
- load_schema 路径处理（Path / str / 不存在）
- validate 错误聚合（多错误排序、首错误 message）
- is_valid 异常吞咽
- validate_file 文件 IO 边界
- SCHEMA_PATH 常量
- 模块结构与签名
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest

from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    is_valid,
    load_schema,
    validate,
    validate_file,
)
from app.schema import (
    __all__ as schema_all,
)


# =========================================================================
# SCHEMA_PATH 常量
# =========================================================================


def test_schema_path_is_path():
    assert isinstance(SCHEMA_PATH, Path)


def test_schema_path_points_to_document_schema():
    assert SCHEMA_PATH.name == "document.schema.json"


def test_schema_path_exists():
    """SCHEMA_PATH 指向打包的真实 schema 文件。"""
    assert SCHEMA_PATH.is_file()


def test_schema_path_resolved():
    """SCHEMA_PATH 是 resolve 后的绝对路径。"""
    assert SCHEMA_PATH.is_absolute()


# =========================================================================
# SchemaValidationError 深度
# =========================================================================


def test_schema_validation_error_message_only():
    e = SchemaValidationError("just message")
    assert str(e) == "just message"


def test_schema_validation_error_default_errors_empty():
    e = SchemaValidationError("msg")
    assert e.errors == []


def test_schema_validation_error_explicit_errors():
    errs = [{"path": ["x"], "message": "err"}]
    e = SchemaValidationError("msg", errors=errs)
    assert e.errors == errs


def test_schema_validation_error_none_errors_empty():
    e = SchemaValidationError("msg", errors=None)
    assert e.errors == []


def test_schema_validation_error_is_exception():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_raises_as_itself():
    with pytest.raises(SchemaValidationError) as exc:
        raise SchemaValidationError("test")
    assert exc.value.errors == []


def test_schema_validation_error_inherits_message_attr():
    e = SchemaValidationError("hello")
    assert e.args == ("hello",)


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_default_path():
    """默认从 SCHEMA_PATH 加载。"""
    schema = load_schema()
    assert isinstance(schema, dict)
    assert "$schema" in schema or "type" in schema


def test_load_schema_str_path():
    schema = load_schema(str(SCHEMA_PATH))
    assert isinstance(schema, dict)


def test_load_schema_path_object():
    schema = load_schema(SCHEMA_PATH)
    assert isinstance(schema, dict)


def test_load_schema_missing_file_raises(tmp_path):
    missing = tmp_path / "missing.schema.json"
    with pytest.raises(FileNotFoundError) as exc:
        load_schema(missing)
    assert "不存在" in str(exc.value)


def test_load_schema_invalid_json_raises(tmp_path):
    p = tmp_path / "broken.schema.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_empty_file_raises(tmp_path):
    p = tmp_path / "empty.schema.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_returns_dict_with_props():
    """真实 schema 含 properties 字段。"""
    schema = load_schema()
    assert "properties" in schema


# =========================================================================
# validate 错误聚合
# =========================================================================


def test_validate_passes_returns_none():
    """有效 document → 不抛。"""
    schema = {
        "type": "object",
        "properties": {"x": {"type": "string"}},
        "required": ["x"],
    }
    validate({"x": "hello"}, schema)


def test_validate_single_error():
    schema = {
        "type": "object",
        "required": ["x"],
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    assert len(exc.value.errors) == 1


def test_validate_multiple_errors_all_collected():
    """多个错误都被收集到 errors 列表。"""
    schema = {
        "type": "object",
        "required": ["a", "b", "c"],
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    assert len(exc.value.errors) == 3


def test_validate_error_has_path():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}},
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({"x": "not int"}, schema)
    assert exc.value.errors[0]["path"] == ["x"]


def test_validate_error_has_message():
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    assert "message" in exc.value.errors[0]


def test_validate_error_has_schema_path():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "string"}},
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({"x": 123}, schema)
    assert "schema_path" in exc.value.errors[0]


def test_validate_exception_message_contains_error_count():
    schema = {
        "type": "object",
        "required": ["a", "b", "c"],
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    assert "3 处" in str(exc.value)


def test_validate_exception_message_contains_first_error_message():
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    # 异常 message 包含原始错误描述
    assert "string" in str(exc.value).lower() or "int" in str(exc.value).lower()


def test_validate_uses_default_schema_when_none():
    """schema=None → 用 SCHEMA_PATH 加载。"""
    # 一个明显无效的 document 应触发 schema 校验失败
    with pytest.raises(SchemaValidationError):
        validate({})


def test_validate_empty_schema_passes_anything():
    """空 schema dict 接受任何输入。"""
    validate({}, {})


# =========================================================================
# is_valid 深度
# =========================================================================


def test_is_valid_true_for_valid():
    schema = {"type": "string"}
    assert is_valid("hello", schema) is True


def test_is_valid_false_for_invalid():
    schema = {"type": "string"}
    assert is_valid(123, schema) is False


def test_is_valid_no_schema_uses_default():
    """无 schema 参数 → 用默认 SCHEMA_PATH。"""
    assert is_valid({}) is False  # 默认 schema 应拒绝空 dict


def test_is_valid_returns_bool_type():
    schema = {"type": "string"}
    assert isinstance(is_valid("x", schema), bool)
    assert isinstance(is_valid(123, schema), bool)


def test_is_valid_does_not_propagate_exception():
    """is_valid 不抛 SchemaValidationError。"""
    schema = {"type": "string"}
    try:
        result = is_valid(123, schema)
        assert result is False
    except SchemaValidationError:
        pytest.fail("is_valid should not raise")


# =========================================================================
# validate_file 深度
# =========================================================================


def test_validate_file_missing_raises_filenotfound(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(missing)


def test_validate_file_missing_error_message(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(missing)
    assert "不存在" in str(exc.value)


def test_validate_file_invalid_json_raises(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_passes_with_explicit_schema(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('"hello"', encoding="utf-8")
    validate_file(p, schema={"type": "string"})  # 不抛


def test_validate_file_fails_with_explicit_schema(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("123", encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p, schema={"type": "string"})


def test_validate_file_str_path(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('"hello"', encoding="utf-8")
    validate_file(str(p), schema={"type": "string"})  # 不抛


def test_validate_file_empty_file_raises(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_is_list():
    assert isinstance(schema_all, list)


def test_module_all_count_six():
    assert len(schema_all) == 6


def test_module_all_exact():
    assert set(schema_all) == {
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    }


def test_module_imports_json():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "import json" in src


def test_module_imports_path():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "from pathlib import Path" in src


def test_module_imports_any():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "from typing import Any" in src


def test_module_imports_draft2020():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "Draft202012Validator" in src


def test_module_imports_jsvalidation_error():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "JSValidationError" in src


def test_module_uses_future_annotations():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import app.schema as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_json_schema():
    import app.schema as mod
    assert "JSON Schema" in mod.__doc__ or "Schema" in mod.__doc__


def test_schema_validation_error_has_docstring():
    assert SchemaValidationError.__doc__ is not None


def test_silence_unused_import_function_exists():
    """_silence_unused_import 内部函数存在（用于保留 JSValidationError import）。"""
    import app.schema as mod
    assert hasattr(mod, "_silence_unused_import")


def test_silence_unused_import_returns_none():
    import app.schema as mod
    assert mod._silence_unused_import() is None


# =========================================================================
# 签名深度
# =========================================================================


def test_load_schema_signature_one_param():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_path_default_schema_path():
    sig = inspect.signature(load_schema)
    assert sig.parameters["path"].default == SCHEMA_PATH


def test_validate_signature_two_params():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_document_no_default():
    sig = inspect.signature(validate)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_validate_schema_default_none():
    sig = inspect.signature(validate)
    assert sig.parameters["schema"].default is None


def test_validate_return_annotation_none():
    """返回注解 = None（from __future__ 使之为字符串 'None'）。"""
    sig = inspect.signature(validate)
    assert sig.return_annotation in (None, "None", inspect.Signature.empty)


def test_is_valid_signature_two_params():
    sig = inspect.signature(is_valid)
    assert len(sig.parameters) == 2


def test_is_valid_schema_default_none():
    sig = inspect.signature(is_valid)
    assert sig.parameters["schema"].default is None


def test_validate_file_signature_two_params():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_path_no_default():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].default is inspect.Parameter.empty


def test_validate_file_schema_default_none():
    sig = inspect.signature(validate_file)
    assert sig.parameters["schema"].default is None


def test_schema_validation_error_init_signature():
    sig = inspect.signature(SchemaValidationError.__init__)
    # self, message, errors
    assert len(sig.parameters) == 3


def test_schema_validation_error_errors_default_none():
    sig = inspect.signature(SchemaValidationError.__init__)
    assert sig.parameters["errors"].default is None


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_then_is_valid_consistent():
    """validate 抛 / is_valid 返 False 应一致。"""
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError):
        validate(123, schema)
    assert is_valid(123, schema) is False


def test_validate_then_is_valid_consistent_pass():
    schema = {"type": "string"}
    validate("hello", schema)
    assert is_valid("hello", schema) is True


def test_load_schema_then_validate():
    """加载默认 schema → 校验合法 document。"""
    schema = load_schema()
    # 简单测试：schema 至少含 type: object
    assert schema.get("type") == "object" or "properties" in schema


def test_validate_does_not_mutate_input():
    """validate 不修改输入 document。"""
    doc = {"x": "hello"}
    doc_before = {"x": "hello"}
    validate(doc, {"type": "object"})
    assert doc == doc_before


def test_is_valid_does_not_mutate_input():
    doc = {"x": "hello"}
    doc_before = {"x": "hello"}
    is_valid(doc, {"type": "object"})
    assert doc == doc_before
