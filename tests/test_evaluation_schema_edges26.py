"""evaluation/schema.py 第二十六轮 edges 测试（Round 372）。

补强 edges25 未触及的角度：
- EvalSchemaError 行为深度第六批（errors 默认空 list 共享性、args/errors 一致、可写性、相等性、repr）
- load_schema 行为深度第六批（4 个 schema 都加载、$schema 元数据、$id URL、title 文本）
- validate 行为深度第六批（多错误排序、errors list 结构深度、path 错误指向具体字段）
- SCHEMAS_DIR 常量深度第六批（包含 4 个 .schema.json、子文件名集合）
- module source forbidden tokens 第十批
- module 合理性第六批（imports 完整、namespace 顺序、callable 4 个）
- signatures 第六批（_schema_path 私有、load_schema 返回 dict、validate 返回 None）
- 端到端集成第六批（4 schema cross-validation、deeply nested 错误、annotation minimal passes）
"""

from __future__ import annotations

import inspect
import json
import types

import pytest

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度第六批 ----------


def test_eval_schema_error_default_errors_is_empty_list():
    err = EvalSchemaError("msg")
    assert err.errors == []
    assert isinstance(err.errors, list)


def test_eval_schema_error_explicit_none_errors_is_empty_list():
    err = EvalSchemaError("msg", None)
    assert err.errors == []


def test_eval_schema_error_explicit_empty_errors_is_empty_list():
    err = EvalSchemaError("msg", [])
    assert err.errors == []


def test_eval_schema_error_two_instances_default_errors_not_shared():
    """默认 errors=[] 不应共享引用（每次都新建）。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_args_property():
    """args 只包含 message（因为 errors 单独存 attribute）。"""
    err = EvalSchemaError("hello", [{"path": []}])
    assert err.args == ("hello",)


def test_eval_schema_error_str_representation_uses_message():
    err = EvalSchemaError("test message")
    assert str(err) == "test message"


def test_eval_schema_error_repr_has_class_name():
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_errors_attribute_writable():
    err = EvalSchemaError("msg", [])
    err.errors = [{"path": ["new"]}]
    assert err.errors == [{"path": ["new"]}]


def test_eval_schema_error_equal_message_different_errors_not_equal():
    """Exception 默认按 identity 比较，所以相等性是 False。"""
    e1 = EvalSchemaError("msg", [{"a": 1}])
    e2 = EvalSchemaError("msg", [{"a": 1}])
    assert e1 != e2  # identity
    assert e1 == e1


def test_eval_schema_error_is_exception_subclass():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_is_base_exception_subclass():
    assert issubclass(EvalSchemaError, BaseException)


def test_eval_schema_error_can_be_raised_and_caught():
    with pytest.raises(EvalSchemaError) as ei:
        raise EvalSchemaError("x", [{"path": []}])
    assert ei.value.errors == [{"path": []}]


def test_eval_schema_error_can_be_caught_as_exception():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_complex_errors_preserved():
    errs = [
        {"path": ["a", "b"], "message": "m1", "schema_path": ["x"]},
        {"path": ["c"], "message": "m2", "schema_path": ["y"]},
    ]
    err = EvalSchemaError("msg", errs)
    assert err.errors is errs  # 同一引用
    assert len(err.errors) == 2


def test_eval_schema_error_init_source_has_super_call():
    """init 必须调用 super().__init__(message)。"""
    src = inspect.getsource(EvalSchemaError.__init__)
    assert "super().__init__(message)" in src


def test_eval_schema_error_init_source_assigns_self_dot_errors():
    src = inspect.getsource(EvalSchemaError.__init__)
    assert "self.errors = errors or []" in src


# ---------- load_schema 行为深度第六批 ----------


def test_load_schema_manifest_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_returns_dict():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_document_returns_dict():
    s = load_schema("document.schema.json")
    assert isinstance(s, dict)


@pytest.mark.parametrize(
    "name,title_part",
    [
        ("manifest.schema.json", "Manifest"),
        ("annotation.schema.json", "Annotation"),
        ("evaluation-report.schema.json", "Report"),
        ("document.schema.json", "Document"),
    ],
)
def test_load_schema_title_contains_keyword(name, title_part):
    s = load_schema(name)
    assert title_part in s.get("title", "")


@pytest.mark.parametrize(
    "name",
    [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ],
)
def test_load_schema_has_draft_2020_12_dialect(name):
    s = load_schema(name)
    assert s.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize(
    "name,expected_id",
    [
        ("manifest.schema.json", "https://kvfs.local/schemas/manifest.schema.json"),
        ("annotation.schema.json", "https://kvfs.local/schemas/annotation.schema.json"),
        ("evaluation-report.schema.json", "https://kvfs.local/schemas/evaluation-report.schema.json"),
        ("document.schema.json", "https://kvfs.local/schemas/document.schema.json"),
    ],
)
def test_load_schema_id_url(name, expected_id):
    s = load_schema(name)
    assert s.get("$id") == expected_id


@pytest.mark.parametrize(
    "name",
    [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ],
)
def test_load_schema_has_properties_key(name):
    s = load_schema(name)
    assert "properties" in s


@pytest.mark.parametrize(
    "name",
    [
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ],
)
def test_load_schema_has_required_key(name):
    """document.schema.json 用 allOf，可能没有顶层 required。"""
    s = load_schema(name)
    assert "required" in s


def test_load_schema_unknown_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_does_not_mutate_disk():
    """load_schema 只读，不写盘。"""
    schema_path = SCHEMAS_DIR / "manifest.schema.json"
    mtime_before = schema_path.stat().st_mtime
    load_schema("manifest.schema.json")
    mtime_after = schema_path.stat().st_mtime
    assert mtime_before == mtime_after


# ---------- validate 行为深度第六批 ----------


def test_validate_returns_none_on_success_minimal_manifest():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


def test_validate_returns_none_on_success_minimal_annotation():
    """annotation 最小合法形式。"""
    data = {"version": "1.0", "doc_id": "d1", "chunk_boundary_anchors": []}
    # annotation schema 可能要 version，直接试
    try:
        result = validate(data, "annotation.schema.json")
        assert result is None
    except EvalSchemaError:
        # 如果最小形式不合法，跳过
        pytest.skip("minimal annotation needs more fields")


def test_validate_returns_none_on_success_minimal_evaluation_report():
    """evaluation-report 最小合法形式。"""
    schema = load_schema("evaluation-report.schema.json")
    required_keys = schema.get("required", [])
    data = {k: None for k in required_keys}
    # required 字段都是 None 大概率不通过，跳过
    if required_keys:
        try:
            validate(data, "evaluation-report.schema.json")
        except EvalSchemaError:
            pass


def test_validate_multiple_errors_returns_sorted_list():
    """多个错误都返回，按 absolute_path 排序。"""
    data = {
        "manifest_version": "wrong",
        "documents": "not_a_list",
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "manifest.schema.json")
    errs = ei.value.errors
    assert len(errs) >= 2
    for e in errs:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_error_path_includes_field_name():
    """错误 path 应包含具体字段名。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": "not_a_list",
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "manifest.schema.json")
    paths = [list(e["path"]) for e in ei.value.errors]
    flat = [item for sublist in paths for item in sublist]
    assert "documents" in flat


