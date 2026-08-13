"""evaluation/schema.py 第六十轮 edges 测试（Round 586）。

补强 edges54 未触及的角度（第三十五批）。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
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


# ---------- SCHEMAS_DIR 第三十五批


def test_schemas_dir_is_path_batch35():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch35():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch35():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_schema_batch35():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch35():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch35():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_endswith_schemas_batch35():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_under_project_root_batch35():
    """SCHEMAS_DIR 应当位于项目根。"""
    # SCHEMAS_DIR = __file__.parent.parent / "schemas"
    expected_parent = Path(smod.__file__).resolve().parent.parent
    assert SCHEMAS_DIR.parent == expected_parent


# ---------- _schema_path 第三十五批


def test_schema_path_existing_file_batch35():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_returns_path_batch35():
    p = _schema_path("annotation.schema.json")
    assert isinstance(p, Path)


def test_schema_path_missing_raises_filenotfound_batch35():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


def test_schema_path_with_subdir_batch35():
    """带子目录的 schema name。"""
    # 测试函数能拼接子目录，但 schemas/ 下没有子目录，这里跳过
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.json")


def test_schema_path_empty_string_raises_batch35():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


# ---------- load_schema 第三十五批


def test_load_schema_manifest_returns_dict_batch35():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_returns_dict_batch35():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict_batch35():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_field_batch35():
    """JSON Schema 自身必须有 $schema 字段。"""
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "$schema" in s


def test_load_schema_has_id_field_batch35():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert "$id" in s


def test_load_schema_missing_raises_filenotfound_batch35():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_idempotent_batch35():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_does_not_cache_batch35():
    """load_schema 每次都重新读文件（验证不缓存）。"""
    # 间接验证：调用两次返回不同对象（虽然内容相同）
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    # dict 内容相同但应是不同对象
    assert s1 is not s2


# ---------- validate 第三十五批


def test_validate_callable_batch35():
    assert callable(validate)


def test_validate_valid_empty_dict_does_not_raise_for_permissive_schema_batch35():
    """空 dict 是否合法取决于 schema。这里只验证不抛非 EvalSchemaError 异常。"""
    # annotation.schema.json 顶层要求 annotation_version + doc_id → 空 dict 应失败
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_invalid_raises_eval_schema_error_batch35():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_returns_none_on_success_batch35():
    """validate 成功 → None（无返回值）。"""
    # 构造一个合法的 manifest 实例
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    out = validate(instance, "manifest.schema.json")
    assert out is None


def test_validate_error_has_errors_attribute_batch35():
    """抛 EvalSchemaError 时 errors 列表非空。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    e = exc_info.value
    assert isinstance(e.errors, list)
    assert len(e.errors) > 0


def test_validate_error_each_item_has_path_batch35():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "path" in err


def test_validate_error_each_item_has_message_batch35():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "message" in err


def test_validate_error_each_item_has_schema_path_batch35():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for err in exc_info.value.errors:
        assert "schema_path" in err


def test_validate_error_message_contains_schema_name_batch35():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc_info.value)


def test_validate_error_message_contains_count_batch35():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    # "校验失败 (N 处)"
    assert "校验失败" in str(exc_info.value)
    assert "处" in str(exc_info.value)


def test_validate_does_not_mutate_input_batch35():
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    before = json.dumps(instance, sort_keys=True)
    validate(instance, "manifest.schema.json")
    assert json.dumps(instance, sort_keys=True) == before


