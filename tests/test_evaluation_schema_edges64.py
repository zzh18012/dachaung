"""evaluation/schema.py 第九十五轮 edges 测试（Round 666）。

补强 edges63 未触及的角度（第五十批）。

新角度：
- EvalSchemaError 多层继承验证（isinstance Exception / BaseException / object）
- EvalSchemaError raise from inside try/except（异常链）
- _schema_path 多 schema 文件存在校验
- _schema_path 错误 message 含 path
- load_schema 返回 dict 的 keys 类型
- load_schema 各 schema 的 required 字段（manifest 3 个 / annotation 2 个）
- validate 多 errors 排序后顺序稳定（多次调用同样顺序）
- validate 错误信息含 schema_path（每个 err）
- validate_file 不同 schema name 校验路径
- validate_file 多层错误传递（FileNotFoundError → JSONDecodeError → EvalSchemaError）
- SCHEMAS_DIR 在项目根的 schemas 子目录
- 模块源码补强（jsonschema Draft202012Validator 调用 / iter_errors / sorted / __future__ / pathlib / typing.Any）
- AST 结构补强（4 函数 / 1 ClassDef / EvalSchemaError __init__ 调 super / validate 1 for + 1 sorted + flat.append / validate_file 1 with + validate_file 调 validate / _schema_path 1 if）
- forbidden tokens 第一百三十六批
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


# ---------- EvalSchemaError 多层继承验证 ----------

def test_eval_schema_error_is_base_exception_batch50():
    e = EvalSchemaError("x")
    assert isinstance(e, BaseException)


def test_eval_schema_error_is_object_batch50():
    """所有 Python 对象都是 object 子类。"""
    e = EvalSchemaError("x")
    assert isinstance(e, object)


def test_eval_schema_error_can_chain_from_other_batch50():
    """raise from 用于异常链。"""
    try:
        try:
            raise ValueError("original")
        except ValueError as ve:
            raise EvalSchemaError("wrapped") from ve
    except EvalSchemaError as e:
        assert e.__cause__ is not None
        assert isinstance(e.__cause__, ValueError)
        assert str(e.__cause__) == "original"


def test_eval_schema_error_can_reraise_batch50():
    """raise 后再 raise 同一个实例。"""
    e = EvalSchemaError("test")
    try:
        raise e
    except EvalSchemaError as caught:
        assert caught is e


# ---------- _schema_path 多 schema 文件存在校验 ----------

def test_schema_path_all_schemas_exist_batch50():
    """3 个 schema 文件都存在。"""
    for name in ["manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"]:
        p = _schema_path(name)
        assert p.is_file()


def test_schema_path_missing_error_message_contains_path_batch50():
    """错误 message 含完整 path。"""
    fake_name = "definitely_nonexistent.schema.json"
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path(fake_name)
    assert fake_name in str(ei.value)
    assert "Schema 文件不存在" in str(ei.value)


def test_schema_path_trailing_dot_batch50():
    """文件名带点也能正常处理。"""
    p = _schema_path("manifest.schema.json")
    assert p.suffix == ".json"


# ---------- load_schema 返回 dict 的 keys 类型 ----------

def test_load_schema_returns_dict_with_type_key_batch50():
    """JSON Schema 顶层 dict 有 'type' 或 'properties' 或 '$schema' key。"""
    s = load_schema("manifest.schema.json")
    assert "type" in s or "properties" in s or "$schema" in s


def test_load_schema_manifest_has_required_batch50():
    s = load_schema("manifest.schema.json")
    assert "required" in s
    required = s["required"]
    assert "manifest_version" in required
    assert "devset_status" in required
    assert "documents" in required


def test_load_schema_annotation_has_required_batch50():
    s = load_schema("annotation.schema.json")
    assert "required" in s
    required = s["required"]
    assert "annotation_version" in required
    assert "doc_id" in required


def test_load_schema_evaluation_report_has_required_batch50():
    s = load_schema("evaluation-report.schema.json")
    assert "required" in s


# ---------- validate 多 errors 排序后顺序稳定 ----------

def test_validate_same_input_same_order_batch50():
    """相同 instance 多次校验给出相同顺序 errors。"""
    instance = {"manifest_version": "wrong", "documents": "wrong_type"}
    err1 = None
    err2 = None
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        err1 = [tuple(err["path"]) for err in e.errors]
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        err2 = [tuple(err["path"]) for err in e.errors]
    assert err1 == err2


def test_validate_errors_each_has_schema_path_batch50():
    """每个 error 含非空 schema_path。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["schema_path"], list)
            assert len(err["schema_path"]) > 0
        return
    pytest.fail("should have raised")


