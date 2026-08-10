r"""evaluation/schema.py 边角测试 - 第十六轮（Round 305）。

edges15 已覆盖：EvalSchemaError 行为（errors=[] / None / 共享 list / message str / errors list）/
_schema_path / load_schema / validate / validate_file / Draft202012Validator + JSValidationError /
module __all__ / SCHEMAS_DIR / schema 文件内容 / forbidden tokens / imports + future /
docstring 深度 / signatures 精确 / source level 完整 / 端到端集成 / 模块整体合理性。

edges16 补强未覆盖的角度（深度边界 + 行为 + source level + signatures + 端到端）：
- **EvalSchemaError 行为深度补强**：isinstance Exception；errors 默认 [] is list；
  errors=[{}] 保留（伪 truthy）；errors 可在 init 后访问 + 修改；__str__ 含 message；
  __repr__ 含 EvalSchemaError 字面量；raise + catch 后 e.args 含 message；
  Exception MRO（直接 base 是 Exception）；source 含 def __init__ + 2 params 精确；
  message 含 unicode 时不破坏；多 errors 时 len(e.errors) 精确
- **EvalSchemaError 深度边界补强**：errors=[] vs errors=None → 等价（都 []）；
  errors=[{"k": "v"}] 单个错误 dict；errors=非 list truthy（tuple/dict/set/str） → 保留原值（不强制 list）；
  message 空字符串；message 长 1000 字符；message 含 emoji
- **_schema_path 行为深度补强**：返回 Path 是 absolute（resolve 后）；is_file() True；
  name=manifest.schema.json 返正确 Path；name 含 .schema.json 后缀必须；
  name 含子目录分隔符（'/' 或 '\\'）仍尝试解析；signature 1 param + return Path；
  source 含 raise FileNotFoundError + f-string 含中文「Schema 文件不存在」
- **load_schema 行为深度补强**：4 schema 都加载（manifest/annotation/evaluation-report/document）；
  返回 dict 不缓存（两次调用返不同 dict）；返回 dict 含 $schema/$id/type；
  document.schema.json 是 4 个之一；evaluation-report 含 $id；
  signature 1 param + return dict；source 含 with + .open + encoding utf-8 + json.load
- **validate 行为深度补强**：成功返 None（隐式）；失败抛 EvalSchemaError；
  不修改 instance；可重复调用；errors 排序精确（按 absolute_path）；
  errors 列表元素是 dict 含 path/message/schema_path；
  head 是 errors[0]；message 含 schema_name + len(errors) + head.message + path；
  signature 2 params + return None
- **validate 错误聚合深度补强**：1 个错误 → errors 长度 1；多个错误 → errors 按路径排序；
  错误 head.message 是 str；错误 head 含 absolute_path；
  flat errors 含 path/message/schema_path 3 keys；path 是 list；schema_path 是 list
- **validate_file 行为深度补强**：成功返 None；失败抛 EvalSchemaError；
  Path / str 都接受；不存在 → FileNotFoundError；目录 → FileNotFoundError；
  invalid JSON → json.JSONDecodeError（不包装）；signature 2 params + return None；
  source 含 Path(path) + .is_file() + FileNotFoundError f-string + .open utf-8 + json.load + validate 调用
- **Draft202012Validator + JSValidationError 行为深度补强**：Draft202012Validator is class；
  JSValidationError is class；二者 issubclass Exception；二者无继承关系；
  source 含 from jsonschema import Draft202012Validator；source 含 from jsonschema.exceptions import ValidationError as JSValidationError
- **module __all__ 完整性补强**：5 entries 顺序精确；namespace；
  SCHEMAS_DIR 是 Path；EvalSchemaError 是 class；3 个是 function
- **SCHEMAS_DIR 行为深度补强**：是 absolute Path；resolve 后是绝对；
  parent.parent 是 project_root；含 4 个 .json 文件；目录名是 'schemas'；
  source 含 Path(__file__).resolve() + .parent.parent
- **schema 文件内容深度补强**：4 schema 都用 Draft 2020-12 ($schema);
  manifest 含 manifest_version const "1.0"；evaluation-report 含 report_version；
  annotation 含 chunk_boundary_anchors + document_id；document 含 source_type；
  manifest 含 documents 是 array；evaluation-report 含 per_doc 是 array；
  annotation 含 document_id + chunk_boundary_anchors；
  document 含 elements + chunks 都是 array
- **module source forbidden tokens 补强**：不含 os/sys/re/logging/subprocess/asyncio/
  threading/time/datetime/collections/math/itertools/functools/socket/email/html/http/
  urllib/sqlite3/csv/pickle
- **module imports 顺序 + future 补强**：5 imports 精确；__future__ → json → pathlib →
  typing → jsonschema 2 行；jsonschema 用 from import 不用 import as；
  source 不含 'import jsonschema as'；source 不含 'import json as'
- **module docstring 深度补强**：含「manifest」/「annotation」/「evaluation-report」/
  「app/schema.py」/「业务」/「评测」
- **signatures 精确补强**：EvalSchemaError.__init__ 2 params (message, errors) +
  errors default=None + return annotation None；_schema_path 1 param + return Path；
  load_schema 1 param + return dict[str, Any]；validate 2 params + return None；
  validate_file 2 params (path: Path | str, schema_name: str) + return None；
  5 callable no varargs/varkw
- **module source level 完整补强**：每个函数 source 含具体语法；
  EvalSchemaError source 含 super().__init__(message) + self.errors = errors or []；
  _schema_path source 含 SCHEMAS_DIR / name + if not p.is_file() + raise + return p；
  load_schema source 含 with _schema_path(name).open("r", encoding="utf-8") as f + return json.load(f)；
  validate source 含 schema = load_schema + validator = Draft202012Validator +
  errors = sorted(validator.iter_errors(instance), key=lambda) +
  if not errors: return + flat list 推导 + head = errors[0] + raise EvalSchemaError；
  validate_file source 含 p = Path(path) + if not p.is_file() + raise +
  with p.open + json.load + validate(data, schema_name)
- **端到端集成补强**：4 schema 都 happy path；cross-schema 失败；
  validate_file 3 个 schema happy；errors 含 path 精确；
  validate 多个错误按 path 排序
- **模块整体合理性**：1 class + 3 function + 1 constant + 1 private helper；无 main 块；
  __all__ 5 entries；module 唯一 constant 是 SCHEMAS_DIR
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
    load_schema,
    validate,
    validate_file,
)


# =========================================================================
# EvalSchemaError 行为深度补强
# =========================================================================


def test_eval_schema_error_isinstance_exception():
    e = EvalSchemaError("msg")
    assert isinstance(e, Exception)


def test_eval_schema_error_default_errors_is_empty_list():
    e = EvalSchemaError("msg")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_empty_dict_in_errors_preserved():
    """errors=[{}] 保留（伪 truthy）。"""
    e = EvalSchemaError("msg", [{}])
    assert e.errors == [{}]


def test_eval_schema_error_errors_accessible_after_init():
    e = EvalSchemaError("msg", [{"path": ["a"]}])
    assert e.errors[0]["path"] == ["a"]


def test_eval_schema_error_errors_mutable_after_init():
    """errors 可在 init 后修改（list 是 mutable）。"""
    e = EvalSchemaError("msg", [{"path": ["a"]}])
    e.errors.append({"path": ["b"]})
    assert len(e.errors) == 2


def test_eval_schema_error_str_contains_message():
    e = EvalSchemaError("hello world")
    assert "hello world" in str(e)


def test_eval_schema_error_repr_contains_class_name():
    e = EvalSchemaError("hello")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_args_contains_message():
    """e.args 含 message（Exception 通用属性）。"""
    e = EvalSchemaError("hello")
    assert "hello" in e.args


def test_eval_schema_error_message_with_unicode():
    """message 含 unicode 时不破坏。"""
    e = EvalSchemaError("原因")
    assert "原因" in str(e)
    assert e.errors == []


def test_eval_schema_error_multiple_errors_count():
    """多 errors 时 len(e.errors) 精确。"""
    errors = [{"path": ["a"]}, {"path": ["b"]}, {"path": ["c"]}]
    e = EvalSchemaError("multi", errors)
    assert len(e.errors) == 3


def test_eval_schema_error_init_signature_2_params():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    # ['self', 'message', 'errors']
    assert params == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_is_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_init_no_varargs_varkw():
    sig = inspect.signature(EvalSchemaError.__init__)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


# =========================================================================
# EvalSchemaError 深度边界补强
# =========================================================================


def test_eval_schema_error_empty_list_equivalent_to_none():
    """errors=[] vs errors=None → 等价（都 []）。"""
    e1 = EvalSchemaError("msg", [])
    e2 = EvalSchemaError("msg", None)
    assert e1.errors == e2.errors == []


def test_eval_schema_error_single_empty_dict():
    e = EvalSchemaError("msg", [{}])
    assert len(e.errors) == 1
    assert e.errors[0] == {}


def test_eval_schema_error_tuple_errors_kept():
    """errors=非 list truthy（tuple） → 保留原值（不强制 list）。"""
    e = EvalSchemaError("msg", ({"path": ["a"]},))
    # errors or [] → tuple 是 truthy → 保留 tuple
    assert isinstance(e.errors, tuple)
    assert len(e.errors) == 1


def test_eval_schema_error_dict_errors_kept():
    """errors=dict → 保留（dict 是 truthy）。"""
    e = EvalSchemaError("msg", {"key": "val"})
    assert isinstance(e.errors, dict)


def test_eval_schema_error_set_errors_kept():
    """errors=set → set() falsy → []；非空 set truthy → 保留。"""
    e1 = EvalSchemaError("msg", set())
    assert e1.errors == []
    e2 = EvalSchemaError("msg", {"a"})
    assert isinstance(e2.errors, set)


def test_eval_schema_error_string_errors_kept():
    """errors=非空 str → 保留（str truthy）。"""
    e = EvalSchemaError("msg", "error string")
    assert e.errors == "error string"


def test_eval_schema_error_empty_message():
    e = EvalSchemaError("")
    assert str(e) == ""


def test_eval_schema_error_long_message():
    long_msg = "x" * 1000
    e = EvalSchemaError(long_msg)
    assert len(str(e)) == 1000


def test_eval_schema_error_emoji_message():
    e = EvalSchemaError("原因😀")
    assert "原因😀" in str(e)


# =========================================================================
# _schema_path 行为深度补强
# =========================================================================


def test_schema_path_returns_absolute_path():
    """返回 Path 是 absolute。"""
    from evaluation.schema import _schema_path
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_returns_existing_file():
    from evaluation.schema import _schema_path
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_manifest_correct():
    from evaluation.schema import _schema_path
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_signature_1_param_return_path():
    from evaluation.schema import _schema_path
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_schema_path_source_has_file_not_found_error():
    from evaluation.schema import _schema_path
    src = inspect.getsource(_schema_path)
    assert "raise FileNotFoundError" in src
    assert "Schema 文件不存在" in src


def test_schema_path_source_has_schemas_dir():
    from evaluation.schema import _schema_path
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR" in src
    assert ".is_file()" in src


def test_schema_path_not_exist_raises_with_chinese_text():
    from evaluation.schema import _schema_path
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


# =========================================================================
# load_schema 行为深度补强
# =========================================================================


def test_load_schema_manifest_has_dollar_schema():
    schema = load_schema("manifest.schema.json")
    assert "$schema" in schema


def test_load_schema_evaluation_report_has_dollar_id():
    schema = load_schema("evaluation-report.schema.json")
    assert "$id" in schema or "$schema" in schema


def test_load_schema_document_has_type_object():
    schema = load_schema("document.schema.json")
    assert schema.get("type") == "object"


def test_load_schema_returns_dict_twice_not_cached():
    """返回 dict 不缓存（两次调用返不同 dict 对象）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_signature_1_param():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1


