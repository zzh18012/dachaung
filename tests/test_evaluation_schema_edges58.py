"""evaluation/schema.py 第八十二轮 edges 测试（Round 618）。

补强 edges57 未触及的角度（第四十三批）。

新角度：
- SCHEMAS_DIR resolve / 父目录 / 含三个 schema 文件
- _schema_path 签名 / FileNotFoundError / 返回 Path
- load_schema 签名 / 调用 _schema_path / 返回 dict
- validate 签名 / Draft202012Validator / 错误排序 path
- validate_file 签名 / FileNotFoundError / JSONDecodeError 透传
- EvalSchemaError 签名 / errors 默认 [] / errors=None / errors=[] / errors=list / super().__init__
- EvalSchemaError isinstance Exception / raise+catch
- errors 字段顺序保留 / repr 含类名
- __all__ 5 entries exact
- module source 字符串精确
- AST 结构
- forbidden tokens 第八十八批
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


# ---------- SCHEMAS_DIR ----------

def test_schemas_dir_is_path_batch43():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_exists_batch43():
    assert SCHEMAS_DIR.exists()


def test_schemas_dir_is_dir_batch43():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_is_project_root_batch43():
    """SCHEMAS_DIR = project_root / 'schemas'。"""
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_contains_manifest_schema_batch43():
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch43():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch43():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_resolved_batch43():
    """SCHEMAS_DIR 是 resolve 后的（无相对路径污染）。"""
    src = inspect.getsource(schema_mod)
    assert "Path(__file__).resolve()" in src


# ---------- _schema_path 签名 ----------

def test_schema_path_signature_batch43():
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_schema_path_param_kind_batch43():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_schema_path_no_default_batch43():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_schema_path_return_annotation_batch43():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


# ---------- _schema_path 行为 ----------

def test_schema_path_returns_path_batch43():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)
    assert p.is_file()


def test_schema_path_missing_raises_filenotfound_batch43():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc_info.value)


def test_schema_path_empty_name_raises_batch43():
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_name_raises_batch43():
    """name 是 '.' → 解析成 SCHEMAS_DIR 自身 → 不是 file。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".")


def test_schema_path_error_contains_path_batch43():
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("missing.json")
    msg = str(exc_info.value)
    assert "missing.json" in msg


# ---------- load_schema 签名 ----------

def test_load_schema_signature_batch43():
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.keys())
    assert params == ["name"]


def test_load_schema_return_annotation_batch43():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


# ---------- load_schema 行为 ----------

def test_load_schema_manifest_batch43():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    assert "$schema" in s or "type" in s or "properties" in s


def test_load_schema_annotation_batch43():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_load_schema_evaluation_report_batch43():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_load_schema_missing_raises_filenotfound_batch43():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.json")


def test_load_schema_uses_utf8_batch43():
    src = inspect.getsource(load_schema)
    assert 'encoding="utf-8"' in src


def test_load_schema_calls_schema_path_batch43():
    with patch("evaluation.schema._schema_path", side_effect=FileNotFoundError("mock")):
        with pytest.raises(FileNotFoundError):
            load_schema("manifest.schema.json")


# ---------- validate 签名 ----------

def test_validate_signature_batch43():
    sig = inspect.signature(validate)
    params = list(sig.parameters.keys())
    assert params == ["instance", "schema_name"]


def test_validate_param_kinds_batch43():
    sig = inspect.signature(validate)
    for name in ["instance", "schema_name"]:
        assert sig.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_validate_return_annotation_batch43():
    sig = inspect.signature(validate)
    assert sig.return_annotation is None or "None" in str(sig.return_annotation)


# ---------- validate 行为 ----------

def test_validate_manifest_valid_batch43():
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {
                "doc_id": "d1",
                "path": "samples/private/d1.pdf",
                "source_type": "pdf",
                "sha256": "a" * 64,
                "categories": ["test"],
            }
        ],
    }
    # 不抛即过
    validate(valid_manifest, "manifest.schema.json")


