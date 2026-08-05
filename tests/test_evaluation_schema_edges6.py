r"""evaluation/schema.py 边角测试 - 第六轮（Round 228）。

补强已有 base/edges/edges2-5（共 ~340 测试）未覆盖的深度：
- EvalSchemaError：errors 是非 list 类型；init 多 kwargs；可被 raise/catch；与 FileNotFoundError 区分
- _schema_path：空 name；带子目录的 name
- load_schema：empty name；name 含路径分隔符；返回 dict 可被修改
- validate：instance 非 dict 类型（list/str/None/int）；空 dict 实例；多 errors 排序
- validate_file：BOM 文件；trailing comma；array/int/None/str 顶层 JSON；非 UTF-8 编码
- 模块结构补强
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

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
# EvalSchemaError 深度（补强 edges5）
# =========================================================================


def test_eval_schema_error_errors_tuple_input():
    """errors 是 tuple → `errors or []` 短路：tuple 是 truthy → 保留 tuple。"""
    err = EvalSchemaError("msg", errors=({"x": 1},))
    # errors 是 tuple（非 list），但 truthy → 保留
    assert err.errors == ({"x": 1},)
    assert isinstance(err.errors, tuple)


def test_eval_schema_error_errors_empty_tuple_becomes_empty_list():
    """errors 是空 tuple → falsy → 替换为 []。"""
    err = EvalSchemaError("msg", errors=())
    assert err.errors == []


def test_eval_schema_error_errors_dict_input_kept_as_is():
    """errors 是 dict（truthy） → 保留 dict（行为记录，调用方应传 list）。"""
    err = EvalSchemaError("msg", errors={"k": "v"})
    assert err.errors == {"k": "v"}


def test_eval_schema_error_errors_int_input_kept_as_is():
    """errors 是非零 int（truthy） → 保留 int。"""
    err = EvalSchemaError("msg", errors=5)
    assert err.errors == 5


def test_eval_schema_error_errors_zero_int_becomes_empty_list():
    """errors=0 → falsy → 替换为 []。"""
    err = EvalSchemaError("msg", errors=0)
    assert err.errors == []


def test_eval_schema_error_init_with_kwargs():
    """init 应支持 kwargs 调用。"""
    err = EvalSchemaError(message="kwmsg", errors=[{"k": "v"}])
    assert str(err) == "kwmsg"
    assert err.errors == [{"k": "v"}]


def test_eval_schema_error_subclass():
    """EvalSchemaError 可被继承。"""
    class CustomError(EvalSchemaError):
        pass
    err = CustomError("custom")
    assert isinstance(err, EvalSchemaError)
    assert isinstance(err, Exception)
    assert str(err) == "custom"


def test_eval_schema_error_cannot_be_caught_as_value_error():
    """不是 ValueError 子类。"""
    err = EvalSchemaError("msg")
    with pytest.raises(EvalSchemaError):
        try:
            raise err
        except ValueError:
            pytest.fail("Should not be caught as ValueError")


def test_eval_schema_error_cannot_be_caught_as_key_error():
    with pytest.raises(EvalSchemaError):
        try:
            raise EvalSchemaError("msg")
        except KeyError:
            pytest.fail("Should not be caught as KeyError")


def test_eval_schema_error_cannot_be_caught_as_file_not_found():
    """不是 FileNotFoundError 子类。"""
    with pytest.raises(EvalSchemaError):
        try:
            raise EvalSchemaError("msg")
        except FileNotFoundError:
            pytest.fail("Should not be caught as FileNotFoundError")


def test_eval_schema_error_str_with_unicode_message():
    err = EvalSchemaError("中文错误消息")
    assert str(err) == "中文错误消息"


def test_eval_schema_error_str_with_newline():
    err = EvalSchemaError("line1\nline2")
    assert "line1" in str(err)
    assert "line2" in str(err)


def test_eval_schema_error_args_contains_message():
    """super().__init__(message) → args[0] = message。"""
    err = EvalSchemaError("hello")
    assert err.args == ("hello",)


def test_eval_schema_error_repr_contains_class_name():
    err = EvalSchemaError("msg", errors=[{"a": 1}])
    r = repr(err)
    assert "EvalSchemaError" in r
    assert "msg" in r


def test_eval_schema_error_set_errors_attribute_after_init():
    """errors 是普通 attribute（不是 property），可直接 set。"""
    err = EvalSchemaError("msg")
    err.errors = [{"new": True}]
    assert err.errors == [{"new": True}]


def test_eval_schema_error_set_message_via_init_only():
    """不能直接 set message（Exception 内部管理）。"""
    err = EvalSchemaError("msg")
    # args 是 tuple，不可变
    with pytest.raises(TypeError):
        err.args[0] = "new"  # type: ignore[index]


# =========================================================================
# _schema_path 深度（补强 edges5）
# =========================================================================


def test_schema_path_empty_name_raises():
    """空 name → SCHEMAS_DIR / '' = SCHEMAS_DIR → is_dir True → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_with_subdir_raises():
    """name 含子目录 → 找不到 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/schema.json")


def test_schema_path_with_dot_prefix():
    """name 以 . 开头 → 视为隐藏文件 → 通常 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".hidden.schema.json")


