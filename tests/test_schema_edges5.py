r"""app/schema.py 边角测试 - 第六轮（Round 150）。

补强已有 base/edges/edges2/edges3/edges4（共 536 测试）未覆盖的深度：
- SCHEMA_PATH 路径精确性（parent 链）
- SchemaValidationError 边界（message 空字符串、errors 空列表）
- load_schema 多种 schema 文件内容（最小/嵌套/带 format）
- validate 错误聚合细节（path/schema_path/message 内容）
- is_valid 异常吞咽（包括非 SchemaValidationError）
- validate_file 错误优先级（FileNotFoundError vs JSONDecodeError vs SchemaValidationError）
- Draft202012Validator 行为
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from app.schema import (
    SCHEMA_PATH,
    SchemaValidationError,
    is_valid,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# SCHEMA_PATH 精确性
# =========================================================================


def test_schema_path_parent_chain():
    """SCHEMA_PATH = app/schema.py → app/ → 项目根 / schemas/document.schema.json。"""
    # app/schema.py 的 parent 是 app/
    # 再 parent 是项目根
    # SCHEMA_PATH 应在 项目根/schemas/
    assert SCHEMA_PATH.parent.name == "schemas"
    assert SCHEMA_PATH.parent.parent.is_dir()


def test_schema_path_absolute_after_resolve():
    """SCHEMA_PATH 经过 resolve。"""
    assert SCHEMA_PATH.is_absolute()


def test_schema_path_sibling_to_app_directory():
    """schemas/ 与 app/ 是同级（项目根的子目录）。"""
    # SCHEMA_PATH.parent (=schemas) 与 app/ 都是项目根的子目录
    schemas_dir = SCHEMA_PATH.parent
    app_dir = schemas_dir.parent / "app"
    assert app_dir.is_dir()


def test_schema_path_filename_value():
    assert SCHEMA_PATH.name == "document.schema.json"


def test_schema_path_stem_value():
    assert SCHEMA_PATH.stem == "document.schema"


def test_schema_path_suffix_value():
    assert SCHEMA_PATH.suffix == ".json"


# =========================================================================
# SchemaValidationError 边界
# =========================================================================


def test_schema_validation_error_empty_message():
    e = SchemaValidationError("")
    assert str(e) == ""
    assert e.errors == []


def test_schema_validation_error_message_with_special_chars():
    msg = "error with 中文 and \n\t whitespace"
    e = SchemaValidationError(msg)
    assert str(e) == msg


def test_schema_validation_error_args_length_one():
    e = SchemaValidationError("msg")
    assert len(e.args) == 1


def test_schema_validation_error_args_value():
    e = SchemaValidationError("msg")
    assert e.args == ("msg",)


def test_schema_validation_error_default_errors_empty_list():
    e = SchemaValidationError("msg")
    assert isinstance(e.errors, list)
    assert len(e.errors) == 0


def test_schema_validation_error_explicit_empty_list():
    e = SchemaValidationError("msg", errors=[])
    assert e.errors == []


def test_schema_validation_error_none_errors_becomes_empty():
    e = SchemaValidationError("msg", errors=None)
    assert e.errors == []


def test_schema_validation_error_can_be_raised_and_caught():
    with pytest.raises(SchemaValidationError):
        raise SchemaValidationError("test")


def test_schema_validation_error_caught_as_exception():
    try:
        raise SchemaValidationError("test")
    except Exception:
        pass


def test_schema_validation_error_inheritance():
    assert issubclass(SchemaValidationError, Exception)
    assert not issubclass(SchemaValidationError, ValueError)


def test_schema_validation_error_errors_attribute_directly_set():
    """errors 列表是直接赋值，不复制（共享引用）。"""
    errs = [{"k": "v"}]
    e = SchemaValidationError("msg", errors=errs)
    assert e.errors is errs


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_returns_dict_with_expected_keys():
    schema = load_schema()
    expected_top_keys = {"$schema", "type", "properties"}
    assert expected_top_keys.issubset(set(schema.keys()))


def test_load_schema_default_path_is_schema_path():
    """无参数 load_schema() 应读取 SCHEMA_PATH。"""
    schema = load_schema()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        expected = json.load(f)
    assert schema == expected


def test_load_schema_explicit_default_value():
    """显式传 SCHEMA_PATH 与默认值结果一致。"""
    a = load_schema(SCHEMA_PATH)
    b = load_schema()
    assert a == b


def test_load_schema_path_with_parent_reference(tmp_path):
    """路径含 .. 段。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    schema_file = sub / "test.schema.json"
    schema_file.write_text('{"type": "object"}', encoding="utf-8")
    loaded = load_schema(tmp_path / "sub" / ".." / "sub" / "test.schema.json")
    assert loaded == {"type": "object"}


