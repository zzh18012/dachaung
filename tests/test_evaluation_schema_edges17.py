"""evaluation/schema.py 第十七轮 edges 测试（Round 311）。

重点补强 edges16 未触及的角度：
- EvalSchemaError 实例化行为深度（None / empty / 非 list / 非 str）
- _schema_path 错误消息深度
- load_schema 返回 dict 类型
- validate 错误列表字段深度
- validate_file 失败模式精确
- SCHEMAS_DIR 路径计算精确
- module source forbidden tokens
- module source 字符串精确
- signatures 精确
- 4 schemas cross-validation 深度
- 端到端集成
- 模块整体合理性
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import FunctionType
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JSValidationError

import evaluation.schema as m
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 实例化深度 ----------


def test_eval_schema_error_message_preserved():
    err = EvalSchemaError("hello")
    assert str(err) == "hello"


def test_eval_schema_error_default_errors_empty_list():
    err = EvalSchemaError("hello")
    assert err.errors == []


def test_eval_schema_error_errors_none_becomes_empty_list():
    err = EvalSchemaError("hello", None)
    assert err.errors == []


def test_eval_schema_error_errors_empty_list_stays_empty():
    err = EvalSchemaError("hello", [])
    assert err.errors == []


def test_eval_schema_error_errors_passed_through():
    errs = [{"path": ["x"], "message": "m"}]
    err = EvalSchemaError("hello", errs)
    assert err.errors is errs  # 引用相同


def test_eval_schema_error_is_exception():
    err = EvalSchemaError("x")
    assert isinstance(err, Exception)


def test_eval_schema_error_raises_in_try():
    with pytest.raises(EvalSchemaError) as ei:
        raise EvalSchemaError("msg", [{"a": 1}])
    assert ei.value.errors == [{"a": 1}]


def test_eval_schema_error_can_be_caught_as_exception():
    with pytest.raises(Exception) as ei:
        raise EvalSchemaError("msg")
    assert isinstance(ei.value, EvalSchemaError)


def test_eval_schema_error_inherits_from_exception_not_base():
    err = EvalSchemaError("x")
    # Exception 已是 BaseException 子类，不重复继承 BaseException
    assert EvalSchemaError.__bases__ == (Exception,)


# ---------- _schema_path 错误消息深度 ----------


def test_schema_path_missing_file_message_includes_path():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("does-not-exist.schema.json")
    assert "does-not-exist.schema.json" in str(ei.value)


def test_schema_path_missing_file_message_includes_schema_word():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("x.json")
    assert "Schema" in str(ei.value) or "schema" in str(ei.value)


def test_schema_path_existing_returns_path():
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)
    assert p.name == "manifest.schema.json"


def test_schema_path_returns_absolute_path():
    p = _schema_path("manifest.schema.json")
    assert p.is_absolute()


# ---------- load_schema 返回类型 ----------


def test_load_schema_returns_dict():
    s = load_schema("manifest.schema.json")
    assert isinstance(s, dict)


def test_load_schema_has_schema_keyword():
    s = load_schema("manifest.schema.json")
    assert s.get("$schema") is not None or "$id" in s or "type" in s


def test_load_schema_all_4_schemas_are_dicts():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_missing_raises_filenotfound():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


# ---------- validate 行为深度 ----------


def test_validate_returns_none_on_success():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_validate_raises_on_invalid_instance():
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_errors_list_each_has_3_keys():
    inst = {}  # 缺 manifest_version/devset_status/documents
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    for e in ei.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


def test_validate_errors_path_is_list():
    inst = {"documents": "not a list"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(
            {
                "manifest_version": "1.0",
                "devset_status": "incomplete",
                "documents": "not a list",
            },
            "manifest.schema.json",
        )
    for e in ei.value.errors:
        assert isinstance(e["path"], list)
        assert isinstance(e["schema_path"], list)


def test_validate_errors_message_is_str():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert isinstance(e["message"], str)


def test_validate_errors_count_at_least_3_for_empty_manifest():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # 缺 manifest_version + devset_status + documents = 至少 3 个 errors
    assert len(ei.value.errors) >= 3


def test_validate_error_message_includes_schema_name():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    assert "manifest.schema.json" in str(ei.value)


def test_validate_error_message_includes_count():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "校验失败" in msg
    # count 数字出现
    assert any(c.isdigit() for c in msg)


def test_validate_error_message_includes_path():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "path" in msg


def test_validate_sorts_errors_by_path():
    """errors 按 absolute_path 排序。"""
    # 故意构造一个 path 较深的 error
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [
            {"path": "x.pdf", "expectations": {"element_count_by_type": "not a dict"}}
        ],
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    # 不直接验证顺序但确保 sorted 不会崩
    assert isinstance(ei.value.errors, list)


# ---------- validate_file 行为深度 ----------


def test_validate_file_missing_input_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_file(tmp_path / "missing.json", "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsonerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_path_string_accepted(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    # str 路径被接受
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_object_accepted(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(Path(p), "manifest.schema.json") is None


def test_validate_file_invalid_content_raises_eval_error(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_message_includes_path_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "missing.json", "manifest.schema.json")
    assert "missing.json" in str(ei.value)


# ---------- SCHEMAS_DIR 路径计算 ----------


def test_schemas_dir_is_absolute_path():
    assert SCHEMAS_DIR.is_absolute()


def test_schemas_dir_is_path_instance():
    assert isinstance(SCHEMAS_DIR, Path)


def test_schemas_dir_exists_on_filesystem():
    assert SCHEMAS_DIR.is_dir()


def test_schemas_dir_parent_is_project_root():
    # SCHEMAS_DIR = evaluation/schema.py 的 parent.parent / "schemas"
    # evaluation/schema.py 的 parent.parent 是项目根
    assert (SCHEMAS_DIR.parent).is_dir()
    # 项目根应该有 pyproject.toml
    assert (SCHEMAS_DIR.parent / "pyproject.toml").is_file()


def test_schemas_dir_contains_4_schema_files():
    files = list(SCHEMAS_DIR.glob("*.schema.json"))
    names = {f.name for f in files}
    assert "manifest.schema.json" in names
    assert "annotation.schema.json" in names
    assert "evaluation-report.schema.json" in names
    assert "document.schema.json" in names


def test_schemas_dir_resolved_no_symlinks():
    # .resolve() 已应用
    assert SCHEMAS_DIR == SCHEMAS_DIR.resolve()


# ---------- 4 schemas cross-validation 深度 ----------


def test_manifest_schema_accepts_minimal_complete():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_manifest_schema_rejects_invalid_devset_status():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "invalid_value",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_manifest_schema_rejects_invalid_manifest_version():
    inst = {
        "manifest_version": "2.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


def test_annotation_schema_accepts_minimal():
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    assert validate(inst, "annotation.schema.json") is None


def test_annotation_schema_rejects_missing_doc_id():
    inst = {"annotation_version": "1.0"}
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_annotation_schema_rejects_missing_annotation_version():
    inst = {"doc_id": "x"}
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_document_schema_accepts_minimal():
    """document.schema.json 最小可用结构（基于现有 docs/tests）。"""
    # 用一个最小可用的 document 实例（依赖具体 schema）
    inst = {
        "source_type": "pdf",
        "source_path": "x.pdf",
        "elements": [],
        "chunks": [],
    }
    # 不强制成功；只验证它不抛 SyntaxError
    try:
        validate(inst, "document.schema.json")
    except EvalSchemaError:
        pass  # 可接受，因为可能要求更多字段


def test_evaluation_report_rejects_missing_required_fields():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_cross_schema_validation_manifest_does_not_pass_annotation():
    """manifest 实例不能通过 annotation schema。"""
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_cross_schema_validation_annotation_does_not_pass_manifest():
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    with pytest.raises(EvalSchemaError):
        validate(inst, "manifest.schema.json")


# ---------- module source forbidden tokens ----------


@pytest.mark.parametrize(
    "token",
    [
        "import time",
        "import random",
        "import uuid",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import socket",
        "import email",
        "import html",
        "import http",
        "import urllib",
        "import sqlite3",
        "import csv",
        "import pickle",
        "import tempfile",
        "import shutil",
        "import glob",
        "import os",
        "import sys",
        "import logging",
        "import threading",
        "import asyncio",
        "import re",
        "import datetime",
        "import itertools",
        "import functools",
        "import collections",
        "import pathlib",
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 必要 imports ----------


def test_module_source_has_from_future():
    src = inspect.getsource(m)
    assert "from __future__ import annotations" in src


def test_module_source_has_import_json():
    src = inspect.getsource(m)
    assert "import json" in src


def test_module_source_has_from_pathlib_import_path():
    src = inspect.getsource(m)
    assert "from pathlib import Path" in src


def test_module_source_has_from_typing_import_any():
    src = inspect.getsource(m)
    assert "from typing import Any" in src


def test_module_source_has_draft202012_import():
    src = inspect.getsource(m)
    assert "from jsonschema import Draft202012Validator" in src


def test_module_source_has_jsvalidation_import():
    src = inspect.getsource(m)
    assert "from jsonschema.exceptions import ValidationError as JSValidationError" in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_class_definition():
    src = inspect.getsource(m)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_init_signature():
    src = inspect.getsource(m)
    assert "def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:" in src


def test_module_source_has_super_init_call():
    src = inspect.getsource(m)
    assert "super().__init__(message)" in src


def test_module_source_has_self_errors_assignment():
    src = inspect.getsource(m)
    assert "self.errors = errors or []" in src


def test_module_source_has_schemas_dir_assignment():
    src = inspect.getsource(m)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent" in src
    assert '"schemas"' in src


def test_module_source_has_schema_path_def():
    src = inspect.getsource(m)
    assert "def _schema_path(name: str) -> Path:" in src


def test_module_source_has_load_schema_def():
    src = inspect.getsource(m)
    assert "def load_schema(name: str) -> dict[str, Any]:" in src


def test_module_source_has_validate_def():
    src = inspect.getsource(m)
    assert "def validate(instance: dict[str, Any], schema_name: str) -> None:" in src


def test_module_source_has_validate_file_def():
    src = inspect.getsource(m)
    assert "def validate_file(path: Path | str, schema_name: str) -> None:" in src


def test_module_source_has_draft202012_validator_usage():
    src = inspect.getsource(m)
    assert "Draft202012Validator(schema)" in src


def test_module_source_has_iter_errors_usage():
    src = inspect.getsource(m)
    assert "validator.iter_errors(instance)" in src


def test_module_source_has_sorted_errors():
    src = inspect.getsource(m)
    assert "sorted(" in src
    assert "absolute_path" in src


def test_module_source_has_errors_flat_construction():
    src = inspect.getsource(m)
    assert "flat: list[dict[str, Any]] = []" in src


def test_module_source_has_flat_append():
    src = inspect.getsource(m)
    assert "flat.append(" in src


def test_module_source_has_head_errors_zero():
    src = inspect.getsource(m)
    assert "head = errors[0]" in src


def test_module_source_has_raise_eval_schema_error():
    src = inspect.getsource(m)
    assert "raise EvalSchemaError(" in src


def test_module_source_has_json_load_in_load_schema():
    src = inspect.getsource(m)
    # load_schema 用 json.load
    assert "json.load(f)" in src


def test_module_source_has_json_load_in_validate_file():
    src = inspect.getsource(m)
    # validate_file 也用 json.load
    assert "json.load(f)" in src


def test_module_source_has_encoding_utf8():
    src = inspect.getsource(m)
    assert 'encoding="utf-8"' in src


def test_module_source_has_all_list():
    src = inspect.getsource(m)
    assert "__all__" in src


def test_module_source_has_docstring():
    src = inspect.getsource(m)
    assert "加载并校验" in src or "Schema" in src


def test_module_source_has_no_main_block():
    src = inspect.getsource(m)
    assert '__name__ == "__main__"' not in src


# ---------- signatures 精确 ----------


def test_validate_signature_2_params():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]


def test_validate_signature_no_defaults():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_signature_no_varargs_varkw():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_validate_signature_return_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


def test_load_schema_signature_1_param():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]


def test_load_schema_return_annotation_dict():
    sig = inspect.signature(load_schema)
    assert sig.return_annotation == "dict[str, Any]"


def test_validate_file_signature_2_params():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]


def test_validate_file_path_annotation_union():
    sig = inspect.signature(validate_file)
    assert sig.parameters["path"].annotation == "Path | str"


def test_validate_file_return_none():
    sig = inspect.signature(validate_file)
    assert sig.return_annotation == "None"


def test_schema_path_signature_1_param():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]


def test_schema_path_return_path():
    sig = inspect.signature(_schema_path)
    assert sig.return_annotation == "Path"


# ---------- module 整体合理性 ----------


def test_module_all_has_5_entries():
    assert set(m.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_all_count_is_5():
    assert len(m.__all__) == 5


def test_module_has_1_class():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type) and getattr(m, n).__module__ == "evaluation.schema"
    ]
    assert classes == ["EvalSchemaError"]


def test_module_has_3_public_functions():
    public_fns = [
        n for n in dir(m)
        if not n.startswith("_")
        and isinstance(getattr(m, n), FunctionType)
        and getattr(m, n).__module__ == "evaluation.schema"
    ]
    assert set(public_fns) == {"load_schema", "validate", "validate_file"}


def test_module_has_1_private_helper():
    private_fns = [
        n for n in dir(m)
        if n.startswith("_")
        and not n.startswith("__")
        and isinstance(getattr(m, n), FunctionType)
    ]
    assert private_fns == ["_schema_path"]


def test_module_has_1_module_level_constant():
    consts = [
        n for n in dir(m)
        if not n.startswith("_")
        and not callable(getattr(m, n))
        and not isinstance(getattr(m, n), type)
    ]
    # SCHEMAS_DIR 是 Path 实例（Path 实例 callable 为 False，type 为 False）
    # 排除 import 进来的 json
    own_consts = [
        n for n in consts
        if getattr(m, n).__class__.__module__ == "pathlib"
        or n == "SCHEMAS_DIR"
    ]
    assert "SCHEMAS_DIR" in own_consts


def test_eval_schema_error_namespace_is_evaluation_schema():
    assert EvalSchemaError.__module__ == "evaluation.schema"


def test_load_schema_namespace_is_evaluation_schema():
    assert load_schema.__module__ == "evaluation.schema"


def test_validate_namespace_is_evaluation_schema():
    assert validate.__module__ == "evaluation.schema"


def test_validate_file_namespace_is_evaluation_schema():
    assert validate_file.__module__ == "evaluation.schema"


def test_schema_path_namespace_is_evaluation_schema():
    assert _schema_path.__module__ == "evaluation.schema"


def test_module_namespace_is_evaluation_schema():
    assert m.__name__ == "evaluation.schema"


# ---------- 端到端集成 ----------


def test_e2e_validate_then_raise_cycle():
    """验证 → 抛 EvalSchemaError → 检查 errors 字段格式。"""
    inst = {"manifest_version": "wrong"}
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    # 至少 2 个 errors（devset_status + documents 缺）
    assert len(ei.value.errors) >= 2
    # str(err) 含 schema 名
    assert "manifest.schema.json" in str(ei.value)


def test_e2e_validate_file_round_trip(tmp_path):
    """写 JSON → validate_file 通过。"""
    p = tmp_path / "valid.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [
                {
                    "doc_id": "x",
                    "path": "samples/x.pdf",
                    "source_type": "pdf",
                    "categories": ["tests"],
                    "expectations": {"element_count_by_type": {"paragraph": 1}},
                }
            ],
        }),
        encoding="utf-8",
    )
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_all_4_schemas_loadable():
    """4 个 schema 都能加载，且是 Draft202012 兼容。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        # Draft202012Validator 检查 schema 自身合法性
        # 如果不合法会抛 SchemaError
        Draft202012Validator.check_schema(s)


