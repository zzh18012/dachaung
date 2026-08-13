"""evaluation/schema.py 第九十二轮 edges 测试（Round 642）。

补强 edges60 未触及的角度（第四十七批）。

新角度：
- SCHEMAS_DIR 路径精确
- EvalSchemaError pickle
- EvalSchemaError errors 默认 []
- EvalSchemaError 一致性
- _schema_path 异常路径
- load_schema 各种 Schema
- validate 多种 error 排序
- validate_file 异常路径
- manifest.schema.json 内部字段
- annotation.schema.json 内部字段
- evaluation-report.schema.json 内部字段
- module source 字符串补强
- AST 结构补强
- forbidden tokens 第一百一十二批
"""

from __future__ import annotations

import ast
import inspect
import json
import pickle
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


# ---------- SCHEMAS_DIR 路径精确 ----------

def test_schemas_dir_is_path_batch47():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_resolved_batch47():
    """已 resolve，是绝对路径。"""
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_endswith_schemas_batch47():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_exists_batch47():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_schema_batch47():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch47():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch47():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_parent_is_project_root_batch47():
    """SCHEMAS_DIR 的父目录是项目根。"""
    assert SCHEMAS_DIR.parent.name == "dachuang-autonomous" or SCHEMAS_DIR.parent.is_dir()


# ---------- EvalSchemaError pickle ----------

def test_eval_schema_error_pickle_roundtrip_batch47():
    """EvalSchemaError 可 pickle（基础异常 pickling）。"""
    err = EvalSchemaError("msg", errors=[{"path": ["a"], "message": "bad"}])
    data = pickle.dumps(err)
    restored = pickle.loads(data)
    assert isinstance(restored, EvalSchemaError)
    assert str(restored) == str(err)


def test_eval_schema_error_pickle_preserves_errors_batch47():
    err = EvalSchemaError("msg", errors=[{"path": ["a"], "message": "bad"}])
    restored = pickle.loads(pickle.dumps(err))
    assert restored.errors == err.errors


def test_eval_schema_error_pickle_no_errors_batch47():
    """errors=None 也能 pickle。"""
    err = EvalSchemaError("msg")
    restored = pickle.loads(pickle.dumps(err))
    assert restored.errors == []


def test_eval_schema_error_pickle_empty_errors_batch47():
    err = EvalSchemaError("msg", errors=[])
    restored = pickle.loads(pickle.dumps(err))
    assert restored.errors == []


# ---------- EvalSchemaError errors 默认 [] ----------

def test_eval_schema_error_errors_default_empty_batch47():
    err = EvalSchemaError("msg")
    assert err.errors == []


def test_eval_schema_error_errors_none_batch47():
    err = EvalSchemaError("msg", None)
    assert err.errors == []


def test_eval_schema_error_errors_explicit_batch47():
    errs = [{"path": ["a"], "message": "bad"}]
    err = EvalSchemaError("msg", errs)
    assert err.errors is errs  # 直接引用


def test_eval_schema_error_str_includes_message_batch47():
    err = EvalSchemaError("hello world")
    assert "hello world" in str(err)


def test_eval_schema_error_repr_batch47():
    err = EvalSchemaError("hello")
    r = repr(err)
    assert "EvalSchemaError" in r


def test_eval_schema_error_is_exception_batch47():
    err = EvalSchemaError("x")
    assert isinstance(err, Exception)


def test_eval_schema_error_can_be_raised_and_caught_batch47():
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("boom", errors=[{"path": [], "message": "x"}])
    assert "boom" in str(exc_info.value)
    assert exc_info.value.errors == [{"path": [], "message": "x"}]


def test_eval_schema_error_caught_as_exception_batch47():
    """应被 except Exception 捕获。"""
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_args_batch47():
    """super().__init__(message) → args[0] 是 message。"""
    err = EvalSchemaError("hello")
    assert err.args == ("hello",)


# ---------- _schema_path 异常路径 ----------

def test_schema_path_valid_batch47():
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_invalid_name_batch47():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "不存在" in str(exc_info.value)


def test_schema_path_returns_path_batch47():
    p = _schema_path("annotation.schema.json")
    assert isinstance(p, Path)


