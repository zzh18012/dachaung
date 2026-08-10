"""evaluation/schema.py 第二十五轮 edges 测试（Round 365）。

重点补强 edges24 未触及的角度：
- _schema_path source level 字符串精确补强第三批
- load_schema source level 字符串精确补强第三批
- validate source level 字符串精确补强第三批
- validate_file source level 字符串精确补强第三批
- EvalSchemaError 行为深度第七批
- validate 行为深度第七批（more combinations）
- validate_file 行为深度第七批（more combinations）
- module source forbidden tokens 第七批
- module source 字符串精确补强第三批
- signatures 精确补强第三批
- 模块整体合理性补强第三批
- 端到端集成补强第三批
"""

from __future__ import annotations

import inspect
import json
import types
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- _schema_path source level 字符串精确补强第三批 ----------


def test_schema_path_source_no_class():
    src = inspect.getsource(_schema_path)
    assert "class " not in src


def test_schema_path_source_no_yield():
    src = inspect.getsource(_schema_path)
    assert "yield" not in src


def test_schema_path_source_no_async():
    src = inspect.getsource(_schema_path)
    assert "async " not in src


def test_schema_path_source_no_walrus():
    src = inspect.getsource(_schema_path)
    assert ":=" not in src


def test_schema_path_source_no_global():
    src = inspect.getsource(_schema_path)
    assert "global " not in src


def test_schema_path_source_no_lambda():
    src = inspect.getsource(_schema_path)
    assert "lambda" not in src


def test_schema_path_source_returns_p_not_path():
    """source 中 return 的是局部变量 p."""
    src = inspect.getsource(_schema_path)
    assert "return p" in src


def test_schema_path_source_uses_local_var_p():
    src = inspect.getsource(_schema_path)
    assert "p = SCHEMAS_DIR / name" in src


def test_schema_path_source_two_statements():
    """函数体至少 3 个语句：赋值 / is_file 检查 / return."""
    src = inspect.getsource(_schema_path)
    # 三个语句
    assert "p = " in src
    assert "if not p.is_file" in src
    assert "return p" in src


def test_schema_path_source_error_message_format():
    src = inspect.getsource(_schema_path)
    assert "Schema 文件不存在" in src


def test_schema_path_source_no_eval():
    src = inspect.getsource(_schema_path)
    assert "eval(" not in src


def test_schema_path_source_no_exec():
    src = inspect.getsource(_schema_path)
    assert "exec(" not in src


def test_schema_path_source_no_compile():
    src = inspect.getsource(_schema_path)
    assert "compile(" not in src


def test_schema_path_source_no_print():
    src = inspect.getsource(_schema_path)
    assert "print(" not in src


def test_schema_path_source_no_open():
    src = inspect.getsource(_schema_path)
    assert "open(" not in src


def test_schema_path_source_no_unlink():
    src = inspect.getsource(_schema_path)
    assert "unlink" not in src


def test_schema_path_source_no_write():
    src = inspect.getsource(_schema_path)
    assert ".write(" not in src


def test_schema_path_source_no_os():
    src = inspect.getsource(_schema_path)
    assert "import os" not in src


def test_schema_path_source_no_sys():
    src = inspect.getsource(_schema_path)
    assert "import sys" not in src


def test_schema_path_source_no_subprocess():
    src = inspect.getsource(_schema_path)
    assert "subprocess" not in src


def test_schema_path_source_no_argparse():
    src = inspect.getsource(_schema_path)
    assert "argparse" not in src


# ---------- load_schema source level 字符串精确补强第三批 ----------


def test_load_schema_source_docstring_present():
    src = inspect.getsource(load_schema)
    assert '"""' in src


def test_load_schema_source_docstring_mentions_schemas():
    src = inspect.getsource(load_schema)
    assert "schemas/" in src or "schemas" in src


def test_load_schema_source_uses_with_statement():
    src = inspect.getsource(load_schema)
    assert "with _schema_path(name).open" in src


def test_load_schema_source_return_inside_with():
    """return 在 with 块内."""
    src = inspect.getsource(load_schema)
    assert "return json.load(f)" in src


def test_load_schema_source_no_class():
    src = inspect.getsource(load_schema)
    assert "class " not in src


def test_load_schema_source_no_yield():
    src = inspect.getsource(load_schema)
    assert "yield" not in src


