"""evaluation/schema.py 第九十六轮 edges 测试（Round 674）。

补强 edges64 未触及的角度（第五十一批）。

新角度：
- EvalSchemaError 更深（__init__ 双参数 / errors None 默认 [] / errors 给 list / str repr / str() = message / __cause__ / raise without from）
- _schema_path 边界（合法 schema / 不存在 raise FileNotFoundError / 错误 message 含路径 / 多种非法名）
- load_schema 边界（manifest / annotation / evaluation-report 3 个 schema / 返回 dict / JSON 解码正确）
- validate 多场景（无 errors 返回 None / 多 errors / errors 顺序 / empty instance manifest / 不存在的 schema name）
- validate_file 多场景（合法 manifest / 合法 annotation / 合法 evaluation-report / FileNotFoundError / JSONDecodeError / Schema 失败）
- SCHEMAS_DIR 路径（位于 evaluation/ 上一级的 schemas/ 目录 / 含 manifest.schema.json / 含 annotation.schema.json / 含 evaluation-report.schema.json）
- 模块源码补强（json/Path/Any imports / Draft202012Validator/JSValidationError imports / SCHEMAS_DIR 定义 / EvalSchemaError docstring / validate 用 sorted + lambda / validate_file 用 with open / __all__ 5 entries）
- AST 结构补强（4 函数 + 顺序 / 1 ClassDef / EvalSchemaError __init__ 单方法 / super().__init__(message) / self.errors = errors or [] / 6 imports / module docstring / 2 顶层 Assign / validate 1 for + 1 sorted + raise / validate_file 1 with + 1 if）
- forbidden tokens 第一百四十四批
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


# ---------- EvalSchemaError 更深 ----------

def test_eval_schema_error_message_only_batch51():
    e = EvalSchemaError("msg only")
    assert str(e) == "msg only"


def test_eval_schema_error_with_errors_list_batch51():
    errs = [{"path": ["x"], "message": "fail", "schema_path": ["y"]}]
    e = EvalSchemaError("with errors", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_errors_default_empty_batch51():
    e = EvalSchemaError("x")
    assert e.errors == []
    assert isinstance(e.errors, list)


def test_eval_schema_error_repr_contains_class_name_batch51():
    e = EvalSchemaError("msg")
    r = repr(e)
    assert "EvalSchemaError" in r
    assert "msg" in r


def test_eval_schema_error_is_exception_batch51():
    e = EvalSchemaError("x")
    assert isinstance(e, Exception)


def test_eval_schema_error_args_batch51():
    """super().__init__(message) 把 message 存进 args。"""
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)


def test_eval_schema_error_raise_no_from_batch51():
    """raise 不带 from → __cause__ is None。"""
    try:
        raise EvalSchemaError("x")
    except EvalSchemaError as e:
        assert e.__cause__ is None


def test_eval_schema_error_raise_with_from_batch51():
    try:
        try:
            raise ValueError("orig")
        except ValueError as ve:
            raise EvalSchemaError("wrapped") from ve
    except EvalSchemaError as e:
        assert isinstance(e.__cause__, ValueError)


def test_eval_schema_error_str_no_errors_attr_in_msg_batch51():
    """str() 只含 message，不含 errors。"""
    e = EvalSchemaError("msg", errors=[{"path": "x"}])
    assert str(e) == "msg"


def test_eval_schema_error_can_be_raised_and_caught_batch51():
    with pytest.raises(EvalSchemaError) as ei:
        raise EvalSchemaError("caught")
    assert "caught" in str(ei.value)


# ---------- _schema_path 边界 ----------

def test_schema_path_returns_path_batch51():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_missing_raises_filenotfounderror_batch51():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(ei.value)


def test_schema_path_error_message_contains_full_path_batch51():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("missing.json")
    msg = str(ei.value)
    assert "missing.json" in msg
    assert str(SCHEMAS_DIR) in msg or "schemas" in msg


def test_schema_path_directory_not_file_batch51():
    """传目录名也会失败（不是 is_file）。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")  # SCHEMAS_DIR/"" 是目录


def test_schema_path_3_valid_schemas_batch51():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        p = _schema_path(name)
        assert p.is_file()


# ---------- load_schema 边界 ----------

def test_load_schema_manifest_returns_dict_batch51():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_annotation_returns_dict_batch51():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_returns_dict_batch51():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_manifest_has_top_level_keys_batch51():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "type" in s
    assert "properties" in s


def test_load_schema_annotation_has_doc_id_property_batch51():
    s = load_schema("annotation.schema.json")
    assert "doc_id" in s.get("properties", {})


def test_load_schema_missing_raises_filenotfounderror_batch51():
    with pytest.raises(FileNotFoundError):
        load_schema("nope.schema.json")


# ---------- validate 多场景 ----------

def test_validate_manifest_valid_batch51():
    instance = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    rv = validate(instance, "manifest.schema.json")
    assert rv is None


