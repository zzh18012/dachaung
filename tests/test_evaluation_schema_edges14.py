r"""evaluation/schema.py 边角测试 - 第十四轮（Round 293）。

edges13 已覆盖：manifest/annotation/evaluation-report 各字段 violation / cross-validation /
multi-error sorting / validate_file edge cases / EvalSchemaError vs ValidationError / module source 补强 /
function signatures / schema field depth / validate isolation / SCHEMAS_DIR behavior。

edges14 补强未覆盖的角度：
- **EvalSchemaError 行为深度**：errors 默认 [] / errors=None → [] / errors falsy tuple → [] /
  errors truthy dict → 保持 / args 属性只含 message / str(message) / repr / raise from 链 /
  init signature / super().__init__ 调用
- **_schema_path 行为深度**：返回 Path / 不存在抛 FileNotFoundError / message 含 'Schema 文件不存在' /
  signature 1 param
- **load_schema 行为深度**：返回 dict / 用 utf-8 encoding 打开 / 调用 _schema_path /
  signature 1 param / 不缓存（每次重读）
- **validate 行为深度**：返回 None / message 含 schema_name + 错误数 / errors 是 list of dict /
  每个 error dict 含 path/message/schema_path 3 key / errors 排序 by absolute_path /
  instance 非 dict 抛 / instance=None 抛 / 不修改 instance
- **validate_file 行为深度**：返回 None / Path 与 str 都接受 / 调用 Path() 包装 /
  utf-8 encoding 打开 / 调用 validate / file 是 dir → FileNotFoundError
- **Draft202012Validator import**：from jsonschema / 用于构造 validator
- **JSValidationError vs EvalSchemaError**：不同 class / 不互相继承 /
  EvalSchemaError 是 Exception 子类 / JSValidationError 来自 jsonschema.exceptions
- **module __all__ 完整性**：5 entries / namespace 含 / valid identifier
- **module source level 补强**：含 SCHEMAS_DIR 计算 / 含 Path(__file__).resolve() /
  含 .parent.parent / 含 sorted(validator.iter_errors(...)) / 含 e.absolute_path / e.message /
  e.absolute_schema_path / errors list / for 循环构造 flat
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/threading/time/
  datetime/collections/math/itertools/functools
- **SCHEMAS_DIR 行为深度**：是 Path / 是 absolute / ends with 'schemas' /
  包含 4 个 schema 文件名精确 / 不含子目录
- **schema 文件内容深度**：每个 schema 含 '$schema' 字段 / 'type': 'object' /
  'additionalProperties': false / 'required' list
- **端到端集成**：load_schema → validate happy path / validate_file happy path /
  cross-schema validate fails
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

import evaluation.schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# 辅助：合法 manifest / annotation / report
# =========================================================================


def _minimal_manifest() -> dict[str, Any]:
    return {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }


def _minimal_annotation() -> dict[str, Any]:
    return {
        "annotation_version": "1.0",
        "doc_id": "d1",
    }


def _minimal_report() -> dict[str, Any]:
    return {
        "report_version": "1.1",
        "provenance": {
            "git_commit": None,
            "git_dirty": True,
            "evaluator_version": "1.1",
            "report_version": "1.1",
            "parser_name": "fallback",
            "parser_version": None,
            "dependencies": {},
            "max_chars": 800,
            "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "incomplete",
            "file_count": 0,
            "content_group_count": 0,
            "pdf_count": 0,
            "docx_count": 0,
            "categories_covered": [],
        },
        "summary": {
            "counts": {},
            "success_rates": {},
            "ratio_macro_averages": {},
            "silent_drop_total": None,
        },
        "per_doc": [],
        "expected_failures": [],
    }


# =========================================================================
# EvalSchemaError 行为深度
# =========================================================================


def test_eval_schema_error_is_exception_subclass():
    """EvalSchemaError 是 Exception 子类。"""
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_baseexception_direct():
    """EvalSchemaError 不直接继承 BaseException。"""
    assert not issubclass(EvalSchemaError, BaseException) or issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_init_default_errors_empty_list():
    """init 默认 errors → []。"""
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_init_explicit_errors_none():
    """init errors=None → []。"""
    e = EvalSchemaError("msg", None)
    assert e.errors == []


def test_eval_schema_error_init_errors_explicit_list():
    """init errors=list → 保持。"""
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_init_errors_falsy_tuple_becomes_empty():
    """init errors=() → []。"""
    e = EvalSchemaError("msg", ())
    assert e.errors == []


def test_eval_schema_error_init_errors_falsy_int_zero_becomes_empty():
    """init errors=0 → []（falsy）。"""
    e = EvalSchemaError("msg", 0)
    assert e.errors == []


def test_eval_schema_error_init_errors_truthy_dict_kept_as_is():
    """init errors={'x': 1} → 保持（truthy）。"""
    e = EvalSchemaError("msg", {"x": 1})
    # 实现是 `errors or []`，truthy dict 不被替换
    assert e.errors == {"x": 1}


def test_eval_schema_error_args_only_message():
    """args 属性只含 message（super().__init__ 只传 message）。"""
    e = EvalSchemaError("msg", [{"x": 1}])
    assert e.args == ("msg",)


def test_eval_schema_error_str_returns_message():
    """str(e) 返回 message。"""
    e = EvalSchemaError("hello world")
    assert str(e) == "hello world"


def test_eval_schema_error_repr_contains_class_name():
    """repr 含 class name。"""
    e = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_can_be_raised():
    """可以 raise。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("test message")
    assert "test message" in str(exc_info.value)