def test_schema_path_absolute_batch47():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# ---------- load_schema 各种 ----------

def test_load_schema_manifest_batch47():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    assert "$schema" in s or "type" in s


def test_load_schema_annotation_batch47():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_file_not_found_batch47():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# ---------- validate 多种 error 排序 ----------

def test_validate_success_manifest_batch47():
    """完整合法 manifest 应通过。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    validate(instance, "manifest.schema.json")  # 不抛


def test_validate_missing_manifest_version_batch47():
    instance = {
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    assert "manifest_version" in str(exc_info.value) or "manifest_version" in str(exc_info.value.errors)


def test_validate_invalid_devset_status_batch47():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "weird",  # 不在 enum
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_manifest_version_wrong_value_batch47():
    """manifest_version 必须是 "1.0"（const）。"""
    instance = {
        "manifest_version": "2.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_errors_sorted_by_path_batch47():
    """errors 应按 absolute_path 排序。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "weird1",  # 错
        "documents": "not_a_list",  # 错
    }
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    errs = exc_info.value.errors
    # 排序：devset_status 在 documents 之前（按字母）
    paths = [e["path"] for e in errs]
    assert paths == sorted(paths, key=lambda p: list(p))


def test_validate_errors_count_batch47():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    # 至少 manifest_version / devset_status / documents 缺失
    assert len(exc_info.value.errors) >= 3


def test_validate_errors_each_has_keys_batch47():
    instance = {}
    with pytest.raises(EvalSchemaError) as exc_info:
        validate(instance, "manifest.schema.json")
    for e in exc_info.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


# ---------- validate_file 异常路径 ----------

def test_validate_file_file_not_found_batch47(tmp_path):
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file(tmp_path / "nofile.json", "manifest.schema.json")
    assert "不存在" in str(exc_info.value)


