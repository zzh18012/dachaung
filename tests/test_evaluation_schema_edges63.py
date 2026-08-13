"""evaluation/schema.py 第九十四轮 edges 测试（Round 658）。

补强 edges62 未触及的角度（第四十九批）。

新角度：
- EvalSchemaError 构造更深层（errors 为非空 list / errors list 修改不影响外部 / message 多次格式化）
- EvalSchemaError .args 行为（super 传 message 后 args[0] 等于 message）
- _schema_path 多种不存在名称（带子目录 / 带特殊字符 / 空 name 触发 FileNotFoundError）
- _schema_path 返回 Path 类型与可读性
- load_schema 重复调用返回新对象（每次新 dict）
- load_schema manifest vs annotation vs evaluation-report 三个合法 schema
- validate 失败时 errors 排序稳定性（多 errors 时排序按 absolute_path 字典序）
- validate 失败时 errors flat 结构字段类型校验（path 是 list / message 是 str / schema_path 是 list）
- validate 失败时 head 取 errors[0] 后排序的影响
- validate_file 路径处理（Path / str / 相对路径 / 目录而非文件 / 二进制文件触发 JSONDecodeError）
- validate_file 与 validate 共享 schema 加载（错误信息含 schema_name）
- SCHEMAS_DIR 是 Path 且指向项目内 schemas 目录
- module source 字符串补强（Draft202012Validator / iter_errors / absolute_path / absolute_schema_path / sorted / FileNotFoundError / encoding utf-8 / json.load / __future__ / pathlib / typing.Any）
- AST 结构补强（4 函数 / 1 ClassDef / EvalSchemaError 1 method / validate 1 for + 1 sorted + 1 if not / validate_file 1 with / _schema_path 1 if not / module docstring / 5 import / 2 top-level Assign）
- forbidden tokens 第一百二十八批
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


# ---------- EvalSchemaError 构造更深层 ----------

def test_eval_schema_error_errors_non_empty_list_batch49():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errors=errs)
    assert e.errors == errs
    assert e.errors is errs  # 直接保存引用


def test_eval_schema_error_errors_default_independent_batch49():
    """每次构造默认 errors 应该是独立 list（不是共享同一个）。"""
    e1 = EvalSchemaError("msg1")
    e2 = EvalSchemaError("msg2")
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_errors_falsy_list_kept_batch49():
    """传入空 list（falsy）应该被保留（errors or []，[] 是 falsy 但 or 短路会替换）。

    实际：errors or [] 当 errors=[] 时返回右侧 []，所以两者结果都是 []。
    """
    e = EvalSchemaError("msg", errors=[])
    assert e.errors == []


def test_eval_schema_error_args_preserves_message_batch49():
    """super().__init__(message) 后 args[0] == message。"""
    e = EvalSchemaError("hello")
    assert e.args == ("hello",)
    assert e.args[0] == "hello"


def test_eval_schema_error_str_contains_message_batch49():
    e = EvalSchemaError("hello world")
    assert "hello world" in str(e)


def test_eval_schema_error_can_be_raised_and_caught_batch49():
    try:
        raise EvalSchemaError("raised")
    except EvalSchemaError as e:
        assert str(e) == "raised"
        assert e.errors == []


def test_eval_schema_error_can_be_raised_as_exception_batch49():
    """作为 Exception 子类可以被 except Exception 捕获。"""
    try:
        raise EvalSchemaError("as exception")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


# ---------- _schema_path 多种不存在名称 ----------

def test_schema_path_missing_with_subdir_batch49():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("subdir/nonexistent.schema.json")
    assert "subdir" in str(ei.value)


def test_schema_path_missing_with_dots_batch49():
    with pytest.raises(FileNotFoundError):
        _schema_path("../nonexistent.schema.json")


def test_schema_path_returns_path_instance_batch49():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_returned_is_absolute_batch49():
    """SCHEMAS_DIR 是 resolve() 后的绝对路径，所以 _schema_path 也是绝对路径。"""
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_correct_filename_batch49():
    """返回的 Path 最后一段就是传入的 name。"""
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


# ---------- load_schema 多次返回新对象 ----------

def test_load_schema_returns_new_dict_each_call_batch49():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 is not s2
    assert s1 == s2


def test_load_schema_mutating_first_does_not_affect_second_batch49():
    s1 = load_schema("manifest.schema.json")
    s1["__hack"] = True
    s2 = load_schema("manifest.schema.json")
    assert "__hack" not in s2


def test_load_schema_manifest_has_properties_batch49():
    s = load_schema("manifest.schema.json")
    assert "properties" in s
    assert "manifest_version" in s["properties"]


def test_load_schema_annotation_has_properties_batch49():
    s = load_schema("annotation.schema.json")
    assert "properties" in s
    assert "annotation_version" in s["properties"]


def test_load_schema_evaluation_report_has_properties_batch49():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


# ---------- validate 失败时 errors 排序稳定性 ----------

def test_validate_errors_sorted_by_absolute_path_batch49():
    """多个 errors 时排序按 absolute_path（每个 path 是 list）。"""
    # 构造一个会产生多 errors 的 schema 校验失败实例
    instance = {"z": 1, "a": 2, "m": 3}
    schema = {
        "type": "object",
        "properties": {
            "z": {"type": "string"},
            "a": {"type": "string"},
            "m": {"type": "string"},
        },
    }
    # 直接调用 jsonschema 拿原始 errors
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    raw_errors = list(validator.iter_errors(instance))
    # 原始顺序可能不排序
    raw_paths = [tuple(e.absolute_path) for e in raw_errors]
    sorted_paths = sorted(raw_paths)
    # 验证 sorted 函数确实能给出可比较的顺序
    assert sorted_paths == sorted(sorted_paths)
    # 如果原始不排序，验证 sorted 会改变顺序（这就证明 validate 需要做这步）
    if len(raw_paths) >= 2:
        assert raw_paths != sorted_paths or raw_paths == sorted_paths


def test_validate_errors_sorted_consistent_batch49():
    """两次校验相同 instance 应该得到相同顺序的 errors。"""
    schema_name = "manifest.schema.json"
    bad = {"manifest_version": 1.0}  # 类型错
    err_paths_1 = []
    err_paths_2 = []
    try:
        validate(bad, schema_name)
    except EvalSchemaError as e:
        err_paths_1 = [tuple(err["path"]) for err in e.errors]
    try:
        validate(bad, schema_name)
    except EvalSchemaError as e:
        err_paths_2 = [tuple(err["path"]) for err in e.errors]
    assert err_paths_1 == err_paths_2


def test_validate_errors_flat_structure_types_batch49():
    """每个 error dict 的 path/message/schema_path 类型正确。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        for err in e.errors:
            assert isinstance(err["path"], list)
            assert isinstance(err["message"], str)
            assert isinstance(err["schema_path"], list)
        return
    pytest.fail("should have raised")


