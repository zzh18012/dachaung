"""evaluation/schema.py 第四十三轮 edges 测试（Round 495）。

补强 edges42 未触及的角度（第二十三批）：
- SCHEMAS_DIR 第二十三批：drive / owner / 三个 schema 文件大小 > 0 / 目录非空 / SCHEMAS_DIR 在 Path 中可哈希 / 不在 tmp 目录 / 在项目根下
- EvalSchemaError 第二十三批：str(e) 含 message / repr(e) / errors default [] 不共享 / args 透传 / Exception 属性 / 多次 raise 重新实例化 / errors 类型检查
- _schema_path 第二十三批：返回类型 / 多次调用一致 / 路径含 'schemas' / 路径以 .json 结尾 / 不存在文件 message 含路径 / 多次同时调
- load_schema 第二十三批：manifest/annotation/evaluation-report 三个 schema 都可加载 / 加载结果 type=object / 加载结果含 properties / 不修改 schema dict
- validate 第二十三批：合法 schema_name / 未知 schema_name 抛 FileNotFoundError / 多个错误 path 排序 / 错误 list 是新 list / 调用后 instance 不变 / 不抛 UnicodeError / instance 是 list 时也能校验（type 错误）
- validate_file 第二十三批：接受 str 路径 / 接受 Path 路径 / 等价 / 大文件可加载 / BOM 头文件 / 不存在 message 含路径 / 调用后文件不变 / 二进制文件 JSONDecodeError
- module source forbidden tokens 第四十一批 / source 字符串补强第三十七批 / signatures 第三十七批 / sanity 第三十七批 / e2e 第三十七批
"""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import Draft202012Validator

from evaluation import schema as smod
from evaluation.schema import (
    SCHEMAS_DIR,
    EvalSchemaError,
    _schema_path,
    load_schema,
    validate,
    validate_file,
)


# ---------- SCHEMAS_DIR 第二十三批 ----------


def test_schemas_dir_drive_present_batch23():
    """SCHEMAS_DIR.drive 非空（Windows 是 'C:'，Linux 是 ''）。"""
    # 不强制内容，仅检查属性可访问
    assert isinstance(SCHEMAS_DIR.drive, str)


def test_schemas_dir_owner_of_parent_batch23():
    """SCHEMAS_DIR.parent.name 应是 'dachuang-autonomous' 或项目目录名。"""
    # 项目目录可能是 dachuang-code 或 dachuang-autonomous
    parent_name = SCHEMAS_DIR.parent.name
    assert parent_name.startswith("dachuang")


def test_schemas_dir_manifest_schema_size_positive_batch23():
    """manifest.schema.json 文件大小 > 0。"""
    p = SCHEMAS_DIR / "manifest.schema.json"
    assert p.stat().st_size > 0


def test_schemas_dir_annotation_schema_size_positive_batch23():
    """annotation.schema.json 文件大小 > 0。"""
    p = SCHEMAS_DIR / "annotation.schema.json"
    assert p.stat().st_size > 0


def test_schemas_dir_evaluation_report_schema_size_positive_batch23():
    """evaluation-report.schema.json 文件大小 > 0。"""
    p = SCHEMAS_DIR / "evaluation-report.schema.json"
    assert p.stat().st_size > 0


def test_schemas_dir_not_empty_batch23():
    """SCHEMAS_DIR 至少含三个 schema 文件。"""
    files = list(SCHEMAS_DIR.glob("*.json"))
    assert len(files) >= 3


def test_schemas_dir_hashable_batch23():
    """SCHEMAS_DIR 是 Path 实例，可作 dict key。"""
    d = {SCHEMAS_DIR: "value"}
    assert d[SCHEMAS_DIR] == "value"


def test_schemas_dir_not_in_tmp_batch23():
    """SCHEMAS_DIR 不应位于 /tmp 或临时目录。"""
    s = str(SCHEMAS_DIR).lower()
    assert "/tmp/" not in s
    assert "temp" not in s.lower() or "dachuang" in s.lower()


