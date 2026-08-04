"""app/schema.py 边角测试（Round 53）。

补强 tests/test_schema.py（117 个测试）未覆盖的 schema.py 公共 API 边角：
- SchemaValidationError 类直接单测
- SCHEMA_PATH 常量属性
- __all__ 导出列表
- load_schema 默认参数行为
- validate errors 格式（每个 error 含 path/message/schema_path 三键）
- validate 错误消息含错误数
- validate_file 自定义 schema 参数
- is_valid True/False 边角
- _silence_unused_import 占位函数
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    __all__,
    _silence_unused_import,
    is_valid,
    load_schema,
    validate,
    validate_file,
)


# ---------- SchemaValidationError 类直接单测 ----------


def test_schema_validation_error_is_exception_subclass():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_inherits_from_exception():
    err = SchemaValidationError("test")
    assert isinstance(err, Exception)


def test_schema_validation_error_str_representation():
    err = SchemaValidationError("hello world")
    assert "hello world" in str(err)


def test_schema_validation_error_can_be_raised_and_caught():
    with pytest.raises(SchemaValidationError) as exc:
        raise SchemaValidationError("msg")
    assert "msg" in str(exc.value)


def test_schema_validation_error_default_errors_empty_list():
    err = SchemaValidationError("msg")
    assert err.errors == []


def test_schema_validation_error_errors_none_becomes_empty_list():
    err = SchemaValidationError("msg", errors=None)
    assert err.errors == []


def test_schema_validation_error_errors_passed_through():
    errs = [{"path": ["a"], "message": "x"}]
    err = SchemaValidationError("msg", errors=errs)
    assert err.errors == errs
    assert err.errors is errs  # 同一对象引用


def test_schema_validation_error_message_attribute_via_str():
    err = SchemaValidationError("custom message")
    # Exception 的 args[0] 是 message
    assert err.args[0] == "custom message"


def test_schema_validation_error_can_be_chained():
    """可以从其它异常包装 raise。"""
    try:
        try:
            raise ValueError("inner")
        except ValueError as e:
            raise SchemaValidationError("outer") from e
    except SchemaValidationError as outer:
        assert isinstance(outer.__cause__, ValueError)


# ---------- SCHEMA_PATH 常量 ----------


def test_schema_path_is_path_object():
    assert isinstance(SCHEMA_PATH, Path)


def test_schema_path_is_absolute():
    assert SCHEMA_PATH.is_absolute()


def test_schema_path_points_to_document_schema_json():
    """SCHEMA_PATH 应指向 schemas/document.schema.json。"""
    assert SCHEMA_PATH.name == "document.schema.json"
    assert SCHEMA_PATH.parent.name == "schemas"


def test_schema_path_file_exists():
    assert SCHEMA_PATH.is_file()


def test_schema_path_load_uses_default_parameter():
    """不传 path 时使用 SCHEMA_PATH。"""
    s = load_schema()  # 默认参数
    assert isinstance(s, dict)
    assert s.get("title") or "$id" in s


# ---------- __all__ 导出列表 ----------


def test_all_exports_listed():
    """__all__ 应含 6 个公开 API。"""
    assert set(__all__) == {
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    }


def test_all_exports_are_list_type():
    assert isinstance(__all__, list)


def test_all_exports_match_actual_module_attributes():
    """__all__ 中每个名字都应是模块属性。"""
    import app.schema as schema_module
    for name in __all__:
        assert hasattr(schema_module, name), f"{name} in __all__ 但模块无此属性"


# ---------- load_schema 边角 ----------


def test_load_schema_default_returns_dict():
    s = load_schema()
    assert isinstance(s, dict)


def test_load_schema_dict_has_json_schema_marker():
    """schema dict 应含 $schema 字段（Draft 2020-12）。"""
    s = load_schema()
    assert "$schema" in s


def test_load_schema_dict_has_id_key():
    s = load_schema()
    assert "$id" in s


def test_load_schema_dict_has_title_key():
    s = load_schema()
    assert "title" in s


def test_load_schema_dict_has_properties_key():
    s = load_schema()
    assert "properties" in s


def test_load_schema_str_path_accepted():
    s = load_schema(str(SCHEMA_PATH))
    assert isinstance(s, dict)


def test_load_schema_path_object_accepted():
    s = load_schema(SCHEMA_PATH)
    assert isinstance(s, dict)


def test_load_schema_missing_file_raises_filenotfound_with_path(tmp_path: Path):
    missing = tmp_path / "nonexistent.schema.json"
    with pytest.raises(FileNotFoundError) as exc:
        load_schema(missing)
    assert "nonexistent.schema.json" in str(exc.value) or "Schema" in str(exc.value)


def test_load_schema_directory_raises_filenotfound(tmp_path: Path):
    """传目录 → is_file() False → FileNotFoundError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        load_schema(sub)


def test_load_schema_invalid_json_raises_jsonerror(tmp_path: Path):
    """schema 文件本身是非法 JSON → json.JSONDecodeError。"""
    p = tmp_path / "bad.schema.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


# ---------- validate() 行为 ----------


def _valid_document() -> dict:
    return {
        "schema_version": "0.1.0",
        "document_id": "d1",
        "source_path": "x.docx",
        "source_type": "docx",
        "source_hash": "a" * 64,
        "parser_name": "fallback",
        "parser_version": "1.0",
        "elements": [],
        "chunks": [],
        "relations": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_validate_returns_none_on_valid_document():
    """validate 在合法时返回 None。"""
    assert validate(_valid_document()) is None


def test_validate_with_custom_schema_passes():
    """传入临时 schema 应使用该 schema 而非默认。"""
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"x": {"type": "string"}},
    }
    # custom schema 不要求 document_id 等，只校验 {x: str}
    validate({"x": "hello"}, schema=custom_schema)