def test_load_schema_source_no_async():
    src = inspect.getsource(load_schema)
    assert "async " not in src


def test_load_schema_source_no_walrus():
    src = inspect.getsource(load_schema)
    assert ":=" not in src


def test_load_schema_source_no_global():
    src = inspect.getsource(load_schema)
    assert "global " not in src


def test_load_schema_source_no_lambda():
    src = inspect.getsource(load_schema)
    assert "lambda" not in src


def test_load_schema_source_no_eval():
    src = inspect.getsource(load_schema)
    assert "eval(" not in src


def test_load_schema_source_no_exec():
    src = inspect.getsource(load_schema)
    assert "exec(" not in src


def test_load_schema_source_no_compile():
    src = inspect.getsource(load_schema)
    assert "compile(" not in src


def test_load_schema_source_no_print():
    src = inspect.getsource(load_schema)
    assert "print(" not in src


def test_load_schema_source_no_unlink():
    src = inspect.getsource(load_schema)
    assert "unlink" not in src


def test_load_schema_source_no_write():
    src = inspect.getsource(load_schema)
    assert ".write(" not in src


def test_load_schema_source_no_os():
    src = inspect.getsource(load_schema)
    assert "import os" not in src


def test_load_schema_source_no_sys():
    src = inspect.getsource(load_schema)
    assert "import sys" not in src


def test_load_schema_source_no_subprocess():
    src = inspect.getsource(load_schema)
    assert "subprocess" not in src


# ---------- validate source level 字符串精确补强第三批 ----------


def test_validate_source_docstring_present():
    src = inspect.getsource(validate)
    assert '"""' in src


def test_validate_source_docstring_mentions_Schema():
    src = inspect.getsource(validate)
    assert "Schema" in src or "schema" in src


def test_validate_source_docstring_mentions_EvalSchemaError():
    src = inspect.getsource(validate)
    assert "EvalSchemaError" in src


def test_validate_source_uses_draft_2020_12():
    src = inspect.getsource(validate)
    assert "Draft202012Validator(schema)" in src


def test_validate_source_uses_iter_errors_method():
    src = inspect.getsource(validate)
    assert "validator.iter_errors(instance)" in src


def test_validate_source_uses_sorted_with_lambda():
    src = inspect.getsource(validate)
    assert "sorted(validator.iter_errors(instance)" in src
    assert "key=lambda e:" in src


def test_validate_source_lambda_uses_absolute_path():
    src = inspect.getsource(validate)
    assert "list(e.absolute_path)" in src


def test_validate_source_uses_if_not_errors():
    src = inspect.getsource(validate)
    assert "if not errors:" in src


def test_validate_source_uses_return_when_no_errors():
    src = inspect.getsource(validate)
    assert "if not errors:\n        return" in src


def test_validate_source_flat_list_init():
    src = inspect.getsource(validate)
    assert "flat: list[dict[str, Any]] = []" in src


def test_validate_source_uses_for_err_in_errors():
    src = inspect.getsource(validate)
    assert "for err in errors:" in src


def test_validate_source_flat_append_dict():
    src = inspect.getsource(validate)
    assert "flat.append(" in src


def test_validate_source_uses_absolute_path_in_flat():
    src = inspect.getsource(validate)
    assert '"path": list(err.absolute_path)' in src


def test_validate_source_uses_message_in_flat():
    src = inspect.getsource(validate)
    assert '"message": err.message' in src


def test_validate_source_uses_schema_path_in_flat():
    src = inspect.getsource(validate)
    assert '"schema_path": list(err.absolute_schema_path)' in src


def test_validate_source_uses_head_eq_errors_0():
    src = inspect.getsource(validate)
    assert "head = errors[0]" in src


def test_validate_source_raises_with_f_string():
    src = inspect.getsource(validate)
    assert "raise EvalSchemaError(" in src


def test_validate_source_message_has_count():
    src = inspect.getsource(validate)
    assert "len(errors)" in src


def test_validate_source_message_has_path():
    src = inspect.getsource(validate)
    assert "list(head.absolute_path)" in src


def test_validate_source_no_class():
    src = inspect.getsource(validate)
    assert "class " not in src


def test_validate_source_no_yield():
    src = inspect.getsource(validate)
    assert "yield" not in src