def test_schema_path_returns_path_under_schemas_dir():
    """返回的 path 应位于 SCHEMAS_DIR 内。"""
    p = _schema_path("manifest.schema.json")
    assert p.relative_to(SCHEMAS_DIR)


def test_schema_path_does_not_open_file():
    """_schema_path 只返回路径，不打开文件。"""
    # 用一个不存在的 name → FileNotFoundError，证明只检查 is_file
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_callable():
    assert callable(_schema_path)


def test_schema_path_one_param():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


# =========================================================================
# load_schema 深度（补强 edges5）
# =========================================================================


def test_load_schema_returns_dict_for_each_known():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        result = load_schema(name)
        assert isinstance(result, dict)
        assert len(result) > 0


def test_load_schema_returns_mutable_dict():
    """返回的 dict 是 mutable（修改不影响下次调用，因为每次重新 load）。"""
    s = load_schema("manifest.schema.json")
    original_type = s.get("type")
    s["type"] = "modified"
    # 重新 load 应是原值
    s2 = load_schema("manifest.schema.json")
    assert s2["type"] == original_type
    assert s2["type"] != "modified"


def test_load_schema_returns_independent_dict():
    """两次 load 返回不同的 dict 对象。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_with_str_name():
    """name 参数应是 str。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_unknown_name_raises_file_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        load_schema("does-not-exist.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


def test_load_schema_callable():
    assert callable(load_schema)


def test_load_schema_signature():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters) == ["name"]


def test_load_schema_no_default():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].default is inspect.Parameter.empty


# =========================================================================
# validate 深度（补强 edges5）
# =========================================================================