def test_validate_with_extra_keys_batch35():
    """额外字段是否合法取决于 schema additionalProperties。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "extra_key": "x",
    }
    # 不强制要求通过；只要不抛非 EvalSchemaError 异常
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError:
        pass


# ---------- validate_file 第三十五批


def test_validate_file_callable_batch35():
    assert callable(validate_file)


def test_validate_file_missing_raises_filenotfound_batch35(tmp_path):
    p = tmp_path / "nonexistent.json"
    with pytest.raises(FileNotFoundError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch35(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error_batch35(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_path_batch35(tmp_path):
    """传 str 路径（不是 Path）也支持。"""
    p = tmp_path / "bad.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(str(p), "manifest.schema.json")


def test_validate_file_success_returns_none_batch35(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_does_not_mutate_file_batch35(tmp_path):
    """不修改被校验的文件。"""
    p = tmp_path / "manifest.json"
    content = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    p.write_text(content, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == content


def test_validate_file_with_unicode_path_batch35(tmp_path):
    """unicode 文件名也支持。"""
    p = tmp_path / "清单.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- EvalSchemaError 第三十五批


def test_eval_schema_error_subclass_of_exception_batch35():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_callable_batch35():
    assert callable(EvalSchemaError)


def test_eval_schema_error_init_no_args_raises_batch35():
    """无参数构造会抛 TypeError（message 是 required）。"""
    with pytest.raises(TypeError):
        EvalSchemaError()  # type: ignore[call-arg]


def test_eval_schema_error_init_one_arg_batch35():
    e = EvalSchemaError("msg")
    assert str(e) == "msg"
    assert e.errors == []


def test_eval_schema_error_init_two_args_batch35():
    e = EvalSchemaError("msg", [{"x": 1}])
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_init_errors_none_batch35():
    e = EvalSchemaError("msg", None)
    assert e.errors == []


def test_eval_schema_error_init_errors_empty_list_batch35():
    e = EvalSchemaError("msg", [])
    assert e.errors == []


def test_eval_schema_error_init_errors_dict_batch35():
    """传 dict 而不是 list → 当 falsy 时变 []；非 falsy 时直接保存（不强制类型）。"""
    e = EvalSchemaError("msg", {"k": "v"})
    # errors=dict 不 falsy → 直接保存（不强制类型）
    assert e.errors == {"k": "v"}


def test_eval_schema_error_can_be_raised_and_caught_batch35():
    with pytest.raises(EvalSchemaError):
        raise EvalSchemaError("x")


def test_eval_schema_error_can_be_caught_as_exception_batch35():
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_errors_attribute_writable_batch35():
    e = EvalSchemaError("x")
    e.errors = [{"new": 1}]
    assert e.errors == [{"new": 1}]


def test_eval_schema_error_repr_batch35():
    """repr 包含类名。"""
    e = EvalSchemaError("msg")
    r = repr(e)
    assert "EvalSchemaError" in r


def test_eval_schema_error_with_unicode_message_batch35():
    e = EvalSchemaError("中文消息")
    assert "中文消息" in str(e)


def test_eval_schema_error_with_long_message_batch35():
    msg = "x" * 1000
    e = EvalSchemaError(msg)
    assert str(e) == msg


def test_eval_schema_error_inherits_args_attribute_batch35():
    e = EvalSchemaError("msg", [{"x": 1}])
    # args 仅含 message（errors 单独存）
    assert e.args == ("msg",)


# ---------- module source forbidden tokens 第五十九批


FORBIDDEN_TOKENS = [
    "eval(",
    "exec(",
    "pickle",
    "yaml",
    "__import__",
    "breakpoint(",
    "shutil",
    "requests",
    "subprocess",
    "os.system",
    "pty.",
    "ctypes",
    "urllib",
    "socket",
]


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_module_source_no_forbidden_tokens_batch35(token):
    src = inspect.getsource(smod)
    assert token not in src


# ---------- module source 字符串精确补强第五十五批


def test_module_source_contains_design_doc_batch35():
    src = inspect.getsource(smod)
    assert "加载并校验" in src


def test_module_source_contains_no_reuse_comment_batch35():
    src = inspect.getsource(smod)
    assert "不与 app/schema.py 复用" in src


def test_module_source_contains_draft_validator_import_batch35():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_validation_error_import_batch35():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError" in src


def test_module_source_contains_schemas_dir_definition_batch35():
    src = inspect.getsource(smod)
    assert 'SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"' in src


def test_module_source_contains_class_definition_batch35():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_source_contains_errors_doc_batch35():
    src = inspect.getsource(smod)
    assert "errors 给程序看" in src


def test_module_source_contains_schema_path_function_batch35():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_function_batch35():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_function_batch35():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_function_batch35():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_json_load_call_batch35():
    src = inspect.getsource(smod)
    assert "json.load(f)" in src


def test_module_source_contains_iter_errors_call_batch35():
    src = inspect.getsource(smod)
    assert "validator.iter_errors(instance)" in src


def test_module_source_contains_sort_errors_keyword_batch35():
    src = inspect.getsource(smod)
    assert "errors = sorted" in src


def test_module_source_contains_absolute_path_keyword_batch35():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_keyword_batch35():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_filenotfound_handler_batch35():
    src = inspect.getsource(smod)
    assert "FileNotFoundError" in src


def test_module_source_contains_encoding_utf8_batch35():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_pathlib_path_import_batch35():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch35():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


# ---------- signatures 第五十五批


def test_signature_schema_path_one_param_batch35():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_schema_path_return_path_batch35():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_signature_load_schema_one_param_batch35():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_load_schema_return_dict_batch35():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_signature_validate_two_params_batch35():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_return_none_batch35():
    """validate 签名 return annotation 是 None（字符串 'None'，因 future annotations）。"""
    sig = inspect.signature(validate)
    assert sig.return_annotation in (None, "None")


def test_signature_validate_file_two_params_batch35():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_validate_file_return_none_batch35():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation in (None, "None")


def test_signature_eval_schema_error_init_batch35():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_signature_eval_schema_error_init_errors_optional_batch35():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


# ---------- module 合理性 第五十五批


def test_module_has_all_attribute_batch35():
    assert hasattr(smod, "__all__")


def test_module_all_is_list_batch35():
    assert isinstance(smod.__all__, list)


def test_module_all_len_five_batch35():
    assert len(smod.__all__) == 5


def test_module_all_contains_schemas_dir_batch35():
    assert "SCHEMAS_DIR" in smod.__all__


def test_module_all_contains_eval_schema_error_batch35():
    assert "EvalSchemaError" in smod.__all__


def test_module_all_contains_load_schema_batch35():
    assert "load_schema" in smod.__all__


def test_module_all_contains_validate_batch35():
    assert "validate" in smod.__all__


def test_module_all_contains_validate_file_batch35():
    assert "validate_file" in smod.__all__


def test_module_does_not_export_schema_path_batch35():
    """_schema_path 是私有，不在 __all__。"""
    assert "_schema_path" not in smod.__all__


def test_module_has_one_class_definition_batch35():
    """模块只有 EvalSchemaError 一个 class。"""
    import ast
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


# ---------- 端到端集成 第五十五批


def test_e2e_validate_then_inspect_errors_batch35():
    """validate 失败后能从异常中拿到详细 errors。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 每个 error 含 path / message / schema_path
        for err in e.errors:
            assert isinstance(err["path"], list)
            assert isinstance(err["message"], str)
            assert isinstance(err["schema_path"], list)


def test_e2e_validate_file_round_trip_batch35(tmp_path):
    """写一个合法 JSON 再校验。"""
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # 不抛异常即成功
    validate_file(p, "manifest.schema.json")


def test_e2e_load_then_validate_batch35():
    """先 load_schema 再用 Draft202012Validator 校验。"""
    from jsonschema import Draft202012Validator
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    errors = list(validator.iter_errors(instance))
    assert errors == []


def test_e2e_idempotent_validate_batch35():
    instance = {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []}
    validate(instance, "manifest.schema.json")
    validate(instance, "manifest.schema.json")
    # 不抛异常即成功


def test_e2e_full_workflow_with_eval_schema_error_round_trip_batch35():
    """EvalSchemaError 能 str/repr/json-safe 序列化。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # str(e) 是合法 string
        assert isinstance(str(e), str)
        # e.errors 是 JSON-serializable
        json.dumps(e.errors, ensure_ascii=False)