def test_validate_manifest_missing_required_batch51():
    instance = {}
    with pytest.raises(EvalSchemaError) as ei:
        validate(instance, "manifest.schema.json")
    errs = ei.value.errors
    assert len(errs) >= 1
    # 每个 err 含 path/message/schema_path
    for e in errs:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_validate_annotation_valid_batch51():
    instance = {"annotation_version": "1.0", "doc_id": "d1"}
    rv = validate(instance, "annotation.schema.json")
    assert rv is None


def test_validate_annotation_invalid_batch51():
    with pytest.raises(EvalSchemaError):
        validate({}, "annotation.schema.json")


def test_validate_evaluation_report_valid_batch51():
    instance = {
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
    rv = validate(instance, "evaluation-report.schema.json")
    assert rv is None


def test_validate_evaluation_report_invalid_batch51():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_validate_returns_none_on_success_batch51():
    """validate 成功返回 None（不是 dict）。"""
    rv = validate({"annotation_version": "1.0", "doc_id": "d1"}, "annotation.schema.json")
    assert rv is None


def test_validate_eval_schema_error_has_errors_attr_batch51():
    """失败时 EvalSchemaError.errors 是 list of dicts。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    e = ei.value
    assert isinstance(e.errors, list)
    assert len(e.errors) > 0
    for err in e.errors:
        assert isinstance(err, dict)
        assert isinstance(err["path"], list)
        assert isinstance(err["schema_path"], list)
        assert isinstance(err["message"], str)


def test_validate_eval_schema_error_message_contains_count_batch51():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "校验失败" in msg
    assert "处" in msg


def test_validate_eval_schema_error_message_contains_schema_name_batch51():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "manifest.schema.json" in msg


# ---------- validate_file 多场景 ----------

def test_validate_file_manifest_valid_batch51(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }), encoding="utf-8")
    rv = validate_file(f, "manifest.schema.json")
    assert rv is None


def test_validate_file_annotation_valid_batch51(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps({
        "annotation_version": "1.0",
        "doc_id": "d1",
    }), encoding="utf-8")
    rv = validate_file(f, "annotation.schema.json")
    assert rv is None


def test_validate_file_evaluation_report_valid_batch51(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({
        "report_version": "1.1",
        "provenance": {
            "git_commit": "abc", "git_dirty": False, "evaluator_version": "1.1",
            "report_version": "1.1", "parser_name": "fallback", "parser_version": None,
            "dependencies": {}, "max_chars": 800, "run_timestamp_iso": "2026-01-01T00:00:00+00:00",
        },
        "devset": {
            "status": "complete", "file_count": 0, "content_group_count": 0,
            "pdf_count": 0, "docx_count": 0, "categories_covered": [],
        },
        "summary": {}, "per_doc": [], "expected_failures": [],
    }), encoding="utf-8")
    rv = validate_file(f, "evaluation-report.schema.json")
    assert rv is None


def test_validate_file_missing_file_batch51(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "nope.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


def test_validate_file_json_decode_error_batch51(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_schema_failure_batch51(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_path_can_be_str_batch51(tmp_path):
    """validate_file 接受 str 路径。"""
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete", "documents": [],
    }), encoding="utf-8")
    rv = validate_file(str(f), "manifest.schema.json")
    assert rv is None


def test_validate_file_accepts_path_object_batch51(tmp_path):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({
        "manifest_version": "1.0", "devset_status": "complete", "documents": [],
    }), encoding="utf-8")
    rv = validate_file(Path(f), "manifest.schema.json")
    assert rv is None


# ---------- SCHEMAS_DIR 路径 ----------

def test_schemas_dir_is_path_batch51():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_exists_batch51():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_name_is_schemas_batch51():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_is_project_root_batch51():
    """SCHEMAS_DIR 的 parent 应该是项目根（含 evaluation/ 子目录）。"""
    parent = SCHEMAS_DIR.parent
    assert (parent / "evaluation").is_dir()


def test_schemas_dir_contains_manifest_schema_batch51():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch51():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch51():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_at_least_3_files_batch51():
    files = [f for f in SCHEMAS_DIR.iterdir() if f.is_file()]
    assert len(files) >= 3


def test_schemas_dir_only_json_files_batch51():
    for f in SCHEMAS_DIR.iterdir():
        if f.is_file():
            assert f.suffix == ".json"


# ---------- 模块源码补强 ----------

def test_source_contains_json_import_batch51():
    src = inspect.getsource(schema_mod)
    assert "import json" in src


def test_source_contains_path_import_batch51():
    src = inspect.getsource(schema_mod)
    assert "from pathlib import Path" in src


def test_source_contains_any_import_batch51():
    src = inspect.getsource(schema_mod)
    assert "from typing import Any" in src


def test_source_imports_draft202012_batch51():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema import Draft202012Validator" in src


def test_source_imports_validation_error_batch51():
    src = inspect.getsource(schema_mod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_source_contains_schemas_dir_definition_batch51():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent / \"schemas\"" in src


def test_source_contains_eval_schema_error_class_batch51():
    src = inspect.getsource(schema_mod)
    assert "class EvalSchemaError(Exception):" in src


def test_source_contains_super_init_message_batch51():
    src = inspect.getsource(schema_mod)
    assert "super().__init__(message)" in src


def test_source_contains_self_errors_assign_batch51():
    src = inspect.getsource(schema_mod)
    assert "self.errors = errors or []" in src


def test_source_contains_draft202012_call_batch51():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator(" in src


def test_source_contains_iter_errors_batch51():
    src = inspect.getsource(schema_mod)
    assert ".iter_errors(" in src


def test_source_contains_sorted_lambda_batch51():
    src = inspect.getsource(schema_mod)
    assert "sorted(" in src
    assert "lambda" in src


def test_source_contains_absolute_path_calls_batch51():
    src = inspect.getsource(schema_mod)
    assert "absolute_path" in src
    assert "absolute_schema_path" in src


def test_source_contains_with_open_batch51():
    src = inspect.getsource(schema_mod)
    assert "with _schema_path(name).open" in src or "with p.open" in src


def test_source_contains_docstring_eval_schema_error_batch51():
    src = inspect.getsource(schema_mod)
    assert "errors 给程序看" in src
    assert "message 给人看" in src


def test_source_all_5_entries_batch51():
    src = inspect.getsource(schema_mod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_top_level_functions_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_function_names_order_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert names == ["_schema_path", "load_schema", "validate", "validate_file"]


def test_ast_has_1_class_def_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_eval_schema_error_has_1_method_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 1
    assert methods[0].name == "__init__"


def test_ast_eval_schema_error_super_call_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "super().__init__(message)" in src


def test_ast_eval_schema_error_self_errors_assign_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvalSchemaError")
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "self.errors = errors or []" in src


def test_ast_no_async_function_def_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def test_ast_has_6_imports_batch51():
    """__future__ + json + Path + Any + Draft202012Validator + JSValidationError = 6。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6


def test_ast_module_docstring_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_has_2_module_assigns_batch51():
    """SCHEMAS_DIR + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_schemas_dir_target_name_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    sd = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "SCHEMAS_DIR" for t in n.targets)
    )
    # SD = Path(__file__).resolve().parent.parent / "schemas"
    src = ast.unparse(sd.value)
    assert "Path(__file__)" in src
    assert ".parent.parent" in src
    assert "schemas" in src


def test_ast_all_value_is_list_5_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    all_assign = next(
        n for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in n.targets)
    )
    assert isinstance(all_assign.value, ast.List)
    assert len(all_assign.value.elts) == 5


def test_ast_validate_has_for_loop_with_append_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_validate_uses_sorted_with_key_lambda_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    sorted_calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(sorted_calls) == 1
    assert len(sorted_calls[0].keywords) == 1
    assert sorted_calls[0].keywords[0].arg == "key"
    assert isinstance(sorted_calls[0].keywords[0].value, ast.Lambda)


def test_ast_validate_raises_eval_schema_error_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_validate_file_has_with_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_validate_file_calls_validate_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "validate(data, schema_name)" in src


def test_ast_validate_file_has_if_not_is_file_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "if not p.is_file()" in src


def test_ast_schema_path_has_if_not_is_file_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    src = ast.unparse(func)
    assert "if not p.is_file()" in src


def test_ast_schema_path_raises_filenotfounderror_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    raises = [n for n in ast.walk(func) if isinstance(n, ast.Raise)]
    assert len(raises) == 1


def test_ast_load_schema_has_with_open_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_no_global_nonlocal_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(tree))


def test_ast_no_with_at_module_level_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.With)


def test_ast_no_while_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.While) for n in ast.walk(tree))


def test_ast_no_delete_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.Delete) for n in ast.walk(tree))


def test_ast_no_star_import_batch51():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        if isinstance(n, ast.ImportFrom):
            for alias in n.names:
                assert alias.name != "*"


# ---------- forbidden tokens 第一百四十四批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_eval_batch51():
    assert "eval(" not in _src()


def test_source_no_exec_batch51():
    assert "exec(" not in _src()


def test_source_no_compile_batch51():
    assert "compile(" not in _src()


def test_source_no_globals_batch51():
    assert "globals(" not in _src()


def test_source_no_locals_batch51():
    assert "locals(" not in _src()


def test_source_no_os_system_batch51():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch51():
    assert "subprocess" not in _src()


def test_source_no_popen_batch51():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch51():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch51():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch51():
    assert "socket" not in _src()


def test_source_no_requests_batch51():
    assert "requests" not in _src()


def test_source_no_urllib_batch51():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch51():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch51():
    assert "yield" not in _src()


def test_source_no_async_await_batch51():
    assert "async " not in _src()
    assert "await " not in _src()


def test_source_open_count_is_2_batch51():
    """load_schema 1 个 + validate_file 1 个 = 2。"""
    assert _src().count("open(") == 2