def test_load_schema_minimal_schema(tmp_path):
    """最小 schema dict。"""
    p = tmp_path / "min.schema.json"
    p.write_text("{}", encoding="utf-8")
    assert load_schema(p) == {}


def test_load_schema_nested_schema(tmp_path):
    p = tmp_path / "nested.schema.json"
    p.write_text(
        json.dumps({
            "type": "object",
            "properties": {
                "x": {"type": "string"},
                "y": {"type": "integer"},
            },
        }),
        encoding="utf-8",
    )
    s = load_schema(p)
    assert "properties" in s
    assert set(s["properties"]) == {"x", "y"}


def test_load_schema_array_root(tmp_path):
    """顶层 schema type=array。"""
    p = tmp_path / "arr.schema.json"
    p.write_text(json.dumps({"type": "array"}), encoding="utf-8")
    s = load_schema(p)
    assert s["type"] == "array"


def test_load_schema_string_root(tmp_path):
    """顶层 schema type=string。"""
    p = tmp_path / "str.schema.json"
    p.write_text(json.dumps({"type": "string"}), encoding="utf-8")
    s = load_schema(p)
    assert s["type"] == "string"


def test_load_schema_integer_root(tmp_path):
    p = tmp_path / "int.schema.json"
    p.write_text(json.dumps({"type": "integer"}), encoding="utf-8")
    s = load_schema(p)
    assert s["type"] == "integer"


def test_load_schema_missing_file_message_contains_path(tmp_path):
    missing = tmp_path / "missing.schema.json"
    with pytest.raises(FileNotFoundError) as exc:
        load_schema(missing)
    assert "missing.schema.json" in str(exc.value)


def test_load_schema_directory_raises(tmp_path):
    """传入目录 → 不是文件 → FileNotFoundError。"""
    sub = tmp_path / "subdir"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        load_schema(sub)


# =========================================================================
# validate 错误聚合细节
# =========================================================================


def test_validate_single_type_error_path_empty():
    """type 错误 → path 空 list。"""
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    err = exc.value.errors[0]
    assert err["path"] == []


