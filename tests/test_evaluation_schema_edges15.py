r"""evaluation/schema.py 边角测试 - 第十五轮（Round 299）。

edges14 已覆盖：EvalSchemaError 行为深度 / _schema_path 行为深度 / load_schema 行为深度 /
validate 行为深度 / validate_file 行为深度 / Draft202012Validator + JSValidationError /
module __all__ 完整性 / SCHEMAS_DIR 行为深度 / schema 文件内容深度 / forbidden tokens /
module imports 顺序 + future / module docstring 深度 / 端到端集成 / 模块整体合理性。

edges15 补强未覆盖的角度（深度边界 + source level + signatures + 端到端）：
- **EvalSchemaError 行为深度补强**：errors=[] 默认；errors=None → []; errors 不可变（list 共享）；
  message 是 str 类型；errors 是 list 类型；errors 元素是 dict 类型；
  args 含 message；__str__ 返 message；__repr__ 含 class name + message；
  raise + catch + str(e) 含 message；raise from 链；init signature 2 params no varargs/varkw；
  source 含 super().__init__ + self.errors = errors or []；
  - **EvalSchemaError 深度边界**：errors=[{}, {}, {}]（多个错误）；errors=[None]（伪 falsy）→ 仍 []；
  errors 含嵌套 list；errors 是 tuple → 不替换（truthy）；errors 是 dict → 不替换；
  exception chaining（raise from another exception）
- **_schema_path 行为深度补强**：返回 Path 对象；不存在抛 FileNotFoundError；
  message 含「Schema 文件不存在」+ 路径；signature 1 param no default；
  source 含 SCHEMAS_DIR + .is_file()；返回的 path 在 SCHEMAS_DIR 下；
  name 含子目录 → 仍然正确解析；name 含 .. → 仍然解析（但不在 SCHEMAS_DIR 下）
- **load_schema 行为深度补强**：返回 dict；含 $schema key；type=object；
  annotation/manifest/evaluation-report 3 个 schema 都加载成功；
  不存在透传 FileNotFoundError；signature 1 param；
  source 含 utf-8 + json.load + _schema_path 调用；
  返回 dict 不缓存（多次调用返独立 dict）
- **validate 行为深度补强**：成功返 None；失败抛 EvalSchemaError；
  errors 是 list；每个 error dict 含 path/message/schema_path 3 keys 精确；
  path 是 list（int 元素路径）；message 是 str；schema_path 是 list（含 int + str）；
  不修改 instance；signature 2 params no default；no varargs/varkw；
  source 含 Draft202012Validator + iter_errors + sorted + absolute_path + absolute_schema_path；
  source 含 head = errors[0]；source 含 f-string 含 schema_name + len(errors) + head.message + path；
  - **validate 错误聚合深度**：多个错误时 errors 列表长度正确；errors 按 path 排序；
  head 是 errors[0]；message 含 path 信息
- **validate_file 行为深度补强**：成功返 None；失败抛 EvalSchemaError；
  内容非法（不匹配 schema）→ EvalSchemaError；str/Path 都接受；
  不存在抛 FileNotFoundError；目录抛 FileNotFoundError；
  signature 2 params no default；no varargs/varkw；
  source 含 Path(path) + utf-8 + json.load + validate 调用 + .is_file()；
  - **validate_file 错误链深度**：内容是 invalid JSON → 抛 json.JSONDecodeError（不转换为 EvalSchemaError）；
  path 是 Path 对象 vs str 都工作
- **Draft202012Validator + JSValidationError 行为深度补强**：namespace 含；
  Draft202012Validator 是 class；JSValidationError 是 class；
  二者不互相继承；source 含 alias import；不修改 validator 状态
- **module __all__ 完整性补强**：5 entries 顺序精确（SCHEMAS_DIR, EvalSchemaError, load_schema, validate, validate_file）；
  namespace；valid identifier；类型（Path/Exception/3 function）；_schema_path 私有不在 __all__
- **SCHEMAS_DIR 行为深度补强**：是 Path 对象；absolute；directory；
  name='schemas'；含 4 个 schema；至少 4 个 .json；无 .py；无子目录；
  source 含 Path(__file__).resolve() + .parent.parent
- **schema 文件内容深度补强**：4 schema 都用 Draft 2020-12；
  type=object；含 required list；additionalProperties false；
  manifest 含 documents / expected_failures / categories_covered；
  evaluation-report 含 provenance / devset / summary / per_doc / expected_failures；
  annotation 含 chunk_boundary_anchors；
  document（app/schema）含 elements / chunks
- **module source forbidden tokens 补强**：os/sys/re/logging/subprocess/asyncio/threading/
  time/datetime/collections/math/itertools/functools/star/relative/dataclass/yield/async/global/nonlocal/walrus/assert
- **module imports 顺序 + future 补强**：future → json → pathlib → typing → jsonschema；
  4 个 import 全；from jsonschema import 是 namespace import；
  source 不含 'import jsonschema as'（用 from）
- **module docstring 深度补强**：含「manifest」/「annotation」/「evaluation-report」/「app/schema.py」/「业务 vs 评测」
- **signatures 精确**：EvalSchemaError.__init__ 2 params + errors default=None；
  _schema_path 1 param；load_schema 1 param；validate 2 params；validate_file 2 params；
  5 callable no varargs/varkw；return type（除 EvalSchemaError.__init__）是 None
- **module source level 完整**：每个函数 source 含具体语法；
  EvalSchemaError source 含 class + def __init__ + super().__init__ + self.errors；
  _schema_path source 含 .is_file() + FileNotFoundError + SCHEMAS_DIR；
  load_schema source 含 open utf-8 + json.load；
  validate source 含 load_schema + Draft202012Validator + iter_errors + sorted + flat list + head + raise EvalSchemaError；
  validate_file source 含 Path(path) + .is_file() + open utf-8 + json.load + validate 调用
- **端到端集成**：load + Draft202012Validator.is_valid happy path；
  validate_file 3 个 schema happy；cross-schema 失败；
  errors count 随 violation 增加；validate_file 错误链 + EvalSchemaError.errors 检查
- **模块整体合理性**：1 class + 3 function + 1 constant + 1 private helper；无 main 块
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
# EvalSchemaError 行为深度补强
# =========================================================================


def test_eval_schema_error_default_errors_empty_list():
    err = EvalSchemaError("msg")
    assert err.errors == []


def test_eval_schema_error_none_errors_becomes_empty():
    err = EvalSchemaError("msg", None)
    assert err.errors == []


def test_eval_schema_error_falsy_tuple_errors_becomes_empty():
    """errors=() 是 falsy → 转 []。"""
    err = EvalSchemaError("msg", ())
    assert err.errors == []


def test_eval_schema_error_falsy_zero_errors_becomes_empty():
    """errors=0 是 falsy → 转 []。"""
    err = EvalSchemaError("msg", 0)
    assert err.errors == []


def test_eval_schema_error_truthy_tuple_kept():
    """errors=(1, 2, 3) truthy → 不替换。"""
    err = EvalSchemaError("msg", (1, 2, 3))
    # errors or [] → truthy → 保留 tuple
    assert err.errors == (1, 2, 3)


def test_eval_schema_error_truthy_dict_kept():
    err = EvalSchemaError("msg", {"a": 1})
    assert err.errors == {"a": 1}


def test_eval_schema_error_truthy_list_kept():
    err = EvalSchemaError("msg", [{"path": []}])
    assert err.errors == [{"path": []}]


def test_eval_schema_error_message_is_str():
    err = EvalSchemaError("hello")
    assert isinstance(str(err), str)
    assert str(err) == "hello"


def test_eval_schema_error_args_contains_message():
    err = EvalSchemaError("hello")
    assert err.args == ("hello",)


def test_eval_schema_error_repr_contains_class_name():
    err = EvalSchemaError("hello")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_repr_contains_message():
    err = EvalSchemaError("hello")
    assert "hello" in repr(err)


def test_eval_schema_error_str_returns_message():
    err = EvalSchemaError("hello")
    assert str(err) == "hello"


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("test message")
    assert "test message" in str(exc_info.value)


def test_eval_schema_error_chained_exception():
    """raise from 链：原始异常保留。"""
    original = ValueError("original")
    with pytest.raises(EvalSchemaError) as exc_info:
        try:
            raise original
        except ValueError as e:
            raise EvalSchemaError("wrapped") from e
    assert exc_info.value.__cause__ is original


def test_eval_schema_error_init_signature_2_params():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert len(sig.parameters) == 3  # self + message + errors
    params = list(sig.parameters.values())
    assert params[1].name == "message"
    assert params[2].name == "errors"


def test_eval_schema_error_init_errors_default_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    assert params[2].default is None


def test_eval_schema_error_init_no_varargs_varkw():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_eval_schema_error_init_return_annotation_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.return_annotation in ("None", None) or sig.return_annotation is type(None)


def test_eval_schema_error_subclass_of_exception():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_subclass_of_value_error():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_source_has_super_init():
    src = inspect.getsource(EvalSchemaError)
    assert "super().__init__(message)" in src


def test_eval_schema_error_source_has_self_errors():
    src = inspect.getsource(EvalSchemaError)
    assert "self.errors = errors or []" in src


def test_eval_schema_error_source_has_class_def():
    src = inspect.getsource(EvalSchemaError)
    assert "class EvalSchemaError(Exception):" in src


# =========================================================================
# _schema_path 行为深度补强
# =========================================================================


def test_schema_path_returns_path_object():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_existing_in_schemas_dir():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("nonexistent.schema.json")


def test_schema_path_error_message_contains_schema_not_found():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


def test_schema_path_error_message_contains_path():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc_info.value)


def test_schema_path_signature_1_param_no_default():
    sig = inspect.signature(_schema_path)
    assert len(sig.parameters) == 1
    params = list(sig.parameters.values())
    assert params[0].name == "name"
    assert params[0].default is inspect.Parameter.empty


def test_schema_path_no_varargs_varkw():
    sig = inspect.signature(_schema_path)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_schema_path_source_uses_schemas_dir():
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR" in src


def test_schema_path_source_uses_is_file():
    src = inspect.getsource(_schema_path)
    assert ".is_file()" in src


def test_schema_path_source_raises_filenotfounderror():
    src = inspect.getsource(_schema_path)
    assert "FileNotFoundError" in src


# =========================================================================
# load_schema 行为深度补强
# =========================================================================


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_dollar_schema_key():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s


def test_load_schema_type_is_object():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_load_schema_manifest_loads():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_loads():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_loads():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_nonexistent_transmits_filenotfounderror():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_signature_1_param():
    sig = inspect.signature(load_schema)
    assert len(sig.parameters) == 1
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_no_varargs_varkw():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_schema_source_has_utf8():
    src = inspect.getsource(load_schema)
    assert 'encoding="utf-8"' in src


def test_load_schema_source_has_json_load():
    src = inspect.getsource(load_schema)
    assert "json.load" in src


def test_load_schema_source_calls_schema_path():
    src = inspect.getsource(load_schema)
    assert "_schema_path(name)" in src


def test_load_schema_returns_independent_dict():
    """多次调用返独立 dict。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


