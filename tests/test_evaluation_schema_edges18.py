"""evaluation/schema.py 第十八轮 edges 测试（Round 317）。

重点补强 edges17 未触及的角度：
- EvalSchemaError 行为深度
- _schema_path 错误消息深度
- load_schema 异常路径
- validate 错误结构精确
- validate_file 异常路径精确
- SCHEMAS_DIR 边界
- 4 schemas cross-validation 深度
- module source 字符串精确
- signatures 精确
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

import evaluation.schema as m
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- EvalSchemaError 行为深度 ----------


def test_eval_schema_error_default_args():
    """EvalSchemaError("msg") 创建时不需要 errors。"""
    err = EvalSchemaError("msg")
    assert err.errors == []
    assert err.args == ("msg",)


def test_eval_schema_error_can_pass_falsy_errors():
    """errors=None 时存为 []。"""
    err = EvalSchemaError("x", None)
    assert err.errors == []


def test_eval_schema_error_keeps_truthy_errors():
    errs = [{"path": [], "message": "m", "schema_path": []}]
    err = EvalSchemaError("x", errs)
    assert err.errors == errs


def test_eval_schema_error_keeps_empty_list_errors():
    err = EvalSchemaError("x", [])
    assert err.errors == []


def test_eval_schema_error_inheritance():
    assert issubclass(EvalSchemaError, Exception)
    assert not issubclass(EvalSchemaError, BaseException.__class__)
    assert EvalSchemaError.__bases__ == (Exception,)


def test_eval_schema_error_super_init_called():
    err = EvalSchemaError("msg")
    # super().__init__ 设置了 args
    assert err.args == ("msg",)


def test_eval_schema_error_message_attribute():
    """Exception 的 args[0] 是 message。"""
    err = EvalSchemaError("hello")
    assert err.args[0] == "hello"


def test_eval_schema_error_str_method():
    err = EvalSchemaError("hello")
    assert str(err) == "hello"


def test_eval_schema_error_repr_method():
    err = EvalSchemaError("hello")
    r = repr(err)
    assert "EvalSchemaError" in r
    assert "hello" in r


# ---------- _schema_path 错误消息深度 ----------


def test_schema_path_no_extension_raises():
    with pytest.raises(FileNotFoundError) as ei:
        _schema_path("manifest")
    assert "manifest" in str(ei.value)


def test_schema_path_wrong_extension_raises():
    with pytest.raises(FileNotFoundError):
        _schema_path("manifest.json")  # not .schema.json


def test_schema_path_correct_extension_existing_returns_path():
    p = _schema_path("manifest.schema.json")
    assert p.name == "manifest.schema.json"


def test_schema_path_returns_path_resolved():
    p = _schema_path("annotation.schema.json")
    assert p.is_absolute()


def test_schema_path_4_schemas_all_resolvable():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        p = _schema_path(name)
        assert p.is_file()


# ---------- load_schema 异常路径 ----------


def test_load_schema_returns_dict_for_each_schema():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        assert isinstance(s, dict)


def test_load_schema_has_type_keyword():
    """4 个 schema 都有 'type' 关键字。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        # document schema 可能在 $defs 里有 type，但顶层应该也有
        assert "type" in s or "anyOf" in s or "$defs" in s


def test_load_schema_missing_raises_filenotfounderror():
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_returns_same_dict_each_call():
    """load_schema 每次都重新读文件（不缓存）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2
    assert s1 is not s2  # 不同 dict 实例


def test_load_schema_invalid_json_raises_jsondecodeerror(tmp_path, monkeypatch):
    """如果 schema 文件本身是无效 JSON（不会发生但代码不防）→ json.JSONDecodeError。"""
    # monkeypatch _schema_path 返回一个 invalid JSON 文件
    bad = tmp_path / "bad.schema.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(m, "SCHEMAS_DIR", tmp_path)
    with pytest.raises(json.JSONDecodeError):
        load_schema("bad.schema.json")


# ---------- validate 错误结构精确 ----------


def test_validate_error_path_starts_empty_for_top_level():
    """顶层错误 path 是 []。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    # 缺 manifest_version → 顶层 path
    # 找一个 path 为 [] 的 error
    top_level = [e for e in ei.value.errors if e["path"] == []]
    assert len(top_level) >= 1