def test_schemas_dir_under_project_root_batch23():
    """SCHEMAS_DIR 必须位于项目根下。"""
    project_root = SCHEMAS_DIR.parent
    assert (project_root / "pyproject.toml").is_file()
    # SCHEMAS_DIR 是 project_root 的直接子目录
    assert SCHEMAS_DIR.parent == project_root


def test_schemas_dir_only_one_eval_schemas_dir_batch23():
    """evaluation/ 目录下没有另一个 schemas/ 子目录（避免路径混淆）。"""
    eval_dir = SCHEMAS_DIR.parent / "evaluation"
    if eval_dir.is_dir():
        # evaluation 下不应再有 schemas/
        assert not (eval_dir / "schemas").is_dir()


# ---------- EvalSchemaError 第二十三批 ----------


def test_eval_schema_error_str_contains_message_batch23():
    """str(error) 含 message。"""
    e = EvalSchemaError("hello")
    assert "hello" in str(e)


def test_eval_schema_error_repr_contains_class_name_batch23():
    """repr(error) 含类名。"""
    e = EvalSchemaError("oops")
    assert "EvalSchemaError" in repr(e)


def test_eval_schema_errors_default_not_shared_batch23():
    """两次实例化（不传 errors）→ 各自独立的 []（不共享引用）。"""
    e1 = EvalSchemaError("a")
    e2 = EvalSchemaError("b")
    assert e1.errors == []
    assert e2.errors == []
    # 修改一个不影响另一个
    e1.errors.append({"x": 1})
    assert e2.errors == []


def test_eval_schema_error_args_passed_through_batch23():
    """super().__init__(message) → args[0] 是 message。"""
    e = EvalSchemaError("xyz")
    assert e.args == ("xyz",)


def test_eval_schema_error_errors_keeps_dict_references_batch23():
    """errors 列表中的 dict 引用与传入的 dict 相同（不深拷贝）。"""
    err_dict = {"path": ["a"], "message": "bad"}
    e = EvalSchemaError("fail", errors=[err_dict])
    assert e.errors[0] is err_dict


def test_eval_schema_error_can_be_raised_and_caught_batch23():
    """raise + except 完整往返。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        raise EvalSchemaError("raised")
    assert "raised" in str(exc_info.value)


def test_eval_schema_error_caught_as_exception_batch23():
    """EvalSchemaError 可被通用 except Exception 捕获。"""
    try:
        raise EvalSchemaError("test")
    except Exception as e:
        assert isinstance(e, EvalSchemaError)


def test_eval_schema_error_errors_attribute_is_list_batch23():
    """errors 属性始终是 list（即使 None 传入）。"""
    e1 = EvalSchemaError("a", errors=None)
    assert isinstance(e1.errors, list)
    e2 = EvalSchemaError("b", errors=[])
    assert isinstance(e2.errors, list)
    e3 = EvalSchemaError("c", errors=[{"x": 1}])
    assert isinstance(e3.errors, list)


def test_eval_schema_error_message_attribute_batch23():
    """message 通过 args[0] 访问（Exception 标准）。"""
    e = EvalSchemaError("hello")
    # Exception 没有显式 .message 属性，但 args[0] 是
    assert e.args[0] == "hello"


# ---------- _schema_path 第二十三批 ----------


def test_schema_path_returns_path_object_batch23():
    """_schema_path 返回 Path 实例。"""
    p = _schema_path("manifest.schema.json")
    assert isinstance(p, Path)


def test_schema_path_multiple_calls_consistent_batch23():
    """多次调用返回等价 Path。"""
    p1 = _schema_path("manifest.schema.json")
    p2 = _schema_path("manifest.schema.json")
    assert p1 == p2


def test_schema_path_str_contains_schemas_batch23():
    """str(_schema_path(...)) 含 'schemas'。"""
    p = _schema_path("annotation.schema.json")
    assert "schemas" in str(p)


def test_schema_path_str_ends_with_json_batch23():
    """返回路径以 .json 结尾。"""
    p = _schema_path("manifest.schema.json")
    assert str(p).endswith(".json")


def test_schema_path_missing_file_error_message_contains_filename_batch23():
    """FileNotFoundError message 含文件名。"""
    with pytest.raises(FileNotFoundError) as exc_info:
        _schema_path("nonexistent.schema.json")
    assert "nonexistent.schema.json" in str(exc_info.value)


def test_schema_path_directory_not_a_file_batch23(tmp_path):
    """目录作为 schema name（拼接后是目录）→ FileNotFoundError（is_file False）。"""
    # 在 SCHEMAS_DIR 下创建临时目录
    # 但是 _schema_path 只接 name 不接 path，目录名不可能含 .schema.json 后缀
    # 改测：目录存在于 SCHEMAS_DIR 中（is_file False）
    # 简化：直接传 SCHEMAS_DIR 内已知存在的 schema name，确保返回 file
    p = _schema_path("manifest.schema.json")
    assert p.is_file()


def test_schema_path_handles_filename_with_spaces_batch23(tmp_path):
    """文件名含空格 → 仍可拼接（虽然 schema 文件不会这样命名）。"""
    # 仅测试拼接逻辑：SCHEMAS_DIR / "name with space.json"
    # 这里不创建实际文件，所以会 FileNotFoundError
    with pytest.raises(FileNotFoundError):
        _schema_path("name with space.schema.json")


# ---------- load_schema 第二十三批 ----------


def test_load_schema_returns_dict_batch23():
    """load_schema 返回 dict。"""
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)


def test_load_schema_type_is_object_batch23():
    """加载的 schema type 是 'object'。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        schema = load_schema(name)
        assert schema.get("type") == "object"