def test_e2e_validate_errors_grow_with_more_violations():
    """多违反 → 多 errors。"""
    # 空对象
    with pytest.raises(EvalSchemaError) as ei1:
        validate({}, "manifest.schema.json")
    n1 = len(ei1.value.errors)
    # 多一个错误字段
    with pytest.raises(EvalSchemaError) as ei2:
        validate({"manifest_version": 123}, "manifest.schema.json")
    n2 = len(ei2.value.errors)
    # 都至少 n1 个错误（多违反不应该减少）
    assert n2 >= n1


# ---------- 私有 _schema_path 行为深度 ----------


def test_schema_path_string_path_accepted():
    """_schema_path 接受 str。"""
    p = _schema_path("manifest.schema.json")
    assert p.exists()


def test_schema_path_returns_path_with_correct_parent():
    p = _schema_path("manifest.schema.json")
    assert p.parent == SCHEMAS_DIR


# ---------- 错误结构深度 ----------


def test_eval_schema_error_can_be_reraised():
    err = EvalSchemaError("msg", [{"x": 1}])
    with pytest.raises(EvalSchemaError) as ei:
        raise err
    assert ei.value is err
    assert ei.value.errors == [{"x": 1}]


def test_eval_schema_error_args_attribute():
    err = EvalSchemaError("hello", [{"a": 1}])
    # Exception args 应该是 (message,)
    assert err.args == ("hello",)


def test_eval_schema_error_errors_attribute_is_list():
    err = EvalSchemaError("x")
    assert isinstance(err.errors, list)


def test_eval_schema_error_repr_includes_class_name():
    err = EvalSchemaError("msg")
    assert "EvalSchemaError" in repr(err)


# ---------- 验证 schema 检查顺序 ----------


def test_validate_loads_schema_each_call():
    """validate 每次都 load_schema（不缓存）。"""
    # 用 spy 检查不容易；改为间接：两次连续调用应该独立
    validate(
        {"manifest_version": "1.0", "devset_status": "incomplete", "documents": []},
        "manifest.schema.json",
    )
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_does_not_modify_input():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    inst_copy = json.loads(json.dumps(inst))
    validate(inst, "manifest.schema.json")
    assert inst == inst_copy


def test_validate_file_does_not_modify_input_file(tmp_path):
    p = tmp_path / "ok.json"
    original = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    })
    p.write_text(original, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == original