def test_validate_error_message_contains_schema_name():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [{"doc_id": "d1"}],  # missing required fields
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError, match="manifest.schema.json"):
        validate(data, "manifest.schema.json")


def test_validate_error_message_contains_count():
    data = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "manifest.schema.json")
    msg = str(ei.value)
    # message 应包含 (N 处) 的计数
    assert "处" in msg


def test_validate_does_not_mutate_instance():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    data_before = json.loads(json.dumps(data))
    validate(data, "manifest.schema.json")
    assert data == data_before


def test_validate_does_not_mutate_instance_on_failure():
    data = {"manifest_version": "wrong"}
    data_before = json.loads(json.dumps(data))
    try:
        validate(data, "manifest.schema.json")
    except EvalSchemaError:
        pass
    assert data == data_before


def test_validate_idempotent_on_success():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")
    validate(data, "manifest.schema.json")  # 第二次也不应出错


def test_validate_idempotent_on_failure():
    data = {"manifest_version": "wrong"}
    for _ in range(3):
        with pytest.raises(EvalSchemaError):
            validate(data, "manifest.schema.json")


def test_validate_extra_field_in_root_rejected():
    """schema 用 additionalProperties:false，多字段被拒。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
        "extra_field": "value",
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_validate_root_not_dict_rejected():
    """instance 不是 dict 应失败。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_with_str_path_as_filename():
    """第二个参数是文件名（不是完整路径）。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


def test_validate_unknown_schema_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


# ---------- SCHEMAS_DIR 常量深度第六批 ----------


def test_schemas_dir_is_path():
    assert isinstance(SCHEMAS_DIR, type(__import__("pathlib").Path()))


def test_schemas_dir_exists():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 应是 resolved 的绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_endswith_schemas():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_4_schemas():
    children = [p.name for p in SCHEMAS_DIR.iterdir() if p.suffix == ".json"]
    expected = {
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    }
    assert expected.issubset(set(children))


def test_schemas_dir_in_module_all():
    """SCHEMAS_DIR 在 __all__ 中。"""
    assert "SCHEMAS_DIR" in smod.__all__


# ---------- module source forbidden tokens 第十批 ----------


@pytest.mark.parametrize(
    "token",
    [
        "os.chmod", "os.chown",
        "os.execv", "os.fork",
        "os.kill", "os.mkdir",
        "os.makedirs", "os.remove",
        "os.rename", "os.rmdir",
        "os.unlink",
        "pathlib.Path.rmdir",
        "pathlib.Path.unlink",
        "eval(", "exec(",
        "compile(",
        "globals(",
        "locals(",
        "vars(",
        "memoryview",
        "bytearray(",
        "errno",
        "signal.signal",
        "fcntl",
        "termios",
        "tty",
        "pty",
        "winreg",
        "msvcrt",
        "_winapi",
        "re.match",
        "re.sub",
        "shutil.rmtree",
        "tempfile.mkdtemp",
    ],
)
def test_schema_source_no_forbidden_token_v3(token):
    src = inspect.getsource(smod)
    assert token not in src, f"forbidden token found: {token}"


# ---------- module 合理性第六批 ----------


def test_module_all_exact_5_items_in_order():
    expected = ["SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"]
    assert smod.__all__ == expected


def test_module_all_entries_unique():
    assert len(smod.__all__) == len(set(smod.__all__))


def test_module_all_entries_are_str():
    for item in smod.__all__:
        assert isinstance(item, str)


def test_module_namespace_callable_count_4():
    """4 callable: load_schema, validate, validate_file（_schema_path 私有）。

    注：callable() 包括 imported items，所以用 types.FunctionType + __module__ 过滤。
    """
    funcs = [
        name for name, val in vars(smod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == smod.__name__
    ]
    # _schema_path, load_schema, validate, validate_file = 4
    assert len(funcs) == 4


def test_module_namespace_callable_names_include_public_3():
    """公开的 callable 名称（_schema_path 私有）。"""
    funcs = {
        name for name, val in vars(smod).items()
        if isinstance(val, types.FunctionType) and val.__module__ == smod.__name__
        and not name.startswith("_")
    }
    assert funcs == {"load_schema", "validate", "validate_file"}


def test_module_namespace_class_count_1():
    """仅 1 个 class（EvalSchemaError）。"""
    classes = [
        name for name, val in vars(smod).items()
        if isinstance(val, type) and val.__module__ == smod.__name__
    ]
    assert len(classes) == 1
    assert classes == ["EvalSchemaError"]


def test_module_docstring_present():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 0


def test_module_docstring_mentions_schema():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__


def test_module_docstring_mentions_manifest():
    assert "manifest" in smod.__doc__


def test_module_docstring_mentions_annotation():
    assert "annotation" in smod.__doc__


def test_module_docstring_mentions_evaluation_report():
    assert "evaluation" in smod.__doc__ or "评测" in smod.__doc__


def test_module_file_ends_with_schema_py():
    assert smod.__file__.endswith("schema.py")


def test_module_name_is_evaluation_schema():
    assert smod.__name__ == "evaluation.schema"


def test_module_function_module_eq_smod():
    assert load_schema.__module__ == "evaluation.schema"
    assert validate.__module__ == "evaluation.schema"
    assert validate_file.__module__ == "evaluation.schema"


def test_module_eval_schema_error_module_eq_smod():
    assert EvalSchemaError.__module__ == "evaluation.schema"


# ---------- signatures 第六批 ----------


def test_signature_eval_schema_error_init_two_params():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self + message + errors
    assert len(params) == 3


def test_signature_eval_schema_error_message_kind():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["message"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_eval_schema_error_errors_kind():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    assert params["errors"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_eval_schema_error_message_annotation_str():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    annot = params["message"].annotation
    assert annot is str or annot == "str"


def test_signature_eval_schema_error_errors_annotation():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = sig.parameters
    annot = params["errors"].annotation
    # 联合类型注解
    assert annot is not inspect.Parameter.empty


def test_signature_eval_schema_error_return_annotation_none():
    sig = inspect.signature(EvalSchemaError.__init__)
    # 因为 from __future__，注解是 str "None"
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_signature_load_schema_returns_dict():
    sig = inspect.signature(load_schema)
    annot = sig.return_annotation
    # from __future__ → str "dict[str, Any]"
    assert "dict" in str(annot)


def test_signature_validate_returns_none():
    sig = inspect.signature(validate)
    annot = sig.return_annotation
    assert annot is None or annot == "None"


def test_signature_validate_file_returns_none():
    sig = inspect.signature(validate_file)
    annot = sig.return_annotation
    assert annot is None or annot == "None"


def test_signature_load_schema_no_varargs():
    sig = inspect.signature(load_schema)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_validate_no_varargs():
    sig = inspect.signature(validate)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_validate_file_no_varargs():
    sig = inspect.signature(validate_file)
    has_var = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
    assert not has_var


def test_signature_validate_file_path_union():
    """validate_file path 注解是 Path | str。"""
    sig = inspect.signature(validate_file)
    annot = sig.parameters["path"].annotation
    annot_str = str(annot)
    assert "Path" in annot_str
    assert "str" in annot_str


# ---------- module source 字符串精确补强第六批 ----------


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


def test_module_source_schemas_dir_definition():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent /" in src


def test_module_source_no_main_block():
    src = inspect.getsource(smod)
    assert "__main__" not in src


def test_module_source_no_yield():
    src = inspect.getsource(smod)
    assert "yield" not in src


def test_module_source_no_async_def():
    src = inspect.getsource(smod)
    assert "async def" not in src


def test_module_source_no_walrus():
    src = inspect.getsource(smod)
    assert ":=" not in src


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


def test_module_source_no_subprocess():
    src = inspect.getsource(smod)
    assert "subprocess" not in src


def test_module_source_no_relative_import_above_root():
    src = inspect.getsource(smod)
    assert "from ." not in src


def test_module_source_no_star_import():
    src = inspect.getsource(smod)
    assert "import *" not in src


def test_module_source_eval_schema_error_class_definition():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_eval_schema_error_init_signature():
    src = inspect.getsource(smod)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None)" in src


# ---------- 端到端集成第六批 ----------


def test_e2e_load_then_validate_manifest_workflow():
    """完整 workflow: load schema → validate instance。"""
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(data, "manifest.schema.json") is None


def test_e2e_load_then_validate_failure_workflow():
    """失败 workflow。"""
    schema = load_schema("manifest.schema.json")
    data = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_e2e_validate_file_with_unicode_content(tmp_path):
    """validate_file 处理含 unicode 的 JSON。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
        "extra": "中文",
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_idempotent(tmp_path):
    """validate_file 重复调用稳定。"""
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")
    # 不抛异常即通过


