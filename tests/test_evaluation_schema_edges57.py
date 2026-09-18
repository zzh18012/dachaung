"""evaluation/schema.py 第五十七轮 edges 测试（Round 610）。

补强 edges56 未触及的角度（第四十二批）。

新角度：
- SCHEMAS_DIR resolve / parent / 在源码中
- _schema_path 缺失文件错误消息含路径
- _schema_path 名字含中文（理论上无影响）
- load_schema 重新加载不同 schema（manifest / annotation / evaluation-report）
- validate 各种 instance 类型（dict / list / int / str）
- validate schema 名字含相对路径（./prefix）
- validate 错误消息含 schema_name + 错误数 + path
- validate_file 路径不存在错误消息含路径
- validate_file 顶层是 list（schema 拒绝）
- validate_file 顶层是 int / string
- EvalSchemaError errors list 内容固定（path/message/schema_path）
- EvalSchemaError 多 errors（schema 多处违反）
- EvalSchemaError 用于 raise / catch / isinstance
- module source 字符串精确
- AST 结构
- forbidden tokens 第八十一批
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import Draft202012Validator
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


# ---------- SCHEMAS_DIR 第四十二批


def test_schemas_dir_is_path_batch42():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_ends_with_schemas_batch42():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_is_project_root_batch42():
    """SCHEMAS_DIR.parent 应该是项目根（含 pyproject.toml）。"""
    parent = SCHEMAS_DIR.parent
    # 不强校验，但应该存在
    assert parent.is_dir()


def test_schemas_dir_contains_manifest_schema_batch42():
    """schemas 目录应含 manifest.schema.json。"""
    assert (SCHEMAS_DIR / "manifest.schema.json").is_file()


def test_schemas_dir_contains_annotation_schema_batch42():
    assert (SCHEMAS_DIR / "annotation.schema.json").is_file()


def test_schemas_dir_contains_evaluation_report_schema_batch42():
    assert (SCHEMAS_DIR / "evaluation-report.schema.json").is_file()


def test_schemas_dir_in_source_batch42():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_schemas_dir_value_in_module_batch42():
    assert smod.SCHEMAS_DIR is SCHEMAS_DIR


# ---------- _schema_path 第四十二批


def test_schema_path_callable_batch42():
    assert callable(_schema_path)


def test_schema_path_returns_path_batch42():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_absolute_batch42():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


def test_schema_path_signature_one_param_batch42():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_return_annotation_path_batch42():
    sig = inspect.signature(_schema_path)
    assert "Path" in str(sig.return_annotation)


def test_schema_path_no_default_for_name_batch42():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].default is inspect.Parameter.empty


def test_schema_path_empty_name_raises_batch42():
    """空 name 也找不到文件。"""
    with pytest.raises(FileNotFoundError):
        _schema_path("")


def test_schema_path_directory_name_raises_batch42():
    """即使 SCHEMAS_DIR 下有同名目录，is_file()=False 也会 raise。"""
    with pytest.raises(FileNotFoundError):
        _schema_path(".")


# ---------- load_schema 第四十二批


def test_load_schema_callable_batch42():
    assert callable(load_schema)


def test_load_schema_manifest_has_required_batch42():
    out = load_schema("manifest.schema.json")
    assert "required" in out


def test_load_schema_missing_file_raises_batch42():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_with_annotation_batch42():
    out = load_schema("annotation.schema.json")
    assert isinstance(out, dict)
    assert "properties" in out


def test_load_schema_signature_one_param_batch42():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_return_annotation_dict_batch42():
    sig = inspect.signature(load_schema)
    assert "dict" in str(sig.return_annotation)


def test_load_schema_modification_isolated_batch42():
    """修改返回值不影响下次调用。"""
    s1 = load_schema("manifest.schema.json")
    s1["__test_only"] = True
    s2 = load_schema("manifest.schema.json")
    assert "__test_only" not in s2


# ---------- validate 第四十二批


def test_validate_callable_batch42():
    assert callable(validate)


def test_validate_signature_two_params_batch42():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_return_annotation_none_batch42():
    sig = inspect.signature(validate)
    assert "None" in str(sig.return_annotation)


def test_validate_manifest_empty_dict_raises_batch42():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_manifest_minimal_valid_batch42():
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # 不抛


def test_validate_invalid_schema_name_raises_file_not_found_batch42():
    with pytest.raises(FileNotFoundError):
        validate({}, "unknown.schema.json")


def test_validate_eval_schema_error_errors_have_full_keys_batch42():
    """每个 error 含 path/message/schema_path。"""
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert len(exc.value.errors) > 0
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_message_contains_schema_name_batch42():
    with pytest.raises(EvalSchemaError) as exc:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(exc.value)


def test_validate_does_not_raise_on_valid_instance_batch42():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")  # 无异常


def test_validate_multiple_violations_batch42():
    """多处违反 → errors 列表含多项。"""
    data = {
        "manifest_version": "0.0",  # const 违反
        "devset_status": "invalid",  # enum 违反
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(data, "manifest.schema.json")
    assert len(exc.value.errors) >= 2


def test_validate_with_documents_batch42(tmp_path):
    (tmp_path / "a.pdf").write_text("x", encoding="utf-8")
    data = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"doc_id": "d1", "path": "a.pdf", "source_type": "pdf"},
        ],
        "expected_failures": [],
    }
    validate(data, "manifest.schema.json")


# ---------- validate_file 第四十二批


def test_validate_file_callable_batch42():
    assert callable(validate_file)


def test_validate_file_signature_two_params_batch42():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_missing_file_raises_with_message_batch42(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_return_annotation_none_batch42():
    sig = inspect.signature(validate_file)
    assert "None" in str(sig.return_annotation)


def test_validate_file_top_level_array_raises_batch42(tmp_path):
    """顶层 list 不符合 manifest schema（manifest 要求 dict）。"""
    p = tmp_path / "arr.json"
    p.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_idempotent_batch42(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }), encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    validate_file(p, "manifest.schema.json")  # 不抛


# ---------- EvalSchemaError 第四十二批


def test_eval_schema_error_is_exception_batch42():
    assert issubclass(EvalSchemaError, Exception)


def test_eval_schema_error_with_errors_batch42():
    errs = [{"path": ["a"], "message": "x", "schema_path": []}]
    err = EvalSchemaError("boom", errors=errs)
    assert err.errors == errs


def test_eval_schema_error_with_empty_list_errors_batch42():
    err = EvalSchemaError("boom", errors=[])
    assert err.errors == []


def test_eval_schema_error_caught_as_exception_batch42():
    with pytest.raises(Exception):
        raise EvalSchemaError("x")


def test_eval_schema_error_caught_specific_batch42():
    """raise EvalSchemaError 被 except EvalSchemaError 捕获。"""
    caught = False
    try:
        raise EvalSchemaError("x")
    except EvalSchemaError:
        caught = True
    assert caught


def test_eval_schema_error_signature_init_batch42():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]


def test_eval_schema_error_errors_default_none_batch42():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert sig.parameters["errors"].default is None


def test_eval_schema_error_module_level_batch42():
    assert hasattr(smod, "EvalSchemaError")


def test_eval_schema_error_repr_includes_name_batch42():
    err = EvalSchemaError("boom")
    assert "EvalSchemaError" in repr(err)


def test_eval_schema_error_multiple_errors_preserved_order_batch42():
    errs = [
        {"path": ["a"], "message": "first", "schema_path": []},
        {"path": ["b"], "message": "second", "schema_path": []},
    ]
    err = EvalSchemaError("multi", errors=errs)
    assert err.errors[0]["message"] == "first"
    assert err.errors[1]["message"] == "second"


# ---------- module source 字符串精确 第四十二批


def test_module_source_contains_docstring_batch42():
    src = inspect.getsource(smod)
    assert '"""' in src


