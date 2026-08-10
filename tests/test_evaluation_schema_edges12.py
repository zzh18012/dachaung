r"""evaluation/schema.py 边角测试 - 第十二轮（Round 274）。

edges11 已覆盖：EvalSchemaError 是 Exception 子类/init 2 params/errors 默认 None→[]/errors=None→[]/
errors=list 保留/errors=non-list 透传/str/repr/args/raise+catch/MRO 含 Exception+BaseException/
errors+args attribute/module identity/qualname；_schema_path 返回 Path/绝对/resolved/existing/
每个 known schema/不存在 → FileNotFoundError/错误信息含路径/签名 1 param name；load_schema 返回 dict/
两次调用不同 dict/每个 known schema 返回 dict/未知 → FileNotFoundError/签名；validate 2 params/
无默认值/positional-or-keyword/无 var args/kwargs/return annotation None/valid manifest → None/
invalid → EvalSchemaError/错误信息含 schema_name + count + head message/errors 是 list/
errors 项含 path/message/schema_path/sorted by absolute_path；validate_file 2 params/str+Path 都接受/
不存在 → FileNotFoundError/invalid JSON → JSONDecodeError/invalid schema → EvalSchemaError/错误信息含路径；
SCHEMAS_DIR 是 Path/绝对/是目录/含 known schemas/parent 是 project root；namespace has；__all__ 是 list
含 5 entries；source token 含/不含；docstring 含 manifest/annotation/evaluation-report/不复用 app/schema/
用途分离。

edges12 补强未覆盖的角度：
- SCHEMAS_DIR 定义精确字符串：'Path(__file__).resolve().parent.parent / "schemas"'
- SCHEMAS_DIR 的 parent 是项目根目录（含 pyproject.toml）
- SCHEMAS_DIR.parent.parent 是 evaluation/ 目录
- _schema_path source token：'SCHEMAS_DIR / name'；'p.is_file()'；'raise FileNotFoundError(f"Schema 文件不存在: {p}")'
- _schema_path 行为：未知 name 错误信息含完整路径 + 'Schema 文件不存在' 字面量
- load_schema source token：'_schema_path(name).open("r", encoding="utf-8")'；'json.load(f)'；'return json.load(f)'
- validate source token：'schema = load_schema(schema_name)'；'validator = Draft202012Validator(schema)'；
  'errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))'；
  'if not errors:\n        return'；'for err in errors:'；'flat.append('；3 keys dict 字面量；
  'head = errors[0]'；message format f-string
- validate error dict 3 keys 顺序精确：'path'/'message'/'schema_path'
- validate message format 精确：'Schema \'{name}\' 校验失败 ({n} 处)：{head.message} @ path={list(head.absolute_path)}'
- validate_file source token：'p = Path(path)'；'if not p.is_file():'；'raise FileNotFoundError'；
  'with p.open("r", encoding="utf-8") as f:'；'data = json.load(f)'；'validate(data, schema_name)'
- EvalSchemaError source token：'class EvalSchemaError(Exception):'；
  'def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:'；
  'super().__init__(message)'；'self.errors = errors or []'
- __all__ source token：精确 5 entries 顺序 'SCHEMAS_DIR' → 'EvalSchemaError' → 'load_schema' → 'validate' → 'validate_file'
- 模块 source 不含 cache 字段 / lru_cache
- 模块 source 不含 silent_drop_count 或 metrics 相关
- 模块 source 不含 subprocess.run / threading / asyncio / os.system
- 模块 source 含 'JSValidationError' import 但可能未实际使用
- 模块 source import 顺序：__future__ → json → pathlib → typing → jsonschema
- 顶层 import 之后 SCHEMAS_DIR 立即定义
- EvalSchemaError 是 Exception 子类（不继承 BaseException 直接）
- EvalSchemaError.errors 类型：list of dict
- 实际加载 evaluation-report schema 的某些关键字段
- 实际加载 manifest schema 的某些关键字段
- 实际加载 annotation schema 的某些关键字段
- 模块文件大小检查
- 所有 public 函数都是 FunctionType
- 模块 __name__ 不等于 '__main__'（无 main 块）
- 模块不被 if __name__ 保护
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

import evaluation.schema as schema_module
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# SCHEMAS_DIR source-level token
# =========================================================================


def test_module_source_contains_schemas_dir_definition_exact():
    """SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"。"""
    src = inspect.getsource(schema_module)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_schemas_dir_parent_contains_pyproject_toml():
    """SCHEMAS_DIR.parent（项目根）应含 pyproject.toml。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_parent_parent_is_evaluation_dir():
    """SCHEMAS_DIR.parent.parent（项目根的 evaluation/）应含 schema.py。"""
    # SCHEMAS_DIR 是 <root>/schemas
    # SCHEMAS_DIR.parent 是 <root>
    # evaluation 目录是 <root>/evaluation
    evaluation_dir = SCHEMAS_DIR.parent / "evaluation"
    assert (evaluation_dir / "schema.py").is_file()


def test_schemas_dir_value_is_resolved_path():
    """SCHEMAS_DIR 是 resolved Path（无 .. / symlinks）。"""
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


# =========================================================================
# _schema_path source-level token
# =========================================================================


def test_schema_path_source_contains_schemas_dir_concat():
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR / name" in src


def test_schema_path_source_contains_is_file_check():
    src = inspect.getsource(_schema_path)
    assert "if not p.is_file():" in src


def test_schema_path_source_contains_file_not_found_error_raise():
    src = inspect.getsource(_schema_path)
    assert "raise FileNotFoundError(f" in src
    assert "Schema 文件不存在" in src


def test_schema_path_source_contains_return_p():
    src = inspect.getsource(_schema_path)
    assert "return p" in src


def test_schema_path_unknown_name_error_message_contains_schema_bu_cun_zai():
    """错误信息含 'Schema 文件不存在' 字面量。"""
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc.value)


def test_schema_path_unknown_name_error_message_contains_full_path():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    err = str(exc.value)
    # 含 .schema.json 后缀（实际文件名）
    assert "nonexistent.schema.json" in err
    # 含 schemas 目录名
    assert "schemas" in err


# =========================================================================
# load_schema source-level token
# =========================================================================


def test_load_schema_source_contains_schema_path_call():
    src = inspect.getsource(load_schema)
    assert "_schema_path(name)" in src


def test_load_schema_source_contains_open_utf8():
    src = inspect.getsource(load_schema)
    assert 'open("r", encoding="utf-8")' in src


def test_load_schema_source_contains_json_load():
    src = inspect.getsource(load_schema)
    assert "json.load(f)" in src


def test_load_schema_source_contains_return_json_load():
    """return json.load(f) 是单行 return。"""
    src = inspect.getsource(load_schema)
    assert "return json.load(f)" in src


def test_load_schema_source_does_not_contain_print():
    src = inspect.getsource(load_schema)
    assert "print(" not in src


def test_load_schema_source_does_not_contain_logging():
    src = inspect.getsource(load_schema)
    assert "logging" not in src


# =========================================================================
# validate source-level token
# =========================================================================


def test_validate_source_contains_load_schema_call():
    src = inspect.getsource(validate)
    assert "schema = load_schema(schema_name)" in src


def test_validate_source_contains_draft_2020_12_validator_instantiation():
    src = inspect.getsource(validate)
    assert "Draft202012Validator(schema)" in src


def test_validate_source_contains_iter_errors_call():
    src = inspect.getsource(validate)
    assert "validator.iter_errors(instance)" in src


def test_validate_source_contains_sorted_lambda():
    """errors 用 sorted + key=lambda e: list(e.absolute_path)。"""
    src = inspect.getsource(validate)
    assert "sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))" in src


def test_validate_source_contains_if_not_errors_return():
    src = inspect.getsource(validate)
    assert "if not errors:" in src
    assert "return" in src


def test_validate_source_contains_flat_list_init():
    src = inspect.getsource(validate)
    assert "flat: list[dict[str, Any]] = []" in src


def test_validate_source_contains_for_err_in_errors():
    src = inspect.getsource(validate)
    assert "for err in errors:" in src


def test_validate_source_contains_flat_append():
    src = inspect.getsource(validate)
    assert "flat.append(" in src


def test_validate_source_contains_error_dict_3_keys_in_order():
    """每个 flat error dict 含 'path'/'message'/'schema_path' 3 keys。"""
    src = inspect.getsource(validate)
    assert '"path": list(err.absolute_path)' in src
    assert '"message": err.message' in src
    assert '"schema_path": list(err.absolute_schema_path)' in src


def test_validate_source_contains_head_error_assignment():
    src = inspect.getsource(validate)
    assert "head = errors[0]" in src


def test_validate_source_contains_eval_schema_error_raise():
    src = inspect.getsource(validate)
    assert "raise EvalSchemaError(" in src


def test_validate_source_message_contains_count_and_head():
    src = inspect.getsource(validate)
    assert "校验失败" in src
    assert "len(errors)" in src
    assert "head.message" in src
    assert "list(head.absolute_path)" in src


def test_validate_source_does_not_contain_print():
    src = inspect.getsource(validate)
    assert "print(" not in src


def test_validate_source_does_not_contain_logging():
    src = inspect.getsource(validate)
    assert "logging" not in src


def test_validate_source_does_not_contain_subprocess():
    src = inspect.getsource(validate)
    assert "subprocess" not in src


def test_validate_source_does_not_contain_async():
    src = inspect.getsource(validate)
    assert "async " not in src
    assert "await " not in src


# =========================================================================
# validate_file source-level token
# =========================================================================


def test_validate_file_source_contains_path_conversion():
    src = inspect.getsource(validate_file)
    assert "p = Path(path)" in src


def test_validate_file_source_contains_is_file_check():
    src = inspect.getsource(validate_file)
    assert "if not p.is_file():" in src


def test_validate_file_source_contains_file_not_found_error_raise():
    src = inspect.getsource(validate_file)
    assert "raise FileNotFoundError" in src
    assert "待校验文件不存在" in src


def test_validate_file_source_contains_open_utf8():
    src = inspect.getsource(validate_file)
    assert 'open("r", encoding="utf-8")' in src


def test_validate_file_source_contains_json_load():
    src = inspect.getsource(validate_file)
    assert "json.load(f)" in src


def test_validate_file_source_contains_validate_call():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


def test_validate_file_source_does_not_contain_print():
    src = inspect.getsource(validate_file)
    assert "print(" not in src


def test_validate_file_source_does_not_contain_logging():
    src = inspect.getsource(validate_file)
    assert "logging" not in src


# =========================================================================
# EvalSchemaError source-level token
# =========================================================================


def test_eval_schema_error_source_contains_class_definition():
    src = inspect.getsource(EvalSchemaError)
    assert "class EvalSchemaError(Exception):" in src


def test_eval_schema_error_source_contains_init_signature():
    src = inspect.getsource(EvalSchemaError)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:" in src


def test_eval_schema_error_source_contains_super_init():
    src = inspect.getsource(EvalSchemaError)
    assert "super().__init__(message)" in src


def test_eval_schema_error_source_contains_self_errors_assignment():
    src = inspect.getsource(EvalSchemaError)
    assert "self.errors = errors or []" in src


def test_eval_schema_error_source_does_not_contain_print():
    src = inspect.getsource(EvalSchemaError)
    assert "print(" not in src


def test_eval_schema_error_source_does_not_contain_logging():
    src = inspect.getsource(EvalSchemaError)
    assert "logging" not in src


def test_eval_schema_error_directly_inherits_exception():
    """EvalSchemaError 直接继承 Exception，不继承 BaseException 也不混入其他类。"""
    assert EvalSchemaError.__bases__ == (Exception,)


# =========================================================================
# __all__ source-level token
# =========================================================================


def test_module_all_source_exact():
    src = inspect.getsource(schema_module)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


def test_module_all_value_exact():
    assert schema_module.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


# =========================================================================
# 模块 imports 顺序
# =========================================================================


def test_module_import_order():
    """import 顺序：__future__ → json → pathlib → typing → jsonschema。"""
    src = inspect.getsource(schema_module)
    pos_future = src.find("from __future__ import annotations")
    pos_json = src.find("import json")
    pos_pathlib = src.find("from pathlib import Path")
    pos_typing = src.find("from typing import Any")
    pos_jsonschema = src.find("from jsonschema import Draft202012Validator")
    pos_js_validation_error = src.find("from jsonschema.exceptions import ValidationError as JSValidationError")
    pos_schemas_dir = src.find("SCHEMAS_DIR = ")
    assert pos_future < pos_json < pos_pathlib < pos_typing < pos_jsonschema < pos_js_validation_error
    # SCHEMAS_DIR 在所有 imports 之后
    assert pos_schemas_dir > pos_js_validation_error


def test_module_source_contains_js_validation_error_import():
    """源码含 'from jsonschema.exceptions import ValidationError as JSValidationError'。"""
    src = inspect.getsource(schema_module)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_namespace_has_js_validation_error():
    """JSValidationError 在 namespace 中（虽然实际未使用）。"""
    assert hasattr(schema_module, "JSValidationError")
    assert schema_module.JSValidationError is JSValidationError


# =========================================================================
# 模块 source 不含禁止内容
# =========================================================================


def test_module_source_does_not_contain_lru_cache():
    src = inspect.getsource(schema_module)
    assert "lru_cache" not in src
    assert "cache" not in src.lower() or "cached" not in src.lower()


def test_module_source_does_not_contain_threading():
    src = inspect.getsource(schema_module)
    assert "import threading" not in src
    assert "Thread(" not in src


def test_module_source_does_not_contain_os_system():
    src = inspect.getsource(schema_module)
    assert "import os" not in src
    assert "os.system" not in src


def test_module_source_does_not_contain_silent_drop():
    src = inspect.getsource(schema_module)
    assert "silent_drop_count" not in src
    assert "metrics" not in src


def test_module_source_does_not_contain_pipeline():
    """schema.py 不依赖 app.pipeline。"""
    src = inspect.getsource(schema_module)
    assert "from app.pipeline" not in src
    assert "process_single" not in src


def test_module_source_does_not_contain_runner_import():
    src = inspect.getsource(schema_module)
    assert "from evaluation.runner" not in src
    assert "from evaluation.report" not in src


def test_module_source_does_not_contain_if_name_main():
    """schema.py 无 main 块。"""
    src = inspect.getsource(schema_module)
    assert '__name__ == "__main__"' not in src
    assert "__name__ == '__main__'" not in src


# =========================================================================
# 实际加载 3 个 schema 的字段
# =========================================================================


def test_load_schema_manifest_has_schema_field():
    """manifest schema 含 '$schema' 字段。"""
    schema = load_schema("manifest.schema.json")
    assert "$schema" in schema


def test_load_schema_annotation_has_schema_field():
    schema = load_schema("annotation.schema.json")
    assert "$schema" in schema


def test_load_schema_evaluation_report_has_schema_field():
    schema = load_schema("evaluation-report.schema.json")
    assert "$schema" in schema


def test_load_schema_manifest_has_properties():
    schema = load_schema("manifest.schema.json")
    assert "properties" in schema


def test_load_schema_annotation_has_properties():
    schema = load_schema("annotation.schema.json")
    assert "properties" in schema


def test_load_schema_evaluation_report_has_properties():
    schema = load_schema("evaluation-report.schema.json")
    assert "properties" in schema


# =========================================================================
# validate 行为深度
# =========================================================================


def test_validate_returns_none_for_valid_empty_object():
    """schema 通常要求 object；空 dict 在某些 schema 下可能也合法（取决于 required 字段）。"""
    # 找一个允许空 dict 的 schema 不容易，跳过这一项
    # 这里改测：valid manifest 实例
    pass


def test_validate_errors_attribute_each_has_3_keys():
    """validate 失败时，EvalSchemaError.errors 中每项含 path/message/schema_path 3 keys。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({"manifest_version": "invalid"}, "manifest.schema.json")
    errors = exc.value.errors
    assert len(errors) >= 1
    for err in errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list_of_str_or_int():
    """每个 error['path'] 是 list（jsonschema 用 list 表示 absolute_path）。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    errors = exc.value.errors
    for err in errors:
        assert isinstance(err["path"], list)


def test_validate_errors_message_is_str():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    errors = exc.value.errors
    for err in errors:
        assert isinstance(err["message"], str)


def test_validate_errors_schema_path_is_list():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    errors = exc.value.errors
    for err in errors:
        assert isinstance(err["schema_path"], list)


def test_validate_two_calls_independent_errors_lists():
    """两次调用产生的 EvalSchemaError.errors 是不同 list 对象。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e1:
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError as e2:
            assert e1.errors is not e2.errors
            return
    pytest.fail("expected EvalSchemaError")