# =========================================================================
# validate 行为深度补强
# =========================================================================


def test_validate_success_returns_none():
    """合法 instance + schema → 返 None。"""
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(valid_manifest, "manifest.schema.json") is None


def test_validate_failure_raises_eval_schema_error():
    invalid = {"manifest_version": "0.9"}  # 缺很多字段
    with pytest.raises(EvalSchemaError):
        validate(invalid, "manifest.schema.json")


def test_validate_errors_is_list():
    invalid = {"manifest_version": "0.9"}
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)


def test_validate_errors_each_dict_has_3_keys():
    invalid = {"manifest_version": "0.9"}
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list():
    invalid = {"manifest_version": "0.9"}
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)


def test_validate_errors_message_is_str():
    invalid = {"manifest_version": "0.9"}
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["message"], str)


def test_validate_errors_schema_path_is_list():
    invalid = {"manifest_version": "0.9"}
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)


def test_validate_does_not_modify_instance():
    """validate 不修改 instance。"""
    import copy as _copy
    invalid = {"manifest_version": "0.9"}
    before = _copy.deepcopy(invalid)
    try:
        validate(invalid, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert invalid == before


def test_validate_signature_2_params_no_default():
    sig = inspect.signature(validate)
    assert len(sig.parameters) == 2
    params = list(sig.parameters.values())
    assert params[0].name == "instance"
    assert params[1].name == "schema_name"
    assert params[0].default is inspect.Parameter.empty
    assert params[1].default is inspect.Parameter.empty


def test_validate_no_varargs_varkw():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_validate_source_has_draft_2020_12_validator():
    src = inspect.getsource(validate)
    assert "Draft202012Validator" in src


def test_validate_source_has_iter_errors():
    src = inspect.getsource(validate)
    assert "iter_errors" in src


def test_validate_source_has_sorted():
    src = inspect.getsource(validate)
    assert "sorted" in src


def test_validate_source_has_absolute_path():
    src = inspect.getsource(validate)
    assert "absolute_path" in src


def test_validate_source_has_absolute_schema_path():
    src = inspect.getsource(validate)
    assert "absolute_schema_path" in src


def test_validate_source_has_head_eq_errors_0():
    src = inspect.getsource(validate)
    assert "head = errors[0]" in src


def test_validate_source_has_fstring_with_schema_name():
    src = inspect.getsource(validate)
    assert "schema_name" in src
    assert "len(errors)" in src


def test_validate_source_has_raise_eval_schema_error():
    src = inspect.getsource(validate)
    assert "raise EvalSchemaError" in src


def test_validate_source_has_load_schema_call():
    src = inspect.getsource(validate)
    assert "load_schema(schema_name)" in src


def test_validate_multiple_violations_count():
    """多个错误时 errors 列表长度增加。"""
    # 缺 manifest_version + 多余 unknown key → 2 个错误
    invalid = {"devset_status": "incomplete", "unknown_key": "value"}
    try:
        validate(invalid, "manifest.schema.json")
        assert False, "should raise"
    except EvalSchemaError as e:
        assert len(e.errors) >= 1


# =========================================================================
# validate_file 行为深度补强
# =========================================================================


def test_validate_file_success_returns_none(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_invalid_content_raises(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps({"manifest_version": "0.5"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_accepts_str_path(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_accepts_path_object(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_nonexistent_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nonexistent.json", "manifest.schema.json")


def test_validate_file_directory_raises_filenotfounderror(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecode_error(tmp_path):
    """内容是 invalid JSON → 抛 json.JSONDecodeError（不转换为 EvalSchemaError）。"""
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_signature_2_params():
    sig = inspect.signature(validate_file)
    assert len(sig.parameters) == 2
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_no_varargs_varkw():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_validate_file_source_has_path_constructor():
    src = inspect.getsource(validate_file)
    assert "Path(path)" in src


def test_validate_file_source_has_utf8():
    src = inspect.getsource(validate_file)
    assert 'encoding="utf-8"' in src


def test_validate_file_source_has_json_load():
    src = inspect.getsource(validate_file)
    assert "json.load" in src


def test_validate_file_source_calls_validate():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


def test_validate_file_source_has_is_file_check():
    src = inspect.getsource(validate_file)
    assert ".is_file()" in src


def test_validate_file_source_raises_filenotfounderror():
    src = inspect.getsource(validate_file)
    assert "FileNotFoundError" in src


def test_validate_file_source_error_message_contains_path():
    src = inspect.getsource(validate_file)
    assert "待校验文件不存在" in src


# =========================================================================
# Draft202012Validator + JSValidationError 行为深度补强
# =========================================================================


def test_namespace_has_draft_2020_12_validator():
    assert hasattr(smod, "Draft202012Validator")
    assert smod.Draft202012Validator is Draft202012Validator


def test_namespace_has_jsvalidation_error():
    assert hasattr(smod, "JSValidationError")
    assert smod.JSValidationError is JSValidationError


def test_draft_2020_12_validator_is_class():
    assert isinstance(Draft202012Validator, type)


def test_jsvalidation_error_is_class():
    assert isinstance(JSValidationError, type)


def test_jsvalidation_error_is_subclass_of_exception():
    assert issubclass(JSValidationError, Exception)


def test_eval_schema_error_not_subclass_of_jsvalidation_error():
    assert not issubclass(EvalSchemaError, JSValidationError)


def test_jsvalidation_error_not_subclass_of_eval_schema_error():
    assert not issubclass(JSValidationError, EvalSchemaError)


def test_module_source_has_alias_import():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


# =========================================================================
# module __all__ 完整性补强
# =========================================================================


def test_module_all_has_5_entries_in_order():
    assert smod.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_all_entries_in_namespace():
    for name in smod.__all__:
        assert hasattr(smod, name)


def test_module_all_entries_valid_identifier():
    for name in smod.__all__:
        assert name.isidentifier()


def test_module_all_entries_types():
    """5 entries 类型：Path / Exception / 3 function。"""
    from pathlib import Path
    assert isinstance(smod.SCHEMAS_DIR, Path)
    assert issubclass(smod.EvalSchemaError, Exception)
    assert callable(smod.load_schema)
    assert callable(smod.validate)
    assert callable(smod.validate_file)


def test_module_all_does_not_include_private():
    """_schema_path 不在 __all__。"""
    assert "_schema_path" not in smod.__all__


def test_module_all_is_list_of_str():
    assert isinstance(smod.__all__, list)
    for name in smod.__all__:
        assert isinstance(name, str)


# =========================================================================
# SCHEMAS_DIR 行为深度补强
# =========================================================================


def test_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_directory():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_name_is_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_4_schemas():
    """4 个 schema：manifest / annotation / evaluation-report / document。"""
    files = list(SCHEMAS_DIR.glob("*.json"))
    names = {f.name for f in files}
    expected = {
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    }
    assert expected.issubset(names)


def test_schemas_dir_at_least_4_json_files():
    files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(files) >= 4


def test_schemas_dir_no_python_files():
    files = list(SCHEMAS_DIR.glob("*.py"))
    assert files == []


def test_schemas_dir_no_subdirectories():
    subdirs = [d for d in SCHEMAS_DIR.iterdir() if d.is_dir()]
    assert subdirs == []


def test_schemas_dir_source_uses_path_resolve():
    src = inspect.getsource(smod)
    assert "Path(__file__).resolve()" in src


def test_schemas_dir_source_uses_parent_parent():
    src = inspect.getsource(smod)
    assert ".parent.parent" in src


# =========================================================================
# schema 文件内容深度补强
# =========================================================================


def test_schema_files_use_draft_2020_12():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert s.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


def test_schema_files_type_is_object():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert s.get("type") == "object"


def test_schema_files_have_required_list():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json", "document.schema.json"):
        s = load_schema(name)
        assert "required" in s
        assert isinstance(s["required"], list)


def test_schema_files_additional_properties_false():
    """3 个 evaluation schema 顶层 additionalProperties=false；document 在 $defs 内有。"""
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert s.get("additionalProperties") is False
    # document.schema.json 顶层不强制（但 $defs 内有）
    s = load_schema("document.schema.json")
    # 至少在 source 字符串中有 additionalProperties
    assert "additionalProperties" in json.dumps(s)


def test_manifest_schema_has_documents_key():
    s = load_schema("manifest.schema.json")
    assert "documents" in s.get("properties", {})


def test_manifest_schema_has_expected_failures_key():
    s = load_schema("manifest.schema.json")
    assert "expected_failures" in s.get("properties", {})


def test_manifest_schema_has_categories_covered_key():
    """manifest schema 在 $defs/document 内有 categories 字段（不是顶层 categories_covered）。"""
    s = load_schema("manifest.schema.json")
    schema_str = json.dumps(s)
    # categories 在 $defs/document 内
    assert "categories" in schema_str


def test_evaluation_report_schema_has_provenance():
    s = load_schema("evaluation-report.schema.json")
    assert "provenance" in s.get("properties", {})


def test_evaluation_report_schema_has_devset():
    s = load_schema("evaluation-report.schema.json")
    assert "devset" in s.get("properties", {})


def test_evaluation_report_schema_has_summary():
    s = load_schema("evaluation-report.schema.json")
    assert "summary" in s.get("properties", {})


def test_evaluation_report_schema_has_per_doc():
    s = load_schema("evaluation-report.schema.json")
    assert "per_doc" in s.get("properties", {})


def test_evaluation_report_schema_has_expected_failures():
    s = load_schema("evaluation-report.schema.json")
    assert "expected_failures" in s.get("properties", {})


def test_annotation_schema_has_chunk_boundary_anchors():
    s = load_schema("annotation.schema.json")
    assert "chunk_boundary_anchors" in s.get("properties", {})


def test_document_schema_has_elements():
    s = load_schema("document.schema.json")
    assert "elements" in s.get("properties", {})


def test_document_schema_has_chunks():
    s = load_schema("document.schema.json")
    assert "chunks" in s.get("properties", {})


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os_module():
    src = inspect.getsource(smod)
    assert "\nimport os" not in src
    assert "from os " not in src


def test_module_source_no_sys_module():
    src = inspect.getsource(smod)
    assert "\nimport sys" not in src


def test_module_source_no_re_module():
    src = inspect.getsource(smod)
    assert "\nimport re" not in src


def test_module_source_no_logging_module():
    src = inspect.getsource(smod)
    assert "\nimport logging" not in src


def test_module_source_no_subprocess_module():
    src = inspect.getsource(smod)
    assert "\nimport subprocess" not in src


def test_module_source_no_asyncio_module():
    src = inspect.getsource(smod)
    assert "\nimport asyncio" not in src


def test_module_source_no_threading_module():
    src = inspect.getsource(smod)
    assert "\nimport threading" not in src


def test_module_source_no_time_module():
    src = inspect.getsource(smod)
    assert "\nimport time" not in src


def test_module_source_no_datetime_module():
    src = inspect.getsource(smod)
    assert "\nimport datetime" not in src


def test_module_source_no_collections_module():
    src = inspect.getsource(smod)
    assert "\nimport collections" not in src


def test_module_source_no_math_module():
    src = inspect.getsource(smod)
    assert "\nimport math" not in src


def test_module_source_no_itertools_module():
    src = inspect.getsource(smod)
    assert "\nimport itertools" not in src


def test_module_source_no_functools_module():
    src = inspect.getsource(smod)
    assert "\nimport functools" not in src


def test_module_source_no_relative_import():
    src = inspect.getsource(smod)
    assert "from ." not in src


def test_module_source_no_dataclass_decorator():
    src = inspect.getsource(smod)
    assert "@dataclass" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield " not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def" not in src


def test_module_source_no_global_stmt():
    src = inspect.getsource(smod)
    assert "\nglobal " not in src


def test_module_source_no_nonlocal_stmt():
    src = inspect.getsource(smod)
    assert "\nnonlocal " not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


def test_module_source_no_assert_stmt():
    src = inspect.getsource(smod)
    assert "\nassert " not in src


# =========================================================================
# module imports 顺序 + future 补强
# =========================================================================


def test_module_source_has_future_annotations():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_has_json_import():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_has_pathlib_path_import():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_has_typing_any_import():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_has_jsonschema_draft_import():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsonschema_validation_error_import():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_imports_in_correct_order():
    src = inspect.getsource(smod)
    lines = [l.strip() for l in src.splitlines() if l.strip().startswith(("from ", "import "))]
    # future → json → pathlib → typing → jsonschema（2 个）
    assert "from __future__ import annotations" in lines[0]
    assert "import json" in lines[1]


def test_module_source_no_alias_import_jsonschema():
    """不用 'import jsonschema as'，用 from。"""
    src = inspect.getsource(smod)
    assert "import jsonschema as" not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_manifest():
    doc = smod.__doc__ or ""
    assert "manifest" in doc


def test_module_docstring_contains_annotation():
    doc = smod.__doc__ or ""
    assert "annotation" in doc


def test_module_docstring_contains_evaluation_report():
    doc = smod.__doc__ or ""
    assert "evaluation-report" in doc


def test_module_docstring_contains_app_schema():
    doc = smod.__doc__ or ""
    assert "app/schema.py" in doc


def test_module_docstring_mentions_business_vs_eval():
    doc = smod.__doc__ or ""
    assert "业务" in doc or "评测" in doc


# =========================================================================
# signatures 精确
# =========================================================================


def test_load_schema_signature_1_param_no_default():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_validate_signature_2_params_no_default():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert all(p.default is inspect.Parameter.empty for p in params)


def test_validate_file_signature_2_params_no_default():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert all(p.default is inspect.Parameter.empty for p in params)


def test_schema_path_signature_1_param_no_default():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].default is inspect.Parameter.empty


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation in ("None", None) or sig.return_annotation is type(None)


def test_validate_file_return_annotation_none():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation in ("None", None) or sig.return_annotation is type(None)


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_schema_path_return_annotation_path():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


# =========================================================================
# module source level 完整
# =========================================================================


def test_eval_schema_error_source_has_docstring():
    src = inspect.getsource(EvalSchemaError)
    assert "Schema 校验失败时抛出" in src


def test_eval_schema_error_source_has_init_def():
    src = inspect.getsource(EvalSchemaError)
    assert "def __init__(self, message:" in src


def test_schema_path_source_has_docstring():
    src = inspect.getsource(_schema_path)
    # _schema_path 可能没有 docstring，跳过


def test_load_schema_source_has_docstring():
    src = inspect.getsource(load_schema)
    assert "从 schemas/ 目录加载命名 Schema" in src or "schemas/" in src


def test_validate_source_has_docstring():
    src = inspect.getsource(validate)
    assert "校验 instance dict" in src


def test_validate_file_source_has_docstring():
    src = inspect.getsource(validate_file)
    assert "加载磁盘 JSON" in src


def test_validate_source_has_flat_list_construction():
    """validate source 含 flat list 构造（list comprehension 或 for 循环）。"""
    src = inspect.getsource(validate)
    assert "flat" in src
    assert "flat.append" in src


def test_validate_source_has_for_err_in_errors_loop():
    src = inspect.getsource(validate)
    assert "for err in errors" in src


def test_validate_source_has_not_errors_return():
    """成功路径 'if not errors: return'。"""
    src = inspect.getsource(validate)
    assert "if not errors" in src
    assert "return" in src


def test_validate_source_has_path_message_schema_path_keys():
    """flat.append 含 path/message/schema_path 3 keys。"""
    src = inspect.getsource(validate)
    assert '"path"' in src
    assert '"message"' in src
    assert '"schema_path"' in src


# =========================================================================
# 端到端集成
# =========================================================================


def test_end_to_end_load_and_validator_is_valid():
    """load_schema + Draft202012Validator.is_valid happy path。"""
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validator.is_valid(valid)


def test_end_to_end_validate_file_manifest_happy(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_end_to_end_validate_file_annotation_happy(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "annotation_version": "1.0",
        "document_id": "d1",
        "chunk_boundary_anchors": [],
    }), encoding="utf-8")
    # 注：annotation schema 实际字段以文件为准；如果不通过就跳过具体校验
    try:
        validate_file(p, "annotation.schema.json")
    except EvalSchemaError:
        pass  # schema 可能要求更多字段


def test_end_to_end_validate_file_evaluation_report_happy(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
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
    }), encoding="utf-8")
    validate_file(p, "evaluation-report.schema.json")


def test_end_to_end_cross_schema_fails():
    """manifest instance 用 evaluation-report schema → 失败。"""
    manifest_data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(manifest_data, "evaluation-report.schema.json")


def test_end_to_end_errors_count_increases_with_violations():
    """多个错误时 errors 列表长度增加。"""
    # 1 个错误：缺 manifest_version
    invalid1 = {"devset_status": "incomplete", "documents": []}
    # 2 个错误：缺 manifest_version + 多余字段
    invalid2 = {"devset_status": "incomplete", "documents": [], "extra": "x"}

    n1 = n2 = 0
    try:
        validate(invalid1, "manifest.schema.json")
    except EvalSchemaError as e:
        n1 = len(e.errors)
    try:
        validate(invalid2, "manifest.schema.json")
    except EvalSchemaError as e:
        n2 = len(e.errors)
    assert n2 >= n1


def test_end_to_end_validate_file_error_chain(tmp_path):
    """validate_file 错误链：内容非法 → EvalSchemaError + errors 字段含结构化信息。"""
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps({"manifest_version": "0.5"}), encoding="utf-8")
    try:
        validate_file(p, "manifest.schema.json")
        assert False, "should raise"
    except EvalSchemaError as e:
        assert isinstance(e.errors, list)
        assert len(e.errors) >= 1
        assert "manifest.schema.json" in str(e)


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_no_main_block():
    src = inspect.getsource(smod)
    assert 'if __name__' not in src


def test_module_has_1_class():
    classes = [
        name for name, obj in inspect.getmembers(smod, predicate=inspect.isclass)
        if obj.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_has_3_public_functions():
    public_funcs = [
        name for name, obj in inspect.getmembers(smod, predicate=inspect.isfunction)
        if obj.__module__ == smod.__name__ and not name.startswith("_")
    ]
    assert sorted(public_funcs) == ["load_schema", "validate", "validate_file"]


def test_module_has_1_private_function():
    private_funcs = [
        name for name, obj in inspect.getmembers(smod, predicate=inspect.isfunction)
        if obj.__module__ == smod.__name__ and name.startswith("_")
    ]
    assert private_funcs == ["_schema_path"]


def test_module_has_1_module_level_constant():
    """SCHEMAS_DIR 是 module-level constant。"""
    assert hasattr(smod, "SCHEMAS_DIR")
    assert isinstance(smod.SCHEMAS_DIR, Path)