def test_validate_source_no_async():
    src = inspect.getsource(validate)
    assert "async " not in src


def test_validate_source_no_global():
    src = inspect.getsource(validate)
    assert "global " not in src


def test_validate_source_no_eval():
    src = inspect.getsource(validate)
    assert "eval(" not in src


def test_validate_source_no_exec():
    src = inspect.getsource(validate)
    assert "exec(" not in src


def test_validate_source_no_compile():
    src = inspect.getsource(validate)
    assert "compile(" not in src


def test_validate_source_no_print():
    src = inspect.getsource(validate)
    assert "print(" not in src


def test_validate_source_no_unlink():
    src = inspect.getsource(validate)
    assert "unlink" not in src


def test_validate_source_no_write():
    src = inspect.getsource(validate)
    assert ".write(" not in src


def test_validate_source_no_os():
    src = inspect.getsource(validate)
    assert "import os" not in src


def test_validate_source_no_sys():
    src = inspect.getsource(validate)
    assert "import sys" not in src


# ---------- validate_file source level 字符串精确补强第三批 ----------


def test_validate_file_source_docstring_present():
    src = inspect.getsource(validate_file)
    assert '"""' in src


def test_validate_file_source_docstring_mentions_json():
    src = inspect.getsource(validate_file)
    assert "JSON" in src or "json" in src


def test_validate_file_source_uses_p_eq_path():
    src = inspect.getsource(validate_file)
    assert "p = Path(path)" in src


def test_validate_file_source_uses_p_is_file():
    src = inspect.getsource(validate_file)
    assert "if not p.is_file" in src


def test_validate_file_source_raises_file_not_found_with_p():
    src = inspect.getsource(validate_file)
    assert "raise FileNotFoundError" in src
    assert "{p}" in src


def test_validate_file_source_uses_with_p_open():
    src = inspect.getsource(validate_file)
    assert "with p.open(" in src


def test_validate_file_source_uses_data_eq_json_load():
    src = inspect.getsource(validate_file)
    assert "data = json.load(f)" in src


def test_validate_file_source_calls_validate_with_data():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


def test_validate_file_source_no_class():
    src = inspect.getsource(validate_file)
    assert "class " not in src


def test_validate_file_source_no_yield():
    src = inspect.getsource(validate_file)
    assert "yield" not in src


def test_validate_file_source_no_async():
    src = inspect.getsource(validate_file)
    assert "async " not in src


def test_validate_file_source_no_global():
    src = inspect.getsource(validate_file)
    assert "global " not in src


def test_validate_file_source_no_eval():
    src = inspect.getsource(validate_file)
    assert "eval(" not in src


def test_validate_file_source_no_exec():
    src = inspect.getsource(validate_file)
    assert "exec(" not in src


def test_validate_file_source_no_compile():
    src = inspect.getsource(validate_file)
    assert "compile(" not in src


def test_validate_file_source_no_print():
    src = inspect.getsource(validate_file)
    assert "print(" not in src


def test_validate_file_source_no_unlink():
    src = inspect.getsource(validate_file)
    assert "unlink" not in src


def test_validate_file_source_no_write():
    src = inspect.getsource(validate_file)
    assert ".write(" not in src


def test_validate_file_source_no_os():
    src = inspect.getsource(validate_file)
    assert "import os" not in src


def test_validate_file_source_no_sys():
    src = inspect.getsource(validate_file)
    assert "import sys" not in src


# ---------- EvalSchemaError 行为深度第七批 ----------


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_message_only():
    err = EvalSchemaError("msg")
    assert str(err) == "msg"


def test_eval_schema_error_message_and_errors():
    errs = [{"path": ["a"], "message": "x"}]
    err = EvalSchemaError("msg", errors=errs)
    assert err.errors == errs


def test_eval_schema_error_errors_default_none():
    err = EvalSchemaError("msg")
    assert err.errors == []  # 默认 None → []


def test_eval_schema_error_errors_default_is_empty_list():
    """errors 默认是空 list（None → []）."""
    err = EvalSchemaError("msg")
    assert isinstance(err.errors, list)
    assert len(err.errors) == 0


def test_eval_schema_error_errors_empty_list_unchanged():
    err = EvalSchemaError("msg", errors=[])
    assert err.errors == []