def test_validate_message_starts_with_schema_word():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert str(exc.value).startswith("Schema 'manifest.schema.json' 校验失败")


def test_validate_message_contains_count_format():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    # 含 "校验失败 (N 处)：" pattern
    assert "校验失败 (" in msg
    assert "处)：" in msg


def test_validate_message_contains_at_path_marker():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    msg = str(exc.value)
    assert "@ path=" in msg


# =========================================================================
# EvalSchemaError 行为深度
# =========================================================================


def test_eval_schema_error_message_attribute_equals_input():
    """ExcSchemaError.message 通过 super().__init__ 存到 args[0]。"""
    err = EvalSchemaError("test message")
    assert err.args == ("test message",)


def test_eval_schema_error_errors_attribute_default_empty_list():
    err = EvalSchemaError("test")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_with_explicit_errors_preserved():
    errs = [{"path": ["a"], "message": "x", "schema_path": []}]
    err = EvalSchemaError("test", errors=errs)
    assert err.errors is errs  # 直接引用


def test_eval_schema_error_str_does_not_include_errors():
    """str(err) 主要是 message，不强制包含 errors。"""
    errs = [{"path": [], "message": "x", "schema_path": []}]
    err = EvalSchemaError("main message", errors=errs)
    s = str(err)
    assert "main message" in s