def test_validate_errors_path_is_list_of_str_or_int_batch50():
    """path 元素是 str（属性名）或 int（数组索引）。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            for p in err["path"]:
                assert isinstance(p, (str, int))
        return
    pytest.fail("should have raised")


def test_validate_head_error_path_in_errors_list_batch50():
    """head error（用于 message）一定在 errors list 中。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        head_msg = str(e)
        # message 含 head.message，head.path
        # head.path 在 errors list 第一个的 path（因为 sorted）
        first_path = e.errors[0]["path"]
        assert f"path={first_path}" in head_msg or "path=[]" in head_msg
        return
    pytest.fail("should have raised")


# ---------- validate_file 不同 schema name 校验路径 ----------

def test_validate_file_with_annotation_schema_batch50(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(
        json.dumps({"annotation_version": "1.0", "doc_id": "d1"}),
        encoding="utf-8",
    )
    out = validate_file(f, "annotation.schema.json")
    assert out is None


def test_validate_file_annotation_invalid_batch50(tmp_path):
    f = tmp_path / "ann.json"
    f.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f, "annotation.schema.json")


def test_validate_file_evaluation_report_schema_batch50(tmp_path):
    f = tmp_path / "report.json"
    f.write_text(
        json.dumps(
            {
                "report_version": "1.1",
                "provenance": {
                    "git_commit": "abc",
                    "git_dirty": False,
                    "evaluator_version": "1.1",
                    "report_version": "1.1",
                    "parser_name": "fallback",
                    "parser_version": None,
                    "dependencies": {},
                    "max_chars": 800,
                    "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
                },
                "devset": {
                    "status": "complete",
                    "file_count": 0,
                    "content_group_count": 0,
                    "pdf_count": 0,
                    "docx_count": 0,
                    "categories_covered": [],
                },
                "summary": {},
                "per_doc": [],
                "expected_failures": [],
            }
        ),
        encoding="utf-8",
    )
    out = validate_file(f, "evaluation-report.schema.json")
    assert out is None


def test_validate_file_evaluation_report_missing_required_batch50(tmp_path):
    """evaluation-report schema 缺 required 字段。"""
    f = tmp_path / "report.json"
    f.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f, "evaluation-report.schema.json")


def test_validate_file_propagates_correct_exception_batch50(tmp_path):
    """不同失败模式给出不同异常。"""
    # FileNotFoundError
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.json", "manifest.schema.json")
    # JSONDecodeError
    f = tmp_path / "bad.json"
    f.write_text("{not", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")
    # EvalSchemaError
    f2 = tmp_path / "bad_schema.json"
    f2.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f2, "manifest.schema.json")


# ---------- SCHEMAS_DIR 在项目根的 schemas 子目录 ----------

def test_schemas_dir_name_is_schemas_batch50():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_only_json_files_batch50():
    for child in SCHEMAS_DIR.iterdir():
        assert child.suffix == ".json"


def test_schemas_dir_has_at_least_3_files_batch50():
    files = list(SCHEMAS_DIR.iterdir())
    assert len([f for f in files if f.is_file()]) >= 3


# ---------- 模块源码补强 ----------