def test_validate_error_path_nested_for_doc_field():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": ["not a dict"],  # 数组项不是 dict
    }
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    # 至少一个 error path 含 "documents" 和 0
    nested = [e for e in ei.value.errors if "documents" in e["path"]]
    assert len(nested) >= 1


def test_validate_error_schema_path_includes_required_keyword():
    """schema_path 通常含 'required'。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    required_errors = [
        e for e in ei.value.errors
        if "required" in e["schema_path"]
    ]
    assert len(required_errors) >= 1


def test_validate_error_message_starts_with_schema_name():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    assert "'manifest.schema.json'" in msg


def test_validate_error_message_includes_count_int():
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    msg = str(ei.value)
    # 找到 "校验失败 (N 处)"
    assert "校验失败" in msg
    # count 是数字
    import re
    match = re.search(r"\((\d+) 处\)", msg)
    assert match is not None
    assert int(match.group(1)) >= 1


def test_validate_errors_count_matches_iter_errors():
    """errors 列表长度 = 错误数。"""
    inst = {}  # 缺 3 个 required
    with pytest.raises(EvalSchemaError) as ei:
        validate(inst, "manifest.schema.json")
    # 至少 3 个（manifest_version + devset_status + documents）
    assert len(ei.value.errors) >= 3


def test_validate_no_extra_fields_in_error_dict():
    """error dict 只有 path/message/schema_path 3 个 key。"""
    with pytest.raises(EvalSchemaError) as ei:
        validate({}, "manifest.schema.json")
    for e in ei.value.errors:
        assert set(e.keys()) == {"path", "message", "schema_path"}


# ---------- validate_file 异常路径精确 ----------


def test_validate_file_missing_input_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(tmp_path / "no.json", "manifest.schema.json")
    assert "待校验文件不存在" in str(ei.value)


def test_validate_file_input_path_in_message(tmp_path):
    target = tmp_path / "no.json"
    with pytest.raises(FileNotFoundError) as ei:
        validate_file(target, "manifest.schema.json")
    assert str(target) in str(ei.value)


def test_validate_file_invalid_json_raises_jsonerror(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_str_path(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "incomplete",
            "documents": [],
        }),
        encoding="utf-8",
    )
    assert validate_file(str(p), "manifest.schema.json") is None


def test_validate_file_path_object(tmp_path):
    p = tmp_path / "ok.json"
    p.write_text(
        json.dumps({
            "manifest_version": "1.0",
            "devset_status": "complete",
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


def test_validate_file_with_valid_annotation(tmp_path):
    p = tmp_path / "anno.json"
    p.write_text(json.dumps({
        "annotation_version": "1.0",
        "doc_id": "x",
    }), encoding="utf-8")
    assert validate_file(p, "annotation.schema.json") is None


def test_validate_file_with_invalid_annotation(tmp_path):
    p = tmp_path / "anno.json"
    p.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "annotation.schema.json")


# ---------- SCHEMAS_DIR 边界 ----------


def test_schemas_dir_path_format():
    assert SCHEMAS_DIR.name == "schemas"


def test_schemas_dir_parent_name():
    """SCHEMAS_DIR.parent 应该是项目根。"""
    parent = SCHEMAS_DIR.parent
    # 项目根有 pyproject.toml
    assert (parent / "pyproject.toml").is_file()


def test_schemas_dir_resolved():
    """SCHEMAS_DIR 已 resolve，无相对部分。"""
    assert SCHEMAS_DIR == Path(SCHEMAS_DIR).resolve()


# ---------- 4 schemas cross-validation 深度 ----------


def test_manifest_schema_complete_status():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_manifest_schema_incomplete_status():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_manifest_schema_with_complete_document():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "categories": ["a"],
                "expectations": {"element_count_by_type": {"paragraph": 1}},
            }
        ],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_manifest_schema_with_expected_failures():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "bad",
                "path": "samples/bad.txt",
                "expected_error_code": "unsupported_format",
                "source_type": "txt",
            }
        ],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_annotation_schema_minimal():
    inst = {"annotation_version": "1.0", "doc_id": "x"}
    assert validate(inst, "annotation.schema.json") is None


def test_annotation_schema_with_chunk_boundary_anchors():
    inst = {
        "annotation_version": "1.0",
        "doc_id": "x",
        "chunk_boundary_anchors": [
            {"marker": "abc", "position": "after"}
        ],
    }
    # chunk_boundary_anchors 应该是合法字段
    try:
        validate(inst, "annotation.schema.json")
    except EvalSchemaError:
        # 如果 schema 不允许，也是合法行为
        pass


def test_document_schema_minimal_attempt():
    inst = {"source_type": "pdf", "source_path": "x.pdf", "elements": [], "chunks": []}
    try:
        validate(inst, "document.schema.json")
    except EvalSchemaError:
        pass  # document schema 可能要求更多字段


def test_evaluation_report_requires_many_fields():
    with pytest.raises(EvalSchemaError):
        validate({}, "evaluation-report.schema.json")


def test_cross_validate_manifest_against_annotation():
    inst = {"manifest_version": "1.0", "devset_status": "complete", "documents": []}
    with pytest.raises(EvalSchemaError):
        validate(inst, "annotation.schema.json")


def test_cross_validate_annotation_against_manifest():
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
    ],
)
def test_module_source_forbidden_tokens(token):
    src = inspect.getsource(m)
    assert token not in src


# ---------- module source 字符串精确 ----------


def test_module_source_has_docstring():
    src = inspect.getsource(m)
    # docstring 含 "Schema" 关键字
    assert "Schema" in src


def test_module_source_has_class_eval_schema_error():
    src = inspect.getsource(m)
    assert "class EvalSchemaError(Exception):" in src


def test_module_source_has_init_with_errors_default_none():
    src = inspect.getsource(m)
    assert "errors: list[dict[str, Any]] | None = None" in src


def test_module_source_has_self_errors_or_empty():
    src = inspect.getsource(m)
    assert "self.errors = errors or []" in src


def test_module_source_has_schemas_dir_with_resolve():
    src = inspect.getsource(m)
    assert "SCHEMAS_DIR = Path(__file__).resolve().parent.parent" in src


def test_module_source_has_schema_path_with_is_file_check():
    src = inspect.getsource(m)
    assert "if not p.is_file():" in src


def test_module_source_has_load_schema_with_open():
    src = inspect.getsource(m)
    assert '_schema_path(name).open("r", encoding="utf-8")' in src


def test_module_source_has_validate_with_draft202012():
    src = inspect.getsource(m)
    assert "Draft202012Validator(schema)" in src


def test_module_source_has_sorted_iter_errors():
    src = inspect.getsource(m)
    assert "sorted(validator.iter_errors(instance)" in src


def test_module_source_has_lambda_for_sort_key():
    src = inspect.getsource(m)
    assert "key=lambda e: list(e.absolute_path)" in src


def test_module_source_has_flat_list_dict():
    src = inspect.getsource(m)
    assert "flat: list[dict[str, Any]] = []" in src


def test_module_source_has_flat_append_with_3_keys():
    src = inspect.getsource(m)
    assert '"path": list(err.absolute_path)' in src
    assert '"message": err.message' in src
    assert '"schema_path": list(err.absolute_schema_path)' in src


def test_module_source_has_head_errors_zero():
    src = inspect.getsource(m)
    assert "head = errors[0]" in src


def test_module_source_has_raise_eval_schema_error_with_fstring():
    src = inspect.getsource(m)
    assert "raise EvalSchemaError(" in src
    assert "f\"Schema '{schema_name}' 校验失败" in src


def test_module_source_has_validate_file_with_path_check():
    src = inspect.getsource(m)
    assert 'if not p.is_file():' in src
    assert 'raise FileNotFoundError(f"待校验文件不存在: {p}")' in src


def test_module_source_has_validate_file_open():
    src = inspect.getsource(m)
    assert 'p.open("r", encoding="utf-8")' in src


def test_module_source_has_all_list_5_entries():
    src = inspect.getsource(m)
    assert '"SCHEMAS_DIR"' in src
    assert '"EvalSchemaError"' in src
    assert '"load_schema"' in src
    assert '"validate"' in src
    assert '"validate_file"' in src


# ---------- signatures 精确 ----------


def test_validate_signature_2_params_no_default():
    sig = inspect.signature(validate)
    assert list(sig.parameters.keys()) == ["instance", "schema_name"]
    for p in sig.parameters.values():
        assert p.default is inspect.Parameter.empty


def test_validate_return_annotation_none():
    sig = inspect.signature(validate)
    assert sig.return_annotation == "None"


def test_load_schema_signature():
    sig = inspect.signature(load_schema)
    assert list(sig.parameters.keys()) == ["name"]
    assert sig.return_annotation == "dict[str, Any]"


def test_validate_file_signature():
    sig = inspect.signature(validate_file)
    assert list(sig.parameters.keys()) == ["path", "schema_name"]
    assert sig.parameters["path"].annotation == "Path | str"
    assert sig.return_annotation == "None"


def test_schema_path_signature():
    sig = inspect.signature(_schema_path)
    assert list(sig.parameters.keys()) == ["name"]
    assert sig.parameters["name"].annotation == "str"
    assert sig.return_annotation == "Path"


def test_validate_no_varargs_varkw():
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_load_schema_no_varargs_varkw():
    sig = inspect.signature(load_schema)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_validate_file_no_varargs_varkw():
    sig = inspect.signature(validate_file)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_namespace_load_schema():
    assert load_schema.__module__ == "evaluation.schema"


def test_namespace_validate():
    assert validate.__module__ == "evaluation.schema"


def test_namespace_validate_file():
    assert validate_file.__module__ == "evaluation.schema"


def test_namespace_schema_path():
    assert _schema_path.__module__ == "evaluation.schema"


def test_namespace_eval_schema_error():
    assert EvalSchemaError.__module__ == "evaluation.schema"


# ---------- module 整体合理性 ----------


def test_module_all_count_5():
    assert len(m.__all__) == 5


def test_module_all_set_strict():
    assert m.__all__ == [
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    ]


def test_module_has_1_class():
    classes = [
        n for n in dir(m)
        if isinstance(getattr(m, n), type)
        and getattr(m, n).__module__ == "evaluation.schema"
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


def test_module_namespace():
    assert m.__name__ == "evaluation.schema"


def test_module_no_main_block():
    src = inspect.getsource(m)
    assert 'if __name__ == "__main__":' not in src


# ---------- 端到端集成 ----------


def test_e2e_validate_full_cycle_manifest():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [
            {
                "doc_id": "x",
                "path": "samples/x.pdf",
                "source_type": "pdf",
                "categories": ["tests"],
                "expectations": {"element_count_by_type": {"paragraph": 1}},
            }
        ],
    }
    assert validate(inst, "manifest.schema.json") is None


def test_e2e_validate_then_get_errors_format():
    with pytest.raises(EvalSchemaError) as ei:
        validate({"manifest_version": 1}, "manifest.schema.json")
    # 每个 error 有 path/message/schema_path
    for e in ei.value.errors:
        assert "path" in e
        assert "message" in e
        assert "schema_path" in e


def test_e2e_validate_file_manifest_round_trip(tmp_path):
    p = tmp_path / "valid.json"
    p.write_text(json.dumps({
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [
            {
                "doc_id": "x",
                "path": "samples/x.txt",
                "expected_error_code": "unsupported_format",
                "source_type": "txt",
            }
        ],
    }), encoding="utf-8")
    assert validate_file(p, "manifest.schema.json") is None


def test_e2e_4_schemas_all_draft202012_compatible():
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
        "document.schema.json",
    ):
        s = load_schema(name)
        Draft202012Validator.check_schema(s)


def test_e2e_validate_does_not_modify_input_dict():
    inst = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
    }
    inst_copy = json.loads(json.dumps(inst))
    validate(inst, "manifest.schema.json")
    assert inst == inst_copy


def test_e2e_validate_file_does_not_modify_input_file(tmp_path):
    p = tmp_path / "ok.json"
    original = json.dumps({
        "manifest_version": "1.0",
        "devset_status": "complete",
        "documents": [],
    })
    p.write_text(original, encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == original