def test_validate_invalid_manifest_missing_required_batch43():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "manifest.schema.json" in msg


def test_validate_invalid_devset_status_batch43():
    bad_manifest = {
        "manifest_version": "1.0",
        "devset_status": "partial",  # 只允许 complete/incomplete
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(bad_manifest, "manifest.schema.json")


def test_validate_errors_field_is_list_batch43():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    assert isinstance(exc_info.value.errors, list)


def test_validate_errors_field_has_keys_batch43():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    if exc_info.value.errors:
        e0 = exc_info.value.errors[0]
        assert "path" in e0
        assert "message" in e0
        assert "schema_path" in e0


def test_validate_error_message_contains_count_batch43():
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "校验失败" in msg


def test_validate_uses_draft202012_batch43():
    src = inspect.getsource(validate)
    assert "Draft202012Validator" in src


def test_validate_sorts_errors_by_path_batch43():
    src = inspect.getsource(validate)
    assert "sorted" in src
    assert "absolute_path" in src


# ---------- validate_file 签名 ----------

def test_validate_file_signature_batch43():
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.keys())
    assert params == ["path", "schema_name"]


def test_validate_file_param_kinds_batch43():
    sig = inspect.signature(validate_file)
    for name in ["path", "schema_name"]:
        assert sig.parameters[name].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


# ---------- validate_file 行为 ----------

def test_validate_file_missing_raises_filenotfound_batch43():
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file("nonexistent.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc_info.value)


def test_validate_file_str_path_batch43(tmp_path):
    """接受 str path。"""
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(str(p), "manifest.schema.json")


def test_validate_file_path_paths_batch43(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecode_batch43(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_schema_fail_batch43(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"wrong": "schema"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_uses_utf8_batch43():
    src = inspect.getsource(validate_file)
    assert 'encoding="utf-8"' in src


def test_validate_file_calls_validate_batch43(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    with patch("evaluation.schema.validate") as mock_v:
        validate_file(p, "any.schema.json")
    mock_v.assert_called_once()


# ---------- EvalSchemaError ----------

def test_eval_schema_error_inherits_exception_batch43():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_not_value_error_batch43():
    assert not issubclass(EvalSchemaError, ValueError)


def test_eval_schema_error_not_type_error_batch43():
    assert not issubclass(EvalSchemaError, TypeError)


def test_eval_schema_error_default_errors_batch43():
    e = EvalSchemaError("oops")
    assert e.errors == []


def test_eval_schema_error_none_errors_batch43():
    e = EvalSchemaError("oops", errors=None)
    assert e.errors == []


def test_eval_schema_error_empty_list_errors_batch43():
    e = EvalSchemaError("oops", errors=[])
    assert e.errors == []


def test_eval_schema_error_with_errors_batch43():
    errs = [{"path": ["a"], "message": "bad"}]
    e = EvalSchemaError("oops", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_errors_order_preserved_batch43():
    errs = [{"i": 1}, {"i": 2}, {"i": 3}]
    e = EvalSchemaError("oops", errors=errs)
    assert e.errors == errs


def test_eval_schema_error_message_stored_batch43():
    e = EvalSchemaError("oops")
    assert str(e) == "oops"


def test_eval_schema_error_repr_contains_classname_batch43():
    e = EvalSchemaError("oops")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_catchable_batch43():
    try:
        raise EvalSchemaError("oops")
    except EvalSchemaError as e:
        assert str(e) == "oops"


def test_eval_schema_error_catchable_as_exception_batch43():
    try:
        raise EvalSchemaError("oops")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_errors_writable_batch43():
    e = EvalSchemaError("oops")
    e.errors.append({"path": [], "message": "x"})
    assert len(e.errors) == 1


def test_eval_schema_error_init_signature_batch43():
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.keys())
    assert params == ["self", "message", "errors"]


def test_eval_schema_error_init_defaults_batch43():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["message"].default is inspect.Parameter.empty
    assert sig.parameters["errors"].default is None


# ---------- __all__ ----------

def test_all_exact_batch43():
    assert set(schema_mod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_all_count_5_batch43():
    assert len(schema_mod.__all__) == 5


def test_all_entries_are_str_batch43():
    for e in schema_mod.__all__:
        assert isinstance(e, str)


def test_all_entries_are_attrs_batch43():
    for e in schema_mod.__all__:
        assert hasattr(schema_mod, e)


def test_all_no_duplicates_batch43():
    assert len(set(schema_mod.__all__)) == len(schema_mod.__all__)


# ---------- module source ----------

def test_module_source_contains_no_reuse_batch43():
    src = inspect.getsource(schema_mod)
    assert "不与 app/schema.py 复用" in src


def test_module_source_contains_jsonschema_batch43():
    src = inspect.getsource(schema_mod)
    assert "jsonschema" in src


def test_module_source_contains_draft202012_batch43():
    src = inspect.getsource(schema_mod)
    assert "Draft202012Validator" in src


def test_module_source_contains_errors_or_none_batch43():
    src = inspect.getsource(schema_mod)
    assert "errors or []" in src


def test_module_source_contains_schemas_dir_init_batch43():
    src = inspect.getsource(schema_mod)
    assert "SCHEMAS_DIR = " in src


def test_module_has_docstring_batch43():
    assert schema_mod.__doc__ is not None
    assert len(schema_mod.__doc__) > 30


# ---------- AST 结构 ----------

def test_ast_top_level_class_count_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1


def test_ast_top_level_class_name_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef)][0]
    assert cls.name == "EvalSchemaError"


def test_ast_top_level_function_count_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert len(funcs) == 4


def test_ast_top_level_function_names_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert funcs == ["_schema_path", "load_schema", "validate", "validate_file"]


def test_ast_eval_schema_error_has_init_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef)][0]
    methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    assert "__init__" in methods


def test_ast_no_try_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.Try)


def test_ast_no_for_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.For)


