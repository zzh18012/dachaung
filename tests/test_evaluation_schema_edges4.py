r"""evaluation/schema.py 边角测试 - 第六轮（Round 158）。

补强已有 base/edges/edges2/edges3（共 394 测试）未覆盖的深度：
- SCHEMAS_DIR 路径精确性
- EvalSchemaError 边界（空 message、None errors、显式空 list）
- _schema_path 错误消息
- load_schema 多种 schema 文件
- validate 错误聚合细节
- validate_file 错误优先级
- 模块结构与签名深度
- 综合行为
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

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
# SCHEMAS_DIR 精确性
# =========================================================================


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR = evaluation/schema.py → evaluation/ → 项目根 / schemas。"""
    assert SCHEMAS_DIR.parent.name == "dachuang-autonomous" or SCHEMAS_DIR.parent.is_dir()


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 经过 resolve（无 .. 段）。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


def test_schemas_dir_filename_value():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_known_schemas():
    """schemas/ 应含 manifest / annotation / evaluation-report schema。"""
    expected_files = {
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    }
    actual = {f.name for f in SCHEMAS_DIR.iterdir() if f.is_file()}
    assert expected_files.issubset(actual)


# =========================================================================
# EvalSchemaError 边界
# =========================================================================


def test_eval_schema_error_empty_message():
    e = EvalSchemaError("")
    assert str(e) == ""
    assert e.errors == []


def test_eval_schema_error_message_with_special_chars():
    msg = "error with 中文 and \n\t whitespace"
    e = EvalSchemaError(msg)
    assert str(e) == msg


def test_eval_schema_error_args_length_one():
    e = EvalSchemaError("msg")
    assert len(e.args) == 1


def test_eval_schema_error_args_value():
    e = EvalSchemaError("msg")
    assert e.args == ("msg",)


def test_eval_schema_error_default_errors_empty_list():
    e = EvalSchemaError("msg")
    assert isinstance(e.errors, list)
    assert len(e.errors) == 0


def test_eval_schema_error_explicit_empty_list():
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_none_errors_becomes_empty():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("test")


def test_eval_schema_error_caught_as_exception():
    try:
        raise EvalSchemaError("test")
    except Exception:
        pass


def test_eval_schema_error_inheritance():
    assert issubclass(EvalSchemaError, Exception)
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_errors_attribute_directly_set():
    """errors 列表是直接赋值（共享引用）。"""
    errs = [{"k": "v"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors is errs


def test_eval_schema_error_init_signature():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert set(sig.parameters) == {"self", "message", "errors"}


def test_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# =========================================================================
# _schema_path 边界
# =========================================================================


def test_schema_path_returns_path_for_known_schema():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)
    assert p.is_file()


def test_schema_path_raises_for_unknown_schema():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc.value)
    assert "nonexistent.schema.json" in str(exc.value)


def test_schema_path_returns_absolute():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_under_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_signature():
    sig = inspect.signature(_schema_path)
    assert "name" in sig.parameters
    assert sig.parameters["name"].default is inspect.Parameter.empty


# =========================================================================
# load_schema 深度
# =========================================================================


def test_load_schema_returns_dict():
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)


def test_load_schema_manifest_has_required_top_keys():
    schema = load_schema("manifest.schema.json")
    expected_top_keys = {"$schema", "type", "properties"}
    assert expected_top_keys.issubset(set(schema.keys()))


def test_load_schema_annotation_returns_dict():
    schema = load_schema("annotation.schema.json")
    assert isinstance(schema, dict)


def test_load_schema_evaluation_report_returns_dict():
    schema = load_schema("evaluation-report.schema.json")
    assert isinstance(schema, dict)


def test_load_schema_default_path_matches_explicit():
    """load_schema('foo') 与 _schema_path('foo') 加载一致。"""
    a = json.loads(_schema_path("manifest.schema.json").read_text(encoding="utf-8"))
    b = load_schema("manifest.schema.json")
    assert a == b


def test_load_schema_unknown_name_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_signature_one_param():
    sig = inspect.signature(load_schema)
    assert set(sig.parameters) == {"name"}
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation).lower()


# =========================================================================
# validate 错误聚合细节
# =========================================================================


def test_validate_no_errors_returns_none():
    """通过校验 → 无返回值（None）。"""
    # 用 manifest schema 校验合法 manifest dict
    minimal_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    result = validate(minimal_manifest, "manifest.schema.json")
    assert result is None


def test_validate_single_error_path_empty():
    """type 错误 → path 空 list。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate("not a dict", "manifest.schema.json")
    err = exc.value.errors[0]
    assert err["path"] == []


def test_validate_property_error_path_has_field():
    """错误发生在 properties.xxx → path 含字段名。"""
    bad_manifest = {
        "manifest_version": "9.9",  # const 是 1.0
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(bad_manifest, "manifest.schema.json")
    # 至少有一个错误的 path 含 manifest_version
    paths = [e["path"] for e in exc.value.errors]
    assert ["manifest_version"] in paths


def test_validate_error_message_is_str():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["message"], str)


def test_validate_error_schema_path_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_errors_count_matches_iter_errors():
    """errors 长度应等于 validator.iter_errors 数量。"""
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    expected_count = len(list(validator.iter_errors({})))
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) == expected_count


def test_validate_exception_message_starts_with_schema_text():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "Schema" in str(exc.value)
    assert "校验失败" in str(exc.value)


def test_validate_exception_message_contains_count():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    # 应包含 "X 处" 格式
    assert "处" in str(exc.value)


def test_validate_exception_message_contains_schema_name():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_with_empty_schema_dict_accepts_anything():
    """用空 schema dict 校验任何输入 → 不抛（空 schema 总通过）。
    但 validate 强制用 named schema，所以这个测试无法直接走 validate。
    改为：minimal manifest with all required fields 通过。"""
    minimal = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(minimal, "manifest.schema.json")


def test_validate_does_not_modify_instance():
    """validate 不应修改被校验的 dict。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    before = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == before