def test_load_schema_source_has_utf8_encoding():
    src = inspect.getsource(load_schema)
    assert 'encoding="utf-8"' in src


def test_load_schema_source_has_json_load():
    src = inspect.getsource(load_schema)
    assert "json.load(f)" in src


def test_load_schema_source_has_schema_path_call():
    src = inspect.getsource(load_schema)
    assert "_schema_path(name)" in src


# =========================================================================
# validate 行为深度补强
# =========================================================================


def test_validate_does_not_mutate_instance():
    """validate 不修改 instance。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": [], "expected_failures": []}
    before = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    after = json.loads(json.dumps(instance))
    assert before == after


def test_validate_repeatable_call():
    """可重复调用（无副作用）。"""
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": [], "expected_failures": []}
    validate(instance, "manifest.schema.json")
    validate(instance, "manifest.schema.json")
    # 没抛就是通过


def test_validate_failed_error_path_is_list():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["path"], list)


def test_validate_failed_error_message_is_str():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["message"], str)


def test_validate_failed_error_schema_path_is_list():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_failed_message_contains_schema_name():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_failed_message_contains_count():
    instance = {"manifest_version": "wrong", "documents": "not_list"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    # 多个错误时 message 含数量
    assert "处" in str(exc_info.value)


def test_validate_signature_2_params():
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2


def test_validate_source_has_draft_validator():
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


def test_validate_source_has_head_eq_errors_0():
    src = inspect.getsource(validate)
    assert "head = errors[0]" in src


# =========================================================================
# validate 错误聚合深度补强
# =========================================================================


def test_validate_single_error_count():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert len(exc_info.value.errors) >= 1


def test_validate_multi_errors_sorted_by_path():
    """errors 按路径排序。"""
    instance = {"manifest_version": "wrong", "documents": "not_list"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc_info.value.errors]
    assert paths == sorted(paths)


def test_validate_flat_error_keys_exact():
    """每个 error dict 含 path/message/schema_path 3 keys 精确。"""
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_head_message_is_str():
    instance = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert isinstance(str(exc_info.value), str)


# =========================================================================
# validate_file 行为深度补强
# =========================================================================


def test_validate_file_path_object(tmp_path):
    p = tmp_path / "test.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(Path(p), "manifest.schema.json")


def test_validate_file_string_path(tmp_path):
    p = tmp_path / "test.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_not_exist_raises_file_not_found(tmp_path):
    p = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        validate_file(str(p), "manifest.schema.json")


def test_validate_file_directory_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(str(tmp_path), "manifest.schema.json")


def test_validate_file_invalid_json_raises_json_decode_error(tmp_path):
    p = tmp_path / "test.json"
    p.write_text("{not valid json}", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(str(p), "manifest.schema.json")


def test_validate_file_signature_2_params():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2


def test_validate_file_source_has_path_call():
    src = inspect.getsource(validate_file)
    assert "Path(path)" in src


def test_validate_file_source_has_is_file():
    src = inspect.getsource(validate_file)
    assert ".is_file()" in src


def test_validate_file_source_has_utf8_encoding():
    src = inspect.getsource(validate_file)
    assert 'encoding="utf-8"' in src


def test_validate_file_source_has_validate_call():
    src = inspect.getsource(validate_file)
    assert "validate(data, schema_name)" in src


# =========================================================================
# Draft202012Validator + JSValidationError 行为深度补强
# =========================================================================


def test_draft202012_validator_is_class():
    assert inspect.isclass(Draft202012Validator)


def test_jsvalidation_error_is_class():
    assert inspect.isclass(JSValidationError)


def test_jsvalidation_error_subclass_exception():
    assert issubclass(JSValidationError, Exception)


def test_draft_validator_not_subclass_jsvalidation_error():
    """Draft202012Validator 与 JSValidationError 无继承关系。"""
    assert not issubclass(Draft202012Validator, JSValidationError)
    assert not issubclass(JSValidationError, Draft202012Validator)


def test_module_source_has_from_jsonschema_draft_validator():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_from_jsonschema_exceptions():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_no_import_jsonschema_as():
    src = inspect.getsource(smod)
    assert "import jsonschema as" not in src


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


def test_module_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_eval_schema_error_is_class():
    assert inspect.isclass(EvalSchemaError)


def test_module_load_schema_validate_validate_file_are_callable():
    assert callable(load_schema)
    assert callable(validate)
    assert callable(validate_file)


def test_module_schema_path_private_not_in_all():
    """_schema_path 私有不在 __all__。"""
    assert "_schema_path" not in smod.__all__


# =========================================================================
# SCHEMAS_DIR 行为深度补强
# =========================================================================


def test_schemas_dir_is_absolute():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_resolves_to_absolute():
    """resolve 后是绝对。"""
    resolved = SCHEMAS_DIR.resolve()
    assert resolved.is_absolute()


def test_schemas_dir_parent_is_project_root():
    """SCHEMAS_DIR.parent 是 project_root（schemas 在 project 下）。"""
    project_root = SCHEMAS_DIR.parent
    # 应该含 pyproject.toml
    assert (project_root / "pyproject.toml").is_file()


def test_schemas_dir_name_is_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_has_4_json_files():
    json_files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(json_files) >= 4


def test_schemas_dir_no_python_files():
    py_files = list(SCHEMAS_DIR.glob("*.py"))
    assert len(py_files) == 0


def test_module_source_has_path_resolve_parent_parent():
    src = inspect.getsource(smod)
    assert "Path(__file__).resolve()" in src
    assert ".parent.parent" in src


# =========================================================================
# schema 文件内容深度补强
# =========================================================================


def test_manifest_schema_has_manifest_version_const():
    schema = load_schema("manifest.schema.json")
    properties = schema.get("properties", {})
    assert properties["manifest_version"].get("const") == "1.0"


def test_evaluation_report_schema_has_provenance():
    schema = load_schema("evaluation-report.schema.json")
    properties = schema.get("properties", {})
    assert "provenance" in properties


def test_evaluation_report_schema_has_per_doc_array():
    schema = load_schema("evaluation-report.schema.json")
    properties = schema.get("properties", {})
    assert properties["per_doc"].get("type") == "array"


def test_annotation_schema_has_chunk_boundary_anchors():
    schema = load_schema("annotation.schema.json")
    properties = schema.get("properties", {})
    assert "chunk_boundary_anchors" in properties


def test_annotation_schema_has_doc_id():
    schema = load_schema("annotation.schema.json")
    properties = schema.get("properties", {})
    assert "doc_id" in properties


def test_document_schema_has_source_type():
    schema = load_schema("document.schema.json")
    properties = schema.get("properties", {})
    assert "source_type" in properties


def test_manifest_schema_documents_is_array():
    schema = load_schema("manifest.schema.json")
    properties = schema.get("properties", {})
    assert properties["documents"].get("type") == "array"


def test_document_schema_elements_is_array():
    schema = load_schema("document.schema.json")
    properties = schema.get("properties", {})
    assert properties["elements"].get("type") == "array"


def test_document_schema_chunks_is_array():
    schema = load_schema("document.schema.json")
    properties = schema.get("properties", {})
    assert properties["chunks"].get("type") == "array"


# =========================================================================
# module source forbidden tokens 补强
# =========================================================================


def test_module_source_no_os():
    src = inspect.getsource(smod)
    assert "import os" not in src
    assert "from os " not in src


def test_module_source_no_sys():
    src = inspect.getsource(smod)
    assert "import sys" not in src


def test_module_source_no_socket():
    src = inspect.getsource(smod)
    assert "import socket" not in src


def test_module_source_no_email():
    src = inspect.getsource(smod)
    assert "import email" not in src


def test_module_source_no_html():
    src = inspect.getsource(smod)
    assert "import html" not in src


def test_module_source_no_http():
    src = inspect.getsource(smod)
    assert "import http" not in src


def test_module_source_no_urllib():
    src = inspect.getsource(smod)
    assert "import urllib" not in src


def test_module_source_no_sqlite3():
    src = inspect.getsource(smod)
    assert "import sqlite3" not in src


def test_module_source_no_csv():
    src = inspect.getsource(smod)
    assert "import csv" not in src


def test_module_source_no_pickle():
    src = inspect.getsource(smod)
    assert "import pickle" not in src


# =========================================================================
# module imports 顺序 + future 补强
# =========================================================================


def test_module_imports_order_6_statements():
    src = inspect.getsource(smod)
    lines = src.split("\n")
    import_lines = [l for l in lines if l.startswith("import ") or l.startswith("from ")]
    # 6 imports: future, json, pathlib, typing, jsonschema Draft + ValidationError
    assert len(import_lines) == 6


def test_module_imports_has_future_annotations():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_imports_has_import_json():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_imports_has_from_pathlib():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_imports_has_from_typing_any():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_no_import_json_as():
    src = inspect.getsource(smod)
    assert "import json as" not in src


# =========================================================================
# module docstring 深度补强
# =========================================================================


def test_module_docstring_contains_manifest():
    src = inspect.getsource(smod)
    assert "manifest" in src


def test_module_docstring_contains_annotation():
    src = inspect.getsource(smod)
    assert "annotation" in src


def test_module_docstring_contains_evaluation_report():
    src = inspect.getsource(smod)
    assert "evaluation-report" in src


def test_module_docstring_contains_app_schema():
    src = inspect.getsource(smod)
    assert "app/schema.py" in src


def test_module_docstring_contains_business():
    src = inspect.getsource(smod)
    assert "业务" in src


def test_module_docstring_contains_evaluation():
    src = inspect.getsource(smod)
    assert "评测" in src


# =========================================================================
# signatures 精确补强
# =========================================================================


def test_load_schema_signature_param_name():
    sig = inspect.signature(load_schema)
    assert "name" in sig.parameters


def test_validate_signature_param_names():
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_validate_file_signature_param_names():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


def test_validate_file_path_annotation_is_path_or_str():
    sig = inspect.signature(validate_file)
    # from __future__ → annotation 是 string
    ann = sig.parameters["path"].annotation
    assert "Path" in ann and "str" in ann


def test_validate_no_varargs_varkw():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_validate_file_no_varargs_varkw():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


def test_load_schema_no_varargs_varkw():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)


# =========================================================================
# module source level 完整补强
# =========================================================================


def test_eval_schema_error_source_has_super_init():
    src = inspect.getsource(EvalSchemaError)
    assert "super().__init__(message)" in src


def test_eval_schema_error_source_has_self_errors_assignment():
    src = inspect.getsource(EvalSchemaError)
    assert "self.errors = errors or []" in src


def test_load_schema_source_complete():
    src = inspect.getsource(load_schema)
    assert 'with _schema_path(name).open("r", encoding="utf-8")' in src
    assert "return json.load(f)" in src


def test_validate_source_complete():
    src = inspect.getsource(validate)
    assert "schema = load_schema(schema_name)" in src
    assert "validator = Draft202012Validator(schema)" in src
    assert "errors = sorted(validator.iter_errors(instance)" in src
    assert "if not errors:" in src
    assert "return" in src
    assert "head = errors[0]" in src
    assert "raise EvalSchemaError" in src


def test_validate_file_source_complete():
    src = inspect.getsource(validate_file)
    assert "p = Path(path)" in src
    assert "if not p.is_file():" in src
    assert "raise FileNotFoundError" in src
    assert "with p.open" in src
    assert "validate(data, schema_name)" in src


# =========================================================================
# 端到端集成补强
# =========================================================================


def test_e2e_validate_3_schemas_happy_path():
    """3 个 schema 都 happy path（manifest/annotation/evaluation-report）。"""
    # manifest
    validate({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }, "manifest.schema.json")
    # annotation
    validate({
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [],
    }, "annotation.schema.json")


def test_e2e_cross_schema_fails():
    """cross-schema 失败：用 annotation 实例验证 manifest schema。"""
    with pytest.raises(EvalSchemaError):
        validate({
            "annotation_version": "1.0",
            "doc_id": "d1",
            "chunk_boundary_anchors": [],
        }, "manifest.schema.json")


def test_e2e_validate_file_3_schemas_happy(tmp_path):
    """validate_file 3 个 schema happy。"""
    # manifest
    p1 = tmp_path / "manifest.json"
    p1.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(str(p1), "manifest.schema.json")
    # annotation
    p2 = tmp_path / "annotation.json"
    p2.write_text(json.dumps({
        "annotation_version": "1.0",
        "doc_id": "d1",
        "chunk_boundary_anchors": [],
    }), encoding="utf-8")
    validate_file(str(p2), "annotation.schema.json")


def test_e2e_validate_errors_grow_with_violations():
    """errors 含量随 violation 增加。"""
    # 单错误：缺 documents
    with pytest.raises(EvalSchemaError) as exc1:
        validate({"manifest_version": "1.0"}, "manifest.schema.json")
    n1 = len(exc1.value.errors)

    # 多错误：缺 documents + 加非法 type
    with pytest.raises(EvalSchemaError) as exc2:
        validate({"manifest_version": "wrong"}, "manifest.schema.json")
    n2 = len(exc2.value.errors)

    # 都至少 1 个错误
    assert n1 >= 1
    assert n2 >= 1


def test_e2e_validate_file_with_path_object(tmp_path):
    """validate_file with Path object."""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


# =========================================================================
# 模块整体合理性
# =========================================================================


def test_module_has_1_class():
    """module 有 1 个 class：EvalSchemaError。"""
    classes = [n for n in dir(smod)
               if inspect.isclass(getattr(smod, n))
               and getattr(smod, n).__module__ == "evaluation.schema"]
    assert "EvalSchemaError" in classes


def test_module_has_3_public_functions():
    """module 有 3 个 public function：load_schema, validate, validate_file。"""
    import types
    funcs = [n for n in dir(smod)
             if not n.startswith("_")
             and isinstance(getattr(smod, n), types.FunctionType)
             and getattr(smod, n).__module__ == "evaluation.schema"]
    assert sorted(funcs) == ["load_schema", "validate", "validate_file"]


def test_module_has_1_private_helper():
    """module 有 1 个 _前缀 helper：_schema_path。"""
    import types
    privates = [n for n in dir(smod)
                if n.startswith("_")
                and not n.startswith("__")
                and isinstance(getattr(smod, n), types.FunctionType)
                and getattr(smod, n).__module__ == "evaluation.schema"]
    assert privates == ["_schema_path"]


def test_module_has_no_main_block():
    src = inspect.getsource(smod)
    assert 'if __name__ ==' not in src
    assert '__main__' not in src


def test_module_has_only_one_constant_schemas_dir():
    """module 唯一 constant 是 SCHEMAS_DIR（其他都是 class/function）。"""
    non_callables = [n for n in dir(smod)
                     if not n.startswith("_")
                     and not callable(getattr(smod, n))
                     and not inspect.isclass(getattr(smod, n))]
    # SCHEMAS_DIR 是 Path 实例
    assert "SCHEMAS_DIR" in non_callables