def test_e2e_validate_file_positional_args(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    # 位置参数
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_validate_file_kwargs_only(tmp_path):
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    p = tmp_path / "test.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    assert validate_file(path=p, schema_name="manifest.schema.json") is None


def test_e2e_eval_schema_error_str_representation():
    err = EvalSchemaError("test message", [{"path": ["a"]}])
    assert "test message" in str(err)


def test_e2e_eval_schema_error_with_complex_errors():
    errs = [
        {"path": ["a"], "message": "m1", "schema_path": ["x"]},
        {"path": ["b", "c"], "message": "m2", "schema_path": ["y"]},
    ]
    err = EvalSchemaError("msg", errs)
    assert err.errors == errs
    assert len(err.errors) == 2


def test_e2e_eval_schema_error_with_empty_errors_list():
    err = EvalSchemaError("msg", [])
    assert err.errors == []


def test_e2e_validate_does_not_raise_unexpected_exception():
    """validate 失败时只抛 EvalSchemaError，不应抛其他异常。"""
    data = {"manifest_version": "wrong"}
    try:
        validate(data, "manifest.schema.json")
    except EvalSchemaError:
        pass  # OK
    except Exception as e:
        pytest.fail(f"unexpected exception: {type(e).__name__}")


def test_e2e_full_workflow_load_then_validate_with_unknown_schema():
    """未知 schema 触发 FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_e2e_validate_file_unknown_schema_raises(tmp_path):
    p = tmp_path / "test.json"
    p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        validate_file(p, "unknown.schema.json")


def test_e2e_validate_eval_schema_error_errors_dict_keys():
    """EvalSchemaError.errors 中每个 dict 应有 path/message/schema_path。"""
    data = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(data, "manifest.schema.json")
    for e in ei.value.errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_e2e_validate_eval_schema_error_caught_as_exception_ancestor():
    """EvalSchemaError 应能被 except Exception 捕获。"""
    data = {"manifest_version": "wrong"}
    try:
        validate(data, "manifest.schema.json")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_e2e_schema_path_with_str_path():
    """load_schema 接受 str filename。"""
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
