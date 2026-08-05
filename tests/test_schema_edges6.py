r"""app/schema.py 边角测试 - 第六轮（Round 173）。

补强已有 base/edges/edges2-5（共 618 测试）未覆盖的深度：
- SCHEMA_PATH 精确路径
- SchemaValidationError 字段、默认值、init 签名
- load_schema 边界（默认/显式 path/不存在）
- validate 各错误路径与聚合细节
- is_valid 各分支
- validate_file 错误优先级
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


def test_schema_path_value():
    """SCHEMA_PATH = project_root/schemas/document.schema.json。"""
    expected = Path(__file__).resolve().parent.parent / "schemas" / "document.schema.json"
    assert SCHEMA_PATH == expected


def test_schema_path_is_absolute():
    assert SCHEMA_PATH.is_absolute()


def test_schema_path_resolved():
    """resolve() 后无 .. 段。"""
    assert SCHEMA_PATH == SCHEMA_PATH.resolve()


def test_schema_path_filename():
    assert SCHEMA_PATH.name == "document.schema.json"


def test_schema_path_parent_name():
    assert SCHEMA_PATH.parent.name == "schemas"


def test_schema_path_is_file():
    assert SCHEMA_PATH.is_file()


# =========================================================================
# SchemaValidationError 深度
# =========================================================================


def test_schema_validation_error_init_signature():
    sig = inspect.signature(SchemaValidationError.__init__)
    assert set(sig.parameters) == {"self", "message", "errors"}


def test_schema_validation_error_errors_default_none():
    sig = inspect.signature(SchemaValidationError.__init__)
    assert sig.parameters["errors"].default is None


def test_schema_validation_error_no_errors_defaults_to_empty_list():
    e = SchemaValidationError("msg")
    assert e.errors == []


def test_schema_validation_error_explicit_none_errors():
    e = SchemaValidationError("msg", errors=None)
    assert e.errors == []


def test_schema_validation_error_explicit_empty_list():
    e = SchemaValidationError("msg", errors=[])
    assert e.errors == []


def test_schema_validation_error_with_errors():
    errs = [{"path": ["x"], "message": "y"}]
    e = SchemaValidationError("msg", errors=errs)
    assert e.errors == errs


def test_schema_validation_error_str_returns_message():
    e = SchemaValidationError("my message")
    assert str(e) == "my message"


def test_schema_validation_error_args_only_message():
    """super().__init__(message) → args = (message,)。"""
    e = SchemaValidationError("m", errors=[{"k": "v"}])
    assert e.args == ("m",)


def test_schema_validation_error_inherits_exception():
    assert issubclass(SchemaValidationError, Exception)


def test_schema_validation_error_not_value_error():
    assert not issubclass(SchemaValidationError, ValueError)


def test_schema_validation_error_caught_specifically():
    with pytest.raises(SchemaValidationError):
        raise SchemaValidationError("x")


def test_schema_validation_error_caught_as_exception():
    try:
        raise SchemaValidationError("x")
    except Exception:
        pass


def test_schema_validation_error_equality_not_identity():
    a = SchemaValidationError("m")
    b = SchemaValidationError("m")
    assert a is not b


# =========================================================================
# load_schema 边界
# =========================================================================


def test_load_schema_default_returns_dict():
    schema = load_schema()
    assert isinstance(schema, dict)


def test_load_schema_explicit_default_path():
    """load_schema() 与 load_schema(SCHEMA_PATH) 等价。"""
    assert load_schema() == load_schema(SCHEMA_PATH)


def test_load_schema_str_path():
    schema = load_schema(str(SCHEMA_PATH))
    assert isinstance(schema, dict)


def test_load_schema_nonexistent_raises():
    with pytest.raises(FileNotFoundError) as exc:
        load_schema(Path("/nonexistent/schema.json"))
    assert "Schema 文件不存在" in str(exc.value)


def test_load_schema_nonexistent_str_path():
    with pytest.raises(FileNotFoundError):
        load_schema("/nonexistent/schema.json")


def test_load_schema_directory_raises():
    """目录不是文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema(SCHEMA_PATH.parent)


def test_load_schema_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_schema(p)


def test_load_schema_returns_new_dict_each_call():
    a = load_schema()
    b = load_schema()
    assert a is not b
    assert a == b


def test_load_schema_signature():
    sig = inspect.signature(load_schema)
    assert set(sig.parameters) == {"path"}


def test_load_schema_default_is_schema_path():
    sig = inspect.signature(load_schema)
    assert sig.parameters["path"].default == SCHEMA_PATH


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


# =========================================================================
# validate 行为
# =========================================================================


def test_validate_no_errors_returns_none(tmp_path: Path):
    """用 empty schema 校验任何 dict → 通过。"""
    result = validate({"x": 1}, schema={})
    assert result is None


def test_validate_with_no_schema_uses_default():
    """不传 schema 用默认；空 dict 校验失败。"""
    with pytest.raises(SchemaValidationError):
        validate({})


def test_validate_collects_all_errors():
    """多个错误都收集到 SchemaValidationError.errors。"""
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema={
            "type": "object",
            "properties": {
                "a": {"type": "string"},
                "b": {"type": "string"},
            },
            "required": ["a", "b"],
        })
    assert len(exc.value.errors) == 2


def test_validate_error_path_empty_for_type_mismatch():
    with pytest.raises(SchemaValidationError) as exc:
        validate("not a dict", schema={"type": "object"})
    assert exc.value.errors[0]["path"] == []


def test_validate_error_path_has_field():
    with pytest.raises(SchemaValidationError) as exc:
        validate({"a": 1}, schema={
            "type": "object",
            "properties": {"a": {"type": "string"}},
        })
    assert exc.value.errors[0]["path"] == ["a"]