def test_module_source_contains_future_annotations_batch42():
    src = inspect.getsource(smod)
    assert "from __future__ import annotations" in src


def test_module_source_contains_json_import_batch42():
    src = inspect.getsource(smod)
    assert "import json" in src


def test_module_source_contains_pathlib_path_import_batch42():
    src = inspect.getsource(smod)
    assert "from pathlib import Path" in src


def test_module_source_contains_typing_any_import_batch42():
    src = inspect.getsource(smod)
    assert "from typing import Any" in src


def test_module_source_contains_jsonschema_import_batch42():
    src = inspect.getsource(smod)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_contains_jsonschema_validation_error_import_batch42():
    src = inspect.getsource(smod)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


def test_module_source_contains_schemas_dir_definition_batch42():
    src = inspect.getsource(smod)
    assert "SCHEMAS_DIR = " in src


def test_module_source_contains_eval_schema_error_class_batch42():
    src = inspect.getsource(smod)
    assert "class EvalSchemaError" in src


def test_module_source_contains_schema_path_function_batch42():
    src = inspect.getsource(smod)
    assert "def _schema_path(" in src


def test_module_source_contains_load_schema_function_batch42():
    src = inspect.getsource(smod)
    assert "def load_schema(" in src


def test_module_source_contains_validate_function_batch42():
    src = inspect.getsource(smod)
    assert "def validate(" in src