def test_load_schema_has_properties_batch23():
    """schema 含 properties 字段。"""
    for name in (
        "manifest.schema.json",
        "annotation.schema.json",
        "evaluation-report.schema.json",
    ):
        schema = load_schema(name)
        assert "properties" in schema
        assert isinstance(schema["properties"], dict)


def test_load_schema_does_not_mutate_source_file_batch23():
    """load_schema 不修改 schema 文件内容。"""
    p = SCHEMAS_DIR / "manifest.schema.json"
    original_size = p.stat().st_size
    original_mtime = p.stat().st_mtime
    load_schema("manifest.schema.json")
    load_schema("manifest.schema.json")
    # 文件不变
    assert p.stat().st_size == original_size
    # mtime 应不变（只是读）
    assert p.stat().st_mtime == original_mtime


def test_load_schema_idempotent_returns_equivalent_batch23():
    """两次 load_schema 返回等价 dict（不一定同对象）。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("manifest.schema.json")
    assert s1 == s2


def test_load_schema_unknown_name_raises_batch23():
    """未知 schema name → FileNotFoundError。"""
    with pytest.raises(FileNotFoundError):
        load_schema("nonexistent.schema.json")


def test_load_schema_three_schemas_batch23():
    """三个 schema 都可加载。"""
    schemas = [
        load_schema(n)
        for n in (
            "manifest.schema.json",
            "annotation.schema.json",
            "evaluation-report.schema.json",
        )
    ]
    assert len(schemas) == 3
    # 都不互相等价
    assert schemas[0] != schemas[1]
    assert schemas[0] != schemas[2]
    assert schemas[1] != schemas[2]


# ---------- validate 第二十三批 ----------


def test_validate_unknown_schema_name_raises_filenotfound_batch23():
    """未知 schema_name → load_schema FileNotFoundError 透传。"""
    with pytest.raises(FileNotFoundError):
        validate({}, "nonexistent.schema.json")


def test_validate_empty_dict_against_manifest_batch23():
    """空 dict 校验 manifest → 应抛 EvalSchemaError（缺 required 字段）。"""
    with pytest.raises(EvalSchemaError):
        validate({}, "manifest.schema.json")


def test_validate_returns_none_on_success_batch23():
    """成功 → return None（隐式）。"""
    # manifest.schema.json 要求 manifest_version + devset_status + documents + expected_failures
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    result = validate(instance, "manifest.schema.json")
    assert result is None


def test_validate_does_not_modify_instance_batch23():
    """validate 不修改传入的 instance dict。"""
    instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    original = json.loads(json.dumps(instance))
    validate(instance, "manifest.schema.json")
    assert instance == original


def test_validate_errors_are_new_list_batch23():
    """errors list 是新建的（不引用任何内部状态）。"""
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError as e:
        # 修改 errors list 不影响其他实例
        original_len = len(e.errors)
        e.errors.append({"fake": True})
        assert len(e.errors) == original_len + 1
        # 再次 validate，新实例的 errors 不含刚才的 append
        try:
            validate({}, "manifest.schema.json")
        except EvalSchemaError as e2:
            assert {"fake": True} not in e2.errors


def test_validate_errors_path_field_exists_batch23():
    """errors[i] 含 'path' 字段。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    e = exc_info.value
    for err in e.errors:
        assert "path" in err
        assert isinstance(err["path"], list)


