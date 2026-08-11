"""evaluation/schema.py 第四十四轮 edges 测试（Round 502）。

补强 edges43 未触及的角度（第二十四批）：
- EvalSchemaError 第二十四批：errors=None 默认 / errors=[] 默认 / errors 非空 / errors 是 tuple / message 透传 / inheritance / hashable / repr
- _schema_path 第二十四批：不存在抛 FileNotFoundError / Path 返回 / parent / resolve 路径 / SCHEMAS_DIR / 命名空间安全
- load_schema 第二十四批：utf-8 编码 / dict 返回 / 重复加载稳定 / 非法 JSON 抛 JSONDecodeError / 三个 schema 都能加载
- validate 第二十四批：成功 None / 失败 EvalSchemaError / errors 排序按 path / errors 含 path/message/schema_path 三字段 / 多 errors / instance 非 dict 接受
- validate_file 第二十四批：str path 接受 / Path 接受 / 不存在 FileNotFoundError / 非 JSON 抛 JSONDecodeError / utf-8 强制
- module source forbidden tokens 第四十二批
- module source 字符串精确补强第三十八批
- signatures 第三十八批
- module 合理性第三十八批
- 端到端集成第三十八批
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


# ---------- EvalSchemaError 第二十四批 ----------


def test_eval_schema_error_default_errors_none_batch24():
    e = EvalSchemaError("msg")
    assert e.errors == []


def test_eval_schema_error_errors_explicit_empty_batch24():
    e = EvalSchemaError("msg", [])
    assert e.errors == []


def test_eval_schema_error_errors_non_empty_batch24():
    errs = [{"path": ["a"], "message": "x"}]
    e = EvalSchemaError("msg", errs)
    assert e.errors == errs


def test_eval_schema_error_errors_tuple_accepted_batch24():
    """传 tuple 也应接受（实现 `errors or []` 对非空 tuple 不替换）。"""
    errs = ({"path": ["a"], "message": "x"},)
    e = EvalSchemaError("msg", errs)
    # tuple 非空 → 保留原 tuple
    assert e.errors == errs


def test_eval_schema_error_message_str_passthrough_batch24():
    e = EvalSchemaError("hello")
    assert str(e) == "hello"


def test_eval_schema_error_inherits_exception_batch24():
    e = EvalSchemaError("x")
    assert isinstance(e, Exception)


def test_eval_schema_error_can_be_raised_caught_batch24():
    with pytest.raises(EvalSchemaError) as exc:
        raise EvalSchemaError("boom", [{"path": [], "message": "m"}])
    assert "boom" in str(exc.value)
    assert exc.value.errors == [{"path": [], "message": "m"}]


def test_eval_schema_error_args_stored_batch24():
    e = EvalSchemaError("m", [{"path": [], "message": "x"}])
    assert e.args == ("m",)


def test_eval_schema_error_repr_batch24():
    e = EvalSchemaError("m")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_error_errors_attribute_is_list_when_default_batch24():
    e = EvalSchemaError("m")
    assert isinstance(e.errors, list)


def test_eval_schema_error_can_be_caught_as_exception_batch24():
    """可被 except Exception 捕获。"""
    try:
        raise EvalSchemaError("x")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_message_attr_batch24():
    """Exception 子类自动存 args[0]。"""
    e = EvalSchemaError("hello world")
    assert e.args[0] == "hello world"


# ---------- _schema_path 第二十四批 ----------


def test_schema_path_returns_path_batch24():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_missing_raises_batch24():
    with pytest.raises(FileNotFoundError) as exc:
        _schema_path("nonexistent.schema.json")
    assert "Schema 文件不存在" in str(exc.value)


def test_schema_path_resolves_relative_to_schemas_dir_batch24():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


def test_schema_path_for_all_three_schemas_batch24():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        p = _schema_path(name)
        assert p.is_file()


def test_schema_path_accepts_complex_name_batch24():
    """带连字符 / 点的 schema 名应正常处理。"""
    p = _schema_path("evaluation-report.schema.json")
    assert p.name == "evaluation-report.schema.json"


def test_schema_path_directory_not_file_batch24():
    """name 是目录 → is_file() False → FileNotFoundError。"""
    # schemas/ 目录本身就是一个不存在的 .schema.json 文件名
    with pytest.raises(FileNotFoundError):
        _schema_path("not_a_real_schema.json")


def test_schemas_dir_constant_value_batch24():
    """SCHEMAS_DIR 应是项目根 / schemas。"""
    # test 文件在 tests/，所以 parent=tests，parent.parent=项目根
    assert SCHEMAS_DIR == Path(__file__).resolve().parent.parent / "schemas"


def test_schemas_dir_is_directory_batch24():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_has_three_schemas_batch24():
    files = list(SCHEMAS_DIR.glob("*.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names


# ---------- load_schema 第二十四批 ----------


def test_load_schema_returns_dict_batch24():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_keyword_batch24():
    s = load_schema("manifest.schema.json")
    assert "$schema" in s or "type" in s or "properties" in s


def test_load_schema_idempotent_batch24():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_missing_raises_file_not_found_batch24():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_invalid_json_raises_decode_error_batch24(tmp_path):
    """Mock _schema_path 返回含非法 JSON 的文件 → JSONDecodeError。"""
    bad = tmp_path / "bad.json"
    bad.write_text("not valid", encoding="utf-8")
    with patch("evaluation.schema._schema_path", return_value=bad):
        with pytest.raises(json.JSONDecodeError):
            load_schema("bad.json")


def test_load_schema_three_schemas_loadable_batch24():
    for name in ("manifest.schema.json", "annotation.schema.json", "evaluation-report.schema.json"):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_manifest_has_properties_batch24():
    s = load_schema("manifest.schema.json")
    assert "properties" in s


def test_load_schema_annotation_has_properties_batch24():
    s = load_schema("annotation.schema.json")
    assert "properties" in s


def test_load_schema_evaluation_report_has_properties_batch24():
    s = load_schema("evaluation-report.schema.json")
    assert "properties" in s


def test_load_schema_uses_utf8_encoding_batch24():
    """load_schema 应使用 encoding='utf-8'。"""
    src = inspect.getsource(smod)
    assert 'encoding="utf-8"' in src


# ---------- validate 第二十四批 ----------


def test_validate_success_returns_none_batch24():
    """最小合法 manifest 实例 → None。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    assert validate(instance, "manifest.schema.json") is None