def test_source_contains_draft202012_validator_call_batch50():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator(" in src


def test_source_contains_iter_errors_call_batch50():
    src = inspect.getsource(schema_mod)
    assert ".iter_errors(" in src


def test_source_contains_sorted_with_lambda_batch50():
    src = inspect.getsource(schema_mod)
    assert "sorted(" in src
    assert "lambda" in src


def test_source_contains_absolute_path_calls_batch50():
    src = inspect.getsource(schema_mod)
    assert "absolute_path" in src
    assert "absolute_schema_path" in src


def test_source_contains_jsonschema_module_batch50():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src
    assert "from jsonschema.exceptions import ValidationError" in src


def test_source_no_extra_jsonschema_imports_batch50():
    """不引入 jsonschema.validators 或其他子模块。"""
    src = inspect.getsource(schema_mod)
    assert "jsonschema.validators" not in src
    assert "jsonschema.draft" not in src


def test_source_eval_schema_error_docstring_batch50():
    src = inspect.getsource(schema_mod)
    assert "errors 给程序看" in src or "errors 给" in src
    assert "message 给人看" in src or "message 给" in src


def test_source_validate_docstring_mentions_eval_schema_error_batch50():
    src = inspect.getsource(schema_mod)
    assert "EvalSchemaError" in src


def test_source_validate_file_docstring_batch50():
    src = inspect.getsource(schema_mod)
    # validate_file 的 docstring
    assert "校验" in src


def test_source_load_schema_docstring_batch50():
    src = inspect.getsource(schema_mod)
    assert "schemas/" in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_top_level_functions_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_function_names_order_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_schema_path", "load_schema", "validate", "validate_file"]


def test_ast_eval_schema_error_class_has_init_only_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 1
    assert methods[0].name == "__init__"


def test_ast_eval_schema_error_init_calls_super_with_message_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "super().__init__(message)" in src


def test_ast_eval_schema_error_init_has_self_errors_assign_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "self.errors = errors or []" in src


def test_ast_validate_has_for_loop_with_append_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "for err in errors:" in src
    assert "flat.append" in src


def test_ast_validate_uses_sorted_with_key_lambda_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    # 找 sorted call
    sorted_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(sorted_calls) == 1
    # 第一个 arg 是 iter_errors 调用
    assert len(sorted_calls[0].args) == 1
    # key 关键字是 lambda
    assert len(sorted_calls[0].keywords) == 1
    assert sorted_calls[0].keywords[0].arg == "key"
    assert isinstance(sorted_calls[0].keywords[0].value, ast.Lambda)


def test_ast_validate_has_head_assignment_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "head = errors[0]" in src


def test_ast_validate_raises_eval_schema_error_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_validate_has_return_none_when_no_errors_batch50():
    """errors 空 → return（None）。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    # 用 ast.walk 找所有 return（包括嵌套在 if 中的）
    returns = [n for n in ast.walk(func) if isinstance(n, ast.Return)]
    assert len(returns) >= 1


def test_ast_validate_file_has_with_open_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_validate_file_calls_validate_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "validate(data, schema_name)" in src


def test_ast_validate_file_has_if_not_is_file_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "if not p.is_file()" in src


def test_ast_schema_path_has_if_not_is_file_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    src = ast.unparse(func)
    assert "if not p.is_file()" in src


def test_ast_schema_path_raises_filenotfounderror_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_module_has_6_imports_batch50():
    """6 个 import：__future__ + json + Path + Any + Draft202012Validator + JSValidationError。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6


def test_ast_module_has_2_top_level_assigns_batch50():
    """SCHEMAS_DIR + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_no_class_def_other_than_eval_schema_error_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_no_async_function_def_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_no_global_statement_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.Global) for n in ast.walk(tree))


def test_ast_no_nonlocal_statement_batch50():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.Nonlocal) for n in ast.walk(tree))


# ---------- forbidden tokens 第一百三十六批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_eval_batch50():
    assert "eval(" not in _src()


def test_source_no_exec_batch50():
    assert "exec(" not in _src()


def test_source_no_compile_batch50():
    assert "compile(" not in _src()


def test_source_no_globals_batch50():
    assert "globals(" not in _src()


def test_source_no_locals_batch50():
    assert "locals(" not in _src()


def test_source_no_os_system_batch50():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch50():
    assert "subprocess" not in _src()


def test_source_no_popen_batch50():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch50():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch50():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch50():
    assert "socket" not in _src()


def test_source_no_requests_batch50():
    assert "requests" not in _src()


def test_source_no_urllib_batch50():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch50():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch50():
    assert "yield" not in _src()


def test_source_open_count_is_2_batch50():
    """load_schema 1 个 + validate_file 1 个 = 2 个 open。"""
    assert _src().count("open(") == 2


def test_source_no_async_await_batch50():
    """schema.py 不使用 async/await。"""
    assert "async " not in _src()
    assert "await " not in _src()