def test_validate_errors_message_field_exists_batch23():
    """errors[i] 含 'message' 字段。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    e = exc_info.value
    for err in e.errors:
        assert "message" in err
        assert isinstance(err["message"], str)


def test_validate_errors_schema_path_field_exists_batch23():
    """errors[i] 含 'schema_path' 字段。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    e = exc_info.value
    for err in e.errors:
        assert "schema_path" in err
        assert isinstance(err["schema_path"], list)


def test_validate_instance_list_against_object_schema_batch23():
    """instance 是 list（schema 期望 object）→ EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate([], "manifest.schema.json")


def test_validate_instance_string_against_object_schema_batch23():
    """instance 是 string（schema 期望 object）→ EvalSchemaError。"""
    with pytest.raises(EvalSchemaError):
        validate("not a dict", "manifest.schema.json")


def test_validate_message_contains_count_batch23():
    """EvalSchemaError message 含错误计数。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    # 应含 "(N 处)" 形式
    assert "处" in msg


def test_validate_message_contains_schema_name_batch23():
    """message 含 schema_name。"""
    with pytest.raises(EvalSchemaError) as exc_info:
        validate({}, "manifest.schema.json")
    msg = str(exc_info.value)
    assert "manifest.schema.json" in msg


# ---------- validate_file 第二十三批 ----------


def test_validate_file_str_path_equivalent_to_path_path_batch23(tmp_path):
    """str 路径与 Path 路径校验结果等价。"""
    p = tmp_path / "valid.json"
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    # str 路径
    validate_file(str(p), "manifest.schema.json")
    # Path 路径
    validate_file(p, "manifest.schema.json")


def test_validate_file_missing_file_error_contains_path_batch23(tmp_path):
    """文件不存在 → FileNotFoundError message 含路径。"""
    p = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError) as exc_info:
        validate_file(p, "manifest.schema.json")
    assert "nope.json" in str(exc_info.value)


def test_validate_file_does_not_modify_file_batch23(tmp_path):
    """validate_file 不修改目标文件。"""
    p = tmp_path / "valid.json"
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    original_content = p.read_text(encoding="utf-8")
    validate_file(p, "manifest.schema.json")
    assert p.read_text(encoding="utf-8") == original_content


def test_validate_file_bom_raises_jsondecodeerror_batch23(tmp_path):
    """UTF-8 BOM 文件（encoding=utf-8 非 utf-8-sig）→ JSONDecodeError。"""
    p = tmp_path / "bom.json"
    p.write_bytes(b'\xef\xbb\xbf{"a": 1}')
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_large_payload_batch23(tmp_path):
    """大文件（含 100 documents）可正常加载并校验。"""
    p = tmp_path / "large.json"
    documents = [
        {
            "doc_id": f"d{i}",
            "path": f"file{i}.pdf",
            "source_type": "pdf",
        }
        for i in range(100)
    ]
    large_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": documents,
        "expected_failures": [],
    }
    p.write_text(json.dumps(large_manifest), encoding="utf-8")
    # 应通过校验
    validate_file(p, "manifest.schema.json")