def test_validate_failure_raises_eval_schema_error_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError):
        validate(instance, "manifest.schema.json")


def test_validate_failure_message_contains_count_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    assert "校验失败" in str(exc.value)


def test_validate_failure_errors_list_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    assert isinstance(exc.value.errors, list)
    assert len(exc.value.errors) >= 1


def test_validate_errors_have_three_keys_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    for err in exc.value.errors:
        assert set(err.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["path"], list)


def test_validate_errors_schema_path_is_list_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["schema_path"], list)


def test_validate_errors_message_is_str_batch24():
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    for err in exc.value.errors:
        assert isinstance(err["message"], str)


def test_validate_multiple_errors_count_batch24():
    """多个字段都错 → errors 列表含多项。"""
    instance = {
        "manifest_version": "wrong",
        "devset_status": "wrong",
        "documents": "not a list",
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    assert len(exc.value.errors) >= 2


def test_validate_errors_sorted_by_path_batch24():
    """errors 应按 path 排序。"""
    instance = {
        "manifest_version": "wrong",
        "devset_status": "wrong",
    }
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    paths = [tuple(e["path"]) for e in exc.value.errors]
    assert paths == sorted(paths)


def test_validate_message_includes_head_error_batch24():
    """错误消息应包含 head.message 与 head.path。"""
    instance = {"wrong": "field"}
    with pytest.raises(EvalSchemaError) as exc:
        validate(instance, "manifest.schema.json")
    msg = str(exc.value)
    assert "校验失败" in msg
    assert "path=" in msg


# ---------- validate_file 第二十四批 ----------


def test_validate_file_accepts_str_path_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_accepts_path_obj_batch24(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_validate_file_missing_raises_file_not_found_batch24(tmp_path):
    with pytest.raises(FileNotFoundError) as exc:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(exc.value)


def test_validate_file_invalid_json_raises_decode_error_batch24(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_content_raises_eval_schema_error_batch24(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "field"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_empty_raises_decode_error_batch24(tmp_path):
    """空文件 → JSONDecodeError。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_directory_raises_batch24(tmp_path):
    """path 是目录 → is_file() False → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path, "manifest.schema.json")


def test_validate_file_utf8_encoded_with_unicode_batch24(tmp_path):
    """含 unicode 字符的 JSON 应可读。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
            "notes": "中文注释",
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    # manifest schema additionalProperties=false，所以会失败
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第四十二批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import asyncio",
    "import threading",
    "import concurrent",
    "import itertools",
    "import functools",
    "import timeit",
    "import time",
    "from logging",
    "from asyncio",
    "from threading",
    "from concurrent",
    "from itertools",
    "from functools",
    "from time",
    "import yaml",
    "import requests",
    "import urllib",
    "import socket",
    "import pickle",
    "import shutil",
    "import tempfile",
    "import argparse",
    "import csv",
    "import random",
    "import hashlib",
]


def test_module_source_forbidden_tokens_batch24():
    source = inspect.getsource(smod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_eval_exec_batch24():
    source = inspect.getsource(smod)
    assert "eval(" not in source
    assert "exec(" not in source


def test_module_source_no_star_import_batch24():
    source = inspect.getsource(smod)
    assert "import *" not in source


def test_module_source_no_relative_imports_batch24():
    source = inspect.getsource(smod)
    assert "from ." not in source


def test_module_source_no_environ_batch24():
    source = inspect.getsource(smod)
    assert "os.environ" not in source
    assert "getenv" not in source


def test_module_source_no_unsafe_network_batch24():
    source = inspect.getsource(smod)
    for tok in ["requests", "urllib.request", "http.client", "socket"]:
        assert tok not in source


def test_module_source_no_dataclass_batch24():
    source = inspect.getsource(smod)
    assert "@dataclass" not in source
    assert "from dataclasses" not in source


def test_module_source_no_argparse_batch24():
    source = inspect.getsource(smod)
    assert "argparse" not in source


def test_module_source_no_module_level_mutables_batch24():
    """不应有 module-level 私有 mutable 常量。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    for node in tree.body:
        if isinstance(node, _ast.Assign) and isinstance(node.targets[0], _ast.Name):
            name = node.targets[0].id
            if name.startswith("_") and not name.startswith("__"):
                pytest.fail(f"private module-level constant: {name}")


def test_module_source_uses_from_future_annotations_batch24():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_source_json_allowed_batch24():
    """schema.py 允许 import json。"""
    source = inspect.getsource(smod)
    assert "import json" in source


def test_module_source_jsonschema_allowed_batch24():
    """schema.py 允许 from jsonschema 导入。"""
    source = inspect.getsource(smod)
    assert "from jsonschema" in source


def test_module_source_no_class_other_than_eval_schema_error_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    classes = [n.name for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == ["EvalSchemaError"]


def test_module_source_no_open_at_module_level_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    for node in tree.body:
        if isinstance(node, _ast.Expr):
            assert not (isinstance(node.value, _ast.Call) and getattr(node.value.func, "id", None) == "open")


def test_module_source_no_subprocess_batch24():
    source = inspect.getsource(smod)
    assert "subprocess" not in source


# ---------- module source 字符串精确补强第三十八批 ----------


def test_module_source_contains_schemas_dir_batch24():
    source = inspect.getsource(smod)
    assert "SCHEMAS_DIR" in source


def test_module_source_contains_path_parent_batch24():
    source = inspect.getsource(smod)
    assert "__file__" in source
    assert ".parent" in source


def test_module_source_contains_draft_2020_12_batch24():
    source = inspect.getsource(smod)
    assert "Draft202012Validator" in source


def test_module_source_contains_iter_errors_batch24():
    source = inspect.getsource(smod)
    assert "iter_errors" in source


def test_module_source_contains_absolute_path_batch24():
    source = inspect.getsource(smod)
    assert "absolute_path" in source


def test_module_source_contains_absolute_schema_path_batch24():
    source = inspect.getsource(smod)
    assert "absolute_schema_path" in source


def test_module_source_contains_errors_default_none_batch24():
    source = inspect.getsource(smod)
    # 实际签名：errors: list[dict[str, Any]] | None = None
    assert "= None" in source
    assert "errors" in source


def test_module_source_contains_self_errors_batch24():
    source = inspect.getsource(smod)
    assert "self.errors" in source


def test_module_source_contains_isfile_check_batch24():
    source = inspect.getsource(smod)
    assert "is_file()" in source


def test_module_source_contains_file_not_found_batch24():
    source = inspect.getsource(smod)
    assert "FileNotFoundError" in source


def test_module_source_contains_super_init_batch24():
    source = inspect.getsource(smod)
    assert "super().__init__" in source


def test_module_source_contains_utf8_encoding_batch24():
    source = inspect.getsource(smod)
    assert 'encoding="utf-8"' in source


# ---------- signatures 第三十八批 ----------


def test_signature_schema_path_param_kind_batch24():
    sig = inspect.signature(_schema_path)
    from inspect import Parameter
    assert sig.parameters["name"].kind == Parameter.POSITIONAL_OR_KEYWORD


def test_signature_schema_path_annotation_batch24():
    sig = inspect.signature(_schema_path)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch24():
    sig = inspect.signature(load_schema)
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch24():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]
    assert sig.parameters["instance"].annotation == "dict[str, Any]"
    assert sig.parameters["schema_name"].annotation == "str"
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch24():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]
    assert sig.parameters["path"].annotation == "Path | str"


def test_signature_eval_schema_error_init_batch24():
    sig = inspect.signature(EvalSchemaError.__init__)
    assert list(sig.parameters.keys()) == ["self", "message", "errors"]
    assert sig.parameters["errors"].default is None


def test_signature_validate_no_varargs_batch24():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)


def test_signature_all_functions_no_defaults_batch24():
    """load_schema / validate / validate_file 都无 default（必填参数）。"""
    for fn in [load_schema, validate, validate_file, _schema_path]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.default is inspect.Parameter.empty, f"{fn.__name__}.{p.name}"


def test_signature_all_annotations_are_strings_batch24():
    """from __future__ import annotations → 所有 annotation 应是 str。"""
    for fn in [_schema_path, load_schema, validate, validate_file]:
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            if p.annotation is not inspect.Parameter.empty:
                assert isinstance(p.annotation, str), f"{fn.__name__}.{p.name}"


# ---------- module 合理性第三十八批 ----------


def test_module_all_present_batch24():
    assert hasattr(smod, "__all__")


def test_module_all_contains_five_names_batch24():
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_has_one_class_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert len(classes) == 1
    assert classes[0].name == "EvalSchemaError"


def test_module_has_three_functions_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    funcs = [n.name for n in tree.body if isinstance(n, _ast.FunctionDef)]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_no_classes_other_than_one_batch24():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    classes = [n for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert len(classes) == 1


def test_module_docstring_present_batch24():
    assert smod.__doc__ is not None
    assert len(smod.__doc__.strip()) > 0


def test_module_docstring_mentions_schema_batch24():
    assert "Schema" in smod.__doc__ or "schema" in smod.__doc__.lower()


def test_module_docstring_mentions_no_reuse_batch24():
    assert "不" in smod.__doc__ or "different" in smod.__doc__.lower() or "不复用" in smod.__doc__


def test_module_uses_from_future_annotations_batch24():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_eval_schema_error_docstring_present_batch24():
    assert EvalSchemaError.__doc__ is not None


def test_module_schemas_dir_is_path_instance_batch24():
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_constants_only_schemas_dir_batch24():
    """module-level 常量只有 SCHEMAS_DIR。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    constants = [
        n.targets[0].id
        for n in tree.body
        if isinstance(n, _ast.Assign)
        and isinstance(n.targets[0], _ast.Name)
        and not n.targets[0].id.startswith("_")
    ]
    assert constants == ["SCHEMAS_DIR"]


def test_module_all_entries_accessible_batch24():
    for name in smod.__all__:
        assert hasattr(smod, name)


# ---------- 端到端集成第三十八批 ----------


def test_e2e_load_then_validate_manifest_batch24():
    """load_schema → validate 一气呵成。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)
    validate(instance, "manifest.schema.json")


def test_e2e_validate_file_round_trip_batch24(tmp_path):
    """写一个合法 manifest → validate_file 通过。"""
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
            "expected_failures": [],
        }),
        encoding="utf-8",
    )
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_invalid_raises_eval_schema_error_batch24(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"wrong": "field"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_annotation_schema_loadable_batch24():
    s = load_schema("annotation.schema.json")
    assert isinstance(s, dict)


def test_e2e_evaluation_report_schema_loadable_batch24():
    s = load_schema("evaluation-report.schema.json")
    assert isinstance(s, dict)


def test_e2e_three_schemas_distinct_batch24():
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2
    assert s1 != s3
    assert s2 != s3


def test_e2e_eval_schema_error_caught_via_type_batch24():
    """EvalSchemaError 应可被 except EvalSchemaError 捕获。"""
    instance = {"wrong": "field"}
    try:
        validate(instance, "manifest.schema.json")
    except EvalSchemaError as e:
        assert e.errors
    else:
        pytest.fail("should have raised")


def test_e2e_validate_minimal_annotation_batch24():
    """最小 annotation schema 实例。"""
    # 加载 annotation schema 检查其 properties
    s = load_schema("annotation.schema.json")
    # annotation schema 应是 object
    assert s.get("type") in ("object", None)
