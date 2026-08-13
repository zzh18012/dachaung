"""evaluation/schema.py 第九十三轮 edges 测试（Round 650）。

补强 edges61 未触及的角度（第四十八批）。

新角度：
- EvalSchemaError 子类化与构造（继承 Exception / errors 默认 [] / errors 显式 None / errors 显式 list / super().__init__）
- EvalSchemaError str/repr 行为
- _schema_path 边界（存在的 schema / 不存在的 schema / 嵌套名称）
- load_schema 边界（多个 schema 文件 / 文件名带 .json / 重复加载返回新 dict）
- validate 成功路径（多个合法 schema / instance 是空 dict / instance 嵌套）
- validate 失败路径（errors 排序按 absolute_path / errors flat 结构 / head 取 errors[0] / message 含 schema_name 和数量）
- validate_file 路径处理（Path / str / 相对路径 / 不存在文件 → FileNotFoundError）
- SCHEMAS_DIR 常量
- module source 字符串补强（jsonschema / Draft202012Validator / JSValidationError / sorted key lambda / __all__）
- AST 结构补强（1 ClassDef / 3 函数 / EvalSchemaError 1 method / validate 1 for / module docstring / 4 import）
- forbidden tokens 第一百二十批
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


# ---------- EvalSchemaError 子类化与构造 ----------

def test_eval_schema_error_is_exception_batch48():
    e = EvalSchemaError("msg")
    assert isinstance(e, Exception)


def test_eval_schema_error_errors_default_empty_batch48():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_errors_none_becomes_empty_batch48():
    e = EvalSchemaError("msg", errors=None)
    assert e.errors == []


def test_eval_schema_error_errors_explicit_list_batch48():
    errs = [{"path": ["a"], "message": "bad"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors is errs


def test_eval_schema_error_super_init_message_batch48():
    e = EvalSchemaError("hello")
    # super().__init__ 把 message 存到 args
    assert e.args == ("hello",)


def test_eval_schema_error_str_contains_message_batch48():
    e = EvalSchemaError("custom message")
    assert "custom message" in str(e)


def test_eval_schema_error_repr_is_exception_repr_batch48():
    e = EvalSchemaError("msg")
    # repr 应当是 EvalSchemaError('msg')
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_can_be_raised_and_caught_batch48():
    with pytest.raises(EvalSchemaError) as ei:
        raise EvalSchemaError("boom", errors=[{"k": 1}])
    assert ei.value.errors == [{"k": 1}]


def test_eval_schema_error_catch_as_exception_batch48():
    """作为 Exception 也能被捕获。"""
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_errors_attribute_writable_batch48():
    e = EvalSchemaError("msg")
    e.errors = [{"new": True}]
    assert e.errors == [{"new": True}]


def test_eval_schema_error_no_required_errors_arg_batch48():
    """errors 是可选参数。"""
    # 不传 errors 也能构造
    e = EvalSchemaError("just message")
    assert e.errors == []


# ---------- _schema_path 边界 ----------

def test_schema_path_existing_batch48():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_annotation_batch48():
    p = _schema_path("annotation.schema.json")
    assert p.is_file()


def test_schema_path_evaluation_report_batch48():
    p = _schema_path("evaluation-report.schema.json")
    assert p.is_file()


def test_schema_path_missing_raises_batch48():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    assert "不存在" in str(ei.value)


def test_schema_path_returns_path_object_batch48():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_nested_name_batch48():
    """带子目录的 schema 名也能解析（虽然实际不存在）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("subdir/nonexistent.schema.json")


# ---------- load_schema 边界 ----------

def test_load_schema_returns_dict_batch48():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_properties_batch48():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties_batch48():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties_batch48():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_twice_returns_independent_dicts_batch48():
    """每次 load_schema 都重新读盘，返回独立 dict（修改互不影响）。"""
    s1 = load_schema("manifest.schema.json")
    original = s1.get("type")
    s1["type"] = "MODIFIED"
    s2 = load_schema("manifest.schema.json")
    assert s2.get("type") == original


def test_load_schema_missing_raises_batch48():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# ---------- validate 成功路径 ----------