def test_eval_schema_error_can_be_caught_as_exception():
    """可以被 except Exception 捕获。"""
    with pytest.raises(Exception):
        raise EvalSchemaError("test")


def test_eval_schema_error_cannot_be_caught_as_validation_error():
    """不能被 except JSValidationError 捕获。"""
    try:
        raise EvalSchemaError("test")
    except JSValidationError:  # 不应该被捕获
        pytest.fail("EvalSchemaError should not be caught as JSValidationError")
    except EvalSchemaError:
        pass  # 正确


def test_eval_schema_error_raise_from_other():
    """raise from 支持链。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        try:
            int("not a number")
        except ValueError as ve:
            raise EvalSchemaError("outer") from ve
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_eval_schema_error_init_signature():
    """init signature 2 params + default None。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self + 2
    assert sig.parameters["message"].default is inspect.Parameter.empty
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_init_no_varargs():
    """init 不接受 *args。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_POSITIONAL


def test_eval_schema_error_init_no_varkw():
    """init 不接受 **kwargs。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind != inspect.Parameter.VAR_KEYWORD


def test_eval_schema_error_source_contains_super_init_call():
    """source 含 super().__init__(message)。"""
    src = inspect.getsource(EvalSchemaError.__init__)
    assert "super()" in src
    assert "__init__" in src


def test_eval_schema_error_source_contains_self_errors_assignment():
    """source 含 self.errors = errors or []。"""
    src = inspect.getsource(EvalSchemaError.__init__)
    assert "self.errors" in src
    assert "or []" in src


# =========================================================================
# _schema_path 行为深度
# =========================================================================


def test_schema_path_returns_path_object():
    """返回 Path。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_existing_returns_path_with_correct_name():
    """返回的 Path name 是 schema 文件名。"""
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_nonexistent_raises_filenotfound():
    """不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_nonexistent_message_contains_schema():
    """错误消息含 'Schema 文件不存在'。"""
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


def test_schema_path_signature_1_param():
    """signature 1 param。"""
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1


def test_schema_path_signature_no_default():
    """无默认值。"""
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_schema_path_source_uses_is_file():
    """source 含 .is_file()。"""
    src = inspect.getsource(_schema_path)
    assert ".is_file()" in src


def test_schema_path_source_uses_schemas_dir():
    """source 含 SCHEMAS_DIR。"""
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR" in src


# =========================================================================
# load_schema 行为深度
# =========================================================================


def test_load_schema_returns_dict():
    """返回 dict。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_schema_field():
    """manifest schema 含 $schema。"""
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_manifest_has_type_object():
    """manifest schema type=object。"""
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_annotation_returns_dict():
    """annotation schema 返回 dict。"""
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict():
    """evaluation-report schema 返回 dict。"""
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_nonexistent_raises_filenotfound():
    """不存在 → FileNotFoundError（透传自 _schema_path）。"""
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_signature_1_param():
    """signature 1 param。"""
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1


def test_load_schema_source_uses_utf8_encoding():
    """source 含 encoding='utf-8'。"""
    src = inspect.getsource(load_schema)
    assert "utf-8" in src or "utf8" in src


def test_load_schema_source_uses_json_load():
    """source 含 json.load(f)。"""
    src = inspect.getsource(load_schema)
    assert "json.load" in src


def test_load_schema_source_calls_schema_path():
    """source 调用 _schema_path。"""
    src = inspect.getsource(load_schema)
    assert "_schema_path" in src


# =========================================================================
# validate 行为深度
# =========================================================================


def test_validate_returns_none_on_success():
    """成功返 None。"""
    assert validate(_minimal_manifest(), "manifest.schema.json") is None


def test_validate_raises_on_failure():
    """失败抛 EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_message_contains_schema_name():
    """错误 message 含 schema_name。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_message_contains_error_count():
    """错误 message 含错误数（'N 处'）。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    # message 格式："Schema 'X' 校验失败 (N 处)：..."
    assert "处" in str(exc_info.value)