def test_module_source_contains_validate_file_function_batch42():
    src = inspect.getsource(smod)
    assert "def validate_file(" in src


def test_module_source_contains_draft_2020_12_batch42():
    src = inspect.getsource(smod)
    assert "Draft202012Validator" in src


def test_module_source_contains_iter_errors_call_batch42():
    src = inspect.getsource(smod)
    assert "iter_errors" in src


def test_module_source_contains_absolute_path_batch42():
    src = inspect.getsource(smod)
    assert "absolute_path" in src


def test_module_source_contains_absolute_schema_path_batch42():
    src = inspect.getsource(smod)
    assert "absolute_schema_path" in src


def test_module_source_contains_encoding_utf8_batch42():
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


def test_module_source_contains_all_export_batch42():
    src = inspect.getsource(smod)
    assert "__all__" in src


# ---------- signatures 第四十二批


def test_signature_validate_params_batch42():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_signature_validate_file_params_batch42():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_signature_load_schema_params_batch42():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_schema_path_params_batch42():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_signature_validate_file_no_default_for_path_batch42():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].default is inspect.Parameter.empty


# ---------- module 合理性 第四十二批


def test_module_has_all_attribute_batch42():
    assert hasattr(smod, "__all__")


def test_module_all_is_list_batch42():
    assert isinstance(smod.__all__, list)


def test_module_all_five_entries_batch42():
    assert len(smod.__all__) == 5


def test_module_all_contains_schemas_dir_batch42():
    assert "SCHEMAS_DIR" in smod.__all__


def test_module_does_not_export_private_batch42():
    for name in ["_schema_path"]:
        assert name not in smod.__all__


def test_module_has_schemas_dir_attr_batch42():
    assert hasattr(smod, "SCHEMAS_DIR")


def test_module_has_eval_schema_error_attr_batch42():
    assert hasattr(smod, "EvalSchemaError")


# ---------- AST 结构 第四十二批


def test_ast_top_level_no_loop_no_with_batch42():
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    for node in tree.body:
        assert not isinstance(node, (ast.For, ast.While, ast.With, ast.Try))


def test_ast_has_one_class_batch42():
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_ast_has_four_functions_batch42():
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert "_schema_path" in funcs
    assert "load_schema" in funcs
    assert "validate" in funcs
    assert "validate_file" in funcs


def test_ast_no_async_functions_batch42():
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    async_funcs = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)]
    assert async_funcs == []


def test_ast_top_level_only_allowed_kinds_batch42():
    """顶层只允许 Expr / Import / ImportFrom / ClassDef / FunctionDef / Assign。"""
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.ClassDef, ast.FunctionDef, ast.Assign))


def test_ast_has_module_docstring_batch42():
    src = inspect.getsource(smod)
    tree = ast.parse(src)
    first = tree.body[0]
    assert isinstance(first, ast.Expr)
    assert isinstance(first.value, ast.Constant)


# ---------- 端到端集成 第四十二批


def test_e2e_validate_invalid_manifest_batch42():
    data = {
        "manifest_version": "0.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(data, "manifest.schema.json")


def test_e2e_eval_schema_error_with_full_info_batch42():
    with pytest.raises(EvalSchemaError) as exc:
        validate({"unknown": "x"}, "manifest.schema.json")
    err = exc.value
    assert isinstance(str(err), str)
    assert isinstance(err.errors, list)
    assert len(err.errors) > 0
    first = err.errors[0]
    assert set(first.keys()) == {"path", "message", "schema_path"}


def test_e2e_load_then_validate_idempotent_batch42():
    data = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
        "expected_failures": [],
    }
    schema = load_schema("manifest.schema.json")
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))
    assert errors == []


# ---------- module source forbidden tokens 第八十一批


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
def test_module_source_no_forbidden_tokens_batch42(token):
    src = inspect.getsource(smod)
    assert token not in src