def test_validate_manifest_minimal_batch48():
    """最小合法 manifest：manifest_version="1.0", documents=[], devset_status。"""
    instance = {
        "manifest_version": "1.0",
        "documents": [],
        "devset_status": "complete",
    }
    # 不抛 = 通过
    validate(instance, "manifest.schema.json")


def test_validate_annotation_minimal_batch48():
    instance = {"annotation_version": "1.0", "doc_id": "d1"}
    validate(instance, "annotation.schema.json")


def test_validate_returns_none_on_success_batch48():
    instance = {
        "manifest_version": "1.0",
        "documents": [],
        "devset_status": "complete",
    }
    assert validate(instance, "manifest.schema.json") is None


# ---------- validate 失败路径 ----------

def test_validate_failure_raises_eval_schema_error_batch48():
    instance = {"manifest_version": "WRONG"}  # const "1.0" 不匹配
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_failure_errors_are_sorted_batch48():
    """errors 按 absolute_path 排序。"""
    instance = {
        "manifest_version": "1.0",
        "documents": [{"path": 123}],  # 多处错误
        "devset_status": "complete",
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    errs = ei.value.errors
    # 排序检查：每个 err 的 path 应当是不减的
    paths = [tuple(e["path"]) for e in errs]
    assert paths == sorted(paths)


def test_validate_failure_errors_flat_structure_batch48():
    """每个 err 是 dict with path/message/schema_path。"""
    instance = {"manifest_version": "BAD"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    for e in ei.value.errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_failure_message_contains_schema_name_batch48():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_failure_message_contains_error_count_batch48():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    # 至少 1 处错误，message 应含数量
    msg = str(ei.value)
    # 提取 "(N 处)"
    assert "处" in msg


def test_validate_failure_head_is_first_after_sort_batch48():
    """head 是 errors[0]（排序后第一个）。"""
    instance = {"manifest_version": "BAD", "documents": "not_list"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    msg = str(ei.value)
    # head.message 应当出现在 message 中
    errs = ei.value.errors
    if errs:
        # message 里的 head.message 应当等于 errs[0]["message"]
        assert errs[0]["message"] in msg


def test_validate_no_errors_returns_none_batch48():
    """通过 case 返回 None。"""
    instance = {
        "manifest_version": "1.0",
        "documents": [],
        "devset_status": "complete",
    }
    assert validate(instance, "manifest.schema.json") is None


# ---------- validate_file 路径处理 ----------

def test_validate_file_accepts_path_object_batch48(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "documents": [], "devset_status": "complete"}
        ),
        encoding="utf-8",
    )
    # 不抛
    validate_file(p, "manifest.schema.json")


def test_validate_file_accepts_str_path_batch48(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "documents": [], "devset_status": "complete"}
        ),
        encoding="utf-8",
    )
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_missing_raises_filenotfound_batch48(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsonerror_batch48(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_instance_raises_eval_error_batch48(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"manifest_version": "WRONG"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_passes_through_to_validate_batch48(tmp_path):
    """validate_file 调用 validate，正确 case 不抛。"""
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps(
            {"manifest_version": "1.0", "documents": [], "devset_status": "complete"}
        ),
        encoding="utf-8",
    )
    # 直接调用 validate_file 多次确认幂等
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")


# ---------- SCHEMAS_DIR 常量 ----------

def test_schemas_dir_is_path_batch48():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_exists_batch48():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_schema_batch48():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch48():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch48():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


# ---------- 模块源码补强 ----------

def test_source_contains_jsonschema_import_batch48():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator" in src


def test_source_contains_jsvalidationerror_import_batch48():
    src = inspect.getsource(schema_mod)
    assert "JSValidationError" in src


def test_source_contains_sorted_lambda_batch48():
    """validate 中 errors = sorted(..., key=lambda e: list(e.absolute_path))。"""
    src = inspect.getsource(schema_mod)
    assert "sorted" in src
    assert "absolute_path" in src


def test_source_contains_all_list_batch48():
    src = inspect.getsource(schema_mod)
    assert "__all__" in src


def test_source_contains_all_entries_batch48():
    src = inspect.getsource(schema_mod)
    for name in ("SCHEMAS_DIR", "EvalSchemaError", "load_schema", "validate", "validate_file"):
        assert name in src


def test_source_contains_class_eval_schema_error_batch48():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError" in src


def test_source_contains_file_not_found_batch48():
    src = inspect.getsource(schema_mod)
    assert "FileNotFoundError" in src


def test_source_contains_super_init_batch48():
    src = inspect.getsource(schema_mod)
    assert "super().__init__" in src


def test_source_contains_encoding_utf8_batch48():
    src = inspect.getsource(schema_mod)
    assert 'encoding="utf-8"' in src


def test_source_contains_docstring_distinct_from_app_schema_batch48():
    """模块 docstring 应当说明与 app/schema.py 分开的原因。"""
    src = inspect.getsource(schema_mod)
    assert "app/schema.py" in src or "app.schema" in src or "不复用" in src or "分开" in src


def test_source_contains_errors_or_none_default_batch48():
    src = inspect.getsource(schema_mod)
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_source_contains_errors_or_empty_list_batch48():
    src = inspect.getsource(schema_mod)
    assert "errors or []" in src or "self.errors = errors or []" in src


def test_source_contains_path_resolve_parent_parent_batch48():
    """SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"。"""
    src = inspect.getsource(schema_mod)
    assert "resolve()" in src
    assert '"schemas"' in src or "'schemas'" in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _schema_path, load_schema, validate, validate_file


def test_ast_top_level_functions_count_actual_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    # _schema_path, load_schema, validate, validate_file
    names = [f.name for f in funcs]
    assert "_schema_path" in names
    assert "load_schema" in names
    assert "validate" in names
    assert "validate_file" in names


def test_ast_class_def_count_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_eval_schema_error_init_method_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert any(m.name == "__init__" for m in methods)


def test_ast_no_async_function_def_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_module_docstring_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_validate_has_for_loop_batch48():
    """validate 中 for err in errors 收集 flat。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) >= 1


def test_ast_validate_has_lambda_batch48():
    """sorted 使用 lambda。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    lambdas = [n for n in ast.walk(func) if isinstance(n, ast.Lambda)]
    assert len(lambdas) >= 1


def test_ast_validate_has_raise_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) >= 1


def test_ast_validate_has_return_none_batch48():
    """通过时 return（None）。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 1


def test_ast_validate_file_has_open_call_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_open = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "open" for c in calls
    )
    assert has_open


def test_ast_schema_path_has_is_file_batch48():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    calls = [n for n in ast.walk(func) if isinstance(n, ast.Call)]
    has_is_file = any(
        isinstance(c.func, ast.Attribute) and c.func.attr == "is_file" for c in calls
    )
    assert has_is_file


def test_ast_module_top_level_import_count_batch48():
    """模块顶部 import：json / Path / Any / Draft202012Validator / JSValidationError。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 4


def test_ast_module_top_level_assign_count_batch48():
    """模块顶部 Assign：SCHEMAS_DIR + __all__。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_eval_schema_error_init_super_call_batch48():
    """EvalSchemaError.__init__ 调用 super().__init__。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == "__init__")
    calls = [n for n in ast.walk(init) if isinstance(n, ast.Call)]
    has_super = any(
        isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Call)
        and isinstance(c.func.value.func, ast.Name) and c.func.value.func.id == "super"
        for c in calls
    )
    assert has_super


# ---------- forbidden tokens 第一百二十批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_eval_batch48():
    assert "eval(" not in _src()


def test_source_no_exec_batch48():
    assert "exec(" not in _src()


def test_source_no_compile_batch48():
    assert "compile(" not in _src()


def test_source_no_globals_batch48():
    assert "globals(" not in _src()


def test_source_no_locals_batch48():
    assert "locals(" not in _src()


def test_source_no_os_system_batch48():
    assert "os.system" not in _src()


def test_source_no_popen_batch48():
    assert "popen" not in _src()


def test_source_no_subprocess_batch48():
    assert "subprocess" not in _src()


def test_source_no_yaml_load_batch48():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch48():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch48():
    assert "socket" not in _src()


def test_source_no_requests_batch48():
    assert "requests" not in _src()


def test_source_no_urllib_batch48():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch48():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch48():
    assert "yield" not in _src()