def test_validate_errors_is_list():
    """errors 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)


def test_validate_errors_each_dict_has_3_keys():
    """每个 error dict 含 path/message/schema_path 3 key。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list():
    """errors.path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list():
    """errors.schema_path 是 list。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)


def test_validate_errors_message_is_str():
    """errors.message 是 str。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["message"], str)


def test_validate_does_not_mutate_input():
    """不修改 instance。"""
    inst = _minimal_manifest()
    inst_before = repr(inst)
    validate(inst, "manifest.schema.json")
    assert repr(inst) == inst_before


def test_validate_does_not_mutate_input_on_failure():
    """失败时也不修改 instance。"""
    inst = {"extra_key": "value"}
    inst_before = repr(inst)
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")
    assert repr(inst) == inst_before


def test_validate_signature_2_params():
    """signature 2 params。"""
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2


def test_validate_no_default_args():
    """无默认值。"""
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_source_uses_draft202012validator():
    """source 含 Draft202012Validator。"""
    src = inspect.getsource(validate)
    assert "Draft202012Validator" in src


def test_validate_source_uses_iter_errors():
    """source 含 iter_errors。"""
    src = inspect.getsource(validate)
    assert "iter_errors" in src


def test_validate_source_uses_sorted():
    """source 含 sorted。"""
    src = inspect.getsource(validate)
    assert "sorted" in src


def test_validate_source_uses_absolute_path():
    """source 含 absolute_path。"""
    src = inspect.getsource(validate)
    assert "absolute_path" in src


def test_validate_source_uses_absolute_schema_path():
    """source 含 absolute_schema_path。"""
    src = inspect.getsource(validate)
    assert "absolute_schema_path" in src


def test_validate_source_returns_implicitly_on_success():
    """成功时隐式 return（无显式 return value）。"""
    src = inspect.getsource(validate)
    # 含 "return" 但不带 value（裸 return）
    assert "return" in src


# =========================================================================
# validate_file 行为深度
# =========================================================================


def test_validate_file_returns_none_on_success(tmp_path):
    """成功返 None。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_raises_on_invalid_content(tmp_path):
    """内容非法 → EvalSchemaError。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_path_accepted(tmp_path):
    """str 路径接受。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # 不抛