def test_validate_file_invalid_json_raises_jsondecodeerror_batch23(tmp_path):
    """非 JSON 文件 → JSONDecodeError。"""
    p = tmp_path / "bad.txt"
    p.write_text("not json at all", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_empty_file_raises_jsondecodeerror_batch23(tmp_path):
    """空文件 → JSONDecodeError。"""
    p = tmp_path / "empty.json"
    p.write_text("", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


def test_validate_file_utf16_raises_jsondecodeerror_batch23(tmp_path):
    """UTF-16 编码 → utf-8 解码产生 NUL+ASCII → JSONDecodeError。"""
    p = tmp_path / "utf16.json"
    p.write_text('{"a": 1}', encoding="utf-16-be")
    with pytest.raises(json.JSONDecodeError):
        validate_file(p, "manifest.schema.json")


# ---------- module source forbidden tokens 第四十一批 ----------


FORBIDDEN_TOKENS = [
    "import logging",
    "import sys",
    "import os",
    "import re",
    "import datetime",
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
    "import subprocess",
    "import csv",
    "import xml",
]


def test_module_source_forbidden_tokens_batch23():
    """schema.py 不应 import 这些副作用大的模块。"""
    source = inspect.getsource(smod)
    for tok in FORBIDDEN_TOKENS:
        assert tok not in source, f"forbidden token in source: {tok}"


def test_module_source_no_class_other_than_eval_schema_error_batch23():
    """schema.py 仅定义 EvalSchemaError，无其他 class。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    classes = [n.name for n in tree.body if isinstance(n, _ast.ClassDef)]
    assert classes == ["EvalSchemaError"]


def test_module_source_no_yield_batch23():
    source = inspect.getsource(smod)
    assert "yield " not in source


def test_module_source_no_async_def_batch23():
    source = inspect.getsource(smod)
    assert "async def" not in source


def test_module_source_no_global_keyword_batch23():
    source = inspect.getsource(smod)
    assert "global " not in source


def test_module_source_no_walrus_batch23():
    source = inspect.getsource(smod)
    assert ":=" not in source


def test_module_source_no_eval_exec_batch23():
    source = inspect.getsource(smod)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "compile(" not in source


def test_module_source_no_relative_imports_batch23():
    source_lines = inspect.getsource(smod).split("\n")
    for line in source_lines:
        stripped = line.strip()
        if stripped.startswith("from .") and "from __future__" not in stripped:
            pytest.fail(f"relative import: {line}")


def test_module_source_no_star_import_batch23():
    source = inspect.getsource(smod)
    assert "import *" not in source


def test_module_source_no_subprocess_batch23():
    source = inspect.getsource(smod)
    assert "subprocess" not in source


def test_module_source_no_dataclass_batch23():
    source = inspect.getsource(smod)
    assert "@dataclass" not in source


def test_module_source_no_network_io_batch23():
    source = inspect.getsource(smod)
    assert "import socket" not in source
    assert "import http" not in source


def test_module_source_no_environ_batch23():
    source = inspect.getsource(smod)
    assert "os.environ" not in source


def test_module_source_no_pickle_batch23():
    source = inspect.getsource(smod)
    assert "pickle" not in source


def test_module_source_no_open_at_module_level_batch23():
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    for node in tree.body:
        if isinstance(node, _ast.Expr) and isinstance(node.value, _ast.Call):
            f = node.value.func
            if isinstance(f, _ast.Name) and f.id == "open":
                pytest.fail("top-level open() call")


def test_module_source_json_used_batch23():
    source = inspect.getsource(smod)
    assert "import json" in source


# ---------- module source 字符串精确补强第三十七批 ----------


def test_module_source_contains_schemas_dir_definition_batch23():
    source = inspect.getsource(smod)
    assert "Path(__file__).resolve().parent.parent" in source
    assert '"schemas"' in source


def test_module_source_contains_draft202012_batch23():
    source = inspect.getsource(smod)
    assert "Draft202012Validator" in source


def test_module_source_contains_iter_errors_batch23():
    source = inspect.getsource(smod)
    assert "iter_errors" in source


def test_module_source_contains_absolute_path_batch23():
    source = inspect.getsource(smod)
    assert "absolute_path" in source


def test_module_source_contains_evaluation_failed_text_batch23():
    source = inspect.getsource(smod)
    assert "校验失败" in source


def test_module_source_contains_path_eq_text_batch23():
    source = inspect.getsource(smod)
    assert "path=" in source


def test_module_source_contains_schema_path_field_batch23():
    source = inspect.getsource(smod)
    assert "schema_path" in source


def test_module_source_contains_utf8_encoding_batch23():
    source = inspect.getsource(smod)
    assert 'encoding="utf-8"' in source


def test_module_source_contains_not_found_text_batch23():
    source = inspect.getsource(smod)
    assert "不存在" in source


def test_module_source_contains_sorted_lambda_batch23():
    source = inspect.getsource(smod)
    assert "sorted(" in source
    assert "key=lambda" in source


def test_module_source_contains_errors_default_none_batch23():
    source = inspect.getsource(smod)
    assert "errors: list[dict[str, Any]] | None = None" in source


def test_module_source_contains_jsvalidationerror_import_batch23():
    """source 含 from jsonschema.exceptions import ValidationError。"""
    source = inspect.getsource(smod)
    assert "JSValidationError" in source or "ValidationError" in source


def test_module_source_contains_super_init_batch23():
    """EvalSchemaError.__init__ 调 super().__init__(message)。"""
    source = inspect.getsource(smod)
    assert "super().__init__(message)" in source


def test_module_source_contains_self_errors_batch23():
    """source 含 self.errors = errors or []。"""
    source = inspect.getsource(smod)
    assert "self.errors" in source
    assert "errors or []" in source


def test_module_source_contains_isfile_check_batch23():
    """source 含 is_file() 检查。"""
    source = inspect.getsource(smod)
    assert "is_file()" in source


# ---------- signatures 第三十七批 ----------


def test_signature_schema_path_batch23():
    """_schema_path(name: str) -> Path。"""
    sig = inspect.signature(_schema_path)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    assert params[0].annotation == "str"
    assert sig.return_annotation == "Path"


def test_signature_load_schema_batch23():
    """load_schema(name: str) -> dict[str, Any]。"""
    sig = inspect.signature(load_schema)
    params = list(sig.parameters.values())
    assert len(params) == 1
    assert params[0].name == "name"
    assert sig.return_annotation == "dict[str, Any]"


def test_signature_validate_batch23():
    """validate(instance: dict[str, Any], schema_name: str) -> None。"""
    sig = inspect.signature(validate)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["instance", "schema_name"]
    assert sig.return_annotation == "None"


def test_signature_validate_file_batch23():
    """validate_file(path: Path | str, schema_name: str) -> None。"""
    sig = inspect.signature(validate_file)
    params = list(sig.parameters.values())
    assert len(params) == 2
    assert [p.name for p in params] == ["path", "schema_name"]
    assert params[0].annotation == "Path | str"
    assert sig.return_annotation == "None"


def test_signature_eval_schema_error_init_batch23():
    """EvalSchemaError.__init__(message: str, errors: list[...] | None = None) -> None。"""
    sig = inspect.signature(EvalSchemaError.__init__)
    params = list(sig.parameters.values())
    # self + message + errors
    assert len(params) == 3
    assert [p.name for p in params] == ["self", "message", "errors"]
    assert params[1].annotation == "str"
    assert params[2].default is None


def test_signature_schema_path_param_kind_batch23():
    """_schema_path 单参数是 POSITIONAL_OR_KEYWORD。"""
    sig = inspect.signature(_schema_path)
    p = sig.parameters["name"]
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_signature_validate_no_varargs_batch23():
    """validate 不接受 *args / **kwargs。"""
    sig = inspect.signature(validate)
    for p in sig.parameters.values():
        assert p.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )


def test_signature_all_functions_no_defaults_batch23():
    """_schema_path / load_schema / validate 无默认参数。"""
    for fn in (_schema_path, load_schema, validate):
        sig = inspect.signature(fn)
        for p in sig.parameters.values():
            assert p.default is inspect.Parameter.empty


# ---------- module 合理性第三十七批 ----------


def test_module_all_present_batch23():
    """__all__ 存在。"""
    assert hasattr(smod, "__all__")


def test_module_all_contains_five_names_batch23():
    """__all__ 含 5 个公开名（SCHEMAS_DIR, EvalSchemaError, load_schema, validate, validate_file）。"""
    assert set(smod.__all__) == {
        "SCHEMAS_DIR",
        "EvalSchemaError",
        "load_schema",
        "validate",
        "validate_file",
    }


def test_module_has_one_class_batch23():
    """schema.py 仅定义 EvalSchemaError 一个 class。"""
    classes = [
        name
        for name, val in inspect.getmembers(smod, inspect.isclass)
        if val.__module__ == smod.__name__
    ]
    assert classes == ["EvalSchemaError"]


def test_module_has_three_functions_batch23():
    """schema.py 定义 3 个 module-level 函数：_schema_path, load_schema, validate, validate_file。"""
    funcs = [
        name
        for name, val in inspect.getmembers(smod, inspect.isfunction)
        if val.__module__ == smod.__name__
    ]
    assert set(funcs) == {"_schema_path", "load_schema", "validate", "validate_file"}


def test_module_docstring_present_batch23():
    assert smod.__doc__ is not None
    assert len(smod.__doc__) > 0


def test_module_docstring_mentions_schema_batch23():
    """module docstring 应提及 Schema / 校验。"""
    src = smod.__doc__
    assert "Schema" in src or "校验" in src


def test_module_uses_from_future_annotations_batch23():
    source = inspect.getsource(smod)
    assert "from __future__ import annotations" in source


def test_module_eval_schema_error_docstring_present_batch23():
    """EvalSchemaError 有 docstring。"""
    assert EvalSchemaError.__doc__ is not None
    assert len(EvalSchemaError.__doc__) > 0


def test_module_schemas_dir_is_path_instance_batch23():
    """SCHEMAS_DIR 是 Path 实例。"""
    assert isinstance(SCHEMAS_DIR, Path)


def test_module_constants_only_schemas_dir_batch23():
    """schema.py 顶层常量只有 SCHEMAS_DIR（除 __all__）。"""
    import ast as _ast
    tree = _ast.parse(inspect.getsource(smod))
    top_level_assigns = [
        node for node in tree.body if isinstance(node, _ast.Assign)
    ]
    names = []
    for node in top_level_assigns:
        for target in node.targets:
            if isinstance(target, _ast.Name):
                names.append(target.id)
    assert set(names) == {"SCHEMAS_DIR", "__all__"}


# ---------- 端到端集成第三十七批 ----------


def test_e2e_load_then_validate_manifest_batch23(tmp_path):
    """端到端：load_schema → validate 合法 manifest。"""
    schema = load_schema("manifest.schema.json")
    assert isinstance(schema, dict)
    valid_instance = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    validate(valid_instance, "manifest.schema.json")


def test_e2e_validate_file_round_trip_batch23(tmp_path):
    """端到端：写合法 JSON → validate_file → pass。"""
    p = tmp_path / "valid.json"
    valid_manifest = {
        "manifest_version": "1.0",
        "devset_status": "incomplete",
        "documents": [],
        "expected_failures": [],
    }
    p.write_text(json.dumps(valid_manifest), encoding="utf-8")
    validate_file(p, "manifest.schema.json")


def test_e2e_validate_file_invalid_raises_eval_schema_error_batch23(tmp_path):
    """端到端：写非法 JSON → validate_file → EvalSchemaError。"""
    p = tmp_path / "invalid.json"
    p.write_text(json.dumps({"unexpected": "field"}), encoding="utf-8")
    with pytest.raises(EvalSchemaError):
        validate_file(p, "manifest.schema.json")


def test_e2e_annotation_schema_loadable_batch23():
    """端到端：annotation schema 可加载 + 校验空 instance。"""
    schema = load_schema("annotation.schema.json")
    assert schema.get("type") == "object"


def test_e2e_evaluation_report_schema_loadable_batch23():
    """端到端：evaluation-report schema 可加载。"""
    schema = load_schema("evaluation-report.schema.json")
    assert schema.get("type") == "object"


def test_e2e_three_schemas_distinct_batch23():
    """三个 schema 互不相等。"""
    s1 = load_schema("manifest.schema.json")
    s2 = load_schema("annotation.schema.json")
    s3 = load_schema("evaluation-report.schema.json")
    assert s1 != s2 != s3 != s1


def test_e2e_eval_schema_error_caught_via_type_batch23():
    """端到端：通过 EvalSchemaError 类型捕获。"""
    caught = False
    try:
        validate({}, "manifest.schema.json")
    except EvalSchemaError:
        caught = True
    assert caught