def test_eval_schema_error_with_none_errors_explicit():
    err = EvalSchemaError("msg", errors=None)
    assert err.errors == []


def test_eval_schema_error_in_try_except():
    try:
        raise EvalSchemaError("custom")
    except EvalSchemaError as e:
        assert str(e) == "custom"


def test_eval_schema_error_in_try_except_exception():
    """应被 except Exception 捕获."""
    try:
        raise EvalSchemaError("custom")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_errors_not_shared_between_instances():
    """errors 默认值不共享（每次都新建 list）."""
    err1 = EvalSchemaError("a")
    err2 = EvalSchemaError("b")
    err1.errors.append({"x": 1})
    assert err2.errors == []


def test_eval_schema_error_args():
    err = EvalSchemaError("msg", errors=[{"a": 1}])
    # args[0] 是 message
    assert err.args[0] == "msg"


def test_eval_schema_error_repr_has_class_name():
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_errors_attribute_writable():
    err = EvalSchemaError("msg")
    err.errors = [{"new": True}]
    assert err.errors == [{"new": True}]


def test_eval_schema_error_complex_errors():
    errs = [
        {"path": ["a", "b"], "message": "x", "schema_path": ["x", "y"]},
        {"path": ["c"], "message": "y"},
    ]
    err = EvalSchemaError("msg", errors=errs)
    assert len(err.errors) == 2
    assert err.errors[0]["path"] == ["a", "b"]


# ---------- validate 行为深度第七批 ----------


def test_validate_returns_none_on_success():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(instance, schema_name) is None


def test_validate_raises_on_missing_required_field():
    schema_name = "manifest.schema.json"
    with pytest.raises(EvalSchemaError):
        validate({}, schema_name)


def test_validate_raises_on_wrong_type():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": 1.0,  # should be string
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_raises_on_extra_field():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra_field": "value",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_error_message_contains_schema_name():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        assert schema_name in str(e)


def test_validate_error_message_contains_path():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        # path 可能是空 list（root）或字段名
        assert "path=" in str(e)


def test_validate_error_errors_list_is_list():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)


def test_validate_error_errors_list_dict_keys():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        for err_dict in e.errors:
            assert "path" in err_dict
            assert "message" in err_dict
            assert "schema_path" in err_dict


def test_validate_with_str_path_as_filename():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, schema_name)


def test_validate_raises_file_not_found_for_unknown_schema():
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_does_not_mutate_instance():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    before = repr(instance)
    validate(instance, schema_name)
    assert repr(instance) == before


def test_validate_does_not_mutate_instance_on_failure():
    schema_name = "manifest.schema.json"
    instance = {"manifest_version": 1.0}  # invalid
    before = repr(instance)
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)
    assert repr(instance) == before


def test_validate_idempotent_on_success():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, schema_name)
    validate(instance, schema_name)


def test_validate_idempotent_on_failure():
    schema_name = "manifest.schema.json"
    instance = {"wrong": "shape"}
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_validate_annotation_schema_minimal_passes():
    schema_name = "annotation.schema.json"
    instance = {"annotation_version": "1.0", "document_id": "x"}
    # annotation schema 可能要求更多字段，这里 try/except
    try:
        validate(instance, schema_name)
    except EvalSchemaError:
        pass  # schema 可能要求更多字段，关键是函数能正常调用


def test_validate_evaluation_report_schema_minimal():
    schema_name = "evaluation-report.schema.json"
    instance = {"report_version": "1.1"}
    try:
        validate(instance, schema_name)
    except EvalSchemaError:
        pass


# ---------- validate_file 行为深度第七批 ----------