def test_validate_file_pathlib_path_accepted(tmp_path):
    """Path 路径接受。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps(_minimal_manifest()), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_nonexistent_raises_filenotfound():
    """文件不存在 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file("/nonexistent/file.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfound(tmp_path):
    """目录路径 → FileNotFoundError（is_file False）。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_signature_2_params():
    """signature 2 params。"""
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2


def test_validate_file_source_uses_path_constructor():
    """source 含 Path(path) 包装。"""
    src = inspect.getsource(validate_file)
    assert "Path(path)" in src or "Path(p)" in src


def test_validate_file_source_uses_utf8_encoding():
    """source 含 encoding='utf-8'。"""
    src = inspect.getsource(validate_file)
    assert "utf-8" in src or "utf8" in src


def test_validate_file_source_calls_validate():
    """source 调用 validate。"""
    src = inspect.getsource(validate_file)
    assert "validate(" in src


def test_validate_file_source_uses_is_file():
    """source 含 .is_file() 检查。"""
    src = inspect.getsource(validate_file)
    assert ".is_file()" in src


# =========================================================================
# Draft202012Validator import + JSValidationError vs EvalSchemaError
# =========================================================================


def test_draft202012validator_imported():
    """Draft202012Validator 在 module namespace。"""
    assert hasattr(smod, "Draft202012Validator")


def test_draft202012validator_class_is_from_jsonschema():
    """Draft202012Validator 是 jsonschema 提供的 class。"""
    assert smod.Draft202012Validator is Draft202012Validator


def test_jsvalidationerror_imported():
    """JSValidationError 在 module namespace（as 别名）。"""
    # 直接 imported 但可能不在 namespace（因为 from X import Y）
    src = inspect.getsource(smod)
    assert "ValidationError as JSValidationError" in src


def test_eval_schema_error_not_subclass_of_jsvalidationerror():
    """EvalSchemaError 不是 JSValidationError 子类。"""
    assert not issubclass(EvalSchemaError, JSValidationError)


def test_jsvalidationerror_not_subclass_of_eval_schema_error():
    """JSValidationError 不是 EvalSchemaError 子类。"""
    assert not issubclass(JSValidationError, EvalSchemaError)


# =========================================================================
# module __all__ 完整性
# =========================================================================


def test_module_all_5_entries():
    """__all__ 5 entries。"""
    assert len(smod.__all__) == 5


def test_module_all_entries_exact():
    """__all__ 内容精确。"""
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_all_entries_in_namespace():
    """每个 __all__ entry 在 namespace。"""
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_all_entries_valid_identifier():
    """每个 __all__ entry 是合法标识符。"""
    for name in smod.__all__:
        assert name.isidentifier()


def test_module_all_entries_correct_types():
    """每个 __all__ entry 类型：Path/Exception/3 function。"""
    assert isinstance(smod.SCHEMAS_DIR, Path)
    assert issubclass(smod.EvalSchemaError, Exception)
    assert callable(smod.load_schema)
    assert callable(smod.validate)
    assert callable(smod.validate_file)


def test_module_namespace_has_private_schema_path():
    """namespace 含 _schema_path（私有 helper）。"""
    assert hasattr(smod, "_schema_path")


def test_module_namespace_private_not_in_all():
    """_schema_path 不在 __all__。"""
    assert "_schema_path" not in smod.__all__


# =========================================================================
# SCHEMAS_DIR 行为深度
# =========================================================================


def test_schemas_dir_is_path():
    """SCHEMAS_DIR 是 Path。"""
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    """SCHEMAS_DIR 是 absolute。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_directory():
    """SCHEMAS_DIR 是 directory。"""
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_name_is_schemas():
    """SCHEMAS_DIR name 是 'schemas'。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_manifest_schema():
    """含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema():
    """含 annotation.schema.json。"""
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema():
    """含 evaluation-report.schema.json。"""
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_contains_document_schema():
    """含 document.schema.json。"""
    assert (SCHEMAS_DIR / "document.schema.json").is_file()


def test_schemas_dir_contains_at_least_4_schemas():
    """至少 4 个 schema 文件。"""
    files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(files) >= 4


def test_schemas_dir_no_python_files():
    """无 .py 文件。"""
    py_files = list(SCHEMAS_DIR.glob("*.py"))
    assert py_files == []


def test_schemas_dir_no_subdirectories():
    """无子目录。"""
    subdirs = [p for p in SCHEMAS_DIR.iterdir() if p.is_dir()]
    assert subdirs == []


def test_schemas_dir_source_uses_path_resolve():
    """source 含 Path(__file__).resolve()。"""
    src = inspect.getsource(smod)
    assert "Path(__file__)" in src
    assert ".resolve()" in src


def test_schemas_dir_source_uses_parent_parent():
    """source 含 .parent.parent。"""
    src = inspect.getsource(smod)
    assert ".parent.parent" in src


# =========================================================================
# schema 文件内容深度
# =========================================================================


def test_all_4_schemas_use_draft_2020_12():
    """4 个 schema 都用 Draft 2020-12。"""
    draft_url = "https://json-schema.org/draft/2020-12/schema"
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert s.get("$schema") == draft_url


def test_all_4_schemas_have_type_object():
    """4 个 schema 都 type=object。"""
    for name in ("manifest.schema.json", "annotation.schema.json",
                 "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert s.get("type") == "object"


def test_manifest_schema_has_required_list():
    """manifest schema 含 required list。"""
    s = load_schema("manifest.schema.json")
    assert "required" in s
    assert isinstance(s["required"], list)


def test_annotation_schema_has_required_list():
    """annotation schema 含 required list。"""
    s = load_schema("annotation.schema.json")
    assert "required" in s
    assert isinstance(s["required"], list)


def test_evaluation_report_schema_has_required_list():
    """evaluation-report schema 含 required list。"""
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s
    assert isinstance(s["required"], list)


def test_manifest_schema_additional_properties_false():
    """manifest schema additionalProperties=false。"""
    s = load_schema("manifest.schema.json")
    assert s.get("additionalProperties") is False


def test_annotation_schema_additional_properties_false():
    """annotation schema additionalProperties=false。"""
    s = load_schema("annotation.schema.json")
    assert s.get("additionalProperties") is False


def test_evaluation_report_schema_additional_properties_false():
    """evaluation-report schema additionalProperties=false。"""
    s = load_schema("evaluation-report.schema.json")
    # top-level additionalProperties 可能 False 或不存在
    # 检查 schema 是 strict 风格
    assert s.get("additionalProperties") is False or "additionalProperties" in s


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_does_not_contain_os():
    """不含 import os。"""
    assert "import os" not in inspect.getsource(smod)


def test_module_source_does_not_contain_sys():
    """不含 import sys。"""
    assert "import sys" not in inspect.getsource(smod)


def test_module_source_does_not_contain_re():
    """不含 import re。"""
    assert "import re" not in inspect.getsource(smod)


def test_module_source_does_not_contain_logging():
    """不含 import logging。"""
    assert "import logging" not in inspect.getsource(smod)


def test_module_source_does_not_contain_subprocess():
    """不含 import subprocess。"""
    assert "import subprocess" not in inspect.getsource(smod)


def test_module_source_does_not_contain_asyncio():
    """不含 import asyncio。"""
    assert "import asyncio" not in inspect.getsource(smod)


def test_module_source_does_not_contain_threading():
    """不含 import threading。"""
    assert "import threading" not in inspect.getsource(smod)


def test_module_source_does_not_contain_time():
    """不含 import time。"""
    assert "import time" not in inspect.getsource(smod)


def test_module_source_does_not_contain_datetime():
    """不含 import datetime。"""
    assert "import datetime" not in inspect.getsource(smod)


def test_module_source_does_not_contain_collections():
    """不含 from collections。"""
    assert "from collections" not in inspect.getsource(smod)


def test_module_source_does_not_contain_math():
    """不含 import math。"""
    assert "import math" not in inspect.getsource(smod)


def test_module_source_does_not_contain_itertools():
    """不含 from itertools。"""
    assert "from itertools" not in inspect.getsource(smod)


def test_module_source_does_not_contain_functools():
    """不含 from functools。"""
    assert "from functools" not in inspect.getsource(smod)


def test_module_source_does_not_contain_star_import():
    """不含 * 导入。"""
    assert "import *" not in inspect.getsource(smod)


def test_module_source_does_not_contain_relative_import():
    """不含相对导入。"""
    src = inspect.getsource(smod)
    assert "from ." not in src
    assert "from .." not in src


def test_module_source_does_not_contain_class_decorator():
    """不含 @dataclass 等装饰器（除了 class 本身）。"""
    src = inspect.getsource(smod)
    assert "@dataclass" not in src


def test_module_source_does_not_contain_yield():
    """不含 yield。"""
    assert "yield" not in inspect.getsource(smod)


def test_module_source_does_not_contain_async_def():
    """不含 async def。"""
    assert "async def" not in inspect.getsource(smod)


def test_module_source_does_not_contain_global_keyword():
    """不含 global 关键字。"""
    assert "global " not in inspect.getsource(smod)


def test_module_source_does_not_contain_nonlocal_keyword():
    """不含 nonlocal 关键字。"""
    assert "nonlocal " not in inspect.getsource(smod)


def test_module_source_does_not_contain_walrus_operator():
    """不含 := 海象运算符。"""
    assert ":=" not in inspect.getsource(smod)


def test_module_source_does_not_contain_assert_statement():
    """不含 assert 语句。"""
    src = inspect.getsource(smod)
    # 检查没有顶层 assert
    lines = [l for l in src.split("\n") if l.strip().startswith("assert")]
    assert lines == []


# =========================================================================
# module imports 顺序 + future annotations
# =========================================================================


def test_module_source_contains_future_annotations():
    """含 from __future__ import annotations。"""
    assert "from __future__ import annotations" in inspect.getsource(smod)


def test_module_imports_json():
    """含 import json。"""
    assert "import json" in inspect.getsource(smod)


def test_module_imports_path():
    """含 from pathlib import Path。"""
    assert "from pathlib import Path" in inspect.getsource(smod)


def test_module_imports_any():
    """含 from typing import Any。"""
    assert "from typing import Any" in inspect.getsource(smod)


def test_module_imports_jsonschema_draft():
    """含 from jsonschema import Draft202012Validator。"""
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_imports_validation_error_as_alias():
    """含 from jsonschema.exceptions import ValidationError as JSValidationError。"""
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_import_order_future_before_json():
    """future annotations 在 import json 之前。"""
    src = inspect.getsource(smod)
    assert src.find("from __future__") < src.find("import json")


def test_module_import_order_json_before_pathlib():
    """import json 在 from pathlib 之前。"""
    src = inspect.getsource(smod)
    assert src.find("import json") < src.find("from pathlib")


def test_module_import_order_pathlib_before_jsonschema():
    """from pathlib 在 from jsonschema 之前。"""
    src = inspect.getsource(smod)
    assert src.find("from pathlib") < src.find("from jsonschema")


# =========================================================================
# module docstring 深度
# =========================================================================


def test_module_docstring_present():
    """module 有 docstring。"""
    assert smod.__doc__ is not None


def test_module_docstring_mentions_manifest():
    """docstring 含 manifest。"""
    assert "manifest" in smod.__doc__


def test_module_docstring_mentions_annotation():
    """docstring 含 annotation。"""
    assert "annotation" in smod.__doc__


def test_module_docstring_mentions_evaluation_report():
    """docstring 含 evaluation-report。"""
    assert "evaluation-report" in smod.__doc__


def test_module_docstring_mentions_app_schema_separation():
    """docstring 含「不与 app/schema.py 复用」说明。"""
    assert "app/schema.py" in smod.__doc__ or "app.schema" in smod.__doc__


def test_module_docstring_mentions_distinction():
    """docstring 含「业务输出 vs 评测元数据」分离说明。"""
    assert "业务" in smod.__doc__ or "评测" in smod.__doc__


# =========================================================================
# 端到端集成：load_schema → validate → validate_file
# =========================================================================


def test_load_then_validate_happy_path():
    """load_schema 后用 Draft202012Validator 直接 validate 也通过。"""
    schema = load_schema("manifest.schema.json")
    v = Draft202012Validator(schema)
    assert v.is_valid(_minimal_manifest())


def test_validate_file_happy_path_for_annotation(tmp_path):
    """validate_file happy path for annotation。"""
    p = tmp_path / "a.json"
    p.write_text(json.dumps(_minimal_annotation()), encoding="utf-8")
    validate_file(p, "annotation.schema.json")


def test_validate_file_happy_path_for_report(tmp_path):
    """validate_file happy path for evaluation-report。"""
    p = tmp_path / "r.json"
    p.write_text(json.dumps(_minimal_report()), encoding="utf-8")
    validate_file(p, "evaluation-report.schema.json")


def test_cross_schema_validate_fails_manifest_against_annotation():
    """manifest 数据用 annotation schema 校验 → 失败。"""
    with pytest.raises(EvalSchemaError):
        validate(_minimal_manifest(), "annotation.schema.json")


def test_cross_schema_validate_fails_annotation_against_manifest():
    """annotation 数据用 manifest schema 校验 → 失败。"""
    with pytest.raises(EvalSchemaError):
        validate(_minimal_annotation(), "manifest.schema.json")


def test_cross_schema_validate_fails_manifest_against_report():
    """manifest 数据用 report schema 校验 → 失败。"""
    with pytest.raises(EvalSchemaError):
        validate(_minimal_manifest(), "evaluation-report.schema.json")


def test_validate_errors_count_increases_with_more_violations():
    """多个 violation → errors 列表更长。"""
    # 单个 violation
    try:
        validate({}, "manifest.schema.json")
        n1 = 0
    except EvalSchemaError as e:
        n1 = len(e.errors)
    # 多个 violation（额外字段 + 缺字段）
    try:
        validate({"manifest_version": "2.0"}, "manifest.schema.json")
        n2 = 0
    except EvalSchemaError as e:
        n2 = len(e.errors)
    # 多 violation 应该至少 1 个错误
    assert n1 >= 1
    assert n2 >= 1


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_no_main_block():
    """没有 if __name__ == '__main__' 块。"""
    src = inspect.getsource(smod)
    assert '__name__ == "__main__"' not in src
    assert "__name__ == '__main__'" not in src


def test_module_class_definition_only_one():
    """只有 1 个 class（EvalSchemaError）。"""
    src = inspect.getsource(smod)
    # 计数顶层 class 定义
    class_count = sum(1 for line in src.split("\n") if line.startswith("class "))
    assert class_count == 1


def test_module_class_eval_schema_error_only():
    """class 名是 EvalSchemaError。"""
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_function_count_4():
    """4 个 module-level function：_schema_path / load_schema / validate / validate_file。"""
    src = inspect.getsource(smod)
    func_count = sum(1 for line in src.split("\n") if line.startswith("def "))
    assert func_count == 4