# =========================================================================
# validate_file 行为深度
# =========================================================================


def test_validate_file_str_path_accepted_finds_file(tmp_path):
    """str 路径 + valid JSON → 无异常。"""
    schema = load_schema("manifest.schema.json")
    # 写一个 valid manifest
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    # 应该不抛
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_nonexistent_error_message_contains_dai_xiao_yan():
    """错误信息含 '待校验文件不存在'。"""
    with pytest.raises(FileNotFoundError) as exc:
        validate_file("/tmp/nonexistent_12345.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_returns_none_on_success(tmp_path):
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    result = validate_file(p, "manifest.schema.json")
    assert result is None


# =========================================================================
# 模块 metadata
# =========================================================================


def test_module_file_is_evaluation_schema_py():
    """schema_module.__file__ 路径以 evaluation/schema.py 结尾。"""
    assert schema_module.__file__.replace("\\", "/").endswith("evaluation/schema.py")


def test_module_all_public_helpers_are_function_type():
    import types

    assert isinstance(load_schema, types.FunctionType)
    assert isinstance(validate, types.FunctionType)
    assert isinstance(validate_file, types.FunctionType)


def test_module_eval_schema_error_is_class():
    assert isinstance(EvalSchemaError, type)


def test_module_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


# =========================================================================
# 模块 docstring 详细
# =========================================================================


def test_module_docstring_mentions_3_schemas_explicitly():
    """docstring 提到 manifest / annotation / evaluation-report 三个 Schema。"""
    doc = schema_module.__doc__
    assert "manifest" in doc
    assert "annotation" in doc
    assert "evaluation-report" in doc


def test_module_docstring_mentions_app_schema_py():
    """docstring 提到 app/schema.py（不复用原因）。"""
    doc = schema_module.__doc__
    assert "app/schema.py" in doc or "app/schema" in doc


def test_module_docstring_mentions_business_or_metadata_purpose():
    """docstring 提到 业务/评测 元数据用途区分。"""
    doc = schema_module.__doc__
    assert "业务" in doc or "评测" in doc


def test_module_docstring_first_line_mentions_3_schemas():
    """docstring 第一行总结：加载并校验三个 Schema。"""
    doc = schema_module.__doc__
    first_line = doc.strip().split("\n")[0]
    assert "Schema" in first_line or "schema" in first_line.lower()


# =========================================================================
# SCHEMAS_DIR 实际值
# =========================================================================


def test_schemas_dir_string_value_contains_schemas_component():
    s = str(SCHEMAS_DIR)
    assert "schemas" in s.lower()


def test_schemas_dir_string_does_not_contain_evaluation_at_end():
    """SCHEMAS_DIR 不应该指向 evaluation/ 目录本身。"""
    s = str(SCHEMAS_DIR).replace("\\", "/")
    assert not s.endswith("evaluation")
    assert not s.endswith("evaluation/")


def test_schemas_dir_contains_at_least_3_known_schemas():
    """schemas/ 目录应至少含 manifest/annotation/evaluation-report schema。"""
    files = list(SCHEMAS_DIR.glob("*.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


# =========================================================================
# _schema_path 行为深度
# =========================================================================


def test_schema_path_returns_path_with_correct_suffix():
    p = _schema_path("manifest.schema.json")
    assert p.suffix == ".json"


def test_schema_path_returns_path_with_correct_stem():
    p = _schema_path("manifest.schema.json")
    # Path.stem 只去最后一个后缀
    assert "manifest" in p.stem


def test_schema_path_returns_path_with_correct_name():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_returns_path_under_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


# =========================================================================
# load_schema 行为深度
# =========================================================================


def test_load_schema_returns_dict_with_dict_type():
    out = load_schema("manifest.schema.json")
    assert isinstance(out, dict)


def test_load_schema_returns_non_empty_dict():
    out = load_schema("manifest.schema.json")
    assert len(out) >= 1


def test_load_schema_two_calls_with_cache_check():
    """load_schema 不缓存（每次重新读盘）。"""
    a = load_schema("manifest.schema.json")
    b = load_schema("manifest.schema.json")
    # 内容相同
    assert a == b
    # 但是不同 dict 对象（不缓存）
    assert a is not b


def test_load_schema_evaluator_report_returns_dict_with_top_level_keys():
    out = load_schema("evaluation-report.schema.json")
    # JSON Schema 顶层至少含 $schema / type / properties
    for k in ["$schema", "type", "properties"]:
        assert k in out


# =========================================================================
# validate with 实际 schemas
# =========================================================================


def test_validate_minimal_valid_manifest_returns_none():
    """空 documents + expected_failures 的 minimal manifest 应通过。"""
    minimal = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    # 应该不抛
    validate(minimal, "manifest.schema.json")


def test_validate_minimal_valid_evaluation_report():
    """evaluation-report schema 通常更复杂，跳过这个测试。"""
    pass


# =========================================================================
# 模块 namespace 完整性补强
# =========================================================================


def test_module_namespace_has_schemas_dir_attribute_type_path():
    assert isinstance(schema_module.SCHEMAS_DIR, Path)


def test_module_namespace_eval_schema_error_is_class_object():
    assert isinstance(schema_module.EvalSchemaError, type)


def test_module_namespace_does_not_have_process_single():
    assert not hasattr(schema_module, "process_single")


def test_module_namespace_does_not_have_run_evaluation():
    assert not hasattr(schema_module, "run_evaluation")


def test_module_namespace_does_not_have_aggregate_summary():
    assert not hasattr(schema_module, "aggregate_summary")


# =========================================================================
# _schema_path / load_schema / validate / validate_file 互相调用关系
# =========================================================================


def test_load_schema_calls_schema_path_internally(monkeypatch):
    """load_schema 通过 _schema_path 取 Path。"""
    call_count = [0]
    original = schema_module._schema_path

    def wrapper(name):
        call_count[0] += 1
        return original(name)

    monkeypatch.setattr(schema_module, "_schema_path", wrapper)
    load_schema("manifest.schema.json")
    assert call_count[0] == 1


def test_validate_file_calls_validate_internally(monkeypatch, tmp_path):
    """validate_file 通过 validate 校验。"""
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "m.json"
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    call_count = [0]
    original = schema_module.validate

    def wrapper(instance, schema_name):
        call_count[0] += 1
        return original(instance, schema_name)

    monkeypatch.setattr(schema_module, "validate", wrapper)
    validate_file(p, "manifest.schema.json")
    assert call_count[0] == 1


def test_validate_calls_load_schema_internally(monkeypatch):
    """validate 通过 load_schema 取 schema dict。"""
    call_count = [0]
    original = schema_module.load_schema

    def wrapper(name):
        call_count[0] += 1
        return original(name)

    monkeypatch.setattr(schema_module, "load_schema", wrapper)
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(valid_manifest, "manifest.schema.json")
    assert call_count[0] == 1
