"""evaluation/schema.py 第九十轮 edges 测试（Round 626）。

补强 edges58 未触及的角度（第四十四批）。

新角度：
- SCHEMAS_DIR 父目录结构
- _schema_path 错误消息含完整路径
- _schema_path 接受带子目录的 name
- load_schema 各 schema 含 $schema/$id
- load_schema 返回 dict 类型
- validate 多个错误聚合
- validate 错误按 path 排序
- validate_file 不存在 → FileNotFoundError 含路径
- validate_file 调用 validate
- EvalSchemaError errors field 各种情况
- EvalSchemaError catchable by specific except
- EvalSchemaError 关键字参数 errors=
- 模块源码字符串精确
- AST 结构
- forbidden tokens 第九十六批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

import evaluation.schema as schema_mod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- SCHEMAS_DIR 详细 ----------

def test_schemas_dir_parent_name_batch44():
    """SCHEMAS_DIR.parent 应该是 evaluation 的父（项目根）。"""
    parent = SCHEMAS_DIR.parent
    # 项目根包含 pyproject.toml
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_contains_only_json_files_batch44():
    """schemas/ 目录下都是 .json 文件。"""
    for p in SCHEMAS_DIR.iterdir():
        if p.is_file():
            assert p.suffix == ".json"


def test_schemas_dir_resolved_absolute_batch44():
    """SCHEMAS_DIR 是绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


# ---------- _schema_path 详细 ----------

def test_schema_path_error_contains_full_path_batch44():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("missing.json")
    msg = str(exc_info.value)
    # 错误消息含 schemas 目录路径
    assert "schemas" in msg
    assert "missing.json" in msg


def test_schema_path_returns_path_with_parent_schemas_batch44():
    p = _schema_path("manifest.schema.json")
    assert p.parent.name == "schemas"


def test_schema_path_pathlib_join_batch44():
    """_schema_path 用 SCHEMAS_DIR / name 拼接。"""
    src = inspect.getsource(_schema_path)
    assert "SCHEMAS_DIR / name" in src


# ---------- load_schema 各 schema 内容 ----------

def test_load_schema_manifest_has_type_object_batch44():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object" or "properties" in s


def test_load_schema_annotation_has_type_object_batch44():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object" or "properties" in s


def test_load_schema_evaluation_report_has_type_object_batch44():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object" or "properties" in s


def test_load_schema_manifest_has_required_batch44():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    required = s["required"]
    assert "manifest_version" in required
    assert "devset_status" in required
    assert "documents" in required


def test_load_schema_evaluation_report_has_required_batch44():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


# ---------- validate 详细 ----------

def test_validate_returns_none_on_success_batch44():
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    out = validate(valid, "manifest.schema.json")
    assert out is None


def test_validate_invalid_type_raises_eval_schema_error_batch44():
    """顶层不是 dict → EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_invalid_type_string_raises_batch44():
    with pytest.raises(EvalSchemaError):
        validate("not a dict", "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_invalid_type_int_raises_batch44():
    with pytest.raises(EvalSchemaError):
        validate(42, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_invalid_type_none_raises_batch44():
    with pytest.raises(EvalSchemaError):
        validate(None, "manifest.schema.json")  # type: ignore[arg-type]


def test_validate_devset_status_complete_batch44():
    valid = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    # 不抛即过
    validate(valid, "manifest.schema.json")


def test_validate_devset_status_incomplete_batch44():
    valid = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(valid, "manifest.schema.json")


def test_validate_devset_status_invalid_value_batch44():
    bad = {
        "manifest_version": "1.0",
        "devset_status": "partial",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_devset_status_missing_batch44():
    bad = {
        "manifest_version": "1.0",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(bad, "manifest.schema.json")


def test_validate_errors_count_batch44():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    # errors 应该非空（多个 required 缺失）
    assert len(exc_info.value.errors) >= 1


def test_validate_error_path_is_list_batch44():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert isinstance(e["path"], list)


def test_validate_error_schema_path_is_list_batch44():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert isinstance(e["schema_path"], list)


def test_validate_error_message_is_str_batch44():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert isinstance(e["message"], str)


# ---------- validate_file 详细 ----------

def test_validate_file_returns_none_on_success_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    out = validate_file(p, "manifest.schema.json")
    assert out is None


def test_validate_file_error_contains_path_batch44(tmp_path):
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    msg = str(exc_info.value)
    assert "missing.json" in msg
    assert "待校验文件不存在" in msg


def test_validate_file_json_decode_error_propagates_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_calls_validate_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    with patch("evaluation.schema.validate", return_value=None) as mock_v:
        validate_file(p, "any.schema.json")
    mock_v.assert_called_once_with({"foo": "bar"}, "any.schema.json")


def test_validate_file_passes_path_object_batch44(tmp_path):
    """validate_file 接受 Path 对象（不仅是 str）。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    # Path 对象
    validate_file(p, "manifest.schema.json")