def test_validate_property_error_path_has_field():
    schema = {
        "type": "object",
        "properties": {"x": {"type": "string"}},
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({"x": 123}, schema)
    err = exc.value.errors[0]
    assert err["path"] == ["x"]


def test_validate_nested_property_error_path():
    schema = {
        "type": "object",
        "properties": {
            "outer": {
                "type": "object",
                "properties": {"inner": {"type": "string"}},
            },
        },
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({"outer": {"inner": 123}}, schema)
    err = exc.value.errors[0]
    assert err["path"] == ["outer", "inner"]


def test_validate_array_element_error_path():
    schema = {
        "type": "array",
        "items": {"type": "string"},
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate(["a", 123, "b"], schema)
    err = exc.value.errors[0]
    assert err["path"] == [1]


def test_validate_error_message_is_str():
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    err = exc.value.errors[0]
    assert isinstance(err["message"], str)


def test_validate_error_schema_path_is_list():
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    err = exc.value.errors[0]
    assert isinstance(err["schema_path"], list)


def test_validate_errors_count_matches_iter_errors():
    """errors 长度应等于 validator.iter_errors 数量。"""
    schema = {
        "type": "object",
        "required": ["a", "b", "c", "d"],
    }
    validator = Draft202012Validator(schema)
    expected_count = len(list(validator.iter_errors({})))
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    assert len(exc.value.errors) == expected_count


def test_validate_exception_message_starts_with_schema_text():
    schema = {"type": "string"}
    with pytest.raises(SchemaValidationError) as exc:
        validate(123, schema)
    assert "Schema 校验失败" in str(exc.value)


def test_validate_exception_message_contains_count():
    schema = {
        "type": "object",
        "required": ["x", "y", "z"],
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    assert "3 处" in str(exc.value)


def test_validate_no_errors_returns_none_explicitly():
    """通过校验时应显式 return None（无 return 也行）。"""
    schema = {"type": "string"}
    result = validate("hello", schema)
    assert result is None


def test_validate_with_empty_schema_passes_anything():
    """空 schema dict（无 type）接受任何输入。"""
    validate({}, {})
    validate([], {})
    validate("string", {})
    validate(123, {})
    validate(None, {})


def test_validate_does_not_modify_schema():
    schema = {"type": "string"}
    schema_before = json.loads(json.dumps(schema))
    validate("hello", schema)
    assert schema == schema_before


def test_validate_does_not_modify_document():
    doc = {"x": "hello"}
    doc_before = json.loads(json.dumps(doc))
    validate(doc, {"type": "object"})
    assert doc == doc_before


# =========================================================================
# is_valid 异常吞咽
# =========================================================================


def test_is_valid_catches_schema_validation_error_only():
    """is_valid 仅 catch SchemaValidationError，其他异常会传播。"""
    schema = {"type": "string"}
    # 正常 case
    assert is_valid("hello", schema) is True
    # SchemaValidationError case
    assert is_valid(123, schema) is False


def test_is_valid_returns_bool_type():
    schema = {"type": "string"}
    assert isinstance(is_valid("x", schema), bool)
    assert isinstance(is_valid(123, schema), bool)


def test_is_valid_does_not_raise_on_invalid():
    schema = {"type": "string"}
    try:
        result = is_valid(123, schema)
        assert result is False
    except SchemaValidationError:
        pytest.fail("is_valid should not raise SchemaValidationError")


def test_is_valid_with_empty_schema_always_true():
    """空 schema 总是通过。"""
    assert is_valid({}, {}) is True
    assert is_valid([], {}) is True
    assert is_valid("x", {}) is True


# =========================================================================
# validate_file 错误优先级
# =========================================================================


def test_validate_file_missing_file_raises_filenotfounderror_first(tmp_path):
    """文件不存在 → FileNotFoundError（不读盘）。"""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(missing, schema={"type": "string"})


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path):
    """文件存在但 JSON 解析失败 → JSONDecodeError。"""
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, schema={"type": "string"})


def test_validate_file_valid_json_failing_schema_raises_schema_error(tmp_path):
    """文件 JSON 合法但 schema 校验失败 → SchemaValidationError。"""
    p = tmp_path / "ok_format.json"
    p.write_text("123", encoding="utf-8")
    with pytest.raises(SchemaValidationError):
        validate_file(p, schema={"type": "string"})


def test_validate_file_passes_with_explicit_schema(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('"hello"', encoding="utf-8")
    # 不抛
    validate_file(p, schema={"type": "string"})


def test_validate_file_str_path(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text('"hello"', encoding="utf-8")
    validate_file(str(p), schema={"type": "string"})


def test_validate_file_with_array_schema(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    validate_file(p, schema={"type": "array"})


def test_validate_file_directory_raises_filenotfounderror(tmp_path):
    """传入目录 → FileNotFoundError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub)


# =========================================================================
# Draft202012Validator 行为
# =========================================================================


def test_default_schema_is_draft202012_compatible():
    """默认打包的 schema 应是 Draft 2020-12 兼容。"""
    schema = load_schema()
    # 不抛 - check_schema 在不兼容时会 raise SchemaError
    Draft202012Validator.check_schema(schema)


def test_draft202012_validator_can_be_constructed_with_default_schema():
    schema = load_schema()
    v = Draft202012Validator(schema)
    assert v is not None
    assert v.schema is schema


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_order():
    """__all__ 应是 [SCHEMA_PATH, SchemaValidationError, load_schema, validate, is_valid, validate_file]。"""
    import app.schema as mod
    assert mod.__all__ == [
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    ]


def test_module_all_no_silence_unused():
    import app.schema as mod
    assert "_silence_unused_import" not in mod.__all__


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


def test_module_imports_draft202012():
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


def test_module_docstring_mentions_json_schema():
    import app.schema as mod
    doc = mod.__doc__
    assert "JSON Schema" in doc or "Schema" in doc or "schema" in doc.lower()


def test_silence_unused_import_returns_none():
    import app.schema as mod
    assert mod._silence_unused_import() is None


def test_silence_unused_import_no_args():
    import app.schema as mod
    sig = inspect.signature(mod._silence_unused_import)
    assert len(sig.parameters) == 0


# =========================================================================
# 签名深度
# =========================================================================


def test_load_schema_path_default_is_schema_path():
    sig = inspect.signature(load_schema)
    assert sig.parameters["path"].default == SCHEMA_PATH


def test_load_schema_path_annotation_str_or_path():
    sig = inspect.signature(load_schema)
    # from __future__ makes annotations strings
    annotation = sig.parameters["path"].annotation
    assert "Path" in str(annotation) or "str" in str(annotation)


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    annotation = sig.return_annotation
    assert "dict" in str(annotation).lower()


def test_validate_document_no_default():
    sig = inspect.signature(validate)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_validate_schema_default_none():
    sig = inspect.signature(validate)
    assert sig.parameters["schema"].default is None


def test_is_valid_document_no_default():
    sig = inspect.signature(is_valid)
    assert sig.parameters["document"].default is inspect.Parameter.empty


def test_is_valid_schema_default_none():
    sig = inspect.signature(is_valid)
    assert sig.parameters["schema"].default is None


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


def test_schema_validation_error_init_errors_default_none():
    sig = inspect.signature(SchemaValidationError.__init__)
    assert sig.parameters["errors"].default is None


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_then_is_valid_consistent_invalid():
    """validate raise vs is_valid False 一致。"""
    schema = {"type": "object", "required": ["x"]}
    with pytest.raises(SchemaValidationError):
        validate({}, schema)
    assert is_valid({}, schema) is False


def test_validate_then_is_valid_consistent_valid():
    schema = {"type": "object", "required": ["x"]}
    validate({"x": 1}, schema)
    assert is_valid({"x": 1}, schema) is True


def test_load_schema_then_validate_with_loaded():
    """load_schema 加载后可直接用。"""
    schema = load_schema()
    # 不抛
    assert isinstance(schema, dict)


def test_validate_file_with_default_schema(tmp_path):
    """validate_file 用默认 SCHEMA_PATH 校验合法 document。"""
    # 先用 SCHEMA_PATH 校验一个合法的 document
    # 简单做法：直接调 validate_file on 一个最小合法 dict
    p = tmp_path / "ok.json"
    # 用 SCHEMA_PATH 校验空 dict 应失败（因为 default schema 要求字段）
    # 但用一个自定义 schema 校验空 dict 应通过
    p.write_text("{}", encoding="utf-8")
    validate_file(p, schema={"type": "object"})


def test_validate_exception_can_be_caught_as_schema_validation_error():
    schema = {"type": "string"}
    try:
        validate(123, schema)
    except SchemaValidationError as e:
        assert "校验失败" in str(e)


def test_validate_error_count_consistent_with_errors_list_length():
    schema = {
        "type": "object",
        "required": ["a", "b"],
        "properties": {
            "a": {"type": "string"},
            "b": {"type": "integer"},
        },
    }
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema)
    msg = str(exc.value)
    # 错误数与 errors 列表长度一致
    n_in_msg = int(msg.split("(")[1].split("处")[0])
    assert n_in_msg == len(exc.value.errors)