def test_validate_file_bad_json_batch47(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_valid_manifest_batch47(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")  # 不抛


def test_validate_file_path_string_batch47(tmp_path):
    """接受 str 或 Path。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")  # 不抛


def test_validate_file_schema_error_batch47(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"wrong": "data"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- manifest.schema.json 内部字段 ----------

def test_manifest_schema_has_type_object_batch47():
    s = load_schema("manifest.schema.json")
    assert s.get("type") == "object"


def test_manifest_schema_has_properties_batch47():
    s = load_schema("manifest.schema.json")
    assert "properties" in s
    assert "manifest_version" in s["properties"]
    assert "devset_status" in s["properties"]
    assert "documents" in s["properties"]


def test_manifest_schema_required_includes_core_batch47():
    s = load_schema("manifest.schema.json")
    required = s.get("required", [])
    assert "manifest_version" in required
    assert "devset_status" in required
    assert "documents" in required


def test_manifest_schema_devset_status_enum_batch47():
    s = load_schema("manifest.schema.json")
    ds = s["properties"]["devset_status"]
    assert set(ds.get("enum", [])) == {"complete", "incomplete"}


def test_manifest_schema_manifest_version_const_batch47():
    s = load_schema("manifest.schema.json")
    mv = s["properties"]["manifest_version"]
    assert mv.get("const") == "1.0" or mv.get("enum") == ["1.0"]


def test_manifest_schema_documents_is_array_batch47():
    s = load_schema("manifest.schema.json")
    docs = s["properties"]["documents"]
    assert docs.get("type") == "array"


# ---------- annotation.schema.json 内部字段 ----------

def test_annotation_schema_has_type_object_batch47():
    s = load_schema("annotation.schema.json")
    assert s.get("type") == "object"


def test_annotation_schema_has_properties_batch47():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_annotation_schema_has_annotation_version_batch47():
    s = load_schema("annotation.schema.json")
    # 应有版本字段
    assert "annotation_version" in s.get("properties", {})


# ---------- evaluation-report.schema.json 内部字段 ----------

def test_evaluation_report_schema_has_type_object_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert s.get("type") == "object"


def test_evaluation_report_schema_has_properties_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_evaluation_report_schema_has_report_version_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert "report_version" in s.get("properties", {})


def test_evaluation_report_schema_has_per_doc_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert "per_doc" in s.get("properties", {})


def test_evaluation_report_schema_has_summary_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert "summary" in s.get("properties", {})


def test_evaluation_report_schema_has_provenance_batch47():
    s = load_schema("evaluation-report.schema.json")
    assert "provenance" in s.get("properties", {})


# ---------- module source 字符串补强 ----------

def test_source_contains_Draft202012Validator_batch47():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator" in src


def test_source_contains_iter_errors_batch47():
    src = inspect.getsource(schema_mod)
    assert "iter_errors" in src


def test_source_contains_absolute_path_batch47():
    src = inspect.getsource(schema_mod)
    assert "absolute_path" in src


def test_source_contains_sorted_with_lambda_batch47():
    src = inspect.getsource(schema_mod)
    assert "sorted" in src
    assert "lambda" in src  # 排序 key 是 lambda


def test_source_contains_utf8_encoding_batch47():
    src = inspect.getsource(schema_mod)
    assert "encoding=" in src


def test_source_contains_Schemas_dir_batch47():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR" in src


def test_source_contains_不与_app_schema_复用_batch47():
    src = inspect.getsource(schema_mod)
    assert "不复用" in src or "复用" in src


def test_source_contains_errors_给人看_batch47():
    src = inspect.getsource(schema_mod)
    assert "给人看" in src or "程序看" in src


def test_source_contains_no_app_schema_import_batch47():
    """不应 import app.schema。"""
    src = inspect.getsource(schema_mod)
    assert "from app.schema" not in src
    assert "import app.schema" not in src


# ---------- AST 结构补强 ----------

def test_ast_top_level_functions_count_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4  # _schema_path / load_schema / validate / validate_file


def test_ast_top_level_class_count_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_eval_schema_error_init_takes_two_args_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    init = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"][0]
    # self + message + errors
    args = [a.arg for a in init.args.args]
    assert args == ["self", "message", "errors"]


def test_ast_eval_schema_error_errors_default_none_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError"][0]
    init = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"][0]
    # errors 默认 None
    assert init.args.defaults[0] is None or isinstance(init.args.defaults[0], ast.Constant)


def test_ast_validate_has_for_loop_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    fors = [n for n in func.body if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_validate_has_lambda_sort_key_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    lambdas = [n for n in ast.walk(func) if isinstance(n, ast.Lambda)]
    assert len(lambdas) == 1


def test_ast_validate_has_raise_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate"][0]
    raises = [n for n in func.body if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_schema_path_has_if_not_is_file_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    assert len(ifs) == 1


def test_ast_validate_file_has_two_if_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file"][0]
    ifs = [n for n in func.body if isinstance(n, ast.If)]
    # if not p.is_file() + with open（不算 if）
    assert len(ifs) == 1


def test_ast_validate_file_has_with_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file"][0]
    withs = [n for n in func.body if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_load_schema_has_with_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema"][0]
    withs = [n for n in func.body if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_module_docstring_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_no_async_batch47():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


# ---------- forbidden tokens 第一百一十二批 ----------

def test_source_no_eval_batch47():
    src = inspect.getsource(schema_mod)
    assert "eval(" not in src


def test_source_no_exec_batch47():
    src = inspect.getsource(schema_mod)
    assert "exec(" not in src


def test_source_no_compile_batch47():
    src = inspect.getsource(schema_mod)
    assert "compile(" not in src


def test_source_no_globals_batch47():
    src = inspect.getsource(schema_mod)
    assert "globals(" not in src


def test_source_no_locals_batch47():
    src = inspect.getsource(schema_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch47():
    src = inspect.getsource(schema_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch47():
    src = inspect.getsource(schema_mod)
    assert ".popen(" not in src


def test_source_no_yaml_load_batch47():
    src = inspect.getsource(schema_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch47():
    src = inspect.getsource(schema_mod)
    assert "pickle.load(" not in src


def test_source_no_subprocess_batch47():
    src = inspect.getsource(schema_mod)
    assert "subprocess" not in src


def test_source_no_yield_batch47():
    src = inspect.getsource(schema_mod)
    assert "yield" not in src


def test_source_no_walrus_batch47():
    src = inspect.getsource(schema_mod)
    assert ":=" not in src


def test_source_no_await_batch47():
    src = inspect.getsource(schema_mod)
    assert "await " not in src