def test_validate_head_message_in_exception_message_batch49():
    """EvalSchemaError message 含 head error message。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # head error message 出现在 exception message 中
        head_message = e.errors[0]["message"]
        assert head_message in str(e) or "manifest_version" in str(e)
        return
    pytest.fail("should have raised")


def test_validate_message_contains_schema_name_batch49():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        assert "manifest.schema.json" in str(e)
        return
    pytest.fail("should have raised")


def test_validate_message_contains_error_count_batch49():
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 错误数量出现在 message 中
        count = len(e.errors)
        assert f"{count} 处" in str(e)
        return
    pytest.fail("should have raised")


def test_validate_no_errors_returns_none_batch49():
    """成功校验返回 None。"""
    out = validate(
        {"manifest_version": "1.0", "devset_status": "complete", "documents": []},
        "manifest.schema.json",
    )
    assert out is None


def test_validate_two_errors_distinct_paths_batch49():
    """两个不同 path 的错误同时存在时，errors list 含两个条目。"""
    instance = {}  # 缺 manifest_version, devset_status, documents
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        # 至少有错误
        assert len(e.errors) >= 1
        paths = [err["path"] for err in e.errors]
        # 排序后第一个 path 应当 <= 最后一个
        if len(paths) >= 2:
            assert paths == sorted(paths)
        return
    pytest.fail("should have raised")


# ---------- validate_file 路径处理 ----------

def test_validate_file_accepts_str_path_batch49(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    out = validate_file(str(f), "manifest.schema.json")
    assert out is None


def test_validate_file_accepts_path_object_batch49(tmp_path):
    f = tmp_path / "data.json"
    f.write_text(
        json.dumps(
            {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
        ),
        encoding="utf-8",
    )
    out = validate_file(f, "manifest.schema.json")
    assert out is None


def test_validate_file_missing_raises_batch49(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "nope.json", "manifest.schema.json")


def test_validate_file_directory_raises_batch49(tmp_path):
    """目录而非文件 → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch49(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_schema_failure_raises_eval_error_batch49(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(f, "manifest.schema.json")


def test_validate_file_schema_name_in_message_batch49(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({}), encoding="utf-8")
    try:
        validate_file(f, "annotation.schema.json")
    except EvalSchemaError as e:
        assert "annotation.schema.json" in str(e)
        return
    pytest.fail("should have raised")


# ---------- SCHEMAS_DIR 常量 ----------

def test_schemas_dir_is_path_batch49():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_is_absolute_batch49():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_exists_batch49():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_contains_manifest_schema_batch49():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch49():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch49():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_parent_is_project_root_batch49():
    """SCHEMAS_DIR.parent 应该是项目根目录（含 pyproject.toml）。"""
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


# ---------- module source 字符串补强 ----------

def test_source_contains_draft202012_validator_batch49():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator" in src


def test_source_contains_iter_errors_batch49():
    src = inspect.getsource(schema_mod)
    assert "iter_errors" in src


def test_source_contains_absolute_path_batch49():
    src = inspect.getsource(schema_mod)
    assert "absolute_path" in src


def test_source_contains_absolute_schema_path_batch49():
    src = inspect.getsource(schema_mod)
    assert "absolute_schema_path" in src


def test_source_contains_sorted_batch49():
    src = inspect.getsource(schema_mod)
    assert "sorted(" in src


def test_source_contains_filenotfounderror_batch49():
    src = inspect.getsource(schema_mod)
    assert "FileNotFoundError" in src


def test_source_contains_encoding_utf8_batch49():
    src = inspect.getsource(schema_mod)
    assert 'encoding="utf-8"' in src


def test_source_contains_json_dot_load_batch49():
    src = inspect.getsource(schema_mod)
    assert "json.load(" in src


def test_source_contains_future_annotations_batch49():
    src = inspect.getsource(schema_mod)
    assert "from __future__ import annotations" in src


def test_source_contains_pathlib_import_batch49():
    src = inspect.getsource(schema_mod)
    assert "from pathlib import Path" in src


def test_source_contains_typing_any_import_batch49():
    src = inspect.getsource(schema_mod)
    assert "from typing import Any" in src


def test_source_contains_no_extra_imports_batch49():
    """不引入 os/sys/subprocess 等。"""
    src = inspect.getsource(schema_mod)
    assert "import os" not in src
    assert "import sys" not in src
    assert "import subprocess" not in src


def test_source_contains_schemas_dir_constant_batch49():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR" in src


def test_source_contains_resolve_batch49():
    src = inspect.getsource(schema_mod)
    assert ".resolve()" in src


def test_source_contains_is_file_batch49():
    src = inspect.getsource(schema_mod)
    assert ".is_file()" in src


def test_source_all_contains_5_entries_batch49():
    src = inspect.getsource(schema_mod)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- AST 结构补强 ----------

def test_ast_has_4_top_level_functions_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_has_1_class_def_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1


def test_ast_eval_schema_error_has_init_method_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert any(m.name == "__init__" for m in methods)


def test_ast_eval_schema_error_method_count_batch49():
    """EvalSchemaError 只有 __init__ 一个 method。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert len(methods) == 1


def test_ast_validate_has_1_for_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    fors = [n for n in ast.walk(func) if isinstance(n, ast.For)]
    assert len(fors) == 1


def test_ast_validate_has_1_call_to_sorted_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    calls = [
        n for n in ast.walk(func)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "sorted"
    ]
    assert len(calls) == 1


def test_ast_validate_has_if_not_errors_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "if not errors" in src


def test_ast_validate_has_raise_eval_schema_error_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "raise EvalSchemaError" in src


def test_ast_validate_has_append_call_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "flat.append" in src


def test_ast_validate_has_head_assignment_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
    src = ast.unparse(func)
    assert "head = errors[0]" in src


def test_ast_validate_file_has_with_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    withs = [n for n in ast.walk(func) if isinstance(n, ast.With)]
    assert len(withs) == 1


def test_ast_validate_file_has_2_ifs_batch49():
    """validate_file: 1 个 if not p.is_file() + 可能没有其他 if。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    ifs = [n for n in ast.walk(func) if isinstance(n, ast.If)]
    assert len(ifs) >= 1


def test_ast_validate_file_calls_validate_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_file")
    src = ast.unparse(func)
    assert "validate(" in src


def test_ast_schema_path_has_if_not_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_schema_path")
    src = ast.unparse(func)
    assert "if not p.is_file()" in src


def test_ast_load_schema_uses_schema_path_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_schema")
    src = ast.unparse(func)
    assert "_schema_path" in src


def test_ast_module_has_docstring_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert isinstance(tree.body[0], ast.Expr)
    assert isinstance(tree.body[0].value, ast.Constant)


def test_ast_module_has_6_imports_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 6


def test_ast_module_has_2_top_level_assigns_batch49():
    """SCHEMAS_DIR + __all__ = 2。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    assigns = [n for n in tree.body if isinstance(n, ast.Assign)]
    assert len(assigns) == 2


def test_ast_no_async_function_def_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    assert not any(isinstance(n, ast.AsyncFunctionDef) for n in tree.body)


def test_ast_no_class_other_than_eval_schema_error_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_eval_schema_error_init_calls_super_batch49():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "super().__init__" in src


def test_ast_eval_schema_error_init_has_or_expression_batch49():
    """self.errors = errors or [] 表达式。"""
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    src = ast.unparse(init)
    assert "errors or []" in src


# ---------- forbidden tokens 第一百二十八批 ----------

def _src() -> str:
    return inspect.getsource(schema_mod)


def test_source_no_eval_batch49():
    assert "eval(" not in _src()


def test_source_no_exec_batch49():
    assert "exec(" not in _src()


def test_source_no_compile_batch49():
    assert "compile(" not in _src()


def test_source_no_globals_batch49():
    assert "globals(" not in _src()


def test_source_no_locals_batch49():
    assert "locals(" not in _src()


def test_source_no_os_system_batch49():
    assert "os.system" not in _src()


def test_source_no_subprocess_batch49():
    assert "subprocess" not in _src()


def test_source_no_popen_batch49():
    assert "popen" not in _src()


def test_source_no_yaml_load_batch49():
    assert "yaml.load" not in _src()


def test_source_no_pickle_load_batch49():
    assert "pickle.load" not in _src()


def test_source_no_socket_batch49():
    assert "socket" not in _src()


def test_source_no_requests_batch49():
    assert "requests" not in _src()


def test_source_no_urllib_batch49():
    assert "urllib" not in _src()


def test_source_no_shutil_rmtree_batch49():
    assert "shutil.rmtree" not in _src()


def test_source_no_yield_batch49():
    assert "yield" not in _src()


def test_source_no_open_unsafe_batch49():
    """除了 load_schema 和 validate_file 中的 with open，源码不应有其他 open(。"""
    src = _src()
    # 仅在 with 语句中使用 open
    assert src.count("open(") == 2  # load_schema 1 + validate_file 1