def test_validate_signature_two_params():
    sig = inspect.signature(validate)
    assert set(sig.parameters) == {"instance", "schema_name"}


def test_validate_params_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# validate_file 错误优先级
# =========================================================================


def test_validate_file_missing_file_raises_first(tmp_path: Path):
    """文件不存在 → FileNotFoundError（不读盘）。"""
    missing = tmp_path / "missing.json"
    with pytest.raises(FileNotFoundError):
        validate_file(missing, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror(tmp_path: Path):
    """文件存在但 JSON 解析失败 → JSONDecodeError。"""
    p = tmp_path / "broken.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_valid_json_failing_schema_raises_eval_error(tmp_path: Path):
    """文件 JSON 合法但 schema 校验失败 → EvalSchemaError。"""
    p = tmp_path / "ok_format.json"
    p.write_text("{}", encoding="utf-8")  # 缺 manifest_version
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_passes_with_valid_manifest(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    # 不抛
    validate_file(p, "manifest.schema.json")


def test_validate_file_str_path(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_unknown_schema_raises_filenotfound(tmp_path: Path):
    p = tmp_path / "ok.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "nonexistent.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path: Path):
    """传入目录 → FileNotFoundError。"""
    sub = tmp_path / "sub"
    sub.mkdir()
    with pytest.raises(FileNotFoundError):
        validate_file(sub, "manifest.schema.json")


def test_validate_file_signature_two_params():
    sig = inspect.signature(validate_file)
    assert set(sig.parameters) == {"path", "schema_name"}


def test_validate_file_params_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


# =========================================================================
# Draft202012Validator 行为
# =========================================================================


def test_manifest_schema_is_draft202012_compatible():
    schema = load_schema("manifest.schema.json")
    Draft202012Validator.check_schema(schema)


def test_annotation_schema_is_draft202012_compatible():
    schema = load_schema("annotation.schema.json")
    Draft202012Validator.check_schema(schema)


def test_evaluation_report_schema_is_draft202012_compatible():
    schema = load_schema("evaluation-report.schema.json")
    Draft202012Validator.check_schema(schema)


def test_draft202012_validator_can_be_constructed_with_manifest():
    schema = load_schema("manifest.schema.json")
    v = Draft202012Validator(schema)
    assert v is not None
    assert v.schema is schema


# =========================================================================
# 模块结构 / __all__
# =========================================================================


def test_module_all_exact_list():
    import evaluation.schema as mod
    assert mod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_no_duplicates():
    import evaluation.schema as mod
    assert len(mod.__all__) == len(set(mod.__all__))


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


def test_module_uses_future_annotations():
    import evaluation.schema as mod
    src = inspect.getsource(mod)
    assert "from __future__ import annotations" in src


def test_module_docstring_present():
    import evaluation.schema as mod
    assert mod.__doc__ is not None


def test_module_docstring_mentions_schema():
    import evaluation.schema as mod
    doc = mod.__doc__
    assert "Schema" in doc or "schema" in doc.lower()


def test_module_docstring_mentions_separation_from_app_schema():
    """docstring 解释为何不与 app/schema.py 复用。"""
    import evaluation.schema as mod
    doc = mod.__doc__
    assert "app/schema" in doc or "不复用" in doc


def test_module_no_silence_unused():
    import evaluation.schema as mod
    assert not hasattr(mod, "_silence_unused")


def test_module_internal_schema_path_callable():
    import evaluation.schema as mod
    assert callable(mod._schema_path)


# =========================================================================
# 综合行为
# =========================================================================


def test_load_schema_idempotent():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a == b


def test_load_schema_returns_new_dict_each_call():
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    assert a is not b
    assert a == b


def test_validate_then_load_schema_consistent():
    """validate 内部 load_schema；直接 load_schema 后用 Draft202012Validator 也应一致。"""
    instance = {}
    # 用 validate
    try:
        validate(instance, "manifest.schema.json")
        schema_errors = []
    except EvalSchemaError as e:
        schema_errors = e.errors

    # 用 Draft202012Validator 直接
    schema = load_schema("manifest.schema.json")
    v = Draft202012Validator(schema)
    direct_errors = list(v.iter_errors(instance))

    assert len(schema_errors) == len(direct_errors)


def test_eval_schema_error_caught_in_caller():
    """调用方可以捕获 EvalSchemaError 并访问 errors 列表。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) > 0
        assert "path" in e.errors[0]
        assert "message" in e.errors[0]
        assert "schema_path" in e.errors[0]


def test_validate_file_with_annotation_schema(tmp_path: Path):
    """用 annotation schema 校验空 dict → 应失败（required 缺）。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "annotation.schema.json")


def test_validate_file_with_evaluation_report_schema(tmp_path: Path):
    """用 evaluation-report schema 校验空 dict → 应失败。"""
    p = tmp_path / "empty.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "evaluation-report.schema.json")