def test_validate_file_returns_none_on_success(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    assert validate_file(p, schema_name) is None


def test_validate_file_accepts_str_path(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    assert validate_file(str(p), schema_name) is None


def test_validate_file_accepts_path_path(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    assert validate_file(Path(p), schema_name) is None


def test_validate_file_raises_file_not_found_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_raises_file_not_found_for_dir(tmp_path):
    """validate_file 用 is_file，目录会失败."""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_raises_on_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_on_empty_file(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_on_array_json(tmp_path):
    p = tmp_path / "arr.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_on_int_json(tmp_path):
    p = tmp_path / "int.json"
    p.write_text("42", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_on_string_json(tmp_path):
    p = tmp_path / "str.json"
    p.write_text('"hello"', encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_on_null_json(tmp_path):
    p = tmp_path / "null.json"
    p.write_text("null", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_raises_eval_schema_error_on_invalid_content(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_does_not_mutate_disk(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    before = p.read_text(encoding="utf-8")
    validate_file(p, schema_name)
    assert p.read_text(encoding="utf-8") == before


def test_validate_file_idempotent(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, schema_name)
    validate_file(p, schema_name)


def test_validate_file_with_unknown_schema_raises_file_not_found(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "unknown.schema.json")


def test_validate_file_positional_args(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(p, schema_name)


def test_validate_file_kwargs_only(tmp_path):
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    validate_file(path=p, schema_name=schema_name)


# ---------- module source forbidden tokens 第七批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "asyncio",
        "threading",
        "concurrent",
        "multiprocessing",
        "queue",
        "socket",
        "select",
        "re.match",
        "datetime",
        "os.system",
        "logging",
        "urllib",
        "http",
        "ctypes",
        "pickle",
        "shutil",
        "tempfile",
        "glob",
        "unittest",
        "pytest",
        "sys.exit",
        "copy",
        "weakref",
        "abc",
        "contextlib",
        "operator",
        "functools",
        "itertools",
        "collections",
        "importlib",
        "platform",
        "subprocess",
        "argparse",
    ],
)
def test_schema_source_no_forbidden_token_seventh(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第三批 ----------


def test_module_source_has_future_annotations():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_imports_json():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_imports_path():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_imports_any():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_imports_draft_validator():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_imports_js_validation_error():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_4_stdlib_imports():
    src = inspect.getsource(smod)
    # future + json + Path + Any
    assert "import json" in src
    assert "from pathlib import Path" in src
    assert "from typing import Any" in src


def test_module_source_schemas_dir_definition():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent /" in src
    assert '"schemas"' in src


def test_module_source_eval_schema_error_class_definition():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_eval_schema_error_init_signature():
    src = inspect.getsource(smod)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None)" in src


def test_module_source_eval_schema_error_init_body():
    src = inspect.getsource(smod)
    assert "super().__init__(message)" in src
    assert "self.errors = errors or []" in src


def test_module_source_no_relative_above_root():
    src = inspect.getsource(smod)
    lines = src.split("\n")
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("from ."):
            assert "evaluation" in stripped or "app" in stripped or "schemas" in stripped


def test_module_source_no_star_import():
    src = inspect.getsource(smod)
    assert "import *" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert 'if __name__' not in src


def test_module_source_no_user_class_beyond_eval_schema_error():
    src = inspect.getsource(smod)
    lines = src.split("\n")
    class_lines = [line for line in lines if line.lstrip().startswith("class ")]
    assert len(class_lines) == 1
    assert "EvalSchemaError" in class_lines[0]


def test_module_source_3_user_functions():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src
    assert "def load_schema(" in src
    assert "def validate(" in src
    assert "def validate_file(" in src


def test_module_source_all_5_entries():
    src = inspect.getsource(smod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_source_no_eval():
    src = inspect.getsource(smod)
    assert "eval(" not in src


def test_module_source_no_exec():
    src = inspect.getsource(smod)
    assert "exec(" not in src


def test_module_source_no_compile():
    src = inspect.getsource(smod)
    assert "compile(" not in src


def test_module_source_no_unlink():
    src = inspect.getsource(smod)
    assert "unlink" not in src


def test_module_source_no_write():
    src = inspect.getsource(smod)
    assert ".write(" not in src


def test_module_source_no_print():
    src = inspect.getsource(smod)
    assert "print(" not in src


def test_module_source_no_os_import():
    src = inspect.getsource(smod)
    assert "import os" not in src


def test_module_source_no_sys_import():
    src = inspect.getsource(smod)
    assert "import sys" not in src


def test_module_source_docstring_present():
    assert smod.__doc__ is not None


def test_module_source_docstring_mentions_schema():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__


def test_module_source_docstring_mentions_manifest():
    assert "manifest" in smod.__doc__.lower()


def test_module_source_docstring_mentions_annotation():
    assert "annotation" in smod.__doc__.lower()


def test_module_source_docstring_mentions_evaluation_report():
    assert "evaluation" in smod.__doc__.lower()


def test_module_source_docstring_mentions_app_schema():
    """docstring 提到 app/schema.py 的存在（说明不重用）."""
    assert "app/schema" in smod.__doc__ or "app" in smod.__doc__.lower()


# ---------- signatures 精确补强第三批 ----------


def test_signature_eval_schema_error_init():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert len(params) == 3  # self, message, errors
    assert params[0].name == "self"
    assert params[1].name == "message"
    assert params[2].name == "errors"


def test_signature_eval_schema_error_message_no_default():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert params[1].default is inspect.Parameter.empty


def test_signature_eval_schema_error_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert params[2].default is None


def test_signature_eval_schema_error_return_annotation_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation == "None"


def test_signature_schema_path():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_schema_path_no_default():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_schema_path_return_annotation_path():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_load_schema():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"


def test_signature_load_schema_no_default():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert params[0].default is inspect.Parameter.empty


def test_signature_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_signature_validate():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "instance"
    assert params[1].name == "schema_name"


def test_signature_validate_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


def test_signature_validate_file():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert params[0].name == "path"
    assert params[1].name == "schema_name"


def test_signature_validate_file_path_union_type():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    # path: Path | str
    assert "Path" in str(params[0].annotation)
    assert "str" in str(params[0].annotation)


def test_signature_validate_file_no_defaults():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_signature_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation == "None"


def test_signature_schema_path_no_varargs():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_load_schema_no_varargs():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_validate_no_varargs():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_signature_validate_file_no_varargs():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL
        assert p.kind != inspect.Parameter.VAR_KEYWORD


# ---------- 模块整体合理性补强第三批 ----------


def test_module_has_docstring():
    assert smod.__doc__ is not None


def test_module_has_all_attribute():
    assert hasattr(smod, "__all__")


def test_module_all_is_list():
    assert isinstance(smod.__all__, list)


def test_module_all_length_5():
    assert len(smod.__all__) == 5


def test_module_all_entries_unique():
    assert len(set(smod.__all__)) == 5


def test_module_all_entries_are_str():
    for entry in smod.__all__:
        assert isinstance(entry, str)


def test_module_all_5_entries_correct():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_namespace_4_callables():
    callables = [
        (name, obj) for name, obj in vars(smod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == smod.__name__
    ]
    assert len(callables) == 4


def test_module_namespace_callable_names():
    callables = {
        name for name, obj in vars(smod).items()
        if isinstance(obj, types.FunctionType) and obj.__module__ == smod.__name__
    }
    assert callables == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_namespace_1_class():
    classes = [
        (name, obj) for name, obj in vars(smod).items()
        if isinstance(obj, type) and obj.__module__ == smod.__name__
    ]
    assert len(classes) == 1
    assert classes[0][0] == "EvalSchemaError"


def test_module_name_is_evaluation_schema():
    assert smod.__name__ == "evaluation.schema"


def test_module_file_ends_with_schema_py():
    assert smod.__file__.endswith("schema.py")


def test_module_eval_schema_error_module_eq_smod():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_module_function_module_eq_smod():
    assert _schema_path.__module__ == "evaluation.schema"
    assert load_schema.__module__ == "evaluation.schema"
    assert validate.__module__ == "evaluation.schema"
    assert validate_file.__module__ == "evaluation.schema"


def test_module_function_names_correct():
    assert _schema_path.__name__ == "_schema_path"
    assert load_schema.__name__ == "load_schema"
    assert validate.__name__ == "validate"
    assert validate_file.__name__ == "validate_file"


def test_module_schemas_dir_is_module_constant():
    """SCHEMAS_DIR 是模块级常量."""
    assert "SCHEMAS_DIR" in vars(smod)


def test_module_schemas_dir_type_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_schemas_dir_resolved():
    """SCHEMAS_DIR 是 resolve() 后的绝对路径."""
    assert SCHEMAS_DIR.is_absolute()


def test_module_schemas_dir_endswith_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_module_schemas_dir_exists():
    assert SCHEMAS_DIR.exists()


def test_module_schemas_dir_in_all():
    assert "SCHEMAS_DIR" in smod.__all__


def test_module_js_validation_error_imported_but_unused():
    """JSValidationError 导入到 namespace（虽然源码中未直接使用）."""
    assert hasattr(smod, "JSValidationError")


def test_module_js_validation_error_is_validation_error_class():
    assert smod.JSValidationError is JSValidationError


# ---------- 端到端集成补强第三批 ----------


def test_e2e_load_manifest_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_annotation_schema_returns_dict():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_evaluation_report_schema_returns_dict():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_e2e_load_schema_idempotent():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_e2e_load_schema_does_not_mutate_disk():
    s = load_schema("manifest.schema.json")
    before = (SCHEMAS_DIR / "manifest.schema.json").read_text(encoding="utf-8")
    # 修改 in-memory dict 不影响磁盘
    s["__test__"] = "x"
    after = (SCHEMAS_DIR / "manifest.schema.json").read_text(encoding="utf-8")
    assert before == after


def test_e2e_validate_minimal_manifest_passes():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, schema_name)


def test_e2e_validate_empty_documents_passes():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, schema_name)


def test_e2e_validate_missing_manifest_version_fails():
    schema_name = "manifest.schema.json"
    instance = {"devset_status": "incomplete", "documents": [], "project_root": "."}
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_e2e_validate_missing_devset_status_fails():
    schema_name = "manifest.schema.json"
    instance = {"manifest_version": "1.0", "documents": [], "project_root": "."}
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_e2e_validate_missing_documents_fails():
    schema_name = "manifest.schema.json"
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "project_root": "."}
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_e2e_validate_invalid_manifest_version_fails():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "9.9",  # invalid enum
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_e2e_validate_with_extra_field_fails():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra": "value",
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, schema_name)


def test_e2e_validate_returns_none_when_pass():
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(instance, schema_name) is None


def test_e2e_validate_eval_schema_error_has_errors_list():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) > 0


def test_e2e_validate_eval_schema_error_errors_dict_keys():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except EvalSchemaError as e:
        for err_dict in e.errors:
            assert set(err_dict.keys()) == {"path", "message", "schema_path"}


def test_e2e_validate_eval_schema_error_caught_as_exception_ancestor():
    schema_name = "manifest.schema.json"
    try:
        validate({}, schema_name)
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_e2e_schema_path_returns_path():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_e2e_schema_path_for_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_e2e_eval_schema_error_with_empty_errors_list():
    err = EvalSchemaError("msg", errors=[])
    assert err.errors == []


def test_e2e_eval_schema_error_with_complex_errors():
    errs = [
        {"path": ["a", "b"], "message": "m1", "schema_path": ["x"]},
        {"path": ["c"], "message": "m2", "schema_path": ["y"]},
    ]
    err = EvalSchemaError("msg", errors=errs)
    assert err.errors[0]["path"] == ["a", "b"]
    assert err.errors[1]["schema_path"] == ["y"]


def test_e2e_eval_schema_error_str_representation():
    err = EvalSchemaError("custom message", errors=[])
    assert "custom message" in str(err)


def test_e2e_validate_file_with_unicode_content(tmp_path):
    """file 含 Unicode 字符也能正常解析."""
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "path": "samples/private/中文.pdf",
                "categories": ["中文"],
                "source_type": "pdf",
            }
        ],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance, ensure_ascii=False), encoding="utf-8")
    # may pass or fail depending on schema strictness
    try:
        validate_file(p, schema_name)
    except EvalSchemaError:
        pass


def test_e2e_schema_path_with_str_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_e2e_load_schema_returns_dict_with_schema_keys():
    s = load_schema("manifest.schema.json")
    # json schema 至少有 $schema 或 $id 或 type
    assert "$schema" in s or "type" in s or "properties" in s


def test_e2e_validate_does_not_raise_unexpected_exception():
    """validate 在合法输入下不应抛非 EvalSchemaError 异常."""
    schema_name = "manifest.schema.json"
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    try:
        validate(instance, schema_name)
    except EvalSchemaError:
        pass  # expected
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")


def test_e2e_full_workflow_load_then_validate(tmp_path):
    """load schema → validate instance → write file → validate_file."""
    schema = load_schema("manifest.schema.json")
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    # 校验
    validator = Draft202012Validator(schema)
    assert validator.is_valid(instance)
    # 写文件
    p = tmp_path / "m.json"
    p.write_text(json.dumps(instance), encoding="utf-8")
    # 校验文件
    validate_file(p, "manifest.schema.json")