def test_ast_no_while_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.While)


def test_ast_no_async_in_module_body_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    for n in tree.body:
        assert not isinstance(n, ast.AsyncFunctionDef)


def test_ast_has_imports_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert len(imports) >= 4


def test_ast_from_future_first_batch43():
    tree = ast.parse(inspect.getsource(schema_mod))
    first = tree.body[0]
    assert isinstance(first, ast.Expr)  # docstring
    second = tree.body[1]
    assert isinstance(second, ast.ImportFrom)
    assert second.module == "__future__"


# ---------- forbidden tokens 第八十八批 ----------

def test_source_no_eval_batch43():
    src = inspect.getsource(schema_mod)
    assert "eval(" not in src


def test_source_no_exec_batch43():
    src = inspect.getsource(schema_mod)
    assert "exec(" not in src


def test_source_no_compile_batch43():
    src = inspect.getsource(schema_mod)
    assert "compile(" not in src


def test_source_no_globals_batch43():
    src = inspect.getsource(schema_mod)
    assert "globals(" not in src


def test_source_no_locals_batch43():
    src = inspect.getsource(schema_mod)
    assert "locals(" not in src


def test_source_no_os_system_batch43():
    src = inspect.getsource(schema_mod)
    assert "os.system(" not in src


def test_source_no_popen_batch43():
    src = inspect.getsource(schema_mod)
    assert "popen(" not in src


def test_source_no_yaml_load_batch43():
    src = inspect.getsource(schema_mod)
    assert "yaml.load(" not in src


def test_source_no_pickle_load_batch43():
    src = inspect.getsource(schema_mod)
    assert "pickle.load(" not in src


def test_source_uses_json_not_pickle_batch43():
    src = inspect.getsource(schema_mod)
    assert "import json" in src
    assert "pickle" not in src