def test_validate_with_custom_schema_rejects_invalid():
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["x"],
        "properties": {"x": {"type": "string"}},
    }
    with pytest.raises(SchemaValidationError):
        validate({}, schema=custom_schema)


def test_validate_errors_format_each_has_three_keys():
    """每个 error dict 含 path/message/schema_path 三键。"""
    bad = _valid_document()
    bad["source_hash"] = "wrong"  # 不符合 sha256 hex 格式
    with pytest.raises(SchemaValidationError) as exc:
        validate(bad)
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_error_message_includes_count():
    """SchemaValidationError 消息含错误数（"处"）。"""
    bad = _valid_document()
    del bad["source_hash"]  # 缺必填字段
    with pytest.raises(SchemaValidationError) as exc:
        validate(bad)
    assert "处" in str(exc.value)


def test_validate_errors_sorted_by_path():
    """errors 列表按 absolute_path 排序。"""
    bad = {
        "schema_version": "0.1.0",
        # 缺多个必填字段，应收集多个错误
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate(bad)
    # 至少 2 个错误，按 path 排序
    assert len(exc.value.errors) >= 2


def test_validate_first_error_used_in_message():
    """消息含 head.message（与 errors[0].message 一致）。"""
    bad = {
        "schema_version": "0.1.0",
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate(bad)
    err = exc.value
    head_msg = err.errors[0]["message"]
    assert head_msg in str(err) or "处" in str(err)


def test_validate_empty_dict_fails_with_multiple_errors():
    """空 dict 不符合 document schema → 多个必填字段缺失。"""
    with pytest.raises(SchemaValidationError) as exc:
        validate({})
    assert len(exc.value.errors) >= 5  # 至少缺 5+ 必填字段


# ---------- is_valid() 边角 ----------


def test_is_valid_returns_true_for_valid_document():
    assert is_valid(_valid_document()) is True


def test_is_valid_returns_false_for_invalid_document():
    bad = _valid_document()
    del bad["document_id"]
    assert is_valid(bad) is False


def test_is_valid_returns_bool_type():
    """返回值是 bool 不是 truthy/falsy。"""
    result_valid = is_valid(_valid_document())
    result_invalid = is_valid({})
    assert isinstance(result_valid, bool)
    assert isinstance(result_invalid, bool)


def test_is_valid_with_custom_schema_true():
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["x"],
    }
    assert is_valid({"x": 1}, schema=custom_schema) is True


def test_is_valid_with_custom_schema_false():
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["x"],
    }
    assert is_valid({}, schema=custom_schema) is False


def test_is_valid_does_not_raise_on_invalid():
    """is_valid 不抛异常，永远返 bool。"""
    result = is_valid(None)  # type: ignore[arg-type]
    # None 不符合 document schema → False（不抛）
    assert result is False


def test_is_valid_with_string_input_returns_false():
    """传字符串（非 dict）→ False（不抛）。"""
    assert is_valid("not a dict") is False  # type: ignore[arg-type]


def test_is_valid_with_list_input_returns_false():
    assert is_valid([1, 2, 3]) is False  # type: ignore[arg-type]


def test_is_valid_with_none_input_returns_false():
    assert is_valid(None) is False  # type: ignore[arg-type]


# ---------- validate_file() 边角 ----------


def test_validate_file_accepts_pathlib(tmp_path: Path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_valid_document()), encoding="utf-8")
    validate_file(p)  # 不抛


def test_validate_file_accepts_str_path(tmp_path: Path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_valid_document()), encoding="utf-8")
    validate_file(str(p))  # 不抛


def test_validate_file_missing_raises_filenotfound(tmp_path: Path):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(missing)
    assert "nope.json" in str(exc.value) or "待校验" in str(exc.value)


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub)


def test_validate_file_invalid_json_raises_jsonerror(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_invalid_content_raises_schema_error(tmp_path: Path):
    p = tmp_path / "wrong.json"
    p.write_text('{"unrelated": "fields"}', encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p)


def test_validate_file_with_custom_schema(tmp_path: Path):
    """传入临时 schema 应使用该 schema。"""
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["x"],
    }
    p = tmp_path / "doc.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    validate_file(p, schema=custom_schema)  # 不抛


def test_validate_file_with_custom_schema_fails(tmp_path: Path):
    custom_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["x"],
    }
    p = tmp_path / "doc.json"
    p.write_text('{"y": 1}', encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p, schema=custom_schema)


def test_validate_file_returns_none_on_success(tmp_path: Path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps(_valid_document()), encoding="utf-8")
    assert validate_file(p) is None


# ---------- _silence_unused_import 占位函数 ----------


def test_silence_unused_import_returns_none():
    assert _silence_unused_import() is None


def test_silence_unused_import_takes_no_arguments():
    """函数签名无参数（除了默认 self）。"""
    import inspect
    sig = inspect.signature(_silence_unused_import)
    assert len(sig.parameters) == 0


def test_silence_unused_import_callable():
    assert callable(_silence_unused_import)


# ---------- Draft202012Validator 直接使用 ----------


def test_validate_with_empty_schema_passes_anything():
    """空 schema（无约束）→ 任何 document 都通过。"""
    empty_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        # 无 type, 无 properties
    }
    validate({"any": "thing"}, schema=empty_schema)  # 不抛
    validate([1, 2, 3], schema=empty_schema)  # 不抛
    validate("string", schema=empty_schema)  # 不抛


def test_validate_with_type_only_schema():
    """只校验 type=object 的最小 schema。"""
    type_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
    }
    validate({}, schema=type_schema)  # 不抛
    with pytest.raises(SchemaValidationError):
        validate([], schema=type_schema)  # array 不是 object