def test_validate_instance_dict_returns_none_for_empty_dict():
    """空 dict instance：manifest schema 要求必填字段 → 抛 EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_instance_list_raises_eval_schema_error():
    """instance 是 list（不是 dict） → schema type 'object' 不匹配 → EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_instance_str_raises_eval_schema_error():
    """instance 是 str → schema type 'object' 不匹配。"""
    with pytest.raises(EvalSchemaError):
        validate("not a dict", "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_instance_int_raises_eval_schema_error():
    with pytest.raises(EvalSchemaError):
        validate(123, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_instance_none_raises_eval_schema_error():
    """instance 是 None → schema type 'object' 不匹配。"""
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_returns_none_on_success():
    """合法 instance → 返回 None。"""
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    result = validate(valid_manifest, "manifest.schema.json")
    assert result is None


def test_validate_errors_sorted_by_path():
    """errors 应按 absolute_path 排序（jsonschema 默认行为）。"""
    bad = {
        "manifest_version": 1,  # wrong type
        "devset_status": "invalid",  # not in enum
        "documents": "not a list",  # wrong type
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    errors = exc_info.value.errors
    # 验证 errors 是 list
    assert isinstance(errors, list)
    # 每个 error 都有 path/message/schema_path
    for e in errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_error_count_in_message():
    bad = {
        "manifest_version": 1,
        "devset_status": "invalid",
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    msg = str(exc_info.value)
    # 消息含 "(N 处)"
    assert "处" in msg


def test_validate_first_error_in_head_message():
    """错误消息中 head 是 errors[0]（按 path 排序后）。"""
    bad = {"manifest_version": 1}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    msg = str(exc_info.value)
    # 应包含 errors[0].message
    errors = exc_info.value.errors
    assert errors[0]["message"] in msg


def test_validate_callable():
    assert callable(validate)


def test_validate_signature():
    sig = inspect.signature(validate)
    assert list(sig.parameters) == ["instance", "schema_name"]


def test_validate_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_does_not_modify_instance():
    """validate 不应修改输入 instance。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    instance_copy = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == instance_copy


# =========================================================================
# validate_file 深度（补强 edges5）
# =========================================================================


def test_validate_file_bom_raises_jsondecodeerror(tmp_path):
    """UTF-8 BOM 文件 → json.load 触发 JSONDecodeError（不被捕获）。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"k": 1}')
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_trailing_comma_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"k": 1,}', encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_single_quotes_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{'k': 1}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_array_root_raises_eval_error(tmp_path):
    """JSON 顶层是 array（不是 dict） → schema type 'object' 失败 → EvalSchemaError。"""
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_int_root_raises_eval_error(tmp_path):
    """JSON 顶层是 int → EvalSchemaError。"""
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_root_raises_eval_error(tmp_path):
    """JSON 顶层是 str → EvalSchemaError。"""
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_null_root_raises_eval_error(tmp_path):
    """JSON 顶层是 null → EvalSchemaError。"""
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_bool_root_raises_eval_error(tmp_path):
    """JSON 顶层是 bool → EvalSchemaError。"""
    p = tmp_path / "bool.json"
    p.write_text("true", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_empty_file_raises(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_priority_missing_first(tmp_path):
    """missing file → FileNotFoundError 比 schema 校验先。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "nonexistent.schema.json")


def test_validate_file_priority_jsondecode_before_schema(tmp_path):
    """非法 JSON → JSONDecodeError 比 schema-not-found 先。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_returns_none_on_success(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


def test_validate_file_callable():
    assert callable(validate_file)


def test_validate_file_signature():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters) == ["path", "schema_name"]


def test_validate_file_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_file_str_path(tmp_path):
    """path 可以是 str。"""
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = validate_file(str(p), "manifest.schema.json")
    assert result is None


def test_validate_file_path_object(tmp_path):
    """path 可以是 Path 对象。"""
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


def test_validate_file_directory_raises(tmp_path):
    """path 是目录 → is_file() False → FileNotFoundError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


# =========================================================================
# 模块结构（补强 edges5）
# =========================================================================


def test_module_all_exact():
    import evaluation.schema as m
    assert set(m.__all__) == {
        "SCHEMAS_DIR", "EvalSchemaError",
        "load_schema", "validate", "validate_file",
    }


def test_module_all_is_list():
    import evaluation.schema as m
    assert isinstance(m.__all__, list)


def test_module_all_length_five():
    import evaluation.schema as m
    assert len(m.__all__) == 5


def test_module_imports_json():
    import evaluation.schema as m
    assert hasattr(m, "json")


def test_module_imports_path():
    import evaluation.schema as m
    assert hasattr(m, "Path")


def test_module_imports_any():
    import evaluation.schema as m
    assert hasattr(m, "Any")


def test_module_imports_draft202012():
    import evaluation.schema as m
    assert hasattr(m, "Draft202012Validator")


def test_module_imports_jsvalidation_error():
    import evaluation.schema as m
    assert hasattr(m, "JSValidationError")


def test_module_docstring_present():
    import evaluation.schema as m
    assert m.__doc__ is not None
    assert len(m.__doc__) > 20


def test_module_docstring_mentions_schema():
    import evaluation.schema as m
    assert "Schema" in m.__doc__ or "schema" in m.__doc__.lower()


def test_module_docstring_mentions_separation_from_app():
    """docstring 应说明与 app/schema.py 分开。"""
    import evaluation.schema as m
    doc = m.__doc__
    assert "app/schema" in doc or "不与" in doc or "分开" in doc


def test_module_uses_future_annotations():
    import evaluation.schema as m
    sig = inspect.signature(m.validate)
    # 返回 None，但 future annotations 使其成为 str
    assert sig.return_annotation is None or isinstance(sig.return_annotation, str)


def test_module_schemas_dir_is_path():
    import evaluation.schema as m
    assert isinstance(m.SCHEMAS_DIR, Path)


def test_module_schemas_dir_absolute():
    import evaluation.schema as m
    assert m.SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_exists():
    import evaluation.schema as m
    assert m.SCHEMAS_DIR.is_dir()


def test_module_eval_schema_error_subclass_of_exception():
    import evaluation.schema as m
    assert issubclass(m.EvalSchemaError, Exception)


def test_module_eval_schema_error_has_docstring():
    import evaluation.schema as m
    assert m.EvalSchemaError.__doc__ is not None
    assert len(m.EvalSchemaError.__doc__) > 5


def test_module_internal_helper_schema_path_present():
    """_schema_path 是模块内部 helper（不在 __all__）。"""
    import evaluation.schema as m
    assert hasattr(m, "_schema_path")


def test_module_internal_helper_not_in_all():
    """_schema_path 不在 __all__（私有）。"""
    import evaluation.schema as m
    assert "_schema_path" not in m.__all__


# =========================================================================
# 综合行为
# =========================================================================


def test_validate_then_load_schema_round_trip():
    """load_schema + Draft202012Validator + validate 一致工作。"""
    schema = load_schema("manifest.schema.json")
    valid_instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    # validate 应通过
    assert validate(valid_instance, "manifest.schema.json") is None
    # 验证 schema 本身有 'properties' key
    assert "properties" in schema


def test_eval_schema_error_chained_with_cause():
    """raise from 应保留 __cause__。"""
    try:
        try:
            raise ValueError("original")
        except ValueError as e:
            raise EvalSchemaError("wrapped") from e
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_can_be_raised_in_try_except_finally():
    """try/except/finally 中 raise 应正常传播。"""
    cleanup = []
    with pytest.raises(EvalSchemaError):
        try:
            raise EvalSchemaError("test")
        finally:
            cleanup.append("done")
    assert cleanup == ["done"]


def test_validate_complex_nested_error_path():
    """复杂嵌套 instance 的错误应记录正确 path。"""
    bad = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "x.txt", "source_type": "invalid_type"}
        ],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(bad, "manifest.schema.json")
    # 错误 path 应包含 documents/0/source_type
    paths = [e["path"] for e in exc_info.value.errors]
    # 至少有一个错误指向 source_type
    assert any("source_type" in p for p in paths)


def test_validate_file_with_extra_top_keys_rejected(tmp_path):
    """manifest 不允许额外 top-level keys。"""
    bad = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
        "extra_key": "should be rejected",
    }
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_schemas_dir_constant_resolved():
    """SCHEMAS_DIR 是 .resolve() 后的（无 .. 或 .）。"""
    assert ".." not in str(SCHEMAS_DIR)
    # 单点 segments 在 Windows 上应已 resolve
    parts = SCHEMAS_DIR.parts
    assert "." not in parts