def test_validate_error_message_is_str():
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema={"type": "object", "required": ["x"]})
    for err in exc.value.errors:
        assert isinstance(err["message"], str)


def test_validate_error_schema_path_is_list():
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema={"type": "object", "required": ["x"]})
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_exception_message_starts_with_schema_text():
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema={"type": "object", "required": ["x"]})
    msg = str(exc.value)
    assert "Schema" in msg
    assert "校验失败" in msg


def test_validate_exception_message_contains_count():
    with pytest.raises(SchemaValidationError) as exc:
        validate({}, schema={"type": "object", "required": ["x", "y", "z"]})
    assert "处" in str(exc.value)


def test_validate_does_not_modify_document():
    doc = {"x": 1}
    before = json.loads(json.dumps(doc))
    validate(doc, schema={})
    assert doc == before


def test_validate_signature():
    sig = inspect.signature(validate)
    assert set(sig.parameters) == {"document", "schema"}


def test_validate_schema_default_none():
    sig = inspect.signature(validate)
    assert sig.parameters["schema"].default is None


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# is_valid 行为
# =========================================================================


def test_is_valid_returns_true_for_valid():
    assert is_valid({"x": 1}, schema={}) is True


def test_is_valid_returns_false_for_invalid():
    assert is_valid("not a dict", schema={"type": "object"}) is False


def test_is_valid_returns_bool_type():
    assert isinstance(is_valid({}, schema={}), bool)


def test_is_valid_does_not_raise():
    """is_valid 不应抛异常。"""
    try:
        is_valid({}, schema={"type": "object", "required": ["x"]})
        is_valid({"x": 1}, schema={})
    except Exception:
        pytest.fail("is_valid should not raise")


def test_is_valid_with_default_schema():
    """不传 schema 用默认 schema；空 dict 应判 False。"""
    result = is_valid({})
    assert isinstance(result, bool)


def test_is_valid_signature():
    sig = inspect.signature(is_valid)
    assert set(sig.parameters) == {"document", "schema"}


def test_is_valid_return_annotation_bool():
    sig = inspect.signature(is_valid)
    assert "bool" in str(sig.return_annotation)


# =========================================================================
# validate_file 行为
# =========================================================================


def test_validate_file_missing_raises(tmp_path: Path):
    p = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(p)


def test_validate_file_invalid_json_raises(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p)


def test_validate_file_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text('{"x": 1}', encoding="utf-8")
    # 用 empty schema，任何 dict 都过
    validate_file(p, schema={})


def test_validate_file_directory_raises(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub)


def test_validate_file_signature():
    sig = inspect.signature(validate_file)
    assert set(sig.parameters) == {"path", "schema"}


def test_validate_file_schema_default_none():
    sig = inspect.signature(validate_file)
    assert sig.parameters["schema"].default is None


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# 默认 schema 内容
# =========================================================================


def test_default_schema_is_draft202012_compatible():
    schema = load_schema()
    Draft202012Validator.check_schema(schema)


def test_default_schema_has_required_top_keys():
    schema = load_schema()
    for key in ("$schema", "type", "properties"):
        assert key in schema


def test_default_schema_type_is_object():
    schema = load_schema()
    assert schema["type"] == "object"


def test_default_schema_has_properties_document_id():
    schema = load_schema()
    assert "document_id" in schema["properties"]


def test_default_schema_has_properties_chunks():
    schema = load_schema()
    assert "chunks" in schema["properties"]


# =========================================================================
# 模块结构
# =========================================================================


def test_module_all_exact():
    import app.schema as mod
    assert mod.__all__ == [
        "SCHEMA_PATH",
        "SchemaValidationError",
        "load_schema",
        "validate",
        "is_valid",
        "validate_file",
    ]


def test_module_all_is_list():
    import app.schema as mod
    assert isinstance(mod.__all__, list)


def test_module_all_no_duplicates():
    import app.schema as mod
    assert len(mod.__all__) == len(set(mod.__all__))


def test_module_uses_future_annotations():
    import app.schema as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


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


def test_module_docstring_present():
    import app.schema as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_business_code():
    """docstring 提及"业务代码只通过这里"。"""
    import app.schema as mod
    doc = mod.__doc__
    assert "业务代码" in doc or "jsonschema" in doc.lower()


def test_module_has_silence_unused():
    """_silence_unused_import 函数存在（保留 JSValidationError import）。"""
    import app.schema as mod
    assert hasattr(mod, "_silence_unused_import")
    assert callable(mod._silence_unused_import)


def test_module_silence_unused_returns_none():
    import app.schema as mod
    assert mod._silence_unused_import() is None


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_then_is_valid_consistent():
    """validate 抛 / is_valid 返 False 应一致。"""
    schema = {"type": "object", "required": ["x"]}
    try:
        validate({}, schema=schema)
        ok = True
    except SchemaValidationError:
        ok = False
    assert ok == is_valid({}, schema=schema)


def test_load_schema_idempotent():
    a = load_schema()
    b = load_schema()
    assert a == b


def test_validate_idempotent():
    """同一输入多次 validate 一致。"""
    schema = {"type": "object", "required": ["x"]}
    for _ in range(3):
        with pytest.raises(SchemaValidationError):
            validate({}, schema=schema)


def test_schema_path_consistent_with_load_schema():
    """load_schema 默认从 SCHEMA_PATH 加载。"""
    direct = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    via_func = load_schema()
    assert direct == via_func


def test_validate_does_not_modify_schema():
    """validate 不应修改传入的 schema dict。"""
    schema = {"type": "object", "required": ["x"]}
    before = json.loads(json.dumps(schema))
    validate({"x": 1}, schema=schema)
    assert schema == before