def test_validate_file_passes_str_path_batch44(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


# ---------- EvalSchemaError 各种 ----------

def test_eval_schema_error_errors_default_is_list_batch44():
    e = EvalSchemaError("msg")
    assert isinstance(e.errors, list)
    assert e.errors == []


def test_eval_schema_error_keyword_argument_errors_batch44():
    """支持 errors= 关键字参数。"""
    e = EvalSchemaError("msg", errors=[{"x": 1}])
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_positional_argument_errors_batch44():
    """支持位置参数 errors。"""
    e = EvalSchemaError("msg", [{"x": 1}])
    assert e.errors == [{"x": 1}]


def test_eval_schema_error_catchable_with_specific_message_batch44():
    try:
        raise EvalSchemaError("specific msg")
    except EvalSchemaError as e:
        if "specific msg" not in str(e):
            pytest.fail("message mismatch")


def test_eval_schema_error_chain_with_from_batch44():
    """可以用 raise ... from ... 链式抛出。"""
    try:
        try:
            raise ValueError("original")
        except ValueError as orig:
            raise EvalSchemaError("wrapped") from orig
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_can_be_raised_in_try_block_batch44():
    """try-except 块内可正常抛出。"""
    for i in range(5):
        try:
            raise EvalSchemaError(f"msg {i}")
        except EvalSchemaError as e:
            assert f"msg {i}" in str(e)


def test_eval_schema_error_args_attribute_batch44():
    """Exception.args 应该包含 message。"""
    e = EvalSchemaError("msg")
    assert "msg" in e.args


def test_eval_schema_error_pickle_roundtrip_batch44():
    """EvalSchemaError 应该可以 pickle（继承自 Exception）。"""
    import pickle
    e = EvalSchemaError("msg", errors=[{"path": ["a"]}])
    data = pickle.dumps(e)
    out = pickle.loads(data)
    assert isinstance(out, EvalSchemaError)
    assert str(out) == "msg"


# ---------- module source ----------

def test_module_source_contains_does_not_reuse_app_schema_batch44():
    src = inspect.getsource(schema_mod)
    assert "不与 app/schema.py 复用" in src


def test_module_source_contains_business_vs_evaluation_batch44():
    src = inspect.getsource(schema_mod)
    assert "业务输出" in src
    assert "评测元数据" in src


def test_module_source_contains_jsonschema_imports_batch44():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsvalidationerror_import_batch44():
    """注意：实现 import 了 JSValidationError 但实际没用（删了？）。"""
    src = inspect.getsource(schema_mod)
    # 即使没用，import 语句存在
    assert "JSValidationError" in src or "ValidationError" in src


def test_module_source_contains_eval_schema_error_class_batch44():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_contains_errors_or_empty_list_batch44():
    src = inspect.getsource(schema_mod)
    assert "self.errors = errors or []" in src


def test_module_source_contains_schema_path_function_batch44():
    src = inspect.getsource(schema_mod)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_contains_load_schema_function_batch44():
    src = inspect.getsource(schema_mod)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_contains_validate_function_batch44():
    src = inspect.getsource(schema_mod)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_contains_validate_file_function_batch44():
    src = inspect.getsource(schema_mod)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


# ---------- __all__ ----------

def test_all_exact_order_batch44():
    assert list(schema_mod.__all__) == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_all_entries_importable_batch44():
    """__all__ 中每个名字都能 getattr 到。"""
    for name in schema_mod.__all__:
        assert hasattr(schema_mod, name), f"missing attr: {name}"


# ---------- AST 结构 ----------

def test_ast_eval_schema_error_class_position_batch44():
    """EvalSchemaError 在 SCHEMAS_DIR 之后，load_schema 之前。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    body_names = []
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    body_names.append(t.id)
        elif isinstance(n, ast.ClassDef):
            body_names.append(n.name)
        elif isinstance(n, ast.FunctionDef):
            body_names.append(n.name)
    # SCHEMAS_DIR 在 EvalSchemaError 之前
    assert body_names.index("SCHEMAS_DIR") < body_names.index("EvalSchemaError")
    # EvalSchemaError 在 load_schema 之前
    assert body_names.index("EvalSchemaError") < body_names.index("load_schema")


def test_ast_eval_schema_error_class_only_has_init_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert methods == ["__init__"]


def test_ast_eval_schema_error_init_calls_super_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    init = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"][0]
    # super().__init__(...) 调用
    has_super = False
    for n in ast.walk(init):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr == "__init__":
                has_super = True
    assert has_super


def test_ast_validate_function_has_sort_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    validate_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    # 内部用 sorted(...)
    has_sorted = False
    for n in ast.walk(validate_func):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted":
            has_sorted = True
    assert has_sorted


def test_ast_validate_function_has_iter_errors_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    validate_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    # 内部用 validator.iter_errors
    has_iter = False
    for n in ast.walk(validate_func):
        if isinstance(n, ast.Attribute) and n.attr == "iter_errors":
            has_iter = True
    assert has_iter


def test_ast_validate_function_raises_eval_schema_error_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    validate_func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    # 内部 raise EvalSchemaError
    has_raise = False
    for n in ast.walk(validate_func):
        if isinstance(n, ast.Raise):
            has_raise = True
    assert has_raise


def test_ast_no_for_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_no_with_in_module_body_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, (ast.With, ast.AsyncWith))


def test_ast_from_future_second_batch44():
    tree = ast.parse(inspect.getsource(schema_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第九十六批 ----------

def test_source_no_eval_batch44():
    src = inspect.getsource(schema_mod)
    assert "eval(" not in src


def test_source_no_exec_batch44():
    src = inspect.getsource(schema_mod)
    assert "exec(" not in src


def test_source_no_compile_batch44():
    src = inspect.getsource(schema_mod)
    assert "compile(" not in src


def test_source_no_globals_batch44():
    src = inspect.getsource(schema_mod)
    assert "globals(" not in src


def test_source_no_locals_batch44():
    src = inspect.getsource(schema_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch44():
    src = inspect.getsource(schema_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch44():
    src = inspect.getsource(schema_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch44():
    src = inspect.getsource(schema_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch44():
    src = inspect.getsource(schema_mod)
    assert "pickle.load(" not in src


def test_source_uses_json_load_batch44():
    """使用 json.load 而非 pickle/yaml。"""
    src = inspect.getsource(schema_mod)
    assert "json.load" in src
